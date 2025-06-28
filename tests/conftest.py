"""
Shared test fixtures and utilities for comprehensive testing.

Provides reusable mocks, test data, and common patterns.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def mock_settings():
    """Standard settings mock with test configuration."""
    with patch("mcp_mitm_mem0.config.settings") as mock:
        mock.mem0_api_key = "test-api-key"
        mock.default_user_id = "test-user"
        mock.mcp_name = "mcp-mitm-mem0"
        mock.debug = False
        mock.mitm_host = "localhost"
        mock.mitm_port = 8080
        yield mock


@pytest.fixture
def mock_memory_clients():
    """Mocked async and sync Mem0 clients with standard behavior."""
    with (
        patch("mcp_mitm_mem0.memory_service.AsyncMemoryClient") as mock_async_class,
        patch("mcp_mitm_mem0.memory_service.MemoryClient") as mock_sync_class,
    ):
        mock_async_instance = AsyncMock()
        mock_sync_instance = Mock()
        mock_async_class.return_value = mock_async_instance
        mock_sync_class.return_value = mock_sync_instance
        yield mock_async_class, mock_sync_class


@pytest.fixture
def memory_service_mocked(mock_settings, mock_memory_clients):
    """MemoryService instance with mocked dependencies."""
    from mcp_mitm_mem0.memory_service import MemoryService

    mock_async_class, mock_sync_class = mock_memory_clients
    service = MemoryService()
    service.async_client = mock_async_class.return_value
    service.sync_client = mock_sync_class.return_value
    return service


@pytest.fixture
def sample_memories():
    """Standard test memory data with varied content."""
    return [
        {
            "id": "mem1",
            "memory": "How do I implement a function to parse JSON data?",
            "created_at": "2024-01-04T10:00:00Z",
        },
        {
            "id": "mem2", 
            "memory": "How do I debug this class that handles file uploads?",
            "created_at": "2024-01-03T09:00:00Z",
        },
        {
            "id": "mem3",
            "memory": "What's the best approach to implement error handling?", 
            "created_at": "2024-01-02T08:00:00Z",
        },
        {
            "id": "mem4",
            "memory": "How can I optimize this function?",
            "created_at": "2024-01-01T08:00:00Z",
        },
    ]


@pytest.fixture
def sample_messages():
    """Standard test message data."""
    return [
        {"role": "user", "content": "How do I implement a Python function?"},
        {"role": "assistant", "content": "Here's how to create a function in Python..."},
        {"role": "user", "content": "Can you show me an example?"},
    ]


@pytest.fixture
def reflection_agent_mocked():
    """ReflectionAgent instance for testing."""
    from mcp_mitm_mem0.reflection_agent import ReflectionAgent
    
    return ReflectionAgent(review_threshold=3)


@pytest.fixture
def mock_mcp_dependencies():
    """Mock all MCP server dependencies."""
    with (
        patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_memory,
        patch("mcp_mitm_mem0.mcp_server.reflection_agent") as mock_agent,
        patch("mcp_mitm_mem0.mcp_server.settings") as mock_settings,
    ):
        mock_settings.default_user_id = "default-user"
        
        # Setup default AsyncMock behaviors
        mock_memory.search_memories = AsyncMock(return_value=[])
        mock_memory.get_all_memories = AsyncMock(return_value=[])
        mock_memory.add_memory = AsyncMock(return_value={"id": "test-mem"})
        mock_memory.delete_memory = AsyncMock(return_value={"status": "deleted"})
        
        mock_agent.analyze_recent_conversations = AsyncMock(return_value={"status": "no_memories", "insights": []})
        mock_agent.suggest_next_steps = AsyncMock(return_value=[])
        
        yield mock_memory, mock_agent, mock_settings