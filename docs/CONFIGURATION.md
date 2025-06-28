# MCP MITM Mem0 Configuration Guide

This project uses environment variables for all configuration. You can set these in a `.env` file or as system environment variables.

## Basic Configuration

### Required Variables

```bash
# LLM Provider - "openai" or "litellm"
MEM0_PROVIDER=openai

# Model name - depends on provider
MODEL_NAME=gpt-4o-mini

# API key - required for OpenAI
OPENAI_API_KEY=your_openai_api_key_here
```

### Optional Variables

```bash
# Authentication token (required in production)
AUTH_TOKEN=your_secure_token_here

# Server settings
SERVER_HOST=localhost
SERVER_PORT=8000

# Development settings
DEBUG=false
AUTH_DISABLED_FOR_DEV=false
```

## Configuration Examples

### 1. Simple OpenAI Setup

```bash
MEM0_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-...
AUTH_TOKEN=your_secure_token
```

### 2. OpenRouter Setup

```bash
MEM0_PROVIDER=litellm
MODEL_NAME=openrouter/anthropic/claude-3.5-sonnet
OPENAI_API_KEY=  # Leave empty
OPENROUTER_API_KEY=sk-or-v1-...
AUTH_TOKEN=your_secure_token
```

### 3. Advanced Setup with Milvus and VoyageAI

For advanced configurations with custom vector stores and embeddings, use the `MEM0_CONFIG` environment variable with a JSON string:

```bash
MEM0_PROVIDER=litellm
MODEL_NAME=openrouter/anthropic/claude-3.5-sonnet
OPENAI_API_KEY=
OPENROUTER_API_KEY=sk-or-v1-...
VOYAGE_API_KEY=pa-...
AUTH_TOKEN=your_secure_token

# Advanced configuration as JSON
MEM0_CONFIG='{
  "vector_store": {
    "provider": "milvus",
    "config": {
      "collection_name": "mcp_mitm_mem0_memories",
      "embedding_model_dims": 1024,
      "url": "./milvus.db"
    }
  },
  "llm": {
    "provider": "litellm",
    "config": {
      "model": "openrouter/anthropic/claude-3.5-sonnet",
      "temperature": 0.2,
      "max_tokens": 1500
    }
  },
  "embedder": {
    "provider": "voyage",
    "config": {
      "model": "voyage-large-2"
    }
  },
  "version": "v1.1"
}'
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEM0_PROVIDER` | Yes | - | LLM provider: "openai" or "litellm" |
| `MODEL_NAME` | Yes | - | Model name (e.g., "gpt-4o-mini") |
| `OPENAI_API_KEY` | Conditional | - | Required for OpenAI provider |
| `AUTH_TOKEN` | No* | - | API authentication token (*required in production) |
| `SERVER_HOST` | No | localhost | API server host |
| `SERVER_PORT` | No | 8000 | API server port |
| `DEBUG` | No | false | Enable debug mode |
| `AUTH_DISABLED_FOR_DEV` | No | false | Disable auth for development |
| `REQUIRE_AUTH` | No | true | Require authentication |
| `ENABLE_SCHEDULED_CLEANUP` | No | false | Enable automatic memory cleanup |
| `OPENROUTER_API_KEY` | No | - | Required when using OpenRouter |
| `VOYAGE_API_KEY` | No | - | Required when using VoyageAI embeddings |
| `MEM0_CONFIG` | No | - | Advanced mem0 configuration (JSON string) |

## Loading Order

1. `.env` file in the project root (using python-dotenv)
2. System environment variables (override `.env` values)

## Security Notes

- Never commit `.env` files with real API keys to version control
- Use strong, unique values for `AUTH_TOKEN`
- In production, always set `REQUIRE_AUTH=true` and `AUTH_DISABLED_FOR_DEV=false`
- Store sensitive environment variables securely in your deployment platform

## Troubleshooting

If you see a configuration error on startup, the application will display:
- Which required variables are missing
- The expected format for each variable
- Helpful examples for common configurations

Check the console output for specific error messages and configuration requirements.