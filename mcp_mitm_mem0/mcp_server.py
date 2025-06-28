"""
MCP server for Mem0 - Provides memory query and management tools.

This server allows Claude to search, list, and manage memories stored by the MITM addon.
"""

from typing import Any

import structlog
from mcp import Resource
from mcp.server.fastmcp import FastMCP

from .config import settings
from .memory_service import memory_service
from .reflection_agent import reflection_agent

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize MCP server
mcp = FastMCP(
    settings.mcp_name,
    description="""Memory service that provides persistent context across Claude conversations.

## When to Use This Server

Connect to this server when you need:
- **Continuity**: Resume previous conversations or reference past discussions
- **Context**: Understand user preferences, coding style, and project history
- **Learning**: Adapt responses based on conversation patterns
- **Debugging**: Recall previous solutions to similar problems

## How It Works

1. **Automatic Capture**: All conversations are intercepted via MITM proxy and stored in Mem0
2. **Semantic Search**: Use natural language to find relevant past conversations
3. **Pattern Analysis**: Identify trends and preferences in user interactions
4. **Actionable Insights**: Get suggestions based on conversation history

## Core Capabilities

- **search_memories**: Find specific conversations using natural language
- **analyze_conversations**: Identify patterns and user preferences
- **list_memories**: Browse complete conversation history
- **add_memory**: Manually store important information
- **suggest_next_actions**: Get recommendations based on patterns
- **memory://**: Browse memories as MCP resources

## Example Workflows

### Resuming Work
```
User: "Let's continue with the auth system"
→ search_memories("authentication system implementation")
→ Found: JWT setup, refresh tokens, security considerations
```

### Learning Preferences
```
After multiple conversations:
→ analyze_conversations()
→ Insights: User prefers TypeScript, functional patterns, concise responses
```

### Debugging
```
User: "Getting that CORS error again"
→ search_memories("CORS error")
→ Found: Previous solution with proxy configuration
```

## Best Practices

1. **Search First**: Always search when users reference past conversations
2. **Analyze Periodically**: Run analysis to stay aware of patterns
3. **Respect Boundaries**: Only access current user's memories
4. **Handle Gracefully**: Memories may not always be available

## Technical Notes

- Memories are stored asynchronously in Mem0's cloud service
- Search uses semantic similarity, not exact matching
- Default user_id is used if not specified
- Resources provide formatted memory browsing
""",
)


