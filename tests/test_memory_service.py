"""
Unit tests for memory service wrapper with retry logic and error handling.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_mitm_mem0.memory_service import (
    AsyncMemoryService,
    MemoryServiceConnectionError,
    MemoryServiceError,
    MemoryServiceTimeoutError,
    MemoryServiceValidationError,
    SyncMemoryService,
    _handle_mem0_exception,
)


class TestExceptionHandling:
    """Test exception conversion and handling."""

    def test_handle_timeout_exception(self):
        """Test timeout exception conversion."""
        original_exc = Exception("Request timeout occurred")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceTimeoutError)
        assert "Memory service timeout" in str(result)
        assert result.original_error is original_exc

    def test_handle_connection_exception(self):
        """Test connection exception conversion."""
        original_exc = Exception("Connection failed to database")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceConnectionError)
        assert "Memory service connection error" in str(result)
        assert result.original_error is original_exc

    def test_handle_network_exception(self):
        """Test network exception conversion."""
        original_exc = Exception("Network error occurred")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceConnectionError)
        assert "Memory service connection error" in str(result)
        assert result.original_error is original_exc

    def test_handle_validation_exception(self):
        """Test validation exception conversion."""
        original_exc = Exception("Invalid input provided")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceValidationError)
        assert "Memory service validation error" in str(result)
        assert result.original_error is original_exc

    def test_handle_bad_request_exception(self):
        """Test bad request exception conversion."""
        original_exc = Exception("Bad request format")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceValidationError)
        assert "Memory service validation error" in str(result)
        assert result.original_error is original_exc

    def test_handle_generic_exception(self):
        """Test generic exception conversion."""
        original_exc = Exception("Some other error")
        result = _handle_mem0_exception(original_exc)

        assert isinstance(result, MemoryServiceError)
        assert "Memory service error" in str(result)
        assert result.original_error is original_exc


# Shared fixtures for both test classes
@pytest.fixture
def mock_async_memory():
    """Create a mock AsyncMemory instance."""
    return AsyncMock()


@pytest.fixture
def async_memory_service(mock_async_memory):
    """Create AsyncMemoryService with mocked memory."""
    with patch(
        "mcp_mitm_mem0.memory_service.AsyncMemory", return_value=mock_async_memory
    ):
        return AsyncMemoryService()


@pytest.fixture
def mock_sync_memory():
    """Create a mock Memory instance."""
    return Mock()


@pytest.fixture
def sync_memory_service(mock_sync_memory):
    """Create SyncMemoryService with mocked memory."""
    with patch("mcp_mitm_mem0.memory_service.Memory", return_value=mock_sync_memory):
        return SyncMemoryService()


class TestAsyncMemoryService:
    """Test AsyncMemoryService wrapper functionality."""

    @pytest.mark.asyncio
    async def test_add_success(self, async_memory_service, mock_async_memory):
        """Test successful memory addition."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.add.return_value = expected_result

        # Execute
        result = await async_memory_service.add(messages, user_id)

        # Verify
        assert result == expected_result
        mock_async_memory.add.assert_called_once_with(
            messages, user_id=user_id, metadata={}, run_id=None
        )

    @pytest.mark.asyncio
    async def test_add_with_metadata_and_run_id(
        self, async_memory_service, mock_async_memory
    ):
        """Test memory addition with metadata and run_id."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"
        metadata = {"source": "test"}
        run_id = "run_123"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.add.return_value = expected_result

        # Execute
        result = await async_memory_service.add(messages, user_id, metadata, run_id)

        # Verify
        assert result == expected_result
        mock_async_memory.add.assert_called_once_with(
            messages, user_id=user_id, metadata=metadata, run_id=run_id
        )

    @pytest.mark.asyncio
    async def test_add_with_dict_response(
        self, async_memory_service, mock_async_memory
    ):
        """Test memory addition with dict-wrapped response."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"
        memories_data = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.add.return_value = {"results": memories_data}

        # Execute
        result = await async_memory_service.add(messages, user_id)

        # Verify
        assert result == memories_data

    @pytest.mark.asyncio
    async def test_add_retry_on_failure(self, async_memory_service, mock_async_memory):
        """Test retry logic on add failure."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"

        # First two calls fail, third succeeds
        mock_async_memory.add.side_effect = [
            Exception("Connection error"),
            Exception("Network timeout"),
            [{"id": "mem_123", "content": "test memory"}],
        ]

        # Execute
        result = await async_memory_service.add(messages, user_id)

        # Verify
        assert result == [{"id": "mem_123", "content": "test memory"}]
        assert mock_async_memory.add.call_count == 3

    @pytest.mark.asyncio
    async def test_add_failure_after_retries(
        self, async_memory_service, mock_async_memory
    ):
        """Test failure after all retries exhausted."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"

        # All calls fail
        mock_async_memory.add.side_effect = Exception("Persistent connection error")

        # Execute & Verify
        with pytest.raises(MemoryServiceConnectionError):
            await async_memory_service.add(messages, user_id)

        assert mock_async_memory.add.call_count == 3

    @pytest.mark.asyncio
    async def test_search_success(self, async_memory_service, mock_async_memory):
        """Test successful memory search."""
        # Setup
        query = "test query"
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.search.return_value = expected_result

        # Execute
        result = await async_memory_service.search(query, user_id)

        # Verify
        assert result == expected_result
        mock_async_memory.search.assert_called_once_with(query, user_id=user_id)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, async_memory_service, mock_async_memory):
        """Test memory search with limit."""
        # Setup
        query = "test query"
        user_id = "test_user"
        limit = 10
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.search.return_value = expected_result

        # Execute
        result = await async_memory_service.search(query, user_id, limit)

        # Verify
        assert result == expected_result
        mock_async_memory.search.assert_called_once_with(
            query, user_id=user_id, limit=limit
        )

    @pytest.mark.asyncio
    async def test_search_retry_on_failure(
        self, async_memory_service, mock_async_memory
    ):
        """Test retry logic on search failure."""
        # Setup
        query = "test query"
        user_id = "test_user"

        # First two calls fail, third succeeds
        mock_async_memory.search.side_effect = [
            Exception("timeout error"),
            Exception("network error"),
            [{"id": "mem_123", "content": "test memory"}],
        ]

        # Execute
        result = await async_memory_service.search(query, user_id)

        # Verify
        assert result == [{"id": "mem_123", "content": "test memory"}]
        assert mock_async_memory.search.call_count == 3

    @pytest.mark.asyncio
    async def test_get_all_success(self, async_memory_service, mock_async_memory):
        """Test successful get all memories."""
        # Setup
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_async_memory.get_all.return_value = expected_result

        # Execute
        result = await async_memory_service.get_all(user_id)

        # Verify
        assert result == expected_result
        mock_async_memory.get_all.assert_called_once_with(user_id=user_id)

    @pytest.mark.asyncio
    async def test_get_all_retry_on_failure(
        self, async_memory_service, mock_async_memory
    ):
        """Test retry logic on get_all failure."""
        # Setup
        user_id = "test_user"

        # First call fails, second succeeds
        mock_async_memory.get_all.side_effect = [
            Exception("connection error"),
            [{"id": "mem_123", "content": "test memory"}],
        ]

        # Execute
        result = await async_memory_service.get_all(user_id)

        # Verify
        assert result == [{"id": "mem_123", "content": "test memory"}]
        assert mock_async_memory.get_all.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_success(self, async_memory_service, mock_async_memory):
        """Test successful memory deletion."""
        # Setup
        memory_id = "mem_123"
        expected_result = {"message": "Memory deleted successfully"}
        mock_async_memory.delete.return_value = expected_result

        # Execute
        result = await async_memory_service.delete(memory_id)

        # Verify
        assert result == expected_result
        mock_async_memory.delete.assert_called_once_with(memory_id)

    @pytest.mark.asyncio
    async def test_delete_retry_on_failure(
        self, async_memory_service, mock_async_memory
    ):
        """Test retry logic on delete failure."""
        # Setup
        memory_id = "mem_123"

        # First call fails, second succeeds
        mock_async_memory.delete.side_effect = [
            Exception("validation error"),
            {"message": "Memory deleted successfully"},
        ]

        # Execute
        result = await async_memory_service.delete(memory_id)

        # Verify
        assert result == {"message": "Memory deleted successfully"}
        assert mock_async_memory.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_all_success(self, async_memory_service, mock_async_memory):
        """Test successful delete all memories."""
        # Setup
        user_id = "test_user"
        expected_result = {"message": "All memories deleted successfully"}
        mock_async_memory.delete_all.return_value = expected_result

        # Execute
        result = await async_memory_service.delete_all(user_id)

        # Verify
        assert result == expected_result
        mock_async_memory.delete_all.assert_called_once_with(user_id=user_id)

    @pytest.mark.asyncio
    async def test_delete_all_retry_on_failure(
        self, async_memory_service, mock_async_memory
    ):
        """Test retry logic on delete_all failure."""
        # Setup
        user_id = "test_user"

        # First call fails, second succeeds
        mock_async_memory.delete_all.side_effect = [
            Exception("connection error"),
            {"message": "All memories deleted successfully"},
        ]

        # Execute
        result = await async_memory_service.delete_all(user_id)

        # Verify
        assert result == {"message": "All memories deleted successfully"}
        assert mock_async_memory.delete_all.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_memories_from_dict_with_results_key(
        self, async_memory_service
    ):
        """Test memory extraction from dict with 'results' key."""
        result = {"results": [{"id": "mem_123"}]}
        extracted = async_memory_service._extract_memories(result)
        assert extracted == [{"id": "mem_123"}]

    @pytest.mark.asyncio
    async def test_extract_memories_from_dict_with_memories_key(
        self, async_memory_service
    ):
        """Test memory extraction from dict with 'memories' key."""
        result = {"memories": [{"id": "mem_123"}]}
        extracted = async_memory_service._extract_memories(result)
        assert extracted == [{"id": "mem_123"}]

    @pytest.mark.asyncio
    async def test_extract_memories_from_dict_with_data_key(self, async_memory_service):
        """Test memory extraction from dict with 'data' key."""
        result = {"data": [{"id": "mem_123"}]}
        extracted = async_memory_service._extract_memories(result)
        assert extracted == [{"id": "mem_123"}]

    @pytest.mark.asyncio
    async def test_extract_memories_from_list(self, async_memory_service):
        """Test memory extraction from direct list."""
        result = [{"id": "mem_123"}]
        extracted = async_memory_service._extract_memories(result)
        assert extracted == [{"id": "mem_123"}]

    @pytest.mark.asyncio
    async def test_extract_memories_invalid_dict(self, async_memory_service):
        """Test error on invalid dict structure."""
        result = {"invalid_key": [{"id": "mem_123"}]}
        with pytest.raises(MemoryServiceValidationError):
            async_memory_service._extract_memories(result)

    @pytest.mark.asyncio
    async def test_extract_memories_invalid_type(self, async_memory_service):
        """Test error on invalid result type."""
        result = "invalid_type"
        with pytest.raises(MemoryServiceValidationError):
            async_memory_service._extract_memories(result)


