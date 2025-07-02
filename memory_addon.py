"""
MITM proxy addon that intercepts Claude API messages and stores them in Mem0.

This addon captures conversations between the user and Claude, storing them
for later retrieval through the MCP server.
"""

import asyncio
import hashlib
import json
from collections import deque
from datetime import datetime

import structlog
from mitmproxy import http

from mcp_mitm_mem0 import memory_service
from mcp_mitm_mem0.config import settings
from mcp_mitm_mem0.reflection_agent import reflection_agent

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Constants
RECENT_MESSAGES_LIMIT = 5
REFLECTION_MESSAGE_THRESHOLD = 5


def parse_sse_response(content: bytes) -> dict:
    """Parse Server-Sent Events response to extract complete Claude response.

    Args:
        content: Raw SSE response content

    Returns:
        Complete response data reconstructed from SSE events
    """
    if not content:
        return {}

    try:
        content_str = content.decode("utf-8")
        lines = content_str.strip().split("\n")

        # Reconstruct the complete response from SSE events
        response_data = {"content": [], "model": "", "usage": {}, "type": "message"}

        current_content_block = None
        current_text = ""

        for line in lines:
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                    event_type = event_data.get("type", "")

                    if event_type == "message_start":
                        # Extract model and basic info
                        message = event_data.get("message", {})
                        response_data["model"] = message.get("model", "")
                        response_data["id"] = message.get("id", "")
                        response_data["usage"] = message.get("usage", {})

                    elif event_type == "content_block_start":
                        # Start of a content block
                        current_content_block = event_data.get("content_block", {})
                        if current_content_block.get("type") == "text":
                            current_text = ""

                    elif event_type == "content_block_delta":
                        # Text delta - accumulate text
                        delta = event_data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            current_text += delta.get("text", "")

                    elif event_type == "content_block_stop":
                        # End of content block - save accumulated text
                        if (
                            current_content_block
                            and current_content_block.get("type") == "text"
                        ):
                            response_data["content"].append({
                                "type": "text",
                                "text": current_text,
                            })
                        current_content_block = None
                        current_text = ""

                except (json.JSONDecodeError, KeyError):
                    # Skip malformed events
                    continue

        return response_data

    except Exception as e:
        logger.error("Failed to parse SSE response", error=str(e))
        return {}


