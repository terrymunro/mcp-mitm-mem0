"""
Comprehensive tests for MemoryService.

Tests core memory operations, configuration, and essential edge cases.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from mcp_mitm_mem0.config import Settings
from mcp_mitm_mem0.memory_service import MemoryService


class TestMemoryService:
    """Test MemoryService core functionality and edge cases."""

    def test_memory_service_initialization(self, mock_memory_clients):
        """Test service initialization with default settings."""
        mock_async_class, mock_sync_class = mock_memory_clients

        with patch("mcp_mitm_mem0.memory_service.settings") as mock_settings:
            mock_settings.mem0_api_key = "test-key"

            service = MemoryService()

            assert service.async_client is not None
            assert service.sync_client is not None

    def test_memory_service_explicit_api_key(self, mock_memory_clients):
        """Test initialization with explicit API key."""
        mock_async_class, mock_sync_class = mock_memory_clients

        MemoryService(api_key="explicit-key")

        # Verify clients were created with explicit key
        mock_async_class.assert_called_with(api_key="explicit-key")
        mock_sync_class.assert_called_with(api_key="explicit-key")

    @pytest.mark.asyncio
    async def test_add_memory_success(self, memory_service_mocked, sample_messages):
        """Test successful memory addition."""
        memory_service_mocked.async_client.add = AsyncMock(
            return_value={"id": "mem123"}
        )

        result = await memory_service_mocked.add_memory(
            sample_messages, user_id="test-user"
        )

        assert result["id"] == "mem123"
        memory_service_mocked.async_client.add.assert_called_once_with(
            messages=sample_messages, user_id="test-user", metadata=None
        )

    @pytest.mark.asyncio
    async def test_add_memory_with_metadata(self, memory_service_mocked):
        """Test memory addition with metadata."""
        metadata = {"source": "test", "priority": "high"}
        memory_service_mocked.async_client.add = AsyncMock(
            return_value={"id": "mem456"}
        )

        result = await memory_service_mocked.add_memory(
            [{"role": "user", "content": "test"}],
            user_id="test-user",
            metadata=metadata,
        )

        assert result["id"] == "mem456"
        memory_service_mocked.async_client.add.assert_called_once_with(
            messages=[{"role": "user", "content": "test"}],
            user_id="test-user",
            metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_search_memories_success(self, memory_service_mocked):
        """Test successful memory search."""
        expected_results = [{"id": "mem1", "content": "Found memory"}]
        memory_service_mocked.async_client.search = AsyncMock(
            return_value=expected_results
        )

        result = await memory_service_mocked.search_memories(
            "test query", user_id="test-user", limit=5
        )

        assert result == expected_results
        memory_service_mocked.async_client.search.assert_called_once_with(
            query="test query", user_id="test-user", limit=5
        )

    @pytest.mark.asyncio
    async def test_get_all_memories_success(
        self, memory_service_mocked, sample_memories
    ):
        """Test getting all memories."""
        memory_service_mocked.async_client.get_all = AsyncMock(
            return_value=sample_memories
        )

        result = await memory_service_mocked.get_all_memories("test-user")

        assert result == sample_memories
        memory_service_mocked.async_client.get_all.assert_called_once_with(
            user_id="test-user"
        )

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, memory_service_mocked):
        """Test successful memory deletion."""
        memory_service_mocked.async_client.delete = AsyncMock(
            return_value={"status": "deleted"}
        )

        result = await memory_service_mocked.delete_memory("mem123")

        assert result["status"] == "deleted"
        memory_service_mocked.async_client.delete.assert_called_once_with(
            memory_id="mem123"
        )

    def test_add_memory_sync_success(self, memory_service_mocked, sample_messages):
        """Test sync memory addition."""
        memory_service_mocked.sync_client.add.return_value = {"id": "sync-mem"}

        result = memory_service_mocked.add_memory_sync(sample_messages)

        assert result["id"] == "sync-mem"
        memory_service_mocked.sync_client.add.assert_called_once()

    def test_search_memories_sync_success(self, memory_service_mocked):
        """Test sync memory search."""
        expected_results = [{"id": "mem1", "content": "Found"}]
        memory_service_mocked.sync_client.search.return_value = expected_results

        result = memory_service_mocked.search_memories_sync("test query")

        assert result == expected_results

    # Essential Edge Cases
    @pytest.mark.asyncio
    async def test_add_memory_empty_messages(self, memory_service_mocked):
        """Test adding memory with empty messages."""
        memory_service_mocked.async_client.add = AsyncMock(
            return_value={"id": "empty-mem"}
        )

        result = await memory_service_mocked.add_memory([], "test-user")

        assert result["id"] == "empty-mem"

    @pytest.mark.asyncio
    async def test_add_memory_api_failure(self, memory_service_mocked):
        """Test add memory API failure."""
        memory_service_mocked.async_client.add = AsyncMock(
            side_effect=Exception("API timeout")
        )

        with pytest.raises(Exception, match="API timeout"):
            await memory_service_mocked.add_memory([
                {"role": "user", "content": "test"}
            ])

    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self, memory_service_mocked):
        """Test search with empty query."""
        memory_service_mocked.async_client.search = AsyncMock(return_value=[])

        result = await memory_service_mocked.search_memories("", "test-user")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_memories_api_failure(self, memory_service_mocked):
        """Test search API failure."""
        memory_service_mocked.async_client.search = AsyncMock(
            side_effect=Exception("Search service down")
        )

        with pytest.raises(Exception, match="Search service down"):
            await memory_service_mocked.search_memories("test")

    @pytest.mark.asyncio
    async def test_delete_memory_nonexistent(self, memory_service_mocked):
        """Test deleting nonexistent memory."""
        memory_service_mocked.async_client.delete = AsyncMock(
            side_effect=Exception("Memory not found")
        )

        with pytest.raises(Exception, match="Memory not found"):
            await memory_service_mocked.delete_memory("nonexistent")

    @pytest.mark.asyncio
    async def test_unicode_content_handling(self, memory_service_mocked):
        """Test basic unicode support."""
        unicode_messages = [
            {"role": "user", "content": "Hello 世界 🌍"},
            {"role": "assistant", "content": "Café résumé naïve"},
        ]
        memory_service_mocked.async_client.add = AsyncMock(
            return_value={"id": "unicode-mem"}
        )

        result = await memory_service_mocked.add_memory(unicode_messages)

        assert result["id"] == "unicode-mem"

    def test_sync_api_error_handling(self, memory_service_mocked):
        """Test sync API error handling."""
        memory_service_mocked.sync_client.add.side_effect = Exception("Sync error")

        with pytest.raises(Exception, match="Sync error"):
            memory_service_mocked.add_memory_sync([{"role": "user", "content": "test"}])


class TestConfiguration:
    """Test configuration management and edge cases."""

    def test_settings_initialization(self):
        """Test settings with environment variables."""
        with patch.dict(
            os.environ,
            {
                "MEM0_API_KEY": "env_key",
                "DEFAULT_USER_ID": "env_user",
                "MCP_NAME": "env_name",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.mem0_api_key == "env_key"
            assert settings.default_user_id == "env_user"
            assert settings.mcp_name == "env_name"

    def test_settings_defaults(self):
        """Test default values are correct."""
        settings = Settings()

        assert settings.default_user_id == "default_user"
        assert settings.mcp_name == "mcp-mitm-mem0"
        assert settings.debug is False
        assert settings.mitm_host == "localhost"
        assert settings.mitm_port == 8080

    def test_settings_with_empty_env_vars(self):
        """Test settings with empty environment variables."""
        with patch.dict(
            os.environ,
            {"MEM0_API_KEY": "", "DEFAULT_USER_ID": ""},
            clear=True,
        ):
            settings = Settings()

            assert settings.mem0_api_key == ""
            assert settings.default_user_id == ""

    def test_settings_unicode_handling(self):
        """Test basic unicode support in configuration."""
        with patch.dict(
            os.environ,
            {"MEM0_API_KEY": "key_🔑_test", "DEFAULT_USER_ID": "user_🤖_123"},
            clear=True,
        ):
            settings = Settings()

            assert "🔑" in settings.mem0_api_key
            assert "🤖" in settings.default_user_id

    def test_memory_service_handles_none_settings(self):
        """Test memory service with invalid settings."""
        with (
            patch("mcp_mitm_mem0.memory_service.AsyncMemoryClient"),
            patch("mcp_mitm_mem0.memory_service.MemoryClient"),
            patch("mcp_mitm_mem0.memory_service.settings", None),
            pytest.raises(AttributeError),
        ):
            MemoryService()
