#!/usr/bin/env python3
"""
Utility functions for Claude Code hooks integration with MCP MITM Mem0.

Provides common functionality for hook scripts including JSON I/O,
memory service interface, error handling, and helper functions.
"""

import json
import sys
import os
import time
import traceback
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# Add the parent directory to Python path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp_mitm_mem0.memory_service import memory_service
    from mcp_mitm_mem0.reflection_agent import reflection_agent
    from mcp_mitm_mem0.config import settings
except ImportError as e:
    # Graceful fallback if modules can't be imported
    memory_service = None
    reflection_agent = None
    settings = None
    print(f"Warning: Could not import MCP modules: {e}", file=sys.stderr)


class HookError(Exception):
    """Custom exception for hook-related errors."""
    pass


class HookResponse:
    """Structured response for Claude Code hooks."""
    
    def __init__(self):
        self.data = {}
    
    def set_decision(self, decision: str, reason: str = ""):
        """Set hook decision (approve/block)."""
        self.data["decision"] = decision
        if reason:
            self.data["reason"] = reason
        return self
    
    def set_continue(self, should_continue: bool, stop_reason: str = ""):
        """Set whether Claude should continue after hook execution."""
        self.data["continue"] = should_continue
        if stop_reason:
            self.data["stopReason"] = stop_reason
        return self
    
    def set_suppress_output(self, suppress: bool = True):
        """Set whether to suppress stdout from transcript mode."""
        self.data["suppressOutput"] = suppress
        return self
    
    def add_data(self, key: str, value: Any):
        """Add custom data to the response."""
        self.data[key] = value
        return self
    
    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.data, indent=2)
    
    def output(self):
        """Output the response and exit with appropriate code."""
        if self.data:
            print(self.to_json())
        
        # Exit with code 0 for success
        sys.exit(0)
    
    def block_with_reason(self, reason: str):
        """Block the operation with a reason and exit."""
        print(reason, file=sys.stderr)
        sys.exit(2)  # Exit code 2 blocks and shows stderr to Claude


def read_hook_input() -> Dict[str, Any]:
    """Read and parse JSON input from stdin."""
    try:
        input_data = json.load(sys.stdin)
        return input_data
    except json.JSONDecodeError as e:
        raise HookError(f"Invalid JSON input: {e}")
    except Exception as e:
        raise HookError(f"Failed to read input: {e}")


def log_hook_execution(hook_name: str, input_data: Dict[str, Any], start_time: float):
    """Log hook execution for debugging."""
    execution_time = time.time() - start_time
    log_entry = {
        "hook": hook_name,
        "execution_time_ms": round(execution_time * 1000, 2),
        "session_id": input_data.get("session_id", "unknown"),
        "tool_name": input_data.get("tool_name", ""),
        "timestamp": time.time()
    }
    
    # Log to a file for debugging
    log_file = Path.home() / ".claude" / "hook_execution.log"
    log_file.parent.mkdir(exist_ok=True)
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        # Don't fail the hook if logging fails
        pass


async def search_memories_async(query: str, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search memories asynchronously."""
    if not memory_service:
        return []
    
    try:
        results = await memory_service.search_memories(
            query=query, user_id=user_id, limit=limit
        )
        return results
    except Exception as e:
        # Silent failure for hooks - don't break Claude's flow
        return []


async def add_memory_async(messages: List[Dict[str, str]], user_id: Optional[str] = None, 
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Add memory asynchronously."""
    if not memory_service:
        return None
    
    try:
        result = await memory_service.add_memory(
            messages=messages, user_id=user_id, metadata=metadata
        )
        return result
    except Exception as e:
        # Silent failure for hooks
        return None


async def analyze_conversations_async(user_id: Optional[str] = None, limit: int = 20) -> Optional[Dict[str, Any]]:
    """Trigger conversation analysis asynchronously."""
    if not reflection_agent:
        return None
    
    try:
        result = await reflection_agent.analyze_recent_conversations(
            user_id=user_id, limit=limit
        )
        return result
    except Exception as e:
        # Silent failure for hooks
        return None


def extract_command_from_tool_input(tool_input: Dict[str, Any]) -> str:
    """Extract command string from Bash tool input."""
    return tool_input.get("command", "")


def extract_file_path_from_tool_input(tool_input: Dict[str, Any]) -> str:
    """Extract file path from file operation tool input."""
    return tool_input.get("file_path", tool_input.get("path", ""))


def extract_content_from_tool_input(tool_input: Dict[str, Any]) -> str:
    """Extract content from tool input (for Write/Edit operations)."""
    return tool_input.get("content", tool_input.get("new_string", ""))


def is_error_related_content(content: str) -> bool:
    """Check if content appears to be error-related."""
    error_indicators = [
        "error", "failed", "exception", "traceback", 
        "fatal", "crash", "bug", "issue", "problem",
        "warning", "deprecated", "not found", "cannot"
    ]
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in error_indicators)


