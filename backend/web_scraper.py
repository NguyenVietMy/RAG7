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


def create_embeddings_batch_with_retry(texts: List[str], max_retries: int = 3) -> List[List[float]]:
    """
    Create embeddings for multiple texts with retry logic and exponential backoff.
    
    Based on the mcp-crawl4ai-rag implementation pattern.
    
    Args:
        texts: List of texts to create embeddings for
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        List of embeddings (each embedding is a list of floats)
        Each embedding is 1536 dimensions for text-embedding-3-small
    
    Error Handling Strategy:
    1. Retry up to max_retries times with exponential backoff (1s, 2s, 4s)
    2. If batch fails after retries, fall back to individual embedding creation
    3. If individual embedding fails, return zero vector (1536 zeros) as fallback
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
    retry_delay = 1.0  # Start with 1 second delay
    
    http_client = httpx.Client(timeout=httpx.Timeout(120.0))
    client = OpenAI(api_key=api_key, http_client=http_client)
    
    try:
        for retry in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=model,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if retry < max_retries - 1:
                    logger.warning(f"Error creating batch embeddings (attempt {retry + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to create batch embeddings after {max_retries} attempts: {e}")
                    # Fallback: Try creating embeddings one by one
                    logger.info("Attempting to create embeddings individually...")
                    embeddings = []
                    successful_count = 0
                    
                    for i, text in enumerate(texts):
                        try:
                            individual_response = client.embeddings.create(
                                model=model,
                                input=[text]
                            )
                            embeddings.append(individual_response.data[0].embedding)
                            successful_count += 1
                        except Exception as individual_error:
                            logger.warning(f"Failed to create embedding for text {i}: {individual_error}")
                            # Add zero embedding as fallback
                            embeddings.append([0.0] * 1536)
                    
                    logger.info(f"Successfully created {successful_count}/{len(texts)} embeddings individually")
                    return embeddings
    finally:
        http_client.close()
    
    # Final fallback: return zero vectors
    logger.error("All embedding attempts failed, returning zero vectors")
    return [[0.0] * 1536 for _ in texts]


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
    max_concurrent: int = 10
) -> List[Dict[str, str]]:
    """
    Batch crawl multiple URLs in parallel with memory management.
    
    Args:
        crawler: AsyncWebCrawler instance
        urls: List of URLs to crawl
        max_concurrent: Maximum number of concurrent browser sessions (default: 10)
    
    Returns:
        List of dictionaries with keys: 'url' and 'markdown'
        Only includes successful crawls with markdown content
    """
    if not CRAWL4AI_AVAILABLE:
        logger.error("crawl4ai not available, cannot perform batch crawling")
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
    max_depth: int = 3,
    max_concurrent: int = 10
) -> List[Dict[str, str]]:
    """
    Recursively crawl internal links from start URLs up to maximum depth.
    
    Args:
        crawler: AsyncWebCrawler instance
        start_urls: List of starting URLs (seed URLs)
        max_depth: Maximum recursion depth (default: 3)
        max_concurrent: Maximum concurrent browser sessions (default: 10)
    
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
    
    for depth in range(max_depth):
        # Filter out already visited URLs
        urls_to_crawl = [
            normalize_url(url)
            for url in current_urls
            if normalize_url(url) not in visited
        ]
        
        if not urls_to_crawl:
            break  # No more URLs to crawl
        
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
    max_depth: int = 3,
    max_concurrent: int = 10,
    chunk_size: int = 5000
) -> Dict[str, Any]:
    """
    Intelligently crawl a URL based on its type.
    
    Args:
        url: URL to crawl (can be sitemap, txt file, or regular webpage)
        strategy: Crawling strategy - "auto", "sitemap", "text_file", or "recursive"
        max_depth: Maximum recursion depth for recursive strategy (default: 3)
        max_concurrent: Maximum concurrent browser sessions (default: 10)
        chunk_size: Chunk size for markdown splitting (default: 5000)
    
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
            if strategy == "text_file":
                crawl_results = await crawl_markdown_file(crawler, url)
                crawl_type = "text_file"
            elif strategy == "sitemap":
                sitemap_urls = parse_sitemap(url)
                if not sitemap_urls:
                    return {
                        "success": False,
                        "error": "No URLs found in sitemap"
                    }
                crawl_results = await crawl_batch(crawler, sitemap_urls, max_concurrent=max_concurrent)
                crawl_type = "sitemap"
            else:  # recursive
                crawl_results = await crawl_recursive_internal_links(
                    crawler,
                    [url],
                    max_depth=max_depth,
                    max_concurrent=max_concurrent
                )
                crawl_type = "webpage"
        
        if not crawl_results:
            return {
                "success": False,
                "error": "No content found"
            }
        
        # Process all crawled pages: chunk and embed
        all_chunks = []
        all_texts_for_embedding = []
        
        for doc in crawl_results:
            source_url = doc['url']
            markdown = doc['markdown']
            
            # Chunk the markdown
            chunks = smart_chunk_markdown(markdown, chunk_size=chunk_size)
            
            # Prepare chunks for embedding
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    'url': source_url,
                    'chunk_index': i,
                    'content': chunk
                })
                all_texts_for_embedding.append(chunk)
        
        # Generate embeddings in batches with retry logic
        logger.info(f"Generating embeddings for {len(all_texts_for_embedding)} chunks...")
        embeddings = create_embeddings_batch_with_retry(all_texts_for_embedding)
        
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

