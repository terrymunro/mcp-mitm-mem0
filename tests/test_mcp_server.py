"""
Comprehensive tests for MCP server tools and resources.

Tests all MCP tools, resources, and essential edge cases.
"""

from unittest.mock import AsyncMock

import pytest

from mcp_mitm_mem0.mcp_server import (
    add_memory,
    analyze_conversations,
    delete_memory,
    list_memories,
    search_memories,
    suggest_next_actions,
)


class TestMCPTools:
    """Test MCP server tools functionality."""

    @pytest.mark.asyncio
    async def test_search_memories_success(self, mock_mcp_dependencies, sample_memories):
        """Test successful memory search."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories = AsyncMock(return_value=sample_memories[:2])
        
        result = await search_memories("coding questions", "test-user", limit=2)
        
        assert len(result) == 2
        assert result[0]["id"] == "mem1"
        mock_memory.search_memories.assert_called_once_with(
            query="coding questions", user_id="test-user", limit=2
        )

    @pytest.mark.asyncio
    async def test_search_memories_with_defaults(self, mock_mcp_dependencies):
        """Test search with default parameters."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.return_value = []
        
        result = await search_memories("test query", "user")
        
        assert result == []
        mock_memory.search_memories.assert_called_once_with(
            query="test query", user_id="user", limit=10
        )

    @pytest.mark.asyncio
    async def test_list_memories_success(self, mock_mcp_dependencies, sample_memories):
        """Test successful memory listing."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.get_all_memories.return_value = sample_memories
        
        result = await list_memories("test-user")
        
        assert len(result) == 4
        assert result[0]["id"] == "mem1"
        mock_memory.get_all_memories.assert_called_once_with(user_id="test-user")

    @pytest.mark.asyncio
    async def test_add_memory_success(self, mock_mcp_dependencies, sample_messages):
        """Test successful memory addition."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.return_value = {"id": "new-mem-123"}
        
        result = await add_memory(sample_messages, "test-user")
        
        assert result["id"] == "new-mem-123"
        mock_memory.add_memory.assert_called_once_with(
            messages=sample_messages, user_id="test-user", metadata=None
        )

    @pytest.mark.asyncio
    async def test_add_memory_with_metadata(self, mock_mcp_dependencies):
        """Test memory addition with metadata."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.return_value = {"id": "meta-mem"}
        
        messages = [{"role": "user", "content": "Important message"}]
        metadata = {"priority": "high", "source": "manual"}
        
        result = await add_memory(messages, "test-user", metadata)
        
        assert result["id"] == "meta-mem"
        mock_memory.add_memory.assert_called_once_with(
            messages=messages, user_id="test-user", metadata=metadata
        )

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, mock_mcp_dependencies):
        """Test successful memory deletion."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.delete_memory.return_value = {"status": "deleted"}
        
        result = await delete_memory("mem-123")
        
        assert result["memory_id"] == "mem-123"
        assert result["status"] == "deleted"
        mock_memory.delete_memory.assert_called_once_with(memory_id="mem-123")

    @pytest.mark.asyncio
    async def test_analyze_conversations_success(self, mock_mcp_dependencies):
        """Test successful conversation analysis."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        analysis_result = {
            "status": "analyzed",
            "memory_count": 5,
            "insights": [
                {"type": "focus_area", "description": "Primary focus on coding"},
                {"type": "frequent_questions", "description": "Many questions asked"},
            ]
        }
        mock_agent.analyze_recent_conversations.return_value = analysis_result
        
        result = await analyze_conversations("test-user", limit=20)
        
        assert result["status"] == "analyzed"
        assert result["memory_count"] == 5
        assert len(result["insights"]) == 2
        mock_agent.analyze_recent_conversations.assert_called_once_with(
            user_id="test-user", limit=20
        )

    @pytest.mark.asyncio
    async def test_suggest_next_actions_success(self, mock_mcp_dependencies):
        """Test successful next action suggestions."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        suggestions = [
            "Consider creating a coding reference guide",
            "Set up a FAQ for common questions",
        ]
        mock_agent.suggest_next_steps.return_value = suggestions
        
        result = await suggest_next_actions("test-user")
        
        assert len(result) == 2
        assert "coding reference" in result[0]
        assert "FAQ" in result[1]
        mock_agent.suggest_next_steps.assert_called_once_with(user_id="test-user")

    # Essential Edge Cases
    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self, mock_mcp_dependencies):
        """Test search with empty query."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.return_value = []
        
        result = await search_memories("", "test-user")
        
        assert result == []
        mock_memory.search_memories.assert_called_once_with(
            query="", user_id="test-user", limit=10
        )

    @pytest.mark.asyncio
    async def test_search_memories_unicode_query(self, mock_mcp_dependencies):
        """Test search with unicode characters."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.return_value = []
        
        unicode_query = "🤖 search with émoji and spëcial chars"
        result = await search_memories(unicode_query, "test-user")
        
        assert result == []
        mock_memory.search_memories.assert_called_once_with(
            query=unicode_query, user_id="test-user", limit=10
        )

    @pytest.mark.asyncio
    async def test_add_memory_empty_messages(self, mock_mcp_dependencies):
        """Test adding memory with empty messages."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.return_value = {"id": "empty-mem"}
        
        result = await add_memory([], "test-user")
        
        assert result["id"] == "empty-mem"
        mock_memory.add_memory.assert_called_once_with(
            messages=[], user_id="test-user", metadata=None
        )

    @pytest.mark.asyncio
    async def test_add_memory_malformed_messages(self, mock_mcp_dependencies):
        """Test adding memory with malformed messages."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.return_value = {"id": "malformed-mem"}
        
        malformed_messages = [
            {"wrong_field": "value"},  # Missing role/content
            {"role": "user"},  # Missing content
            {"content": "text"},  # Missing role
            {},  # Empty dict
        ]
        
        result = await add_memory(malformed_messages, "test-user")
        
        assert result["id"] == "malformed-mem"

    @pytest.mark.asyncio
    async def test_delete_memory_empty_id(self, mock_mcp_dependencies):
        """Test delete with empty memory ID."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.delete_memory.return_value = {"status": "deleted"}
        
        result = await delete_memory("")
        
        assert result["memory_id"] == ""
        assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_list_memories_empty_user_id(self, mock_mcp_dependencies):
        """Test list memories with empty user ID."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.get_all_memories.return_value = []
        
        result = await list_memories("")
        
        assert result == []
        mock_memory.get_all_memories.assert_called_once_with(user_id="")

    @pytest.mark.asyncio
    async def test_analyze_conversations_zero_limit(self, mock_mcp_dependencies):
        """Test analysis with zero limit."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_agent.analyze_recent_conversations.return_value = {
            "status": "analyzed", "memory_count": 0, "insights": []
        }
        
        result = await analyze_conversations("test-user", limit=0)
        
        assert result["memory_count"] == 0
        mock_agent.analyze_recent_conversations.assert_called_once_with(
            user_id="test-user", limit=0
        )

    @pytest.mark.asyncio
    async def test_suggest_next_actions_empty_result(self, mock_mcp_dependencies):
        """Test suggestions when none available."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_agent.suggest_next_steps.return_value = []
        
        result = await suggest_next_actions("test-user")
        
        assert result == []

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_search_memories_api_failure(self, mock_mcp_dependencies):
        """Test search when memory service fails."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.side_effect = Exception("API timeout")
        
        with pytest.raises(RuntimeError, match="Search failed: API timeout"):
            await search_memories("test query", "test-user")

    @pytest.mark.asyncio
    async def test_list_memories_api_failure(self, mock_mcp_dependencies):
        """Test list when memory service fails."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.get_all_memories.side_effect = Exception("Connection error")
        
        with pytest.raises(RuntimeError, match="List failed: Connection error"):
            await list_memories("test-user")

    @pytest.mark.asyncio
    async def test_add_memory_api_failure(self, mock_mcp_dependencies):
        """Test add memory when service fails."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(RuntimeError, match="Add failed: Rate limit exceeded"):
            await add_memory([{"role": "user", "content": "test"}], "test-user")

    @pytest.mark.asyncio
    async def test_delete_memory_api_failure(self, mock_mcp_dependencies):
        """Test delete when memory not found."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.delete_memory.side_effect = Exception("Memory not found")
        
        with pytest.raises(RuntimeError, match="Delete failed: Memory not found"):
            await delete_memory("nonexistent-id")

    @pytest.mark.asyncio
    async def test_analyze_conversations_api_failure(self, mock_mcp_dependencies):
        """Test analysis when reflection agent fails."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_agent.analyze_recent_conversations.side_effect = Exception("Analysis service down")
        
        with pytest.raises(RuntimeError, match="Analysis failed: Analysis service down"):
            await analyze_conversations("test-user")

    @pytest.mark.asyncio
    async def test_suggest_next_actions_api_failure(self, mock_mcp_dependencies):
        """Test suggestions when reflection agent fails."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_agent.suggest_next_steps.side_effect = Exception("Suggestion engine error")
        
        with pytest.raises(RuntimeError, match="Failed to generate suggestions: Suggestion engine error"):
            await suggest_next_actions("test-user")

    # Default User ID Handling
    @pytest.mark.asyncio
    async def test_tools_use_none_for_default_user(self, mock_mcp_dependencies):
        """Test that tools pass None through for default user handling."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.return_value = []
        
        # MCP server passes None through, memory service handles default
        result = await search_memories("test query", None)
        
        assert result == []
        mock_memory.search_memories.assert_called_once_with(
            query="test query", user_id=None, limit=10
        )

    @pytest.mark.asyncio
    async def test_message_order_preservation(self, mock_mcp_dependencies):
        """Test that message order is preserved."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.add_memory.return_value = {"id": "ordered-mem"}
        
        ordered_messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Second message"},
            {"role": "user", "content": "Third message"},
        ]
        
        await add_memory(ordered_messages, "test-user")
        
        # Verify exact message order was passed
        call_args = mock_memory.add_memory.call_args
        passed_messages = call_args[1]["messages"]
        assert passed_messages == ordered_messages

    @pytest.mark.asyncio
    async def test_unicode_user_ids(self, mock_mcp_dependencies):
        """Test handling of unicode user IDs."""
        mock_memory, mock_agent, mock_settings = mock_mcp_dependencies
        mock_memory.search_memories.return_value = []
        
        unicode_user_id = "用户_🤖_123"
        result = await search_memories("test", unicode_user_id)
        
        assert result == []
        mock_memory.search_memories.assert_called_once_with(
            query="test", user_id=unicode_user_id, limit=10
        )