class TestSyncMemoryService:
    """Test SyncMemoryService wrapper functionality."""

    def test_add_success(self, sync_memory_service, mock_sync_memory):
        """Test successful memory addition."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_sync_memory.add.return_value = expected_result

        # Execute
        result = sync_memory_service.add(messages, user_id)

        # Verify
        assert result == expected_result
        mock_sync_memory.add.assert_called_once_with(
            messages, user_id=user_id, metadata={}, run_id=None
        )

    def test_add_retry_on_failure(self, sync_memory_service, mock_sync_memory):
        """Test retry logic on add failure."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"

        # First two calls fail, third succeeds
        mock_sync_memory.add.side_effect = [
            Exception("Connection error"),
            Exception("Network timeout"),
            [{"id": "mem_123", "content": "test memory"}],
        ]

        # Execute
        result = sync_memory_service.add(messages, user_id)

        # Verify
        assert result == [{"id": "mem_123", "content": "test memory"}]
        assert mock_sync_memory.add.call_count == 3

    def test_add_failure_after_retries(self, sync_memory_service, mock_sync_memory):
        """Test failure after all retries exhausted."""
        # Setup
        messages = [{"role": "user", "content": "test message"}]
        user_id = "test_user"

        # All calls fail
        mock_sync_memory.add.side_effect = Exception("Persistent connection error")

        # Execute & Verify
        with pytest.raises(MemoryServiceConnectionError):
            sync_memory_service.add(messages, user_id)

        assert mock_sync_memory.add.call_count == 3

    def test_search_success(self, sync_memory_service, mock_sync_memory):
        """Test successful memory search."""
        # Setup
        query = "test query"
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_sync_memory.search.return_value = expected_result

        # Execute
        result = sync_memory_service.search(query, user_id)

        # Verify
        assert result == expected_result
        mock_sync_memory.search.assert_called_once_with(query, user_id=user_id)

    def test_search_retry_on_failure(self, sync_memory_service, mock_sync_memory):
        """Test retry logic on search failure."""
        # Setup
        query = "test query"
        user_id = "test_user"

        # First call fails, second succeeds
        mock_sync_memory.search.side_effect = [
            Exception("timeout error"),
            [{"id": "mem_123", "content": "test memory"}],
        ]

        # Execute
        result = sync_memory_service.search(query, user_id)

        # Verify
        assert result == [{"id": "mem_123", "content": "test memory"}]
        assert mock_sync_memory.search.call_count == 2

    def test_get_all_success(self, sync_memory_service, mock_sync_memory):
        """Test successful get all memories."""
        # Setup
        user_id = "test_user"
        expected_result = [{"id": "mem_123", "content": "test memory"}]
        mock_sync_memory.get_all.return_value = expected_result

        # Execute
        result = sync_memory_service.get_all(user_id)

        # Verify
        assert result == expected_result
        mock_sync_memory.get_all.assert_called_once_with(user_id=user_id)

    def test_delete_success(self, sync_memory_service, mock_sync_memory):
        """Test successful memory deletion."""
        # Setup
        memory_id = "mem_123"
        expected_result = {"message": "Memory deleted successfully"}
        mock_sync_memory.delete.return_value = expected_result

        # Execute
        result = sync_memory_service.delete(memory_id)

        # Verify
        assert result == expected_result
        mock_sync_memory.delete.assert_called_once_with(memory_id)

    def test_delete_all_success(self, sync_memory_service, mock_sync_memory):
        """Test successful delete all memories."""
        # Setup
        user_id = "test_user"
        expected_result = {"message": "All memories deleted successfully"}
        mock_sync_memory.delete_all.return_value = expected_result

        # Execute
        result = sync_memory_service.delete_all(user_id)

        # Verify
        assert result == expected_result
        mock_sync_memory.delete_all.assert_called_once_with(user_id=user_id)


