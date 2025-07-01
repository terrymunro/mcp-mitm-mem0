#!/usr/bin/env python3
"""
Session context loader hook for Claude Code.

This hook automatically loads relevant context at the start of new sessions,
ensuring Claude has immediate access to important project context, recent work,
and ongoing patterns without needing to search manually.

Usage:
- Stop hook: Load context when starting new sessions (stop_hook_active=False)
- Can be combined with memory_analyze.py or used standalone
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils import (
    HookResponse, HookError, read_hook_input, log_hook_execution,
    search_memories_async, analyze_conversations_async, 
    safe_execute_hook, get_user_id_from_input
)


def is_new_session(input_data: Dict[str, Any]) -> bool:
    """Determine if this is a new session that warrants context loading."""
    
    # If stop_hook_active is False, this is likely the first stop in a session
    if not input_data.get("stop_hook_active", False):
        return True
    
    return False


def detect_project_context(transcript_path: str = None) -> Dict[str, Any]:
    """Detect project context from current working directory and transcript."""
    
    context = {
        "project_type": "unknown",
        "technologies": [],
        "current_directory": str(Path.cwd()),
        "project_files": [],
        "recent_work": []
    }
    
    # Analyze current directory for project type
    cwd = Path.cwd()
    
    # Check for common project files
    project_indicators = {
        "python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
        "javascript": ["package.json", "yarn.lock", "npm-shrinkwrap.json"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "go": ["go.mod", "go.sum"],
        "java": ["pom.xml", "build.gradle", "gradle.properties"],
        "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        "web": ["index.html", "webpack.config.js", "vite.config.js"],
        "git": [".git"]
    }
    
    detected_types = []
    for project_type, indicators in project_indicators.items():
        for indicator in indicators:
            if (cwd / indicator).exists():
                detected_types.append(project_type)
                context["project_files"].append(indicator)
                break
    
    if detected_types:
        context["project_type"] = detected_types[0]  # Primary type
        context["technologies"] = detected_types
    
    # Get recent files from directory (modified in last week)
    try:
        import os
        import time as time_module
        
        week_ago = time_module.time() - (7 * 24 * 60 * 60)
        recent_files = []
        
        for root, dirs, files in os.walk(cwd):
            # Skip hidden directories and common build/cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'target', 'build', 'dist']]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    if file_path.stat().st_mtime > week_ago:
                        rel_path = file_path.relative_to(cwd)
                        recent_files.append(str(rel_path))
                except (OSError, ValueError):
                    continue
        
        context["recent_work"] = recent_files[:10]  # Limit to 10 most recent
    
    except Exception:
        pass  # Don't fail if we can't get recent files
    
    return context


async def load_project_memories(project_context: Dict[str, Any], user_id: str = None) -> List[Dict[str, Any]]:
    """Load memories relevant to the current project."""
    
    memories = []
    
    # Search based on project type
    project_type = project_context.get("project_type", "")
    if project_type != "unknown":
        type_memories = await search_memories_async(
            query=f"{project_type} project development", user_id=user_id, limit=8
        )
        memories.extend(type_memories)
    
    # Search based on technologies
    technologies = project_context.get("technologies", [])
    for tech in technologies[:3]:  # Limit to first 3 technologies
        tech_memories = await search_memories_async(
            query=f"{tech} configuration setup", user_id=user_id, limit=5
        )
        memories.extend(tech_memories)
    
    # Search based on current directory
    current_dir = project_context.get("current_directory", "")
    if current_dir:
        dir_name = Path(current_dir).name
        if dir_name and dir_name != "/":
            dir_memories = await search_memories_async(
                query=f"{dir_name} project work", user_id=user_id, limit=5
            )
            memories.extend(dir_memories)
    
    # Search for recent work patterns
    recent_work = project_context.get("recent_work", [])
    if recent_work:
        # Get file extensions to understand what kind of work is happening
        extensions = set()
        for file in recent_work:
            ext = Path(file).suffix
            if ext:
                extensions.add(ext[1:])  # Remove the dot
        
        for ext in list(extensions)[:3]:  # Limit to 3 extensions
            ext_memories = await search_memories_async(
                query=f"{ext} file development coding", user_id=user_id, limit=3
            )
            memories.extend(ext_memories)
    
    # Get general project memories
    general_memories = await search_memories_async(
        query="project work development implementation", user_id=user_id, limit=8
    )
    memories.extend(general_memories)
    
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
    
    return unique_memories[:15]  # Return top 15 most relevant


async def load_recent_session_context(user_id: str = None) -> List[Dict[str, Any]]:
    """Load context from recent sessions and ongoing work."""
    
    memories = []
    
    # Search for incomplete work
    incomplete_memories = await search_memories_async(
        query="working on implementing building incomplete", user_id=user_id, limit=8
    )
    memories.extend(incomplete_memories)
    
    # Search for recent errors that might need attention
    error_memories = await search_memories_async(
        query="error problem issue debugging", user_id=user_id, limit=5
    )
    memories.extend(error_memories)
    
    # Search for recent decisions and preferences
    decision_memories = await search_memories_async(
        query="decided prefer using approach", user_id=user_id, limit=5
    )
    memories.extend(decision_memories)
    
    # Search for recent successful solutions
    solution_memories = await search_memories_async(
        query="fixed solved working success", user_id=user_id, limit=5
    )
    memories.extend(solution_memories)
    
    # Deduplicate
    seen_ids = set()
    unique_memories = []
    for memory in memories:
        memory_id = memory.get("id")
        if memory_id and memory_id not in seen_ids:
            seen_ids.add(memory_id)
            unique_memories.append(memory)
        elif not memory_id:
            unique_memories.append(memory)
    
    return unique_memories[:10]


def format_session_context(project_memories: List[Dict[str, Any]], 
                          session_memories: List[Dict[str, Any]], 
                          project_context: Dict[str, Any]) -> str:
    """Format session context for display to Claude."""
    
    if not project_memories and not session_memories:
        return ""
    
    formatted = "🚀 **Session Context Loaded**\n\n"
    
    # Show project context
    if project_context.get("project_type") != "unknown":
        tech_list = ", ".join(project_context.get("technologies", []))
        formatted += f"**Project**: {project_context['project_type']}"
        if tech_list:
            formatted += f" ({tech_list})"
        formatted += f" in `{Path(project_context['current_directory']).name}`\n"
        
        if project_context.get("recent_work"):
            recent_count = len(project_context["recent_work"])
            formatted += f"**Recent Activity**: {recent_count} files modified in last week\n"
        
        formatted += "\n"
    
    # Show project-relevant memories
    if project_memories:
        formatted += f"**📋 Project Context** ({len(project_memories)} memories):\n"
        for memory in project_memories[:5]:  # Show top 5
            content = memory.get("memory", memory.get("content", ""))
            summary = content[:80] + "..." if len(content) > 80 else content
            formatted += f"• {summary}\n"
        
        if len(project_memories) > 5:
            formatted += f"• ... and {len(project_memories) - 5} more project-related memories\n"
        formatted += "\n"
    
    # Show session-relevant memories
    if session_memories:
        formatted += f"**🔄 Recent Session Context** ({len(session_memories)} memories):\n"
        
        # Group by type for better presentation
        incomplete = []
        errors = []
        solutions = []
        decisions = []
        
        for memory in session_memories:
            content = memory.get("memory", memory.get("content", "")).lower()
            
            if any(word in content for word in ["working on", "implementing", "building", "incomplete"]):
                incomplete.append(memory)
            elif any(word in content for word in ["error", "problem", "issue", "debug"]):
                errors.append(memory)
            elif any(word in content for word in ["fixed", "solved", "working", "success"]):
                solutions.append(memory)
            elif any(word in content for word in ["decided", "prefer", "using", "approach"]):
                decisions.append(memory)
        
        if incomplete:
            formatted += "**Ongoing Work**:\n"
            for memory in incomplete[:2]:
                content = memory.get("memory", memory.get("content", ""))
                summary = content[:80] + "..." if len(content) > 80 else content
                formatted += f"• {summary}\n"
        
        if errors:
            formatted += "**Recent Issues**:\n"
            for memory in errors[:2]:
                content = memory.get("memory", memory.get("content", ""))
                summary = content[:80] + "..." if len(content) > 80 else content
                formatted += f"• {summary}\n"
        
        if solutions:
            formatted += "**Recent Solutions**:\n"
            for memory in solutions[:2]:
                content = memory.get("memory", memory.get("content", ""))
                summary = content[:80] + "..." if len(content) > 80 else content
                formatted += f"• {summary}\n"
        
        if decisions:
            formatted += "**Recent Decisions**:\n"
            for memory in decisions[:1]:
                content = memory.get("memory", memory.get("content", ""))
                summary = content[:80] + "..." if len(content) > 80 else content
                formatted += f"• {summary}\n"
        
        formatted += "\n"
    
    formatted += "---\n\n"
    return formatted


async def main():
    """Main hook execution function."""
    start_time = time.time()
    
    try:
        # Read hook input
        input_data = read_hook_input()
        
        # Extract relevant information
        session_id = input_data.get("session_id", "")
        transcript_path = input_data.get("transcript_path", "")
        user_id = get_user_id_from_input(input_data)
        
        # Log execution
        log_hook_execution("session_context", input_data, start_time)
        
        # Check if this is a new session
        if not is_new_session(input_data):
            response = HookResponse()
            response.set_suppress_output(True)
            response.output()
        
        # Detect project context
        project_context = detect_project_context(transcript_path)
        
        # Load relevant memories
        project_memories = await load_project_memories(project_context, user_id)
        session_memories = await load_recent_session_context(user_id)
        
        # Create response
        response = HookResponse()
        
        if project_memories or session_memories:
            # Format and display context
            formatted_context = format_session_context(project_memories, session_memories, project_context)
            print(formatted_context)
            
            # Add metadata to response
            response.add_data("context_loaded", True)
            response.add_data("project_memories", len(project_memories))
            response.add_data("session_memories", len(session_memories))
            response.add_data("project_type", project_context.get("project_type"))
            
            response.set_suppress_output(False)
        else:
            # No context to load
            if project_context.get("project_type") != "unknown":
                print(f"🚀 **New Session** - Working in {project_context['project_type']} project")
                response.set_suppress_output(False)
            else:
                response.set_suppress_output(True)
        
        response.output()
        
    except HookError as e:
        # Hook-specific error - log and exit gracefully
        safe_execute_hook(lambda: print(f"Session context hook error: {e}", file=sys.stderr))
        sys.exit(1)
    
    except Exception as e:
        # Unexpected error - don't block Claude, just log
        safe_execute_hook(lambda: print(f"Unexpected error in session context hook: {e}", file=sys.stderr))
        sys.exit(0)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())