#!/usr/bin/env python3
"""
Pre-response hook for error pattern detection and prevention.
Analyzes Claude's responses for error patterns and injects preventive suggestions.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    read_json_input, write_json_output, log,
    get_mcp_client, ERROR_PATTERNS, PREVENTION_SUGGESTIONS
)

def detect_error_patterns(response: str) -> List[str]:
    """Detect potential error patterns in Claude's response."""
    detected_patterns = []
    
    # Check for error keywords
    error_keywords = [
        "error", "failed", "exception", "not found", "permission denied",
        "unable to", "cannot", "invalid", "undefined", "null reference"
    ]
    
    response_lower = response.lower()
    for keyword in error_keywords:
        if keyword in response_lower:
            detected_patterns.append(keyword)
    
    # Check for specific error patterns
    patterns = {
        r"ImportError|ModuleNotFoundError": "import_error",
        r"TypeError|AttributeError": "type_error",
        r"FileNotFoundError|No such file": "file_not_found",
        r"PermissionError|Permission denied": "permission_error",
        r"SyntaxError|IndentationError": "syntax_error",
        r"KeyError|IndexError": "access_error",
        r"ConnectionError|TimeoutError": "network_error"
    }
    
    for pattern, error_type in patterns.items():
        if re.search(pattern, response, re.IGNORECASE):
            detected_patterns.append(error_type)
    
    return list(set(detected_patterns))  # Remove duplicates

def search_similar_errors(patterns: List[str]) -> List[Dict[str, Any]]:
    """Search memory for similar error patterns and their solutions."""
    if not patterns:
        return []
    
    try:
        client = get_mcp_client()
        
        # Build search query
        query = f"error resolution solution fixed {' OR '.join(patterns)}"
        
        result = client.call_tool(
            "mcp__memory__search_memories",
            {"query": query, "limit": 5}
        )
        
        if result and result.get("content"):
            memories = json.loads(result["content"][0]["text"])
            return memories.get("results", [])
    except Exception as e:
        log(f"Error searching memories: {e}")
    
    return []

def generate_prevention_suggestions(patterns: List[str], similar_errors: List[Dict]) -> Optional[str]:
    """Generate preventive suggestions based on detected patterns."""
    if not patterns and not similar_errors:
        return None
    
    suggestions = []
    
    # Add pattern-specific suggestions
    for pattern in patterns:
        if pattern in PREVENTION_SUGGESTIONS:
            suggestions.append(f"⚠️ {pattern}: {PREVENTION_SUGGESTIONS[pattern]}")
    
    # Add suggestions from similar errors
    if similar_errors:
        suggestions.append("\n📚 Similar errors resolved previously:")
        for error in similar_errors[:3]:  # Top 3 similar errors
            memory_text = error.get("memory", "")
            # Extract solution from memory
            if "fixed" in memory_text.lower() or "resolved" in memory_text.lower():
                suggestions.append(f"  • {memory_text[:200]}...")
    
    if suggestions:
        return "\n".join(suggestions)
    
    return None

def inject_suggestions(response: str, suggestions: str) -> str:
    """Inject prevention suggestions into Claude's response."""
    # Find a good injection point (after error message, before code blocks)
    lines = response.split('\n')
    injection_index = -1
    
    for i, line in enumerate(lines):
        # Look for error messages or before code blocks
        if any(err in line.lower() for err in ["error", "failed", "exception"]):
            injection_index = i + 1
            break
        elif line.strip().startswith("```") and i > 0:
            injection_index = i
            break
    
    if injection_index == -1:
        # If no good spot found, add at the beginning
        injection_index = 0
    
    # Create the suggestion block
    suggestion_block = [
        "",
        "---",
        "💡 **Error Prevention Suggestions:**",
        suggestions,
        "---",
        ""
    ]
    
    # Insert the suggestions
    lines[injection_index:injection_index] = suggestion_block
    
    return '\n'.join(lines)

def main():
    """Main hook function."""
    try:
        # Read input
        data = read_json_input()
        
        if data["type"] != "response":
            write_json_output(data)
            return
        
        response_text = data.get("response", "")
        
        # Detect error patterns
        patterns = detect_error_patterns(response_text)
        
        if patterns:
            log(f"Detected error patterns: {patterns}")
            
            # Search for similar errors
            similar_errors = search_similar_errors(patterns)
            
            # Generate prevention suggestions
            suggestions = generate_prevention_suggestions(patterns, similar_errors)
            
            if suggestions:
                # Inject suggestions into response
                modified_response = inject_suggestions(response_text, suggestions)
                data["response"] = modified_response
                log("Injected error prevention suggestions")
        
        # Write output
        write_json_output(data)
        
    except Exception as e:
        log(f"Hook error: {e}")
        # Pass through on error
        write_json_output(data)

if __name__ == "__main__":
    main()