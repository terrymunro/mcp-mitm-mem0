#!/usr/bin/env python3
"""
Automatic reflection hook for intelligent conversation analysis.
Triggers reflection based on conversation patterns and complexity.
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

# Reflection trigger thresholds
REFLECTION_TRIGGERS = {
    "message_count": 20,  # Trigger after N messages
    "error_count": 3,     # Trigger after N errors
    "tool_count": 15,     # Trigger after N tool uses
    "time_elapsed": 1800,  # Trigger after 30 minutes
    "complexity_score": 50  # Trigger at complexity threshold
}

def calculate_conversation_complexity(messages: List[Dict]) -> int:
    """Calculate complexity score based on conversation patterns."""
    complexity = 0
    
    for msg in messages:
        content = msg.get("content", "")
        
        # Tool usage adds complexity
        if "tool_name" in msg:
            complexity += 3
            
        # Errors add significant complexity
        if any(err in content.lower() for err in ["error", "failed", "exception"]):
            complexity += 5
            
        # Long messages indicate complex topics
        if len(content) > 1000:
            complexity += 2
            
        # Code blocks indicate technical discussion
        if "```" in content:
            complexity += 2
            
        # Multiple file edits indicate project work
        if any(tool in content for tool in ["Edit", "MultiEdit", "Write"]):
            complexity += 3
    
    return complexity

def should_trigger_reflection(session_data: Dict) -> tuple[bool, str]:
    """Determine if reflection should be triggered."""
    stats = session_data.get("conversation_stats", {})
    
    # Check message count
    if stats.get("message_count", 0) >= REFLECTION_TRIGGERS["message_count"]:
        return True, f"Message count ({stats['message_count']}) reached threshold"
    
    # Check error count
    if stats.get("error_count", 0) >= REFLECTION_TRIGGERS["error_count"]:
        return True, f"Error count ({stats['error_count']}) reached threshold"
    
    # Check tool usage
    if stats.get("tool_count", 0) >= REFLECTION_TRIGGERS["tool_count"]:
        return True, f"Tool usage ({stats['tool_count']}) reached threshold"
    
    # Check time elapsed
    start_time = session_data.get("start_time")
    if start_time:
        elapsed = (datetime.now() - datetime.fromisoformat(start_time)).seconds
        if elapsed >= REFLECTION_TRIGGERS["time_elapsed"]:
            return True, f"Time elapsed ({elapsed}s) reached threshold"
    
    # Check complexity
    if stats.get("complexity_score", 0) >= REFLECTION_TRIGGERS["complexity_score"]:
        return True, f"Complexity score ({stats['complexity_score']}) reached threshold"
    
    return False, ""

def trigger_reflection_analysis(messages: List[Dict], reason: str) -> Optional[Dict]:
    """Trigger reflection agent to analyze conversation."""
    try:
        client = get_mcp_client()
        
        # Prepare focused analysis request
        analysis_prompt = f"""Automatic reflection triggered: {reason}

Please analyze this conversation for:
1. Key learnings and solutions discovered
2. Patterns that should be remembered
3. User preferences demonstrated
4. Common errors and their resolutions
5. Project-specific insights

Focus on actionable insights that will improve future assistance."""
        
        result = client.call_tool(
            "mcp__memory__analyze_conversations",
            {"limit": len(messages)}
        )
        
        if result and result.get("content"):
            analysis = json.loads(result["content"][0]["text"])
            
            # Store the analysis as a special memory
            client.call_tool(
                "mcp__memory__add_memory",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Reflection Analysis - {reason}\n\n{json.dumps(analysis, indent=2)}"
                        }
                    ],
                    "metadata": {
                        "type": "reflection_analysis",
                        "trigger_reason": reason,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )
            
            return analysis
    except Exception as e:
        log(f"Error triggering reflection: {e}")
    
    return None

def update_session_stats(session_file: Path, data: Dict):
    """Update session statistics for reflection triggers."""
    session_data = {}
    if session_file.exists():
        session_data = json.loads(session_file.read_text())
    
    # Initialize stats if not present
    if "conversation_stats" not in session_data:
        session_data["conversation_stats"] = {
            "message_count": 0,
            "error_count": 0,
            "tool_count": 0,
            "complexity_score": 0,
            "start_time": datetime.now().isoformat()
        }
    
    stats = session_data["conversation_stats"]
    
    # Update based on current data
    if data.get("type") == "response":
        stats["message_count"] += 1
        
        # Check for errors
        response = data.get("response", "")
        if any(err in response.lower() for err in ["error", "failed", "exception"]):
            stats["error_count"] += 1
    
    elif data.get("tool_name"):
        stats["tool_count"] += 1
    
    # Update complexity if messages provided
    if "messages" in data:
        stats["complexity_score"] = calculate_conversation_complexity(data["messages"])
    
    # Check if reflection should trigger
    should_trigger, reason = should_trigger_reflection(session_data)
    
    if should_trigger:
        log(f"Triggering automatic reflection: {reason}")
        
        # Get recent messages
        messages = data.get("messages", [])
        if messages:
            analysis = trigger_reflection_analysis(messages, reason)
            
            if analysis:
                # Reset counters after successful reflection
                stats["message_count"] = 0
                stats["error_count"] = 0
                stats["tool_count"] = 0
                stats["complexity_score"] = 0
                stats["last_reflection"] = datetime.now().isoformat()
                
                # Add reflection notice to response
                if data.get("type") == "response":
                    data["response"] += f"\n\n💭 *Automatic reflection completed: {reason}*"
    
    # Save updated stats
    session_file.write_text(json.dumps(session_data, indent=2))

def main():
    """Main hook function."""
    try:
        # Read input
        data = read_json_input()
        
        # Get session file
        session_file = get_session_file()
        
        # Update session statistics
        update_session_stats(session_file, data)
        
        # Write output
        write_json_output(data)
        
    except Exception as e:
        log(f"Hook error: {e}")
        # Pass through on error
        write_json_output(data)

if __name__ == "__main__":
    main()