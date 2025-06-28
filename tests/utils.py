#!/usr/bin/env python3
"""Test utilities for MCP MITM Mem0 tests.

This module provides helper functions and fixtures for testing FastAPI applications
with httpx AsyncClient, resolving compatibility issues with newer httpx versions.
"""

from httpx import ASGITransport, AsyncClient


async def get_async_client(app):
    """Create an AsyncClient with proper ASGI transport configuration.

    This helper resolves the "AsyncClient.__init__ got unexpected keyword argument 'app'"
    error by using the proper ASGITransport configuration for newer httpx versions.

    Args:
        app: The FastAPI application instance to test

    Returns:
        AsyncClient: Configured async client for testing
    """
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
