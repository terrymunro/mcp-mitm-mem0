#!/usr/bin/env python3
"""
Permission intelligence hook for Claude Code.

This hook provides intelligent context when Claude requests permission
for operations, helping users make informed decisions based on past
experiences and potential issues.

Usage:
- Notification hook: Analyze permission requests and provide context
"""

import asyncio
import time
from typing import Dict, Any, List, Optional

from utils import (
    HookResponse, HookError, read_hook_input, log_hook_execution,
    search_memories_async, safe_execute_hook, get_user_id_from_input
)


def extract_operation_context_from_notification(message: str, title: str) -> Dict[str, str]:
    """Extract operation context from the notification message."""
    
    context = {
        "operation_type": "unknown",
        "tool_name": "",
        "risk_level": "low",
        "key_terms": []
    }
    
    message_lower = message.lower()
    
    # Identify operation type from message
    if "bash" in message_lower or "command" in message_lower:
        context["operation_type"] = "command_execution"
        context["tool_name"] = "Bash"
        context["risk_level"] = "medium"
        
        # Extract command if possible
        if "run" in message_lower or "execute" in message_lower:
            # Try to extract the actual command
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ["run", "execute"] and i + 1 < len(words):
                    context["key_terms"].append(words[i + 1])
    
    elif "edit" in message_lower or "modify" in message_lower:
        context["operation_type"] = "file_modification"
        context["tool_name"] = "Edit"
        context["risk_level"] = "medium"
        
        # Look for file names or paths
        words = message.split()
        for word in words:
            if "." in word and "/" in word:  # Likely a file path
                context["key_terms"].append(word)
    
    elif "write" in message_lower or "create" in message_lower:
        context["operation_type"] = "file_creation"
        context["tool_name"] = "Write"
        context["risk_level"] = "low"
    
    elif "delete" in message_lower or "remove" in message_lower:
        context["operation_type"] = "deletion"
        context["risk_level"] = "high"
        
        # Look for what's being deleted
        words = message.split()
        for word in words:
            if word.startswith("/") or "." in word:
                context["key_terms"].append(word)
    
    elif "install" in message_lower or "package" in message_lower:
        context["operation_type"] = "package_management"
        context["risk_level"] = "medium"
        
        # Look for package names
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() in ["install", "add", "update"] and i + 1 < len(words):
                context["key_terms"].append(words[i + 1])
    
    elif "git" in message_lower:
        context["operation_type"] = "version_control"
        context["tool_name"] = "Bash"
        context["risk_level"] = "medium"
        
        if any(risky in message_lower for risky in ["push", "force", "reset", "rebase"]):
            context["risk_level"] = "high"
    
    # Check for high-risk indicators
    if any(risky in message_lower for risky in [
        "sudo", "rm -rf", "force", "--hard", "production", "main", "master"
    ]):
        context["risk_level"] = "high"
    
    return context


async def search_relevant_permission_context(context: Dict[str, str], user_id: str = None) -> List[Dict[str, Any]]:
    """Search for memories relevant to the permission request."""
    
    memories = []
    
    # Search based on operation type
    operation_type = context["operation_type"]
    
    if operation_type == "command_execution" and context["key_terms"]:
        # Search for command-specific memories
        for term in context["key_terms"][:3]:  # Limit to first 3 terms
            cmd_memories = await search_memories_async(
                query=f"{term} command error problem", user_id=user_id, limit=5
            )
            memories.extend(cmd_memories)
    
    elif operation_type == "file_modification" and context["key_terms"]:
        # Search for file-specific context
        for term in context["key_terms"][:2]:
            file_memories = await search_memories_async(
                query=f"file {term} edit modify", user_id=user_id, limit=5
            )
            memories.extend(file_memories)
    
    elif operation_type == "deletion":
        # Search for deletion-related issues
        delete_memories = await search_memories_async(
            query="delete remove rm file loss problem", user_id=user_id, limit=8
        )
        memories.extend(delete_memories)
    
    elif operation_type == "package_management":
        # Search for package/dependency issues
        package_memories = await search_memories_async(
            query="install package dependency npm yarn pip error", user_id=user_id, limit=8
        )
        memories.extend(package_memories)
    
    elif operation_type == "version_control":
        # Search for git-related issues
        git_memories = await search_memories_async(
            query="git commit push pull merge conflict error", user_id=user_id, limit=8
        )
        memories.extend(git_memories)
    
    # Also do a general search based on risk level
    if context["risk_level"] == "high":
        risk_memories = await search_memories_async(
            query="error problem failed dangerous issue", user_id=user_id, limit=5
        )
        memories.extend(risk_memories)
    
    # Deduplicate memories
    seen_ids = set()
    unique_memories = []
    for memory in memories:
        memory_id = memory.get("id")
        if memory_id and memory_id not in seen_ids:
            seen_ids.add(memory_id)
            unique_memories.append(memory)
        elif not memory_id:
            unique_memories.append(memory)
    
    return unique_memories[:8]  # Return top 8 most relevant


