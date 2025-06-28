"""
MITM proxy addon that intercepts Claude API messages and stores them in Mem0.

This addon captures conversations between the user and Claude, storing them
for later retrieval through the MCP server.
"""

import json
from typing import Any

import structlog
from mitmproxy import http

from mcp_mitm_mem0 import memory_service
from mcp_mitm_mem0.config import settings

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
        structlog.processors.JSONRenderer()
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
        self.logger.info("Memory addon initialized")
    
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
                                "content": msg.get("content", "")
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
                            "content": assistant_content
                        })
                
                # Store conversation in Mem0 if we have messages
                if messages:
                    metadata = {
                        "source": "mitm_proxy",
                        "model": response_data.get("model", "unknown"),
                        "timestamp": response_data.get("created", "")
                    }
                    
                    # Use sync method for MITM addon
                    result = memory_service.add_memory_sync(
                        messages=messages,
                        user_id=settings.default_user_id,
                        metadata=metadata
                    )
                    
                    self.logger.info(
                        "Stored conversation in memory",
                        memory_id=result.get("id"),
                        message_count=len(messages)
                    )
                
            except Exception as e:
                self.logger.error("Failed to process Claude response", error=str(e))


# Create addon instance
addons = [MemoryAddon()]