"""
Unified Character State Management
=================================

Single source of truth for character state across S1/S2 systems.
"""

from .character_manager import (
    CharacterManager,
    CharacterProfile,
    CharacterState,
    MissionTemplate,
    MissionType,
    get_character_for_mission,
    update_character_mission_state
)

__all__ = [
    "CharacterManager",
    "CharacterProfile",
    "CharacterState",
    "MissionTemplate", 
    "MissionType",
    "get_character_for_mission",
    "update_character_mission_state"
]