def format_permission_context(memories: List[Dict[str, Any]], context: Dict[str, str]) -> str:
    """Format memory context for permission decision."""
    
    if not memories:
        return ""
    
    risk_level = context["risk_level"]
    operation_type = context["operation_type"]
    
    # Create appropriate header based on risk level
    if risk_level == "high":
        header = "⚠️  **HIGH RISK OPERATION** - Review past experiences:"
    elif risk_level == "medium":
        header = "⚡ **Permission Context** - Relevant past experiences:"
    else:
        header = "💡 **Context Available** - Related past work:"
    
    formatted = f"\n{header}\n\n"
    
    # Group memories by type for better presentation
    error_memories = []
    solution_memories = []
    general_memories = []
    
    for memory in memories:
        content = memory.get("memory", memory.get("content", "")).lower()
        if any(error_word in content for error_word in ["error", "failed", "problem", "issue"]):
            error_memories.append(memory)
        elif any(solution_word in content for solution_word in ["fixed", "solved", "success", "working"]):
            solution_memories.append(memory)
        else:
            general_memories.append(memory)
    
    # Show errors first (most important for permission decisions)
    if error_memories:
        formatted += "**⚠️ Previous Issues:**\n"
        for memory in error_memories[:3]:
            content = memory.get("memory", memory.get("content", ""))
            summary = content[:120] + "..." if len(content) > 120 else content
            formatted += f"- {summary}\n"
        formatted += "\n"
    
    # Show solutions next
    if solution_memories:
        formatted += "**✅ Previous Solutions:**\n"
        for memory in solution_memories[:2]:
            content = memory.get("memory", memory.get("content", ""))
            summary = content[:120] + "..." if len(content) > 120 else content
            formatted += f"- {summary}\n"
        formatted += "\n"
    
    # Show general context if space
    if general_memories and len(error_memories + solution_memories) < 4:
        formatted += "**📋 Related Context:**\n"
        for memory in general_memories[:2]:
            content = memory.get("memory", memory.get("content", ""))
            summary = content[:100] + "..." if len(content) > 100 else content
            formatted += f"- {summary}\n"
        formatted += "\n"
    
    # Add risk-based recommendation
    if risk_level == "high" and error_memories:
        formatted += "🔴 **Recommendation**: Review errors above carefully before proceeding.\n"
    elif risk_level == "medium" and error_memories:
        formatted += "🟡 **Recommendation**: Consider past issues when making decision.\n"
    elif solution_memories:
        formatted += "🟢 **Note**: Past solutions available if needed.\n"
    
    return formatted


def should_provide_context(message: str, title: str, context: Dict[str, str]) -> bool:
    """Determine if we should provide context for this permission request."""
    
    # Always provide context for high-risk operations
    if context["risk_level"] == "high":
        return True
    
    # Provide context for medium-risk operations with specific terms
    if context["risk_level"] == "medium" and context["key_terms"]:
        return True
    
    # Provide context for operations that commonly have issues
    high_issue_operations = ["command_execution", "package_management", "version_control"]
    if context["operation_type"] in high_issue_operations:
        return True
    
    return False


async def main():
    """Main hook execution function."""
    start_time = time.time()
    
    try:
        # Read hook input
        input_data = read_hook_input()
        
        # Extract notification information
        message = input_data.get("message", "")
        title = input_data.get("title", "")
        session_id = input_data.get("session_id", "")
        user_id = get_user_id_from_input(input_data)
        
        # Log execution
        log_hook_execution("permission_intelligence", input_data, start_time)
        
        # Extract operation context from the notification
        context = extract_operation_context_from_notification(message, title)
        
        # Check if we should provide context for this operation
        if not should_provide_context(message, title, context):
            response = HookResponse()
            response.set_suppress_output(True)
            response.output()
        
        # Search for relevant memories
        memories = await search_relevant_permission_context(context, user_id)
        
        # Create response
        response = HookResponse()
        
        if memories:
            # Format context for the user
            formatted_context = format_permission_context(memories, context)
            print(formatted_context)
            response.set_suppress_output(False)
        else:
            # No relevant context found
            if context["risk_level"] == "high":
                print(f"⚠️ **HIGH RISK OPERATION** - No specific past context found for {context['operation_type']}")
                response.set_suppress_output(False)
            else:
                response.set_suppress_output(True)
        
        response.output()
        
    except HookError as e:
        # Hook-specific error - log and exit gracefully
        safe_execute_hook(lambda: print(f"Permission intelligence hook error: {e}", file=sys.stderr))
        sys.exit(1)
    
    except Exception as e:
        # Unexpected error - don't block notification, just log
        safe_execute_hook(lambda: print(f"Unexpected error in permission intelligence hook: {e}", file=sys.stderr))
        sys.exit(0)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())