class MemoryAddon:
    """MITM addon for capturing and storing Claude conversations."""

    def __init__(self):
        """Initialize the memory addon."""
        self.logger = logger.bind(addon="memory")
        self.message_count = 0
        self.recent_messages = deque(
            maxlen=RECENT_MESSAGES_LIMIT
        )  # Keep last messages for reflection
        self.logger.info("Memory addon initialized")

    async def _trigger_reflection_async(self, messages: list[dict], user_id: str):
        """Trigger reflection analysis asynchronously (fire-and-forget).

        Args:
            messages: Recent messages to analyze
            user_id: User ID for memory operations
        """
        try:
            self.logger.info(
                "Starting reflection analysis", message_count=len(messages)
            )

            # Search for relevant memories to provide context
            # Build a clean search query from message content
            query_parts = []
            for msg in messages:
                content = msg.get("content", "")
                if content:
                    # Take first 100 chars and clean up
                    clean_content = content[:100].strip()
                    if clean_content:
                        query_parts.append(clean_content)

            # Only search if we have meaningful content
            context_memories = []
            if query_parts:
                search_query = " ".join(query_parts)
                try:
                    context_memories = await memory_service.search_memories(
                        query=search_query, user_id=user_id, limit=20
                    )
                except Exception as search_error:
                    # Log but don't fail the entire reflection
                    self.logger.warning(
                        "Memory search failed during reflection",
                        error=str(search_error),
                    )
                    context_memories = []

            # Trigger reflection with messages and context
            await reflection_agent.reflect_on_messages(
                messages=messages, context_memories=context_memories, user_id=user_id
            )

            self.logger.info("Reflection analysis completed successfully")

        except Exception as e:
            self.logger.error("Failed to complete reflection analysis", error=str(e))

    async def request(self, flow: http.HTTPFlow) -> None:
        """Handle outgoing requests to Claude API."""
        # Only process Claude API requests
        if "api.anthropic.com" not in flow.request.pretty_host:
            return

        # Store the request for later processing with response
        if flow.request.path.startswith("/v1/messages"):
            try:
                request_data = json.loads(flow.request.content)
                flow.metadata["claude_request"] = request_data
            except Exception as e:
                self.logger.error("Failed to parse request", error=str(e))

    async def response(self, flow: http.HTTPFlow) -> None:
        """Handle responses from Claude API and store conversations."""
        # Only process Claude API responses
        if "api.anthropic.com" not in flow.request.pretty_host:
            return

        # Only process /v1/messages requests that have stored request data
        if not (
            flow.request.path.startswith("/v1/messages")
            and "claude_request" in flow.metadata
        ):
            return

        try:
            request_data = flow.metadata["claude_request"]
            is_streaming = "text/event-stream" in flow.response.headers.get(
                "content-type", ""
            )

            if is_streaming:
                response_data = parse_sse_response(flow.response.content)
                # Only process if we have actual content (complete response)
                if not response_data.get("content") or not response_data.get(
                    "content", [{}]
                )[0].get("text"):
                    return  # Skip incomplete streaming chunks
            else:
                response_data = json.loads(flow.response.content)

            if not response_data:
                return

            # Create unique conversation ID for deduplication
            conv_id = f"{request_data.get('model', 'unknown')}_{response_data.get('id', 'unknown')}"
            if flow.metadata.get("processed_conv_id") == conv_id:
                return
            flow.metadata["processed_conv_id"] = conv_id

            # Log only when we're actually processing a complete response
            self.logger.info(
                "Processing complete Claude API response",
                path=flow.request.path,
                content_blocks=len(response_data.get("content", [])),
            )

            model = response_data.get("model", "")
            if model.startswith("claude-3-5-haiku-"):
                return

            # Build conversation messages - only store the current turn (latest user + assistant)
            messages = []

            if "messages" in request_data and request_data["messages"]:
                last_user_msg = None
                for msg in reversed(request_data["messages"]):
                    if msg.get("role") == "user":
                        last_user_msg = msg
                        break

                if last_user_msg:
                    # Extract text content properly - handle both string and array formats
                    content = last_user_msg.get("content", "")
                    if isinstance(content, list):
                        # Extract text from content blocks (tool results, text blocks, etc.)
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block.get("type") == "tool_result":
                                    text_parts.append(block.get("content", ""))
                        content = " ".join(text_parts)

                    if content:  # Only add if we have actual content
                        messages.append({
                            "role": "user",
                            "content": content,
                        })

            if "content" in response_data and response_data["content"]:
                assistant_content = " ".join([
                    block.get("text", "")
                    for block in response_data["content"]
                    if block.get("type") == "text"
                ])

                if assistant_content:
                    messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                    })

            if messages:
                session_content = (
                    f"{settings.default_user_id}_{datetime.now().isoformat()}"
                )
                for msg in messages:
                    session_content += f"_{msg.get('content', '')[:50]}"

                run_id = hashlib.sha256(session_content.encode()).hexdigest()[:12]

                metadata = {
                    "source": "mitm_proxy",
                    "model": response_data.get("model", "unknown"),
                    "timestamp": response_data.get("created", ""),
                    "session_id": run_id,
                }

                try:
                    result = await memory_service.add_memory(
                        messages=messages,
                        user_id=settings.default_user_id,
                        agent_id=settings.default_agent_id,
                        run_id=run_id,
                        categories=settings.memory_categories,
                        metadata=metadata,
                    )
                except Exception as mem_error:
                    # Log detailed error info including what we tried to send
                    self.logger.error(
                        "Memory service call failed",
                        error=str(mem_error),
                        messages=messages,
                        user_id=settings.default_user_id,
                        agent_id=settings.default_agent_id,
                        run_id=run_id,
                        categories=settings.memory_categories,
                        metadata=metadata,
                    )
                    raise

                self.logger.info(
                    "Stored conversation in memory",
                    memory_id=result.get("id"),
                    message_count=len(messages),
                    user_id=settings.default_user_id,
                    agent_id=settings.default_agent_id,
                    run_id=run_id,
                    categories=settings.memory_categories,
                )

                # Track messages and trigger reflection every 5 messages
                self.recent_messages.extend(messages)
                self.message_count += len(messages)

                if self.message_count >= REFLECTION_MESSAGE_THRESHOLD:
                    reflection_messages = list(self.recent_messages)

                    try:
                        asyncio.create_task(
                            self._trigger_reflection_async(
                                messages=reflection_messages,
                                user_id=settings.default_user_id,
                            )
                        )

                        self.logger.info(
                            "Triggered reflection analysis in background",
                            reflection_message_count=len(reflection_messages),
                        )
                    except Exception as e:
                        self.logger.error("Failed to trigger reflection", error=str(e))

                    self.message_count = 0
            else:
                self.logger.warning(
                    "No messages found to store",
                    request_messages_count=len(request_data.get("messages", [])),
                    response_content_exists=bool(response_data.get("content")),
                )

        except Exception as e:
            self.logger.error("Failed to process Claude response", error=str(e))


addons = [MemoryAddon()]
