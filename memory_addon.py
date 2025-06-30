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


class MemoryAddon:
    """MITM addon for capturing and storing Claude conversations."""

    def __init__(self):
        """Initialize the memory addon."""
        self.logger = logger.bind(addon="memory")
        self.message_count = 0
        self.recent_messages = deque(maxlen=5)  # Keep last 5 messages for reflection
        self.logger.info("Memory addon initialized")

    async def _trigger_reflection_async(self, messages: list[dict], user_id: str):
        """Trigger reflection analysis asynchronously (fire-and-forget).
        
        Args:
            messages: Recent messages to analyze
            user_id: User ID for memory operations
        """
        try:
            self.logger.info("Starting reflection analysis", message_count=len(messages))
            
            # Search for relevant memories to provide context
            search_query = " ".join([msg.get("content", "")[:100] for msg in messages])
            context_memories = await memory_service.search_memories(
                query=search_query, 
                user_id=user_id, 
                limit=20
            )
            
            # Trigger reflection with messages and context
            await reflection_agent.reflect_on_messages(
                messages=messages,
                context_memories=context_memories,
                user_id=user_id
            )
            
            self.logger.info("Reflection analysis completed successfully")
            
        except Exception as e:
            self.logger.error("Failed to complete reflection analysis", error=str(e))

    def request(self, flow: http.HTTPFlow) -> None:
        """Handle outgoing requests to Claude API."""
        # Only process Claude API requests
        if "api.anthropic.com" not in flow.request.pretty_host:
            return

        # Store the request for later processing with response
        if flow.request.path == "/v1/messages":
            try:
                request_data = json.loads(flow.request.content)
                flow.metadata["claude_request"] = request_data
                self.logger.debug("Captured Claude request", path=flow.request.path)
            except Exception as e:
                self.logger.error("Failed to parse request", error=str(e))

    def response(self, flow: http.HTTPFlow) -> None:
        """Handle responses from Claude API and store conversations."""
        # Only process Claude API responses
        if "api.anthropic.com" not in flow.request.pretty_host:
            return

        if flow.request.path == "/v1/messages" and "claude_request" in flow.metadata:
            try:
                # Extract request and response data
                request_data = flow.metadata["claude_request"]
                response_data = json.loads(flow.response.content)

                # Build conversation messages
                messages = []

                # Add user messages from request
                if "messages" in request_data:
                    for msg in request_data["messages"]:
                        if msg.get("role") == "user":
                            messages.append({
                                "role": "user",
                                "content": msg.get("content", ""),
                            })

                # Add assistant response
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

                # Store conversation in Mem0 if we have messages
                if messages:
                    # Generate session ID based on conversation content and timestamp
                    session_content = f"{settings.default_user_id}_{datetime.now().isoformat()}"
                    for msg in messages:
                        session_content += f"_{msg.get('content', '')[:50]}"
                    
                    run_id = hashlib.md5(session_content.encode()).hexdigest()[:12]  # noqa: S324
                    
                    metadata = {
                        "source": "mitm_proxy",
                        "model": response_data.get("model", "unknown"),
                        "timestamp": response_data.get("created", ""),
                        "session_id": run_id,
                    }

                    # Use async method with asyncio.run for MITM addon
                    result = asyncio.run(memory_service.add_memory(
                        messages=messages,
                        user_id=settings.default_user_id,
                        agent_id=settings.default_agent_id,
                        run_id=run_id,
                        categories=settings.memory_categories,
                        metadata=metadata,
                    ))

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
                    
                    if self.message_count >= 5:
                        # Create fire-and-forget task for reflection
                        reflection_messages = list(self.recent_messages)
                        asyncio.create_task(
                            self._trigger_reflection_async(
                                messages=reflection_messages,
                                user_id=settings.default_user_id
                            )
                        )
                        
                        # Reset counter
                        self.message_count = 0
                        
                        self.logger.info(
                            "Triggered reflection analysis",
                            reflection_message_count=len(reflection_messages)
                        )

            except Exception as e:
                self.logger.error("Failed to process Claude response", error=str(e))


# Create addon instance
addons = [MemoryAddon()]
