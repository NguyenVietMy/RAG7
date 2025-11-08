"""
MCP Tools Implementation

Defines and implements all MCP tools (actions AI can take).
"""
import logging
import time
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
            },
            {
                "name": "summarize_document",
                "description": "Generate hierarchical summary of a document using efficient batch processing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the collection"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to summarize"
                        },
                        "chunks_per_batch": {
                            "type": "integer",
                            "description": "Number of chunks per batch (default: 25)",
                            "default": 25
                        }
                    },
                    "required": ["collection_name", "filename"]
                }
            },
            {
                "name": "get_document_summary",
                "description": "Retrieve stored summary for a document from PostgreSQL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the collection"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name of the file"
                        }
                    },
                    "required": ["collection_name", "filename"]
                }
            },
            {
                "name": "scrape_web_documentation",
                "description": "Scrape web documentation using Crawl4AI with three intelligent strategies (sitemap, text file, recursive)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to scrape (can be sitemap, text file, or webpage)"
                        },
                        "collection_name": {
                            "type": "string",
                            "description": "Name of the ChromaDB collection to store scraped content"
                        },
                        "strategy": {
                            "type": "string",
                            "description": "Crawling strategy: 'auto', 'sitemap', 'text_file', or 'recursive'",
                            "enum": ["auto", "sitemap", "text_file", "recursive"],
                            "default": "auto"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum recursion depth for recursive strategy",
                            "default": 3
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "description": "Maximum concurrent browser sessions",
                            "default": 10
                        },
                        "chunk_size": {
                            "type": "integer",
                            "description": "Chunk size for markdown splitting",
                            "default": 5000
                        }
                    },
                    "required": ["url", "collection_name"]
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
        elif tool_name == "summarize_document":
            return self._summarize_document(
                arguments.get("collection_name"),
                arguments.get("filename"),
                arguments.get("chunks_per_batch", 25)
            )
        elif tool_name == "get_document_summary":
            return self._get_document_summary(
                arguments.get("collection_name"),
                arguments.get("filename")
            )
        elif tool_name == "scrape_web_documentation":
            return self._scrape_web_documentation(
                arguments.get("url"),
                arguments.get("collection_name"),
                arguments.get("strategy", "auto"),
                arguments.get("max_depth", 3),
                arguments.get("max_concurrent", 10),
                arguments.get("chunk_size", 5000)
            )
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
            # Only include where clause if we have actual filters
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            # Note: Can add where filters here if needed in the future
            results = collection.query(**query_kwargs)
            
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
                
                # Add document summary if include_summaries is True
                if include_summaries:
                    from document_summarizer import DocumentSummarizer
                    summarizer = DocumentSummarizer()
                    filename = metadata.get("filename")
                    if filename:
                        summary_data = summarizer.get_summary(collection_name, filename)
                        if summary_data:
                            result_item["document_summary"] = summary_data.get("summary")
                
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
    
    def _summarize_document(
        self,
        collection_name: str,
        filename: str,
        chunks_per_batch: int = 25
    ) -> Dict[str, Any]:
        """Generate hierarchical summary of a document."""
        from document_summarizer import DocumentSummarizer
        summarizer = DocumentSummarizer()
        return summarizer.summarize_document(collection_name, filename, chunks_per_batch)
    
    def _get_document_summary(
        self,
        collection_name: str,
        filename: str
    ) -> Dict[str, Any]:
        """Retrieve stored document summary."""
        from document_summarizer import DocumentSummarizer
        summarizer = DocumentSummarizer()
        summary = summarizer.get_summary(collection_name, filename)
        if summary:
            return summary
        else:
            return {"error": f"No summary found for {collection_name}/{filename}"}
    
    def _scrape_web_documentation(
        self,
        url: str,
        collection_name: str,
        strategy: str = "auto",
        max_depth: int = 3,
        max_concurrent: int = 10,
        chunk_size: int = 5000
    ) -> Dict[str, Any]:
        """Scrape web documentation and store in ChromaDB."""
        import asyncio
        from web_scraper import smart_crawl_url
        from chroma_client import get_chroma_client
        from urllib.parse import urlparse
        
        try:
            # Run the async crawl - handle nested event loops
            # Use a thread pool to run the async function in a separate event loop
            import concurrent.futures
            
            def run_async_in_thread():
                """Run async function in a new thread with its own event loop."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        smart_crawl_url(url, strategy, max_depth, max_concurrent, chunk_size)
                    )
                finally:
                    new_loop.close()
            
            # Execute in a separate thread to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_in_thread)
                crawl_result = future.result(timeout=300)  # 5 minute timeout
            
            if not crawl_result.get("success"):
                return crawl_result
            
            chunks = crawl_result.get("chunks", [])
            if not chunks:
                return {
                    "success": False,
                    "error": "No chunks generated from scraped content"
                }
            
            # Store chunks in ChromaDB
            client = get_chroma_client()
            collection = client.get_or_create_collection(name=collection_name)
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                # Generate unique ID from URL, chunk index, and global index
                # Use full URL hash to ensure uniqueness across different pages
                url_hash = abs(hash(chunk['url'])) % 1000000
                chunk_id = f"{urlparse(chunk['url']).netloc}_{chunk['chunk_index']}_{url_hash}_{i}"
                ids.append(chunk_id)
                documents.append(chunk['content'])
                embeddings.append(chunk.get('embedding', []))
                metadatas.append({
                    "filename": chunk['url'],  # Use URL as filename
                    "file_type": "web_scraped",
                    "chunk_index": chunk['chunk_index'],
                    "source_url": chunk['url'],
                    "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
            
            # Upsert to ChromaDB in batches
            CHROMADB_BATCH_SIZE = 1000
            total_chunks = len(ids)
            
            if total_chunks <= CHROMADB_BATCH_SIZE:
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            else:
                # Multiple batches
                total_batches = (total_chunks + CHROMADB_BATCH_SIZE - 1) // CHROMADB_BATCH_SIZE
                for i in range(0, total_chunks, CHROMADB_BATCH_SIZE):
                    batch_ids = ids[i:i + CHROMADB_BATCH_SIZE]
                    batch_embeddings = embeddings[i:i + CHROMADB_BATCH_SIZE]
                    batch_documents = documents[i:i + CHROMADB_BATCH_SIZE]
                    batch_metadatas = metadatas[i:i + CHROMADB_BATCH_SIZE]
                    batch_num = (i // CHROMADB_BATCH_SIZE) + 1
                    
                    collection.upsert(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        documents=batch_documents,
                        metadatas=batch_metadatas
                    )
                    logger.info(f"Upserted batch {batch_num}/{total_batches} ({len(batch_ids)} chunks)")
            
            return {
                "success": True,
                "crawl_type": crawl_result.get("crawl_type"),
                "pages_crawled": crawl_result.get("pages_crawled", 0),
                "chunks_created": len(chunks),
                "chunks_stored": total_chunks,
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Error scraping web documentation: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

