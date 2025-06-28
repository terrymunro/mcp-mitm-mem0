"""
Unified memory service using Mem0 SaaS platform.

Provides both async and sync interfaces for memory operations.
"""

from typing import Any

import structlog
from mem0 import AsyncMemoryClient, MemoryClient

from .config import settings

logger = structlog.get_logger(__name__)


class MemoryService:
    """Memory service wrapper for Mem0 SaaS platform."""

    def __init__(self, api_key: str | None = None):
        """Initialize memory service with API key.

        Args:
            api_key: Mem0 API key (defaults to settings if not provided)
        """
        api_key = api_key or settings.mem0_api_key

        # Initialize both sync and async clients
        self.async_client = AsyncMemoryClient(api_key=api_key)
        self.sync_client = MemoryClient(api_key=api_key)

        self._logger = logger.bind(service="memory")

    # Async methods for MCP server

    async def add_memory(
        self,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add memory asynchronously.

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (defaults to settings.default_user_id)
            metadata: Optional metadata to attach to the memory

        Returns:
            Response from Mem0 API
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info(
                "Adding memory", user_id=user_id, message_count=len(messages)
            )

            result = await self.async_client.add(
                messages=messages, user_id=user_id, metadata=metadata
            )

            self._logger.info(
                "Memory added successfully", user_id=user_id, memory_id=result.get("id")
            )
            return result

        except Exception as e:
            self._logger.error("Failed to add memory", user_id=user_id, error=str(e))
            raise

    async def search_memories(
        self, query: str, user_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search memories asynchronously.

        Args:
            query: Search query
            user_id: User identifier (defaults to settings.default_user_id)
            limit: Maximum number of results

        Returns:
            List of matching memories
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info("Searching memories", user_id=user_id, query=query[:50])

            results = await self.async_client.search(
                query=query, user_id=user_id, limit=limit
            )

            self._logger.info(
                "Search completed", user_id=user_id, result_count=len(results)
            )
            return results

        except Exception as e:
            self._logger.error(
                "Failed to search memories", user_id=user_id, error=str(e)
            )
            raise

    async def get_all_memories(
        self, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all memories for a user asynchronously.

        Args:
            user_id: User identifier (defaults to settings.default_user_id)

        Returns:
            List of all memories for the user
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info("Getting all memories", user_id=user_id)

            results = await self.async_client.get_all(user_id=user_id)

            self._logger.info(
                "Retrieved memories", user_id=user_id, memory_count=len(results)
            )
            return results

        except Exception as e:
            self._logger.error("Failed to get memories", user_id=user_id, error=str(e))
            raise

    async def delete_memory(self, memory_id: str) -> dict[str, Any]:
        """Delete a specific memory asynchronously.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            Deletion response
        """
        try:
            self._logger.info("Deleting memory", memory_id=memory_id)

            result = await self.async_client.delete(memory_id=memory_id)

            self._logger.info("Memory deleted", memory_id=memory_id)
            return result

        except Exception as e:
            self._logger.error(
                "Failed to delete memory", memory_id=memory_id, error=str(e)
            )
            raise

    # Sync methods for MITM addon

    def add_memory_sync(
        self,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add memory synchronously (for MITM addon).

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (defaults to settings.default_user_id)
            metadata: Optional metadata to attach to the memory

        Returns:
            Response from Mem0 API
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info(
                "Adding memory (sync)", user_id=user_id, message_count=len(messages)
            )

            result = self.sync_client.add(
                messages=messages, user_id=user_id, metadata=metadata
            )

            self._logger.info(
                "Memory added successfully (sync)",
                user_id=user_id,
                memory_id=result.get("id"),
            )
            return result

        except Exception as e:
            self._logger.error(
                "Failed to add memory (sync)", user_id=user_id, error=str(e)
            )
            raise

    def search_memories_sync(
        self, query: str, user_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search memories synchronously (for MITM addon).

        Args:
            query: Search query
            user_id: User identifier (defaults to settings.default_user_id)
            limit: Maximum number of results

        Returns:
            List of matching memories
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info(
                "Searching memories (sync)", user_id=user_id, query=query[:50]
            )

            results = self.sync_client.search(query=query, user_id=user_id, limit=limit)

            self._logger.info(
                "Search completed (sync)", user_id=user_id, result_count=len(results)
            )
            return results

        except Exception as e:
            self._logger.error(
                "Failed to search memories (sync)", user_id=user_id, error=str(e)
            )
            raise


# Global instance for convenience
try:
    memory_service = MemoryService()
except (ValueError, Exception):
    # Skip initialization during testing or if API key is invalid
    memory_service = None
