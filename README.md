# MCP MITM Mem0

A simplified memory service for Claude that intercepts conversations via MITM proxy and provides memory access through MCP.

## Overview

This project provides three core components:

1. **MITM Addon** - Intercepts Claude API conversations and stores them in Mem0
2. **MCP Server** - Provides tools for Claude to query and manage memories
3. **Reflection Agent** - Analyzes conversations to identify patterns and provide insights

## Features

- 🎯 **Simple & Focused** - Just memory capture and retrieval, no enterprise complexity
- 🌐 **Mem0 SaaS** - Uses Mem0's cloud service, no local infrastructure needed  
- 🔍 **Memory Search** - Natural language search across conversation history
- 📊 **Reflection Analysis** - Identifies patterns and suggests improvements
- 🛠️ **MCP Tools** - Direct integration with Claude via MCP protocol
- 📚 **Memory Resources** - Browse memories as MCP resources

## Setup

### 1. Get a Mem0 API Key

Sign up at [https://app.mem0.ai](https://app.mem0.ai) and get your API key.

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your MEM0_API_KEY
```

### 3. Install Dependencies

```bash
uv sync
```

## Usage

### Running the MITM Proxy

```bash
# Start mitmproxy with the memory addon
mitmdump -s memory_addon.py
```

Configure your Claude client to use the proxy (typically `localhost:8080`).

### Running the MCP Server

```bash
# Start the MCP server
uv run mcp-mitm-mem0
```

### Configure Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "memory-service": {
      "command": "uv",
      "args": ["run", "mcp-mitm-mem0"],
      "cwd": "/path/to/mcp-mitm-mem0"
    }
  }
}
```

## MCP Tools

- `search_memories(query, user_id?, limit?)` - Search memories using natural language
- `list_memories(user_id?)` - List all memories for a user
- `add_memory(messages, user_id?, metadata?)` - Manually add memories
- `delete_memory(memory_id)` - Delete a specific memory
- `analyze_conversations(user_id?, limit?)` - Analyze patterns in recent conversations
- `suggest_next_actions(user_id?)` - Get suggestions based on conversation history

## MCP Resources

- `memory://{user_id}` - Browse all memories for a specific user
- `memory://recent` - View the 10 most recent memories

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Client  │────▶│   MITM Proxy    │────▶│  Anthropic API  │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │   Mem0 SaaS   │
                         └───────▲───────┘
                                 │
┌─────────────────┐     ┌───────┴───────┐
│      Claude     │────▶│  MCP Server   │
│    (via MCP)    │     │ + Reflection  │
└─────────────────┘     └───────────────┘
```

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Configuration

All configuration is done via environment variables:

- `MEM0_API_KEY` - Your Mem0 SaaS API key (required)
- `DEBUG` - Enable debug logging (default: false)
- `DEFAULT_USER_ID` - Default user ID for memories (default: "default_user")
- `MITM_HOST` - MITM proxy host (default: "localhost")
- `MITM_PORT` - MITM proxy port (default: 8080)
- `MCP_NAME` - MCP server name (default: "memory-service")

## License

MIT