"""
Weather Persona Tool - Integrates weather API with character switching
Automatically switches to weatherman persona when weather requests are detected
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
from .weather_api_tool import weather_tool

logger = logging.getLogger(__name__)

class WeatherPersonaTool:
    """Tool that combines weather API calls with automatic persona switching"""
    
    def __init__(self):
        self.tool_name = "weather_persona_tool"
        self.description = "Handles weather requests with automatic weatherman persona switching"
        self.score = 0.0
        self.s1_endpoint = "http://neurosync:5001"
        self.weatherman_character_id = "weatherman_template"
        
    async def create_weatherman_character(self) -> Dict[str, Any]:
        """Create weatherman character if it doesn't exist"""
        try:
            weatherman_data = {
                "id": "weatherman_template",
                "name": "Weather Forecaster",
                "role": "Professional Meteorologist",
                "personality_traits": [
                    "enthusiastic",
                    "informative", 
                    "accurate",
                    "friendly",
                    "energetic"
                ],
                "communication_style": "broadcast professional with warm personality",
                "emotional_range": "upbeat and reassuring",
                "domain_expertise": [
                    "weather patterns",
                    "climate analysis",
                    "meteorology",
                    "seasonal forecasting",
                    "weather safety",
                    "atmospheric science"
                ],
                "behavioral_rules": [
                    "Always provide accurate weather information",
                    "Include safety recommendations for severe weather",
                    "Use engaging, broadcast-style delivery",
                    "Explain weather phenomena in accessible terms",
                    "Maintain professional authority while being personable"
                ],
                "formality_level": "professional but approachable",
                "autonomous_enabled": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.s1_endpoint}/character/create",
                    json=weatherman_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        logger.info("✅ [WEATHER_PERSONA] Weatherman character created successfully")
                        return {"success": True, "character": result}
                    else:
                        logger.warning(f"⚠️ [WEATHER_PERSONA] Character creation failed: {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            logger.error(f"❌ [WEATHER_PERSONA] Error creating weatherman character: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_to_weatherman(self) -> Dict[str, Any]:
        """Switch S1 Avatar to weatherman persona"""
        try:
            # First, try to create the character in case it doesn't exist
            await self.create_weatherman_character()
            
            # Then switch to the weatherman character
            switch_payload = {
                "character_id": self.weatherman_character_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.s1_endpoint}/character/switch",
                    json=switch_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("✅ [WEATHER_PERSONA] Switched to weatherman persona")
                        return {"success": True, "character": result}
                    else:
                        logger.warning(f"⚠️ [WEATHER_PERSONA] Character switch failed: {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            logger.error(f"❌ [WEATHER_PERSONA] Error switching to weatherman: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_weather_with_persona(self, request_type: str = "current", location: str = "San Francisco, CA") -> Dict[str, Any]:
        """Get weather information with automatic persona switching"""
        try:
            # Step 1: Switch to weatherman persona
            persona_result = await self.switch_to_weatherman()
            if not persona_result["success"]:
                logger.warning("⚠️ [WEATHER_PERSONA] Continuing without persona switch")
            
            # Step 2: Get weather data
            if request_type == "current":
                weather_data = await weather_tool.get_current_weather(location)
                formatted_response = await weather_tool.format_weather_response(weather_data, "current")
            elif request_type == "forecast":
                weather_data = await weather_tool.get_forecast(location)
                formatted_response = await weather_tool.format_weather_response(weather_data, "forecast")
            elif request_type == "alerts":
                weather_data = await weather_tool.get_weather_alerts(location)
                formatted_response = await weather_tool.format_weather_response(weather_data, "alerts")
            else:
                formatted_response = f"I'm not sure what type of weather information you're looking for. I can provide current conditions, forecasts, or alerts for {location}."
            
            # Step 3: Add weatherman personality to the response
            weatherman_intro = "Good day! I'm your weather forecaster, and I'm excited to share the latest weather information with you. "
            
            if "error" not in str(weather_data):
                # Add weather safety tips based on conditions
                if request_type == "current" and "rain" in formatted_response.lower():
                    weatherman_intro += "⛈️ Before we dive into the details, remember to keep an umbrella handy! "
                elif request_type == "current" and "sunny" in formatted_response.lower():
                    weatherman_intro += "☀️ It's looking like a beautiful day ahead! "
                elif request_type == "alerts" and weather_data.get("alerts"):
                    weatherman_intro += "🚨 I have some important weather alerts to share with you for your safety. "
            
            final_response = weatherman_intro + formatted_response
            
            return {
                "success": True,
                "response": final_response,
                "weather_data": weather_data,
                "persona_switched": persona_result["success"],
                "request_type": request_type,
                "location": location
            }
            
        except Exception as e:
            logger.error(f"❌ [WEATHER_PERSONA] Error getting weather with persona: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble accessing weather information right now. Please try again later."
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for the tool registry"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "score": self.score,
            "capabilities": [
                "weather_with_persona_switching",
                "automatic_weatherman_character_creation",
                "weather_current_conditions",
                "weather_forecasts",
                "weather_alerts",
                "persona_management"
            ],
            "supported_locations": ["any city, state or country"],
            "character_integration": True,
            "auto_persona_switch": True
        }

# Global weather persona tool instance
weather_persona_tool = WeatherPersonaTool()

async def execute_weather_persona_tool(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute weather persona tool based on context"""
    try:
        request_type = context.get("request_type", "current")
        location = context.get("location", "San Francisco, CA")
        
        # Detect weather intent from stimuli content
        content = context.get("content", "").lower()
        
        # Determine request type from content
        if "forecast" in content or "tomorrow" in content or "this week" in content:
            request_type = "forecast"
        elif "alert" in content or "warning" in content or "severe" in content:
            request_type = "alerts"
        else:
            request_type = "current"
        
        # Extract location from content if mentioned
        # This is a simple implementation - could be enhanced with NLP
        if "in " in content:
            location_part = content.split("in ")[-1].split()[0:3]  # Take next few words
            potential_location = " ".join(location_part).strip(".,!?")
            if len(potential_location) > 2:
                location = potential_location
        
        # Get weather with persona switching
        result = await weather_persona_tool.get_weather_with_persona(request_type, location)
        
        return {
            "success": result["success"],
            "response": result["response"],
            "tool_used": "weather_persona_tool",
            "request_type": request_type,
            "location": location,
            "persona_switched": result.get("persona_switched", False),
            "weather_data": result.get("weather_data", {}),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"❌ [WEATHER_PERSONA] Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "weather_persona_tool",
            "response": "I'm having trouble processing your weather request right now."
        }

# Tool registry integration
async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for the weather persona tool"""
    return await execute_weather_persona_tool(context)