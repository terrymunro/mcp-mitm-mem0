"""
This is a MCP server for Mem0.

TODO: Write a better description of the MCP server.
"""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mem0 import AsyncMemory

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "test-key")

mcp = FastMCP("mcp-extended-memory", dependencies=["mem0ai", "mitmproxy"])
mem0 = AsyncMemory()

@dataclass
class AppContext:
    mem0: AsyncMemory


def extract_memories(result: Any) -> list[dict[str, Any]]:
    """
    Extract memories from the result of a mem0 operation.

    Args:
        result: The result of a mem0 operation.

    Returns:
        A list of memories.
    """
    # Handle possible dict-wrapped or direct list return
    if isinstance(result, dict):
        for key in ("results", "memories", "data"):  # common keys
            if key in result and isinstance(result[key], list):
                return result[key]
        raise ValueError(f"Unexpected dict structure from mem0: {result}")
    if isinstance(result, list):
        return result
    raise TypeError(f"mem0 returned unexpected type: {type(result)}")


@mcp.tool()
async def search_memories(user_id: str, query: str) -> list[dict[str, Any]]:
    """
    Search session memories using Mem0.

    Args:
        user_id: The user ID.
        query: The query to search for.

    Returns:
        A list of memories.
    """
    result = await mem0.search(query, user_id=user_id)
    return extract_memories(result)


@mcp.tool()
async def list_memories(user_id: str) -> list[dict[str, Any]]:
    """
    List all session memories for a user.

    Args:
        user_id: The user ID.

    Returns:
        A list of memories.
    """
    result = await mem0.get_all(user_id=user_id)
    return extract_memories(result)


@mcp.tool()
async def remember(
    user_id: str,
    messages: list[dict[str, str]],
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Add a session memory (run_id) for a user.

    Args:
        user_id: The user ID.
        messages: The messages to add.
    """
    result = await mem0.add(
        messages, user_id=user_id, metadata=metadata or {}, run_id=run_id
    )
    return extract_memories(result)


@mcp.tool()
async def forget(user_id: str, memory_id: str | None = None) -> dict[str, str]:
    """
    Delete a specific memory by id or all session memories for a user.

    Args:
        user_id: The user ID.
        memory_id: The memory ID.
    """
    if memory_id:
        return await mem0.delete(memory_id)

    return await mem0.delete_all(user_id=user_id)


if __name__ == "__main__":
    mcp.run()
