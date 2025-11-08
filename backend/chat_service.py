import os
import logging
from typing import List, Optional, Dict, Any
from openai import OpenAI
import httpx

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
from embeddings import embed_texts

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY must be set")
        
        http_client = httpx.Client(timeout=httpx.Timeout(60.0))
        self.client = OpenAI(api_key=api_key, http_client=http_client)
        self.model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
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
    
    def get_rag_context(self, collection_name: str, query: str, n_results: int = 3) -> str:
        """Get relevant context from ChromaDB for RAG."""
        try:
            logger.info(f"🔍 RAG Query: collection='{collection_name}', query='{query[:50]}...', n_results={n_results}")
            client = get_chroma_client()
            collection = client.get_collection(name=collection_name)
            
            # Try to get a sample embedding to determine the expected dimension
            # First, try with the default embedding model (text-embedding-3-small, 384 dims)
            query_embeddings = embed_texts([query])
            
            if not query_embeddings or len(query_embeddings) == 0:
                logger.warning("❌ Failed to generate embeddings for query")
                return ""
            
            embedding_dim = len(query_embeddings[0])
            logger.info(f"📊 Generated embeddings with dimension: {embedding_dim}")
            
            # If the default embedding doesn't match, try text-embedding-ada-002 (1536 dims)
            # This handles collections created with older embedding models
            try:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as dim_error:
                if "dimension" in str(dim_error).lower():
                    logger.info(f"⚠️  Dimension mismatch ({embedding_dim} dims), trying text-embedding-ada-002 (1536 dims)")
                    # Try with text-embedding-ada-002 which has 1536 dimensions
                    try:
                        query_embeddings = embed_texts([query], model="text-embedding-ada-002")
                        if query_embeddings and len(query_embeddings) > 0:
                            results = collection.query(
                                query_embeddings=query_embeddings,
                                n_results=n_results,
                                include=["documents", "metadatas", "distances"]
                            )
                        else:
                            logger.error("❌ Failed to generate embeddings with text-embedding-ada-002")
                            return ""
                    except Exception as ada_error:
                        logger.error(f"❌ Error querying with text-embedding-ada-002: {str(ada_error)}")
                        return ""
                else:
                    raise
            
            if not results or not results.get("documents") or not results["documents"][0]:
                logger.warning(f"⚠️  No documents found in collection '{collection_name}' for query")
                return ""
            
            # Format context from retrieved documents
            context_parts = []
            documents = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            
            logger.info(f"✅ RAG Success: Found {len(documents)} documents")
            
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                filename = metadata.get("filename", "Unknown")
                distance = distances[i] if i < len(distances) else None
                distance_str = f" (distance: {distance:.3f})" if distance is not None else ""
                logger.info(f"  📄 Document {i+1}: {filename}{distance_str}")
                context_parts.append(f"[Source: {filename}]\n{doc}")
            
            context = "\n\n".join(context_parts)
            logger.info(f"📝 RAG Context length: {len(context)} characters")
            return context
        except MissingEnvironmentVariableError:
            logger.warning("⚠️  ChromaDB not configured, skipping RAG")
            return ""
        except Exception as e:
            logger.error(f"❌ Error getting RAG context: {str(e)}")
            return ""
    
    def build_system_prompt(self, collection_name: Optional[str] = None) -> str:
        """Build system prompt, optionally with RAG context."""
        base_prompt = """You are a helpful AI assistant. Provide accurate, helpful, and concise responses."""
        
        if collection_name:
            base_prompt += f"\n\nYou have access to a knowledge base (collection: {collection_name}). Use the provided context to answer questions accurately. If the context doesn't contain relevant information, say so and provide a general answer based on your knowledge."
        
        return base_prompt
    
    def format_messages_for_openai(
        self, 
        messages: List[Dict[str, Any]], 
        collection_name: Optional[str] = None,
        user_query: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Format messages for OpenAI API, including RAG context if applicable."""
        formatted = []
        
        # Add system prompt
        system_prompt = self.build_system_prompt(collection_name)
        
        # If RAG is enabled and we have a user query, add context
        if collection_name and user_query:
            rag_context = self.get_rag_context(collection_name, user_query)
            if rag_context:
                logger.info(f"✅ RAG context added to system prompt ({len(rag_context)} chars)")
                system_prompt += f"\n\nRelevant context from knowledge base:\n\n{rag_context}"
            else:
                logger.warning(f"⚠️  No RAG context retrieved for collection '{collection_name}'")
        
        formatted.append({"role": "system", "content": system_prompt})
        
        # Limit context window to last N messages
        recent_messages = messages[-self.max_context_messages:] if len(messages) > self.max_context_messages else messages
        
        # Format user/assistant messages
        for msg in recent_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                formatted.append({"role": role, "content": content})
        
        return formatted
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate chat response using OpenAI API.
        
        Args:
            messages: List of previous messages with 'role' and 'content'
            collection_name: Optional ChromaDB collection for RAG
            stream: Whether to stream the response
        
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
            user_query=last_user_message
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

