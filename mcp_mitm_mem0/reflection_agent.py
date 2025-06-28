"""
Reflection agent for analyzing conversations and curating memories.

This agent reviews conversations between the user and Claude, identifies patterns,
and can add enriched memories or hints back to the memory store.
"""

import asyncio
from typing import Any

import structlog

from .memory_service import memory_service
from .config import settings

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
        self, 
        user_id: str | None = None,
        limit: int = 20
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
            # Get recent memories
            memories = await memory_service.get_all_memories(user_id=user_id)
            
            # Sort by creation date and get most recent
            if memories:
                recent_memories = sorted(
                    memories,
                    key=lambda m: m.get('created_at', ''),
                    reverse=True
                )[:limit]
            else:
                return {"status": "no_memories", "insights": []}
            
            # Analyze patterns
            insights = await self._analyze_patterns(recent_memories)
            
            # Generate reflection memory if insights found
            if insights:
                await self._store_reflection(insights, user_id)
            
            return {
                "status": "analyzed",
                "memory_count": len(recent_memories),
                "insights": insights
            }
            
        except Exception as e:
            self._logger.error("Failed to analyze conversations", error=str(e))
            raise
    
    async def _analyze_patterns(self, memories: list[dict[str, Any]]) -> list[dict[str, str]]:
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
            content = memory.get('memory', memory.get('content', ''))
            
            # Simple pattern matching (could be enhanced with LLM analysis)
            if isinstance(content, str):
                # Track questions
                if '?' in content:
                    questions_asked.append(content)
                
                # Track code-related discussions
                if any(keyword in content.lower() for keyword in ['function', 'class', 'implement', 'code', 'debug']):
                    if 'coding' not in topics:
                        topics['coding'] = 0
                    topics['coding'] += 1
                
                # Track problem-solving approaches
                if any(keyword in content.lower() for keyword in ['try', 'attempt', 'approach', 'solution']):
                    approaches_tried.append(content)
        
        # Generate insights based on patterns
        if len(questions_asked) > 3:
            insights.append({
                "type": "frequent_questions",
                "description": f"User has asked {len(questions_asked)} questions recently. Consider providing more proactive information.",
                "examples": questions_asked[-3:]
            })
        
        if topics:
            most_discussed = max(topics.items(), key=lambda x: x[1])
            insights.append({
                "type": "focus_area",
                "description": f"Primary focus appears to be on {most_discussed[0]} (mentioned {most_discussed[1]} times)",
                "recommendation": f"Consider preparing more detailed resources on {most_discussed[0]}"
            })
        
        if len(approaches_tried) > 2:
            insights.append({
                "type": "problem_solving_pattern",
                "description": "Multiple approaches being tried, suggesting iterative problem solving",
                "recommendation": "Consider suggesting a structured approach or framework"
            })
        
        return insights
    
    async def _store_reflection(
        self, 
        insights: list[dict[str, Any]], 
        user_id: str
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
            
            if 'recommendation' in insight:
                reflection_content += f"**Recommendation:** {insight['recommendation']}\n"
            
            if 'examples' in insight:
                reflection_content += "\n**Examples:**\n"
                for example in insight['examples'][:3]:
                    reflection_content += f"- {example[:100]}...\n"
            
            reflection_content += "\n"
        
        # Store as a reflection memory
        messages = [
            {
                "role": "system",
                "content": "Reflection Agent Analysis"
            },
            {
                "role": "assistant",
                "content": reflection_content
            }
        ]
        
        metadata = {
            "type": "reflection",
            "source": "reflection_agent",
            "insight_count": len(insights)
        }
        
        result = await memory_service.add_memory(
            messages=messages,
            user_id=user_id,
            metadata=metadata
        )
        
        self._logger.info(
            "Stored reflection insights",
            user_id=user_id,
            insight_count=len(insights),
            memory_id=result.get("id")
        )
        
        return result
    
    async def suggest_next_steps(
        self, 
        user_id: str | None = None
    ) -> list[str]:
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


# Global instance
reflection_agent = ReflectionAgent()