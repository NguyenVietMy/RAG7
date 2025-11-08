"""
MCP Resources Implementation

Defines and implements all MCP resources (data AI can read).
"""
import logging
from typing import Any, Dict, List, Optional

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
from rag_config import get_rag_config

logger = logging.getLogger(__name__)


class MCPResources:
    """Manages all MCP resources."""
    
    def __init__(self):
        self._resources = self._define_resources()
    
    def _define_resources(self) -> List[Dict[str, Any]]:
        """Define all available resources."""
        return [
            {
                "uri": "collection://*",
                "name": "Collection Metadata",
                "description": "Collection metadata and file list",
                "mimeType": "application/json"
            },
            {
                "uri": "rag-config://current",
                "name": "RAG Configuration",
                "description": "Current RAG configuration settings",
                "mimeType": "application/json"
            },
            {
                "uri": "chroma-health://status",
                "name": "ChromaDB Health",
                "description": "ChromaDB connection status",
                "mimeType": "application/json"
            }
        ]
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """Return list of all resources."""
        return self._resources
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        if uri.startswith("collection://"):
            collection_name = uri.replace("collection://", "")
            return self._read_collection_resource(collection_name)
        elif uri == "rag-config://current":
            return self._read_rag_config_resource()
        elif uri == "chroma-health://status":
            return self._read_chroma_health_resource()
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    def _read_collection_resource(self, collection_name: str) -> Dict[str, Any]:
        """Read collection metadata resource."""
        try:
            client = get_chroma_client()
            collection = client.get_collection(collection_name)
            count = collection.count()
            
            # Get files from collection (sample some records to extract unique filenames)
            # Note: This is a simplified version - full implementation would query all records
            files = []
            try:
                # Get a sample of records to extract file metadata
                sample = collection.get(limit=1000)
                if sample and sample.get("metadatas"):
                    seen_files = set()
                    for metadata in sample["metadatas"]:
                        filename = metadata.get("filename")
                        if filename and filename not in seen_files:
                            seen_files.add(filename)
                            # Count records for this file
                            file_records = collection.get(
                                where={"filename": filename}
                            )
                            file_count = len(file_records["ids"]) if file_records["ids"] else 0
                            files.append({
                                "filename": filename,
                                "record_count": file_count,
                                "file_type": metadata.get("file_type", "unknown")
                            })
            except Exception as e:
                logger.warning(f"Error extracting file list: {e}")
            
            return {
                "name": collection.name,
                "count": count,
                "metadata": collection.metadata or {},
                "files": files
            }
        
        except Exception as e:
            logger.error(f"Error reading collection resource: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _read_rag_config_resource(self) -> Dict[str, Any]:
        """Read RAG configuration resource."""
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
    
    def _read_chroma_health_resource(self) -> Dict[str, Any]:
        """Read ChromaDB health status."""
        try:
            client = get_chroma_client()
            collections = client.list_collections()
            return {
                "status": "ok",
                "collections_count": len(collections),
                "connected": True
            }
        except MissingEnvironmentVariableError as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }
        except Exception as e:
            logger.error(f"Error checking ChromaDB health: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }

