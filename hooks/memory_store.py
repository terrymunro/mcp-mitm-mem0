#!/usr/bin/env python3
"""
Memory storage hook for Claude Code.

This hook automatically stores important outcomes, solutions, and patterns
after successful tool execution, ensuring valuable learning is captured
without relying on Claude to remember to store it.

Usage:
- PostToolUse hook: Store outcomes after successful tool execution
- Can be configured to target specific tools or all tools
"""

import asyncio
import time
from typing import Dict, Any, List, Optional

from utils import (
    read_json_input, write_json_output, log,
    add_memory_async, extract_command_from_tool_input,
    extract_file_path_from_tool_input, extract_content_from_tool_input,
    is_error_related_content, is_solution_related_content,
    extract_project_context_from_path, safe_execute_hook,
    get_user_id_from_input
)


def should_store_memory(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]) -> bool:
    """Determine if this tool execution should result in memory storage."""
    
    # Check if the operation was successful
    success = tool_response.get("success", True)  # Default to True if not specified
    if not success:
        return False
    
    # Store memories for high-value tools
    high_value_tools = [
        "Bash", "Edit", "MultiEdit", "Write", 
        "Task", "WebFetch", "WebSearch"
    ]
    
    if tool_name in high_value_tools:
        return True
    
    # Store memories for MCP tool usage
    if tool_name.startswith("mcp__"):
        return True
    
    return False


def determine_memory_type(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]) -> str:
    """Determine the type of memory to store based on tool usage."""
    
    if tool_name == "Bash":
        command = extract_command_from_tool_input(tool_input)
        
        # Check if it's error-related
        response_content = str(tool_response)
        if is_error_related_content(command) or is_error_related_content(response_content):
            return "error_resolution"
        
        # Check for common command types
        if any(cmd in command.lower() for cmd in ["git", "commit", "push", "pull"]):
            return "git_operation"
        elif any(cmd in command.lower() for cmd in ["npm", "yarn", "pip", "uv"]):
            return "package_management"
        elif any(cmd in command.lower() for cmd in ["test", "pytest", "jest"]):
            return "testing"
        elif any(cmd in command.lower() for cmd in ["build", "compile", "make"]):
            return "build_operation"
        else:
            return "command_execution"
    
    elif tool_name in ["Edit", "MultiEdit"]:
        file_path = extract_file_path_from_tool_input(tool_input)
        content = extract_content_from_tool_input(tool_input)
        
        if is_solution_related_content(content):
            return "solution_implementation"
        
        # Determine by file type
        if file_path:
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs')):
                return "code_modification"
            elif file_path.endswith(('.md', '.txt', '.rst')):
                return "documentation"
            elif file_path.endswith(('.json', '.yaml', '.yml', '.toml', '.xml')):
                return "configuration"
        
        return "file_modification"
    
    elif tool_name == "Write":
        file_path = extract_file_path_from_tool_input(tool_input)
        content = extract_content_from_tool_input(tool_input)
        
        if is_solution_related_content(content):
            return "solution_creation"
        
        # Determine by file type  
        if file_path:
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs')):
                return "code_creation"
            elif file_path.endswith(('.md', '.txt', '.rst')):
                return "documentation_creation"
            elif file_path.endswith(('.json', '.yaml', '.yml', '.toml', '.xml')):
                return "configuration_creation"
        
        return "file_creation"
    
    elif tool_name == "Task":
        return "task_execution"
    
    elif tool_name in ["WebFetch", "WebSearch"]:
        return "research"
    
    elif tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 2:
            return f"mcp_{parts[1]}_operation"
        return "mcp_operation"
    
    return "general_operation"


