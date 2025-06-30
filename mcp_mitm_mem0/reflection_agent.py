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
        """Analyze recent conversations and generate insights.

        Args:
            user_id: User to analyze (defaults to settings)
            limit: Number of recent memories to analyze

        Returns:
            Analysis results with patterns and suggestions
        """
        user_id = user_id or settings.default_user_id

        try:
            memories = await memory_service.get_all_memories(user_id=user_id)

            if memories:
                recent_memories = sorted(
                    memories, key=lambda m: m.get("created_at", ""), reverse=True
                )[:limit]
            else:
                return {"status": "no_memories", "insights": []}

            insights = await self._analyze_patterns(recent_memories)

            if insights:
                await self._store_reflection(insights, user_id)

            return {
                "status": "analyzed",
                "memory_count": len(recent_memories),
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
        """Suggest next steps based on conversation history.

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

            suggestions = []

            for insight in insights:
                if insight["type"] == "frequent_questions":
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

            return suggestions

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


# Global instance
reflection_agent = ReflectionAgent()
