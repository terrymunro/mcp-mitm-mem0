"""
Comprehensive tests for ReflectionAgent.

Tests pattern analysis, insight generation, and suggestion logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_mitm_mem0.reflection_agent import ReflectionAgent


class TestReflectionAgent:
    """Test ReflectionAgent functionality comprehensively."""

    def test_reflection_agent_initialization(self):
        """Test agent initialization with custom threshold."""
        agent = ReflectionAgent(review_threshold=3)
        assert agent.review_threshold == 3
        assert agent._processed_memory_ids == set()

    def test_reflection_agent_default_threshold(self):
        """Test default threshold value."""
        agent = ReflectionAgent()
        assert agent.review_threshold == 5

    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_no_memories(self, reflection_agent_mocked):
        """Test analysis when no memories exist."""
        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(return_value=[])

            result = await reflection_agent_mocked.analyze_recent_conversations("test_user")

            assert result["status"] == "no_memories"
            assert result["insights"] == []
            mock_service.get_all_memories.assert_called_once_with(user_id="test_user")

    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_with_coding_patterns(
        self, reflection_agent_mocked, sample_memories
    ):
        """Test analysis detecting coding-focused conversations."""
        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(return_value=sample_memories)
            mock_service.add_memory = AsyncMock(return_value={"id": "reflection_mem"})

            result = await reflection_agent_mocked.analyze_recent_conversations("test_user")

            assert result["status"] == "analyzed"
            assert result["memory_count"] == 4
            assert len(result["insights"]) > 0

            # Check for coding focus insight
            focus_insights = [i for i in result["insights"] if i["type"] == "focus_area"]
            assert len(focus_insights) == 1
            assert "coding" in focus_insights[0]["description"]

            # Check for frequent questions insight
            question_insights = [i for i in result["insights"] if i["type"] == "frequent_questions"]
            assert len(question_insights) == 1

            # Verify reflection was stored
            mock_service.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_patterns_coding_keywords(self, reflection_agent_mocked, sample_memories):
        """Test pattern analysis identifies coding keywords correctly."""
        insights = await reflection_agent_mocked._analyze_patterns(sample_memories)

        # Should detect coding focus
        focus_insights = [i for i in insights if i["type"] == "focus_area"]
        assert len(focus_insights) == 1
        assert "coding" in focus_insights[0]["description"]

        # Should detect frequent questions (4 questions with '?')
        question_insights = [i for i in insights if i["type"] == "frequent_questions"]
        assert len(question_insights) == 1
        assert "4 questions" in question_insights[0]["description"]

    @pytest.mark.asyncio
    async def test_analyze_patterns_problem_solving(self, reflection_agent_mocked):
        """Test detection of problem-solving patterns."""
        memories_with_approaches = [
            {"memory": "Let me try this approach to solve the issue"},
            {"memory": "I'll attempt a different solution here"},
            {"memory": "What's another approach we could try?"},
        ]

        insights = await reflection_agent_mocked._analyze_patterns(memories_with_approaches)

        problem_solving_insights = [i for i in insights if i["type"] == "problem_solving_pattern"]
        assert len(problem_solving_insights) == 1
        assert "iterative problem solving" in problem_solving_insights[0]["description"]

    @pytest.mark.asyncio
    async def test_analyze_patterns_no_clear_patterns(self, reflection_agent_mocked):
        """Test analysis when no clear patterns exist."""
        no_pattern_memories = [
            {"memory": "Hello there", "created_at": "2024-01-01T10:00:00Z"},
            {"memory": "How is the weather today", "created_at": "2024-01-01T09:00:00Z"},
        ]
        
        insights = await reflection_agent_mocked._analyze_patterns(no_pattern_memories)

        # Should not generate insights for unclear patterns
        assert len(insights) == 0

    @pytest.mark.asyncio
    async def test_analyze_patterns_memory_content_variations(self, reflection_agent_mocked):
        """Test handling different memory content formats."""
        varied_memories = [
            {"memory": "Standard content here"},
            {"content": "Alternative content field"},
            {"memory": None},  # None value
            {"other_field": "No memory/content field"},
            {},  # Empty dict
        ]

        # Should not crash with varied content formats
        insights = await reflection_agent_mocked._analyze_patterns(varied_memories)
        assert isinstance(insights, list)

    @pytest.mark.asyncio
    async def test_store_reflection_creates_proper_memory(self, reflection_agent_mocked):
        """Test that reflection storage creates properly formatted memory."""
        insights = [
            {
                "type": "focus_area",
                "description": "Primary focus on coding",
                "recommendation": "Consider more coding resources",
            },
            {
                "type": "frequent_questions",
                "description": "Many questions asked",
                "examples": ["How do I?", "What is?", "Where can I?"],
            },
        ]

        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.add_memory = AsyncMock(return_value={"id": "reflection_mem"})

            result = await reflection_agent_mocked._store_reflection(insights, "test_user")

            assert result["id"] == "reflection_mem"

            # Verify the call structure
            call_args = mock_service.add_memory.call_args
            assert call_args[1]["user_id"] == "test_user"
            assert len(call_args[1]["messages"]) == 2
            assert call_args[1]["messages"][0]["role"] == "system"
            assert call_args[1]["messages"][1]["role"] == "assistant"
            assert "Focus Area" in call_args[1]["messages"][1]["content"]
            assert call_args[1]["metadata"]["type"] == "reflection"

    @pytest.mark.asyncio
    async def test_suggest_next_steps_with_insights(self, reflection_agent_mocked):
        """Test suggestion generation based on insights."""
        with patch.object(reflection_agent_mocked, "analyze_recent_conversations") as mock_analyze:
            mock_analyze.return_value = {
                "insights": [
                    {"type": "frequent_questions", "description": "Many questions"},
                    {"type": "focus_area", "description": "Primary focus on coding (mentioned 5 times)"},
                    {"type": "problem_solving_pattern", "description": "Multiple approaches"},
                ]
            }

            suggestions = await reflection_agent_mocked.suggest_next_steps("test_user")

            assert len(suggestions) == 3
            assert any("FAQ" in s for s in suggestions)
            assert any("coding" in s for s in suggestions)
            assert any("breaking down" in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_next_steps_no_insights(self, reflection_agent_mocked):
        """Test suggestion generation when no insights available."""
        with patch.object(reflection_agent_mocked, "analyze_recent_conversations") as mock_analyze:
            mock_analyze.return_value = {"insights": []}

            suggestions = await reflection_agent_mocked.suggest_next_steps("test_user")

            assert suggestions == []

    @pytest.mark.asyncio
    async def test_suggest_next_steps_handles_analysis_errors(self, reflection_agent_mocked):
        """Test suggestion generation handles analysis errors gracefully."""
        with patch.object(reflection_agent_mocked, "analyze_recent_conversations") as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")

            suggestions = await reflection_agent_mocked.suggest_next_steps("test_user")

            assert suggestions == []

    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_limits_results(self, reflection_agent_mocked):
        """Test that analysis respects the limit parameter."""
        many_memories = [
            {
                "id": f"mem{i}",
                "memory": f"Memory {i}",
                "created_at": f"2024-01-{i:02d}T10:00:00Z",
            }
            for i in range(1, 26)  # 25 memories
        ]

        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(return_value=many_memories)
            mock_service.add_memory = AsyncMock(return_value={"id": "reflection_mem"})

            # Request only 10 recent memories
            result = await reflection_agent_mocked.analyze_recent_conversations("test_user", limit=10)

            assert result["memory_count"] == 10

    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_sorts_by_date(self, reflection_agent_mocked):
        """Test that analysis gets most recent memories first."""
        unsorted_memories = [
            {"id": "old", "memory": "Old memory", "created_at": "2024-01-01T10:00:00Z"},
            {"id": "new", "memory": "New memory", "created_at": "2024-01-03T10:00:00Z"},
            {"id": "mid", "memory": "Mid memory", "created_at": "2024-01-02T10:00:00Z"},
        ]

        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(return_value=unsorted_memories)
            mock_service.add_memory = AsyncMock(return_value={"id": "reflection_mem"})

            # Mock the _analyze_patterns to track what memories it receives
            with patch.object(reflection_agent_mocked, "_analyze_patterns") as mock_patterns:
                mock_patterns.return_value = []

                await reflection_agent_mocked.analyze_recent_conversations("test_user")

                # Check that memories were sorted by date (newest first)
                analyzed_memories = mock_patterns.call_args[0][0]
                assert analyzed_memories[0]["id"] == "new"
                assert analyzed_memories[1]["id"] == "mid"
                assert analyzed_memories[2]["id"] == "old"

    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_uses_default_user_id(self, reflection_agent_mocked):
        """Test that default user ID is used when none provided."""
        with (
            patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service,
            patch("mcp_mitm_mem0.reflection_agent.settings") as mock_settings,
        ):
            mock_settings.default_user_id = "default_user"
            mock_service.get_all_memories = AsyncMock(return_value=[])

            await reflection_agent_mocked.analyze_recent_conversations()

            mock_service.get_all_memories.assert_called_once_with(user_id="default_user")

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_analyze_recent_conversations_handles_api_errors(self, reflection_agent_mocked):
        """Test error handling when memory service fails."""
        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.get_all_memories = AsyncMock(side_effect=Exception("API Error"))

            with pytest.raises(Exception, match="API Error"):
                await reflection_agent_mocked.analyze_recent_conversations("test_user")

    @pytest.mark.asyncio
    async def test_store_reflection_handles_storage_errors(self, reflection_agent_mocked):
        """Test error handling when reflection storage fails."""
        insights = [{"type": "test", "description": "Test insight"}]

        with patch("mcp_mitm_mem0.reflection_agent.memory_service") as mock_service:
            mock_service.add_memory = AsyncMock(side_effect=Exception("Storage failed"))

            with pytest.raises(Exception, match="Storage failed"):
                await reflection_agent_mocked._store_reflection(insights, "test_user")

    # Edge Cases
    @pytest.mark.asyncio
    async def test_unicode_memory_content_handling(self, reflection_agent_mocked):
        """Test handling of unicode content in memories."""
        unicode_memories = [
            {"memory": "How do I implement 函数 in Python? 🐍"},
            {"memory": "Debugging this クラス for file uploads"},
            {"memory": "Best approach for エラー handling?"},
        ]

        insights = await reflection_agent_mocked._analyze_patterns(unicode_memories)

        # Should handle unicode content without crashing
        assert isinstance(insights, list)
        # Should still detect patterns despite unicode
        focus_insights = [i for i in insights if i["type"] == "focus_area"]
        assert len(focus_insights) > 0

    @pytest.mark.asyncio
    async def test_empty_memory_strings_handling(self, reflection_agent_mocked):
        """Test handling of empty or whitespace-only memory content."""
        edge_case_memories = [
            {"memory": ""},  # Empty string
            {"memory": "   "},  # Whitespace only
            {"memory": "\n\t\r"},  # Whitespace characters
            {"memory": "Valid content here"},
        ]

        # Should not crash with edge case content
        insights = await reflection_agent_mocked._analyze_patterns(edge_case_memories)
        assert isinstance(insights, list)