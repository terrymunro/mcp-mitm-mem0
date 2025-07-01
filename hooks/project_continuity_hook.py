#!/usr/bin/env python3
"""
Project continuity hook for maintaining context across sessions.
Tracks project state, recent changes, and current focus areas.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    read_json_input, write_json_output, log,
    get_mcp_client, get_session_file
)

def extract_project_context(messages: List[Dict]) -> Dict[str, Any]:
    """Extract project context from recent messages."""
    context = {
        "files_modified": set(),
        "commands_run": [],
        "current_task": None,
        "recent_errors": [],
        "dependencies_added": [],
        "tests_run": []
    }
    
    for msg in messages[-20:]:  # Last 20 messages
        content = msg.get("content", "")
        
        # Extract file modifications
        file_patterns = [
            r"Modified\s+([^\s]+\.[a-zA-Z]+)",
            r"Created\s+([^\s]+\.[a-zA-Z]+)",
            r"Editing\s+([^\s]+\.[a-zA-Z]+)",
            r"Writing to\s+([^\s]+\.[a-zA-Z]+)"
        ]
        
        for pattern in file_patterns:
            import re
            matches = re.findall(pattern, content)
            context["files_modified"].update(matches)
        
        # Extract commands
        if "```bash" in content or "```sh" in content:
            command_blocks = re.findall(r'```(?:bash|sh)\n(.*?)\n```', content, re.DOTALL)
            context["commands_run"].extend(command_blocks)
        
        # Extract current task from TodoWrite
        if "TodoWrite" in content:
            try:
                todo_match = re.search(r'"content":\s*"([^"]+)".*?"status":\s*"in_progress"', content)
                if todo_match:
                    context["current_task"] = todo_match.group(1)
            except:
                pass
        
        # Extract errors
        if any(err in content.lower() for err in ["error", "failed", "exception"]):
            context["recent_errors"].append(content[:200])
        
        # Extract dependency changes
        dep_patterns = [
            r"npm install\s+([^\s]+)",
            r"pip install\s+([^\s]+)",
            r"uv add\s+([^\s]+)",
            r"cargo add\s+([^\s]+)"
        ]
        
        for pattern in dep_patterns:
            matches = re.findall(pattern, content)
            context["dependencies_added"].extend(matches)
        
        # Extract test runs
        test_patterns = [
            r"pytest",
            r"npm test",
            r"cargo test",
            r"go test"
        ]
        
        for pattern in test_patterns:
            if pattern in content:
                context["tests_run"].append(pattern)
    
    # Convert sets to lists for JSON serialization
    context["files_modified"] = list(context["files_modified"])
    
    return context

def store_project_state(context: Dict[str, Any], session_file: Path):
    """Store project state for continuity."""
    try:
        client = get_mcp_client()
        
        # Prepare project state summary
        state_summary = f"""Project State Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}

Current Task: {context.get('current_task', 'Not specified')}

Recent File Modifications:
{chr(10).join(f'- {f}' for f in context['files_modified'][:10])}

Recent Commands:
{chr(10).join(f'- {cmd.strip()}' for cmd in context['commands_run'][-5:])}

Dependencies Added: {', '.join(context['dependencies_added'][:5])}

Recent Errors: {len(context['recent_errors'])}
"""
        
        # Store in memory
        result = client.call_tool(
            "mcp__memory__add_memory",
            {
                "messages": [
                    {
                        "role": "system",
                        "content": state_summary
                    }
                ],
                "metadata": {
                    "type": "project_state",
                    "session_id": session_file.stem,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
        
        log("Stored project state for continuity")
        
        # Also save to session file
        session_data = {}
        if session_file.exists():
            session_data = json.loads(session_file.read_text())
        
        session_data["project_state"] = {
            "context": context,
            "summary": state_summary,
            "timestamp": datetime.now().isoformat()
        }
        
        session_file.write_text(json.dumps(session_data, indent=2))
        
    except Exception as e:
        log(f"Error storing project state: {e}")

def retrieve_previous_state() -> Optional[str]:
    """Retrieve previous project state from memory."""
    try:
        client = get_mcp_client()
        
        # Search for recent project state
        result = client.call_tool(
            "mcp__memory__search_memories",
            {
                "query": "project state update current task file modifications",
                "limit": 3
            }
        )
        
        if result and result.get("content"):
            memories = json.loads(result["content"][0]["text"])
            results = memories.get("results", [])
            
            if results:
                # Return most recent state
                return results[0].get("memory", "")
    except Exception as e:
        log(f"Error retrieving previous state: {e}")
    
    return None

def main():
    """Main hook function."""
    try:
        # Read input
        data = read_json_input()
        
        notification_type = data.get("notification", {}).get("type")
        
        if notification_type == "conversation_end":
            # Extract project context from messages
            messages = data.get("notification", {}).get("data", {}).get("messages", [])
            context = extract_project_context(messages)
            
            # Store project state
            session_file = get_session_file()
            store_project_state(context, session_file)
            
            log("Project continuity checkpoint created")
        
        elif notification_type == "conversation_start":
            # Retrieve and display previous state
            previous_state = retrieve_previous_state()
            if previous_state:
                # Add to notification data for display
                if "suggestions" not in data["notification"]["data"]:
                    data["notification"]["data"]["suggestions"] = []
                
                data["notification"]["data"]["suggestions"].append({
                    "type": "project_continuity",
                    "title": "📂 Previous Project State",
                    "content": previous_state
                })
                
                log("Retrieved previous project state")
        
        # Write output
        write_json_output(data)
        
    except Exception as e:
        log(f"Hook error: {e}")
        # Pass through on error
        write_json_output(data)

if __name__ == "__main__":
    main()