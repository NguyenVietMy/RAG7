"""
Document Summarization Service

Implements hierarchical summarization algorithm for cost-efficient document summarization.
Process: 25 chunks per batch → batch summaries → final summary
Cost: ~22-23 LLM calls for 500 chunks
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import httpx

from dotenv import load_dotenv
from chroma_client import get_chroma_client

# Load environment variables
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)

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


class DocumentSummarizer:
    """Hierarchical document summarization service."""
    
    def __init__(self, model: Optional[str] = None):
        """Initialize summarizer with OpenAI client."""
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY must be set")
        
        http_client = httpx.Client(timeout=httpx.Timeout(120.0))  # Longer timeout for summarization
        self.client = OpenAI(api_key=api_key, http_client=http_client)
        self.model = model or os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.chunks_per_batch = 25  # Process 25 chunks at a time
    
    def summarize_document(
        self,
        collection_name: str,
        filename: str,
        chunks_per_batch: int = 25
    ) -> Dict[str, Any]:
        """
        Generate hierarchical summary of a document.
        
        Algorithm:
        1. Retrieve all chunks for the document from ChromaDB
        2. Process in batches of 25 chunks → generate batch summaries
        3. Final summarization: combine all batch summaries → final summary
        4. Store summary in PostgreSQL
        
        Args:
            collection_name: Name of the ChromaDB collection
            filename: Name of the file to summarize
            chunks_per_batch: Number of chunks per batch (default: 25)
        
        Returns:
            Dictionary with summary, metadata, and processing stats
        """
        try:
            # Check if summary already exists
            existing_summary = self.get_summary(collection_name, filename)
            if existing_summary:
                logger.info(f"Summary already exists for '{filename}', returning cached summary")
                return {
                    "summary": existing_summary["summary"],
                    "chunks_processed": existing_summary.get("chunks_processed"),
                    "llm_calls_made": existing_summary.get("llm_calls_made", 0),
                    "model_used": existing_summary.get("model_used"),
                    "cached": True,
                    "created_at": existing_summary.get("created_at"),
                    "updated_at": existing_summary.get("updated_at")
                }
            
            # Get all chunks for this document
            client = get_chroma_client()
            collection = client.get_collection(collection_name)
            
            # Query all chunks for this filename
            results = collection.get(
                where={"filename": filename},
                include=["documents", "metadatas"]
            )
            
            if not results["ids"]:
                return {
                    "error": f"No chunks found for file '{filename}' in collection '{collection_name}'"
                }
            
            chunks = results["documents"]
            total_chunks = len(chunks)
            
            logger.info(f"Summarizing document '{filename}': {total_chunks} chunks")
            
            # Step 1: Process chunks in batches
            batch_summaries = []
            llm_calls = 0
            
            for i in range(0, total_chunks, chunks_per_batch):
                batch = chunks[i:i + chunks_per_batch]
                batch_num = (i // chunks_per_batch) + 1
                total_batches = (total_chunks + chunks_per_batch - 1) // chunks_per_batch
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
                
                # Create batch summary
                batch_text = "\n\n---\n\n".join(batch)
                batch_summary = self._summarize_batch(batch_text, batch_num, total_batches)
                llm_calls += 1
                
                if batch_summary:
                    batch_summaries.append(batch_summary)
                else:
                    logger.warning(f"Failed to generate summary for batch {batch_num}")
            
            if not batch_summaries:
                return {
                    "error": "Failed to generate any batch summaries"
                }
            
            # Step 2: Final summarization
            logger.info(f"Generating final summary from {len(batch_summaries)} batch summaries")
            
            # If we have many batch summaries, may need to summarize in stages
            if len(batch_summaries) > 10:
                # Two-stage final summarization
                # Stage 1: Summarize first half
                first_half = "\n\n---\n\n".join(batch_summaries[:len(batch_summaries)//2])
                first_summary = self._summarize_batch(first_half, 1, 2)
                llm_calls += 1
                
                # Stage 2: Summarize second half
                second_half = "\n\n---\n\n".join(batch_summaries[len(batch_summaries)//2:])
                second_summary = self._summarize_batch(second_half, 2, 2)
                llm_calls += 1
                
                # Stage 3: Final summary
                combined = f"{first_summary}\n\n---\n\n{second_summary}"
                final_summary = self._create_final_summary(combined, filename)
                llm_calls += 1
            else:
                # Single-stage final summarization
                combined = "\n\n---\n\n".join(batch_summaries)
                final_summary = self._create_final_summary(combined, filename)
                llm_calls += 1
            
            # Step 3: Store in PostgreSQL
            stored = self._store_summary(
                collection_name=collection_name,
                filename=filename,
                summary=final_summary,
                chunks_processed=total_chunks,
                llm_calls_made=llm_calls,
                model_used=self.model
            )
            
            return {
                "summary": final_summary,
                "chunks_processed": total_chunks,
                "batches_processed": len(batch_summaries),
                "llm_calls_made": llm_calls,
                "model_used": self.model,
                "stored": stored
            }
            
        except Exception as e:
            logger.error(f"Error summarizing document: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _summarize_batch(self, batch_text: str, batch_num: int, total_batches: int) -> str:
        """Summarize a batch of chunks."""
        prompt = f"""Summarize the following content from a document. This is batch {batch_num} of {total_batches}.

