"""
Recipe Generation Tool - Available only to chef persona
Generates recipes and cooking instructions for chef characters
"""

import logging
import asyncio
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute recipe generation tool
    
    This tool is restricted to chef personas and generates recipes,
    cooking instructions, and culinary guidance based on the context.
    """
    
    try:
        # Log persona-specific tool usage
        logger.info("👨‍🍳 [RECIPE_TOOL] Recipe generation tool executed by chef persona")
        
        # Extract cooking query from context
        content = context.get("content", context.get("message", ""))
        character_name = context.get("character_name", "Chef")
        
        # Simulate recipe generation
        await asyncio.sleep(0.7)  # Simulate processing time
        
        # Sample recipe components
        dishes = ["Pasta Carbonara", "Grilled Salmon", "Vegetable Stir-Fry", "Chocolate Soufflé", "Beef Stroganoff"]
        cooking_methods = ["sauté", "grill", "roast", "braise", "steam"]
        flavor_profiles = ["savory", "sweet", "spicy", "tangy", "rich"]
        
        selected_dish = random.choice(dishes)
        cooking_method = random.choice(cooking_methods)
        flavor_profile = random.choice(flavor_profiles)
        
        # Generate recipe response
        recipe_response = f"""
👨‍🍳 **Recipe from {character_name}**

**Inspired by your request:** {content}

**🍽️ Featured Recipe: {selected_dish}**

**Cooking Method:** {cooking_method.title()}
**Flavor Profile:** {flavor_profile.title()}

**Ingredients:**
- Fresh, high-quality ingredients (chef's choice)
- Seasonal vegetables and herbs
- Premium proteins or plant-based alternatives
- Aromatic spices and seasonings

**Cooking Instructions:**
1. **Preparation:** Mise en place - organize all ingredients
2. **Technique:** Apply {cooking_method} method with precision
3. **Timing:** Cook with attention to texture and doneness
4. **Seasoning:** Taste and adjust flavors throughout process
5. **Plating:** Present with artistic flair and garnish

**Chef's Tips:**
- Quality ingredients make the difference
- Proper technique ensures consistent results
- Taste at every stage of cooking
- Presentation enhances the dining experience

**Culinary Wisdom:** "Cooking is an art, but great cooking is a science combined with passion!"
        """.strip()
        
        return {
            "success": True,
            "response": recipe_response,
            "tool_used": "recipe_generation_tool",
            "persona_required": "chef",
            "recipe_generated": True,
            "featured_dish": selected_dish,
            "cooking_method": cooking_method,
            "execution_time": 0.7
        }
        
    except Exception as e:
        logger.error(f"❌ [RECIPE_TOOL] Error in recipe generation tool: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "recipe_generation_tool",
            "persona_required": "chef"
        }