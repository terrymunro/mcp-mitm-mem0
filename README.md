# MCP MITM Mem0

> [!WARNING]
> **This project is experimental and deprecated.** A new, improved version is being developed at [https://github.com/terrymunro/mcp-claude-memories](https://github.com/terrymunro/mcp-claude-memories). Please consider using the new version for future projects.

A simplified memory service for Claude that intercepts conversations via MITM proxy and provides memory access through MCP.

## Overview

This project provides three core components:

1. **MITM Addon** - Intercepts Claude API conversations and stores them in Mem0
2. **MCP Server** - Provides tools for Claude to query and manage memories
3. **Reflection Agent** - Analyzes conversations to identify patterns and provide insights

## What This Project IS For

### ✅ Core Use Cases

1. **Personal AI Assistant Memory**
   - Give Claude memory of your past conversations
   - Enable continuity across sessions
   - Example: "Claude, what was that Docker command we used last week?"

2. **Project Context Persistence**
   - Maintain project-specific knowledge across conversations
   - Track decisions, approaches, and solutions
   - Example: Claude remembers your preferred coding style and project structure

3. **Learning and Adaptation**
   - Claude learns your preferences over time
   - Identifies patterns in your questions and needs
   - Example: Claude notices you prefer concise answers and adapts accordingly

4. **Development Workflow Enhancement**
   - Remember debugging sessions and solutions
   - Track what approaches worked or failed
   - Example: Claude recalls "We tried approach X for this error before, it didn't work because..."

### 🎯 Real-World Examples

**Example 1: Continuing Work**

```
User: "Let's continue working on that authentication system"
Claude: *searches memories* "I found our previous discussion about JWT authentication.
We were implementing refresh tokens and had decided to store them in HTTP-only cookies..."
```

**Example 2: Learning Preferences**

```
Claude: *after analyzing conversations* "I've noticed you prefer functional programming
patterns and often ask about TypeScript. Should I prioritize these in my responses?"
```

**Example 3: Debugging History**

```
User: "I'm getting that CORS error again"
Claude: *searches memories* "We encountered this CORS error before with your React app.
The solution was to add the proxy configuration in package.json..."
```

## What This Project is NOT For

### ❌ Not Designed For

1. **Enterprise Knowledge Management**
   - ❌ Multi-tenant memory isolation with RBAC
   - ❌ Compliance features (GDPR right-to-be-forgotten, HIPAA, SOC2)
   - ❌ Complex retention policies and data governance
   - ✅ **Instead**: Simple user-based memory storage

2. **Team Collaboration**
   - ❌ Shared memory pools across team members
   - ❌ Real-time sync between multiple Claude instances
   - ❌ Collaborative knowledge base editing
   - ✅ **Instead**: Personal memory for individual users

3. **Structured Data Systems**
   - ❌ CRM replacement for tracking contacts/customers
   - ❌ Project management tool with tasks and deadlines
   - ❌ Documentation platform with versioning
   - ✅ **Instead**: Conversational memory storage

4. **High-Performance Requirements**
   - ❌ Sub-millisecond memory retrieval
   - ❌ Real-time streaming of memories
   - ❌ High-frequency trading or gaming applications
   - ✅ **Instead**: Async cloud-based memory suitable for conversations

5. **Complex Analytics**
   - ❌ Business intelligence dashboards
   - ❌ Advanced NLP analysis pipelines
   - ❌ Machine learning model training
   - ✅ **Instead**: Simple pattern recognition for conversation insights

### 🚫 Anti-Patterns to Avoid

- **Don't** try to use this as a general-purpose database
- **Don't** expect ACID transactions or complex queries
- **Don't** store sensitive data without understanding Mem0's security model
- **Don't** assume memories are instantly available after storage

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

## Concrete Use Case Examples

### 🔧 Software Development Assistant

**Scenario**: Working on a complex refactoring across multiple sessions

```markdown
Day 1:
User: "I need to refactor the authentication system to use JWT"
Claude: "I'll help you refactor to JWT. Let's start by..."
[Discussion about JWT implementation]

Day 3:
User: "What was our plan for the refresh token rotation?"
Claude: _search_memories("JWT refresh token rotation")_
"From our discussion 2 days ago, we planned to implement refresh token rotation with
a 15-minute access token lifetime and 7-day refresh token lifetime..."
```

### 🐛 Debug Session Continuity

**Scenario**: Debugging an intermittent production issue

```markdown
Week 1:
User: "Production is throwing intermittent 504 errors"
Claude: "Let's investigate. Can you share the logs?"
[Long debugging session]

Week 2:
User: "Those 504 errors are back"
Claude: _analyze_conversations()_
"I see we've encountered this issue before. Last time, we found it correlated with
database connection pool exhaustion during peak hours. We should check if the connection
pool settings we adjusted have reverted..."
```

### 📚 Learning & Mentorship

**Scenario**: Learning a new technology with Claude as a mentor

```markdown
Session 1:
User: "Can you teach me React hooks?"
Claude: "Let's start with useState..."

Session 5:
Claude: _analyze_conversations()_
"Based on our previous sessions, you've mastered useState and useEffect. You struggled
with useCallback dependencies. Today, let's focus on custom hooks which will reinforce
those concepts..."
```

### 🏗️ Project Architecture Evolution

**Scenario**: Building a startup MVP over several months

```markdown
Month 1:
User: "Should we use microservices or monolith for our MVP?"
Claude: "For an MVP, I recommend starting with a monolith..."

Month 3:
User: "We need to scale the payment processing"
Claude: _search_memories("architecture monolith microservices")_
"Three months ago, we chose a monolithic architecture for your MVP. Now that you need
to scale payment processing, we could extract just that service following the plan we
outlined where payments would be the first candidate for extraction..."
```

### 💡 Personal Coding Preferences

**Scenario**: Claude learns and adapts to your style

```markdown
After multiple sessions:
Claude: _analyze_conversations()_
Insights detected:

- User prefers functional components over class components
- User consistently asks for TypeScript examples
- User values comprehensive error handling
- User prefers explicit types over inference

Claude: "I'll prioritize functional TypeScript examples with explicit typing and robust
error handling in my responses."
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

