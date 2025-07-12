"""
Unified Character State Management
=================================

Single source of truth for character state across S1/S2 systems.
Consolidates character management from multiple locations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Set
import uuid

from ..config import get_config
from ..di import ServiceLifecycle, singleton
from ..errors import handle_errors, error_context, ValidationError
from ..queue import QueueService


logger = logging.getLogger(__name__)


class CharacterOperationalState(str, Enum):
    """Character operational states"""
    INACTIVE = "inactive"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MissionType(str, Enum):
    """Available mission types"""
    TRADING = "trading"
    EDUCATION = "education"
    STREAMING = "streaming"
    GENERAL = "general"
    RESEARCH = "research"
    ENTERTAINMENT = "entertainment"


@dataclass
class CharacterProfile:
    """Complete character profile"""
    id: str
    name: str
    template_name: str
    mission_type: MissionType
    system_assignment: str  # "s1", "s2", "both"
    capabilities: List[str]
    preferences: Dict[str, Any]
    constraints: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if not self.capabilities:
            self.capabilities = []
        if not self.preferences:
            self.preferences = {}
        if not self.constraints:
            self.constraints = {}
        if not self.metadata:
            self.metadata = {}


@dataclass
class CharacterRuntimeState:
    """Real-time character state"""
    character_id: str
    current_state: CharacterOperationalState
    last_activity: datetime
    current_mission: Optional[str]
    active_sessions: Set[str]
    resource_usage: Dict[str, float]
    performance_metrics: Dict[str, Any]
    error_count: int
    last_error: Optional[str]
    
    def __post_init__(self):
        if not self.active_sessions:
            self.active_sessions = set()
        if not self.resource_usage:
            self.resource_usage = {}
        if not self.performance_metrics:
            self.performance_metrics = {}


@dataclass
class MissionTemplate:
    """Mission configuration template"""
    id: str
    name: str
    mission_type: MissionType
    description: str
    required_capabilities: List[str]
    default_tools: List[str]
    autonomy_level: str  # "low", "medium", "high", "maximum"
    max_duration: timedelta
    success_criteria: Dict[str, Any]
    
    def __post_init__(self):
        if not self.required_capabilities:
            self.required_capabilities = []
        if not self.default_tools:
            self.default_tools = []
        if not self.success_criteria:
            self.success_criteria = {}


@singleton()
class CharacterManager(ServiceLifecycle):
    """
    Unified character state management service.
    
    Consolidates character management from:
    - autogen-agent/services/character_state_manager.py
    - graphflow character coordination
    - S1 system character management
    
    Features:
    - Centralized character profiles
    - Real-time state tracking
    - Mission management
    - Cross-system synchronization
    - Performance monitoring
    """
    
    def __init__(self, queue_service: QueueService = None):
        self.queue_service = queue_service
        
        # Character data
        self.profiles: Dict[str, CharacterProfile] = {}
        self.states: Dict[str, CharacterRuntimeState] = {}
        self.mission_templates: Dict[str, MissionTemplate] = {}
        
        # Synchronization
        self._state_locks: Dict[str, asyncio.Lock] = {}
        self._sync_task: Optional[asyncio.Task] = None
        
        self._running = False
    
    async def start(self):
        """Start character manager"""
        if self._running:
            return
        
        # Load default character profiles and missions
        await self._load_default_profiles()
        await self._load_mission_templates()
        
        # Start state synchronization task
        self._sync_task = asyncio.create_task(self._state_sync_loop())
        
        self._running = True
        logger.info("Character manager started")
    
    async def stop(self):
        """Stop character manager"""
        if not self._running:
            return
        
        # Stop sync task
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        self._running = False
        logger.info("Character manager stopped")
    
    async def health_check(self) -> bool:
        """Check manager health"""
        return self._running and len(self.profiles) > 0
    
    def _get_state_lock(self, character_id: str) -> asyncio.Lock:
        """Get or create state lock for character"""
        if character_id not in self._state_locks:
            self._state_locks[character_id] = asyncio.Lock()
        return self._state_locks[character_id]
    
    @handle_errors(operation="register_character", component="character_manager")
    async def register_character(
        self,
        character_id: str,
        name: str,
        template_name: str,
        mission_type: MissionType,
        system_assignment: str = "both",
        capabilities: List[str] = None,
        preferences: Dict[str, Any] = None,
        constraints: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> CharacterProfile:
        """Register a new character"""
        if character_id in self.profiles:
            raise ValidationError(f"Character already registered: {character_id}")
        
        profile = CharacterProfile(
            id=character_id,
            name=name,
            template_name=template_name,
            mission_type=mission_type,
            system_assignment=system_assignment,
            capabilities=capabilities or [],
            preferences=preferences or {},
            constraints=constraints or {},
            metadata=metadata or {}
        )
        
        # Create initial state
        state = CharacterRuntimeState(
            character_id=character_id,
            current_state=CharacterOperationalState.IDLE,
            last_activity=datetime.now(),
            current_mission=None,
            active_sessions=set(),
            resource_usage={},
            performance_metrics={},
            error_count=0,
            last_error=None
        )
        
        async with self._get_state_lock(character_id):
            self.profiles[character_id] = profile
            self.states[character_id] = state
        
        logger.info(f"Registered character: {character_id} ({name})")
        return profile
    
    @handle_errors(operation="get_character", component="character_manager")
    async def get_character(self, character_id: str) -> Optional[CharacterProfile]:
        """Get character profile"""
        return self.profiles.get(character_id)
    
    @handle_errors(operation="get_character_state", component="character_manager")
    async def get_character_state(self, character_id: str) -> Optional[CharacterRuntimeState]:
        """Get character state"""
        return self.states.get(character_id)
    
    @handle_errors(operation="update_character_state", component="character_manager")
    async def update_character_state(
        self,
        character_id: str,
        state: CharacterOperationalState = None,
        current_mission: str = None,
        add_session: str = None,
        remove_session: str = None,
        resource_usage: Dict[str, float] = None,
        performance_metrics: Dict[str, Any] = None,
        error_message: str = None
    ) -> bool:
        """Update character state"""
        if character_id not in self.states:
            raise ValidationError(f"Character not found: {character_id}")
        
        async with self._get_state_lock(character_id):
            char_state = self.states[character_id]
            
            if state:
                char_state.current_state = state
            
            if current_mission is not None:
                char_state.current_mission = current_mission
            
            if add_session:
                char_state.active_sessions.add(add_session)
            
            if remove_session:
                char_state.active_sessions.discard(remove_session)
            
            if resource_usage:
                char_state.resource_usage.update(resource_usage)
            
            if performance_metrics:
                char_state.performance_metrics.update(performance_metrics)
            
            if error_message:
                char_state.error_count += 1
                char_state.last_error = error_message
                if char_state.error_count > 5:  # Too many errors
                    char_state.current_state = CharacterOperationalState.ERROR
            
            char_state.last_activity = datetime.now()
        
        logger.debug(f"Updated state for character {character_id}")
        return True
    
    @handle_errors(operation="assign_mission", component="character_manager")
    async def assign_mission(
        self,
        character_id: str,
        mission_template_id: str,
        session_id: str = None,
        custom_parameters: Dict[str, Any] = None
    ) -> str:
        """Assign mission to character"""
        if character_id not in self.profiles:
            raise ValidationError(f"Character not found: {character_id}")
        
        if mission_template_id not in self.mission_templates:
            raise ValidationError(f"Mission template not found: {mission_template_id}")
        
        profile = self.profiles[character_id]
        template = self.mission_templates[mission_template_id]
        
        # Validate capabilities
        missing_capabilities = set(template.required_capabilities) - set(profile.capabilities)
        if missing_capabilities:
            raise ValidationError(
                f"Character {character_id} missing required capabilities: {missing_capabilities}"
            )
        
        # Create mission instance
        mission_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        # Update character state
        await self.update_character_state(
            character_id=character_id,
            state=CharacterOperationalState.BUSY,
            current_mission=mission_id,
            add_session=session_id
        )
        
        # Queue mission for processing
        if self.queue_service:
            await self.queue_service.enqueue(
                queue_name=f"missions_{template.mission_type.value}",
                payload={
                    "mission_id": mission_id,
                    "character_id": character_id,
                    "template_id": mission_template_id,
                    "session_id": session_id,
                    "custom_parameters": custom_parameters or {},
                    "assigned_at": datetime.now().isoformat()
                },
                metadata={
                    "type": "mission_assignment",
                    "character": character_id,
                    "template": mission_template_id
                }
            )
        
        logger.info(f"Assigned mission {mission_id} to character {character_id}")
        return mission_id
    
    @handle_errors(operation="complete_mission", component="character_manager")
    async def complete_mission(
        self,
        character_id: str,
        mission_id: str,
        success: bool,
        results: Dict[str, Any] = None,
        session_id: str = None
    ) -> bool:
        """Complete character mission"""
        if character_id not in self.states:
            raise ValidationError(f"Character not found: {character_id}")
        
        char_state = self.states[character_id]
        
        if char_state.current_mission != mission_id:
            logger.warning(f"Mission mismatch for character {character_id}: {char_state.current_mission} != {mission_id}")
        
        # Update performance metrics
        performance_update = {
            "last_mission_success": success,
            "last_mission_completion": datetime.now().isoformat(),
            "mission_count": char_state.performance_metrics.get("mission_count", 0) + 1
        }
        
        if success:
            performance_update["success_count"] = char_state.performance_metrics.get("success_count", 0) + 1
        else:
            performance_update["failure_count"] = char_state.performance_metrics.get("failure_count", 0) + 1
        
        # Update state
        await self.update_character_state(
            character_id=character_id,
            state=CharacterOperationalState.IDLE,
            current_mission=None,
            remove_session=session_id,
            performance_metrics=performance_update
        )
        
        logger.info(f"Completed mission {mission_id} for character {character_id} (success: {success})")
        return True
    
    @handle_errors(operation="get_available_characters", component="character_manager")
    async def get_available_characters(
        self,
        mission_type: MissionType = None,
        system_assignment: str = None,
        required_capabilities: List[str] = None
    ) -> List[CharacterProfile]:
        """Get available characters matching criteria"""
        available = []
        
        for character_id, profile in self.profiles.items():
            state = self.states.get(character_id)
            
            # Check availability
            if not state or state.current_state not in [CharacterOperationalState.IDLE]:
                continue
            
            # Check mission type
            if mission_type and profile.mission_type != mission_type:
                continue
            
            # Check system assignment
            if system_assignment and profile.system_assignment not in [system_assignment, "both"]:
                continue
            
            # Check capabilities
            if required_capabilities:
                missing = set(required_capabilities) - set(profile.capabilities)
                if missing:
                    continue
            
            available.append(profile)
        
        return available
    
    async def _load_default_profiles(self):
        """Load default character profiles"""
        # Default profiles based on existing system
        default_profiles = [
            {
                "id": "dr_house_trader",
                "name": "Dr. House Trading Assistant",
                "template_name": "dr._house_doctor_template",
                "mission_type": MissionType.TRADING,
                "system_assignment": "s2",
                "capabilities": ["trading", "market_analysis", "risk_assessment", "financial_planning"],
                "preferences": {"conservative_risk": True, "detailed_analysis": True},
                "constraints": {"max_position_size": 10000, "risk_limit": 0.02}
            },
            {
                "id": "emma_educator",
                "name": "Emma Teaching Assistant",
                "template_name": "emma_teacher_template",
                "mission_type": MissionType.EDUCATION,
                "system_assignment": "both",
                "capabilities": ["teaching", "curriculum_design", "assessment", "research"],
                "preferences": {"interactive_learning": True, "adaptive_content": True},
                "constraints": {"age_appropriate": True, "educational_standards": True}
            },
            {
                "id": "weatherman_streamer",
                "name": "Weatherman Streaming Host",
                "template_name": "weatherman_template",
                "mission_type": MissionType.STREAMING,
                "system_assignment": "both",
                "capabilities": ["content_creation", "audience_engagement", "trend_analysis", "social_media"],
                "preferences": {"entertaining_style": True, "current_topics": True},
                "constraints": {"content_rating": "general", "time_limit": 3600}
            }
        ]
        
        for profile_data in default_profiles:
            try:
                await self.register_character(**profile_data)
            except ValidationError:
                # Character already exists
                pass
    
    async def _load_mission_templates(self):
        """Load mission templates"""
        templates = [
            {
                "id": "market_analysis",
                "name": "Market Analysis Mission",
                "mission_type": MissionType.TRADING,
                "description": "Analyze market conditions and provide trading recommendations",
                "required_capabilities": ["trading", "market_analysis"],
                "default_tools": ["market_data_tool", "technical_analysis_tool"],
                "autonomy_level": "medium",
                "max_duration": timedelta(hours=2),
                "success_criteria": {"analysis_depth": "detailed", "recommendation_provided": True}
            },
            {
                "id": "educational_content",
                "name": "Educational Content Creation",
                "mission_type": MissionType.EDUCATION,
                "description": "Create educational content for specific learning objectives",
                "required_capabilities": ["teaching", "curriculum_design"],
                "default_tools": ["educational_content_tool", "assessment_tool"],
                "autonomy_level": "high",
                "max_duration": timedelta(hours=4),
                "success_criteria": {"learning_objectives_met": True, "engagement_level": "high"}
            },
            {
                "id": "stream_content",
                "name": "Streaming Content Creation",
                "mission_type": MissionType.STREAMING,
                "description": "Create engaging streaming content",
                "required_capabilities": ["content_creation", "audience_engagement"],
                "default_tools": ["streaming_tool", "social_media_tool"],
                "autonomy_level": "medium",
                "max_duration": timedelta(hours=1),
                "success_criteria": {"engagement_rate": 0.1, "content_quality": "high"}
            }
        ]
        
        for template_data in templates:
            template = MissionTemplate(**template_data)
            self.mission_templates[template.id] = template
        
        logger.info(f"Loaded {len(templates)} mission templates")
    
    async def _state_sync_loop(self):
        """Background task to sync character states"""
        while self._running:
            try:
                await self._sync_with_external_systems()
                await asyncio.sleep(30)  # Sync every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in state sync loop: {e}")
                await asyncio.sleep(10)
    
    async def _sync_with_external_systems(self):
        """Sync character states with external systems (S1, SCB, etc.)"""
        # This would integrate with existing S1 synchronization endpoints
        # For now, just clean up stale sessions
        
        now = datetime.now()
        stale_threshold = timedelta(hours=1)
        
        for character_id, state in self.states.items():
            if now - state.last_activity > stale_threshold:
                if state.current_state == CharacterState.BUSY:
                    logger.warning(f"Character {character_id} has been busy for too long, marking as idle")
                    await self.update_character_state(
                        character_id=character_id,
                        state=CharacterState.IDLE,
                        current_mission=None
                    )
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get character system statistics"""
        total_characters = len(self.profiles)
        
        state_counts = {}
        for state in CharacterOperationalState:
            state_counts[state.value] = sum(
                1 for s in self.states.values() 
                if s.current_state == state
            )
        
        mission_counts = {}
        for mission_type in MissionType:
            mission_counts[mission_type.value] = sum(
                1 for p in self.profiles.values()
                if p.mission_type == mission_type
            )
        
        return {
            "total_characters": total_characters,
            "state_distribution": state_counts,
            "mission_type_distribution": mission_counts,
            "active_sessions": sum(len(s.active_sessions) for s in self.states.values()),
            "total_missions": len(self.mission_templates)
        }


# Backward compatibility functions
async def get_character_for_mission(mission_type: str, system: str = "s2") -> Optional[str]:
    """Get available character for mission (backward compatibility)"""
    from ..di import get_container
    
    manager = get_container().get(CharacterManager)
    
    try:
        mission_enum = MissionType(mission_type)
    except ValueError:
        mission_enum = MissionType.GENERAL
    
    available = await manager.get_available_characters(
        mission_type=mission_enum,
        system_assignment=system
    )
    
    return available[0].id if available else None


async def update_character_mission_state(
    character_id: str,
    mission_id: str,
    state: str
) -> bool:
    """Update character mission state (backward compatibility)"""
    from ..di import get_container
    
    manager = get_container().get(CharacterManager)
    
    try:
        state_enum = CharacterState(state)
    except ValueError:
        state_enum = CharacterState.IDLE
    
    return await manager.update_character_state(
        character_id=character_id,
        state=state_enum,
        current_mission=mission_id if state != "idle" else None
    )