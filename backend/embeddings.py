import os
from typing import List, Optional

from openai import OpenAI


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be set to embed texts or provide embeddings directly")

    client = OpenAI(api_key=api_key)
    model_name = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # OpenAI SDK v1 returns data[].embedding
    resp = client.embeddings.create(model=model_name, input=texts)
    return [item.embedding for item in resp.data]

