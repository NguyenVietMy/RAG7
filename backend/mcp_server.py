"""
MCP (Model Context Protocol) Server using FastMCP

Implements an MCP server using FastMCP framework for AI assistants (Cursor, Claude Desktop).
"""
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastMCP
try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "FastMCP is required. Install it with: pip install fastmcp"
    )

# Import tool implementations
from mcp_tools import MCPTools
from mcp_resources import MCPResources
from mcp_prompts import MCPPrompts

# Initialize FastMCP server
mcp = FastMCP("DSS Knowledge Base MCP Server")

# Initialize tool/resource/prompt managers
tools_manager = MCPTools()
resources_manager = MCPResources()
prompts_manager = MCPPrompts()


# Register tools using FastMCP decorators
@mcp.tool()
def list_collections() -> dict:
    """List all ChromaDB collections with metadata."""
    return tools_manager._list_collections()


@mcp.tool()
def get_collection_info(collection_name: str) -> dict:
    """Get collection metadata and stats."""
    return tools_manager._get_collection_info(collection_name)


@mcp.tool()
def query_collection(
    collection_name: str,
    query: str,
    n_results: int = 3,
    similarity_threshold: float = 0.0,
    include_summaries: bool = False
) -> dict:
    """Search a collection with RAG (text query → embeddings → results)."""
    return tools_manager._query_collection(
        collection_name, query, n_results, similarity_threshold, include_summaries
    )


@mcp.tool()
def rag_chat(
    collection_name: str,
    messages: list,
    rag_n_results: int = 3
) -> dict:
    """Chat with RAG context from a collection."""
    return tools_manager._rag_chat(collection_name, messages, rag_n_results)


@mcp.tool()
def get_rag_config() -> dict:
    """Get current RAG settings."""
    return tools_manager._get_rag_config()


@mcp.tool()
def update_rag_config(
    rag_n_results: int = None,
    rag_similarity_threshold: float = None,
    rag_max_context_tokens: int = None
) -> dict:
    """Update RAG parameters (n_results, threshold, max_tokens)."""
    config = {}
    if rag_n_results is not None:
        config["rag_n_results"] = rag_n_results
    if rag_similarity_threshold is not None:
        config["rag_similarity_threshold"] = rag_similarity_threshold
    if rag_max_context_tokens is not None:
        config["rag_max_context_tokens"] = rag_max_context_tokens
    
    return tools_manager._update_rag_config(config)


# Register resources
@mcp.resource("collection://{name}")
def get_collection_resource(name: str) -> str:
    """Collection metadata and file list."""
    import json
    result = resources_manager._read_collection_resource(name)
    return json.dumps(result, indent=2)


@mcp.resource("rag-config://current")
def get_rag_config_resource() -> str:
    """Current RAG configuration settings."""
    import json
    result = resources_manager._read_rag_config_resource()
    return json.dumps(result, indent=2)


@mcp.resource("chroma-health://status")
def get_chroma_health_resource() -> str:
    """ChromaDB connection status."""
    import json
    result = resources_manager._read_chroma_health_resource()
    return json.dumps(result, indent=2)


# Register prompts
@mcp.prompt()
def rag_query_template(collection_name: str, query: str) -> str:
    """Template for querying collections with RAG."""
    return prompts_manager._get_rag_query_template(collection_name, query)


@mcp.prompt()
def chat_context_template(collection_name: str, user_message: str) -> str:
    """Template for RAG chat context."""
    return prompts_manager._get_chat_context_template(collection_name, user_message)


def main():
    """Entry point for MCP server."""
    logger.info("Starting MCP server with FastMCP...")
    mcp.run()


if __name__ == "__main__":
    main()
