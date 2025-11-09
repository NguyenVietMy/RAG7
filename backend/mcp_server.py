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


# Register tools using FastMCP decorators with explicit names
@mcp.tool(name="list_collections")
def list_collections() -> dict:
    """List all ChromaDB collections with metadata."""
    return tools_manager._list_collections()


@mcp.tool(name="get_collection_info")
def get_collection_info(collection_name: str) -> dict:
    """Get collection metadata and stats."""
    return tools_manager._get_collection_info(collection_name)


@mcp.tool(name="query_collection")
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


@mcp.tool(name="rag_chat")
def rag_chat(
    collection_name: str,
    messages: list,
    rag_n_results: int = 3
) -> dict:
    """Chat with RAG context from a collection."""
    return tools_manager._rag_chat(collection_name, messages, rag_n_results)


@mcp.tool(name="get_rag_config")
def get_rag_config() -> dict:
    """Get current RAG settings."""
    return tools_manager._get_rag_config()


@mcp.tool(name="update_rag_config")
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


@mcp.tool(name="summarize_document")
def summarize_document(
    collection_name: str,
    filename: str,
    chunks_per_batch: int = 25
) -> dict:
    """Generate hierarchical summary of a document using efficient batch processing."""
    return tools_manager._summarize_document(collection_name, filename, chunks_per_batch)


@mcp.tool(name="get_document_summary")
def get_document_summary(collection_name: str, filename: str) -> dict:
    """Retrieve stored summary for a document from PostgreSQL."""
    return tools_manager._get_document_summary(collection_name, filename)


@mcp.tool(name="scrape_web_documentation")
def scrape_web_documentation(
    url: str,
    collection_name: str,
    strategy: str = "auto",
    max_depth: int = 2,
    max_concurrent: int = 3,
    chunk_size: int = 5000
) -> dict:
    """Scrape web documentation using Crawl4AI with three intelligent strategies.
    
    Defaults are optimized to prevent resource exhaustion:
    - max_depth: 2 (reduced from 3)
    - max_concurrent: 3 (reduced from 10)
    - Automatic timeout: 2 minutes
    - Max pages: 150 for recursive, 100 for sitemap
    """
    return tools_manager._scrape_web_documentation(
        url, collection_name, strategy, max_depth, max_concurrent, chunk_size
    )


@mcp.tool(name="scrape_github_repo")
def scrape_github_repo(
    repo_url: str,
    collection_name: str,
    include_patterns: list = None,
    exclude_patterns: list = None,
    max_file_size_kb: int = 100,
    chunk_size: int = 5000,
    include_readme: bool = True,
    include_code: bool = True
) -> dict:
    """Scrape and ingest GitHub repository (code, READMEs, docs) into ChromaDB.
    
    Clones the repository, extracts code and documentation files, chunks them
    with context, generates embeddings, and stores in ChromaDB.
    """
    return tools_manager._scrape_github_repo(
        repo_url,
        collection_name,
        include_patterns or [],
        exclude_patterns or [],
        max_file_size_kb,
        chunk_size,
        include_readme,
        include_code
    )


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


@mcp.resource("document-summary://{collection}/{filename}")
def get_document_summary_resource(collection: str, filename: str) -> str:
    """Document summary from PostgreSQL."""
    import json
    result = resources_manager._read_document_summary_resource(collection, filename)
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
    # Explicitly use stdio transport for MCP protocol
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
