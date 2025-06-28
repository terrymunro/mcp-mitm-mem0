#!/usr/bin/env python3
"""
Project-level pytest configuration and shared fixtures.

This module provides shared fixtures used across multiple test modules:
- async_client: AsyncClient for testing FastAPI endpoints
- disable_auth: Disables authentication for testing
- mock_memory_service: Mock memory service for testing
- base_url: Base URL fixture for tests
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from mcp_mitm_mem0.api import app
from mcp_mitm_mem0.memory_service import AsyncMemoryService
from tests.utils import get_async_client


@pytest_asyncio.fixture
async def async_client():
    """Create async test client.

    Returns:
        AsyncClient: Configured async client for testing FastAPI endpoints
    """
    client = await get_async_client(app)
    async with client as ac:
        yield ac


@pytest.fixture
def disable_auth():
    """Disable authentication for testing.

    This fixture patches the auth_token setting to None, effectively
    disabling authentication requirements for all endpoints during tests.

    Yields:
        Mock: Mocked settings object with auth_token set to None
    """
    with patch("mcp_mitm_mem0.api.settings") as mock_settings:
        mock_settings.auth_token = None
        yield mock_settings


@pytest.fixture
def mock_memory_service():
    """Create mock memory service.

    This fixture creates a mock AsyncMemoryService and patches it into
    the API module for testing. The mock can be configured in individual
    tests to return specific values or raise exceptions.

    Returns:
        AsyncMock: Mock memory service with AsyncMemoryService spec
    """
    mock_service = AsyncMock(spec=AsyncMemoryService)
    with patch("mcp_mitm_mem0.api.memory_service", mock_service):
        yield mock_service


@pytest.fixture
def base_url():
    """Base URL fixture for tests that expect it.

    Returns:
        str: Test base URL
    """
    return "http://test"
