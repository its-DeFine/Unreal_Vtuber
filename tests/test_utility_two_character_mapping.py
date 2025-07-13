"""
Test-Driven Development Tests for Utility Two: S2 Team with S1 Character Mapping
Created: 2025-07-13

This test suite validates that every S2 team has accompanying S1 character mapping,
with the option to specify no mapped characters (which keeps S1 inactive).
"""

import pytest
import threading
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock
from dataclasses import dataclass
from enum import Enum


class TestS2TeamCharacterMapper:
    """Comprehensive test suite for S2 Team Character Mapping utility"""
    
    @pytest.fixture
    def character_mapper(self):
        """Create S2TeamCharacterMapper for testing"""
        class MockS2TeamCharacterMapper:
            def __init__(self):
                self._mappings = {}
                self._lock = threading.RLock()
                self._valid_s2_teams = {"trader", "educator", "streamer"}
                self._available_s1_characters = {
                    "gordon_trader", "marcus_trader", "emma_teacher", 
                    "professor_smith", "alex_streamer", "mike_streamer",
                    "dr_house", "diana_educator", "sarah_educator"
                }
                self._s1_activation_status = {}
            
            @dataclass
            class TeamMapping:
                s2_team: str
                s1_characters: List[str]
                allow_empty: bool
                is_active: bool
                created_at: float
                last_modified: float
            
            def _validate_s2_team(self, s2_team: str):
                if s2_team not in self._valid_s2_teams:
                    raise ValueError(f"Invalid S2 team: {s2_team}")
            
            def _validate_s1_characters(self, s1_characters: List[str]):
                for char in s1_characters:
                    if char not in self._available_s1_characters:
                        raise ValueError(f"Invalid S1 character: {char}")
            
            def create_team_mapping(self, s2_team: str, s1_characters: List[str], allow_empty: bool = False):
                self._validate_s2_team(s2_team)
                
                # If characters provided, validate them
                if s1_characters:
                    self._validate_s1_characters(s1_characters)
                
                # If no characters and not allowing empty, raise error
                if not s1_characters and not allow_empty:
                    raise ValueError("S2 team must have S1 character mapping unless allow_empty=True")
                
                with self._lock:
                    current_time = time.time()
                    mapping = self.TeamMapping(
                        s2_team=s2_team,
                        s1_characters=s1_characters.copy(),
                        allow_empty=allow_empty,
                        is_active=len(s1_characters) > 0,  # Active only if characters exist
                        created_at=current_time,
                        last_modified=current_time
                    )
                    
                    self._mappings[s2_team] = mapping
                    self._s1_activation_status[s2_team] = mapping.is_active
                    
                    return mapping
            
            def get_team_mapping(self, s2_team: str):
                self._validate_s2_team(s2_team)
                with self._lock:
                    if s2_team not in self._mappings:
                        raise ValueError(f"No mapping found for S2 team: {s2_team}")
                    return self._mappings[s2_team]
            
            def activate_s1_characters(self, s2_team: str):
                mapping = self.get_team_mapping(s2_team)
                if not mapping.s1_characters:
                    raise ValueError("Cannot activate S1: no characters mapped")
                
                with self._lock:
                    self._s1_activation_status[s2_team] = True
                    mapping.is_active = True
                    mapping.last_modified = time.time()
                    return True
            
            def deactivate_s1_characters(self, s2_team: str):
                mapping = self.get_team_mapping(s2_team)
                
                with self._lock:
                    self._s1_activation_status[s2_team] = False
                    mapping.is_active = False
                    mapping.last_modified = time.time()
                    return True
            
            def is_s1_active_for_team(self, s2_team: str):
                return self._s1_activation_status.get(s2_team, False)
            
            def update_team_mapping(self, s2_team: str, s1_characters: List[str]):
                mapping = self.get_team_mapping(s2_team)
                self._validate_s1_characters(s1_characters)
                
                with self._lock:
                    mapping.s1_characters = s1_characters.copy()
                    mapping.last_modified = time.time()
                    
                    # If characters added and mapping allows activation
                    if s1_characters and not mapping.is_active:
                        mapping.is_active = True
                        self._s1_activation_status[s2_team] = True
                    
                    return mapping
            
            def get_all_mappings(self):
                with self._lock:
                    return self._mappings.copy()
            
            def remove_team_mapping(self, s2_team: str):
                mapping = self.get_team_mapping(s2_team)
                
                with self._lock:
                    # Deactivate before removing
                    self._s1_activation_status[s2_team] = False
                    del self._mappings[s2_team]
                    del self._s1_activation_status[s2_team]
                    return True
        
        return MockS2TeamCharacterMapper()
    
    @pytest.fixture
    def sample_character_mappings(self):
        """Sample S1 character mappings for S2 teams"""
        return {
            "trader": ["gordon_trader", "marcus_trader"],
            "educator": ["emma_teacher", "professor_smith", "diana_educator"],
            "streamer": ["alex_streamer", "mike_streamer"],
            "empty_team": []  # For testing allow_empty case
        }

    # ===== CORE FUNCTIONALITY TESTS =====
    
    def test_mandatory_character_mapping(self, character_mapper, sample_character_mappings):
        """Test that S2 teams must have character mapping"""
        # Valid mapping should succeed
        mapping = character_mapper.create_team_mapping(
            "trader", 
            sample_character_mappings["trader"]
        )
        assert mapping.s2_team == "trader"
        assert len(mapping.s1_characters) == 2
        assert "gordon_trader" in mapping.s1_characters
        assert mapping.is_active == True
        
        # Empty mapping without allow_empty should fail
        with pytest.raises(ValueError, match="S2 team must have S1 character mapping"):
            character_mapper.create_team_mapping("educator", [])
    
    def test_allow_empty_character_mapping(self, character_mapper):
        """Test S2 team with no mapped characters (allow_empty=True)"""
        # Empty mapping with allow_empty should succeed
        mapping = character_mapper.create_team_mapping(
            "streamer", 
            [], 
            allow_empty=True
        )
        assert mapping.s2_team == "streamer"
        assert len(mapping.s1_characters) == 0
        assert mapping.allow_empty == True
        assert mapping.is_active == False  # S1 inactive when no characters
        
        # S1 should be inactive for this team
        assert character_mapper.is_s1_active_for_team("streamer") == False
    
    def test_s1_activation_control(self, character_mapper, sample_character_mappings):
        """Test S1 activation and deactivation for teams"""
        # Create mapping with characters
        character_mapper.create_team_mapping(
            "educator", 
            sample_character_mappings["educator"]
        )
        
        # Should be active by default when characters exist
        assert character_mapper.is_s1_active_for_team("educator") == True
        
        # Should be able to deactivate
        assert character_mapper.deactivate_s1_characters("educator") == True
        assert character_mapper.is_s1_active_for_team("educator") == False
        
        # Should be able to reactivate
        assert character_mapper.activate_s1_characters("educator") == True
        assert character_mapper.is_s1_active_for_team("educator") == True
    
    def test_s1_activation_with_empty_mapping(self, character_mapper):
        """Test that empty mappings cannot be activated"""
        # Create empty mapping
        character_mapper.create_team_mapping("trader", [], allow_empty=True)
        
        # Should not be active
        assert character_mapper.is_s1_active_for_team("trader") == False
        
        # Should not be able to activate empty mapping
        with pytest.raises(ValueError, match="Cannot activate S1: no characters mapped"):
            character_mapper.activate_s1_characters("trader")
    
    def test_all_three_teams_mapping(self, character_mapper, sample_character_mappings):
        """Test that all three S2 teams can have character mappings"""
        # Create mappings for all teams
        for team_name, characters in sample_character_mappings.items():
            if team_name != "empty_team":
                mapping = character_mapper.create_team_mapping(team_name, characters)
                assert mapping.s2_team == team_name
                assert len(mapping.s1_characters) == len(characters)
                assert mapping.is_active == True
        
        # Verify all teams have mappings
        all_mappings = character_mapper.get_all_mappings()
        assert len(all_mappings) == 3
        assert "trader" in all_mappings
        assert "educator" in all_mappings  
        assert "streamer" in all_mappings
        
        # Verify all teams have active S1
        for team in ["trader", "educator", "streamer"]:
            assert character_mapper.is_s1_active_for_team(team) == True

    # ===== CHARACTER VALIDATION TESTS =====
    
    def test_invalid_s2_team(self, character_mapper):
        """Test handling of invalid S2 team names"""
        with pytest.raises(ValueError, match="Invalid S2 team"):
            character_mapper.create_team_mapping("invalid_team", ["gordon_trader"])
        
        with pytest.raises(ValueError, match="Invalid S2 team"):
            character_mapper.get_team_mapping("nonexistent_team")
    
    def test_invalid_s1_characters(self, character_mapper):
        """Test handling of invalid S1 character names"""
        with pytest.raises(ValueError, match="Invalid S1 character"):
            character_mapper.create_team_mapping("trader", ["invalid_character"])
        
        with pytest.raises(ValueError, match="Invalid S1 character"):
            character_mapper.create_team_mapping("educator", ["emma_teacher", "fake_character"])
    
    def test_mixed_valid_invalid_characters(self, character_mapper):
        """Test that one invalid character fails entire mapping"""
        with pytest.raises(ValueError, match="Invalid S1 character"):
            character_mapper.create_team_mapping(
                "trader", 
                ["gordon_trader", "invalid_character", "marcus_trader"]
            )

    # ===== MAPPING MANAGEMENT TESTS =====
    
    def test_update_team_mapping(self, character_mapper, sample_character_mappings):
        """Test updating existing team mappings"""
        # Create initial mapping
        character_mapper.create_team_mapping(
            "trader", 
            ["gordon_trader"]
        )
        
        # Update with more characters
        updated_mapping = character_mapper.update_team_mapping(
            "trader",
            sample_character_mappings["trader"]
        )
        
        assert len(updated_mapping.s1_characters) == 2
        assert "marcus_trader" in updated_mapping.s1_characters
        assert updated_mapping.last_modified > updated_mapping.created_at
    
    def test_get_nonexistent_mapping(self, character_mapper):
        """Test retrieving mapping that doesn't exist"""
        with pytest.raises(ValueError, match="No mapping found for S2 team"):
            character_mapper.get_team_mapping("trader")
    
    def test_remove_team_mapping(self, character_mapper, sample_character_mappings):
        """Test removing team mappings"""
        # Create mapping
        character_mapper.create_team_mapping(
            "educator",
            sample_character_mappings["educator"] 
        )
        
        # Verify it exists and is active
        assert character_mapper.is_s1_active_for_team("educator") == True
        
        # Remove mapping
        assert character_mapper.remove_team_mapping("educator") == True
        
        # Verify it's gone and deactivated
        with pytest.raises(ValueError, match="No mapping found"):
            character_mapper.get_team_mapping("educator")
        
        assert character_mapper.is_s1_active_for_team("educator") == False

    # ===== INTEGRATION TESTS =====
    
    def test_mixed_team_scenarios(self, character_mapper, sample_character_mappings):
        """Test mixed scenarios: some teams with characters, some empty"""
        # Trader team with characters (active S1)
        character_mapper.create_team_mapping(
            "trader",
            sample_character_mappings["trader"]
        )
        
        # Educator team with empty mapping (inactive S1)
        character_mapper.create_team_mapping(
            "educator",
            [],
            allow_empty=True
        )
        
        # Streamer team with characters but manually deactivated
        character_mapper.create_team_mapping(
            "streamer",
            sample_character_mappings["streamer"]
        )
        character_mapper.deactivate_s1_characters("streamer")
        
        # Verify final states
        assert character_mapper.is_s1_active_for_team("trader") == True
        assert character_mapper.is_s1_active_for_team("educator") == False
        assert character_mapper.is_s1_active_for_team("streamer") == False
        
        # Verify mappings exist
        trader_mapping = character_mapper.get_team_mapping("trader")
        educator_mapping = character_mapper.get_team_mapping("educator")
        streamer_mapping = character_mapper.get_team_mapping("streamer")
        
        assert len(trader_mapping.s1_characters) == 2
        assert len(educator_mapping.s1_characters) == 0
        assert len(streamer_mapping.s1_characters) == 2

    def test_character_reuse_across_teams(self, character_mapper):
        """Test that characters can be reused across different teams"""
        # Both teams can use the same character
        character_mapper.create_team_mapping("trader", ["gordon_trader"])
        character_mapper.create_team_mapping("educator", ["gordon_trader"])
        
        trader_mapping = character_mapper.get_team_mapping("trader")
        educator_mapping = character_mapper.get_team_mapping("educator")
        
        assert "gordon_trader" in trader_mapping.s1_characters
        assert "gordon_trader" in educator_mapping.s1_characters
        
        # Both should be active
        assert character_mapper.is_s1_active_for_team("trader") == True
        assert character_mapper.is_s1_active_for_team("educator") == True

    def test_team_initialization_workflow(self, character_mapper, sample_character_mappings):
        """Test complete team initialization workflow"""
        # Step 1: Initialize trader team with characters (S1 active)
        trader_mapping = character_mapper.create_team_mapping(
            "trader",
            sample_character_mappings["trader"]
        )
        assert trader_mapping.is_active == True
        
        # Step 2: Initialize educator team with no characters (S1 inactive)
        educator_mapping = character_mapper.create_team_mapping(
            "educator",
            [],
            allow_empty=True
        )
        assert educator_mapping.is_active == False
        
        # Step 3: Later add characters to educator and activate
        character_mapper.update_team_mapping(
            "educator",
            sample_character_mappings["educator"]
        )
        character_mapper.activate_s1_characters("educator")
        assert character_mapper.is_s1_active_for_team("educator") == True
        
        # Step 4: Verify final state
        all_mappings = character_mapper.get_all_mappings()
        assert len(all_mappings) == 2
        
        for team in ["trader", "educator"]:
            assert character_mapper.is_s1_active_for_team(team) == True
            mapping = character_mapper.get_team_mapping(team)
            assert len(mapping.s1_characters) > 0

    # ===== PERFORMANCE AND CONCURRENCY TESTS =====
    
    def test_concurrent_mapping_operations(self, character_mapper, sample_character_mappings):
        """Test thread-safe concurrent mapping operations"""
        import threading
        
        results = []
        errors = []
        
        def create_mapping(team_name: str, characters: List[str]):
            try:
                mapping = character_mapper.create_team_mapping(team_name, characters)
                results.append((team_name, len(mapping.s1_characters)))
            except Exception as e:
                errors.append((team_name, str(e)))
        
        def toggle_activation(team_name: str):
            try:
                # Wait a bit for mapping to be created
                time.sleep(0.01)
                if character_mapper.is_s1_active_for_team(team_name):
                    character_mapper.deactivate_s1_characters(team_name)
                    character_mapper.activate_s1_characters(team_name)
                results.append((f"{team_name}_toggle", "success"))
            except Exception as e:
                errors.append((f"{team_name}_toggle", str(e)))
        
        # Create threads for concurrent operations
        threads = []
        for team, characters in sample_character_mappings.items():
            if team != "empty_team":
                create_thread = threading.Thread(target=create_mapping, args=(team, characters))
                toggle_thread = threading.Thread(target=toggle_activation, args=(team,))
                threads.extend([create_thread, toggle_thread])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=2.0)
        
        # Verify no critical errors
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"
        assert len(results) >= 3, "Not enough operations completed successfully"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])