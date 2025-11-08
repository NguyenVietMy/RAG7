import os
import logging
from typing import List, Optional
import httpx

from openai import OpenAI

logger = logging.getLogger(__name__)


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Embed texts using OpenAI API, automatically batching if needed.
    """
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be set to embed texts or provide embeddings directly")

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
        if len(texts) <= BATCH_SIZE:
            resp = client.embeddings.create(model=model_name, input=texts)
            return [item.embedding for item in resp.data]
        
        # Otherwise, process in batches
        all_embeddings = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
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

