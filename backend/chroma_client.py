import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
import chromadb


# Load .env from the backend directory (alongside this file) if present
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)


class MissingEnvironmentVariableError(RuntimeError):
    """Raised when a required environment variable is not set."""


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    api_key = (os.getenv("CHROMA_API_KEY") or "").strip()
    tenant = (os.getenv("CHROMA_TENANT") or "").strip()
    database = (os.getenv("CHROMA_DATABASE") or "Lola").strip()

    if not api_key or not tenant:
        raise MissingEnvironmentVariableError(
            "CHROMA_API_KEY and CHROMA_TENANT must be set in environment (.env)"
        )
    return chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)
