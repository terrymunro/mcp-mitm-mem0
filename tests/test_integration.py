"""
Integration tests for component interactions.

Tests how MCP server, memory service, and reflection agent work together.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestComponentIntegration:
    """Test integration between major components."""

    @pytest.mark.asyncio
    async def test_mcp_server_memory_service_integration(self, sample_messages):
        """Test MCP server tools integrate correctly with memory service."""
        from mcp_mitm_mem0.mcp_server import add_memory, search_memories

        # Test the full flow: add memory then search for it
        with patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_service:
            # Setup mocks for add and search
            mock_service.add_memory = AsyncMock(return_value={"id": "integration-mem-123"})
            mock_service.search_memories = AsyncMock(
                return_value=[{"id": "integration-mem-123", "content": "Test integration memory"}]
            )

            # Add a memory
            add_result = await add_memory(sample_messages, "integration_user")

            # Search for the memory
            search_result = await search_memories("integration test", "integration_user")

            # Verify the flow
            assert add_result["id"] == "integration-mem-123"
            assert len(search_result) == 1
            assert search_result[0]["id"] == "integration-mem-123"

            # Verify service calls
            mock_service.add_memory.assert_called_once_with(
                messages=sample_messages, user_id="integration_user", metadata=None
            )
            mock_service.search_memories.assert_called_once_with(
                query="integration test", user_id="integration_user", limit=10
            )

    @pytest.mark.asyncio
    async def test_reflection_agent_memory_service_integration(self):
        """Test reflection agent integrates correctly with memory service."""
        from mcp_mitm_mem0.reflection_agent import ReflectionAgent

        agent = ReflectionAgent(review_threshold=3)

        # Mock memory service with sample conversation data
        sample_memories = [
            {
                "id": "mem1",
                "memory": "How do I implement a function in Python?",
                "created_at": "2024-01-03T10:00:00Z",
            },
            {
                "id": "mem2",
                "memory": "Can you help me debug this class?",
                "created_at": "2024-01-02T09:00:00Z",
            },
            {
                "id": "mem3",
                "memory": "What's the best approach to handle errors?",
                "created_at": "2024-01-01T08:00:00Z",
            },
        ]

        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(return_value=sample_memories)
            mock_service.add_memory = AsyncMock(return_value={"id": "reflection-mem-456"})

            # Analyze conversations
            result = await agent.analyze_recent_conversations("integration_user")

            # Verify analysis results
            assert result["status"] == "analyzed"
            assert result["memory_count"] == 3
            assert len(result["insights"]) > 0

            # Verify memory service interactions
            mock_service.get_all_memories.assert_called_once_with(user_id="integration_user")
            mock_service.add_memory.assert_called_once()  # Reflection stored

            # Verify reflection memory was created
            reflection_call = mock_service.add_memory.call_args
            assert reflection_call[1]["user_id"] == "integration_user"
            assert reflection_call[1]["metadata"]["type"] == "reflection"

    @pytest.mark.asyncio
    async def test_mcp_server_reflection_agent_integration(self):
        """Test MCP server analyze tool integrates with reflection agent."""
        from mcp_mitm_mem0.mcp_server import analyze_conversations, suggest_next_actions

        with patch("mcp_mitm_mem0.mcp_server.reflection_agent") as mock_agent:
            # Mock analysis results
            mock_agent.analyze_recent_conversations = AsyncMock(
                return_value={
                    "status": "analyzed",
                    "memory_count": 5,
                    "insights": [
                        {"type": "focus_area", "description": "Primary focus on coding"},
                        {"type": "frequent_questions", "description": "Many questions asked"},
                    ],
                }
            )

            # Mock suggestions
            mock_agent.suggest_next_steps = AsyncMock(
                return_value=[
                    "Consider creating a coding reference guide",
                    "Set up a FAQ for common questions",
                ]
            )

            # Test conversation analysis
            analysis_result = await analyze_conversations("integration_user", limit=15)

            # Test suggestion generation
            suggestions_result = await suggest_next_actions("integration_user")

            # Verify results
            assert analysis_result["status"] == "analyzed"
            assert analysis_result["memory_count"] == 5
            assert len(analysis_result["insights"]) == 2

            assert len(suggestions_result) == 2
            assert "coding reference" in suggestions_result[0]
            assert "FAQ" in suggestions_result[1]

            # Verify agent calls
            mock_agent.analyze_recent_conversations.assert_called_once_with(
                user_id="integration_user", limit=15
            )
            mock_agent.suggest_next_steps.assert_called_once_with(user_id="integration_user")

    @pytest.mark.asyncio
    async def test_end_to_end_memory_workflow(self, sample_messages):
        """Test complete end-to-end memory workflow."""
        from mcp_mitm_mem0.mcp_server import (
            add_memory,
            analyze_conversations,
            search_memories,
        )

        # Simulate a complete workflow:
        # 1. Add several memories
        # 2. Search for them  
        # 3. Analyze patterns
        # 4. Verify all components work together

        with (
            patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_memory_service,
            patch("mcp_mitm_mem0.mcp_server.reflection_agent") as mock_agent,
        ):
            # Setup memory service mocks
            memory_ids = ["mem1", "mem2", "mem3"]
            mock_memory_service.add_memory = AsyncMock(
                side_effect=[{"id": mid} for mid in memory_ids]
            )
            mock_memory_service.search_memories = AsyncMock(
                return_value=[
                    {"id": "mem1", "content": "Python coding question"},
                    {"id": "mem2", "content": "Debugging help needed"},
                ]
            )

            # Setup reflection agent mock
            mock_agent.analyze_recent_conversations = AsyncMock(
                return_value={
                    "status": "analyzed",
                    "memory_count": 3,
                    "insights": [{"type": "focus_area", "description": "Coding focus detected"}],
                }
            )

            # Step 1: Add memories
            conversations = [
                [{"role": "user", "content": "How do I write a Python function?"}],
                [{"role": "user", "content": "Can you help me debug this code?"}],
                [{"role": "user", "content": "What's the best coding practice?"}],
            ]

            add_results = []
            for i, messages in enumerate(conversations):
                result = await add_memory(messages, f"user_{i}")
                add_results.append(result)

            # Step 2: Search memories
            search_result = await search_memories("Python coding", "user_0")

            # Step 3: Analyze patterns
            analysis_result = await analyze_conversations("user_0")

            # Verify the complete workflow
            assert len(add_results) == 3
            assert all("id" in result for result in add_results)

            assert len(search_result) == 2
            assert "Python coding" in search_result[0]["content"]

            assert analysis_result["status"] == "analyzed"
            assert "Coding focus" in analysis_result["insights"][0]["description"]

            # Verify all service calls were made
            assert mock_memory_service.add_memory.call_count == 3
            mock_memory_service.search_memories.assert_called_once()
            mock_agent.analyze_recent_conversations.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_propagation_across_components(self):
        """Test that errors propagate correctly between components."""
        from mcp_mitm_mem0.mcp_server import analyze_conversations, search_memories

        # Test memory service error propagation
        with patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_service:
            mock_service.search_memories = AsyncMock(side_effect=Exception("Memory service down"))

            with pytest.raises(RuntimeError, match="Search failed: Memory service down"):
                await search_memories("test", "user")

        # Test reflection agent error propagation
        with patch("mcp_mitm_mem0.mcp_server.reflection_agent") as mock_agent:
            mock_agent.analyze_recent_conversations = AsyncMock(
                side_effect=Exception("Analysis failed")
            )

            with pytest.raises(RuntimeError, match="Analysis failed: Analysis failed"):
                await analyze_conversations("user")

    @pytest.mark.asyncio
    async def test_configuration_consistency_across_components(self):
        """Test that configuration is used consistently across components."""
        from mcp_mitm_mem0.mcp_server import search_memories
        from mcp_mitm_mem0.reflection_agent import ReflectionAgent

        # Test that default user ID is used consistently
        with (
            patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_service,
            patch("mcp_mitm_mem0.mcp_server.settings") as mock_settings,
            patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_reflection_service,
            patch("mcp_mitm_mem0.reflection_agent.settings") as mock_reflection_settings,
        ):
            # Setup consistent settings
            mock_settings.default_user_id = "consistent_user"
            mock_reflection_settings.default_user_id = "consistent_user"

            mock_service.search_memories = AsyncMock(return_value=[])
            mock_reflection_service.get_all_memories = AsyncMock(return_value=[])

            # Test MCP server uses default user ID
            await search_memories("test", None)  # Explicit None for user_id
            # The MCP server passes None through, memory service handles default
            mock_service.search_memories.assert_called_once_with(
                query="test", user_id=None, limit=10
            )

            # Test reflection agent uses default user ID
            agent = ReflectionAgent()
            await agent.analyze_recent_conversations()  # No user_id provided
            mock_reflection_service.get_all_memories.assert_called_once_with(
                user_id="consistent_user"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sample_messages):
        """Test concurrent operations across components."""
        from mcp_mitm_mem0.mcp_server import add_memory, search_memories

        with patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_service:
            # Setup mocks with delays to simulate real API calls
            async def delayed_add(*args, **kwargs):
                await asyncio.sleep(0.01)  # Small delay
                return {"id": f"concurrent-{len(args)}"}

            async def delayed_search(*args, **kwargs):
                await asyncio.sleep(0.01)  # Small delay
                return [{"id": "found", "content": "concurrent result"}]

            mock_service.add_memory = AsyncMock(side_effect=delayed_add)
            mock_service.search_memories = AsyncMock(side_effect=delayed_search)

            # Run concurrent operations
            tasks = [
                add_memory([{"role": "user", "content": "Message 1"}], "user1"),
                add_memory([{"role": "user", "content": "Message 2"}], "user2"),
                search_memories("concurrent", "user1"),
                search_memories("test", "user2"),
            ]

            results = await asyncio.gather(*tasks)

            # Verify all operations completed
            assert len(results) == 4
            # Both add_memory calls should succeed with some ID
            assert "id" in results[0]  # add_memory result
            assert "id" in results[1]  # add_memory result
            assert len(results[2]) == 1  # search result
            assert len(results[3]) == 1  # search result

            # Verify all service calls were made
            assert mock_service.add_memory.call_count == 2
            assert mock_service.search_memories.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_lifecycle_integration(self):
        """Test complete memory lifecycle across components."""
        from mcp_mitm_mem0.mcp_server import (
            add_memory,
            analyze_conversations,
            delete_memory,
            search_memories,
        )

        # Test: Add -> Search -> Analyze -> Delete workflow
        with (
            patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_service,
            patch("mcp_mitm_mem0.mcp_server.reflection_agent") as mock_agent,
        ):
            # Setup mocks
            mock_service.add_memory = AsyncMock(return_value={"id": "lifecycle-mem"})
            mock_service.search_memories = AsyncMock(
                return_value=[{"id": "lifecycle-mem", "content": "Lifecycle test"}]
            )
            mock_service.delete_memory = AsyncMock(return_value={"status": "deleted"})
            mock_agent.analyze_recent_conversations = AsyncMock(
                return_value={"status": "analyzed", "memory_count": 1, "insights": []}
            )

            # Step 1: Add memory
            add_result = await add_memory(
                [{"role": "user", "content": "Test lifecycle memory"}], "lifecycle_user"
            )

            # Step 2: Search for it
            search_result = await search_memories("lifecycle", "lifecycle_user")

            # Step 3: Analyze patterns
            analysis_result = await analyze_conversations("lifecycle_user")

            # Step 4: Delete memory
            delete_result = await delete_memory("lifecycle-mem")

            # Verify complete lifecycle
            assert add_result["id"] == "lifecycle-mem"
            assert len(search_result) == 1
            assert search_result[0]["id"] == "lifecycle-mem"
            assert analysis_result["status"] == "analyzed"
            assert delete_result["status"] == "deleted"

            # Verify all operations were called in sequence
            mock_service.add_memory.assert_called_once()
            mock_service.search_memories.assert_called_once()
            mock_agent.analyze_recent_conversations.assert_called_once()
            mock_service.delete_memory.assert_called_once_with(memory_id="lifecycle-mem")

    @pytest.mark.asyncio
    async def test_unicode_handling_across_components(self):
        """Test unicode content handling across all components."""
        from mcp_mitm_mem0.mcp_server import add_memory, search_memories
        from mcp_mitm_mem0.reflection_agent import ReflectionAgent

        unicode_content = "Testing 🤖 unicode characters 世界"
        unicode_user = "用户_🤖_123"

        with (
            patch("mcp_mitm_mem0.mcp_server.memory_service") as mock_memory_service,
            patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_reflection_service,
        ):
            # Setup mocks
            mock_memory_service.add_memory = AsyncMock(return_value={"id": "unicode-mem"})
            mock_memory_service.search_memories = AsyncMock(return_value=[])
            mock_reflection_service.get_all_memories = AsyncMock(
                return_value=[{"memory": unicode_content}]
            )
            mock_reflection_service.add_memory = AsyncMock(return_value={"id": "reflection"})

            # Test MCP server with unicode
            unicode_messages = [{"role": "user", "content": unicode_content}]
            add_result = await add_memory(unicode_messages, unicode_user)
            search_result = await search_memories(unicode_content, unicode_user)

            # Test reflection agent with unicode
            agent = ReflectionAgent()
            analysis_result = await agent.analyze_recent_conversations(unicode_user)

            # Verify unicode handling
            assert add_result["id"] == "unicode-mem"
            assert search_result == []
            assert isinstance(analysis_result, dict)

            # Verify unicode parameters were passed correctly
            mock_memory_service.add_memory.assert_called_once()
            add_call_args = mock_memory_service.add_memory.call_args
            assert add_call_args[1]["user_id"] == unicode_user
            assert add_call_args[1]["messages"][0]["content"] == unicode_content