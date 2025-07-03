# MCP MITM Mem0 Architecture

**Last Updated:** 2024-12-19
**Version:** 1.0.0
**Authors:** Terry Munro

## Overview

MCP MITM Mem0 is a simplified memory service for Claude that intercepts conversations via MITM proxy and provides memory access through the Model Context Protocol (MCP). The system captures Claude API conversations, stores them in Mem0's cloud service, and enables memory retrieval through MCP tools.

## System Context

This system sits between Claude clients and the Anthropic API, intercepting conversations and storing them for later retrieval. It integrates with:

- **Claude Clients** (Cursor, Claude Desktop, etc.) - via MITM proxy
- **Anthropic API** - intercepted conversations
- **Mem0 SaaS** - cloud-based memory storage
- **MCP Clients** - memory access tools

## Goals and Non-Goals

### Goals

- **Personal AI Assistant Memory**: Enable Claude to remember past conversations across sessions
- **Simple Setup**: Minimal configuration using cloud services (Mem0 SaaS)
- **MCP Integration**: Seamless memory access through standardized MCP protocol
- **Pattern Recognition**: Automatic analysis of conversation patterns and user preferences
- **Conversation Continuity**: Maintain context and preferences across multiple Claude sessions

### Non-Goals

- **Enterprise Knowledge Management**: Multi-tenant systems with RBAC and compliance features
- **Team Collaboration**: Shared memory pools across multiple users
- **High-Performance Requirements**: Sub-millisecond response times or real-time processing
- **Local Storage**: All memory operations use cloud-based Mem0 service
- **Complex Analytics**: Advanced business intelligence or machine learning model training

## High-Level Design

The system follows a three-component architecture:

1. **MITM Addon**: Transparent proxy that intercepts Claude API calls and extracts conversations
2. **Memory Service**: Handles all interactions with Mem0 SaaS for memory storage and retrieval
3. **MCP Server**: Exposes memory operations as MCP tools and resources for Claude integration

## Detailed Design

### Core Components

#### MITM Addon (memory_addon.py)

The MITM addon uses mitmproxy to intercept HTTP/HTTPS traffic between Claude clients and the Anthropic API.

**Responsibilities:**

- Intercept Claude API conversations (`/v1/messages` endpoints)
- Parse streaming and non-streaming API responses
- Extract user and assistant messages from conversations
- Trigger memory storage for complete conversation turns
- Handle reflection analysis after message thresholds

**Interfaces:**

- **Input**: HTTP/HTTPS traffic from Claude clients
- **Output**: Parsed conversation data to Memory Service

**Dependencies:**

- mitmproxy framework for traffic interception
- Memory Service for storage operations
- Reflection Agent for conversation analysis

#### Memory Service (memory_service.py)

Handles all operations with the Mem0 SaaS platform for memory management.

**Responsibilities:**

- Store conversation messages in Mem0 with metadata
- Search memories using natural language queries
- Retrieve specific memories by ID or user
- Manage memory lifecycle (add, search, delete)
- Handle Mem0 API authentication and error handling

**Interfaces:**

- **Input**: Conversation data, search queries, memory operations
- **Output**: Memory storage results, search results, retrieved memories

**Dependencies:**

- Mem0 SaaS API for memory operations
- Configuration service for API credentials

#### MCP Server (mcp_server.py)

Provides standardized MCP protocol interface for Claude to access memory operations.

**Responsibilities:**

- Expose memory search as MCP tools
- Provide memory browsing as MCP resources
- Handle conversation analysis requests
- Manage user session contexts
- Transform memory data for Claude consumption

**Interfaces:**

- **Input**: MCP tool calls and resource requests from Claude
- **Output**: Formatted memory data and analysis results

**Dependencies:**

- Memory Service for all memory operations
- Reflection Agent for conversation analysis
- MCP SDK for protocol compliance

#### Reflection Agent (reflection_agent.py)

Analyzes conversation patterns and provides insights about user preferences and behavior.

**Responsibilities:**

- Analyze recent conversation history
- Identify patterns in user questions and preferences
- Generate insights about communication style and interests
- Store analysis results as specialized memories
- Provide actionable suggestions for improved interactions

**Interfaces:**

- **Input**: Recent conversation messages and context memories
- **Output**: Analysis insights and pattern recognition results

**Dependencies:**

- Memory Service for accessing conversation history
- Mem0 for storing analysis results

### Data Flow

