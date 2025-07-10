"""
Persona-Aware Tool Registry

This module extends the base tool registry with persona-aware capabilities,
ensuring tools are only available to appropriate character personas and
missions.
"""

import logging
import time
from typing import Callable, Dict, Optional, List, Any, Set
from autogen_agent.core.tool_registry import ToolRegistry
from autogen_agent.services.character_state_manager import get_character_state_manager, CharacterStateManager

logger = logging.getLogger(__name__)

class PersonaAwareToolRegistry(ToolRegistry):
    """Enhanced tool registry with persona-aware tool access control"""
    
    def __init__(self, package: str = "autogen_agent.tools"):
        super().__init__(package)
        self.character_state_manager: Optional[CharacterStateManager] = None
        
        # Persona-specific tool mappings
        self.persona_tool_mappings = {
            "doctor": {
                "allowed_tools": [
                    "medical_information_tool",
                    "health_assessment_tool",
                    "wellness_recommendation_tool", 
                    "symptom_analysis_tool",
                    "medication_information_tool",
                    "admin_character_tool",  # Always available for character management
                    "goal_management_tools",  # Core system tools
                    "core_evolution_tool"
                ],
                "restricted_tools": [
                    "recipe_generation_tool",
                    "cooking_technique_tool",
                    "workout_planning_tool",
                    "fitness_assessment_tool"
                ],
                "priority_boost": 0.3  # Boost for medical-related tools
            },
            "teacher": {
                "allowed_tools": [
                    "educational_content_tool",
                    "learning_assessment_tool",
                    "curriculum_planning_tool",
                    "study_guidance_tool", 
                    "knowledge_verification_tool",
                    "admin_character_tool",
                    "goal_management_tools",
                    "core_evolution_tool"
                ],
                "restricted_tools": [
                    "medical_information_tool",
                    "symptom_analysis_tool",
                    "recipe_generation_tool"
                ],
                "priority_boost": 0.25
            },
            "chef": {
                "allowed_tools": [
                    "recipe_generation_tool",
                    "ingredient_analysis_tool",
                    "cooking_technique_tool",
                    "nutrition_information_tool",
                    "meal_planning_tool",
                    "admin_character_tool",
                    "goal_management_tools",
                    "core_evolution_tool"
                ],
                "restricted_tools": [
                    "medical_information_tool",
                    "workout_planning_tool",
                    "educational_content_tool"
                ],
                "priority_boost": 0.3
            },
            "coach": {
                "allowed_tools": [
                    "workout_planning_tool",
                    "fitness_assessment_tool",
                    "motivation_tool",
                    "goal_tracking_tool",
                    "exercise_instruction_tool",
                    "admin_character_tool",
                    "goal_management_tools",
                    "core_evolution_tool"
                ],
                "restricted_tools": [
                    "medical_information_tool",
                    "recipe_generation_tool",
                    "educational_content_tool"
                ],
                "priority_boost": 0.35
            },
            "librarian": {
                "allowed_tools": [
                    "research_tool",
                    "information_organization_tool",
                    "fact_checking_tool",
                    "knowledge_discovery_tool",
                    "citation_tool",
                    "admin_character_tool",
                    "goal_management_tools",
                    "core_evolution_tool"
                ],
                "restricted_tools": [],  # Librarian has broad access
                "priority_boost": 0.2
            }
        }
        
        # Universal tools available to all personas
        self.universal_tools = {
            "admin_character_tool",      # Character management
            "goal_management_tools",     # Goal system
            "core_evolution_tool",       # System evolution
            "variable_tool_calls",       # Dynamic tool selection
            "weather_persona_tool"       # Weather information (if weather character)
        }
        
        logger.info("🎭 [PERSONA_TOOL_REGISTRY] Persona-aware tool registry initialized")
        logger.info(f"🔧 [PERSONA_TOOL_REGISTRY] Configured {len(self.persona_tool_mappings)} persona types")
    
    def set_character_state_manager(self, manager: CharacterStateManager):
        """Set the character state manager for persona awareness"""
        self.character_state_manager = manager
        logger.info("✅ [PERSONA_TOOL_REGISTRY] Character state manager connected")
    
    def _get_current_persona_type(self) -> Optional[str]:
        """Get current persona type from character state manager"""
        if not self.character_state_manager:
            return None
        
        character = self.character_state_manager.get_current_character()
        if not character:
            return None
        
        # Determine persona type from role
        role = character.role.lower()
        if "medical" in role or "doctor" in role:
            return "doctor"
        elif "teacher" in role or "educator" in role:
            return "teacher"
        elif "chef" in role or "culinary" in role:
            return "chef"
        elif "coach" in role or "fitness" in role:
            return "coach"
        elif "librarian" in role or "information" in role:
            return "librarian"
        
        return "librarian"  # Default fallback
    
    def _is_tool_allowed_for_persona(self, tool_name: str, persona_type: str) -> bool:
        """Check if a tool is allowed for a specific persona"""
        if tool_name in self.universal_tools:
            return True
        
        if persona_type not in self.persona_tool_mappings:
            return True  # Allow if persona not configured
        
        persona_config = self.persona_tool_mappings[persona_type]
        
        # Check if explicitly restricted
        if tool_name in persona_config.get("restricted_tools", []):
            return False
        
        # Check if explicitly allowed
        allowed_tools = persona_config.get("allowed_tools", [])
        if allowed_tools and tool_name not in allowed_tools:
            return False
        
        return True
    
    def get_available_tools_for_persona(self, persona_type: Optional[str] = None) -> List[str]:
        """Get list of tools available for current or specified persona"""
        if persona_type is None:
            persona_type = self._get_current_persona_type()
        
        if not persona_type:
            return self.list_tools()  # No restrictions if no persona
        
        available_tools = []
        for tool_name in self.tools.keys():
            if self._is_tool_allowed_for_persona(tool_name, persona_type):
                available_tools.append(tool_name)
        
        return available_tools
    
    def select_tool(self, context: dict) -> Optional[Callable]:
        """Select tool with persona-aware scoring"""
        if not self.tools:
            logger.warning("⚠️ [PERSONA_TOOL_REGISTRY] No tools available")
            return None
        
        # Get current persona type
        persona_type = self._get_current_persona_type()
        
        # Add character context to selection context
        if self.character_state_manager:
            character_context = self.character_state_manager.get_character_context_for_stimuli()
            context.update(character_context)
        
        # Extract context text for analysis
        context_text = self._extract_context_text(context)
        
        # Calculate scores for all tools with persona awareness
        tool_scores = {}
        for tool_name in self.tools.keys():
            # Check if tool is allowed for current persona
            if persona_type and not self._is_tool_allowed_for_persona(tool_name, persona_type):
                tool_scores[tool_name] = 0.0  # Block restricted tools
                logger.debug(f"🚫 [PERSONA_TOOL_REGISTRY] Tool {tool_name} blocked for persona {persona_type}")
                continue
            
            # Calculate base score
            score = self._calculate_tool_score_with_persona(tool_name, context, context_text, persona_type)
            tool_scores[tool_name] = score
            logger.debug(f"🎯 [PERSONA_TOOL_REGISTRY] Tool {tool_name}: score {score:.3f}")
        
        # Filter out zero scores (blocked tools)
        available_scores = {name: score for name, score in tool_scores.items() if score > 0.0}
        
        if not available_scores:
            logger.warning(f"⚠️ [PERSONA_TOOL_REGISTRY] No tools available for persona {persona_type}")
            return None
        
        # Select tool with highest score
        selected_name = max(available_scores, key=available_scores.get)
        selected_score = available_scores[selected_name]
        
        # Store selection scores
        if not hasattr(self, '_last_selection_scores'):
            self._last_selection_scores = {}
        self._last_selection_scores = tool_scores.copy()
        
        # Update usage history
        self._update_tool_usage(selected_name, context)
        
        logger.info(f"🧠 [PERSONA_TOOL_REGISTRY] PERSONA-AWARE selection: {selected_name} (score: {selected_score:.3f}, persona: {persona_type})")
        logger.info(f"📊 [PERSONA_TOOL_REGISTRY] Available tools: {', '.join([f'{name}:{score:.2f}' for name, score in sorted(available_scores.items(), key=lambda x: x[1], reverse=True)])}")
        
        return self.tools[selected_name]
    
    def _calculate_tool_score_with_persona(self, tool_name: str, context: dict, context_text: str, persona_type: Optional[str]) -> float:
        """Calculate tool score with persona-aware enhancements"""
        # Get base score from parent class
        base_score = super()._calculate_tool_score(tool_name, context, context_text)
        
        if not persona_type:
            return base_score
        
        # Apply persona-specific bonuses
        persona_config = self.persona_tool_mappings.get(persona_type, {})
        
        # Priority boost for persona-specific tools
        allowed_tools = persona_config.get("allowed_tools", [])
        if tool_name in allowed_tools and tool_name not in self.universal_tools:
            priority_boost = persona_config.get("priority_boost", 0.0)
            base_score += priority_boost
            logger.debug(f"🎭 [PERSONA_TOOL_REGISTRY] Persona boost {priority_boost:.2f} for {tool_name}")
        
        # Character mission priority context boost
        if self.character_state_manager:
            if self.character_state_manager.should_prioritize_context(context_text):
                base_score += 0.2
                logger.debug(f"🎯 [PERSONA_TOOL_REGISTRY] Mission context boost for {tool_name}")
        
        # Operational mode adjustments
        if self.character_state_manager:
            operational_mode = self.character_state_manager.get_operational_mode()
            
            # Boost autonomous tools in autonomous mode
            if operational_mode == "autonomous":
                autonomous_tools = ["goal_management_tools", "core_evolution_tool"]
                if tool_name in autonomous_tools:
                    base_score += 0.15
            
            # Boost reactive tools in reactive mode  
            elif operational_mode == "reactive":
                # Character-specific tools get boost in reactive mode
                if tool_name in allowed_tools:
                    base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_context_relevance(self, tool_name: str, context: dict, context_text: str) -> float:
        """Enhanced context relevance with persona awareness"""
        # Get base relevance
        base_relevance = super()._calculate_context_relevance(tool_name, context, context_text)
        
        # Add persona-specific context mappings
        persona_type = self._get_current_persona_type()
        if not persona_type:
            return base_relevance
        
        # Enhanced context mappings for persona tools
        persona_context_mappings = {
            "medical_information_tool": ["health", "medical", "symptoms", "diagnosis", "treatment", "medicine", "healthcare", "wellness"],
            "health_assessment_tool": ["health", "symptoms", "assessment", "evaluation", "medical"],
            "wellness_recommendation_tool": ["wellness", "health", "lifestyle", "prevention", "wellbeing"],
            "symptom_analysis_tool": ["symptoms", "diagnosis", "medical", "analysis", "health"],
            "medication_information_tool": ["medication", "drugs", "prescription", "medicine", "treatment"],
            
            "educational_content_tool": ["education", "learning", "teaching", "curriculum", "instruction"],
            "learning_assessment_tool": ["assessment", "evaluation", "learning", "progress", "education"],
            "curriculum_planning_tool": ["curriculum", "planning", "education", "syllabus", "course"],
            "study_guidance_tool": ["study", "guidance", "learning", "education", "instruction"],
            "knowledge_verification_tool": ["knowledge", "verification", "testing", "assessment", "evaluation"],
            
            "recipe_generation_tool": ["recipe", "cooking", "food", "cuisine", "meal", "dish"],
            "ingredient_analysis_tool": ["ingredients", "food", "nutrition", "cooking", "analysis"],
            "cooking_technique_tool": ["cooking", "technique", "culinary", "kitchen", "method"],
            "nutrition_information_tool": ["nutrition", "diet", "health", "food", "nutrients"],
            "meal_planning_tool": ["meal", "planning", "food", "diet", "menu"],
            
            "workout_planning_tool": ["workout", "exercise", "fitness", "training", "physical"],
            "fitness_assessment_tool": ["fitness", "assessment", "health", "physical", "evaluation"],
            "motivation_tool": ["motivation", "goals", "inspiration", "encouragement", "support"],
            "goal_tracking_tool": ["goals", "tracking", "progress", "achievement", "objectives"],
            "exercise_instruction_tool": ["exercise", "instruction", "fitness", "training", "movement"],
            
            "research_tool": ["research", "information", "investigation", "study", "analysis"],
            "information_organization_tool": ["organization", "categorization", "structure", "management", "data"],
            "fact_checking_tool": ["facts", "verification", "accuracy", "truth", "validation"],
            "knowledge_discovery_tool": ["knowledge", "discovery", "learning", "exploration", "research"],
            "citation_tool": ["citation", "reference", "source", "bibliography", "documentation"]
        }
        
        if tool_name in persona_context_mappings:
            keywords = persona_context_mappings[tool_name]
            context_lower = context_text.lower()
            matches = sum(1 for keyword in keywords if keyword in context_lower)
            if matches > 0:
                keyword_relevance = (matches / len(keywords)) * 0.8
                base_relevance += keyword_relevance
                logger.debug(f"🔍 [PERSONA_TOOL_REGISTRY] Keyword relevance boost {keyword_relevance:.2f} for {tool_name}")
        
        return min(base_relevance, 1.0)
    
    def get_persona_tool_status(self) -> Dict[str, Any]:
        """Get persona-aware tool registry status"""
        base_status = self.get_tool_status()
        
        persona_type = self._get_current_persona_type()
        available_tools = self.get_available_tools_for_persona(persona_type)
        
        persona_status = {
            "persona_awareness_enabled": True,
            "character_state_manager_connected": self.character_state_manager is not None,
            "current_persona": persona_type,
            "available_tools_for_persona": available_tools,
            "persona_tool_count": len(available_tools),
            "universal_tools": list(self.universal_tools),
            "configured_personas": list(self.persona_tool_mappings.keys())
        }
        
        if self.character_state_manager:
            character = self.character_state_manager.get_current_character()
            if character:
                persona_status["character_info"] = {
                    "character_name": character.character_name,
                    "role": character.role,
                    "operational_mode": self.character_state_manager.get_operational_mode(),
                    "mission_active": character.mission is not None,
                    "priority_contexts": self.character_state_manager.get_priority_contexts()
                }
        
        # Merge with base status
        base_status.update(persona_status)
        return base_status
    
    async def handle_character_change_notification(self, character_id: str):
        """Handle character change notification for tool availability updates"""
        logger.info(f"🔄 [PERSONA_TOOL_REGISTRY] Handling character change: {character_id}")
        
        if self.character_state_manager:
            success = await self.character_state_manager.handle_character_change(character_id)
            if success:
                new_persona = self._get_current_persona_type()
                available_tools = self.get_available_tools_for_persona(new_persona)
                logger.info(f"✅ [PERSONA_TOOL_REGISTRY] Tool availability updated for persona: {new_persona}")
                logger.info(f"🔧 [PERSONA_TOOL_REGISTRY] Available tools: {len(available_tools)}")
                return True
            else:
                logger.error("❌ [PERSONA_TOOL_REGISTRY] Failed to update character state")
                return False
        else:
            logger.warning("⚠️ [PERSONA_TOOL_REGISTRY] No character state manager connected")
            return False


# Global persona-aware tool registry instance
global_persona_tool_registry: Optional[PersonaAwareToolRegistry] = None

def get_persona_tool_registry() -> Optional[PersonaAwareToolRegistry]:
    """Get the global persona-aware tool registry instance"""
    return global_persona_tool_registry

def initialize_persona_tool_registry(package: str = "autogen_agent.tools") -> PersonaAwareToolRegistry:
    """Initialize the global persona-aware tool registry"""
    global global_persona_tool_registry
    
    if global_persona_tool_registry:
        logger.warning("⚠️ [PERSONA_TOOL_REGISTRY] Already initialized")
        return global_persona_tool_registry
    
    global_persona_tool_registry = PersonaAwareToolRegistry(package)
    
    # Connect character state manager if available
    character_manager = get_character_state_manager()
    if character_manager:
        global_persona_tool_registry.set_character_state_manager(character_manager)
    
    logger.info("✅ [PERSONA_TOOL_REGISTRY] Global persona-aware tool registry initialized")
    return global_persona_tool_registry