@mcp.tool(
    name="search_memories",
    description="Search conversation history using natural language",
)
async def search_memories(
    query: str, user_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search memories using natural language queries to find relevant past conversations.

    ## When to Use

    - User references a previous conversation ("remember when we...", "last time...")
    - You need context from past discussions
    - User asks about something you might have discussed before
    - Debugging an issue that might have been encountered previously

    ## Example Queries

    ```python
    # Find specific technical discussions
    search_memories("Docker compose configuration from last week")
    search_memories("JWT refresh token implementation")
    search_memories("database migration strategy")

    # Understand user preferences
    search_memories("preferred coding style")
    search_memories("naming conventions we discussed")

    # Debug recurring issues
    search_memories("CORS error Access-Control-Allow-Origin")
    search_memories("TypeError undefined is not a function")

    # Project context
    search_memories("authentication requirements")
    search_memories("API design decisions")
    ```

    ## Example Responses

    ```json
    [
        {
            "id": "mem_abc123",
            "memory": "User prefers functional React components with TypeScript...",
            "created_at": "2024-01-15T10:30:00Z",
            "metadata": {"type": "conversation", "topic": "coding_style"}
        }
    ]
    ```

    Args:
        query: Natural language search query (be specific for better results)
        user_id: User ID (optional, defaults to DEFAULT_USER_ID from settings)
        limit: Maximum results to return (default: 10, max: 50)

    Returns:
        List of memories sorted by relevance, each containing:
        - id: Unique memory identifier
        - memory/content: The stored conversation text
        - created_at: When the memory was created
        - metadata: Additional context about the memory
    """
    try:
        results = await memory_service.search_memories(
            query=query, user_id=user_id, limit=limit
        )
        logger.info("Memory search completed", result_count=len(results))
        return results
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise RuntimeError(f"Search failed: {str(e)}") from e


@mcp.tool(name="list_memories", description="List all stored conversation memories")
async def list_memories(user_id: str | None = None) -> list[dict[str, Any]]:
    """
    List all memories for a user, providing a complete conversation history.

    ## When to Use

    - User wants to see their complete conversation history
    - You need to browse through all memories
    - Performing a comprehensive review or audit
    - Search didn't find specific memories
    - Getting an overview of all stored conversations

    ## Example Usage

    ```python
    # List all memories for default user
    memories = await list_memories()

    # List memories for specific user
    memories = await list_memories(user_id="alice@example.com")
    ```

    ## Example Response

    ```json
    [
        {
            "id": "mem_xyz789",
            "memory": "Discussion about implementing OAuth2 with refresh tokens...",
            "created_at": "2024-01-20T14:30:00Z",
            "metadata": {"type": "conversation", "topic": "authentication"}
        },
        {
            "id": "mem_abc123",
            "memory": "User mentioned preferring PostgreSQL over MySQL...",
            "created_at": "2024-01-19T09:15:00Z",
            "metadata": {"type": "preference"}
        }
    ]
    ```

    Note: This returns ALL memories. For large histories, prefer search_memories() for specific topics.

    Args:
        user_id: User ID (optional, defaults to DEFAULT_USER_ID from settings)

    Returns:
        List of all memories sorted by creation date (newest first), each containing:
        - id: Unique memory identifier
        - memory/content: The stored conversation text
        - created_at: ISO timestamp of memory creation
        - metadata: Additional context
    """
    try:
        results = await memory_service.get_all_memories(user_id=user_id)
        logger.info("Memory list retrieved", memory_count=len(results))
        return results
    except Exception as e:
        logger.error("List failed", error=str(e))
        raise RuntimeError(f"List failed: {str(e)}") from e


@mcp.tool(name="add_memory", description="Manually add important information to memory")
async def add_memory(
    messages: list[dict[str, str]],
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Manually add important information to memory storage.

    ## When to Use

    - User explicitly asks to remember something ("Remember that...")
    - Critical information needs to be stored for future reference
    - Adding context that wasn't automatically captured
    - Storing user preferences, decisions, or project details
    - Documenting important discoveries or solutions

    ## Example Scenarios

    ```python
    # Store user preferences
    add_memory(
        messages=[
            {"role": "user", "content": "I prefer tabs over spaces"},
            {"role": "assistant", "content": "Noted. I'll use tabs in code examples."},
        ],
        metadata={"type": "preference", "category": "coding_style"},
    )

    # Remember project configuration
    add_memory(
        messages=[
            {"role": "user", "content": "Our API keys are in AWS Secrets Manager"},
            {
                "role": "assistant",
                "content": "I'll remember to reference AWS Secrets Manager for API keys.",
            },
        ],
        metadata={"type": "configuration", "project": "backend"},
    )

    # Document a solution
    add_memory(
        messages=[
            {
                "role": "assistant",
                "content": 'Solved CORS issue by adding proxy config to package.json: "proxy": "http://localhost:5000"',
            }
        ],
        metadata={"type": "solution", "issue": "CORS", "resolved": true},
    )
    ```

    ## Example Response

    ```json
    {
        "id": "mem_newid123",
        "created_at": "2024-01-20T15:45:00Z",
        "status": "created",
        "message": "Memory added successfully"
    }
    ```

    Args:
        messages: List of message dictionaries, each with:
            - role: "user", "assistant", or "system"
            - content: The message text to store
        user_id: User ID (optional, defaults to DEFAULT_USER_ID)
        metadata: Optional metadata dict for categorization (type, project, tags, etc.)

    Returns:
        Dictionary containing:
        - id: Unique identifier for the created memory
        - created_at: Timestamp of creation
        - status: "created" on success
        - message: Confirmation message
    """
    try:
        result = await memory_service.add_memory(
            messages=messages, user_id=user_id, metadata=metadata
        )
        logger.info("Memory added", memory_id=result.get("id"))
        return result
    except Exception as e:
        logger.error("Add failed", error=str(e))
        raise RuntimeError(f"Add failed: {str(e)}") from e


@mcp.tool(name="delete_memory", description="Delete a specific memory by ID")
async def delete_memory(memory_id: str) -> dict[str, str]:
    """
    Permanently delete a specific memory by its ID.

    ## When to Use

    - User explicitly requests to forget something ("forget about...", "delete that memory")
    - Incorrect or misleading information was stored
    - Outdated memories that are no longer relevant
    - Privacy concerns or sensitive data removal
    - Cleaning up test or temporary memories

    ## Example Usage

    ```python
    # Delete after finding incorrect memory
    memories = await search_memories("API endpoint")
    # User: "That old endpoint is wrong, delete it"
    await delete_memory("mem_oldid456")

    # Delete outdated preference
    # User: "Actually, forget what I said about tabs vs spaces"
    await delete_memory("mem_tabpref789")
    ```

    ## Example Response

    ```json
    {
        "status": "deleted",
        "memory_id": "mem_oldid456",
        "message": "Memory successfully deleted"
    }
    ```

    ⚠️ **Caution**: Deletions are permanent and cannot be undone. Always confirm with the user if you're unsure about deleting a memory.

    Args:
        memory_id: The unique memory ID to delete (obtained from search_memories or list_memories)

    Returns:
        Confirmation dictionary containing:
        - status: "deleted" on success
        - memory_id: The ID that was deleted
        - message: Confirmation message
    """
    try:
        await memory_service.delete_memory(memory_id=memory_id)
        logger.info("Memory deleted", memory_id=memory_id)
        return {"status": "deleted", "memory_id": memory_id}
    except Exception as e:
        logger.error("Delete failed", error=str(e))
        raise RuntimeError(f"Delete failed: {str(e)}") from e


# Memory resources for browsing
@mcp.resource("memory://{user_id}")
async def get_user_memories(user_id: str) -> Resource:
    """Get all memories for a specific user as a resource.

    Browse memories in a structured format. Useful for:
    - Reviewing conversation history
    - Understanding the full context of user interactions
    - Finding memories that might not appear in search
    """
    try:
        memories = await memory_service.get_all_memories(user_id=user_id)

        # Format memories for display
        content = f"# Memories for user: {user_id}\n\n"
        content += f"Total memories: {len(memories)}\n\n"

        for i, memory in enumerate(memories, 1):
            content += f"## Memory {i}\n"
            content += f"- ID: {memory.get('id', 'N/A')}\n"
            content += f"- Created: {memory.get('created_at', 'N/A')}\n"
            content += (
                f"- Content: {memory.get('memory', memory.get('content', 'N/A'))}\n"
            )

            if metadata := memory.get("metadata"):
                content += f"- Metadata: {metadata}\n"

            content += "\n"

        return Resource(
            uri=f"memory://{user_id}",
            name=f"Memories for {user_id}",
            description=f"All stored memories for user {user_id}",
            mimeType="text/markdown",
            text=content,
        )

    except Exception as e:
        logger.error("Failed to get user memories", user_id=user_id, error=str(e))
        raise


@mcp.resource("memory://recent")
async def get_recent_memories() -> Resource:
    """Get recent memories for the default user.

    Quick access to the 10 most recent memories. Useful for:
    - Getting up to speed at the start of a session
    - Checking what was just discussed
    - Understanding current context without searching
    """
    try:
        memories = await memory_service.get_all_memories()

        # Sort by creation date and get last 10
        if memories:
            # Assuming memories have created_at field
            sorted_memories = sorted(
                memories, key=lambda m: m.get("created_at", ""), reverse=True
            )[:10]
        else:
            sorted_memories = []

        content = "# Recent Memories\n\n"
        content += f"Showing {len(sorted_memories)} most recent memories\n\n"

        for i, memory in enumerate(sorted_memories, 1):
            content += f"## {i}. {memory.get('created_at', 'N/A')}\n"
            content += f"- ID: {memory.get('id', 'N/A')}\n"
            content += (
                f"- Content: {memory.get('memory', memory.get('content', 'N/A'))}\n\n"
            )

        return Resource(
            uri="memory://recent",
            name="Recent Memories",
            description="Most recent memories from all conversations",
            mimeType="text/markdown",
            text=content,
        )

    except Exception as e:
        logger.error("Failed to get recent memories", error=str(e))
        raise


@mcp.tool(
    name="analyze_conversations",
    description="Analyze conversation patterns and generate insights",
)
async def analyze_conversations(
    user_id: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """
    Analyze recent conversations to identify patterns, preferences, and generate actionable insights.

    ## When to Use

    - Starting a new session (understand user's recent work and context)
    - User asks about their communication or work patterns
    - You want to adapt responses to user preferences
    - Periodically to maintain awareness of ongoing projects
    - After multiple similar questions (identify knowledge gaps)
    - When you need to understand the user's learning style

    ## What It Analyzes

    - **Topic Frequency**: Most discussed subjects and technologies
    - **Question Patterns**: Types of questions frequently asked
    - **Work Style**: Problem-solving approaches and preferences
    - **Project Focus**: Current projects and priorities
    - **Knowledge Gaps**: Areas where user needs more support

    ## Example Usage

    ```python
    # Analyze at session start
    insights = await analyze_conversations()
    # Use insights to tailor your responses

    # Analyze more history for deeper patterns
    insights = await analyze_conversations(limit=50)

    # Analyze specific user
    insights = await analyze_conversations(user_id="alice@example.com")
    ```

    ## Example Response

    ```json
    {
        "status": "analyzed",
        "memory_count": 20,
        "insights": [
            {
                "type": "frequent_questions",
                "description": "User has asked 5 questions about React hooks recently.",
                "examples": [
                    "How do I use useCallback correctly?",
                    "When should I use useMemo?",
                    "What's the difference between useEffect and useLayoutEffect?"
                ],
                "recommendation": "Consider providing more proactive React hooks guidance"
            },
            {
                "type": "focus_area",
                "description": "Primary focus appears to be on authentication (mentioned 8 times)",
                "recommendation": "Prepare detailed auth implementation resources"
            },
            {
                "type": "problem_solving_pattern",
                "description": "User prefers iterative approaches with testing",
                "recommendation": "Include test examples in code suggestions"
            }
        ]
    }
    ```

    Args:
        user_id: User ID to analyze (optional, defaults to DEFAULT_USER_ID)
        limit: Number of recent memories to analyze (default: 20, max: 100)

    Returns:
        Analysis dictionary containing:
        - status: "analyzed" on success
        - memory_count: Number of memories analyzed
        - insights: List of insight objects, each with:
            - type: Category of insight (frequent_questions, focus_area, etc.)
            - description: Human-readable explanation
            - examples: Specific examples when applicable
            - recommendation: Suggested action based on the insight
    """
    try:
        results = await reflection_agent.analyze_recent_conversations(
            user_id=user_id, limit=limit
        )
        logger.info(
            "Conversation analysis completed", insights=len(results.get("insights", []))
        )
        return results
    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        raise RuntimeError(f"Analysis failed: {str(e)}") from e


@mcp.tool(
    name="suggest_next_actions",
    description="Get personalized recommendations based on conversation history",
)
async def suggest_next_actions(user_id: str | None = None) -> list[str]:
    """
    Generate personalized action recommendations based on conversation patterns and history.

    ## When to Use

    - User asks "what should I do next?" or seems stuck
    - Completing a task and planning follow-up work
    - You notice repetitive questions or recurring issues
    - User explicitly requests recommendations
    - Starting a new session to proactively offer guidance
    - After analyzing conversations to provide actionable advice

    ## Types of Suggestions

    - **Documentation**: Create guides for frequently asked topics
    - **Learning**: Resources for identified knowledge gaps
    - **Workflow**: Process improvements based on patterns
    - **Next Steps**: Logical progression in current projects
    - **Best Practices**: Improvements based on observed anti-patterns
    - **Tools**: Recommendations for tools that could help

    ## Example Usage

    ```python
    # Get suggestions for current user
    suggestions = await suggest_next_actions()
    # Present to user: "Based on our conversations, here are some suggestions..."

    # Get suggestions for specific user
    suggestions = await suggest_next_actions(user_id="alice@example.com")
    ```

    ## Example Response

    ```python
    [
        "Create a personal React hooks cheat sheet - you've asked about useCallback, useMemo, and useEffect multiple times",
        "Set up a testing framework for your auth system - you mentioned wanting to test but haven't started",
        "Consider using TypeScript for your new components - you've had several type-related bugs",
        "Document your API authentication flow - it's complex and you might forget the details",
        "Explore React Query for data fetching - it would solve several issues you've encountered",
    ]
    ```

    ## How Suggestions Are Generated

    1. Analyzes recent conversation patterns
    2. Identifies pain points and repeated issues
    3. Recognizes knowledge gaps and learning opportunities
    4. Considers project context and goals
    5. Generates specific, actionable recommendations

    Args:
        user_id: User ID to analyze (optional, defaults to DEFAULT_USER_ID)

    Returns:
        List of actionable suggestion strings, each being:
        - Specific and concrete (not vague advice)
        - Based on actual conversation history
        - Prioritized by potential impact
        - Practical and implementable
    """
    try:
        suggestions = await reflection_agent.suggest_next_steps(user_id=user_id)
        logger.info("Generated suggestions", count=len(suggestions))
        return suggestions
    except Exception as e:
        logger.error("Suggestion generation failed", error=str(e))
        raise RuntimeError(f"Failed to generate suggestions: {str(e)}") from e


def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.mcp_name} MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
