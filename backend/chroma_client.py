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
    """
    Get ChromaDB client. Supports both self-hosted (Docker) and cloud modes.
    
    Self-hosted mode (default): Uses CHROMA_HOST and CHROMA_PORT
    Cloud mode (fallback): Uses CHROMA_API_KEY and CHROMA_TENANT if provided
    """
    # Check for self-hosted configuration first
    chroma_host = (os.getenv("CHROMA_HOST") or "localhost").strip()
    chroma_port = int(os.getenv("CHROMA_PORT") or "8001")
    database = (os.getenv("CHROMA_DATABASE") or "Lola").strip()
    
    # If cloud credentials are provided, use cloud client (backward compatibility)
    api_key = (os.getenv("CHROMA_API_KEY") or "").strip()
    tenant = (os.getenv("CHROMA_TENANT") or "").strip()
    
    if api_key and tenant:
        # Cloud mode (backward compatibility)
        return chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)
    
    # Self-hosted mode (default) - connect to local Docker instance
    # For self-hosted without auth, use empty settings
    return chromadb.HttpClient(
        host=chroma_host,
        port=chroma_port,
        settings=chromadb.Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