Focus on:
- Key concepts and main ideas
- Important details and facts
- Technical information if present
- Structure and organization

Content:
{batch_text}

Summary:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error summarizing batch {batch_num}: {e}")
            return ""
    
    def _create_final_summary(self, combined_summaries: str, filename: str) -> str:
        """Create final comprehensive summary from batch summaries."""
        prompt = f"""Create a comprehensive summary of the document "{filename}" based on these batch summaries.

The summary should:
- Synthesize all key information from the batch summaries
- Provide a coherent overview of the entire document
- Highlight main themes, concepts, and important details
- Be well-structured and easy to understand

Batch Summaries:
{combined_summaries}

Comprehensive Summary:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error creating final summary: {e}")
            return ""
    
    def _store_summary(
        self,
        collection_name: str,
        filename: str,
        summary: str,
        chunks_processed: int,
        llm_calls_made: int,
        model_used: str
    ) -> bool:
        """Store summary in PostgreSQL."""
        conn = _get_db_connection()
        if not conn:
            logger.warning("PostgreSQL connection not available")
            return False
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Upsert: Update if exists, insert if new
                cur.execute(
                    """INSERT INTO document_summaries 
                       (collection_name, filename, summary, chunks_processed, llm_calls_made, model_used, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                       ON CONFLICT (collection_name, filename)
                       DO UPDATE SET
                           summary = EXCLUDED.summary,
                           chunks_processed = EXCLUDED.chunks_processed,
                           llm_calls_made = EXCLUDED.llm_calls_made,
                           model_used = EXCLUDED.model_used,
                           updated_at = NOW()""",
                    [collection_name, filename, summary, chunks_processed, llm_calls_made, model_used]
                )
                conn.commit()
                logger.info(f"Stored summary for {collection_name}/{filename}")
                return True
        except Exception as e:
            logger.error(f"Error storing summary: {e}", exc_info=True)
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_summary(self, collection_name: str, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored summary from PostgreSQL."""
        conn = _get_db_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT summary, chunks_processed, llm_calls_made, model_used, created_at, updated_at
                       FROM document_summaries
                       WHERE collection_name = %s AND filename = %s""",
                    [collection_name, filename]
                )
                row = cur.fetchone()
                
                if row:
                    return {
                        "summary": row["summary"],
                        "chunks_processed": row["chunks_processed"],
                        "llm_calls_made": row["llm_calls_made"],
                        "model_used": row["model_used"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving summary: {e}")
            return None
        finally:
            conn.close()

