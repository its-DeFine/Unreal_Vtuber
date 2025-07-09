"""
Character State Manager for System 2 (AutoGen)

This module manages character state synchronization between S1 and S2 systems,
providing persona-aware tool access and mission-based operations.
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CharacterMission:
    """Mission configuration for a character persona"""
    mission_id: str
    title: str
    description: str
    objectives: List[str]
    target_outcomes: List[str]
    success_metrics: List[str]
    available_tools: List[str]
    priority_contexts: List[str]
    operational_mode: str  # autonomous, reactive, hybrid
    duration: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class CharacterState:
    """Complete character state for S2 operations"""
    character_id: str
    character_name: str
    role: str
    personality_traits: List[str]
    domain_expertise: List[str]
    behavioral_rules: List[str]
    mission: Optional[CharacterMission] = None
    available_tools: Set[str] = field(default_factory=set)
    last_sync: Optional[datetime] = None
    is_active: bool = False
    
class CharacterStateManager:
    """Manages character state and persona-aware tool access for S2"""
    
    def __init__(self, s1_endpoint: str = "http://neurosync:5001"):
        self.s1_endpoint = s1_endpoint
        self.current_character: Optional[CharacterState] = None
        self.character_cache: Dict[str, CharacterState] = {}
        self.mission_templates: Dict[str, CharacterMission] = {}
        self.sync_interval = 30  # seconds
        self.last_sync_attempt = None
        
        # Initialize mission templates
        self._initialize_mission_templates()
        
        logger.info("🎭 [CHARACTER_STATE] Character State Manager initialized")
    
    def _initialize_mission_templates(self):
        """Initialize predefined mission templates for different persona types"""
        
        # Medical Professional Mission
        self.mission_templates["doctor"] = CharacterMission(
            mission_id="medical_assistance",
            title="Medical Information and Health Guidance",
            description="Provide accurate medical information, health guidance, and wellness support",
            objectives=[
                "Offer evidence-based medical information",
                "Provide health and wellness recommendations",
                "Support patient education and health literacy",
                "Promote preventive care and healthy lifestyle choices"
            ],
            target_outcomes=[
                "Improved health awareness and education",
                "Better understanding of medical conditions",
                "Enhanced wellness and prevention practices",
                "Increased health literacy"
            ],
            success_metrics=[
                "Accuracy of medical information provided",
                "Patient satisfaction and understanding",
                "Positive health behavior changes",
                "Reduced health-related anxiety"
            ],
            available_tools=[
                "medical_information_tool",
                "health_assessment_tool", 
                "wellness_recommendation_tool",
                "symptom_analysis_tool",
                "medication_information_tool"
            ],
            priority_contexts=[
                "health", "medical", "symptoms", "diagnosis", "treatment",
                "wellness", "prevention", "medication", "healthcare"
            ],
            operational_mode="reactive"
        )
        
        # Educational Professional Mission  
        self.mission_templates["teacher"] = CharacterMission(
            mission_id="educational_support",
            title="Educational Instruction and Learning Support",
            description="Provide educational guidance, learning support, and knowledge transfer",
            objectives=[
                "Facilitate learning and knowledge acquisition",
                "Provide clear explanations and instruction",
                "Support educational goal achievement",
                "Encourage critical thinking and curiosity"
            ],
            target_outcomes=[
                "Enhanced learning outcomes and comprehension",
                "Improved educational engagement",
                "Better knowledge retention and application",
                "Increased learning motivation"
            ],
            success_metrics=[
                "Learning objective achievement",
                "Student engagement and participation",
                "Knowledge retention rates",
                "Educational goal progress"
            ],
            available_tools=[
                "educational_content_tool",
                "learning_assessment_tool",
                "curriculum_planning_tool",
                "study_guidance_tool",
                "knowledge_verification_tool"
            ],
            priority_contexts=[
                "learning", "education", "teaching", "curriculum", "study",
                "knowledge", "instruction", "academic", "school"
            ],
            operational_mode="hybrid"
        )
        
        # Culinary Expert Mission
        self.mission_templates["chef"] = CharacterMission(
            mission_id="culinary_guidance",
            title="Culinary Expertise and Cooking Guidance",
            description="Provide cooking instruction, recipe guidance, and culinary knowledge",
            objectives=[
                "Share culinary techniques and cooking methods",
                "Provide recipe recommendations and modifications",
                "Educate about ingredients and food safety",
                "Inspire culinary creativity and experimentation"
            ],
            target_outcomes=[
                "Improved cooking skills and techniques",
                "Enhanced culinary knowledge and confidence",
                "Better understanding of flavors and ingredients",
                "Increased cooking enjoyment and creativity"
            ],
            success_metrics=[
                "Cooking skill improvement",
                "Recipe success rates",
                "Culinary knowledge expansion",
                "Cooking confidence levels"
            ],
            available_tools=[
                "recipe_generation_tool",
                "ingredient_analysis_tool",
                "cooking_technique_tool",
                "nutrition_information_tool",
                "meal_planning_tool"
            ],
            priority_contexts=[
                "cooking", "recipe", "ingredients", "food", "cuisine",
                "flavor", "technique", "kitchen", "culinary"
            ],
            operational_mode="reactive"
        )
        
        # Fitness Coach Mission
        self.mission_templates["coach"] = CharacterMission(
            mission_id="fitness_coaching",
            title="Fitness Coaching and Wellness Motivation",
            description="Provide fitness guidance, motivation, and wellness coaching",
            objectives=[
                "Motivate and inspire fitness goals achievement",
                "Provide workout guidance and exercise instruction",
                "Support healthy lifestyle habits development",
                "Encourage consistent fitness practice"
            ],
            target_outcomes=[
                "Improved physical fitness and health",
                "Enhanced motivation and goal achievement",
                "Better exercise habits and consistency",
                "Increased wellness and energy levels"
            ],
            success_metrics=[
                "Fitness goal achievement rates",
                "Exercise consistency and adherence",
                "Physical health improvements",
                "Motivation and engagement levels"
            ],
            available_tools=[
                "workout_planning_tool",
                "fitness_assessment_tool",
                "motivation_tool",
                "goal_tracking_tool",
                "exercise_instruction_tool"
            ],
            priority_contexts=[
                "fitness", "exercise", "workout", "health", "wellness",
                "goals", "motivation", "training", "physical"
            ],
            operational_mode="autonomous"
        )
        
        # Information Specialist Mission
        self.mission_templates["librarian"] = CharacterMission(
            mission_id="information_management",
            title="Information Organization and Research Support",
            description="Provide information organization, research assistance, and knowledge management",
            objectives=[
                "Organize and categorize information effectively",
                "Provide research assistance and guidance",
                "Support information literacy and fact-checking",
                "Facilitate knowledge discovery and access"
            ],
            target_outcomes=[
                "Improved information organization and access",
                "Enhanced research skills and efficiency",
                "Better information literacy and critical evaluation",
                "Increased knowledge discovery and learning"
            ],
            success_metrics=[
                "Information organization effectiveness",
                "Research success and accuracy rates",
                "Information literacy improvement",
                "Knowledge access and utilization"
            ],
            available_tools=[
                "research_tool",
                "information_organization_tool",
                "fact_checking_tool",
                "knowledge_discovery_tool",
                "citation_tool"
            ],
            priority_contexts=[
                "research", "information", "knowledge", "data", "facts",
                "organization", "library", "documentation", "reference"
            ],
            operational_mode="hybrid"
        )
        
        logger.info(f"🎯 [CHARACTER_STATE] Initialized {len(self.mission_templates)} mission templates")
    
    async def sync_with_s1(self) -> bool:
        """Synchronize character state with S1 system"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get current character from S1
                async with session.get(f"{self.s1_endpoint}/character/current") as response:
                    if response.status == 200:
                        s1_data = await response.json()
                        character_info = s1_data.get("character", {})
                        
                        if character_info:
                            await self._update_character_state(character_info)
                            self.last_sync_attempt = datetime.now()
                            logger.info(f"✅ [CHARACTER_STATE] Synchronized with S1: {character_info.get('name', 'Unknown')}")
                            return True
                        else:
                            logger.warning("⚠️ [CHARACTER_STATE] No active character in S1")
                            self.current_character = None
                            return False
                    else:
                        logger.error(f"❌ [CHARACTER_STATE] S1 sync failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ [CHARACTER_STATE] S1 sync error: {e}")
            return False
    
    async def _update_character_state(self, character_info: Dict[str, Any]):
        """Update character state from S1 character information"""
        character_id = character_info.get("id", "unknown")
        character_name = character_info.get("name", "Unknown")
        role = character_info.get("role", "")
        
        # Determine persona type from role or domain expertise
        persona_type = self._determine_persona_type(character_info)
        
        # Get mission template for this persona type
        mission = None
        if persona_type in self.mission_templates:
            mission_template = self.mission_templates[persona_type]
            mission = CharacterMission(
                mission_id=f"{character_id}_{mission_template.mission_id}",
                title=mission_template.title,
                description=mission_template.description,
                objectives=mission_template.objectives.copy(),
                target_outcomes=mission_template.target_outcomes.copy(),
                success_metrics=mission_template.success_metrics.copy(),
                available_tools=mission_template.available_tools.copy(),
                priority_contexts=mission_template.priority_contexts.copy(),
                operational_mode=mission_template.operational_mode
            )
        
        # Create character state
        character_state = CharacterState(
            character_id=character_id,
            character_name=character_name,
            role=role,
            personality_traits=character_info.get("personality_traits", []),
            domain_expertise=character_info.get("domain_expertise", []),
            behavioral_rules=character_info.get("behavioral_rules", []),
            mission=mission,
            available_tools=set(mission.available_tools) if mission else set(),
            last_sync=datetime.now(),
            is_active=True
        )
        
        # Update current character and cache
        self.current_character = character_state
        self.character_cache[character_id] = character_state
        
        logger.info(f"🎭 [CHARACTER_STATE] Updated character: {character_name} ({persona_type})")
        if mission:
            logger.info(f"🎯 [CHARACTER_STATE] Mission: {mission.title}")
            logger.info(f"🔧 [CHARACTER_STATE] Available tools: {len(mission.available_tools)}")
    
    def _determine_persona_type(self, character_info: Dict[str, Any]) -> str:
        """Determine persona type from character information"""
        role = character_info.get("role", "").lower()
        domain_expertise = [exp.lower() for exp in character_info.get("domain_expertise", [])]
        
        # Check role keywords
        if "medical" in role or "doctor" in role or "physician" in role:
            return "doctor"
        elif "teacher" in role or "educator" in role or "professor" in role or "instructor" in role:
            return "teacher"
        elif "chef" in role or "culinary" in role or "cook" in role:
            return "chef"
        elif "coach" in role or "trainer" in role or "fitness" in role:
            return "coach"
        elif "librarian" in role or "information" in role or "research" in role:
            return "librarian"
        
        # Check domain expertise
        medical_domains = ["medicine", "health", "healthcare", "medical"]
        education_domains = ["education", "teaching", "learning", "academic"]
        culinary_domains = ["cooking", "culinary", "food", "cuisine"]
        fitness_domains = ["fitness", "wellness", "training", "exercise"]
        information_domains = ["research", "information", "knowledge", "library"]
        
        if any(domain in medical_domains for domain in domain_expertise):
            return "doctor"
        elif any(domain in education_domains for domain in domain_expertise):
            return "teacher"
        elif any(domain in culinary_domains for domain in domain_expertise):
            return "chef"
        elif any(domain in fitness_domains for domain in domain_expertise):
            return "coach"
        elif any(domain in information_domains for domain in domain_expertise):
            return "librarian"
        
        # Default to librarian for general assistance
        return "librarian"
    
    def get_current_character(self) -> Optional[CharacterState]:
        """Get current active character state"""
        return self.current_character
    
    def get_available_tools(self) -> Set[str]:
        """Get tools available to current character"""
        if self.current_character and self.current_character.mission:
            return self.current_character.available_tools
        return set()
    
    def is_tool_available_for_character(self, tool_name: str) -> bool:
        """Check if a tool is available for the current character"""
        available_tools = self.get_available_tools()
        if not available_tools:
            return True  # No restrictions if no character active
        return tool_name in available_tools
    
    def get_character_mission(self) -> Optional[CharacterMission]:
        """Get current character's mission"""
        if self.current_character:
            return self.current_character.mission
        return None
    
    def get_priority_contexts(self) -> List[str]:
        """Get priority contexts for current character"""
        if self.current_character and self.current_character.mission:
            return self.current_character.mission.priority_contexts
        return []
    
    def should_prioritize_context(self, context_text: str) -> bool:
        """Check if context should be prioritized for current character"""
        priority_contexts = self.get_priority_contexts()
        if not priority_contexts:
            return False
        
        context_lower = context_text.lower()
        return any(priority in context_lower for priority in priority_contexts)
    
    def get_operational_mode(self) -> str:
        """Get current character's operational mode"""
        if self.current_character and self.current_character.mission:
            return self.current_character.mission.operational_mode
        return "reactive"
    
    async def handle_character_change(self, character_id: str) -> bool:
        """Handle character change notification from admin system"""
        logger.info(f"🔄 [CHARACTER_STATE] Handling character change to: {character_id}")
        
        # Force sync with S1 to get new character
        success = await self.sync_with_s1()
        
        if success and self.current_character:
            logger.info(f"✅ [CHARACTER_STATE] Character changed to: {self.current_character.character_name}")
            logger.info(f"🎯 [CHARACTER_STATE] New mission: {self.current_character.mission.title if self.current_character.mission else 'No mission'}")
            return True
        else:
            logger.error(f"❌ [CHARACTER_STATE] Failed to sync character change")
            return False
    
    def get_character_context_for_stimuli(self) -> Dict[str, Any]:
        """Get character context information for stimuli processing"""
        if not self.current_character:
            return {"character_active": False}
        
        context = {
            "character_active": True,
            "character_id": self.current_character.character_id,
            "character_name": self.current_character.character_name,
            "role": self.current_character.role,
            "domain_expertise": self.current_character.domain_expertise,
            "operational_mode": self.get_operational_mode(),
            "available_tools": list(self.get_available_tools()),
            "priority_contexts": self.get_priority_contexts()
        }
        
        if self.current_character.mission:
            context["mission"] = {
                "title": self.current_character.mission.title,
                "description": self.current_character.mission.description,
                "objectives": self.current_character.mission.objectives,
                "target_outcomes": self.current_character.mission.target_outcomes
            }
        
        return context
    
    def get_status(self) -> Dict[str, Any]:
        """Get character state manager status"""
        status = {
            "manager_active": True,
            "s1_endpoint": self.s1_endpoint,
            "last_sync": self.last_sync_attempt.isoformat() if self.last_sync_attempt else None,
            "cached_characters": len(self.character_cache),
            "mission_templates": len(self.mission_templates)
        }
        
        if self.current_character:
            status["current_character"] = {
                "character_id": self.current_character.character_id,
                "character_name": self.current_character.character_name,
                "role": self.current_character.role,
                "is_active": self.current_character.is_active,
                "available_tools_count": len(self.current_character.available_tools),
                "mission_active": self.current_character.mission is not None,
                "operational_mode": self.get_operational_mode(),
                "last_sync": self.current_character.last_sync.isoformat() if self.current_character.last_sync else None
            }
            
            if self.current_character.mission:
                status["current_character"]["mission"] = {
                    "mission_id": self.current_character.mission.mission_id,
                    "title": self.current_character.mission.title,
                    "objectives_count": len(self.current_character.mission.objectives),
                    "available_tools": list(self.current_character.available_tools),
                    "priority_contexts": self.current_character.mission.priority_contexts
                }
        else:
            status["current_character"] = None
        
        return status


# Global character state manager instance
global_character_state_manager: Optional[CharacterStateManager] = None

def get_character_state_manager() -> Optional[CharacterStateManager]:
    """Get the global character state manager instance"""
    return global_character_state_manager

def initialize_character_state_manager(s1_endpoint: str = "http://neurosync:5001") -> CharacterStateManager:
    """Initialize the global character state manager"""
    global global_character_state_manager
    
    if global_character_state_manager:
        logger.warning("⚠️ [CHARACTER_STATE] Manager already initialized")
        return global_character_state_manager
    
    global_character_state_manager = CharacterStateManager(s1_endpoint)
    logger.info("✅ [CHARACTER_STATE] Global character state manager initialized")
    return global_character_state_manager