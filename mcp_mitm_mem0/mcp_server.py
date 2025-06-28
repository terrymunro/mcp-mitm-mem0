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
    description="""Memory service that provides persistent context across conversations.

This service automatically captures and stores all conversations via MITM proxy, allowing you to:
- Search previous discussions when users reference past conversations
- Analyze patterns to understand user preferences and adapt responses
- Maintain project context and debugging history across sessions

Best practices:
- Always search memories when users mention previous conversations
- Use analyze_conversations() periodically to identify patterns
- Respect memory boundaries - only access memories for the current user_id
- Handle missing memories gracefully

The service stores memories asynchronously in Mem0's cloud service.
"""
)


@mcp.tool()
async def search_memories(
    query: str, user_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search memories using natural language query.
    
    Use this when:
    - User references a previous conversation ("remember when we...", "last time...")
    - You need context from past discussions
    - User asks about something you might have discussed before
    - Debugging an issue that might have been encountered previously
    
    Example queries:
    - "Docker compose configuration from last week"
    - "JWT authentication discussion"
    - "user's preferred coding style"
    - "previous CORS error solutions"

    Args:
        query: Natural language search query
        user_id: User ID (optional, defaults to settings)
        limit: Maximum results (default: 10)

    Returns:
        List of matching memories with content and metadata
    """
    try:
        results = await memory_service.search_memories(
            query=query, user_id=user_id, limit=limit
        )
        logger.info("Memory search completed", result_count=len(results))
        return results
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise RuntimeError(f"Search failed: {str(e)}")


@mcp.tool()
async def list_memories(user_id: str | None = None) -> list[dict[str, Any]]:
    """
    List all memories for a user.
    
    Use this when:
    - User wants to see their conversation history
    - You need to browse through all memories
    - Performing a comprehensive review
    - Search didn't find specific memories
    
    Note: This returns ALL memories, so use search_memories for specific topics.

    Args:
        user_id: User ID (optional, defaults to settings)

    Returns:
        List of all memories chronologically
    """
    try:
        results = await memory_service.get_all_memories(user_id=user_id)
        logger.info("Memory list retrieved", memory_count=len(results))
        return results
    except Exception as e:
        logger.error("List failed", error=str(e))
        raise RuntimeError(f"List failed: {str(e)}")


@mcp.tool()
async def add_memory(
    messages: list[dict[str, str]],
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Add a new memory from messages.
    
    Use this when:
    - User explicitly asks to remember something important
    - Critical information needs to be stored for future reference
    - Adding context that wasn't automatically captured
    - Storing user preferences or decisions
    
    Example scenarios:
    - "Remember that our API key is stored in AWS Secrets Manager"
    - "Note that I prefer tabs over spaces"
    - Important debugging discoveries

    Args:
        messages: List of message dicts with 'role' and 'content'
        user_id: User ID (optional, defaults to settings)
        metadata: Optional metadata dict for categorization

    Returns:
        Created memory with ID and timestamp
    """
    try:
        result = await memory_service.add_memory(
            messages=messages, user_id=user_id, metadata=metadata
        )
        logger.info("Memory added", memory_id=result.get("id"))
        return result
    except Exception as e:
        logger.error("Add failed", error=str(e))
        raise RuntimeError(f"Add failed: {str(e)}")


@mcp.tool()
async def delete_memory(memory_id: str) -> dict[str, str]:
    """
    Delete a specific memory by ID.
    
    Use this when:
    - User explicitly requests to forget something
    - Incorrect information was stored
    - Outdated memories need removal
    - Privacy concerns
    
    Caution: Deletions are permanent. Confirm with user if unsure.

    Args:
        memory_id: Memory ID to delete (from search/list results)

    Returns:
        Deletion confirmation with memory_id
    """
    try:
        await memory_service.delete_memory(memory_id=memory_id)
        logger.info("Memory deleted", memory_id=memory_id)
        return {"status": "deleted", "memory_id": memory_id}
    except Exception as e:
        logger.error("Delete failed", error=str(e))
        raise RuntimeError(f"Delete failed: {str(e)}")


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


@mcp.tool()
async def analyze_conversations(
    user_id: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """
    Analyze recent conversations to identify patterns and generate insights.
    
    Use this when:
    - Starting a new session (to understand user's recent work)
    - User asks about their communication patterns
    - You want to adapt your responses to user preferences
    - Periodically to maintain awareness of ongoing projects
    - After multiple similar questions (to identify knowledge gaps)
    
    This helps you:
    - Identify frequently discussed topics
    - Recognize user's preferred approaches
    - Spot recurring problems
    - Understand user's learning style

    Args:
        user_id: User ID (optional, defaults to settings)
        limit: Number of recent memories to analyze (default: 20)

    Returns:
        Analysis with insights on patterns, focus areas, and recommendations
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
        raise RuntimeError(f"Analysis failed: {str(e)}")


@mcp.tool()
async def suggest_next_actions(user_id: str | None = None) -> list[str]:
    """
    Get suggestions for next steps based on conversation history.
    
    Use this when:
    - User seems stuck or asks "what should I do next?"
    - Completing a task and planning follow-ups
    - You notice repetitive questions or issues
    - User requests recommendations
    - Starting a new session to proactively offer help
    
    Suggestions might include:
    - Creating documentation for repeated questions
    - Learning resources for identified gaps
    - Workflow improvements based on patterns
    - Next logical steps in ongoing projects

    Args:
        user_id: User ID (optional, defaults to settings)

    Returns:
        Actionable suggestions based on conversation patterns
    """
    try:
        suggestions = await reflection_agent.suggest_next_steps(user_id=user_id)
        logger.info("Generated suggestions", count=len(suggestions))
        return suggestions
    except Exception as e:
        logger.error("Suggestion generation failed", error=str(e))
        raise RuntimeError(f"Failed to generate suggestions: {str(e)}")


def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.mcp_name} MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
