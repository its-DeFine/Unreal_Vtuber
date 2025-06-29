# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

# game_control_processor.py
import json
import logging
import requests
from typing import List, Dict, Any
from openai import OpenAI
from config import get_llm_config

class GameControlProcessor:
    """
    Specialized LLM processor for converting natural language prompts 
    into Unreal Engine TCP commands for avatar/environment control
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Game control system prompt - teaches the LLM about TCP commands
        self.system_prompt = self._build_system_prompt()
        
        # Initialize with lightweight LLM config for speed
        self.llm_config = get_llm_config(system_message=self.system_prompt)
        # Override with lighter model if available for faster processing
        if self.llm_config.get("LLM_PROVIDER") == "ollama":
            # Use faster model for game control if available
            self.llm_config["OLLAMA_MODEL"] = self.llm_config.get("GAME_CONTROL_MODEL", "llama3.2:3b")
        
        self.logger.info("🎮 Game Control Processor initialized")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that teaches the LLM about game commands"""
        return """You are a Game Control Assistant that converts natural language requests into Unreal Engine TCP commands.

IMPORTANT: Always respond with ONLY a valid JSON array of commands. No explanations, no extra text.

AVAILABLE COMMANDS:

LEVELS (Backgrounds):
- LVL.Home - Cloud environment  
- LVL.Medieval - Castle/fantasy scene
- LVL.DJ - Music/party environment
- LVL.Lofi - Cozy ambient setting

CHARACTER PRESETS:
- PRS.Masc - Masculine build
- PRS.Fem - Feminine build  
- PRS.Masc1 - Masculine variant
- PRS.Fem1 - Feminine variant

OUTFITS:
- OF.Default, OF.Maid Dress, OF.Pop Star, OF.Kimono, OF.Black Dress

HAIR STYLES:
- HS.Default, HS.Buzz, HS.Crop

HAIR COLOR (RGB 0.0-1.0):
- HCR.0.9 (red channel), HCG.0.8 (green), HCB.0.3 (blue)
- Red hair: HCR.0.9, HCG.0.1, HCB.0.1
- Blonde: HCR.0.9, HCG.0.8, HCB.0.3  
- Blue: HCR.0.1, HCG.0.3, HCB.0.9
- Yellow: HCR.0.9, HCG.0.9, HCB.0.2

SKIN COLOR:
- SKC.0.7 (0.2-1.2 range, 0.7 is medium)

EYE COLOR:
- EC.0.3 (hue 0.0-1.0), ES.15000 (saturation)

BONE SIZES (scaling):
- BNH.1.2 (head), BNC.0.9 (chest), BNA.1.0 (abdomen)
- BNAR.1.1 (arms), BNL.1.0 (legs), BNF.1.0 (feet)

MORPH TARGETS (0.0-1.0):
Face: MTNW.0.8 (nose width), MTCW.0.7 (chin width), MTEYW.0.6 (eye width)
Head: MTHT.0.5 (head top), MTHS.0.6 (head sides)

ANIMATIONS:
- ANIM.Dance

ENVIRONMENT:
- SNH.0.2 (sun height, 0.1=night, 0.8=day)
- STRB.0.8 (star brightness)

EXAMPLES:
Input: "yellow hair, medieval scene"  
Output: ["HCR.0.9", "HCG.0.9", "HCB.0.2", "LVL.Medieval"]

Input: "blue hair, bigger eyes, DJ scene"
Output: ["HCR.0.1", "HCG.0.3", "HCB.0.9", "MTEYW.0.8", "LVL.DJ"]

Input: "feminine character, maid dress, red hair"  
Output: ["PRS.Fem", "OF.Maid Dress", "HCR.0.9", "HCG.0.1", "HCB.0.1"]

Input: "night time, bright stars"
Output: ["SNH.0.1", "STRB.0.9"]

Respond ONLY with JSON array of commands. If no changes needed, return [].
"""

    def _generate_simple_llm_response(self, prompt: str) -> str:
        """
        Generate a simple LLM response using the configured provider
        
        Args:
            prompt: Input prompt for the LLM
            
        Returns:
            Response text from the LLM
        """
        provider = self.llm_config.get("LLM_PROVIDER", "openai")
        
        # Build messages in chat format
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            if provider == "ollama":
                return self._call_ollama(messages)
            elif provider == "openai":
                return self._call_openai(messages)
            else:
                self.logger.warning(f"🚫 Unsupported LLM provider for game control: {provider}")
                return "[]"  # Return empty array as fallback
        except Exception as e:
            self.logger.error(f"🚫 LLM call failed: {e}")
            return "[]"  # Return empty array on error
    
    def _call_ollama(self, messages: List[Dict]) -> str:
        """Call Ollama API for game control response"""
        try:
            endpoint = self.llm_config.get("OLLAMA_API_ENDPOINT", "http://vtuber-ollama:11434")
            model = self.llm_config.get("OLLAMA_MODEL", "llama3.2:3b")
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,  # Non-streaming for game control
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent output
                    "top_p": 0.9,
                    "num_predict": 200,  # Short response
                }
            }
            
            response = requests.post(f"{endpoint}/api/chat", json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if 'message' in result and 'content' in result['message']:
                return result['message']['content'].strip()
            else:
                self.logger.error("🚫 Unexpected Ollama response format")
                return "[]"
                
        except Exception as e:
            self.logger.error(f"🚫 Ollama call failed: {e}")
            return "[]"
    
    def _call_openai(self, messages: List[Dict]) -> str:
        """Call OpenAI API for game control response"""
        try:
            api_key = self.llm_config.get("OPENAI_API_KEY")
            if not api_key:
                self.logger.error("🚫 OpenAI API key not found")
                return "[]"
            
            model = self.llm_config.get("OPENAI_MODEL", "gpt-4o-mini")
            
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=200,  # Short response for game control
                temperature=0.1,  # Low temperature for consistent output
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"🚫 OpenAI call failed: {e}")
            return "[]"

    async def process_game_control_prompt(self, prompt: str) -> List[str]:
        """
        Process a game control prompt and return list of TCP commands
        
        Args:
            prompt: Natural language prompt like "yellow hair, medieval scene"
            
        Returns:
            List of TCP command strings
        """
        try:
            self.logger.info(f"🎮 Processing game control prompt: {prompt}")
            
            # Use the LLM to convert prompt to commands
            response = self._generate_simple_llm_response(prompt)
            
            # Parse JSON response
            try:
                commands = json.loads(response.strip())
                if isinstance(commands, list):
                    self.logger.info(f"🎯 Generated {len(commands)} game commands: {commands}")
                    return commands
                else:
                    self.logger.warning(f"🚫 Invalid response format (not a list): {response}")
                    return []
            except json.JSONDecodeError as e:
                self.logger.error(f"🚫 Failed to parse JSON response: {response}, Error: {e}")
                return []
                
        except Exception as e:
            self.logger.error(f"🚫 Error processing game control prompt: {e}")
            return []
    
    def validate_command(self, command: str) -> bool:
        """
        Validate if a command is properly formatted
        
        Args:
            command: TCP command string like "HCR.0.9"
            
        Returns:
            True if command appears valid
        """
        if not command or not isinstance(command, str):
            return False
            
        # Check basic format (KEY.VALUE or just KEY)
        if '.' not in command:
            # Simple commands like "MENU."
            return command.replace('.', '').replace(' ', '').isalpha()
        
        parts = command.split('.')
        if len(parts) != 2:
            return False
            
        key, value = parts
        
        # Validate key is alphabetic
        if not key.replace(' ', '').replace('_', '').isalpha():
            return False
            
        # If value is numeric, validate range
        try:
            float_val = float(value)
            # Most values should be 0.0-1.2 range (some exceptions exist)
            return -1.0 <= float_val <= 2.0
        except ValueError:
            # Non-numeric values (like "OF.Maid Dress") are also valid
            return True
    
    def get_supported_features(self) -> Dict[str, Any]:
        """Return dictionary of supported game control features"""
        return {
            "levels": ["Home", "Medieval", "DJ", "Lofi", "Split", "Split3", "Split4"],
            "presets": ["Masc", "Fem", "Masc1", "Fem1"],
            "outfits": ["Default", "Maid Dress", "Pop Star", "Kimono", "Black Dress"],
            "hair_styles": ["Default", "Buzz", "Crop"],
            "animations": ["Dance"],
            "color_channels": ["HCR", "HCG", "HCB"],  # Hair colors
            "morph_targets": {
                "nose": "MTNW",
                "chin": "MTCW", 
                "eyes": "MTEYW",
                "head_top": "MTHT"
            },
            "bone_scaling": {
                "head": "BNH",
                "chest": "BNC",
                "arms": "BNAR",
                "legs": "BNL"
            },
            "environment": {
                "sun_height": "SNH",
                "star_brightness": "STRB",
                "cloud_speed": "CLDS",
                "cloud_opacity": "CLDO"
            }
        } 