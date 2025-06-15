# mcp-mitm-mem0

## Goals

- FastAPI-based MCP server with tools:
  - `search_memories`: Search session memories using Mem0
  - `list_memories`: List all session memories
  - `remember`: Add a session memory (run_id)
  - `forget`: Delete a specific memory by id or all session memories
- mitmproxy addon to capture chat JSON payloads and store conversations in Mem0

## Setup

1. Install dependencies:

   ```sh
   pip install mem0ai fastapi uvicorn mitmproxy
   ```

2. Set your `OPENAI_API_KEY` and (optionally) `MEM0_API_KEY` as environment variables.
3. Run the FastAPI server:

   ```sh
   uvicorn main:app --reload
   ```

4. Use mitmproxy with the addon:

   ```sh
   mitmproxy -s mitm_mem0_addon.py
   ```
