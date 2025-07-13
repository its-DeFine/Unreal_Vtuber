"""
S2 Team Character Mapper - Utility Two Implementation
Created: 2025-07-13

Manages mapping between System 2 teams and their associated System 1 characters.
Every S2 team must have character mapping, with option for empty mapping (inactive S1).
"""

import json
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from pathlib import Path

from docker_vtuber.app.CORE.shared.character.character_manager import CharacterManager
from docker_vtuber.app.CORE.autogen_agent.autogen_agent.clients.scb_v2_client import SCBv2Client


class S2TeamType(Enum):
    """Valid S2 team types"""
    TRADER = "trader"
    EDUCATOR = "educator"
    STREAMER = "streamer"


@dataclass
class TeamMapping:
    """Represents mapping between S2 team and S1 characters"""
    s2_team: str
    s1_characters: List[str]
    allow_empty: bool
    is_active: bool
    created_at: float
    last_modified: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamMapping':
        """Create from dictionary"""
        return cls(**data)


class S2TeamCharacterMapper:
    """
    Maps S2 teams to their associated S1 characters with activation control.
    
    Features:
    - Mandatory character mapping for all S2 teams
    - Optional empty mapping (allow_empty=True) keeps S1 inactive
    - Character activation/deactivation control
    - Integration with existing CharacterManager
    - Persistent storage via SCBClient
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize S2TeamCharacterMapper"""
        self._lock = threading.RLock()
        self._scb_client = SCBv2Client()
        self._character_manager = CharacterManager()
        
        # Storage key for persistent mappings
        self._mappings_key = "s2_character_mappings"
        
        # Valid teams and characters from existing architecture
        self._valid_s2_teams = {team.value for team in S2TeamType}
        self._available_s1_characters = self._load_available_characters()
        
        # In-memory cache for performance
        self._mappings_cache: Dict[str, TeamMapping] = {}
        self._s1_activation_status: Dict[str, bool] = {}
        
        # Load existing mappings from storage
        self._load_mappings_from_storage()
    
    def _load_available_characters(self) -> Set[str]:
        """Load available S1 characters from character manager"""
        try:
            # Get character profiles from character manager
            profiles = self._character_manager.get_all_character_profiles()
            characters = set()
            
            for profile in profiles:
                # Add character ID to available set
                characters.add(profile.get('id', ''))
                
            # Add default characters if none found
            if not characters:
                characters = {
                    "gordon_trader", "marcus_trader", "emma_teacher", 
                    "professor_smith", "alex_streamer", "mike_streamer",
                    "dr_house", "diana_educator", "sarah_educator"
                }
                
            return characters
            
        except Exception:
            # Fallback to hardcoded characters
            return {
                "gordon_trader", "marcus_trader", "emma_teacher", 
                "professor_smith", "alex_streamer", "mike_streamer",
                "dr_house", "diana_educator", "sarah_educator"
            }
    
    def _load_mappings_from_storage(self) -> None:
        """Load existing mappings from persistent storage"""
        try:
            with self._lock:
                stored_data = self._scb_client.get_slice(self._mappings_key)
                if stored_data:
                    if isinstance(stored_data, str):
                        mappings_data = json.loads(stored_data)
                    else:
                        mappings_data = stored_data
                    
                    # Restore mappings from storage
                    for team_name, mapping_dict in mappings_data.get('mappings', {}).items():
                        mapping = TeamMapping.from_dict(mapping_dict)
                        self._mappings_cache[team_name] = mapping
                        self._s1_activation_status[team_name] = mapping.is_active
                        
        except Exception:
            # If loading fails, start with empty mappings
            pass
    
    def _save_mappings_to_storage(self) -> None:
        """Save current mappings to persistent storage"""
        try:
            with self._lock:
                storage_data = {
                    'mappings': {
                        team: mapping.to_dict() 
                        for team, mapping in self._mappings_cache.items()
                    },
                    'last_updated': time.time()
                }
                
                serialized_data = json.dumps(storage_data)
                self._scb_client.set_slice(self._mappings_key, serialized_data)
                
        except Exception:
            # If saving fails, continue with in-memory only
            pass
    
    def _validate_s2_team(self, s2_team: str) -> None:
        """Validate S2 team name"""
        if s2_team not in self._valid_s2_teams:
            raise ValueError(f"Invalid S2 team: {s2_team}. Valid teams: {self._valid_s2_teams}")
    
    def _validate_s1_characters(self, s1_characters: List[str]) -> None:
        """Validate S1 character names"""
        for char in s1_characters:
            if char not in self._available_s1_characters:
                raise ValueError(f"Invalid S1 character: {char}. Available: {self._available_s1_characters}")
    
    def create_team_mapping(self, s2_team: str, s1_characters: List[str], allow_empty: bool = False) -> TeamMapping:
        """
        Create mapping between S2 team and S1 characters.
        
        Args:
            s2_team: S2 team name (trader, educator, streamer)
            s1_characters: List of S1 character IDs to map to team
            allow_empty: Whether to allow empty character list (default: False)
            
        Returns:
            TeamMapping object with mapping details
            
        Raises:
            ValueError: Invalid team/characters or empty mapping without allow_empty
        """
        self._validate_s2_team(s2_team)
        
        # Validate characters if provided
        if s1_characters:
            self._validate_s1_characters(s1_characters)
        
        # Check empty mapping policy
        if not s1_characters and not allow_empty:
            raise ValueError("S2 team must have S1 character mapping unless allow_empty=True")
        
        with self._lock:
            current_time = time.time()
            mapping = TeamMapping(
                s2_team=s2_team,
                s1_characters=s1_characters.copy(),
                allow_empty=allow_empty,
                is_active=len(s1_characters) > 0,  # Active only if characters exist
                created_at=current_time,
                last_modified=current_time
            )
            
            # Store in cache and update activation status
            self._mappings_cache[s2_team] = mapping
            self._s1_activation_status[s2_team] = mapping.is_active
            
            # Persist to storage
            self._save_mappings_to_storage()
            
            return mapping
    
    def get_team_mapping(self, s2_team: str) -> TeamMapping:
        """
        Retrieve mapping for S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            TeamMapping object
            
        Raises:
            ValueError: Invalid team or no mapping found
        """
        self._validate_s2_team(s2_team)
        
        with self._lock:
            if s2_team not in self._mappings_cache:
                raise ValueError(f"No mapping found for S2 team: {s2_team}")
            return self._mappings_cache[s2_team]
    
    def activate_s1_characters(self, s2_team: str) -> bool:
        """
        Activate S1 characters for S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            True if activation successful
            
        Raises:
            ValueError: No characters mapped to team
        """
        mapping = self.get_team_mapping(s2_team)
        
        if not mapping.s1_characters:
            raise ValueError("Cannot activate S1: no characters mapped to team")
        
        with self._lock:
            self._s1_activation_status[s2_team] = True
            mapping.is_active = True
            mapping.last_modified = time.time()
            
            # Persist changes
            self._save_mappings_to_storage()
            
            return True
    
    def deactivate_s1_characters(self, s2_team: str) -> bool:
        """
        Deactivate S1 characters for S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            True if deactivation successful
        """
        mapping = self.get_team_mapping(s2_team)
        
        with self._lock:
            self._s1_activation_status[s2_team] = False
            mapping.is_active = False
            mapping.last_modified = time.time()
            
            # Persist changes
            self._save_mappings_to_storage()
            
            return True
    
    def is_s1_active_for_team(self, s2_team: str) -> bool:
        """
        Check if S1 is active for S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            True if S1 is active for team
        """
        return self._s1_activation_status.get(s2_team, False)
    
    def update_team_mapping(self, s2_team: str, s1_characters: List[str]) -> TeamMapping:
        """
        Update S1 characters for existing S2 team mapping.
        
        Args:
            s2_team: S2 team name
            s1_characters: New list of S1 character IDs
            
        Returns:
            Updated TeamMapping object
        """
        mapping = self.get_team_mapping(s2_team)
        self._validate_s1_characters(s1_characters)
        
        with self._lock:
            mapping.s1_characters = s1_characters.copy()
            mapping.last_modified = time.time()
            
            # If characters added and mapping allows activation
            if s1_characters and not mapping.is_active:
                mapping.is_active = True
                self._s1_activation_status[s2_team] = True
            
            # If characters removed, deactivate
            elif not s1_characters:
                mapping.is_active = False
                self._s1_activation_status[s2_team] = False
            
            # Persist changes
            self._save_mappings_to_storage()
            
            return mapping
    
    def get_all_mappings(self) -> Dict[str, TeamMapping]:
        """
        Get all team mappings.
        
        Returns:
            Dictionary mapping team names to TeamMapping objects
        """
        with self._lock:
            return self._mappings_cache.copy()
    
    def remove_team_mapping(self, s2_team: str) -> bool:
        """
        Remove mapping for S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            True if removal successful
        """
        mapping = self.get_team_mapping(s2_team)
        
        with self._lock:
            # Deactivate before removing
            self._s1_activation_status[s2_team] = False
            del self._mappings_cache[s2_team]
            del self._s1_activation_status[s2_team]
            
            # Persist changes
            self._save_mappings_to_storage()
            
            return True
    
    def get_s1_characters_for_team(self, s2_team: str) -> List[str]:
        """
        Get S1 characters mapped to S2 team.
        
        Args:
            s2_team: S2 team name
            
        Returns:
            List of S1 character IDs
        """
        mapping = self.get_team_mapping(s2_team)
        return mapping.s1_characters.copy()
    
    def get_active_teams(self) -> List[str]:
        """
        Get list of S2 teams with active S1 characters.
        
        Returns:
            List of S2 team names with active S1
        """
        with self._lock:
            return [
                team for team, is_active in self._s1_activation_status.items()
                if is_active
            ]
    
    def get_inactive_teams(self) -> List[str]:
        """
        Get list of S2 teams with inactive S1 characters.
        
        Returns:
            List of S2 team names with inactive S1
        """
        with self._lock:
            return [
                team for team, is_active in self._s1_activation_status.items()
                if not is_active
            ]
    
    def validate_mapping_integrity(self) -> Dict[str, List[str]]:
        """
        Validate integrity of all mappings and return any issues.
        
        Returns:
            Dictionary with validation issues by team
        """
        issues = {}
        
        with self._lock:
            for team_name, mapping in self._mappings_cache.items():
                team_issues = []
                
                # Check if team name is valid
                if team_name not in self._valid_s2_teams:
                    team_issues.append(f"Invalid team name: {team_name}")
                
                # Check character validity
                for char in mapping.s1_characters:
                    if char not in self._available_s1_characters:
                        team_issues.append(f"Invalid character: {char}")
                
                # Check activation consistency
                expected_active = len(mapping.s1_characters) > 0
                actual_active = self._s1_activation_status.get(team_name, False)
                if mapping.is_active != actual_active:
                    team_issues.append("Activation status inconsistency")
                
                if team_issues:
                    issues[team_name] = team_issues
        
        return issues
    
    def get_available_characters(self) -> Set[str]:
        """
        Get set of available S1 characters.
        
        Returns:
            Set of available S1 character IDs
        """
        return self._available_s1_characters.copy()
    
    def refresh_available_characters(self) -> None:
        """Refresh available characters from character manager"""
        self._available_s1_characters = self._load_available_characters()
    
    def get_mapping_summary(self) -> Dict[str, Any]:
        """
        Get summary of all team mappings.
        
        Returns:
            Dictionary with mapping summary statistics
        """
        with self._lock:
            total_teams = len(self._mappings_cache)
            active_teams = len(self.get_active_teams())
            inactive_teams = len(self.get_inactive_teams())
            
            character_usage = {}
            for mapping in self._mappings_cache.values():
                for char in mapping.s1_characters:
                    character_usage[char] = character_usage.get(char, 0) + 1
            
            return {
                "total_teams": total_teams,
                "active_teams": active_teams,
                "inactive_teams": inactive_teams,
                "character_usage": character_usage,
                "available_characters": len(self._available_s1_characters),
                "last_updated": max(
                    (m.last_modified for m in self._mappings_cache.values()),
                    default=0
                )
            }


# Singleton instance for application-wide use
s2_character_mapper = S2TeamCharacterMapper()


def get_s2_character_mapper() -> S2TeamCharacterMapper:
    """Get the singleton S2TeamCharacterMapper instance"""
    return s2_character_mapper