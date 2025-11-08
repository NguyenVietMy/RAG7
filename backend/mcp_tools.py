"""
MCP Tools Implementation

Defines and implements all MCP tools (actions AI can take).
"""
import logging
from typing import Any, Dict, List, Optional

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
from rag_config import get_rag_config, upsert_rag_config
from chat_service import ChatService

logger = logging.getLogger(__name__)


class MCPTools:
    """Manages all MCP tools."""
    
    def __init__(self):
        self.chat_service = ChatService()
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define all available tools."""
        return [
            {
                "name": "list_collections",
                "description": "List all ChromaDB collections with metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_collection_info",
                "description": "Get collection metadata and stats",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the collection"
                        }
                    },
                    "required": ["collection_name"]
                }
            },
            {
                "name": "query_collection",
                "description": "Search a collection with RAG (text query → embeddings → results)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the collection"
                        },
                        "query": {
                            "type": "string",
                            "description": "Text query to search for"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 3
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Minimum similarity threshold",
                            "default": 0.0
                        },
                        "include_summaries": {
                            "type": "boolean",
                            "description": "Include document summaries in results",
                            "default": False
                        }
                    },
                    "required": ["collection_name", "query"]
                }
            },
            {
                "name": "rag_chat",
                "description": "Chat with RAG context from a collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the collection"
                        },
                        "messages": {
                            "type": "array",
                            "description": "Chat messages",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                    "content": {"type": "string"}
                                }
                            }
                        },
                        "rag_n_results": {
                            "type": "integer",
                            "description": "Number of RAG results to include",
                            "default": 3
                        }
                    },
                    "required": ["collection_name", "messages"]
                }
            },
            {
                "name": "get_rag_config",
                "description": "Get current RAG settings",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "update_rag_config",
                "description": "Update RAG parameters (n_results, threshold, max_tokens)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rag_n_results": {
                            "type": "integer",
                            "description": "Number of results to return"
                        },
                        "rag_similarity_threshold": {
                            "type": "number",
                            "description": "Similarity threshold"
                        },
                        "rag_max_context_tokens": {
                            "type": "integer",
                            "description": "Maximum context tokens"
                        }
                    }
                }
            }
        ]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of all tools."""
        return self._tools
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by name with arguments."""
        if tool_name == "list_collections":
            return self._list_collections()
        elif tool_name == "get_collection_info":
            return self._get_collection_info(arguments.get("collection_name"))
        elif tool_name == "query_collection":
            return self._query_collection(
                arguments.get("collection_name"),
                arguments.get("query"),
                arguments.get("n_results", 3),
                arguments.get("similarity_threshold", 0.0),
                arguments.get("include_summaries", False)
            )
        elif tool_name == "rag_chat":
            return self._rag_chat(
                arguments.get("collection_name"),
                arguments.get("messages", []),
                arguments.get("rag_n_results", 3)
            )
        elif tool_name == "get_rag_config":
            return self._get_rag_config()
        elif tool_name == "update_rag_config":
            return self._update_rag_config(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _list_collections(self) -> Dict[str, Any]:
        """List all ChromaDB collections."""
        try:
            client = get_chroma_client()
            collections = client.list_collections()
            
            result = {
                "collections": [],
                "total": len(collections)
            }
            
            for collection in collections:
                count = collection.count()
                result["collections"].append({
                    "name": collection.name,
                    "count": count,
                    "metadata": collection.metadata or {}
                })
            
            return result
        
        except MissingEnvironmentVariableError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection metadata and stats."""
        try:
            client = get_chroma_client()
            collection = client.get_collection(collection_name)
            count = collection.count()
            
            return {
                "name": collection.name,
                "count": count,
                "metadata": collection.metadata or {}
            }
        
        except Exception as e:
            logger.error(f"Error getting collection info: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _query_collection(
        self,
        collection_name: str,
        query: str,
        n_results: int = 3,
        similarity_threshold: float = 0.0,
        include_summaries: bool = False
    ) -> Dict[str, Any]:
        """Query a collection with RAG."""
        try:
            client = get_chroma_client()
            collection = client.get_collection(collection_name)
            
            # Get RAG config for embedding model
            rag_config = get_rag_config() or {}
            
            # Generate query embedding
            from embeddings import embed_texts
            query_embedding = embed_texts([query])[0]
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"$and": []}  # Can add filters here
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                document = results["documents"][0][i]
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else None
                
                # Convert distance to similarity (1 - distance for cosine similarity)
                similarity = 1.0 - distance if distance is not None else None
                
                result_item = {
                    "document": document,
                    "metadata": metadata,
                    "similarity": similarity
                }
                
                # TODO: Add document summary if include_summaries is True
                # This will be implemented when document_summarizer.py is ready
                
                formatted_results.append(result_item)
            
            return {
                "results": formatted_results,
                "query": query,
                "n_results": len(formatted_results)
            }
        
        except Exception as e:
            logger.error(f"Error querying collection: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _rag_chat(
        self,
        collection_name: str,
        messages: List[Dict[str, str]],
        rag_n_results: int = 3
    ) -> Dict[str, Any]:
        """Chat with RAG context."""
        try:
            # Get RAG config for similarity threshold
            rag_config = get_rag_config() or {}
            similarity_threshold = rag_config.get("rag_similarity_threshold", 0.0)
            max_context_tokens = rag_config.get("rag_max_context_tokens", 2000)
            
            # Get chat response with RAG
            response = self.chat_service.chat(
                messages=messages,
                collection_name=collection_name,
                rag_n_results=rag_n_results,
                rag_similarity_threshold=similarity_threshold,
                rag_max_context_tokens=max_context_tokens
            )
            
            # Extract citations from filenames in RAG context (if available)
            # TODO: Enhance to extract actual citations from retrieved documents
            citations = []
            
            return {
                "content": response.get("content", ""),
                "citations": citations,
                "tokens_used": response.get("tokens_used", 0),
                "model": response.get("model", "gpt-4o-mini")
            }
        
        except Exception as e:
            logger.error(f"Error in RAG chat: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _get_rag_config(self) -> Dict[str, Any]:
        """Get current RAG configuration."""
        config = get_rag_config()
        if config:
            return config
        else:
            return {
                "rag_n_results": 3,
                "rag_similarity_threshold": 0.0,
                "rag_max_context_tokens": 2000,
                "chat_model": "gpt-4o-mini"
            }
    
    def _update_rag_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update RAG configuration."""
        success = upsert_rag_config(config)
        if success:
            return {"success": True, "config": get_rag_config()}
        else:
            return {"success": False, "error": "Failed to update config"}

