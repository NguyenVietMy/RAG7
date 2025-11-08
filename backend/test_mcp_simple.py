"""
Simple test for MCP server - tests if server can start and basic functionality works.
"""
import subprocess
import sys
import time
from pathlib import Path


def test_server_starts():
    """Test that the server can start without errors."""
    print("Testing if server can start...")
    
    server_path = Path(__file__).parent / "mcp_server.py"
    
    try:
        # Start server with a timeout
        server = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment
        time.sleep(1)
        
        # Check if it's still running
        if server.poll() is None:
            print("✅ Server started and is running")
            server.terminate()
            server.wait(timeout=2)
            return True
        else:
            # Server exited
            stderr = server.stderr.read()
            stdout = server.stdout.read()
            print("❌ Server exited immediately")
            print(f"STDERR: {stderr}")
            print(f"STDOUT: {stdout}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting imports...")
    
    try:
        from fastmcp import FastMCP
        print("✅ FastMCP imported")
    except ImportError as e:
        print(f"❌ FastMCP import failed: {e}")
        return False
    
    try:
        import mcp_server
        print("✅ mcp_server imported")
    except Exception as e:
        print(f"❌ mcp_server import failed: {e}")
        return False
    
    try:
        from mcp_tools import MCPTools
        tools = MCPTools()
        print("✅ MCPTools created")
        
        # Test a simple method
        result = tools._list_collections()
        print(f"✅ list_collections method works (returned: {type(result).__name__})")
    except Exception as e:
        print(f"⚠️  MCPTools test failed: {e}")
        print("   (This might be OK if ChromaDB isn't running)")
    
    return True


def main():
    """Run simple tests."""
    print("=" * 60)
    print("Simple MCP Server Test")
    print("=" * 60)
    print()
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test server starts
    if not test_server_starts():
        print("\n❌ Server start test failed")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Basic tests passed!")
    print("=" * 60)
    print("\nThe server appears to be set up correctly.")
    print("To test full functionality:")
    print("1. Make sure ChromaDB is running")
    print("2. Make sure PostgreSQL is running (for RAG config)")
    print("3. Configure the server in Cursor/Claude Desktop")
    print("4. Try using it in chat!")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

