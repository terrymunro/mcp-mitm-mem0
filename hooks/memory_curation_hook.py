#!/usr/bin/env python3
"""
Memory curation hook for organizing and enhancing stored memories.
Adds tags, categories, and relationships to improve memory retrieval.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    read_json_input, write_json_output, log,
    get_mcp_client
)

# Memory categorization patterns
MEMORY_CATEGORIES = {
    "error_solution": {
        "patterns": ["fixed", "resolved", "solution", "workaround"],
        "tags": ["troubleshooting", "debugging", "fixes"]
    },
    "configuration": {
        "patterns": ["config", "settings", "preferences", "setup"],
        "tags": ["configuration", "setup", "preferences"]
    },
    "best_practice": {
        "patterns": ["best practice", "recommended", "should", "pattern"],
        "tags": ["best-practices", "patterns", "guidelines"]
    },
    "command_reference": {
        "patterns": ["command", "bash", "npm", "git", "python"],
        "tags": ["commands", "cli", "reference"]
    },
    "project_specific": {
        "patterns": ["project", "codebase", "architecture", "structure"],
        "tags": ["project", "architecture", "codebase"]
    },
    "user_preference": {
        "patterns": ["prefer", "like", "want", "style", "approach"],
        "tags": ["preferences", "user-style", "personal"]
    },
    "learning": {
        "patterns": ["learned", "discovered", "realized", "understand"],
        "tags": ["learning", "insights", "discoveries"]
    },
    "api_reference": {
        "patterns": ["api", "endpoint", "function", "method", "class"],
        "tags": ["api", "reference", "documentation"]
    }
}

def categorize_memory(content: str) -> tuple[str, List[str]]:
    """Categorize memory content and return category and tags."""
    content_lower = content.lower()
    
    # Check each category
    for category, info in MEMORY_CATEGORIES.items():
        for pattern in info["patterns"]:
            if pattern in content_lower:
                return category, info["tags"]
    
    # Default category
    return "general", ["uncategorized"]

def extract_entities(content: str) -> List[str]:
    """Extract important entities from memory content."""
    entities = []
    
    # Extract file names
    file_patterns = [
        r'([a-zA-Z0-9_\-]+\.[a-zA-Z]+)',  # filename.ext
        r'`([^`]+)`',  # code in backticks
        r'"([^"]+\.[a-zA-Z]+)"',  # quoted filenames
    ]
    
    for pattern in file_patterns:
        matches = re.findall(pattern, content)
        entities.extend(matches)
    
    # Extract command names
    command_pattern = r'(?:^|\s)(npm|git|python|bash|uv|cargo|go)\s+(\w+)'
    command_matches = re.findall(command_pattern, content, re.MULTILINE)
    for cmd, subcmd in command_matches:
        entities.append(f"{cmd}_{subcmd}")
    
    # Extract error types
    error_pattern = r'(\w+Error|Exception\w*)'
    error_matches = re.findall(error_pattern, content)
    entities.extend(error_matches)
    
    return list(set(entities))  # Remove duplicates

def find_related_memories(content: str, entities: List[str]) -> List[str]:
    """Find memories related to current content."""
    try:
        client = get_mcp_client()
        
        # Build search query from entities
        if entities:
            query = " OR ".join(entities[:5])  # Use top 5 entities
        else:
            # Fallback to key words from content
            words = content.split()[:10]
            query = " ".join(words)
        
        result = client.call_tool(
            "mcp__memory__search_memories",
            {"query": query, "limit": 5}
        )
        
        if result and result.get("content"):
            memories = json.loads(result["content"][0]["text"])
            return [m.get("id") for m in memories.get("results", []) if m.get("id")]
    except Exception as e:
        log(f"Error finding related memories: {e}")
    
    return []

def enhance_memory_metadata(memory_data: Dict) -> Dict:
    """Enhance memory with additional metadata for better retrieval."""
    content = memory_data.get("content", "")
    
    # Categorize the memory
    category, tags = categorize_memory(content)
    
    # Extract entities
    entities = extract_entities(content)
    
    # Find related memories
    related_ids = find_related_memories(content, entities)
    
    # Build enhanced metadata
    enhanced_metadata = memory_data.get("metadata", {})
    enhanced_metadata.update({
        "category": category,
        "tags": tags,
        "entities": entities[:10],  # Limit to 10 entities
        "related_memories": related_ids[:3],  # Top 3 related
        "curated": True,
        "curation_timestamp": datetime.now().isoformat()
    })
    
    # Add search keywords for better retrieval
    search_keywords = set()
    search_keywords.update(tags)
    search_keywords.update(entities[:5])
    search_keywords.add(category)
    enhanced_metadata["search_keywords"] = list(search_keywords)
    
    return enhanced_metadata

def curate_stored_memory(tool_result: Dict) -> Dict:
    """Curate a memory that was just stored."""
    try:
        # Extract memory ID from result
        result_text = tool_result.get("content", [{}])[0].get("text", "{}")
        result_data = json.loads(result_text)
        memory_id = result_data.get("id")
        
        if not memory_id:
            return tool_result
        
        log(f"Curating memory: {memory_id}")
        
        # Get the original memory data from the tool input
        # This is a simplified approach - in production you'd fetch from Mem0
        # For now we'll enhance based on what we have
        
        client = get_mcp_client()
        
        # Search for the memory we just created
        search_result = client.call_tool(
            "mcp__memory__search_memories",
            {"query": f"id:{memory_id}", "limit": 1}
        )
        
        if search_result and search_result.get("content"):
            memories = json.loads(search_result["content"][0]["text"])
            if memories.get("results"):
                memory = memories["results"][0]
                
                # Enhance metadata
                enhanced_metadata = enhance_memory_metadata({
                    "content": memory.get("memory", ""),
                    "metadata": memory.get("metadata", {})
                })
                
                # Log curation details
                log(f"Added tags: {enhanced_metadata.get('tags', [])}")
                log(f"Category: {enhanced_metadata.get('category', 'general')}")
                log(f"Entities: {len(enhanced_metadata.get('entities', []))}")
                
                # Add curation notice to result
                tool_result["curated"] = True
                tool_result["curation_metadata"] = enhanced_metadata
    
    except Exception as e:
        log(f"Error curating memory: {e}")
    
    return tool_result

def main():
    """Main hook function."""
    try:
        # Read input
        data = read_json_input()
        
        # Check if this is a memory storage operation
        if (data.get("tool_name") == "mcp__memory__add_memory" and 
            data.get("tool_result")):
            # Curate the stored memory
            data["tool_result"] = curate_stored_memory(data["tool_result"])
            log("Memory curated successfully")
        
        # Write output
        write_json_output(data)
        
    except Exception as e:
        log(f"Hook error: {e}")
        # Pass through on error
        write_json_output(data)

if __name__ == "__main__":
    main()