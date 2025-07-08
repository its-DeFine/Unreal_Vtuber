"""
Educational Content Tool - Available only to teacher persona
Provides educational content and learning guidance for teacher characters
"""

import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute educational content tool
    
    This tool is restricted to teacher personas and provides educational content,
    learning guidance, and instructional support based on the context.
    """
    
    try:
        # Log persona-specific tool usage
        logger.info("📚 [EDUCATION_TOOL] Educational content tool executed by teacher persona")
        
        # Extract educational query from context
        content = context.get("content", context.get("message", ""))
        character_name = context.get("character_name", "Teacher")
        
        # Simulate educational content generation
        await asyncio.sleep(0.6)  # Simulate processing time
        
        # Generate educational response
        educational_response = f"""
📚 **Educational Content from {character_name}**

**Learning Topic:** {content}

**📖 Learning Objectives:**
- Understand core concepts and principles
- Apply knowledge in practical scenarios
- Develop critical thinking skills
- Build foundation for advanced learning

**🎯 Teaching Approach:**
1. **Introduction:** Context and relevance
2. **Explanation:** Clear, step-by-step breakdown
3. **Examples:** Real-world applications
4. **Practice:** Hands-on exercises
5. **Assessment:** Knowledge check and feedback

**💡 Key Learning Points:**
- Break down complex topics into manageable parts
- Use analogies and examples to clarify concepts
- Encourage questions and active participation
- Provide multiple perspectives on the subject
- Connect new learning to existing knowledge

**📝 Study Tips:**
- Take notes and summarize key points
- Practice regularly with exercises
- Discuss concepts with peers
- Apply learning to real situations
- Review and reflect on progress

**🌟 Encouraging Words:**
"Every expert was once a beginner. Learning is a journey, not a destination. Keep asking questions and stay curious!"

**Next Steps:**
- Review the material provided
- Practice with examples
- Ask questions for clarification
- Apply concepts in your own context
        """.strip()
        
        return {
            "success": True,
            "response": educational_response,
            "tool_used": "educational_content_tool",
            "persona_required": "teacher",
            "educational_content_provided": True,
            "learning_objectives_included": True,
            "execution_time": 0.6
        }
        
    except Exception as e:
        logger.error(f"❌ [EDUCATION_TOOL] Error in educational content tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "educational_content_tool",
            "persona_required": "teacher"
        }