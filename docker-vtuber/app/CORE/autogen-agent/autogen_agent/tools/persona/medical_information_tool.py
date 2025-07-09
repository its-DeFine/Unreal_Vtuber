"""
Medical Information Tool - Available only to doctor persona
Provides medical information and health guidance for doctor characters
"""

import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute medical information tool
    
    This tool is restricted to doctor personas and provides medical information,
    health guidance, and wellness recommendations based on the context.
    """
    
    try:
        # Log persona-specific tool usage
        logger.info("🏥 [MEDICAL_TOOL] Medical information tool executed by doctor persona")
        
        # Extract medical query from context
        content = context.get("content", context.get("message", ""))
        character_name = context.get("character_name", "Doctor")
        
        # Simulate medical information lookup
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Generate medical guidance response
        medical_response = f"""
🏥 **Medical Information from {character_name}**

Based on your query about: {content}

**Professional Medical Guidance:**
- This is a medical information tool response
- Always consult with qualified healthcare professionals
- Medical information should be verified with current medical literature
- Patient safety and wellbeing are the top priorities

**Next Steps:**
1. Recommend consultation with appropriate medical specialist
2. Suggest evidence-based treatment options
3. Provide educational resources for patient understanding
4. Emphasize importance of professional medical care

**Important Disclaimer:** This information is for educational purposes only and should not replace professional medical advice.
        """.strip()
        
        return {
            "success": True,
            "response": medical_response,
            "tool_used": "medical_information_tool",
            "persona_required": "doctor",
            "medical_guidance_provided": True,
            "execution_time": 0.5
        }
        
    except Exception as e:
        logger.error(f"❌ [MEDICAL_TOOL] Error in medical information tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "medical_information_tool",
            "persona_required": "doctor"
        }