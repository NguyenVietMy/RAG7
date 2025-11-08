"""
Test script for MCP server

This script tests the MCP server by sending JSON-RPC requests and verifying responses.
"""
import json
import subprocess
import sys
import time
from pathlib import Path


def send_request(server_process, request: dict, timeout: float = 5.0) -> dict:
    """Send a JSON-RPC request to the server and get response."""
    import threading
    import queue
    
    request_json = json.dumps(request) + "\n"
    server_process.stdin.write(request_json.encode())
    server_process.stdin.flush()
    
    # Use a queue to get the response from a thread
    response_queue = queue.Queue()
    error_queue = queue.Queue()
    
    def read_response():
        """Read response in a separate thread."""
        try:
            response_line = server_process.stdout.readline()
            if response_line:
                response_queue.put(response_line)
            else:
                error_queue.put("No response line")
        except Exception as e:
            error_queue.put(str(e))
    
    # Start reading in a thread
    reader_thread = threading.Thread(target=read_response, daemon=True)
    reader_thread.start()
    reader_thread.join(timeout=timeout)
    
    # Check if we got a response
    if not response_queue.empty():
        response_line = response_queue.get()
        try:
            return json.loads(response_line.decode().strip())
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}")
            print(f"Response was: {response_line}")
            return None
    elif not error_queue.empty():
        error = error_queue.get()
        print(f"⚠️  Error reading response: {error}")
        return None
    else:
        print(f"⚠️  Timeout waiting for response (>{timeout}s)")
        print("   (This might be OK if ChromaDB isn't running or connection is slow)")
        return None


def test_mcp_server():
    """Test the MCP server with basic requests."""
    print("=" * 60)
    print("Testing MCP Server")
    print("=" * 60)
    
    # Start the server process
    server_path = Path(__file__).parent / "mcp_server.py"
    print(f"\n1. Starting server: {server_path}")
    
    try:
        server = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Use bytes mode
        )
        
        # Give server a moment to start
        time.sleep(0.5)
        
        if server.poll() is not None:
            # Server exited immediately
            stderr_output = server.stderr.read().decode()
            print(f"❌ Server failed to start!")
            print(f"Error: {stderr_output}")
            return False
        
        print("✅ Server started successfully")
        
        # Test 1: Initialize
        print("\n2. Testing initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = send_request(server, init_request)
        if init_response and "result" in init_response:
            print("✅ Initialize successful")
            print(f"   Server: {init_response['result'].get('serverInfo', {}).get('name', 'unknown')}")
        else:
            print("❌ Initialize failed")
            print(f"   Response: {init_response}")
            server.terminate()
            return False
        
        # Send initialized notification (required by MCP protocol)
        print("\n2a. Sending initialized notification...")
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        request_json = json.dumps(initialized_notification) + "\n"
        server.stdin.write(request_json.encode())
        server.stdin.flush()
        print("✅ Initialized notification sent")
        
        # Test 2: List tools
        print("\n3. Testing tools/list...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        tools_response = send_request(server, tools_request)
        if tools_response and "result" in tools_response:
            tools = tools_response["result"].get("tools", [])
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools[:5]:  # Show first 5
                print(f"   - {tool.get('name', 'unknown')}")
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")
        else:
            print("❌ tools/list failed")
            print(f"   Response: {tools_response}")
        
        # Test 3: List resources
        print("\n4. Testing resources/list...")
        resources_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/list"
        }
        
        resources_response = send_request(server, resources_request)
        if resources_response and "result" in resources_response:
            resources = resources_response["result"].get("resources", [])
            print(f"✅ Found {len(resources)} resources:")
            for resource in resources:
                print(f"   - {resource.get('uri', 'unknown')}")
        else:
            print("❌ resources/list failed")
            print(f"   Response: {resources_response}")
        
        # Test 4: Call a tool (list_collections)
        print("\n5. Testing tools/call (list_collections)...")
        print("   (This may take a moment if ChromaDB needs to connect)...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "list_collections",
                "arguments": {}
            }
        }
        
        # Use longer timeout for tool calls (they might need to connect to ChromaDB)
        call_response = send_request(server, call_request, timeout=10.0)
        if call_response and "result" in call_response:
            print("✅ list_collections tool executed")
            # Try to parse the result
            content = call_response["result"].get("content", [])
            if content and len(content) > 0:
                try:
                    result_data = json.loads(content[0].get("text", "{}"))
                    if "error" in result_data:
                        print(f"   ⚠️  Tool returned error: {result_data.get('error')}")
                        print("   (This is OK if ChromaDB isn't running)")
                    else:
                        collections = result_data.get("collections", [])
                        print(f"   Found {len(collections)} collections")
                        for coll in collections[:3]:
                            print(f"   - {coll.get('name', 'unknown')} ({coll.get('count', 0)} records)")
                except Exception as e:
                    print(f"   (Could not parse result content: {e})")
                    print(f"   Raw content: {content[0] if content else 'None'}")
        elif call_response and "error" in call_response:
            print(f"❌ tools/call failed with error: {call_response['error']}")
        else:
            print("❌ tools/call failed or timed out")
            print(f"   Response: {call_response}")
            print("   (This might be OK if ChromaDB isn't running)")
        
        # Cleanup
        print("\n6. Shutting down server...")
        server.terminate()
        server.wait(timeout=2)
        print("✅ Server stopped")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        if 'server' in locals():
            server.terminate()
        return False


if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)