def create_memory_content(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]) -> List[Dict[str, str]]:
    """Create appropriate memory content based on tool usage."""
    
    messages = []
    
    if tool_name == "Bash":
        command = extract_command_from_tool_input(tool_input)
        description = tool_input.get("description", "")
        
        # Create a concise description of what was done
        user_message = f"Executed command: {command}"
        if description:
            user_message += f" ({description})"
        
        messages.append({"role": "user", "content": user_message})
        
        # Include outcome if available
        if tool_response:
            response_summary = str(tool_response)[:200]  # Limit length
            messages.append({"role": "assistant", "content": f"Command executed successfully. Result: {response_summary}"})
    
    elif tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = extract_file_path_from_tool_input(tool_input)
        content = extract_content_from_tool_input(tool_input)
        
        # Create context about the file operation
        operation = "Modified" if tool_name in ["Edit", "MultiEdit"] else "Created"
        user_message = f"{operation} file: {file_path}"
        
        # Add project context if available
        project_context = extract_project_context_from_path(file_path)
        if project_context.get("project_root"):
            user_message += f" in project {project_context['project_root']}"
        
        messages.append({"role": "user", "content": user_message})
        
        # Include a summary of what was changed (truncated)
        if content:
            content_summary = content[:150] + "..." if len(content) > 150 else content
            messages.append({"role": "assistant", "content": f"Successfully {operation.lower()} file with content: {content_summary}"})
    
    elif tool_name == "Task":
        description = tool_input.get("description", "Task execution")
        prompt = tool_input.get("prompt", "")
        
        user_message = f"Executed task: {description}"
        messages.append({"role": "user", "content": user_message})
        
        if prompt:
            prompt_summary = prompt[:100] + "..." if len(prompt) > 100 else prompt
            messages.append({"role": "assistant", "content": f"Task completed successfully. Prompt: {prompt_summary}"})
    
    elif tool_name in ["WebFetch", "WebSearch"]:
        url = tool_input.get("url", "")
        query = tool_input.get("query", "")
        
        if url:
            user_message = f"Fetched content from: {url}"
        elif query:
            user_message = f"Searched for: {query}"
        else:
            user_message = f"Performed web operation: {tool_name}"
        
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": "Web operation completed successfully"})
    
    elif tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        server = parts[1] if len(parts) > 1 else "unknown"
        tool = parts[2] if len(parts) > 2 else "unknown"
        
        user_message = f"Used MCP tool: {tool} from {server} server"
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": f"MCP operation completed successfully"})
    
    else:
        # Generic fallback
        user_message = f"Used tool: {tool_name}"
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": "Operation completed successfully"})
    
    return messages


def create_memory_metadata(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
    """Create metadata for the memory."""
    
    metadata = {
        "type": memory_type,
        "source": "claude_code_hook",
        "tool_name": tool_name,
        "auto_stored": True,
        "timestamp": str(int(time.time()))
    }
    
    # Add tool-specific metadata
    if tool_name == "Bash":
        command = extract_command_from_tool_input(tool_input)
        if command:
            cmd_parts = command.split()
            if cmd_parts:
                metadata["command"] = cmd_parts[0]
                metadata["full_command"] = command[:100]  # Truncate long commands
    
    elif tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = extract_file_path_from_tool_input(tool_input)
        if file_path:
            project_context = extract_project_context_from_path(file_path)
            metadata["file_name"] = project_context["file_name"]
            metadata["file_extension"] = project_context["extension"]
            if project_context["project_root"]:
                metadata["project"] = project_context["project_root"]
    
    elif tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 2:
            metadata["mcp_server"] = parts[1]
        if len(parts) >= 3:
            metadata["mcp_tool"] = parts[2]
    
    return metadata


async def store_tool_outcome(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any], user_id: str = None) -> Optional[Dict[str, Any]]:
    """Store the outcome of a tool execution as a memory."""
    
    # Determine memory type
    memory_type = determine_memory_type(tool_name, tool_input, tool_response)
    
    # Create memory content
    messages = create_memory_content(tool_name, tool_input, tool_response)
    
    # Create metadata
    metadata = create_memory_metadata(tool_name, tool_input, tool_response, memory_type)
    
    # Store the memory
    result = await add_memory_async(messages=messages, user_id=user_id, metadata=metadata)
    
    return result


async def main():
    """Main hook execution function."""
    start_time = time.time()
    
    try:
        # Read hook input
        input_data = read_json_input()
        
        # Extract relevant information
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})
        user_id = get_user_id_from_input(input_data)
        
        # Check if we should store memory for this tool
        if not should_store_memory(tool_name, tool_input, tool_response):
            # No storage needed, exit silently
            write_json_output(input_data)
            return
        
        # Store the memory
        result = await store_tool_outcome(tool_name, tool_input, tool_response, user_id)
        
        if result and result.get("id"):
            # Success - log but don't announce unless in debug mode
            memory_type = determine_memory_type(tool_name, tool_input, tool_response)
            log(f"Stored {memory_type} memory: {result.get('id')}")
        
        # Write output
        write_json_output(input_data)
        
    except Exception as e:
        # Unexpected error - don't block Claude, just log
        log(f"Memory storage hook error: {e}")
        # Pass through on error
        write_json_output(input_data)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())