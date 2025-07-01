#!/usr/bin/env python3
"""
Memory analysis hook for Claude Code.

This hook triggers reflection analysis automatically at key points,
ensuring conversation patterns are analyzed and insights are captured
without relying on Claude to remember to do analysis.

Usage:
- Stop hook: Analyze conversations when Claude finishes responding
- Can be configured to trigger based on conversation length or complexity
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils import (
    HookResponse, HookError, read_hook_input, log_hook_execution,
    analyze_conversations_async, safe_execute_hook,
    get_user_id_from_input
)


def should_trigger_analysis(input_data: Dict[str, Any]) -> bool:
    """Determine if analysis should be triggered based on conversation context."""
    
    # Always trigger if stop_hook_active is False (first stop in a session)
    if not input_data.get("stop_hook_active", False):
        return True
    
    # Check if we have a transcript to analyze
    transcript_path = input_data.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        return False
    
    # Analyze transcript to determine if analysis is worthwhile
    try:
        with open(transcript_path, 'r') as f:
            # Count lines to estimate conversation length
            line_count = sum(1 for line in f)
            
            # Trigger analysis if conversation is substantial
            if line_count > 20:  # Arbitrary threshold for "substantial"
                return True
    
    except Exception:
        # If we can't read the transcript, default to not triggering
        pass
    
    return False


def analyze_transcript_for_patterns(transcript_path: str) -> Dict[str, Any]:
    """Analyze the transcript file for patterns that might warrant analysis."""
    
    if not Path(transcript_path).exists():
        return {"should_analyze": False, "reason": "Transcript not found"}
    
    try:
        patterns = {
            "error_count": 0,
            "solution_count": 0,
            "question_count": 0,
            "tool_usage_count": 0,
            "code_blocks": 0,
            "total_messages": 0
        }
        
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    patterns["total_messages"] += 1
                    
                    # Look for content in the entry
                    content = ""
                    if isinstance(entry, dict):
                        if "content" in entry:
                            content = str(entry["content"]).lower()
                        elif "message" in entry and isinstance(entry["message"], dict):
                            content = str(entry["message"].get("content", "")).lower()
                    
                    if content:
                        # Count patterns
                        if any(error_word in content for error_word in ["error", "failed", "exception", "traceback"]):
                            patterns["error_count"] += 1
                        
                        if any(solution_word in content for solution_word in ["fixed", "solved", "working", "success"]):
                            patterns["solution_count"] += 1
                        
                        if "?" in content:
                            patterns["question_count"] += 1
                        
                        if any(tool_word in content for tool_word in ["tool_name", "function_call", "bash", "edit"]):
                            patterns["tool_usage_count"] += 1
                        
                        if "```" in content:
                            patterns["code_blocks"] += 1
                
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        
        # Determine if analysis is worthwhile
        analysis_score = (
            patterns["error_count"] * 2 +  # Errors are high value
            patterns["solution_count"] * 3 +  # Solutions are very high value
            patterns["question_count"] +  # Questions indicate learning
            patterns["tool_usage_count"] +  # Tool usage indicates work
            patterns["code_blocks"]  # Code indicates technical work
        )
        
        should_analyze = analysis_score >= 5 or patterns["total_messages"] >= 30
        
        return {
            "should_analyze": should_analyze,
            "patterns": patterns,
            "analysis_score": analysis_score,
            "reason": f"Score: {analysis_score}, Messages: {patterns['total_messages']}"
        }
    
    except Exception as e:
        return {"should_analyze": False, "reason": f"Error analyzing transcript: {e}"}


def format_analysis_results(analysis_results: Dict[str, Any]) -> str:
    """Format analysis results for display to Claude."""
    
    if not analysis_results or analysis_results.get("status") != "analyzed":
        return "Analysis completed but no specific insights generated."
    
    insights = analysis_results.get("insights", [])
    if not insights:
        return "Analysis completed but no specific patterns identified."
    
    formatted = "## Conversation Analysis Results\n\n"
    
    memory_stats = {
        "memory_count": analysis_results.get("memory_count", 0),
        "recent_count": analysis_results.get("recent_count", 0),
        "relevant_count": analysis_results.get("relevant_count", 0)
    }
    
    formatted += f"Analyzed {memory_stats['memory_count']} memories "
    formatted += f"({memory_stats['recent_count']} recent, {memory_stats['relevant_count']} semantically relevant)\n\n"
    
    # Group insights by type
    insight_groups = {}
    for insight in insights:
        insight_type = insight.get("type", "general")
        if insight_type not in insight_groups:
            insight_groups[insight_type] = []
        insight_groups[insight_type].append(insight)
    
    # Format each group
    for group_type, group_insights in insight_groups.items():
        formatted += f"### {group_type.replace('_', ' ').title()}\n"
        
        for insight in group_insights:
            description = insight.get("description", "")
            recommendation = insight.get("recommendation", "")
            examples = insight.get("examples", [])
            
            formatted += f"- {description}\n"
            
            if recommendation:
                formatted += f"  - **Recommendation**: {recommendation}\n"
            
            if examples:
                formatted += f"  - **Examples**: {', '.join(examples[:2])}\n"
        
        formatted += "\n"
    
    return formatted


async def perform_analysis(user_id: str = None, limit: int = 25) -> Optional[Dict[str, Any]]:
    """Perform conversation analysis using the reflection agent."""
    
    try:
        # Trigger analysis
        results = await analyze_conversations_async(user_id=user_id, limit=limit)
        return results
    
    except Exception as e:
        # Log error but don't fail the hook
        safe_execute_hook(lambda: print(f"Analysis error: {e}", file=sys.stderr))
        return None


async def main():
    """Main hook execution function."""
    start_time = time.time()
    
    try:
        # Read hook input
        input_data = read_hook_input()
        
        # Extract relevant information
        session_id = input_data.get("session_id", "")
        transcript_path = input_data.get("transcript_path", "")
        stop_hook_active = input_data.get("stop_hook_active", False)
        user_id = get_user_id_from_input(input_data)
        
        # Log execution
        log_hook_execution("memory_analyze", input_data, start_time)
        
        # Check if we should trigger analysis
        if not should_trigger_analysis(input_data):
            response = HookResponse()
            response.set_suppress_output(True)
            response.output()
        
        # Analyze transcript to get more context
        transcript_analysis = analyze_transcript_for_patterns(transcript_path)
        
        # If transcript analysis suggests we shouldn't analyze, respect that
        if not transcript_analysis.get("should_analyze", False):
            response = HookResponse()
            response.set_suppress_output(True)
            response.output()
        
        # Perform the analysis
        analysis_results = await perform_analysis(user_id=user_id, limit=30)
        
        # Create response
        response = HookResponse()
        
        if analysis_results and analysis_results.get("insights"):
            # Format and display results
            formatted_results = format_analysis_results(analysis_results)
            print(f"🧠 Conversation analysis completed:\n\n{formatted_results}")
            
            # Add analysis metadata to response
            response.add_data("analysis_completed", True)
            response.add_data("insights_count", len(analysis_results.get("insights", [])))
            response.add_data("transcript_patterns", transcript_analysis.get("patterns", {}))
            
            response.set_suppress_output(False)  # Show in transcript
        else:
            # Analysis completed but no insights to show
            patterns = transcript_analysis.get("patterns", {})
            if patterns.get("total_messages", 0) > 10:
                print(f"📊 Analyzed conversation ({patterns['total_messages']} messages) - no specific patterns identified")
            
            response.set_suppress_output(True)
        
        response.output()
        
    except HookError as e:
        # Hook-specific error - log and exit gracefully
        safe_execute_hook(lambda: print(f"Memory analysis hook error: {e}", file=sys.stderr))
        sys.exit(1)
    
    except Exception as e:
        # Unexpected error - don't block Claude, just log
        safe_execute_hook(lambda: print(f"Unexpected error in memory analysis hook: {e}", file=sys.stderr))
        sys.exit(0)  # Don't block operation


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())