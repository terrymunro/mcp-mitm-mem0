"""
Unified memory service using Mem0 SaaS platform.

Provides both async and sync interfaces for memory operations.
"""

from typing import Any

import structlog
from mem0 import AsyncMemoryClient

from .config import settings

logger = structlog.get_logger(__name__)


class MemoryService:
    """Memory service wrapper for Mem0 SaaS platform."""

    def __init__(self, api_key: str | None = None, org_id: str | None = None, project_id: str | None = None):
        """Initialize memory service with API key and optional org/project IDs.

        Args:
            api_key: Mem0 API key (defaults to settings if not provided)
            org_id: Organization ID (defaults to settings if not provided)
            project_id: Project ID (defaults to settings if not provided)
        """
        api_key = api_key or settings.mem0_api_key
        org_id = org_id or settings.mem0_org_id
        project_id = project_id or settings.mem0_project_id

        # Initialize async client with optional org/project IDs
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["org_id"] = org_id
        if project_id:
            client_kwargs["project_id"] = project_id
            
        self.async_client = AsyncMemoryClient(**client_kwargs)

        self._logger = logger.bind(service="memory")

    async def add_memory(
        self,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        categories: list[dict[str, str]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add memory asynchronously.

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (defaults to settings.default_user_id)
            agent_id: Agent identifier (defaults to settings.default_agent_id)
            run_id: Session/run identifier for tracking conversations
            categories: List of custom categories with descriptions for organizing memories
            metadata: Optional metadata to attach to the memory

        Returns:
            Response from Mem0 API
        """
        user_id = user_id or settings.default_user_id
        agent_id = agent_id or settings.default_agent_id
        categories = categories or settings.memory_categories

        # Build the add parameters
        add_params = {
            "messages": messages,
            "user_id": user_id,
            "agent_id": agent_id,
            "version": "v2"
        }
        
        # Add optional parameters if provided
        if run_id:
            add_params["run_id"] = run_id
        if categories:
            add_params["custom_categories"] = categories
            add_params["output_format"] = "v1.1"  # Required for custom categories
        if metadata:
            add_params["metadata"] = metadata

        try:
            self._logger.info(
                "Adding memory", 
                user_id=user_id, 
                agent_id=agent_id,
                run_id=run_id,
                categories=categories,
                message_count=len(messages)
            )

            result = await self.async_client.add(**add_params)

            self._logger.info(
                "Memory added successfully", 
                user_id=user_id, 
                agent_id=agent_id,
                run_id=run_id,
                categories=categories,
                memory_id=result.get("id")
            )
            return result

        except Exception as e:
            # Log the full error details for debugging
            error_details = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details = f"{str(e)} - Response: {e.response.text}"
            
            self._logger.error(
                "Failed to add memory", 
                user_id=user_id, 
                agent_id=agent_id,
                run_id=run_id,
                categories=categories,
                error=error_details,
                add_params=add_params  # Log the actual parameters being sent
            )
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

            # v2 API requires filters parameter
            search_params = {
                "query": query,
                "filters": {
                    "user_id": user_id,
                    "agent_id": settings.default_agent_id
                },
                "version": "v2",
                "top_k": limit
            }

            results = await self.async_client.search(**search_params)

            self._logger.info(
                "Search completed", user_id=user_id, result_count=len(results)
            )
            return results

        except Exception as e:
            # Enhanced error logging
            error_details = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details = f"{str(e)} - Response: {e.response.text}"
            
            self._logger.error(
                "Failed to search memories", 
                user_id=user_id, 
                error=error_details,
                search_params=search_params if 'search_params' in locals() else None
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

            results = await self.async_client.get_all(user_id=user_id, version="v2")

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


# Global instance for convenience
try:
    memory_service = MemoryService()
except (ValueError, Exception):
    # Skip initialization during testing or if API key is invalid
    memory_service = None
