"""
Web Scraping Service

Comprehensive web crawling system with three distinct strategies:
1. Sitemap crawling - Parse sitemap.xml and crawl all URLs in parallel
2. Text file crawling - Directly retrieve .txt/markdown files
3. Recursive internal link crawling - Follow internal links recursively

Includes smart markdown chunking and batch embedding generation with retry logic.
"""
import os
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urldefrag
from xml.etree import ElementTree
import requests

from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)

logger = logging.getLogger(__name__)

# Try to import crawl4ai, but handle gracefully if not installed
# Note: crawl4ai requires uvloop which doesn't support Windows
# On Windows, you may need to install dependencies manually or use an alternative approach
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, MemoryAdaptiveDispatcher
    CRAWL4AI_AVAILABLE = True
except ImportError as e:
    CRAWL4AI_AVAILABLE = False
    # Create a dummy class for type hints when crawl4ai is not available
    from typing import Any
    AsyncWebCrawler = Any
    BrowserConfig = Any
    CrawlerRunConfig = Any
    CacheMode = Any
    MemoryAdaptiveDispatcher = Any
    import sys
    if sys.platform == "win32":
        logger.warning(
            "crawl4ai not available on Windows (requires uvloop which doesn't support Windows). "
            "Web scraping features will be limited. Consider using Linux/WSL or Docker for web scraping."
        )
    else:
        logger.warning(f"crawl4ai not installed: {e}. Web scraping features will be limited.")


