"""
Team SCB Manager - Utility One Implementation
Created: 2025-07-13

Provides team-specific and common SCB state management with proper access controls.
Each team has its own SCB state, plus access to a common SCB state.
S1 teams have read-only access, S2 teams have read-write access.
"""

import json
import threading
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from docker_vtuber.app.AVATAR.NeuroBridge.NeuroSync_Player.utils.scb.scb_store import SCBStore
from docker_vtuber.app.CORE.autogen_agent.autogen_agent.clients.scb_client import SCBClient


class TeamType(Enum):
    """Valid team types in the system"""
    TRADER = "trader"
    EDUCATOR = "educator" 
    STREAMER = "streamer"


class SystemLevel(Enum):
    """System access levels"""
    S1 = 1  # Read-only access
    S2 = 2  # Read-write access


@dataclass
class SCBState:
    """Represents SCB state data with metadata"""
    data: Dict[str, Any]
    last_modified: float
    team_name: str
    access_level: SystemLevel
    is_common: bool = False


class TeamSCBManager:
    """
    Enhanced SCB manager providing team-specific and common state management.
    
    Features:
    - Team-isolated SCB states (trader, educator, streamer)
    - Common SCB state accessible by all teams
    - S1 read-only, S2 read-write access controls
    - Thread-safe operations
    - Integration with existing SCBStore and SCBClient
    """
    
    def __init__(self):
        """Initialize TeamSCBManager with existing SCB infrastructure"""
        self._scb_store = SCBStore()
        self._scb_client = SCBClient()
        self._lock = threading.RLock()
        
        # SCB key prefixes for organization
        self._team_prefix = "team_scb"
        self._common_key = "common_scb"
        
        # Valid teams from existing architecture
        self._valid_teams = {team.value for team in TeamType}
        
        # Initialize team SCBs if they don't exist
        self._initialize_team_scbs()
    
    def _initialize_team_scbs(self) -> None:
        """Initialize empty SCB states for all teams if they don't exist"""
        with self._lock:
            for team in self._valid_teams:
                team_key = f"{self._team_prefix}:{team}"
                if not self._key_exists(team_key):
                    self._set_scb_data(team_key, {})
            
            # Initialize common SCB if it doesn't exist
            if not self._key_exists(self._common_key):
                self._set_scb_data(self._common_key, {})
    
    def _validate_team_name(self, team_name: str) -> None:
        """Validate that team name is supported"""
        if team_name not in self._valid_teams:
            raise ValueError(f"Invalid team name: {team_name}. Valid teams: {self._valid_teams}")
    
    def _validate_system_level(self, system_level: int) -> SystemLevel:
        """Validate and convert system level to enum"""
        try:
            return SystemLevel(system_level)
        except ValueError:
            raise ValueError(f"Invalid system level: {system_level}. Valid levels: 1 (S1), 2 (S2)")
    
    def _check_write_permission(self, system_level: SystemLevel) -> None:
        """Check if system level has write permission"""
        if system_level == SystemLevel.S1:
            raise PermissionError("S1 teams have read-only access to SCB")
    
    def _get_team_key(self, team_name: str) -> str:
        """Generate Redis key for team SCB"""
        return f"{self._team_prefix}:{team_name}"
    
    def _key_exists(self, key: str) -> bool:
        """Check if a key exists in SCB storage"""
        try:
            # Try SCBClient first (Redis), then fallback to SCBStore
            result = self._scb_client.get_state(key)
            return result is not None
        except Exception:
            # Fallback to checking SCBStore
            try:
                return key in self._scb_store._scb_data
            except Exception:
                return False
    
    def _get_scb_data(self, key: str) -> Dict[str, Any]:
        """Retrieve SCB data from storage"""
        try:
            # Try SCBClient first (Redis)
            result = self._scb_client.get_state(key)
            if result is not None:
                if isinstance(result, str):
                    return json.loads(result)
                return result
        except Exception:
            pass
        
        # Fallback to SCBStore
        try:
            if key in self._scb_store._scb_data:
                return self._scb_store._scb_data[key]
        except Exception:
            pass
        
        # Return empty dict if key doesn't exist
        return {}
    
    def _set_scb_data(self, key: str, data: Dict[str, Any]) -> bool:
        """Store SCB data to storage"""
        try:
            # Try SCBClient first (Redis)
            serialized_data = json.dumps(data) if not isinstance(data, str) else data
            self._scb_client.set_state(key, serialized_data, ttl=86400)  # 24 hour TTL
            return True
        except Exception:
            pass
        
        # Fallback to SCBStore
        try:
            self._scb_store._scb_data[key] = data
            return True
        except Exception:
            return False
    
    def get_team_scb(self, team_name: str, system_level: int) -> SCBState:
        """
        Retrieve team-specific SCB state.
        
        Args:
            team_name: Name of the team (trader, educator, streamer)
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            SCBState object containing team's SCB data
            
        Raises:
            ValueError: Invalid team name or system level
        """
        self._validate_team_name(team_name)
        access_level = self._validate_system_level(system_level)
        
        with self._lock:
            team_key = self._get_team_key(team_name)
            data = self._get_scb_data(team_key)
            
            return SCBState(
                data=data,
                last_modified=time.time(),
                team_name=team_name,
                access_level=access_level,
                is_common=False
            )
    
    def set_team_scb(self, team_name: str, data: Dict[str, Any], system_level: int) -> bool:
        """
        Set team-specific SCB state.
        
        Args:
            team_name: Name of the team (trader, educator, streamer)
            data: SCB data to store
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: Invalid team name, system level, or None data
            PermissionError: S1 teams attempting write operation
        """
        if data is None:
            raise ValueError("SCB data cannot be None")
        
        self._validate_team_name(team_name)
        access_level = self._validate_system_level(system_level)
        self._check_write_permission(access_level)
        
        with self._lock:
            team_key = self._get_team_key(team_name)
            return self._set_scb_data(team_key, data)
    
    def get_common_scb(self, system_level: int) -> SCBState:
        """
        Retrieve common SCB state accessible by all teams.
        
        Args:
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            SCBState object containing common SCB data
            
        Raises:
            ValueError: Invalid system level
        """
        access_level = self._validate_system_level(system_level)
        
        with self._lock:
            data = self._get_scb_data(self._common_key)
            
            return SCBState(
                data=data,
                last_modified=time.time(),
                team_name="common",
                access_level=access_level,
                is_common=True
            )
    
    def set_common_scb(self, data: Dict[str, Any], system_level: int) -> bool:
        """
        Set common SCB state accessible by all teams.
        
        Args:
            data: SCB data to store
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: Invalid system level or None data
            PermissionError: S1 teams attempting write operation
        """
        if data is None:
            raise ValueError("SCB data cannot be None")
        
        access_level = self._validate_system_level(system_level)
        self._check_write_permission(access_level)
        
        with self._lock:
            return self._set_scb_data(self._common_key, data)
    
    def get_accessible_scb_keys(self, team_name: str, system_level: int) -> List[str]:
        """
        Get list of SCB keys accessible to a team at given system level.
        
        Args:
            team_name: Name of the team
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            List of accessible SCB keys
            
        Raises:
            ValueError: Invalid team name or system level
        """
        self._validate_team_name(team_name)
        access_level = self._validate_system_level(system_level)
        
        accessible_keys = []
        
        if access_level == SystemLevel.S1:
            # S1 teams can access their own team SCB and common SCB (read-only)
            accessible_keys = [
                self._get_team_key(team_name),
                self._common_key
            ]
        elif access_level == SystemLevel.S2:
            # S2 teams can access all team SCBs and common SCB (read-write)
            accessible_keys = [
                self._get_team_key(team) for team in self._valid_teams
            ]
            accessible_keys.append(self._common_key)
        
        return accessible_keys
    
    def update_team_scb(self, team_name: str, updates: Dict[str, Any], system_level: int) -> bool:
        """
        Update specific fields in team SCB without overwriting entire state.
        
        Args:
            team_name: Name of the team
            updates: Dictionary of fields to update
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            True if successful, False otherwise
        """
        current_state = self.get_team_scb(team_name, system_level)
        current_data = current_state.data.copy()
        current_data.update(updates)
        
        return self.set_team_scb(team_name, current_data, system_level)
    
    def update_common_scb(self, updates: Dict[str, Any], system_level: int) -> bool:
        """
        Update specific fields in common SCB without overwriting entire state.
        
        Args:
            updates: Dictionary of fields to update
            system_level: System access level (1=S1, 2=S2)
            
        Returns:
            True if successful, False otherwise
        """
        current_state = self.get_common_scb(system_level)
        current_data = current_state.data.copy()
        current_data.update(updates)
        
        return self.set_common_scb(current_data, system_level)
    
    def clear_team_scb(self, team_name: str, system_level: int) -> bool:
        """
        Clear all data from team-specific SCB.
        
        Args:
            team_name: Name of the team
            system_level: System access level (must be S2)
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_team_scb(team_name, {}, system_level)
    
    def get_team_scb_summary(self, team_name: str, system_level: int) -> Dict[str, Any]:
        """
        Get summary information about team SCB state.
        
        Args:
            team_name: Name of the team
            system_level: System access level
            
        Returns:
            Dictionary with summary information
        """
        scb_state = self.get_team_scb(team_name, system_level)
        
        return {
            "team_name": team_name,
            "system_level": system_level,
            "data_size": len(str(scb_state.data)),
            "key_count": len(scb_state.data),
            "last_modified": scb_state.last_modified,
            "is_empty": len(scb_state.data) == 0,
            "top_level_keys": list(scb_state.data.keys())[:10]  # First 10 keys
        }
    
    def get_all_team_summaries(self, system_level: int) -> Dict[str, Dict[str, Any]]:
        """
        Get summary information for all accessible team SCBs.
        
        Args:
            system_level: System access level
            
        Returns:
            Dictionary mapping team names to their summaries
        """
        summaries = {}
        
        if system_level == 2:  # S2 can access all teams
            for team in self._valid_teams:
                summaries[team] = self.get_team_scb_summary(team, system_level)
        
        # Always include common SCB summary
        common_state = self.get_common_scb(system_level)
        summaries["common"] = {
            "team_name": "common",
            "system_level": system_level,
            "data_size": len(str(common_state.data)),
            "key_count": len(common_state.data),
            "last_modified": common_state.last_modified,
            "is_empty": len(common_state.data) == 0,
            "top_level_keys": list(common_state.data.keys())[:10]
        }
        
        return summaries


# Singleton instance for application-wide use
team_scb_manager = TeamSCBManager()


def get_team_scb_manager() -> TeamSCBManager:
    """Get the singleton TeamSCBManager instance"""
    return team_scb_manager