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
mcp = FastMCP(settings.mcp_name)


@mcp.tool()
async def search_memories(
    query: str, user_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search memories using natural language query.

    Args:
        query: Search query
        user_id: User ID (optional, defaults to settings)
        limit: Maximum results (default: 10)

    Returns:
        List of matching memories
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

    Args:
        user_id: User ID (optional, defaults to settings)

    Returns:
        List of all memories
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

    Args:
        messages: List of message dicts with 'role' and 'content'
        user_id: User ID (optional, defaults to settings)
        metadata: Optional metadata

    Returns:
        Created memory details
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

    Args:
        memory_id: Memory ID to delete

    Returns:
        Deletion confirmation
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
    """Get all memories for a specific user as a resource."""
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
    """Get recent memories for the default user."""
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

    This reflection tool helps understand conversation themes, frequently asked
    questions, and problem-solving approaches.

    Args:
        user_id: User ID (optional, defaults to settings)
        limit: Number of recent memories to analyze (default: 20)

    Returns:
        Analysis results with patterns and insights
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

    This tool provides actionable recommendations based on identified patterns
    in the conversation history.

    Args:
        user_id: User ID (optional, defaults to settings)

    Returns:
        List of suggested next steps
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
