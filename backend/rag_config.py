import os
from pathlib import Path
from typing import Optional
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

# Load .env from the backend directory (alongside this file) if present
# Also try parent directory .env (for project-wide env vars)
_ENV_PATH = Path(__file__).parent / ".env"
_PARENT_ENV_PATH = Path(__file__).parent.parent / ".env"

load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)
load_dotenv(dotenv_path=_PARENT_ENV_PATH if _PARENT_ENV_PATH.exists() else None, override=False)

logger = logging.getLogger(__name__)


def _get_db_connection():
    """Get PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5433")),
            database=os.getenv("POSTGRES_DB", "lola_db"),
            user=os.getenv("POSTGRES_USER", "lola"),
            password=os.getenv("POSTGRES_PASSWORD", "lola_dev_password"),
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return None


def get_rag_config() -> Optional[dict]:
    """
    Get RAG configuration from PostgreSQL (single config for local app).
    Returns None if settings don't exist or database is not configured.
    """
    conn = _get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM rag_settings ORDER BY created_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            
            if row:
                logger.info(f"Retrieved RAG config: rag_n_results={row['rag_n_results']}, threshold={row['rag_similarity_threshold']}, max_tokens={row['rag_max_context_tokens']}")
                config = {
                    "rag_n_results": row["rag_n_results"],
                    "rag_similarity_threshold": float(row["rag_similarity_threshold"]),
                    "rag_max_context_tokens": row["rag_max_context_tokens"],
                }
                # Add chat_model if it exists
                if "chat_model" in row and row["chat_model"]:
                    config["chat_model"] = row["chat_model"]
                return config
            logger.debug("No RAG config found")
            return None
    except Exception as e:
        logger.warning(f"Error fetching RAG config from PostgreSQL: {str(e)}")
        return None
    finally:
        conn.close()


def upsert_rag_config(config: dict) -> bool:
    """
    Create or update RAG configuration in PostgreSQL (single config for local app).
    Returns True if successful, False otherwise.
    """
    conn = _get_db_connection()
    if not conn:
        logger.warning("PostgreSQL connection not available")
        return False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if config exists
            cur.execute("SELECT id FROM rag_settings LIMIT 1")
            existing = cur.fetchone()
            
            rag_n_results = config.get("rag_n_results", 3)
            rag_similarity_threshold = config.get("rag_similarity_threshold", 0.0)
            rag_max_context_tokens = config.get("rag_max_context_tokens", 2000)
            
            if existing:
                # Update existing
                cur.execute(
                    """UPDATE rag_settings 
                       SET rag_n_results = %s, 
                           rag_similarity_threshold = %s, 
                           rag_max_context_tokens = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    [rag_n_results, rag_similarity_threshold, rag_max_context_tokens, existing["id"]]
                )
            else:
                # Insert new
                cur.execute(
                    """INSERT INTO rag_settings 
                       (rag_n_results, rag_similarity_threshold, rag_max_context_tokens, created_at, updated_at)
                       VALUES (%s, %s, %s, NOW(), NOW())""",
                    [rag_n_results, rag_similarity_threshold, rag_max_context_tokens]
                )
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error upserting RAG config to PostgreSQL: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        conn.rollback()
        return False
    finally:
        conn.close()

