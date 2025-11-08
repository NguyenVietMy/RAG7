"""
Simple health check for MCP server

Quick check to see if the server can start and basic imports work.
"""
import sys
from pathlib import Path

def check_imports():
    """Check if all required modules can be imported."""
    print("Checking imports...")
    
    try:
        from fastmcp import FastMCP
        print("✅ FastMCP imported successfully")
    except ImportError as e:
        print(f"❌ FastMCP import failed: {e}")
        print("   Install with: pip install fastmcp")
        return False
    
    try:
        from mcp_tools import MCPTools
        print("✅ mcp_tools imported successfully")
    except ImportError as e:
        print(f"❌ mcp_tools import failed: {e}")
        return False
    
    try:
        from mcp_resources import MCPResources
        print("✅ mcp_resources imported successfully")
    except ImportError as e:
        print(f"❌ mcp_resources import failed: {e}")
        return False
    
    try:
        from mcp_prompts import MCPPrompts
        print("✅ mcp_prompts imported successfully")
    except ImportError as e:
        print(f"❌ mcp_prompts import failed: {e}")
        return False
    
    try:
        # Try importing the server module (but don't run it)
        import mcp_server
        print("✅ mcp_server module imported successfully")
    except Exception as e:
        print(f"❌ mcp_server import failed: {e}")
        return False
    
    return True


def check_dependencies():
    """Check if backend dependencies are available."""
    print("\nChecking backend dependencies...")
    
    try:
        from chroma_client import get_chroma_client
        print("✅ chroma_client available")
    except Exception as e:
        print(f"⚠️  chroma_client issue: {e}")
        print("   (This is OK if ChromaDB isn't running yet)")
    
    try:
        from rag_config import get_rag_config
        print("✅ rag_config available")
    except Exception as e:
        print(f"⚠️  rag_config issue: {e}")
        print("   (This is OK if PostgreSQL isn't configured)")
    
    try:
        from chat_service import ChatService
        print("✅ chat_service available")
    except Exception as e:
        print(f"⚠️  chat_service issue: {e}")
        return False
    
    try:
        from embeddings import embed_texts
        print("✅ embeddings available")
    except Exception as e:
        print(f"⚠️  embeddings issue: {e}")
        return False
    
    return True


def main():
    """Run health check."""
    print("=" * 60)
    print("MCP Server Health Check")
    print("=" * 60)
    print()
    
    # Check imports
    if not check_imports():
        print("\n❌ Health check failed: Import errors")
        return False
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Health check completed with warnings")
        print("   Server may work, but some features might not be available")
        return True
    
    print("\n" + "=" * 60)
    print("✅ Health check passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python test_mcp_server.py (for full test)")
    print("2. Run: python mcp_server.py (to start server)")
    print("3. Configure in Cursor/Claude Desktop")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

