import os
import logging
from typing import List, Optional, Dict, Any
from openai import OpenAI
import httpx

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
from embeddings import embed_texts
from system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, model: Optional[str] = None):
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY must be set")
        
        http_client = httpx.Client(timeout=httpx.Timeout(60.0))
        self.client = OpenAI(api_key=api_key, http_client=http_client)
        # Use provided model, or env var, or default
        self.model = model or os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.max_context_messages = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
    
    def generate_title(self, user_message: str) -> str:
        """Generate a chat title based on the user's prompt."""
        try:
            prompt = f"""Generate a concise, descriptive title (max 60 characters) for a chat conversation based on this user prompt:

User prompt: {user_message}

Title:"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.3
            )
            
            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')
            # Limit to 60 chars
            return title[:60] if title else "New chat"
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            return user_message[:50] if user_message else "New chat"
    
    def get_rag_context(
        self, 
        collection_name: str, 
        query: str, 
        n_results: int = 3,
        similarity_threshold: float = 0.0,
        max_context_tokens: int = 2000
    ) -> str:
        """
        Get relevant context from ChromaDB for RAG.
        
        Args:
            collection_name: Name of the ChromaDB collection
            query: User query to search for
            n_results: Number of results to retrieve (default: 3)
            similarity_threshold: Minimum similarity score (0.0-1.0) to include results (default: 0.0)
            max_context_tokens: Maximum tokens to include in context (default: 2000)
        
        Returns:
            Formatted context string, filtered by similarity and token limit
        """
        try:
            client = get_chroma_client()
            collection = client.get_collection(name=collection_name)
            
            # Get embedding model from collection metadata
            collection_metadata = collection.metadata or {}
            embedding_model = collection_metadata.get("embedding_model")
            
            # If no model in metadata, use default (for backward compatibility with old collections)
            if not embedding_model:
                embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            
            # Embed query using the same model as the collection
            query_embeddings = embed_texts([query], model=embedding_model)
            
            if not query_embeddings or len(query_embeddings) == 0:
                return ""
            
            # Query ChromaDB with the correctly embedded query
            # Note: ChromaDB returns distances (lower is better), so we need to convert to similarity
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results.get("documents") or not results["documents"][0]:
                return ""
            
            # Format context from retrieved documents, filtering by similarity threshold
            context_parts = []
            documents = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            
            # Log RAG query results
            logger.info(f"🔍 RAG Query Results (n_results={n_results}, threshold={similarity_threshold}):")
            logger.info(f"   Retrieved {len(documents)} documents from collection '{collection_name}'")
            
            # Rough token estimation: ~1 token per 4 characters (conservative estimate)
            current_tokens = 0
            included_count = 0
            
            for i, doc in enumerate(documents):
                # Convert distance to similarity (assuming cosine distance, 0 = perfect match, 2 = opposite)
                # Similarity = 1 - (distance / 2) for cosine distance
                distance = distances[i] if i < len(distances) else 1.0
                similarity = 1.0 - (distance / 2.0)  # Approximate conversion
                similarity = max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
                
                metadata = metadatas[i] if i < len(metadatas) else {}
                filename = metadata.get("filename", "Unknown")
                
                # Log each retrieved document
                logger.info(f"   [{i+1}] {filename} (similarity: {similarity:.3f}, distance: {distance:.3f})")
                logger.info(f"       Preview: {doc[:100]}..." if len(doc) > 100 else f"       Content: {doc}")
                
                # Filter by similarity threshold
                if similarity < similarity_threshold:
                    logger.info(f"       ⚠️  Filtered out (similarity {similarity:.3f} < threshold {similarity_threshold})")
                    continue
                
                # Estimate tokens for this document
                doc_tokens = len(doc) // 4  # Rough estimate
                
                # Check if adding this would exceed token limit
                if current_tokens + doc_tokens > max_context_tokens:
                    logger.info(f"       ⚠️  Skipped (would exceed token limit: {current_tokens + doc_tokens} > {max_context_tokens})")
                    break
                
                context_parts.append(f"[Source: {filename}]\n{doc}")
                current_tokens += doc_tokens
                included_count += 1
            
            logger.info(f"   ✅ Included {included_count} documents in context ({current_tokens} estimated tokens)")
            
            return "\n\n".join(context_parts)
        except MissingEnvironmentVariableError:
            return ""
        except Exception:
            return ""
    
    def build_system_prompt(self, collection_name: Optional[str] = None) -> str:
        """Build system prompt for the AI assistant."""
        return SYSTEM_PROMPT
    
    def format_messages_for_openai(
        self, 
        messages: List[Dict[str, Any]], 
        collection_name: Optional[str] = None,
        user_query: Optional[str] = None,
        rag_n_results: int = 3,
        rag_similarity_threshold: float = 0.0,
        rag_max_context_tokens: int = 2000
    ) -> List[Dict[str, str]]:
        """
        Format messages for OpenAI API with the structure:
        1) System prompt (only in first message)
        2) User prompt (with retrieved documents if applicable)
        3) Conversation history (assistant messages)
        """
        formatted = []
        
        # Check if this is the first message (no assistant responses yet)
        has_assistant_messages = any(msg.get("role") == "assistant" for msg in messages)
        is_first_message = not has_assistant_messages
        
        # 1) Add system prompt only for the first message
        if is_first_message:
            system_prompt = self.build_system_prompt(collection_name)
            formatted.append({"role": "system", "content": system_prompt})
        
        # 2) Get RAG context if applicable
        rag_context = ""
        if collection_name and user_query:
            rag_context = self.get_rag_context(
                collection_name, 
                user_query,
                n_results=rag_n_results,
                similarity_threshold=rag_similarity_threshold,
                max_context_tokens=rag_max_context_tokens
            )
            if not rag_context:
                logger.info("⚠️  No RAG context retrieved")
        
        # 3) Format messages - combine user query with retrieved documents
        # Limit context window to last N messages
        recent_messages = messages[-self.max_context_messages:] if len(messages) > self.max_context_messages else messages
        
        # Process messages to format them correctly
        for msg in recent_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                # For the last user message, append RAG context if available
                if msg == recent_messages[-1] and rag_context:
                    # This is the most recent user message - add retrieved documents
                    user_content = content
                    if rag_context:
                        user_content += f"\n\n========================\nRETRIEVED DOCUMENTS:\n========================\n\n{rag_context}"
                    formatted.append({"role": "user", "content": user_content})
                else:
                    # Other user messages in history
                    formatted.append({"role": "user", "content": content})
            elif role == "assistant":
                formatted.append({"role": "assistant", "content": content})
        
        # Log what's being sent to OpenAI API
        logger.info("=" * 80)
        logger.info("📤 Sending to OpenAI API:")
        if is_first_message:
            logger.info("   (First message - system prompt included)")
        else:
            logger.info("   (Continuing conversation - system prompt omitted)")
        logger.info("-" * 80)
        for msg in formatted:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                logger.info(f"1) SYSTEM PROMPT ({len(content)} chars):\n{content[:500]}..." if len(content) > 500 else f"1) SYSTEM PROMPT ({len(content)} chars):\n{content}")
            elif role == "user":
                # Show structure for user messages
                if "\n\n========================\nRETRIEVED DOCUMENTS:" in content:
                    parts = content.split("\n\n========================\nRETRIEVED DOCUMENTS:")
                    user_part = parts[0]
                    docs_part = parts[1] if len(parts) > 1 else ""
                    logger.info(f"{'2' if is_first_message else '1'}) USER PROMPT:\n{user_part}")
                    logger.info(f"{'3' if is_first_message else '2'}) RETRIEVED DOCUMENTS:\n{docs_part[:500]}..." if len(docs_part) > 500 else f"{'3' if is_first_message else '2'}) RETRIEVED DOCUMENTS:\n{docs_part}")
                else:
                    logger.info(f"{'2' if is_first_message else '1'}) USER PROMPT:\n{content[:200]}..." if len(content) > 200 else f"{'2' if is_first_message else '1'}) USER PROMPT:\n{content}")
            else:
                logger.info(f"{role.upper()}: {content[:200]}..." if len(content) > 200 else f"{role.upper()}: {content}")
        logger.info("=" * 80)
        
        return formatted
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        stream: bool = False,
        rag_n_results: int = 3,
        rag_similarity_threshold: float = 0.0,
        rag_max_context_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate chat response using OpenAI API.
        
        Args:
            messages: List of previous messages with 'role' and 'content'
            collection_name: Optional ChromaDB collection for RAG
            stream: Whether to stream the response
            rag_n_results: Number of RAG results to retrieve (default: 3)
            rag_similarity_threshold: Minimum similarity for RAG results (default: 0.0)
            rag_max_context_tokens: Maximum tokens for RAG context (default: 2000)
        
        Returns:
            Dict with 'content', 'tokens_used', and 'model'
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Get the last user message for RAG context
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content")
                break
        
        # Format messages with RAG context
        formatted_messages = self.format_messages_for_openai(
            messages, 
            collection_name=collection_name,
            user_query=last_user_message,
            rag_n_results=rag_n_results,
            rag_similarity_threshold=rag_similarity_threshold,
            rag_max_context_tokens=rag_max_context_tokens
        )
        
        try:
            if stream:
                # For streaming, we'll return an iterator
                # For now, we'll implement non-streaming
                raise NotImplementedError("Streaming not yet implemented")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model": self.model
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, "client") and hasattr(self.client, "_client"):
            self.client._client.close()

