#!/usr/bin/env python3
"""
Memory search hook for Claude Code.

This hook searches for relevant memories before tool execution,
providing proactive context to help Claude make better decisions
and avoid repeating past mistakes.

Usage:
- PreToolUse hook: Search memories before executing tools
- Can be configured to target specific tools or all tools
"""

import asyncio
import time
from typing import Dict, Any, List

from utils import (
    HookResponse, HookError, read_hook_input, log_hook_execution,
    search_memories_async, should_trigger_memory_search,
    create_search_query_from_tool_use, extract_command_from_tool_input,
    extract_file_path_from_tool_input, safe_execute_hook,
    get_user_id_from_input
)


async def search_relevant_memories(tool_name: str, tool_input: Dict[str, Any], user_id: str = None) -> List[Dict[str, Any]]:
    """Search for memories relevant to the current tool use."""
    
    # Create search query based on tool type and input
    search_query = create_search_query_from_tool_use(tool_name, tool_input)
    
    # Get memories
    memories = await search_memories_async(query=search_query, user_id=user_id, limit=8)
    
    # For specific tools, do additional targeted searches
    additional_memories = []
    
    if tool_name == "Bash":
        command = extract_command_from_tool_input(tool_input)
        if command:
            # Search for command-specific patterns
            cmd_parts = command.split()
            if cmd_parts:
                base_cmd = cmd_parts[0]
                cmd_memories = await search_memories_async(
                    query=f"{base_cmd} command error solution", 
                    user_id=user_id, 
                    limit=5
                )
                additional_memories.extend(cmd_memories)
    
    elif tool_name in ["Edit", "MultiEdit", "Write"]:
        file_path = extract_file_path_from_tool_input(tool_input)
        if file_path:
            # Search for file-specific context
            file_memories = await search_memories_async(
                query=f"file {file_path} editing modification",
                user_id=user_id,
                limit=5
            )
            additional_memories.extend(file_memories)
    
    # Combine and deduplicate memories
    all_memories = memories + additional_memories
    seen_ids = set()
    unique_memories = []
    
    for memory in all_memories:
        memory_id = memory.get("id")
        if memory_id and memory_id not in seen_ids:
            seen_ids.add(memory_id)
            unique_memories.append(memory)
        elif not memory_id:  # Keep memories without IDs
            unique_memories.append(memory)
    
    return unique_memories[:10]  # Limit to top 10 results


def format_memories_for_claude(memories: List[Dict[str, Any]]) -> str:
    """Format memories in a way that's helpful for Claude."""
    if not memories:
        return ""
    
    formatted = "## Relevant Context from Memory\n\n"
    
    for i, memory in enumerate(memories, 1):
        content = memory.get("memory", memory.get("content", ""))
        created_at = memory.get("created_at", "")
        metadata = memory.get("metadata", {})
        
        formatted += f"### {i}. Memory from {created_at}\n"
        
        # Add metadata context if available
        if metadata:
            mem_type = metadata.get("type", "")
            if mem_type:
                formatted += f"**Type**: {mem_type}  \n"
        
        # Add content (truncated if too long)
        if len(content) > 300:
            content = content[:300] + "..."
        
        formatted += f"{content}\n\n"
    
    formatted += "---\n\n"
    return formatted


def check_for_error_patterns(memories: List[Dict[str, Any]], tool_name: str, tool_input: Dict[str, Any]) -> tuple[bool, str]:
    """Check if memories contain error patterns that suggest blocking the operation."""
    
    if tool_name != "Bash":
        return False, ""
    
    command = extract_command_from_tool_input(tool_input)
    if not command:
        return False, ""
    
    # Look for error patterns in memories
    error_count = 0
    error_details = []
    
    for memory in memories:
        content = memory.get("memory", memory.get("content", "")).lower()
        
        # Check if this memory is about the same command and contains errors
        if command.split()[0] in content if command.split() else False:
            if any(error_word in content for error_word in ["failed", "error", "cannot", "permission denied", "not found"]):
                error_count += 1
                
                # Extract error context
                lines = content.split('\n')
                for line in lines:
                    if any(error_word in line for error_word in ["failed", "error", "cannot"]):
                        error_details.append(line[:100])
                        break
    
    # If multiple error memories, suggest caution
    if error_count >= 2:
        error_summary = ". ".join(error_details[:2])
        return True, f"This command has failed multiple times before. Previous errors: {error_summary}. Consider reviewing the approach."
    
    return False, ""


async def main():
    """Main hook execution function."""
    start_time = time.time()
    
    try:
        # Read hook input
        input_data = read_hook_input()
        
        # Extract relevant information
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        user_id = get_user_id_from_input(input_data)
        
        # Log execution
        log_hook_execution("memory_search", input_data, start_time)
        
        # Check if we should trigger memory search for this tool
        if not should_trigger_memory_search(tool_name, tool_input):
            # No search needed, allow operation to proceed
            response = HookResponse()
            response.set_suppress_output(True)
            response.output()
        
        # Search for relevant memories
        memories = await search_relevant_memories(tool_name, tool_input, user_id)
        
        # Create response
        response = HookResponse()
        
        if memories:
            # Format memories for Claude
            formatted_memories = format_memories_for_claude(memories)
            
            # Check for error patterns that might warrant blocking
            should_block, block_reason = check_for_error_patterns(memories, tool_name, tool_input)
            
            if should_block:
                # Block the operation with context
                response.block_with_reason(f"{block_reason}\n\nRelevant memories:\n{formatted_memories}")
            else:
                # Provide context but allow operation
                print(f"Found {len(memories)} relevant memories for {tool_name} operation:\n\n{formatted_memories}")
                response.set_suppress_output(False)
        else:
            # No memories found, proceed silently
            response.set_suppress_output(True)
        
        # Allow operation to proceed
        response.output()
        
    except HookError as e:
        # Hook-specific error - log and exit gracefully
        print(f"Memory search hook error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        # Unexpected error - don't block Claude, just log
        safe_execute_hook(lambda: print(f"Unexpected error in memory search hook: {e}", file=sys.stderr))
        sys.exit(0)  # Don't block operation


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())