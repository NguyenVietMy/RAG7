import os
import logging
import re
from typing import List, Optional
import httpx

from openai import OpenAI

logger = logging.getLogger(__name__)


def clean_text_for_utf8(text: str) -> str:
    """
    Clean text to ensure it's valid UTF-8.
    Removes or replaces invalid Unicode characters, including surrogate pairs.
    """
    if not isinstance(text, str):
        # If it's already bytes, decode it first
        try:
            text = text.decode('utf-8', errors='replace')
        except (AttributeError, UnicodeDecodeError):
            return ""
    
    # First, try to encode/decode to catch any issues
    try:
        # This will raise UnicodeEncodeError if there are invalid characters
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # If encoding fails, we need to clean the text
        pass
    
    # Remove or replace problematic characters
    # Method 1: Replace surrogates and invalid chars
    try:
        # Encode to utf-8 with error handling, then decode back
        cleaned = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except Exception:
        # Fallback: remove all non-ASCII if still problematic
        cleaned = text.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    
    # Remove any remaining control characters that might cause issues
    # Keep common whitespace (space, tab, newline, carriage return)
    cleaned = ''.join(
        char if (ord(char) >= 32 or char in '\n\r\t') and ord(char) != 0xFFFE and ord(char) != 0xFFFF
        else ' '
        for char in cleaned
    )
    
    # Normalize whitespace (replace multiple spaces with single space, but keep newlines)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Multiple spaces/tabs to single space
    cleaned = re.sub(r'[ \t]*\n[ \t]*', '\n', cleaned)  # Clean up around newlines
    
    return cleaned


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Embed texts using OpenAI API, automatically batching if needed.
    Text is automatically cleaned to ensure valid UTF-8 encoding.
    """
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be set to embed texts or provide embeddings directly")

    # Clean all texts to ensure valid UTF-8 before embedding
    cleaned_texts = [clean_text_for_utf8(text) for text in texts]
    
    # Log if any texts were modified
    modified_count = sum(1 for orig, cleaned in zip(texts, cleaned_texts) if orig != cleaned)
    if modified_count > 0:
        logger.warning(f"Cleaned {modified_count} out of {len(texts)} texts to ensure valid UTF-8 encoding")

    # Create httpx client with explicit settings to avoid proxy-related issues
    # httpx 0.28.0+ removed proxies argument
    http_client = httpx.Client(
        timeout=httpx.Timeout(60.0)
    )
    
    try:
        client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )
        model_name = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # Batch size: 600 chunks per request (safely under 300k token limit)
        BATCH_SIZE = 600
        
        # If texts fit in one batch, process directly
        if len(cleaned_texts) <= BATCH_SIZE:
            resp = client.embeddings.create(model=model_name, input=cleaned_texts)
            return [item.embedding for item in resp.data]
        
        # Otherwise, process in batches
        all_embeddings = []
        total_batches = (len(cleaned_texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(cleaned_texts), BATCH_SIZE):
            batch = cleaned_texts[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            resp = client.embeddings.create(model=model_name, input=batch)
            batch_embeddings = [item.embedding for item in resp.data]
            all_embeddings.extend(batch_embeddings)
            
            if total_batches > 1:
                logger.info(f"Embedded batch {batch_num}/{total_batches} ({len(batch)} chunks)")
        
        return all_embeddings
    finally:
        # Clean up the http client
        http_client.close()

