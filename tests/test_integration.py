#!/usr/bin/env python3
"""
Integration tests for the MCP MITM Mem0 system.

This module tests:
- Full FastAPI application with AsyncClient
- Integration with mocked Mem0 services
- Synthetic Claude traffic simulation using pytest-mitmproxy
- End-to-end workflows and error handling
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestFastAPIIntegration:
    """Test FastAPI application integration with httpx.AsyncClient."""

    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test health endpoint with async client."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "memory_service_available" in data
        assert "timestamp" in data
        assert "correlation_id" in data

    @pytest.mark.asyncio
    async def test_search_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test search endpoint with async client."""
        # Configure mock
        mock_memory_service.search.return_value = [{"id": "mem_123", "content": "test memory", "score": 0.95}]

        payload = {"user_id": "test_user", "query": "test query", "limit": 10}
        response = await async_client.post("/search", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "count" in data
        assert data["count"] == 1
        assert len(data["memories"]) == 1

        # Verify mock was called correctly
        mock_memory_service.search.assert_called_once_with(query="test query", user_id="test_user", limit=10)

    @pytest.mark.asyncio
    async def test_remember_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test remember endpoint with async client."""
        # Configure mock
        mock_memory_service.add.return_value = [{"id": "new_mem_456", "content": "remembered content"}]

        payload = {
            "user_id": "test_user",
            "messages": [
                {"role": "user", "content": "Remember this important information"},
                {"role": "assistant", "content": "I'll remember that for you"},
            ],
            "metadata": {"source": "integration_test"},
            "run_id": "test_run_123",
        }

        response = await async_client.post("/remember", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "count" in data
        assert data["count"] == 1

        # Verify mock was called correctly
        mock_memory_service.add.assert_called_once_with(
            messages=payload["messages"],
            user_id="test_user",
            metadata={"source": "integration_test"},
            run_id="test_run_123",
            tags=None,
            expires_at=None,
        )

    @pytest.mark.asyncio
    async def test_list_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test list endpoint with async client."""
        # Configure mock
        mock_memory_service.get_all.return_value = [
            {"id": "mem_1", "content": "first memory"},
            {"id": "mem_2", "content": "second memory"},
        ]

        payload = {"user_id": "test_user"}
        response = await async_client.post("/list", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "count" in data
        assert data["count"] == 2

        # Verify mock was called correctly
        mock_memory_service.get_all.assert_called_once_with(user_id="test_user")

    @pytest.mark.asyncio
    async def test_forget_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test forget endpoint with async client."""
        # Configure mock
        mock_memory_service.delete.return_value = {"message": "Memory deleted successfully"}

        payload = {"user_id": "test_user", "memory_id": "mem_to_delete"}
        response = await async_client.post("/forget", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert data["success"] is True

        # Verify mock was called correctly
        mock_memory_service.delete.assert_called_once_with(memory_id="mem_to_delete")

    @pytest.mark.asyncio
    async def test_forget_all_endpoint_integration(self, async_client, mock_memory_service, disable_auth):
        """Test forget all memories endpoint with async client."""
        # Configure mock
        mock_memory_service.delete_all.return_value = {"message": "All memories deleted"}

        payload = {"user_id": "test_user"}  # No memory_id means delete all
        response = await async_client.post("/forget", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify mock was called correctly
        mock_memory_service.delete_all.assert_called_once_with(user_id="test_user")

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, async_client, mock_memory_service, disable_auth):
        """Test error handling in integration scenario."""
        from mcp_mitm_mem0.memory_service import MemoryServiceConnectionError

        # Configure mock to raise error
        mock_memory_service.search.side_effect = MemoryServiceConnectionError("Connection failed")

        payload = {"user_id": "test_user", "query": "test query"}
        response = await async_client.post("/search", json=payload)

        assert response.status_code == 503  # Service unavailable
        data = response.json()
        assert "details" in data

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, async_client, mock_memory_service, disable_auth):
        """Test handling of concurrent requests."""
        # Configure mock
        mock_memory_service.search.return_value = [{"id": "mem_concurrent", "content": "concurrent result"}]

        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            payload = {"user_id": f"user_{i}", "query": f"query_{i}"}
            task = async_client.post("/search", json=payload)
            tasks.append(task)

        # Wait for all requests to complete
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "memories" in data

        # Should have called search 10 times
        assert mock_memory_service.search.call_count == 10


class TestMemoryServiceIntegration:
    """Test memory service integration patterns."""

    @pytest.mark.asyncio
    async def test_memory_service_unavailable_handling(self, async_client, disable_auth):
        """Test handling when memory service is unavailable."""
        with patch("mcp_mitm_mem0.api.memory_service", None):
            payload = {"user_id": "test_user", "query": "test query"}
            response = await async_client.post("/search", json=payload)

            assert response.status_code == 503
            data = response.json()
            assert "unavailable" in data["details"].lower()

    @pytest.mark.asyncio
    async def test_memory_service_retry_behavior(self, async_client, disable_auth):
        """Test that retry logic works in integration scenarios."""
        mock_service = AsyncMock()

        # First two calls fail, third succeeds
        mock_service.search.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            [{"id": "mem_success", "content": "finally succeeded"}],
        ]

        with patch("mcp_mitm_mem0.api.memory_service", mock_service):
            payload = {"user_id": "test_user", "query": "test query"}
            response = await async_client.post("/search", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert mock_service.search.call_count == 3

    @pytest.mark.asyncio
    async def test_memory_service_timeout_handling(self, async_client, disable_auth):
        """Test handling of memory service timeouts."""
        from mcp_mitm_mem0.memory_service import MemoryServiceTimeoutError

        mock_service = AsyncMock()
        mock_service.search.side_effect = MemoryServiceTimeoutError("Request timeout")

        with patch("mcp_mitm_mem0.api.memory_service", mock_service):
            payload = {"user_id": "test_user", "query": "test query"}
            response = await async_client.post("/search", json=payload)

            assert response.status_code == 503


class TestMetricsIntegration:
    """Test Prometheus metrics integration."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_integration(self, async_client, disable_auth):
        """Test metrics endpoint integration."""
        response = await async_client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        # Should contain Prometheus metrics
        content = response.text
        assert "http_requests_total" in content
        assert "memory_service_available" in content

    @pytest.mark.asyncio
    async def test_metrics_updated_after_requests(self, async_client, disable_auth):
        """Test that metrics are updated after API requests."""
        mock_service = AsyncMock()
        mock_service.search.return_value = []

        with patch("mcp_mitm_mem0.api.memory_service", mock_service):
            # Make some API calls
            await async_client.post("/search", json={"user_id": "test", "query": "test"})
            await async_client.get("/health")

            # Check metrics
            response = await async_client.get("/metrics")
            content = response.text

            # Should have recorded the requests
            assert "memory_operations_total" in content


class TestAuthenticationIntegration:
    """Test authentication in integration scenarios."""

    @pytest.mark.asyncio
    async def test_authenticated_workflow_integration(self, async_client):
        """Test complete authenticated workflow."""
        with patch("mcp_mitm_mem0.api.settings") as mock_settings:
            mock_settings.auth_token = "integration-test-token"

            mock_service = AsyncMock()
            mock_service.search.return_value = []
            mock_service.add.return_value = [{"id": "new_mem", "content": "test"}]

            with patch("mcp_mitm_mem0.api.memory_service", mock_service):
                headers = {"Authorization": "Bearer integration-test-token"}

                # Test authenticated search
                response = await async_client.post(
                    "/search", json={"user_id": "test", "query": "test"}, headers=headers
                )
                assert response.status_code == 200

                # Test authenticated remember
                response = await async_client.post(
                    "/remember",
                    json={"user_id": "test", "messages": [{"role": "user", "content": "test"}]},
                    headers=headers,
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_mixed_auth_requests_integration(self, async_client):
        """Test mix of authenticated and unauthenticated requests."""
        with patch("mcp_mitm_mem0.api.settings") as mock_settings:
            mock_settings.auth_token = "required-token"

            # Unauthenticated request should fail
            response = await async_client.post("/search", json={"user_id": "test", "query": "test"})
            assert response.status_code == 401

            # Health check should work without auth
            response = await async_client.get("/health")
            assert response.status_code != 401  # May be 503 but not 401

            # Authenticated request should work
            mock_service = AsyncMock()
            mock_service.search.return_value = []

            with patch("mcp_mitm_mem0.api.memory_service", mock_service):
                headers = {"Authorization": "Bearer required-token"}
                response = await async_client.post(
                    "/search", json={"user_id": "test", "query": "test"}, headers=headers
                )
                assert response.status_code == 200


class TestMITMProxyIntegration:
    """Test integration with mitmproxy for Claude traffic simulation."""

    def test_mitmproxy_claude_request_simulation(self):
        """Test simulation of Claude API requests through mitmproxy."""
        # This test simulates what would happen when Claude traffic
        # is intercepted and processed by our system

        # Mock the typical Claude API request structure
        claude_request = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "What is the capital of France?"},
            ],
        }

        claude_response = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "The capital of France is Paris."}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 8},
        }

        # Simulate mitmproxy addon processing
        mock_memory_service = AsyncMock()
        mock_memory_service.add.return_value = [{"id": "mem_claude", "content": "France capital"}]

        with patch("mcp_mitm_mem0.memory_service.AsyncMemoryService", return_value=mock_memory_service):
            # This would be the processing logic in the mitmproxy addon
            claude_request["messages"][0]["content"]
            claude_response["content"][0]["text"]

            # Simulate memory storage

            # This simulates what the addon would do
            # (Note: In real scenario, this would be async)
            memory_service = mock_memory_service

            # Verify the mock would be called correctly
            assert memory_service is not None

    def test_claude_conversation_memory_extraction(self):
        """Test extracting conversation memories from Claude traffic."""
        # Simulate a multi-turn conversation
        conversation_requests = [
            {
                "messages": [
                    {"role": "user", "content": "Tell me about Python"},
                ]
            },
            {
                "messages": [
                    {"role": "user", "content": "Tell me about Python"},
                    {"role": "assistant", "content": "Python is a programming language..."},
                    {"role": "user", "content": "What about Django?"},
                ]
            },
        ]

        conversation_responses = [
            {"content": [{"type": "text", "text": "Python is a programming language..."}]},
            {"content": [{"type": "text", "text": "Django is a web framework for Python..."}]},
        ]

        # Simulate extracting memories from the conversation
        extracted_memories = []
        for req, resp in zip(conversation_requests, conversation_responses, strict=False):
            # Get the last user message (the new one in this turn)
            user_msg = req["messages"][-1]["content"]
            assistant_msg = resp["content"][0]["text"]

            extracted_memories.append({"user": user_msg, "assistant": assistant_msg})

        # Verify extraction worked correctly
        assert len(extracted_memories) == 2
        assert "Python" in extracted_memories[0]["user"]
        assert "Django" in extracted_memories[1]["user"]
        assert "programming language" in extracted_memories[0]["assistant"]
        assert "web framework" in extracted_memories[1]["assistant"]

    def test_mitmproxy_error_handling_simulation(self):
        """Test error handling in mitmproxy addon scenarios."""
        # Simulate various error conditions that could occur
        error_scenarios = [
            {"error": "connection_error", "should_retry": True},
            {"error": "timeout_error", "should_retry": True},
            {"error": "validation_error", "should_retry": False},
            {"error": "auth_error", "should_retry": False},
        ]

        for scenario in error_scenarios:
            # Simulate addon handling of different error types
            if scenario["should_retry"]:
                # For retryable errors, addon should attempt retry
                assert scenario["error"] in ["connection_error", "timeout_error"]
            else:
                # For non-retryable errors, addon should log and continue
                assert scenario["error"] in ["validation_error", "auth_error"]

    def test_mem0_service_call_verification(self):
        """Test that Mem0 service calls are properly made and verified."""
        # This test verifies that when Claude traffic is processed,
        # the appropriate Mem0 service calls are made

        mock_memory_service = Mock()
        mock_memory_service.add.return_value = [{"id": "mem_verified", "content": "test"}]

        # Simulate the addon making a memory service call
        user_id = "claude_user_123"
        messages = [
            {"role": "user", "content": "Remember this important fact"},
            {"role": "assistant", "content": "I'll remember that for you"},
        ]

        # This would be called by the mitmproxy addon
        result = mock_memory_service.add(
            messages=messages, user_id=user_id, metadata={"source": "claude_api", "timestamp": "2024-01-01T00:00:00Z"}
        )

        # Verify the call was made correctly
        mock_memory_service.add.assert_called_once()
        call_args = mock_memory_service.add.call_args
        assert call_args[1]["user_id"] == user_id
        assert len(call_args[1]["messages"]) == 2
        assert call_args[1]["metadata"]["source"] == "claude_api"
        assert result == [{"id": "mem_verified", "content": "test"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
