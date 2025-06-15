"""
This is an addon for mitmproxy that stores chat messages in Mem0.
"""

import json
import os
from typing import Any, TypedDict, TypeGuard

from mem0 import Memory
from mitmproxy import http
from pydantic import ValidationError


class Content(TypedDict):
    type: str
    text: str


class Message(TypedDict):
    role: str
    content: list[Content]


class ClaudeRequest(TypedDict):
    model: str
    messages: list[Message]


def is_claude_request(data: Any) -> TypeGuard[ClaudeRequest]:
    """
    Check if the request is a valid Claude request.
    """
    return (
        isinstance(data, dict) and
        data.get("model", "").startswith("claude-sonnet") and  # type: ignore
        "messages" in data
    )


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "test-key")
mem0 = Memory()


def _valid_requests(flow: http.HTTPFlow) -> bool:
    """
    Check if the request is a valid request.
    """
    return (
        "application/json" in flow.request.headers.get("content-type", "")  # type: ignore
        and flow.request.headers.get("anthropic-beta") == "claude-code"  # type: ignore
        and flow.request.pretty_url.split("?")[0].endswith("/v1/messages")
    )


def request(flow: http.HTTPFlow) -> None:
    """
    This is a request hook that stores chat messages in Mem0.

    Args:
        flow: The HTTP flow.
    """
    if not _valid_requests(flow):
        return

    # Parse the request body as json
    try:
        raw_text = flow.request.get_text()
        data = json.loads(str(raw_text))
    except json.JSONDecodeError:
        return

    if not is_claude_request(data):
        return

    data.get("")
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        return

    for message in messages:
        try:
            msg = Message.model_validate(message)
        except ValidationError as e:
            print(f"Error validating message: {e}")
            continue

    user_id = flow.request.headers.get("X-User-Id", "mitm-user")
    mem0.add(messages, user_id=user_id, metadata={"source": "mitmproxy"})
