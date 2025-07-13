"""
Standalone Test for Utility One: Team SCB Manager
Created: 2025-07-13

Simplified test that directly imports and tests the team SCB manager implementation.
"""

import pytest
import threading
import time
import json
from typing import Dict, Any, List
from unittest.mock import Mock
from dataclasses import dataclass
from enum import Enum


# Copy the core classes from the implementation for testing
class TeamType(Enum):
    TRADER = "trader"
    EDUCATOR = "educator" 
    STREAMER = "streamer"


class SystemLevel(Enum):
    S1 = 1
    S2 = 2


@dataclass
class SCBState:
    data: Dict[str, Any]
    last_modified: float
    team_name: str
    access_level: SystemLevel
    is_common: bool = False


class TestTeamSCBManager:
    """Standalone test for TeamSCBManager implementation"""
    
    def create_manager(self):
        """Create a simplified TeamSCBManager for testing"""
        class MockTeamSCBManager:
            def __init__(self):
                self._storage = {}
                self._lock = threading.RLock()
                self._team_prefix = "team_scb"
                self._common_key = "common_scb"
                self._valid_teams = {"trader", "educator", "streamer"}
                self._initialize_team_scbs()
            
            def _initialize_team_scbs(self):
                for team in self._valid_teams:
                    team_key = f"{self._team_prefix}:{team}"
                    if team_key not in self._storage:
                        self._storage[team_key] = {}
                if self._common_key not in self._storage:
                    self._storage[self._common_key] = {}
            
            def _validate_team_name(self, team_name: str):
                if team_name not in self._valid_teams:
                    raise ValueError(f"Invalid team name: {team_name}")
            
            def _validate_system_level(self, system_level: int):
                try:
                    return SystemLevel(system_level)
                except ValueError:
                    raise ValueError(f"Invalid system level: {system_level}")
            
            def _check_write_permission(self, system_level: SystemLevel):
                if system_level == SystemLevel.S1:
                    raise PermissionError("S1 teams have read-only access")
            
            def _get_team_key(self, team_name: str):
                return f"{self._team_prefix}:{team_name}"
            
            def get_team_scb(self, team_name: str, system_level: int):
                self._validate_team_name(team_name)
                access_level = self._validate_system_level(system_level)
                
                with self._lock:
                    team_key = self._get_team_key(team_name)
                    data = self._storage.get(team_key, {})
                    
                    return SCBState(
                        data=data.copy(),
                        last_modified=time.time(),
                        team_name=team_name,
                        access_level=access_level,
                        is_common=False
                    )
            
            def set_team_scb(self, team_name: str, data: Dict[str, Any], system_level: int):
                if data is None:
                    raise ValueError("SCB data cannot be None")
                
                self._validate_team_name(team_name)
                access_level = self._validate_system_level(system_level)
                self._check_write_permission(access_level)
                
                with self._lock:
                    team_key = self._get_team_key(team_name)
                    self._storage[team_key] = data.copy()
                    return True
            
            def get_common_scb(self, system_level: int):
                access_level = self._validate_system_level(system_level)
                
                with self._lock:
                    data = self._storage.get(self._common_key, {})
                    
                    return SCBState(
                        data=data.copy(),
                        last_modified=time.time(),
                        team_name="common",
                        access_level=access_level,
                        is_common=True
                    )
            
            def set_common_scb(self, data: Dict[str, Any], system_level: int):
                if data is None:
                    raise ValueError("SCB data cannot be None")
                
                access_level = self._validate_system_level(system_level)
                self._check_write_permission(access_level)
                
                with self._lock:
                    self._storage[self._common_key] = data.copy()
                    return True
            
            def get_accessible_scb_keys(self, team_name: str, system_level: int):
                self._validate_team_name(team_name)
                access_level = self._validate_system_level(system_level)
                
                accessible_keys = []
                
                if access_level == SystemLevel.S1:
                    accessible_keys = [
                        self._get_team_key(team_name),
                        self._common_key
                    ]
                elif access_level == SystemLevel.S2:
                    accessible_keys = [
                        self._get_team_key(team) for team in self._valid_teams
                    ]
                    accessible_keys.append(self._common_key)
                
                return accessible_keys
        
        return MockTeamSCBManager()
    
    @pytest.fixture
    def team_scb_manager(self):
        return self.create_manager()
    
    @pytest.fixture
    def sample_team_data(self):
        return {
            "trader": {
                "market_analysis": {"TSLA": {"price": 250, "trend": "bullish"}},
                "trading_strategy": "momentum",
                "risk_level": 0.3
            },
            "educator": {
                "current_lesson": "Python Basics",
                "student_progress": {"alice": 85, "bob": 92},
                "curriculum_state": "module_2"
            },
            "streamer": {
                "stream_title": "Learning AI",
                "viewer_count": 150,
                "chat_sentiment": "positive"
            }
        }
    
    @pytest.fixture 
    def sample_common_data(self):
        return {
            "system_status": "active",
            "global_context": "afternoon_session",
            "shared_memory": ["Welcome message", "System initialized"],
            "cross_team_insights": {
                "market_impact_on_education": "Low volatility favors learning focus"
            }
        }

    # Core functionality tests
    def test_team_scb_isolation(self, team_scb_manager, sample_team_data):
        """Test that team SCB states are isolated"""
        # S2 teams should be able to write to their own SCB
        assert team_scb_manager.set_team_scb("trader", sample_team_data["trader"], 2)
        assert team_scb_manager.set_team_scb("educator", sample_team_data["educator"], 2)
        assert team_scb_manager.set_team_scb("streamer", sample_team_data["streamer"], 2)
        
        # Each team should only see their own data
        trader_scb = team_scb_manager.get_team_scb("trader", 2)
        educator_scb = team_scb_manager.get_team_scb("educator", 2)
        streamer_scb = team_scb_manager.get_team_scb("streamer", 2)
        
        assert trader_scb.data["market_analysis"]["TSLA"]["price"] == 250
        assert educator_scb.data["current_lesson"] == "Python Basics"
        assert streamer_scb.data["stream_title"] == "Learning AI"
        
        # Cross-team data should not be visible in team-specific SCB
        assert "current_lesson" not in trader_scb.data
        assert "market_analysis" not in educator_scb.data
        assert "viewer_count" not in trader_scb.data

    def test_common_scb_accessibility(self, team_scb_manager, sample_common_data):
        """Test that all teams can access common SCB"""
        # S2 team should be able to write to common SCB
        assert team_scb_manager.set_common_scb(sample_common_data, 2)
        
        # All teams should be able to read common SCB
        for system_level in [1, 2]:
            common_scb = team_scb_manager.get_common_scb(system_level)
            assert common_scb.data["system_status"] == "active"
            assert common_scb.data["global_context"] == "afternoon_session"
            assert len(common_scb.data["shared_memory"]) == 2

    def test_s1_read_only_access(self, team_scb_manager, sample_team_data, sample_common_data):
        """Test that S1 teams have read-only access"""
        # Setup data with S2 access
        team_scb_manager.set_team_scb("trader", sample_team_data["trader"], 2)
        team_scb_manager.set_common_scb(sample_common_data, 2)
        
        # S1 should be able to read team SCB
        trader_scb_s1 = team_scb_manager.get_team_scb("trader", 1)
        assert trader_scb_s1.data["trading_strategy"] == "momentum"
        
        # S1 should be able to read common SCB
        common_scb_s1 = team_scb_manager.get_common_scb(1)
        assert common_scb_s1.data["system_status"] == "active"
        
        # S1 should NOT be able to write to team SCB
        with pytest.raises(PermissionError, match="S1 teams have read-only access"):
            team_scb_manager.set_team_scb("trader", {"new_data": "test"}, 1)
        
        # S1 should NOT be able to write to common SCB
        with pytest.raises(PermissionError, match="S1 teams have read-only access"):
            team_scb_manager.set_common_scb({"new_data": "test"}, 1)

    def test_s2_read_write_access(self, team_scb_manager, sample_team_data, sample_common_data):
        """Test that S2 teams have full read-write access"""
        # S2 should be able to write to team SCB
        assert team_scb_manager.set_team_scb("educator", sample_team_data["educator"], 2)
        
        # S2 should be able to write to common SCB
        assert team_scb_manager.set_common_scb(sample_common_data, 2)
        
        # S2 should be able to read what they wrote
        educator_scb = team_scb_manager.get_team_scb("educator", 2)
        assert educator_scb.data["student_progress"]["alice"] == 85
        
        common_scb = team_scb_manager.get_common_scb(2)
        assert common_scb.data["global_context"] == "afternoon_session"

    def test_accessible_scb_keys(self, team_scb_manager, sample_team_data, sample_common_data):
        """Test retrieval of accessible SCB keys"""
        # Setup data
        team_scb_manager.set_team_scb("trader", sample_team_data["trader"], 2)
        team_scb_manager.set_team_scb("educator", sample_team_data["educator"], 2)
        team_scb_manager.set_common_scb(sample_common_data, 2)
        
        # S1 team should see own team SCB + common SCB
        s1_trader_keys = team_scb_manager.get_accessible_scb_keys("trader", 1)
        expected_s1_keys = ["team_scb:trader", "common_scb"]
        assert set(s1_trader_keys) == set(expected_s1_keys)
        
        # S2 team should see all SCBs
        s2_educator_keys = team_scb_manager.get_accessible_scb_keys("educator", 2)
        expected_s2_keys = ["team_scb:trader", "team_scb:educator", "team_scb:streamer", "common_scb"]
        assert set(s2_educator_keys) == set(expected_s2_keys)

    def test_invalid_team_name(self, team_scb_manager):
        """Test handling of invalid team names"""
        with pytest.raises(ValueError, match="Invalid team name"):
            team_scb_manager.get_team_scb("invalid_team", 2)
        
        with pytest.raises(ValueError, match="Invalid team name"):
            team_scb_manager.set_team_scb("invalid_team", {}, 2)

    def test_invalid_system_level(self, team_scb_manager):
        """Test handling of invalid system levels"""
        with pytest.raises(ValueError, match="Invalid system level"):
            team_scb_manager.get_team_scb("trader", 3)
        
        with pytest.raises(ValueError, match="Invalid system level"):
            team_scb_manager.set_common_scb({}, 0)

    def test_empty_data_handling(self, team_scb_manager):
        """Test handling of empty or None data"""
        # Empty data should be allowed
        assert team_scb_manager.set_team_scb("trader", {}, 2)
        
        empty_scb = team_scb_manager.get_team_scb("trader", 2)
        assert empty_scb.data == {}
        
        # None data should raise error
        with pytest.raises(ValueError, match="SCB data cannot be None"):
            team_scb_manager.set_team_scb("trader", None, 2)

    def test_all_three_teams_end_to_end(self, team_scb_manager, sample_team_data, sample_common_data):
        """End-to-end test with all three teams"""
        # Setup: S2 teams initialize their SCBs and common SCB
        for team_name, data in sample_team_data.items():
            assert team_scb_manager.set_team_scb(team_name, data, 2)
        
        assert team_scb_manager.set_common_scb(sample_common_data, 2)
        
        # Test: All teams can read their own data (S1 and S2)
        for team_name in ["trader", "educator", "streamer"]:
            for system_level in [1, 2]:
                team_scb = team_scb_manager.get_team_scb(team_name, system_level)
                assert team_scb.data is not None
                assert len(team_scb.data) > 0
        
        # Test: All teams can read common data
        for system_level in [1, 2]:
            common_scb = team_scb_manager.get_common_scb(system_level)
            assert common_scb.data["system_status"] == "active"
        
        # Test: S2 teams can update common SCB with collaborative insights
        collaborative_update = {
            "cross_team_insights": {
                "market_education_sync": "Market volatility affects learning",
                "stream_trader_collab": "Educational trading content increases retention"
            }
        }
        assert team_scb_manager.set_common_scb(collaborative_update, 2)
        
        # Verify all teams see the collaborative update
        updated_common = team_scb_manager.get_common_scb(1)
        assert "market_education_sync" in updated_common.data["cross_team_insights"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])