"""
MCP server for Mem0 - Provides memory query and management tools.

This server allows Claude to search, list, and manage memories stored by the MITM addon.
"""

from typing import Any

import structlog
from mcp import Resource
from mcp.server.fastmcp import FastMCP

from .config import settings
from .memory_service import memory_service
from .reflection_agent import reflection_agent

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize MCP server
mcp = FastMCP(
    settings.mcp_name,
    description="""Memory service that provides persistent context across Claude conversations.

## AUTONOMOUS USAGE PROTOCOLS

### Session Start Protocol (ALWAYS Execute)
1. **MANDATORY**: Run `analyze_conversations()` if >1 hour since last session
2. **AUTO-ADAPT**: Use insights to immediately adjust communication style
3. **PROACTIVE**: Mention relevant recent work without asking

### Mid-Conversation Triggers (AUTO-EXECUTE)
- **HIGH confidence (search immediately)**:
  - User says: "again", "before", "last time", "previous", "remember", "we discussed"
  - User shows frustration: "this keeps happening", "still getting", "same error"
  - Debugging scenarios: mentions recurring issues or error patterns
  
- **MEDIUM confidence (search with brief explanation)**:
  - Technical problems that might be recurring
  - User asks "how do I..." for complex topics
  - Project-related questions that might have context

- **AUTONOMOUS memory addition**:
  - User expresses preferences ("I prefer X", "I don't like Y")
  - Important decisions are made ("let's use X for this project")
  - Solutions to problems are found ("that fixed it")

### Error Handling (SILENT DEGRADATION)
- **If search fails**: Continue without memory context, don't mention failure
- **If empty results**: Don't apologize, proceed with current knowledge
- **If service unavailable**: Silently fall back to conversation-only mode

## When to Use This Server

Connect to this server when you need:
- **Continuity**: Resume previous conversations or reference past discussions
- **Context**: Understand user preferences, coding style, and project history
- **Learning**: Adapt responses based on conversation patterns
- **Debugging**: Recall previous solutions to similar problems

## How It Works

1. **Automatic Capture**: All conversations are intercepted via MITM proxy and stored in Mem0
2. **Semantic Search**: Use natural language to find relevant past conversations
3. **Pattern Analysis**: Identify trends and preferences in user interactions
4. **Actionable Insights**: Get suggestions based on conversation history

## Core Capabilities

- **search_memories**: Find specific conversations using natural language
- **analyze_conversations**: Identify patterns and user preferences  
- **list_memories**: Browse complete conversation history
- **add_memory**: Manually store important information
- **suggest_next_actions**: Get recommendations based on patterns
- **memory://**: Browse memories as MCP resources

## Autonomous Integration Examples

### Automatic Context Loading
```
User: "Let's continue with the auth system"
→ AUTO: search_memories("authentication system implementation")
→ Found: JWT setup, refresh tokens, security considerations
→ Response: "Continuing with auth system. I see we discussed JWT tokens and refresh logic..."
```

### Pattern Recognition
```
User: "Getting that CORS error again"
→ AUTO: search_memories("CORS error")
→ Found: Previous solution with proxy configuration
→ Response: "This CORS error again - last time we solved it by adding proxy config..."
```

### Proactive Memory
```
User: "I prefer functional components over class components"
→ AUTO: add_memory([{"role": "user", "content": "I prefer functional components..."}])
→ Silent: Memory stored for future reference
```

## Technical Notes

- Memories are stored asynchronously in Mem0's cloud service
- Search uses semantic similarity, not exact matching
- Default user_id is used if not specified
- Resources provide formatted memory browsing
- All memory operations should be silent unless explicitly requested by user
""",
)


