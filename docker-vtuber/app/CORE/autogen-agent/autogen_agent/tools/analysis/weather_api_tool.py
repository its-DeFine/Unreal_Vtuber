"""
Weather API Tool for AutoGen Agent
Provides weather information integration for the stimuli system
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import random

logger = logging.getLogger(__name__)

class WeatherAPITool:
    """Mock Weather API tool for demonstration purposes"""
    
    def __init__(self):
        self.tool_name = "weather_api_tool"
        self.description = "Provides current weather information and forecasts"
        self.score = 0.0
        
        # Mock weather conditions for demonstration
        self.weather_conditions = [
            "sunny", "partly cloudy", "cloudy", "overcast", 
            "light rain", "heavy rain", "drizzle", "thunderstorms",
            "snow", "clear", "foggy", "windy"
        ]
        
        self.temperature_ranges = {
            "sunny": (70, 85),
            "partly cloudy": (65, 80),
            "cloudy": (60, 75),
            "overcast": (55, 70),
            "light rain": (50, 65),
            "heavy rain": (45, 60),
            "drizzle": (50, 65),
            "thunderstorms": (55, 75),
            "snow": (25, 40),
            "clear": (65, 80),
            "foggy": (55, 70),
            "windy": (60, 75)
        }
        
    async def get_current_weather(self, location: str = "San Francisco, CA") -> Dict[str, Any]:
        """Get current weather for a location"""
        try:
            # Simulate API delay
            await asyncio.sleep(0.1)
            
            # Generate mock weather data
            condition = random.choice(self.weather_conditions)
            temp_range = self.temperature_ranges.get(condition, (60, 75))
            temperature = random.randint(temp_range[0], temp_range[1])
            humidity = random.randint(30, 90)
            wind_speed = random.randint(0, 25)
            
            weather_data = {
                "location": location,
                "temperature": temperature,
                "condition": condition,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "pressure": random.randint(2980, 3050) / 100,  # Convert to inHg
                "visibility": random.randint(5, 15),
                "uv_index": random.randint(1, 10),
                "timestamp": datetime.now().isoformat(),
                "feels_like": temperature + random.randint(-5, 5)
            }
            
            logger.info(f"🌤️ [WEATHER_API] Retrieved weather for {location}: {condition}, {temperature}°F")
            return weather_data
            
        except Exception as e:
            logger.error(f"❌ [WEATHER_API] Error getting weather: {e}")
            return {"error": str(e), "location": location}
    
    async def get_forecast(self, location: str = "San Francisco, CA", days: int = 7) -> Dict[str, Any]:
        """Get weather forecast for a location"""
        try:
            await asyncio.sleep(0.1)
            
            forecast_data = {
                "location": location,
                "forecast_days": days,
                "forecast": [],
                "timestamp": datetime.now().isoformat()
            }
            
            for day in range(days):
                date = datetime.now() + timedelta(days=day)
                condition = random.choice(self.weather_conditions)
                temp_range = self.temperature_ranges.get(condition, (60, 75))
                high_temp = random.randint(temp_range[0], temp_range[1])
                low_temp = high_temp - random.randint(10, 20)
                
                day_forecast = {
                    "date": date.strftime("%Y-%m-%d"),
                    "day_of_week": date.strftime("%A"),
                    "condition": condition,
                    "high_temp": high_temp,
                    "low_temp": max(low_temp, 32),  # Don't go below freezing unrealistically
                    "precipitation_chance": random.randint(0, 100),
                    "wind_speed": random.randint(0, 20)
                }
                
                forecast_data["forecast"].append(day_forecast)
            
            logger.info(f"📅 [WEATHER_API] Retrieved {days}-day forecast for {location}")
            return forecast_data
            
        except Exception as e:
            logger.error(f"❌ [WEATHER_API] Error getting forecast: {e}")
            return {"error": str(e), "location": location}
    
    async def get_weather_alerts(self, location: str = "San Francisco, CA") -> Dict[str, Any]:
        """Get weather alerts for a location"""
        try:
            await asyncio.sleep(0.1)
            
            # Randomly generate weather alerts (or none)
            alerts = []
            
            if random.random() < 0.3:  # 30% chance of an alert
                alert_types = [
                    "High Wind Warning",
                    "Flood Watch",
                    "Heat Advisory",
                    "Winter Storm Watch",
                    "Severe Thunderstorm Warning"
                ]
                
                alert_type = random.choice(alert_types)
                alerts.append({
                    "type": alert_type,
                    "severity": random.choice(["Minor", "Moderate", "Severe"]),
                    "description": f"{alert_type} in effect for {location}",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(hours=random.randint(2, 24))).isoformat()
                })
            
            alert_data = {
                "location": location,
                "alerts": alerts,
                "alert_count": len(alerts),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🚨 [WEATHER_API] Retrieved {len(alerts)} alerts for {location}")
            return alert_data
            
        except Exception as e:
            logger.error(f"❌ [WEATHER_API] Error getting alerts: {e}")
            return {"error": str(e), "location": location}
    
    async def format_weather_response(self, weather_data: Dict[str, Any], request_type: str = "current") -> str:
        """Format weather data into a natural language response"""
        try:
            if "error" in weather_data:
                return f"I'm having trouble getting weather information right now. {weather_data['error']}"
            
            if request_type == "current":
                condition = weather_data.get("condition", "unknown")
                temp = weather_data.get("temperature", "unknown")
                location = weather_data.get("location", "your area")
                humidity = weather_data.get("humidity", "unknown")
                wind = weather_data.get("wind_speed", "unknown")
                
                response = f"Right now in {location}, it's {temp}°F with {condition} skies. "
                response += f"Humidity is at {humidity}% with winds at {wind} mph. "
                
                # Add weather-specific advice
                if "rain" in condition:
                    response += "Don't forget an umbrella if you're heading out!"
                elif condition == "sunny":
                    response += "Perfect weather for outdoor activities!"
                elif "snow" in condition:
                    response += "Drive carefully and bundle up!"
                
                return response
                
            elif request_type == "forecast":
                location = weather_data.get("location", "your area")
                forecast_days = weather_data.get("forecast_days", 0)
                forecast = weather_data.get("forecast", [])
                
                if not forecast:
                    return f"I don't have forecast information for {location} right now."
                
                response = f"Here's the {forecast_days}-day forecast for {location}:\n\n"
                
                for day in forecast[:3]:  # Show first 3 days
                    day_name = day.get("day_of_week", "Unknown")
                    condition = day.get("condition", "unknown")
                    high = day.get("high_temp", "unknown")
                    low = day.get("low_temp", "unknown")
                    precip = day.get("precipitation_chance", 0)
                    
                    response += f"{day_name}: {condition}, High {high}°F, Low {low}°F"
                    if precip > 30:
                        response += f", {precip}% chance of precipitation"
                    response += "\n"
                
                return response.strip()
                
            elif request_type == "alerts":
                location = weather_data.get("location", "your area")
                alerts = weather_data.get("alerts", [])
                
                if not alerts:
                    return f"No weather alerts currently in effect for {location}."
                
                response = f"⚠️ Weather alerts for {location}:\n\n"
                for alert in alerts:
                    alert_type = alert.get("type", "Weather Alert")
                    severity = alert.get("severity", "Unknown")
                    description = alert.get("description", "")
                    response += f"{alert_type} ({severity}): {description}\n"
                
                return response.strip()
                
        except Exception as e:
            logger.error(f"❌ [WEATHER_API] Error formatting response: {e}")
            return "I'm having trouble processing the weather information right now."
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for the tool registry"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "score": self.score,
            "capabilities": [
                "current_weather",
                "weather_forecast", 
                "weather_alerts",
                "weather_formatting"
            ],
            "supported_locations": ["any city, state or country"],
            "response_format": "natural language weather information"
        }

# Global weather tool instance
weather_tool = WeatherAPITool()

async def execute_weather_tool(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute weather tool based on context"""
    try:
        request_type = context.get("request_type", "current")
        location = context.get("location", "San Francisco, CA")
        
        if request_type == "current":
            weather_data = await weather_tool.get_current_weather(location)
            response = await weather_tool.format_weather_response(weather_data, "current")
            
        elif request_type == "forecast":
            days = context.get("days", 7)
            weather_data = await weather_tool.get_forecast(location, days)
            response = await weather_tool.format_weather_response(weather_data, "forecast")
            
        elif request_type == "alerts":
            weather_data = await weather_tool.get_weather_alerts(location)
            response = await weather_tool.format_weather_response(weather_data, "alerts")
            
        else:
            response = "I'm not sure what type of weather information you're looking for."
        
        return {
            "success": True,
            "response": response,
            "tool_used": "weather_api_tool",
            "request_type": request_type,
            "location": location
        }
        
    except Exception as e:
        logger.error(f"❌ [WEATHER_API] Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "weather_api_tool"
        }