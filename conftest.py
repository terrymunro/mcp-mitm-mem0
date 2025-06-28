#!/usr/bin/env python3
"""
Project-level pytest configuration and shared fixtures.

This module provides shared fixtures used across multiple test modules:
- mock_memory_service: Mock memory service for testing
"""

from unittest.mock import AsyncMock

import pytest

# Don't import MemoryService directly to avoid API key validation


@pytest.fixture
def mock_memory_service():
    """Create mock memory service.

    This fixture creates a mock MemoryService for testing.
    The mock can be configured in individual tests to return specific
    values or raise exceptions.

    Returns:
        AsyncMock: Mock memory service
    """
    return AsyncMock()