class TestRetryBehavior:
    """Test retry behavior and configuration."""

    @pytest.mark.asyncio
    async def test_retry_stops_after_max_attempts(self):
        """Test that retries stop after maximum attempts."""
        mock_memory = AsyncMock()
        mock_memory.add.side_effect = Exception("Persistent error")

        with patch(
            "mcp_mitm_mem0.memory_service.AsyncMemory", return_value=mock_memory
        ):
            service = AsyncMemoryService()

            with pytest.raises(MemoryServiceError):
                await service.add([{"role": "user", "content": "test"}], "user_id")

            # Should attempt 3 times (initial + 2 retries)
            assert mock_memory.add.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff behavior (timing not verified, just structure)."""
        mock_memory = AsyncMock()
        # First two fail, third succeeds
        mock_memory.search.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            [{"id": "mem_123"}],
        ]

        with patch(
            "mcp_mitm_mem0.memory_service.AsyncMemory", return_value=mock_memory
        ):
            service = AsyncMemoryService()

            result = await service.search("test", "user_id")

            assert result == [{"id": "mem_123"}]
            assert mock_memory.search.call_count == 3


class TestLoggingBehavior:
    """Test structured logging behavior."""

    @pytest.mark.asyncio
    async def test_logging_on_success(self):
        """Test that successful operations are logged."""
        mock_memory = AsyncMock()
        mock_memory.add.return_value = [{"id": "mem_123"}]

        with patch(
            "mcp_mitm_mem0.memory_service.AsyncMemory", return_value=mock_memory
        ), patch("mcp_mitm_mem0.memory_service.logger") as mock_logger:
            service = AsyncMemoryService()

            await service.add([{"role": "user", "content": "test"}], "user_id")

            # Verify info logging was called
            assert (
                mock_logger.bind.return_value.info.call_count >= 2
            )  # start and success

    @pytest.mark.asyncio
    async def test_logging_on_failure(self):
        """Test that failed operations are logged."""
        mock_memory = AsyncMock()
        mock_memory.add.side_effect = Exception("Test error")

        with patch(
            "mcp_mitm_mem0.memory_service.AsyncMemory", return_value=mock_memory
        ), patch("mcp_mitm_mem0.memory_service.logger") as mock_logger:
            service = AsyncMemoryService()

            with pytest.raises(MemoryServiceError):
                await service.add([{"role": "user", "content": "test"}], "user_id")

            # Verify error logging was called
            mock_logger.bind.return_value.error.assert_called()