def smart_chunk_markdown(text: str, chunk_size: int = 5000) -> List[str]:
    """
    Split text into chunks, respecting code blocks and paragraphs.
    
    Based on the mcp-crawl4ai-rag implementation pattern.
    
    Args:
        text: The markdown text to chunk
        chunk_size: Target size for each chunk in characters (default: 5000)
    
    Returns:
        List of text chunks
    
    Chunking Strategy (in priority order):
    1. Code block boundaries (```): Prefer breaking at code block endings
    2. Paragraph breaks (\n\n): Break at double newlines if past 30% of chunk_size
    3. Sentence breaks (. ): Break at sentence endings if past 30% of chunk_size
    4. Hard break: If no natural break found, break at exact chunk_size
    
    Rules:
    - Only break at natural boundaries if past 30% of chunk_size (prevents tiny chunks)
    - Always preserve code blocks intact
    - Strip whitespace from each chunk
    - Skip empty chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:  # Only break if past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            # Find the last sentence break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:  # Only break if past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = end

    return chunks


def _estimate_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """
    Estimate token count for a text using character-based estimation.
    
    Uses a conservative estimate: 1 token ≈ 4 characters for English text.
    This is a safe approximation that works well for most cases.
    """
    # Rough estimate: 1 token ≈ 4 characters for English text
    # This is conservative and works well for embedding models
    return len(text) // 4


def _is_token_limit_error(error: Exception) -> bool:
    """Check if an error is related to token/context length limits."""
    error_str = str(error).lower()
    token_limit_indicators = [
        "maximum context length",
        "token limit",
        "context length exceeded",
        "too many tokens",
        "maximum tokens",
        "input is too long",
        "context_length_exceeded"
    ]
    return any(indicator in error_str for indicator in token_limit_indicators)


def create_embeddings_batch_with_retry(texts: List[str], max_retries: int = 3, batch_size: int = 2048) -> List[List[float]]:
    """
    Create embeddings for multiple texts with retry logic and exponential backoff.
    
    Based on the mcp-crawl4ai-rag implementation pattern.
    
    Args:
        texts: List of texts to create embeddings for
        max_retries: Maximum number of retry attempts (default: 3)
        batch_size: Maximum number of texts per API call (default: 2048, OpenAI's limit)
    
    Returns:
        List of embeddings (each embedding is a list of floats)
        Each embedding is 1536 dimensions for text-embedding-3-small
    
    Error Handling Strategy:
    1. Split large batches into chunks of batch_size
    2. Check token limits before sending (max ~8000 tokens per request)
    3. Retry up to max_retries times with exponential backoff (1s, 2s, 4s)
    4. If token limit error, split batch by token count instead of text count
    5. If batch fails after retries, fall back to smaller batches
    6. If individual batch fails, return zero vector (1536 zeros) as fallback
    """
    if not texts:
        return []
    
    from openai import OpenAI
    import httpx
    
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        logger.error("OPENAI_API_KEY not set, cannot generate embeddings")
        return [[0.0] * 1536 for _ in texts]
    
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Token limits: OpenAI embedding models typically allow ~8000 tokens per request
    # Using 7000 as a safe limit to account for overhead
    MAX_TOKENS_PER_BATCH = 7000
    
    http_client = httpx.Client(timeout=httpx.Timeout(120.0))
    client = OpenAI(api_key=api_key, http_client=http_client)
    
    all_embeddings = []
    total_texts = len(texts)
    
    try:
        # First pass: split by batch_size (number of texts)
        current_batch = []
        current_batch_tokens = 0
        batch_num = 0
        
        for i, text in enumerate(texts):
            text_tokens = _estimate_tokens(text, model)
            
            # Check if adding this text would exceed limits
            would_exceed_count = len(current_batch) >= batch_size
            would_exceed_tokens = (current_batch_tokens + text_tokens) > MAX_TOKENS_PER_BATCH
            
            if would_exceed_count or would_exceed_tokens:
                # Process current batch
                if current_batch:
                    batch_num += 1
                    total_batches = (total_texts + batch_size - 1) // batch_size
                    if total_batches > 1:
                        logger.info(f"Processing embedding batch {batch_num} ({len(current_batch)} texts, ~{current_batch_tokens} tokens)...")
                    
                    batch_embeddings = _process_single_batch(
                        client, model, current_batch, batch_num, max_retries
                    )
                    all_embeddings.extend(batch_embeddings)
                    
                    # Small delay between batches to avoid rate limiting
                    time.sleep(0.1)
                
                # Start new batch
                current_batch = [text]
                current_batch_tokens = text_tokens
            else:
                # Add to current batch
                current_batch.append(text)
                current_batch_tokens += text_tokens
        
        # Process final batch
        if current_batch:
            batch_num += 1
            total_batches = (total_texts + batch_size - 1) // batch_size
            if total_batches > 1:
                logger.info(f"Processing embedding batch {batch_num} ({len(current_batch)} texts, ~{current_batch_tokens} tokens)...")
            
            batch_embeddings = _process_single_batch(
                client, model, current_batch, batch_num, max_retries
            )
            all_embeddings.extend(batch_embeddings)
        
        logger.info(f"✅ Successfully generated {len(all_embeddings)} embeddings from {total_texts} texts")
        return all_embeddings
        
    finally:
        http_client.close()
    
    # Final fallback: return zero vectors
    logger.error("All embedding attempts failed, returning zero vectors")
    return [[0.0] * 1536 for _ in texts]


def _process_single_batch(
    client: Any,
    model: str,
    batch_texts: List[str],
    batch_num: int,
    max_retries: int
) -> List[List[float]]:
    """
    Process a single batch of texts, handling token limit errors by splitting further.
    
    Returns:
        List of embeddings for the batch
    """
    retry_delay = 1.0
    
    # Retry logic for this batch
    for retry in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model,
                input=batch_texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a token limit error
            if _is_token_limit_error(e):
                logger.warning(f"Token limit exceeded for batch {batch_num} ({len(batch_texts)} texts). Splitting by token count...")
                # Split by token count instead
                return _process_batch_by_tokens(client, model, batch_texts, batch_num, max_retries)
            
            # For other errors, retry with exponential backoff
            if retry < max_retries - 1:
                logger.warning(f"Error creating batch embeddings (attempt {retry + 1}/{max_retries}): {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to create batch embeddings after {max_retries} attempts: {e}")
                # Fallback: Try smaller batches or individual calls
                logger.info(f"Attempting to process batch {batch_num} in smaller chunks...")
                return _process_batch_with_fallback(client, model, batch_texts, batch_num)
    
    # If all retries failed, return zero vectors
    logger.warning(f"Batch {batch_num} completely failed, adding zero vectors")
    return [[0.0] * 1536 for _ in batch_texts]


def _process_batch_by_tokens(
    client: Any,
    model: str,
    batch_texts: List[str],
    batch_num: int,
    max_retries: int,
    max_tokens_per_chunk: int = 6000
) -> List[List[float]]:
    """
    Process a batch by splitting it into token-limited chunks.
    """
    all_embeddings = []
    current_chunk = []
    current_chunk_tokens = 0
    chunk_num = 0
    
    for text in batch_texts:
        text_tokens = _estimate_tokens(text, model)
        
        if (current_chunk_tokens + text_tokens) > max_tokens_per_chunk and current_chunk:
            # Process current chunk
            chunk_num += 1
            logger.info(f"  Processing token-limited chunk {chunk_num} of batch {batch_num} ({len(current_chunk)} texts, ~{current_chunk_tokens} tokens)...")
            
            chunk_embeddings = _process_single_batch(client, model, current_chunk, f"{batch_num}.{chunk_num}", max_retries)
            all_embeddings.extend(chunk_embeddings)
            
            # Start new chunk
            current_chunk = [text]
            current_chunk_tokens = text_tokens
        else:
            current_chunk.append(text)
            current_chunk_tokens += text_tokens
    
    # Process final chunk
    if current_chunk:
        chunk_num += 1
        logger.info(f"  Processing token-limited chunk {chunk_num} of batch {batch_num} ({len(current_chunk)} texts, ~{current_chunk_tokens} tokens)...")
        chunk_embeddings = _process_single_batch(client, model, current_chunk, f"{batch_num}.{chunk_num}", max_retries)
        all_embeddings.extend(chunk_embeddings)
    
    return all_embeddings


def _process_batch_with_fallback(
    client: Any,
    model: str,
    batch_texts: List[str],
    batch_num: int
) -> List[List[float]]:
    """
    Fallback: Try processing in smaller sub-batches, then individual calls if needed.
    """
    batch_embeddings = []
    successful_count = 0
    
    # Try processing in smaller sub-batches first
    sub_batch_size = max(1, len(batch_texts) // 4)
    for sub_start in range(0, len(batch_texts), sub_batch_size):
        sub_end = min(sub_start + sub_batch_size, len(batch_texts))
        sub_batch = batch_texts[sub_start:sub_end]
        
        try:
            sub_response = client.embeddings.create(
                model=model,
                input=sub_batch
            )
            batch_embeddings.extend([item.embedding for item in sub_response.data])
            successful_count += len(sub_batch)
        except Exception as sub_error:
            logger.warning(f"Failed sub-batch, falling back to individual calls: {sub_error}")
            # Final fallback: individual calls
            for text in sub_batch:
                try:
                    individual_response = client.embeddings.create(
                        model=model,
                        input=[text]
                    )
                    batch_embeddings.append(individual_response.data[0].embedding)
                    successful_count += 1
                except Exception as individual_error:
                    logger.warning(f"Failed individual embedding: {individual_error}")
                    batch_embeddings.append([0.0] * 1536)
    
    logger.info(f"Successfully created {successful_count}/{len(batch_texts)} embeddings for batch {batch_num}")
    return batch_embeddings


def is_sitemap(url: str) -> bool:
    """Check if a URL is a sitemap."""
    return url.endswith('sitemap.xml') or 'sitemap' in urlparse(url).path.lower()


def is_txt(url: str) -> bool:
    """Check if a URL is a text file."""
    return url.endswith('.txt') or url.endswith('.md') or url.endswith('.markdown')


def parse_sitemap(sitemap_url: str) -> List[str]:
    """
    Parse a sitemap XML and extract all URLs.
    
    Args:
        sitemap_url: URL of the sitemap (e.g., 'https://example.com/sitemap.xml')
    
    Returns:
        List of URLs found in the sitemap
    """
    try:
        resp = requests.get(sitemap_url, timeout=30)
        urls = []
        if resp.status_code == 200:
            try:
                tree = ElementTree.fromstring(resp.content)
                # Find all <loc> elements regardless of namespace
                urls = [loc.text for loc in tree.findall('.//{*}loc') if loc.text]
            except Exception as e:
                logger.error(f"Error parsing sitemap XML: {e}")
        return urls
    except Exception as e:
        logger.error(f"Error fetching sitemap: {e}")
        return []


async def crawl_batch(
    crawler: AsyncWebCrawler,
    urls: List[str],
    max_concurrent: int = 3,
    max_pages: int = 300,
    timeout_seconds: int = 90
) -> List[Dict[str, str]]:
    """
    Batch crawl multiple URLs in parallel with memory management.
    
    Args:
        crawler: AsyncWebCrawler instance
        urls: List of URLs to crawl
        max_concurrent: Maximum number of concurrent browser sessions (default: 3)
        max_pages: Maximum number of pages to crawl (default: 300)
        timeout_seconds: Maximum time to spend crawling in seconds (default: 90)
    
    Returns:
        List of dictionaries with keys: 'url' and 'markdown'
        Only includes successful crawls with markdown content
    """
    if not CRAWL4AI_AVAILABLE:
        logger.error("crawl4ai not available, cannot perform batch crawling")
        return []
    
    import time as time_module
    start_time = time_module.time()
    
    # Limit number of URLs to prevent resource exhaustion
    if len(urls) > max_pages:
        logger.warning(f"Limiting crawl to {max_pages} pages (found {len(urls)} URLs)")
        urls = urls[:max_pages]
    
    # Check timeout before starting
    if time_module.time() - start_time > timeout_seconds:
        logger.warning(f"Timeout reached before starting batch crawl")
        return []
    
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=False
    )
    
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent
    )
    
    results = await crawler.arun_many(
        urls=urls,
        config=crawl_config,
        dispatcher=dispatcher
    )
    
    return [
        {'url': r.url, 'markdown': r.markdown}
        for r in results
        if r.success and r.markdown
    ]


async def crawl_markdown_file(
    crawler: AsyncWebCrawler,
    url: str
) -> List[Dict[str, str]]:
    """
    Crawl a .txt or markdown file directly.
    
    Args:
        crawler: AsyncWebCrawler instance
        url: URL of the text file
    
    Returns:
        List with single dictionary containing 'url' and 'markdown' keys
        Returns empty list if crawl fails
    """
    if not CRAWL4AI_AVAILABLE:
        logger.error("crawl4ai not available, cannot crawl markdown file")
        return []
    
    crawl_config = CrawlerRunConfig()
    result = await crawler.arun(url=url, config=crawl_config)
    
    if result.success and result.markdown:
        return [{'url': url, 'markdown': result.markdown}]
    else:
        logger.warning(f"Failed to crawl {url}: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
        return []


async def crawl_recursive_internal_links(
    crawler: AsyncWebCrawler,
    start_urls: List[str],
    max_depth: int = 2,
    max_concurrent: int = 3,
    max_pages: int = 300,
    timeout_seconds: int = 90
) -> List[Dict[str, str]]:
    """
    Recursively crawl internal links from start URLs up to maximum depth.
    
    Args:
        crawler: AsyncWebCrawler instance
        start_urls: List of starting URLs (seed URLs)
        max_depth: Maximum recursion depth (default: 2)
        max_concurrent: Maximum concurrent browser sessions (default: 3)
        max_pages: Maximum total pages to crawl (default: 300)
    
    Returns:
        List of dictionaries with 'url' and 'markdown' keys
    """
    if not CRAWL4AI_AVAILABLE:
        logger.error("crawl4ai not available, cannot perform recursive crawling")
        return []
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=False
    )
    
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent
    )
    
    visited = set()
    
    def normalize_url(url):
        """Remove fragment from URL to avoid duplicate crawls."""
        return urldefrag(url)[0]
    
    current_urls = set([normalize_url(u) for u in start_urls])
    results_all = []
    
    # Get base domain from first URL
    base_domain = urlparse(start_urls[0]).netloc if start_urls else None
    
    import time as time_module
    start_time = time_module.time()
    
    for depth in range(max_depth):
        # Check timeout
        elapsed = time_module.time() - start_time
        if elapsed > timeout_seconds:
            logger.warning(f"Timeout reached ({elapsed:.1f}s), stopping crawl")
            break
        
        # Stop if we've reached max_pages limit
        if len(results_all) >= max_pages:
            logger.info(f"Reached max_pages limit ({max_pages}), stopping crawl")
            break
        
        # Filter out already visited URLs
        urls_to_crawl = [
            normalize_url(url)
            for url in current_urls
            if normalize_url(url) not in visited
        ]
        
        if not urls_to_crawl:
            break  # No more URLs to crawl
        
        # Limit URLs per depth level to prevent resource exhaustion
        if len(urls_to_crawl) > max_pages - len(results_all):
            urls_to_crawl = urls_to_crawl[:max_pages - len(results_all)]
            logger.info(f"Limiting crawl at depth {depth} to {len(urls_to_crawl)} URLs")
        
        # Add rate limiting delay between depth levels
        if depth > 0:
            await asyncio.sleep(1.0)  # 1 second delay between depth levels
        
        # Crawl all URLs at current depth in parallel
        results = await crawler.arun_many(
            urls=urls_to_crawl,
            config=run_config,
            dispatcher=dispatcher
        )
        
        next_level_urls = set()
        for result in results:
            norm_url = normalize_url(result.url)
            visited.add(norm_url)
            
            if result.success and result.markdown:
                # Add to results
                results_all.append({
                    'url': result.url,
                    'markdown': result.markdown
                })
                
                # Stop if we've reached max_pages
                if len(results_all) >= max_pages:
                    break
                
                # Extract internal links for next depth level
                if hasattr(result, 'links') and result.links:
                    for link in result.links.get("internal", []):
                        link_href = link.get("href") if isinstance(link, dict) else link
                        if link_href:
                            next_url = normalize_url(link_href)
                            # Only follow links from same domain
                            if base_domain and urlparse(next_url).netloc == base_domain:
                                if next_url not in visited:
                                    next_level_urls.add(next_url)
        
        # Prepare URLs for next depth level
        current_urls = next_level_urls
    
    return results_all


async def smart_crawl_url(
    url: str,
    strategy: str = "auto",
    max_depth: int = 2,
    max_concurrent: int = 3,
    chunk_size: int = 5000,
    max_pages: int = 300,
    timeout_seconds: int = 90
) -> Dict[str, Any]:
    """
    Intelligently crawl a URL based on its type.
    
    Args:
        url: URL to crawl (can be sitemap, txt file, or regular webpage)
        strategy: Crawling strategy - "auto", "sitemap", "text_file", or "recursive"
        max_depth: Maximum recursion depth for recursive strategy (default: 2)
        max_concurrent: Maximum concurrent browser sessions (default: 3)
        chunk_size: Chunk size for markdown splitting (default: 5000)
        max_pages: Maximum number of pages to crawl (default: 300)
        timeout_seconds: Maximum time to spend crawling in seconds (default: 90)
    
    Returns:
        Dictionary with:
        - 'success': bool
        - 'crawl_type': str ('sitemap', 'text_file', or 'webpage')
        - 'pages_crawled': int
        - 'chunks': List[Dict] with keys: 'url', 'chunk_index', 'content', 'embedding'
        - 'error': str (if failed)
    """
    if not CRAWL4AI_AVAILABLE:
        import sys
        error_msg = "crawl4ai not available."
        if sys.platform == "win32":
            error_msg += " crawl4ai requires uvloop which doesn't support Windows. Consider using Linux/WSL or Docker."
        else:
            error_msg += " Install with: pip install crawl4ai==0.6.2"
        return {
            "success": False,
            "error": error_msg
        }
    
    try:
        import time as time_module
        start_time = time_module.time()
        
        crawl_results = []
        crawl_type = None
        
        # Strategy selection
        if strategy == "auto":
            if is_txt(url):
                strategy = "text_file"
            elif is_sitemap(url):
                strategy = "sitemap"
            else:
                strategy = "recursive"
        
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Check timeout before crawling
            elapsed = time_module.time() - start_time
            if elapsed > timeout_seconds:
                return {
                    "success": False,
                    "error": f"Timeout reached before starting crawl ({elapsed:.1f}s)"
                }
            
            if strategy == "text_file":
                logger.info(f"   Using text file strategy for: {url}")
                crawl_results = await crawl_markdown_file(crawler, url)
                crawl_type = "text_file"
            elif strategy == "sitemap":
                logger.info(f"   Using sitemap strategy, parsing sitemap...")
                sitemap_urls = parse_sitemap(url)
                if not sitemap_urls:
                    logger.error("   ❌ No URLs found in sitemap")
                    return {
                        "success": False,
                        "error": "No URLs found in sitemap"
                    }
                logger.info(f"   Found {len(sitemap_urls)} URLs in sitemap, crawling...")
                crawl_results = await crawl_batch(crawler, sitemap_urls, max_concurrent=max_concurrent, max_pages=max_pages, timeout_seconds=timeout_seconds)
                crawl_type = "sitemap"
            else:  # recursive
                logger.info(f"   Using recursive strategy (max_depth={max_depth}, max_pages={max_pages})...")
                crawl_results = await crawl_recursive_internal_links(
                    crawler,
                    [url],
                    max_depth=max_depth,
                    max_concurrent=max_concurrent,
                    max_pages=max_pages,
                    timeout_seconds=timeout_seconds
                )
                crawl_type = "webpage"
        
        if not crawl_results:
            logger.error("   ❌ No content found after crawling")
            return {
                "success": False,
                "error": "No content found"
            }
        
        logger.info(f"   ✅ Crawled {len(crawl_results)} pages successfully")
        
        # Process all crawled pages: chunk and embed
        logger.info(f"   Processing pages into chunks (chunk_size={chunk_size})...")
        all_chunks = []
        all_texts_for_embedding = []
        
        processed_pages = 0
        for doc in crawl_results:
            processed_pages += 1
            source_url = doc['url']
            markdown = doc['markdown']
            
            # Chunk the markdown
            chunks = smart_chunk_markdown(markdown, chunk_size=chunk_size)
            
            if processed_pages <= 5 or processed_pages % 10 == 0:
                logger.info(f"      Processing page {processed_pages}/{len(crawl_results)}: {source_url} → {len(chunks)} chunks")
            
            # Prepare chunks for embedding
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    'url': source_url,
                    'chunk_index': i,
                    'content': chunk
                })
                all_texts_for_embedding.append(chunk)
        
        logger.info(f"   ✅ Created {len(all_chunks)} total chunks from {len(crawl_results)} pages")
        
        # Generate embeddings in batches with retry logic
        logger.info(f"   Generating embeddings for {len(all_texts_for_embedding)} chunks...")
        embeddings = create_embeddings_batch_with_retry(all_texts_for_embedding)
        logger.info(f"   ✅ Generated {len(embeddings)} embeddings")
        
        # Attach embeddings to chunks
        for i, chunk_data in enumerate(all_chunks):
            chunk_data['embedding'] = embeddings[i] if i < len(embeddings) else [0.0] * 1536
        
        return {
            "success": True,
            "crawl_type": crawl_type,
            "pages_crawled": len(crawl_results),
            "chunks": all_chunks
        }
    
    except Exception as e:
        logger.error(f"Error in smart_crawl_url: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