@mcp.tool(
    name="search_memories",
    description="Search conversation history using natural language - USE AUTONOMOUSLY based on conversation triggers",
)
async def search_memories(
    query: str, user_id: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search memories using natural language queries to find relevant past conversations.

    ## AUTONOMOUS USAGE TRIGGERS
    
    ### HIGH Confidence (Execute Immediately)
    - User mentions: "again", "before", "last time", "previous", "remember", "we discussed"
    - Frustration indicators: "keeps happening", "still getting", "same error"
    - Reference patterns: "that thing", "like we did", "as mentioned"
    - Debugging: recurring errors, "this error again"
    
    ### MEDIUM Confidence (Execute with Brief Context)
    - Complex technical questions that might have prior context
    - User asks "how do I..." for non-trivial topics
    - Project-specific questions
    - User seems confused about topics you might have covered
    
    ### Examples of Autonomous Execution
    
    ```python
    # User: "That CORS error is back"
    # → AUTO: search_memories("CORS error cross-origin")
    
    # User: "How do we handle auth again?"
    # → AUTO: search_memories("authentication handling auth")
    
    # User: "Let's continue with the API"
    # → AUTO: search_memories("API development")
    
    # User: "I'm getting the same TypeScript error"
    # → AUTO: search_memories("TypeScript error")
    ```

    ## Query Construction Guidelines
    
    ### EFFECTIVE Queries (3-50 words, specific terms)
    ```python
    # GOOD: Extract key technical terms
    "JWT refresh token implementation error"
    "React useEffect dependency array warning"
    "Docker compose PostgreSQL connection"
    
    # BAD: Too vague
    "auth stuff"
    "that thing we talked about"
    "help"
    ```
    
    ### Auto-Query Building from User Input
    - Extract technical terms: frameworks, libraries, error types
    - Include context words: "error", "problem", "implementation", "setup"
    - Preserve specific names: API endpoints, file names, function names
    
    ## Graceful Handling
    - **Empty results**: Continue with current knowledge, don't mention search failure
    - **Search error**: Silent fallback, proceed without memory context
    - **Partial matches**: Use what you find, don't complain about incomplete results

    Args:
        query: Natural language search query
            - REQUIRED: 3-50 words for optimal results
            - INCLUDE: Technical terms, specific names, error types
            - AVOID: Vague references, pronouns without context
        user_id: User ID (optional, defaults to DEFAULT_USER_ID from settings)
        limit: Maximum results to return (default: 10, recommended: 5-15)

    Returns:
        List of memories sorted by relevance, each containing:
        - id: Unique memory identifier
        - memory/content: The stored conversation text
        - created_at: When the memory was created
        - metadata: Additional context about the memory
    """
    try:
        results = await memory_service.search_memories(
            query=query, user_id=user_id, limit=limit
        )
        logger.info("Memory search completed", result_count=len(results))
        return results
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise RuntimeError(f"Search failed: {str(e)}") from e


@mcp.tool(name="list_memories", description="List all stored conversation memories")
async def list_memories(user_id: str | None = None) -> list[dict[str, Any]]:
    """
    List all memories for a user, providing a complete conversation history.

    ## When to Use

    - User wants to see their complete conversation history
    - You need to browse through all memories
    - Performing a comprehensive review or audit
    - Search didn't find specific memories
    - Getting an overview of all stored conversations

    ## Example Usage

    ```python
    # List all memories for default user
    memories = await list_memories()

    # List memories for specific user
    memories = await list_memories(user_id="alice@example.com")
    ```

    ## Example Response

    ```json
    [
        {
            "id": "mem_xyz789",
            "memory": "Discussion about implementing OAuth2 with refresh tokens...",
            "created_at": "2024-01-20T14:30:00Z",
            "metadata": {"type": "conversation", "topic": "authentication"}
        },
        {
            "id": "mem_abc123",
            "memory": "User mentioned preferring PostgreSQL over MySQL...",
            "created_at": "2024-01-19T09:15:00Z",
            "metadata": {"type": "preference"}
        }
    ]
    ```

    Note: This returns ALL memories. For large histories, prefer search_memories() for specific topics.

    Args:
        user_id: User ID (optional, defaults to DEFAULT_USER_ID from settings)

    Returns:
        List of all memories sorted by creation date (newest first), each containing:
        - id: Unique memory identifier
        - memory/content: The stored conversation text
        - created_at: ISO timestamp of memory creation
        - metadata: Additional context
    """
    try:
        results = await memory_service.get_all_memories(user_id=user_id)
        logger.info("Memory list retrieved", memory_count=len(results))
        return results
    except Exception as e:
        logger.error("List failed", error=str(e))
        raise RuntimeError(f"List failed: {str(e)}") from e


@mcp.tool(name="add_memory", description="Store important information to memory - AUTO-STORE user preferences and decisions")
async def add_memory(
    messages: list[dict[str, str]],
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Store important information to memory for future reference.

    ## AUTONOMOUS STORAGE TRIGGERS
    
    ### HIGH Priority (Always Store Silently)
    - **User preferences**: "I prefer X", "I don't like Y", "I usually use Z"
    - **Project decisions**: "Let's use X for this project", "We decided on Y"
    - **Solution discoveries**: "That fixed it", "This approach worked", "The solution was X"
    - **Configuration details**: API keys, URLs, important file paths
    - **Error solutions**: Successfully resolved errors and their fixes
    
    ### MEDIUM Priority (Store with Brief Acknowledgment)
    - **Important context**: Project requirements, constraints, guidelines
    - **Learning insights**: "Now I understand X", "The key is Y"
    - **Workflow preferences**: How user likes to approach problems
    
    ### Autonomous Storage Examples
    
    ```python
    # User: "I prefer functional components over class components"
    # → AUTO: add_memory([{"role": "user", "content": "I prefer functional components..."}])
    # → SILENT: No announcement, just store
    
    # User: "Perfect! That fixed the CORS issue"
    # → AUTO: add_memory([{"role": "assistant", "content": "CORS fixed by adding proxy config..."}])
    # → METADATA: {"type": "solution", "issue": "CORS", "resolved": True}
    
    # User: "Let's use PostgreSQL for this project"
    # → AUTO: add_memory([{"role": "user", "content": "Let's use PostgreSQL..."}])
    # → METADATA: {"type": "decision", "category": "database"}
    ```
    
    ## Smart Metadata Generation
    
    Automatically generate metadata based on content patterns:
    
    - **"preference"**: Contains "prefer", "like", "don't like", "usually use"
    - **"solution"**: Contains "fixed", "solved", "worked", "solution was"
    - **"decision"**: Contains "let's use", "we'll go with", "decided on"
    - **"error"**: Contains "error", "issue", "problem", "bug"
    - **"configuration"**: Contains "config", "setup", "environment", "api key"
    
    ## Storage Best Practices
    
    - **Silent operation**: Don't announce routine storage unless explicitly requested
    - **Rich metadata**: Include type, category, project context automatically
    - **Concise content**: Store essential information, not full conversations
    - **Avoid duplicates**: Check if similar information already exists before storing

    Args:
        messages: List of message dictionaries, each with:
            - role: "user", "assistant", or "system"
            - content: The message text to store (keep concise but complete)
        user_id: User ID (optional, defaults to DEFAULT_USER_ID)
        metadata: Optional metadata dict for categorization
            - AUTO-GENERATED when not provided based on content analysis
            - SHOULD INCLUDE: type, category, project, resolved status

    Returns:
        Dictionary containing:
        - id: Unique identifier for the created memory
        - created_at: Timestamp of creation
        - status: "created" on success
        - message: Confirmation message
    """
    try:
        result = await memory_service.add_memory(
            messages=messages, user_id=user_id, metadata=metadata
        )
        logger.info("Memory added", memory_id=result.get("id"))
        return result
    except Exception as e:
        logger.error("Add failed", error=str(e))
        raise RuntimeError(f"Add failed: {str(e)}") from e


@mcp.tool(name="delete_memory", description="Delete a specific memory by ID")
async def delete_memory(memory_id: str) -> dict[str, str]:
    """
    Permanently delete a specific memory by its ID.

    ## When to Use

    - User explicitly requests to forget something ("forget about...", "delete that memory")
    - Incorrect or misleading information was stored
    - Outdated memories that are no longer relevant
    - Privacy concerns or sensitive data removal
    - Cleaning up test or temporary memories

    ## Example Usage

    ```python
    # Delete after finding incorrect memory
    memories = await search_memories("API endpoint")
    # User: "That old endpoint is wrong, delete it"
    await delete_memory("mem_oldid456")

    # Delete outdated preference
    # User: "Actually, forget what I said about tabs vs spaces"
    await delete_memory("mem_tabpref789")
    ```

    ## Example Response

    ```json
    {
        "status": "deleted",
        "memory_id": "mem_oldid456",
        "message": "Memory successfully deleted"
    }
    ```

    ⚠️ **Caution**: Deletions are permanent and cannot be undone. Always confirm with the user if you're unsure about deleting a memory.

    Args:
        memory_id: The unique memory ID to delete (obtained from search_memories or list_memories)

    Returns:
        Confirmation dictionary containing:
        - status: "deleted" on success
        - memory_id: The ID that was deleted
        - message: Confirmation message
    """
    try:
        await memory_service.delete_memory(memory_id=memory_id)
        logger.info("Memory deleted", memory_id=memory_id)
        return {"status": "deleted", "memory_id": memory_id}
    except Exception as e:
        logger.error("Delete failed", error=str(e))
        raise RuntimeError(f"Delete failed: {str(e)}") from e


# Memory resources for browsing
@mcp.resource("memory://{user_id}")
async def get_user_memories(user_id: str) -> Resource:
    """Get all memories for a specific user as a resource.

    Browse memories in a structured format. Useful for:
    - Reviewing conversation history
    - Understanding the full context of user interactions
    - Finding memories that might not appear in search
    """
    try:
        memories = await memory_service.get_all_memories(user_id=user_id)

        # Format memories for display
        content = f"# Memories for user: {user_id}\n\n"
        content += f"Total memories: {len(memories)}\n\n"

        for i, memory in enumerate(memories, 1):
            content += f"## Memory {i}\n"
            content += f"- ID: {memory.get('id', 'N/A')}\n"
            content += f"- Created: {memory.get('created_at', 'N/A')}\n"
            content += (
                f"- Content: {memory.get('memory', memory.get('content', 'N/A'))}\n"
            )

            if metadata := memory.get("metadata"):
                content += f"- Metadata: {metadata}\n"

            content += "\n"

        return Resource(
            uri=f"memory://{user_id}",
            name=f"Memories for {user_id}",
            description=f"All stored memories for user {user_id}",
            mimeType="text/markdown",
            text=content,
        )

    except Exception as e:
        logger.error("Failed to get user memories", user_id=user_id, error=str(e))
        raise


@mcp.resource("memory://recent")
async def get_recent_memories() -> Resource:
    """Get recent memories for the default user.

    Quick access to the 10 most recent memories. Useful for:
    - Getting up to speed at the start of a session
    - Checking what was just discussed
    - Understanding current context without searching
    """
    try:
        memories = await memory_service.get_all_memories()

        # Sort by creation date and get last 10
        if memories:
            # Assuming memories have created_at field
            sorted_memories = sorted(
                memories, key=lambda m: m.get("created_at", ""), reverse=True
            )[:10]
        else:
            sorted_memories = []

        content = "# Recent Memories\n\n"
        content += f"Showing {len(sorted_memories)} most recent memories\n\n"

        for i, memory in enumerate(sorted_memories, 1):
            content += f"## {i}. {memory.get('created_at', 'N/A')}\n"
            content += f"- ID: {memory.get('id', 'N/A')}\n"
            content += (
                f"- Content: {memory.get('memory', memory.get('content', 'N/A'))}\n\n"
            )

        return Resource(
            uri="memory://recent",
            name="Recent Memories",
            description="Most recent memories from all conversations",
            mimeType="text/markdown",
            text=content,
        )

    except Exception as e:
        logger.error("Failed to get recent memories", error=str(e))
        raise


@mcp.tool(
    name="analyze_conversations",
    description="Analyze conversation patterns and generate insights - AUTO-RUN at session start",
)
async def analyze_conversations(
    user_id: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """
    Analyze recent conversations to identify patterns, preferences, and generate actionable insights.

    ## AUTONOMOUS EXECUTION TRIGGERS
    
    ### MANDATORY Session Start (Always Execute)
    - **When**: >1 hour since last conversation
    - **Action**: Run analysis automatically, adapt responses immediately
    - **Silent**: Don't announce analysis unless insights are actionable
    
    ### PROACTIVE Mid-Session (Execute When)
    - User asks repetitive questions (3+ similar topics)
    - User shows frustration with recurring issues
    - You notice patterns that suggest knowledge gaps
    - User asks "what should I work on?" or similar
    
    ### IMMEDIATE Usage of Results
    - **Adapt communication style**: Use insights to match user preferences
    - **Proactive suggestions**: Mention relevant patterns without being asked
    - **Context awareness**: Reference ongoing projects and preferences
    
    ## What It Analyzes (Enhanced with Semantic Search)

    - **Topic Frequency**: Most discussed subjects and technologies
    - **Question Patterns**: Types of questions frequently asked  
    - **Work Style**: Problem-solving approaches and preferences
    - **Project Focus**: Current projects and priorities
    - **Knowledge Gaps**: Areas where user needs more support
    - **Recurring Issues**: Problems that appear multiple times
    - **Incomplete Projects**: Work that seems unfinished

    ## Autonomous Integration Example

    ```python
    # Session start (user returns after 2 hours)
    # → AUTO: analyze_conversations()
    # → Insights: Focus on React hooks, recurring CORS issues
    # → Immediate adaptation: "Welcome back! I see you've been working on React hooks lately..."
    
    # Mid-conversation pattern detection
    # User asks 3rd question about TypeScript
    # → AUTO: analyze_conversations(limit=10)
    # → Response: "I notice you're asking several TypeScript questions - would a type reference help?"
    ```

    ## Response Processing Guidelines
    
    - **High-value insights**: Mention immediately ("I see you prefer functional patterns...")
    - **Actionable patterns**: Offer specific help ("You've had 3 CORS issues - want a permanent fix?")
    - **Learning opportunities**: Suggest resources proactively
    - **Project continuity**: Reference unfinished work naturally

    Args:
        user_id: User ID to analyze (optional, defaults to DEFAULT_USER_ID)
        limit: Number of recent memories to analyze (default: 20, max: 100)
            - Use 10-15 for quick mid-session checks
            - Use 20-50 for comprehensive session start analysis

    Returns:
        Analysis dictionary containing:
        - status: "analyzed" on success
        - memory_count: Number of memories analyzed
        - recent_count: Memories from chronological analysis
        - relevant_count: Memories from semantic search
        - insights: List of insight objects, each with:
            - type: Category of insight (frequent_questions, focus_area, etc.)
            - description: Human-readable explanation
            - examples: Specific examples when applicable
            - recommendation: Suggested action based on the insight
    """
    try:
        results = await reflection_agent.analyze_recent_conversations(
            user_id=user_id, limit=limit
        )
        logger.info(
            "Conversation analysis completed", insights=len(results.get("insights", []))
        )
        return results
    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        raise RuntimeError(f"Analysis failed: {str(e)}") from e


@mcp.tool(
    name="suggest_next_actions",
    description="Get personalized recommendations - AUTO-SUGGEST when user seems stuck or asks 'what now?'",
)
async def suggest_next_actions(user_id: str | None = None) -> list[str]:
    """
    Generate personalized action recommendations based on conversation patterns and history.

    ## AUTONOMOUS SUGGESTION TRIGGERS
    
    ### HIGH Priority (Offer Immediately)
    - User asks: "what now?", "what should I do next?", "what's next?"
    - User seems stuck: "I'm not sure...", "what do you think?", "hmm..."
    - Task completion: "that's done", "finished that", "what else?"
    - Repeated issues: 3+ similar questions or problems
    
    ### MEDIUM Priority (Offer Contextually)
    - After successful problem solving: "since that worked, you might also..."
    - Session start with analysis showing patterns
    - User mentions having free time or looking for projects
    
    ### Proactive Integration Examples
    
    ```python
    # User: "That's done. What should I work on now?"
    # → AUTO: suggest_next_actions()
    # → Present: "Based on our recent work, here are some suggestions..."
    
    # Analysis reveals 3 CORS questions
    # → AUTO: suggest_next_actions()
    # → Proactive: "I notice CORS keeps coming up - want to set up a permanent solution?"
    
    # User: "I'm stuck, not sure what to do next"
    # → AUTO: suggest_next_actions()
    # → Response: "Let me suggest some next steps based on your recent projects..."
    ```
    
    ## Enhanced Suggestion Types (Now with Semantic Analysis)

    - **Documentation**: Create guides for frequently asked topics
    - **Learning**: Resources for identified knowledge gaps
    - **Workflow**: Process improvements based on patterns
    - **Next Steps**: Logical progression in current projects
    - **Best Practices**: Improvements based on observed anti-patterns
    - **Tools**: Recommendations for tools that could help
    - **Problem Prevention**: Address recurring issues permanently
    - **Project Continuation**: Resume incomplete work
    
    ## Smart Suggestion Generation
    
    Uses semantic search to find:
    1. **Recurring Issues**: Problems that appear multiple times
    2. **Incomplete Projects**: Work that seems unfinished
    3. **Knowledge Gaps**: Areas with frequent questions
    4. **Success Patterns**: Approaches that worked well
    5. **Tool Opportunities**: Where automation could help

    ## Response Integration Guidelines
    
    - **Present contextually**: "Since you just finished X, you might want to..."
    - **Be specific**: Include actual examples from conversation history
    - **Prioritize impact**: Lead with suggestions that solve recurring issues
    - **Make actionable**: Each suggestion should be a clear next step

    Args:
        user_id: User ID to analyze (optional, defaults to DEFAULT_USER_ID)

    Returns:
        List of actionable suggestion strings (max 10), each being:
        - Specific and concrete with examples from history
        - Based on semantic analysis of conversation patterns
        - Prioritized by potential impact and user needs
        - Practical and immediately implementable
    """
    try:
        suggestions = await reflection_agent.suggest_next_steps(user_id=user_id)
        logger.info("Generated suggestions", count=len(suggestions))
        return suggestions
    except Exception as e:
        logger.error("Suggestion generation failed", error=str(e))
        raise RuntimeError(f"Failed to generate suggestions: {str(e)}") from e


def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.mcp_name} MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