1. **Conversation Capture**: Claude client sends request through MITM proxy to Anthropic API
2. **Response Interception**: MITM addon captures both request and response data
3. **Message Extraction**: Parse conversation messages from API request/response
4. **Memory Storage**: Store complete conversation turn in Mem0 with metadata
5. **Reflection Trigger**: After threshold, analyze recent messages for patterns
6. **Memory Access**: Claude uses MCP tools to search and retrieve stored memories
7. **Context Enhancement**: Retrieved memories provide context for continued conversations

### APIs and Interfaces

#### MCP Tools

- **search_memories(query, user_id?, limit?)**: Natural language search across conversation history
- **list_memories(user_id?)**: List all memories for a specific user
- **add_memory(messages, user_id?, metadata?)**: Manually add memories to storage
- **delete_memory(memory_id)**: Remove specific memory by ID
- **analyze_conversations(user_id?, limit?)**: Analyze patterns in recent conversations
- **suggest_next_actions(user_id?)**: Get suggestions based on conversation history

#### MCP Resources

- **memory://{user_id}**: Browse all memories for a specific user
- **memory://recent**: View the 10 most recent memories across all users

#### External Integrations

- **Mem0 SaaS API**: Cloud-based memory storage and retrieval
- **Anthropic API**: Claude conversation interception (read-only)
- **mitmproxy**: HTTP/HTTPS traffic interception framework

## Technology Stack

### Backend

- **Language**: Python 3.12+
- **Framework**: AsyncIO for asynchronous operations
- **Memory Storage**: Mem0 SaaS cloud service
- **Proxy**: mitmproxy for traffic interception
- **Protocol**: MCP (Model Context Protocol) for Claude integration

### Configuration

- **Configuration Management**: Pydantic Settings with environment variables
- **Logging**: structlog for structured JSON logging
- **Testing**: pytest with asyncio support

### Dependencies

- **Core**: mcp, mem0ai, mitmproxy
- **Configuration**: pydantic, pydantic-settings
- **Logging**: structlog
- **Development**: pytest, ruff (linting/formatting)

## Security Considerations

### Authentication & Authorization

- **Mem0 API Key**: Required for all memory operations, stored in environment variables
- **User Isolation**: Memories are scoped by user_id to prevent cross-user access
- **No Local Storage**: All data stored in Mem0's secure cloud infrastructure

### Data Protection

- **In Transit**: All communications with Mem0 use HTTPS/TLS encryption
- **At Rest**: Conversation data stored in Mem0's secure cloud infrastructure
- **API Keys**: Sensitive credentials managed through environment variables only

### Network Security

- **MITM Proxy**: Runs on localhost (127.0.0.1:8080) by default
- **Certificate Handling**: Requires proper certificate installation for HTTPS interception
- **Scope Limitation**: Only intercepts traffic to api.anthropic.com domain

### Privacy Considerations

- **Conversation Storage**: All Claude conversations are stored in Mem0 cloud
- **Data Retention**: Follows Mem0's data retention and deletion policies
- **User Consent**: Users must be aware that conversations are being stored

## Performance and Scalability

### Performance Requirements

- **Throughput**: Designed for individual user conversation volumes
- **Latency**: Memory search typically < 2 seconds via Mem0 API
- **Availability**: Dependent on Mem0 SaaS uptime and reliability

### Scaling Strategy

- **Horizontal Scaling**: Not applicable - designed for single-user instances
- **Memory Scaling**: Unlimited storage through Mem0 cloud service
- **API Rate Limits**: Subject to Mem0 SaaS rate limiting policies

### Bottlenecks and Limitations

- **Mem0 API Limits**: Subject to Mem0's rate limiting and quota restrictions
- **Network Dependency**: Requires internet connectivity for memory operations
- **Single User Focus**: Not designed for multi-user or enterprise deployments
- **MITM Complexity**: Requires certificate installation and proxy configuration

## Reliability and Monitoring

### Error Handling

- **Memory Service Failures**: Graceful degradation with error logging
- **API Timeouts**: Retry logic with exponential backoff
- **Malformed Data**: Skip processing with detailed error logs

### Monitoring

- **Structured Logging**: JSON-formatted logs for all operations
- **Memory Metrics**: Track memory storage and retrieval success rates
- **Reflection Analysis**: Monitor pattern recognition effectiveness

### Recovery

- **Stateless Design**: No local state to recover
- **Memory Persistence**: All data persisted in Mem0 cloud
- **Automatic Retry**: Built-in retry logic for transient failures 