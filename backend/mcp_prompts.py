"""
MCP Prompts Implementation

Defines and implements all MCP prompt templates.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MCPPrompts:
    """Manages all MCP prompts."""
    
    def __init__(self):
        self._prompts = self._define_prompts()
    
    def _define_prompts(self) -> List[Dict[str, Any]]:
        """Define all available prompts."""
        return [
            {
                "name": "rag-query-template",
                "description": "Template for querying collections with RAG",
                "arguments": [
                    {
                        "name": "collection_name",
                        "description": "Name of the collection to query",
                        "required": True
                    },
                    {
                        "name": "query",
                        "description": "The search query",
                        "required": True
                    }
                ]
            },
            {
                "name": "chat-context-template",
                "description": "Template for RAG chat context",
                "arguments": [
                    {
                        "name": "collection_name",
                        "description": "Name of the collection",
                        "required": True
                    },
                    {
                        "name": "user_message",
                        "description": "The user's message",
                        "required": True
                    }
                ]
            }
        ]
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """Return list of all prompts."""
        return self._prompts
    
    def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        """Get a prompt by name with arguments."""
        if prompt_name == "rag-query-template":
            return self._get_rag_query_template(
                arguments.get("collection_name"),
                arguments.get("query")
            )
        elif prompt_name == "chat-context-template":
            return self._get_chat_context_template(
                arguments.get("collection_name"),
                arguments.get("user_message")
            )
        else:
            raise ValueError(f"Unknown prompt: {prompt_name}")
    
    def _get_rag_query_template(self, collection_name: str, query: str) -> str:
        """Generate RAG query template."""
        return f"""You are querying the knowledge base collection "{collection_name}".

Query: {query}

Use the query_collection tool to search for relevant information in this collection.
The tool will return relevant chunks from documents that match your query.

After getting results, provide a comprehensive answer based on the retrieved information."""
    
    def _get_chat_context_template(self, collection_name: str, user_message: str) -> str:
        """Generate chat context template."""
        return f"""You are having a conversation about the knowledge base collection "{collection_name}".

User message: {user_message}

Use the rag_chat tool to get a response that includes relevant context from the collection.
The tool will automatically retrieve relevant chunks and generate a contextual response."""

