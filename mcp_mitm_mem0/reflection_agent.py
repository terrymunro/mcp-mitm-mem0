"""
Reflection agent for analyzing conversations and curating memories.

This agent reviews conversations between the user and Claude, identifies patterns,
and can add enriched memories or hints back to the memory store.
"""

from typing import Any

import structlog
from claude_code_sdk import AssistantMessage, ClaudeCodeOptions, TextBlock, query

from .config import settings
from .memory_service import memory_service

logger = structlog.get_logger(__name__)


class ReflectionAgent:
    """Agent that reflects on conversations and curates memory insights."""

    def __init__(self, review_threshold: int = 5):
        """Initialize the reflection agent.

        Args:
            review_threshold: Number of new memories before triggering reflection
        """
        self.review_threshold = review_threshold
        self._processed_memory_ids = set()
        self._logger = logger.bind(agent="reflection")

    async def analyze_recent_conversations(
        self, user_id: str | None = None, limit: int = 20
    ) -> dict[str, Any]:
        """Analyze recent conversations and generate insights using semantic search.

        Args:
            user_id: User to analyze (defaults to settings)
            limit: Number of recent memories to analyze

        Returns:
            Analysis results with patterns and suggestions
        """
        user_id = user_id or settings.default_user_id

        try:
            # Get a mix of recent and semantically relevant memories
            all_memories = await memory_service.get_all_memories(user_id=user_id)
            
            if not all_memories:
                return {"status": "no_memories", "insights": []}

            # Get recent memories for recency bias
            recent_memories = sorted(
                all_memories, key=lambda m: m.get("created_at", ""), reverse=True
            )[:limit//2]  # Half from recent

            # Get semantically relevant memories using pattern-based queries
            relevant_memories = await self._get_relevant_memories_for_analysis(
                user_id=user_id, 
                recent_memories=recent_memories,
                remaining_limit=limit - len(recent_memories)
            )

            # Combine and deduplicate
            combined_memories = self._deduplicate_memories(recent_memories + relevant_memories)
            
            insights = await self._analyze_patterns(combined_memories)

            if insights:
                await self._store_reflection(insights, user_id)

            return {
                "status": "analyzed",
                "memory_count": len(combined_memories),
                "recent_count": len(recent_memories),
                "relevant_count": len(relevant_memories),
                "insights": insights,
            }

        except Exception as e:
            self._logger.error("Failed to analyze conversations", error=str(e))
            raise

    async def _analyze_patterns(
        self, memories: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Analyze memory patterns and extract insights.

        Args:
            memories: List of memories to analyze

        Returns:
            List of insights with type and description
        """
        insights = []

        # Track topics discussed
        topics = {}
        questions_asked = []
        approaches_tried = []

        for memory in memories:
            content = memory.get("memory", memory.get("content", ""))

            # Simple pattern matching (could be enhanced with LLM analysis)
            if isinstance(content, str):
                # Track questions
                if "?" in content:
                    questions_asked.append(content)

                # Track code-related discussions
                if any(
                    keyword in content.lower()
                    for keyword in ["function", "class", "implement", "code", "debug"]
                ):
                    if "coding" not in topics:
                        topics["coding"] = 0
                    topics["coding"] += 1

                # Track problem-solving approaches
                if any(
                    keyword in content.lower()
                    for keyword in ["try", "attempt", "approach", "solution"]
                ):
                    approaches_tried.append(content)

        # Generate insights based on patterns
        if len(questions_asked) > 3:
            insights.append({
                "type": "frequent_questions",
                "description": f"User has asked {len(questions_asked)} questions recently. Consider providing more proactive information.",
                "examples": questions_asked[-3:],
            })

        if topics:
            most_discussed = max(topics.items(), key=lambda x: x[1])
            insights.append({
                "type": "focus_area",
                "description": f"Primary focus appears to be on {most_discussed[0]} (mentioned {most_discussed[1]} times)",
                "recommendation": f"Consider preparing more detailed resources on {most_discussed[0]}",
            })

        if len(approaches_tried) > 2:
            insights.append({
                "type": "problem_solving_pattern",
                "description": "Multiple approaches being tried, suggesting iterative problem solving",
                "recommendation": "Consider suggesting a structured approach or framework",
            })

        return insights

    async def _store_reflection(
        self, insights: list[dict[str, Any]], user_id: str
    ) -> dict[str, Any]:
        """Store reflection insights as a special memory.

        Args:
            insights: List of insights to store
            user_id: User ID for the memory

        Returns:
            Created memory result
        """
        # Format insights as a reflection message
        reflection_content = "## Conversation Analysis\n\n"

        for insight in insights:
            reflection_content += f"### {insight['type'].replace('_', ' ').title()}\n"
            reflection_content += f"{insight['description']}\n"

            if "recommendation" in insight:
                reflection_content += (
                    f"**Recommendation:** {insight['recommendation']}\n"
                )

            if "examples" in insight:
                reflection_content += "\n**Examples:**\n"
                for example in insight["examples"][:3]:
                    reflection_content += f"- {example[:100]}...\n"

            reflection_content += "\n"

        # Store as a reflection memory
        messages = [
            {"role": "system", "content": "Reflection Agent Analysis"},
            {"role": "assistant", "content": reflection_content},
        ]

        metadata = {
            "type": "reflection",
            "source": "reflection_agent",
            "insight_count": len(insights),
        }

        result = await memory_service.add_memory(
            messages=messages, user_id=user_id, metadata=metadata
        )

        self._logger.info(
            "Stored reflection insights",
            user_id=user_id,
            insight_count=len(insights),
            memory_id=result.get("id"),
        )

        return result

    async def suggest_next_steps(self, user_id: str | None = None) -> list[str]:
        """Suggest next steps based on conversation history using semantic analysis.

        Args:
            user_id: User to analyze (defaults to settings)

        Returns:
            List of suggested next steps
        """
        user_id = user_id or settings.default_user_id

        try:
            # Analyze recent conversations
            analysis = await self.analyze_recent_conversations(user_id=user_id)
            insights = analysis.get("insights", [])

            # Search for repeated issues or incomplete projects
            issue_memories = await memory_service.search_memories(
                query="error problem issue bug failed", user_id=user_id, limit=10
            )
            
            project_memories = await memory_service.search_memories(
                query="implement build create project working on", user_id=user_id, limit=10
            )

            suggestions = []

            # Generate suggestions from pattern analysis
            for insight in insights:
                if insight["type"] == "frequent_questions":
                    examples = insight.get("examples", [])
                    if examples:
                        topic = self._extract_topic_from_questions(examples)
                        suggestions.append(
                            f"Create a personal reference guide for {topic} - you've asked about this multiple times"
                        )
                    else:
                        suggestions.append(
                            "Consider creating a FAQ or documentation for commonly asked questions"
                        )
                elif insight["type"] == "focus_area":
                    area = insight["description"].split("on ")[1].split(" (")[0]
                    suggestions.append(
                        f"Deep dive into {area} with more structured learning resources"
                    )
                elif insight["type"] == "problem_solving_pattern":
                    suggestions.append(
                        "Try breaking down the problem into smaller, testable components"
                    )

            # Add suggestions based on semantic searches
            if issue_memories:
                recurring_issues = self._identify_recurring_issues(issue_memories)
                for issue in recurring_issues:
                    suggestions.append(f"Document solution for recurring {issue} - appears multiple times")

            if project_memories:
                incomplete_projects = self._identify_incomplete_projects(project_memories)
                for project in incomplete_projects:
                    suggestions.append(f"Consider resuming work on {project} - seems unfinished")

            return suggestions[:10]  # Limit to top 10 suggestions

        except Exception as e:
            self._logger.error("Failed to suggest next steps", error=str(e))
            return []

    async def reflect_on_messages(
        self, 
        messages: list[dict[str, Any]], 
        context_memories: list[dict[str, Any]], 
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Reflect on a batch of messages using Claude Code SDK for enhanced reasoning.

        Args:
            messages: Recent messages to analyze
            context_memories: Relevant memories for context
            user_id: User ID for memory operations

        Returns:
            Reflection analysis results
        """
        user_id = user_id or settings.default_user_id

        try:
            self._logger.info(
                "Starting enhanced reflection analysis", 
                message_count=len(messages), 
                context_count=len(context_memories)
            )

            # Prepare the reflection prompt
            reflection_prompt = self._build_reflection_prompt(messages, context_memories)

            # Use claude-code-sdk for enhanced reasoning
            options = ClaudeCodeOptions(
                system_prompt="You are a reflection agent analyzing conversation patterns and decision-making quality.",
                max_turns=1
            )

            insights = []
            async for message in query(prompt=reflection_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Parse the response to extract structured insights
                            insights.append(block.text)

            # Process and store the reflection insights
            if insights:
                reflection_result = await self._store_enhanced_reflection(
                    insights=insights, 
                    messages=messages, 
                    user_id=user_id
                )
                
                self._logger.info(
                    "Enhanced reflection analysis completed",
                    user_id=user_id,
                    memory_id=reflection_result.get("id"),
                    insight_length=len(insights[0]) if insights else 0
                )
                
                return {
                    "status": "completed",
                    "memory_id": reflection_result.get("id"),
                    "insight_count": len(insights)
                }
            else:
                self._logger.warning("No insights generated from reflection")
                return {"status": "no_insights"}

        except Exception as e:
            self._logger.error("Failed to complete enhanced reflection", error=str(e))
            # Fallback to basic reflection if claude-code-sdk fails
            try:
                return await self.analyze_recent_conversations(user_id=user_id, limit=len(messages))
            except Exception as fallback_error:
                self._logger.error("Fallback reflection also failed", error=str(fallback_error))
                raise

    def _build_reflection_prompt(
        self, 
        messages: list[dict[str, Any]], 
        context_memories: list[dict[str, Any]]
    ) -> str:
        """Build a comprehensive reflection prompt for claude-code-sdk analysis."""
        
        prompt = """You are analyzing a conversation between a user and Claude to identify patterns, decision-making quality, and opportunities for knowledge consolidation.

## Recent Messages to Analyze:
"""
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt += f"\n{i+1}. **{role.title()}**: {content[:500]}{'...' if len(content) > 500 else ''}\n"

        if context_memories:
            prompt += "\n## Relevant Context from Memory:\n"
            for memory in context_memories[:5]:  # Limit to top 5 for brevity
                memory_content = memory.get("memory", memory.get("content", ""))
                prompt += f"\n- {memory_content[:200]}{'...' if len(memory_content) > 200 else ''}\n"

        prompt += """

## Analysis Tasks:
Please analyze the above conversation and provide insights in the following areas:

1. **Decision-Making Patterns**: How is Claude approaching problems? Is the reasoning sound?
2. **Knowledge Gaps**: What information seems to be missing or could be better consolidated?
3. **Communication Effectiveness**: How well is Claude explaining concepts and solutions?
4. **Learning Opportunities**: What patterns suggest opportunities for better memory consolidation?
5. **Behavioral Insights**: What does this conversation reveal about the user's needs and preferences?

## Output Format:
Provide a structured analysis with actionable insights that can help improve future conversations. Focus on meta-level observations about reasoning quality and knowledge consolidation opportunities.
"""
        
        return prompt

    async def _store_enhanced_reflection(
        self, 
        insights: list[str], 
        messages: list[dict[str, Any]], 
        user_id: str
    ) -> dict[str, Any]:
        """Store enhanced reflection insights as a special memory with reflection metadata."""
        
        # Combine all insights into a comprehensive reflection
        combined_insights = "\n\n".join(insights)
        
        reflection_content = f"""## Enhanced Conversation Reflection

{combined_insights}

---
*This reflection was generated by analyzing {len(messages)} recent messages using enhanced LLM reasoning to identify patterns, decision-making quality, and knowledge consolidation opportunities.*
"""

        # Create messages for memory storage
        reflection_messages = [
            {"role": "system", "content": "Enhanced Reflection Agent Analysis"},
            {"role": "assistant", "content": reflection_content},
        ]

        # Special metadata to distinguish reflection memories
        metadata = {
            "type": "enhanced_reflection",
            "source": "reflection_agent_claude_sdk",
            "analyzed_message_count": len(messages),
            "reflection_agent": True,
            "timestamp": str(int(__import__("time").time()))
        }

        # Store with special agent_id
        result = await memory_service.add_memory(
            messages=reflection_messages,
            user_id=user_id,
            agent_id="reflect-agent",  # Special agent ID as requested
            metadata=metadata,
            categories=[
                {"name": "reflection", "description": "Meta-analysis of conversation patterns"},
                {"name": "reasoning_quality", "description": "Assessment of decision-making patterns"},
                {"name": "knowledge_consolidation", "description": "Opportunities for better memory organization"}
            ]
        )

        return result

    async def _get_relevant_memories_for_analysis(
        self, 
        user_id: str, 
        recent_memories: list[dict[str, Any]], 
        remaining_limit: int
    ) -> list[dict[str, Any]]:
        """Get semantically relevant memories for pattern analysis."""
        
        if remaining_limit <= 0:
            return []
        
        # Extract key topics from recent memories for semantic search
        search_queries = self._extract_search_queries_from_memories(recent_memories)
        
        relevant_memories = []
        memories_per_query = max(1, remaining_limit // len(search_queries)) if search_queries else remaining_limit
        
        for query in search_queries:
            try:
                memories = await memory_service.search_memories(
                    query=query, user_id=user_id, limit=memories_per_query
                )
                relevant_memories.extend(memories)
            except Exception as e:
                self._logger.warning(f"Search failed for query '{query}'", error=str(e))
                continue
        
        return relevant_memories[:remaining_limit]
    
    def _extract_search_queries_from_memories(self, memories: list[dict[str, Any]]) -> list[str]:
        """Extract search queries from recent memories to find related patterns."""
        
        queries = []
        topics = set()
        
        for memory in memories:
            content = memory.get("memory", memory.get("content", ""))
            if not isinstance(content, str):
                continue
                
            content_lower = content.lower()
            
            # Look for technical terms, errors, and project-related keywords
            technical_terms = []
            
            # Extract technical keywords
            tech_keywords = ["react", "typescript", "javascript", "python", "node", "docker", 
                           "api", "database", "authentication", "auth", "jwt", "cors", "error",
                           "component", "function", "class", "module", "package", "framework"]
            
            for keyword in tech_keywords:
                if keyword in content_lower:
                    technical_terms.append(keyword)
            
            # Look for error patterns
            if "error" in content_lower or "problem" in content_lower or "issue" in content_lower:
                topics.add("errors debugging troubleshooting")
            
            # Look for implementation patterns
            if any(word in content_lower for word in ["implement", "build", "create", "develop"]):
                topics.add("implementation development coding")
            
            # Look for learning patterns
            if any(word in content_lower for word in ["how", "what", "why", "explain", "understand"]):
                topics.add("learning questions understanding")
            
            # Add technical terms as topics
            if technical_terms:
                topics.add(" ".join(technical_terms[:3]))  # Limit to 3 terms per query
        
        # Convert topics to search queries
        queries = list(topics)[:5]  # Limit to 5 queries to avoid too many API calls
        
        # Add default queries if we don't have enough
        default_queries = ["programming coding development", "error problem solution"]
        for default_query in default_queries:
            if default_query not in queries and len(queries) < 3:
                queries.append(default_query)
        
        return queries
    
    def _deduplicate_memories(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate memories based on ID."""
        seen_ids = set()
        deduplicated = []
        
        for memory in memories:
            memory_id = memory.get("id")
            if memory_id and memory_id not in seen_ids:
                seen_ids.add(memory_id)
                deduplicated.append(memory)
            elif not memory_id:  # Keep memories without IDs for safety
                deduplicated.append(memory)
        
        return deduplicated
    
    def _extract_topic_from_questions(self, questions: list[str]) -> str:
        """Extract the main topic from a list of questions."""
        
        # Common technical topics
        topics = {
            "react": ["react", "jsx", "component", "hook", "usestate", "useeffect"],
            "typescript": ["typescript", "type", "interface", "generic"],
            "authentication": ["auth", "login", "jwt", "token", "session"],
            "database": ["database", "sql", "query", "table", "schema"],
            "api": ["api", "endpoint", "request", "response", "http"],
            "css": ["css", "style", "layout", "flexbox", "grid"],
            "testing": ["test", "spec", "mock", "assertion"],
        }
        
        question_text = " ".join(questions).lower()
        
        for topic, keywords in topics.items():
            if any(keyword in question_text for keyword in keywords):
                return topic
        
        return "general programming topics"
    
    def _identify_recurring_issues(self, issue_memories: list[dict[str, Any]]) -> list[str]:
        """Identify recurring issues from error/problem memories."""
        
        issue_counts = {}
        
        for memory in issue_memories:
            content = memory.get("memory", memory.get("content", ""))
            if not isinstance(content, str):
                continue
                
            content_lower = content.lower()
            
            # Look for common issue patterns
            issue_patterns = {
                "CORS issues": ["cors", "cross-origin", "access-control"],
                "type errors": ["type error", "typescript error", "cannot read property"],
                "import/export issues": ["import", "export", "module", "cannot resolve"],
                "build errors": ["build failed", "compilation error", "webpack"],
                "API errors": ["api error", "fetch failed", "network error", "status 500"],
                "dependency issues": ["npm install", "package", "dependency", "version conflict"]
            }
            
            for issue_type, keywords in issue_patterns.items():
                if any(keyword in content_lower for keyword in keywords):
                    issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        # Return issues that appear more than once
        return [issue for issue, count in issue_counts.items() if count > 1]
    
    def _identify_incomplete_projects(self, project_memories: list[dict[str, Any]]) -> list[str]:
        """Identify potentially incomplete projects from memory content."""
        
        project_keywords = {}
        completion_keywords = ["finished", "completed", "done", "deployed", "released"]
        
        for memory in project_memories:
            content = memory.get("memory", memory.get("content", ""))
            if not isinstance(content, str):
                continue
                
            content_lower = content.lower()
            
            # Look for project names/types
            project_patterns = {
                "authentication system": ["auth system", "authentication", "login system"],
                "API development": ["api", "backend", "server", "endpoint"],
                "frontend application": ["frontend", "ui", "interface", "component"],
                "database integration": ["database", "db", "schema", "migration"],
                "testing framework": ["test", "testing", "spec", "automation"]
            }
            
            for project_type, keywords in project_patterns.items():
                if any(keyword in content_lower for keyword in keywords):
                    if project_type not in project_keywords:
                        project_keywords[project_type] = {"mentions": 0, "completed": False}
                    
                    project_keywords[project_type]["mentions"] += 1
                    
                    # Check if this memory suggests completion
                    if any(completion in content_lower for completion in completion_keywords):
                        project_keywords[project_type]["completed"] = True
        
        # Return projects with multiple mentions but no completion indicators
        incomplete = []
        for project, data in project_keywords.items():
            if data["mentions"] > 1 and not data["completed"]:
                incomplete.append(project)
        
        return incomplete


# Global instance
reflection_agent = ReflectionAgent()
