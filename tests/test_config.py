#!/usr/bin/env python3
"""
Simple test to verify memory service configuration works.
"""

import asyncio

from mem0.configs.base import LlmConfig, MemoryConfig

from mcp_mitm_mem0.memory_service import AsyncMemoryService


async def test_memory_service():
    """Test basic memory service functionality."""
    try:
        # Create a simple config (this won't actually work without valid API keys)
        llm_config = LlmConfig(provider="openai", config={"model": "gpt-4", "api_key": "test-key"})
        memory_config = MemoryConfig(llm=llm_config)

        # This should initialize without error
        memory_service = AsyncMemoryService(config=memory_config)
        print("✅ Memory service initialized successfully")

        # Test that the service has the expected interface
        assert hasattr(memory_service, "add")
        assert hasattr(memory_service, "search")
        assert hasattr(memory_service, "get_all")
        assert hasattr(memory_service, "delete")
        assert hasattr(memory_service, "delete_all")
        print("✅ Memory service has all required methods")

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_memory_service())
