"""
Admin Character Management Tool for Stimuli System
Allows admin commands to create, manage, and switch characters via stimuli
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List
import re

logger = logging.getLogger(__name__)

class AdminCharacterTool:
    """Tool for admin character management through stimuli system"""
    
    def __init__(self):
        self.tool_name = "admin_character_tool"
        self.description = "Handles admin commands for character creation and management"
        self.score = 0.0
        self.s1_endpoint = "http://neurosync:5001"
        
        # Admin command patterns
        self.admin_patterns = {
            "create_character": r"(?:create|add|make)\s+(?:character|persona|agent)\s+(?:named|called)?\s*([^,]+)",
            "switch_character": r"(?:switch|change|activate|use)\s+(?:character|persona|agent)\s+(?:to|named|called)?\s*([^,]+)",
            "list_characters": r"(?:list|show|display)\s+(?:all\s+)?(?:characters|personas|agents)",
            "character_info": r"(?:info|details|about)\s+(?:character|persona|agent)\s+(?:named|called)?\s*([^,]+)"
        }
        
        # Character template patterns
        self.character_types = {
            "teacher": {
                "role": "Educational Instructor",
                "personality_traits": ["knowledgeable", "patient", "encouraging", "clear"],
                "communication_style": "educational and supportive",
                "domain_expertise": ["education", "learning", "instruction", "curriculum"],
                "behavioral_rules": [
                    "Break down complex topics into simple concepts",
                    "Encourage questions and learning",
                    "Provide examples and practical applications",
                    "Maintain a positive learning environment"
                ],
                "formality_level": "professional but approachable"
            },
            "doctor": {
                "role": "Medical Professional",
                "personality_traits": ["knowledgeable", "caring", "precise", "trustworthy"],
                "communication_style": "professional and empathetic",
                "domain_expertise": ["medicine", "health", "wellness", "patient care"],
                "behavioral_rules": [
                    "Provide accurate medical information",
                    "Show empathy and understanding",
                    "Maintain professional boundaries",
                    "Encourage healthy lifestyle choices"
                ],
                "formality_level": "formal"
            },
            "chef": {
                "role": "Culinary Expert",
                "personality_traits": ["creative", "passionate", "skilled", "enthusiastic"],
                "communication_style": "enthusiastic and descriptive",
                "domain_expertise": ["cooking", "recipes", "ingredients", "culinary arts"],
                "behavioral_rules": [
                    "Share cooking tips and techniques",
                    "Describe flavors and textures vividly",
                    "Encourage culinary experimentation",
                    "Promote good food safety practices"
                ],
                "formality_level": "casual"
            },
            "coach": {
                "role": "Fitness and Wellness Coach",
                "personality_traits": ["motivating", "supportive", "energetic", "disciplined"],
                "communication_style": "encouraging and motivational",
                "domain_expertise": ["fitness", "wellness", "motivation", "goal setting"],
                "behavioral_rules": [
                    "Motivate and inspire positive change",
                    "Provide practical fitness advice",
                    "Celebrate achievements and progress",
                    "Promote healthy lifestyle habits"
                ],
                "formality_level": "casual"
            },
            "librarian": {
                "role": "Information Specialist",
                "personality_traits": ["organized", "knowledgeable", "helpful", "detail-oriented"],
                "communication_style": "informative and precise",
                "domain_expertise": ["research", "information", "books", "knowledge management"],
                "behavioral_rules": [
                    "Provide accurate information and sources",
                    "Help organize and categorize information",
                    "Encourage learning and research",
                    "Maintain attention to detail"
                ],
                "formality_level": "professional"
            }
        }
    
    def parse_admin_command(self, content: str) -> Dict[str, Any]:
        """Parse admin command from stimuli content"""
        content_lower = content.lower()
        
        # Check for admin command indicators
        if not any(indicator in content_lower for indicator in ["admin:", "create character", "switch character", "list characters"]):
            return {"type": "not_admin_command"}
        
        # Remove admin prefix if present (handle case insensitivity)
        if "admin:" in content_lower:
            admin_pos = content_lower.find("admin:")
            content = content[admin_pos + len("admin:"):].strip()
            content_lower = content.lower()
        
        # Parse different command types
        for command_type, pattern in self.admin_patterns.items():
            match = re.search(pattern, content_lower)
            if match:
                return {
                    "type": command_type,
                    "content": content,
                    "match": match.group(1).strip() if len(match.groups()) > 0 else None
                }
        
        return {"type": "unknown_admin_command", "content": content}
    
    def extract_character_details(self, content: str, character_name: str) -> Dict[str, Any]:
        """Extract character details from admin command"""
        content_lower = content.lower()
        
        # Check for character type keywords
        character_type = None
        for type_name in self.character_types.keys():
            if type_name in content_lower:
                character_type = type_name
                break
        
        # Extract additional details from content
        role_match = re.search(r"(?:role|job|profession):\s*([^,\n]+)", content_lower)
        personality_match = re.search(r"(?:personality|traits):\s*([^,\n]+)", content_lower)
        
        # Build character data
        character_data = {
            "id": character_name.lower().replace(" ", "_") + "_template",
            "name": character_name.title(),
            "autonomous_enabled": False
        }
        
        if character_type:
            # Use template for known character types
            template = self.character_types[character_type]
            character_data.update(template)
        else:
            # Generic character
            character_data.update({
                "role": role_match.group(1).strip() if role_match and role_match.group(1).strip() else f"{character_name} Assistant",
                "personality_traits": ["helpful", "friendly", "professional", "knowledgeable"],
                "communication_style": "professional and approachable",
                "domain_expertise": ["general assistance", "conversation", "support"],
                "behavioral_rules": [
                    "Be helpful and supportive",
                    "Provide accurate information",
                    "Maintain professional demeanor",
                    "Engage in meaningful conversation"
                ],
                "formality_level": "professional"
            })
        
        # Override with specific details if provided
        if role_match:
            role_text = role_match.group(1).strip() if role_match.group(1) else ""
            if role_text:  # Only override if we have actual content
                character_data["role"] = role_text
        
        if personality_match:
            personality_text = personality_match.group(1).strip() if personality_match.group(1) else ""
            if personality_text:  # Only process if we have actual content
                traits = [trait.strip() for trait in personality_text.split(",") if trait.strip()]
                if traits:  # Only override if we have actual traits
                    character_data["personality_traits"] = traits
        
        return character_data
    
    async def create_character_in_s1(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create character in S1 system via API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.s1_endpoint}/character/create",
                    json=character_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"✅ [ADMIN_CHARACTER] Character created successfully: {character_data['name']}")
                        return {"success": True, "character": result}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ [ADMIN_CHARACTER] Character creation failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error creating character: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_character_in_s1(self, character_id: str) -> Dict[str, Any]:
        """Switch character in S1 system via API"""
        try:
            switch_payload = {"character_id": character_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.s1_endpoint}/character/switch",
                    json=switch_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ [ADMIN_CHARACTER] Character switched successfully: {character_id}")
                        return {"success": True, "character": result}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ [ADMIN_CHARACTER] Character switch failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error switching character: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_characters_in_s1(self) -> Dict[str, Any]:
        """List characters in S1 system via API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.s1_endpoint}/character/list",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ [ADMIN_CHARACTER] Characters listed successfully")
                        return {"success": True, "characters": result}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ [ADMIN_CHARACTER] Character listing failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error listing characters: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_character_info_in_s1(self, character_id: str) -> Dict[str, Any]:
        """Get character information from S1 system via API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.s1_endpoint}/character/current",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ [ADMIN_CHARACTER] Character info retrieved successfully")
                        return {"success": True, "character": result}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ [ADMIN_CHARACTER] Character info failed: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error getting character info: {e}")
            return {"success": False, "error": str(e)}
    
    async def notify_s2_character_change(self, character_id: str) -> bool:
        """Notify S2 systems about character change for persona-aware tool updates"""
        try:
            # Import here to avoid circular dependencies
            from autogen_agent.core.persona_aware_tool_registry import get_persona_tool_registry
            from autogen_agent.services.character_state_manager import get_character_state_manager
            
            # Notify character state manager
            character_manager = get_character_state_manager()
            if character_manager:
                success = await character_manager.handle_character_change(character_id)
                if success:
                    logger.info(f"✅ [ADMIN_CHARACTER] S2 character state updated: {character_id}")
                else:
                    logger.warning(f"⚠️ [ADMIN_CHARACTER] S2 character state update failed: {character_id}")
            
            # Notify persona-aware tool registry
            tool_registry = get_persona_tool_registry()
            if tool_registry:
                success = await tool_registry.handle_character_change_notification(character_id)
                if success:
                    logger.info(f"✅ [ADMIN_CHARACTER] S2 tool registry updated: {character_id}")
                else:
                    logger.warning(f"⚠️ [ADMIN_CHARACTER] S2 tool registry update failed: {character_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error notifying S2 of character change: {e}")
            return False
    
    async def execute_admin_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute admin command based on parsed content"""
        try:
            command_type = command["type"]
            
            if command_type == "create_character":
                character_name = command["match"]
                character_data = self.extract_character_details(command["content"], character_name)
                
                # Create character in S1
                result = await self.create_character_in_s1(character_data)
                
                if result["success"]:
                    response = f"✅ Character '{character_name}' created successfully as {character_data['role']}!"
                    response += f"\nCharacter ID: {character_data['id']}"
                    response += f"\nPersonality: {', '.join(character_data['personality_traits'])}"
                    response += f"\nCommunication Style: {character_data['communication_style']}"
                    return {
                        "success": True,
                        "response": response,
                        "character_created": character_data
                    }
                else:
                    return {
                        "success": False,
                        "response": f"❌ Failed to create character '{character_name}': {result['error']}"
                    }
            
            elif command_type == "switch_character":
                character_name = command["match"]
                character_id = character_name.lower().replace(" ", "_") + "_template"
                
                result = await self.switch_character_in_s1(character_id)
                
                if result["success"]:
                    # Notify S2 systems of character change
                    await self.notify_s2_character_change(character_id)
                    
                    response = f"✅ Successfully switched to character '{character_name}'!"
                    response += f"\n🔄 S2 systems updated for persona-aware tool access"
                    return {
                        "success": True,
                        "response": response,
                        "character_switched": character_id,
                        "s2_notified": True
                    }
                else:
                    return {
                        "success": False,
                        "response": f"❌ Failed to switch to character '{character_name}': {result['error']}"
                    }
            
            elif command_type == "list_characters":
                result = await self.list_characters_in_s1()
                
                if result["success"]:
                    characters = result["characters"]["characters"]
                    if characters:
                        response = "📋 Available Characters:\n"
                        for char in characters:
                            status = "✅ Current" if char["is_current"] else "⚪ Available"
                            response += f"\n{status} {char['name']} ({char['role']})"
                        response += f"\n\nTotal: {len(characters)} characters"
                    else:
                        response = "📋 No characters available. Use 'create character' to add one."
                    
                    return {
                        "success": True,
                        "response": response,
                        "characters": characters
                    }
                else:
                    return {
                        "success": False,
                        "response": f"❌ Failed to list characters: {result['error']}"
                    }
            
            elif command_type == "character_info":
                result = await self.get_character_info_in_s1(command["match"])
                
                if result["success"]:
                    char = result["character"]["character"]
                    response = f"📋 Character Information:\n"
                    response += f"Name: {char['name']}\n"
                    response += f"Role: {char['role']}\n"
                    response += f"Personality: {', '.join(char['personality_traits'])}\n"
                    response += f"Communication Style: {char['communication_style']}\n"
                    response += f"Domain Expertise: {', '.join(char['domain_expertise'])}\n"
                    response += f"Formality Level: {char['formality_level']}"
                    
                    return {
                        "success": True,
                        "response": response,
                        "character": char
                    }
                else:
                    return {
                        "success": False,
                        "response": f"❌ Failed to get character info: {result['error']}"
                    }
            
            elif command_type == "not_admin_command":
                return {
                    "success": False,
                    "response": "This doesn't appear to be an admin command.",
                    "skip": True
                }
            
            else:
                return {
                    "success": False,
                    "response": f"❌ Unknown admin command type: {command_type}"
                }
                
        except Exception as e:
            logger.error(f"❌ [ADMIN_CHARACTER] Error executing admin command: {e}")
            return {
                "success": False,
                "response": f"❌ Error executing admin command: {str(e)}"
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for the tool registry"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "score": self.score,
            "capabilities": [
                "create_character_via_admin_command",
                "switch_character_via_admin_command",
                "list_characters_via_admin_command",
                "character_info_via_admin_command",
                "character_template_generation"
            ],
            "supported_character_types": list(self.character_types.keys()),
            "admin_command_patterns": list(self.admin_patterns.keys())
        }

# Global admin character tool instance
admin_character_tool = AdminCharacterTool()

async def execute_admin_character_tool(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute admin character tool based on context"""
    try:
        content = context.get("content", "")
        
        # Parse admin command
        command = admin_character_tool.parse_admin_command(content)
        
        if command["type"] == "not_admin_command":
            return {
                "success": False,
                "response": "Not an admin command",
                "skip": True
            }
        
        # Execute admin command
        result = await admin_character_tool.execute_admin_command(command)
        
        return {
            "success": result["success"],
            "response": result["response"],
            "tool_used": "admin_character_tool",
            "command_type": command["type"],
            "character_data": result.get("character_created", {}),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"❌ [ADMIN_CHARACTER] Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_used": "admin_character_tool",
            "response": "❌ Error processing admin command"
        }

# Tool registry integration
async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for the admin character tool"""
    return await execute_admin_character_tool(context)