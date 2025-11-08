import os
from pathlib import Path
from typing import Optional
import httpx
import logging

from dotenv import load_dotenv

# Load .env from the backend directory (alongside this file) if present
# Also try parent directory .env (for project-wide env vars)
_ENV_PATH = Path(__file__).parent / ".env"
_PARENT_ENV_PATH = Path(__file__).parent.parent / ".env"

load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)
load_dotenv(dotenv_path=_PARENT_ENV_PATH if _PARENT_ENV_PATH.exists() else None, override=False)

logger = logging.getLogger(__name__)


def _get_supabase_url() -> Optional[str]:
    """Get Supabase URL from environment."""
    # Try multiple possible env var names
    url = (
        os.getenv("SUPABASE_URL") 
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        or os.getenv("SUPABASE_PROJECT_URL")
    )
    
    if not url:
        logger.debug("Supabase URL not found in environment variables. Checked: SUPABASE_URL, NEXT_PUBLIC_SUPABASE_URL, SUPABASE_PROJECT_URL")
    
    return url


def _get_supabase_key() -> Optional[str]:
    """Get Supabase API key from environment."""
    # Try multiple possible env var names (prefer service role key for backend)
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    
    if not key:
        logger.debug("Supabase API key not found in environment variables. Checked: SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY, NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    return key


def get_rag_config() -> Optional[dict]:
    """
    Get RAG configuration from Supabase via HTTP API (single config for local app).
    Returns None if settings don't exist or Supabase is not configured.
    """
    supabase_url = _get_supabase_url()
    supabase_key = _get_supabase_key()
    
    if not supabase_url or not supabase_key:
        return None
    
    try:
        # Supabase REST API: GET /rest/v1/rag_settings (single config)
        url = f"{supabase_url}/rest/v1/rag_settings"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        # Get first config (limit=1)
        params = {"limit": "1"}
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                settings = data[0]
                logger.info(f"Retrieved RAG config: rag_n_results={settings.get('rag_n_results')}, threshold={settings.get('rag_similarity_threshold')}, max_tokens={settings.get('rag_max_context_tokens')}")
                return {
                    "rag_n_results": settings.get("rag_n_results", 3),
                    "rag_similarity_threshold": float(settings.get("rag_similarity_threshold", 0.0)),
                    "rag_max_context_tokens": settings.get("rag_max_context_tokens", 2000),
                }
            logger.debug("No RAG config found")
            return None
    except Exception as e:
        logger.warning(f"Error fetching RAG config from Supabase: {str(e)}")
        return None


def upsert_rag_config(config: dict) -> bool:
    """
    Create or update RAG configuration in Supabase via HTTP API (single config for local app).
    Returns True if successful, False otherwise.
    """
    supabase_url = _get_supabase_url()
    supabase_key = _get_supabase_key()
    
    if not supabase_url or not supabase_key:
        logger.warning("Supabase URL or API key not configured")
        return False
    
    try:
        # Supabase REST API: First check if config exists, then update or insert
        url = f"{supabase_url}/rest/v1/rag_settings"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        
        # Check if config exists
        with httpx.Client(timeout=10.0) as client:
            check_response = client.get(url, headers=headers, params={"limit": "1"})
            check_response.raise_for_status()
            existing = check_response.json()
            
            payload = {
                "rag_n_results": config.get("rag_n_results", 3),
                "rag_similarity_threshold": config.get("rag_similarity_threshold", 0.0),
                "rag_max_context_tokens": config.get("rag_max_context_tokens", 2000),
            }
            
            if existing and len(existing) > 0:
                # Update existing
                config_id = existing[0]["id"]
                update_url = f"{url}?id=eq.{config_id}"
                response = client.patch(update_url, headers=headers, json=payload)
            else:
                # Insert new
                response = client.post(url, headers=headers, json=payload)
            
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error upserting RAG config: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error upserting RAG config to Supabase: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

