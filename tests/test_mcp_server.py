#!/usr/bin/env python3
"""Test script to interact with the MCP server."""

import asyncio
import json
import subprocess


async def test_mcp_server():
    """Test the MCP server functionality."""
    print("Starting MCP server test...")

    # Start the MCP server as a subprocess
    server_process = subprocess.Popen(
        ["uv", "run", "python", "-m", "mcp_mitm_mem0.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Test server initialization
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print("Sending initialize request...")
        server_process.stdin.write(json.dumps(init_request) + "\n")
        server_process.stdin.flush()

        # Read response
        response_line = server_process.stdout.readline()
        if response_line:
            print(f"Initialize response: {response_line.strip()}")

        # Send initialized notification
        initialized_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        print("Sending initialized notification...")
        server_process.stdin.write(json.dumps(initialized_notification) + "\n")
        server_process.stdin.flush()

        # Wait a bit for the server to process
        await asyncio.sleep(0.1)

        # Test tools list
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        print("Sending tools/list request...")
        server_process.stdin.write(json.dumps(tools_request) + "\n")
        server_process.stdin.flush()

        response_line = server_process.stdout.readline()
        if response_line:
            print(f"Tools list response: {response_line.strip()}")

        # Test memory operations
        remember_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "remember",
                "arguments": {"user_id": "test_user", "messages": [{"role": "user", "content": "Hello, I like pizza"}]},
            },
        }

        print("Testing remember function...")
        server_process.stdin.write(json.dumps(remember_request) + "\n")
        server_process.stdin.flush()

        response_line = server_process.stdout.readline()
        if response_line:
            print(f"Remember response: {response_line.strip()}")

        # Test search
        search_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "search_memories", "arguments": {"user_id": "test_user", "query": "pizza"}},
        }

        print("Testing search_memories function...")
        server_process.stdin.write(json.dumps(search_request) + "\n")
        server_process.stdin.flush()

        response_line = server_process.stdout.readline()
        if response_line:
            print(f"Search response: {response_line.strip()}")

    except Exception as e:
        print(f"Error during testing: {e}")

    finally:
        # Clean up
        print("Terminating server...")
        server_process.terminate()
        server_process.wait(timeout=5)

        # Read any remaining stderr
        stderr_output = server_process.stderr.read()
        if stderr_output:
            print(f"Server stderr: {stderr_output}")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
