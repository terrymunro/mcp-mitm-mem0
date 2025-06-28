#!/usr/bin/env python3
"""
Example client demonstrating secure API usage with authentication and error handling.

This script shows how to:
- Use bearer token authentication
- Handle rate limiting
- Handle graceful degradation when Mem0 is unavailable
"""

import json
import os
import time

import requests


class MemoryAPIClient:
    """Client for the MCP MITM Mem0 API with security features."""

    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str | None = None):
        """Initialize the API client.

        Args:
            base_url: Base URL of the API server
            auth_token: Bearer token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"})
        else:
            self.session.headers.update({"Content-Type": "application/json"})

    def _handle_response(self, response: requests.Response) -> dict:
        """Handle API response with proper error handling."""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise RuntimeError("Authentication failed - check your AUTH_TOKEN")
        elif response.status_code == 429:
            raise RuntimeError("Rate limit exceeded - please wait before retrying")
        elif response.status_code == 503:
            error_data = response.json() if response.content else {}
            raise RuntimeError(f"Service unavailable: {error_data.get('details', 'Mem0 service is down')}")
        else:
            try:
                error_data = response.json()
                raise RuntimeError(f"API error ({response.status_code}): {error_data.get('error', 'Unknown error')}")
            except json.JSONDecodeError:
                raise RuntimeError(f"API error ({response.status_code}): {response.text}")

    def health_check(self) -> dict:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/health")
        return self._handle_response(response)

    def search_memories(self, user_id: str, query: str, limit: int | None = None) -> dict:
        """Search memories."""
        data = {"user_id": user_id, "query": query}
        if limit is not None:
            data["limit"] = limit

        response = self.session.post(f"{self.base_url}/search", json=data)
        return self._handle_response(response)

    def list_memories(self, user_id: str) -> dict:
        """List all memories for a user."""
        data = {"user_id": user_id}
        response = self.session.post(f"{self.base_url}/list", json=data)
        return self._handle_response(response)

    def remember(self, user_id: str, messages: list, metadata: dict | None = None, run_id: str | None = None) -> dict:
        """Add memories."""
        data = {"user_id": user_id, "messages": messages}
        if metadata:
            data["metadata"] = metadata
        if run_id:
            data["run_id"] = run_id

        response = self.session.post(f"{self.base_url}/remember", json=data)
        return self._handle_response(response)

    def forget(self, user_id: str, memory_id: str | None = None) -> dict:
        """Delete memories."""
        data = {"user_id": user_id}
        if memory_id:
            data["memory_id"] = memory_id

        response = self.session.post(f"{self.base_url}/forget", json=data)
        return self._handle_response(response)


def main():
    """Example usage of the Memory API client."""
    # Get auth token from environment
    auth_token = os.getenv("AUTH_TOKEN")
    if not auth_token:
        print("⚠️  No AUTH_TOKEN found in environment - API calls may fail if authentication is required")

    # Initialize client
    client = MemoryAPIClient(auth_token=auth_token)

    try:
        print("🔍 Checking API health...")
        health = client.health_check()
        print(f"✅ API is healthy: {health}")

        if not health.get("memory_service_available", False):
            print("⚠️  Memory service is not available - some operations may fail")

        # Example user ID
        user_id = "example_user_123"

        print(f"\n📝 Adding memories for user {user_id}...")
        memories_result = client.remember(
            user_id=user_id,
            messages=[
                {"role": "user", "content": "I love machine learning"},
                {"role": "assistant", "content": "That's great! ML is a fascinating field."},
            ],
            metadata={"source": "example_conversation"},
        )
        print(f"✅ Added {memories_result['count']} memories")

        print(f"\n🔍 Searching memories for user {user_id}...")
        search_result = client.search_memories(user_id=user_id, query="machine learning")
        print(f"✅ Found {search_result['count']} memories matching 'machine learning'")

        print(f"\n📋 Listing all memories for user {user_id}...")
        list_result = client.list_memories(user_id=user_id)
        print(f"✅ User has {list_result['count']} total memories")

        # Demonstrate rate limiting by making multiple requests quickly
        print("\n⏱️  Testing rate limiting...")
        for i in range(3):
            try:
                health = client.health_check()
                print(f"   Request {i + 1}: ✅ Success")
                time.sleep(0.1)  # Small delay
            except RuntimeError as e:
                if "rate limit" in str(e).lower():
                    print(f"   Request {i + 1}: ⚠️  Rate limited: {e}")
                else:
                    print(f"   Request {i + 1}: ❌ Error: {e}")

    except RuntimeError as e:
        print(f"❌ API Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


if __name__ == "__main__":
    main()