def is_solution_related_content(content: str) -> bool:
    """Check if content appears to be solution-related."""
    solution_indicators = [
        "fixed", "solved", "resolved", "working", "success",
        "completed", "done", "implemented", "solution", "fix"
    ]
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in solution_indicators)


def extract_project_context_from_path(file_path: str) -> Dict[str, str]:
    """Extract project context from file path."""
    path = Path(file_path)
    context = {
        "file_name": path.name,
        "directory": str(path.parent),
        "extension": path.suffix,
        "project_root": ""
    }
    
    # Look for common project indicators
    for parent in path.parents:
        if any((parent / indicator).exists() for indicator in 
               ["package.json", "pyproject.toml", "Cargo.toml", ".git", "pom.xml"]):
            context["project_root"] = str(parent)
            break
    
    return context


def should_trigger_memory_search(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Determine if a memory search should be triggered for this tool use."""
    high_value_tools = [
        "Bash", "Edit", "MultiEdit", "Write", "Read",
        "Task", "WebFetch", "WebSearch"
    ]
    
    # Always trigger for high-value tools
    if tool_name in high_value_tools:
        return True
    
    # Trigger for MCP tools
    if tool_name.startswith("mcp__"):
        return True
    
    return False


def create_search_query_from_tool_use(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Create an appropriate search query based on tool usage."""
    if tool_name == "Bash":
        command = extract_command_from_tool_input(tool_input)
        # Extract key terms from the command
        return f"bash command {command.split()[0] if command.split() else 'command'}"
    
    elif tool_name in ["Edit", "MultiEdit", "Write", "Read"]:
        file_path = extract_file_path_from_tool_input(tool_input)
        if file_path:
            path = Path(file_path)
            return f"file {path.name} {path.suffix} editing"
        return "file editing"
    
    elif tool_name == "Task":
        description = tool_input.get("description", "")
        return f"task {description[:50]}"
    
    elif tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            server = parts[1]
            tool = parts[2]
            return f"{server} {tool} mcp"
        return "mcp tool"
    
    return f"{tool_name.lower()} operation"


def safe_execute_hook(hook_func, *args, **kwargs):
    """Safely execute a hook function with error handling."""
    try:
        return hook_func(*args, **kwargs)
    except Exception as e:
        # Log the error but don't fail the hook
        error_msg = f"Hook execution error: {e}\n{traceback.format_exc()}"
        log_file = Path.home() / ".claude" / "hook_errors.log"
        log_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(log_file, "a") as f:
                f.write(f"{time.time()}: {error_msg}\n")
        except Exception:
            pass
        
        return None


def get_user_id_from_input(input_data: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from hook input, with fallback to settings."""
    # Check if user ID is in the input data
    user_id = input_data.get("user_id")
    if user_id:
        return user_id
    
    # Fallback to settings
    if settings and hasattr(settings, 'default_user_id'):
        return settings.default_user_id
    
    return None


if __name__ == "__main__":
    # Test the utility functions
    print("MCP MITM Mem0 Hook Utils - Test Mode")
    
    # Test JSON input/output
    test_input = {"test": "data", "session_id": "test-123"}
    print(f"Test input: {json.dumps(test_input, indent=2)}")
    
    # Test response creation
    response = HookResponse()
    response.add_data("test_status", "success")
    print(f"Test response: {response.to_json()}")
    
    print("Utils test completed successfully")