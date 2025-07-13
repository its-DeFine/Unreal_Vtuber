"""
End-to-End Tests for Both Utilities with All Three Teams
Created: 2025-07-13

Comprehensive test suite that validates both utilities working together
across all three teams (trader, educator, streamer) with both S1 and S2 systems.
"""

import pytest
import threading
import time
from typing import Dict, Any, List
from unittest.mock import Mock
from dataclasses import dataclass
from enum import Enum


class TestEndToEndAllUtilities:
    """End-to-end tests for both utilities across all teams"""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated system with both utilities"""
        # Import the mock implementations from previous tests
        from test_utility_one_standalone import TestTeamSCBManager
        from test_utility_two_character_mapping import TestS2TeamCharacterMapper
        
        scb_test = TestTeamSCBManager()
        mapper_test = TestS2TeamCharacterMapper()
        
        return {
            'scb_manager': scb_test.create_manager(),
            'character_mapper': mapper_test.character_mapper(None)
        }
    
    @pytest.fixture
    def complete_test_data(self):
        """Complete test data for all three teams"""
        return {
            'scb_data': {
                "trader": {
                    "market_analysis": {"TSLA": {"price": 250, "trend": "bullish"}},
                    "trading_strategy": "momentum",
                    "risk_level": 0.3,
                    "active_positions": ["TSLA", "AAPL"]
                },
                "educator": {
                    "current_lesson": "Python Basics",
                    "student_progress": {"alice": 85, "bob": 92, "charlie": 78},
                    "curriculum_state": "module_2",
                    "next_topics": ["functions", "loops"]
                },
                "streamer": {
                    "stream_title": "Learning AI with Python",
                    "viewer_count": 150,
                    "chat_sentiment": "positive",
                    "scheduled_content": ["coding demo", "Q&A session"]
                }
            },
            'common_scb': {
                "system_status": "active",
                "global_context": "afternoon_session", 
                "shared_memory": ["Welcome message", "System initialized"],
                "cross_team_insights": {
                    "market_impact_on_education": "Low volatility favors learning focus",
                    "educational_content_popularity": "Python tutorials trending",
                    "trading_education_synergy": "Educational trading content increases engagement"
                }
            },
            'character_mappings': {
                "trader": ["gordon_trader", "marcus_trader"],
                "educator": ["emma_teacher", "professor_smith", "diana_educator"],
                "streamer": ["alex_streamer", "mike_streamer"]
            }
        }

    # ===== INTEGRATION TESTS =====
    
    def test_complete_system_initialization(self, integrated_system, complete_test_data):
        """Test complete system initialization with both utilities"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Phase 1: Initialize character mappings for all teams
        for team_name, characters in complete_test_data['character_mappings'].items():
            mapping = character_mapper.create_team_mapping(team_name, characters)
            assert mapping.s2_team == team_name
            assert len(mapping.s1_characters) == len(characters)
            assert mapping.is_active == True
        
        # Phase 2: Initialize SCB states for all teams  
        for team_name, scb_data in complete_test_data['scb_data'].items():
            success = scb_manager.set_team_scb(team_name, scb_data, 2)  # S2 level
            assert success == True
        
        # Phase 3: Initialize common SCB
        success = scb_manager.set_common_scb(complete_test_data['common_scb'], 2)
        assert success == True
        
        # Phase 4: Verify all teams are properly initialized
        for team_name in ["trader", "educator", "streamer"]:
            # Check character mapping
            mapping = character_mapper.get_team_mapping(team_name)
            assert len(mapping.s1_characters) > 0
            assert character_mapper.is_s1_active_for_team(team_name) == True
            
            # Check SCB state
            team_scb = scb_manager.get_team_scb(team_name, 2)
            assert len(team_scb.data) > 0
            
            # Check common SCB access
            common_scb = scb_manager.get_common_scb(1)  # S1 can read
            assert common_scb.data["system_status"] == "active"

    def test_s1_s2_access_patterns_all_teams(self, integrated_system, complete_test_data):
        """Test S1/S2 access patterns across all teams"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Setup: Initialize all teams with characters and SCB data
        for team_name, characters in complete_test_data['character_mappings'].items():
            character_mapper.create_team_mapping(team_name, characters)
            scb_manager.set_team_scb(team_name, complete_test_data['scb_data'][team_name], 2)
        
        scb_manager.set_common_scb(complete_test_data['common_scb'], 2)
        
        # Test S1 access (read-only) for all teams
        for team_name in ["trader", "educator", "streamer"]:
            # S1 can read team SCB
            team_scb_s1 = scb_manager.get_team_scb(team_name, 1)
            assert len(team_scb_s1.data) > 0
            
            # S1 can read common SCB
            common_scb_s1 = scb_manager.get_common_scb(1)
            assert common_scb_s1.data["system_status"] == "active"
            
            # S1 cannot write to team SCB
            with pytest.raises(PermissionError):
                scb_manager.set_team_scb(team_name, {"test": "data"}, 1)
        
        # Test S2 access (read-write) for all teams
        for team_name in ["trader", "educator", "streamer"]:
            # S2 can read and write team SCB
            original_data = scb_manager.get_team_scb(team_name, 2).data
            new_data = original_data.copy()
            new_data["s2_update"] = f"Updated by {team_name} S2"
            
            success = scb_manager.set_team_scb(team_name, new_data, 2)
            assert success == True
            
            # Verify update
            updated_scb = scb_manager.get_team_scb(team_name, 2)
            assert updated_scb.data["s2_update"] == f"Updated by {team_name} S2"

    def test_cross_team_collaboration(self, integrated_system, complete_test_data):
        """Test cross-team collaboration using both utilities"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Setup all teams
        for team_name, characters in complete_test_data['character_mappings'].items():
            character_mapper.create_team_mapping(team_name, characters)
            scb_manager.set_team_scb(team_name, complete_test_data['scb_data'][team_name], 2)
        
        scb_manager.set_common_scb(complete_test_data['common_scb'], 2)
        
        # Scenario: Trader team shares market insights via common SCB
        trader_insights = {
            "market_update": "Tech stocks showing strong momentum",
            "recommended_focus": "Educational content on trading fundamentals",
            "collaboration_request": "Need educator help with financial literacy content"
        }
        
        # Update common SCB with trader insights
        current_common = scb_manager.get_common_scb(2)
        updated_common = current_common.data.copy()
        updated_common["trader_insights"] = trader_insights
        scb_manager.set_common_scb(updated_common, 2)
        
        # Educator team responds via common SCB
        educator_response = {
            "content_proposal": "Financial literacy course for traders",
            "collaboration_status": "Accepted trader collaboration request",
            "shared_resources": ["trading_basics.pdf", "market_analysis_template.xlsx"]
        }
        
        current_common = scb_manager.get_common_scb(2)
        updated_common = current_common.data.copy() 
        updated_common["educator_response"] = educator_response
        scb_manager.set_common_scb(updated_common, 2)
        
        # Streamer team creates content plan based on collaboration
        streamer_plan = {
            "upcoming_streams": ["Trading Basics with Professor Smith", "Market Analysis Tutorial"],
            "collaboration_participants": ["gordon_trader", "emma_teacher"],
            "content_schedule": "Next week Tuesday and Thursday"
        }
        
        current_common = scb_manager.get_common_scb(2)
        updated_common = current_common.data.copy()
        updated_common["streamer_plan"] = streamer_plan
        scb_manager.set_common_scb(updated_common, 2)
        
        # Verify all teams can see the collaborative outcome
        final_common = scb_manager.get_common_scb(1)  # Even S1 can read
        assert "trader_insights" in final_common.data
        assert "educator_response" in final_common.data
        assert "streamer_plan" in final_common.data
        assert "Trading Basics with Professor Smith" in final_common.data["streamer_plan"]["upcoming_streams"]

    def test_mixed_character_activation_scenarios(self, integrated_system, complete_test_data):
        """Test mixed scenarios with different character activation states"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Scenario 1: Trader team with active characters
        character_mapper.create_team_mapping(
            "trader", 
            complete_test_data['character_mappings']['trader']
        )
        scb_manager.set_team_scb("trader", complete_test_data['scb_data']['trader'], 2)
        
        # Scenario 2: Educator team with empty mapping (S1 inactive)
        character_mapper.create_team_mapping("educator", [], allow_empty=True)
        scb_manager.set_team_scb("educator", complete_test_data['scb_data']['educator'], 2)
        
        # Scenario 3: Streamer team with characters but manually deactivated
        character_mapper.create_team_mapping(
            "streamer", 
            complete_test_data['character_mappings']['streamer']
        )
        character_mapper.deactivate_s1_characters("streamer")
        scb_manager.set_team_scb("streamer", complete_test_data['scb_data']['streamer'], 2)
        
        # Verify activation states
        assert character_mapper.is_s1_active_for_team("trader") == True
        assert character_mapper.is_s1_active_for_team("educator") == False
        assert character_mapper.is_s1_active_for_team("streamer") == False
        
        # All teams should still have SCB access regardless of S1 activation
        for team_name in ["trader", "educator", "streamer"]:
            team_scb = scb_manager.get_team_scb(team_name, 2)
            assert len(team_scb.data) > 0
        
        # Later: Educator adds characters and activates S1
        character_mapper.update_team_mapping(
            "educator", 
            complete_test_data['character_mappings']['educator']
        )
        character_mapper.activate_s1_characters("educator")
        
        # Verify educator now has active S1
        assert character_mapper.is_s1_active_for_team("educator") == True
        educator_mapping = character_mapper.get_team_mapping("educator")
        assert len(educator_mapping.s1_characters) == 3

    def test_system_resilience_and_error_handling(self, integrated_system, complete_test_data):
        """Test system resilience with error conditions"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Setup valid state first
        for team_name, characters in complete_test_data['character_mappings'].items():
            character_mapper.create_team_mapping(team_name, characters)
            scb_manager.set_team_scb(team_name, complete_test_data['scb_data'][team_name], 2)
        
        # Test error scenarios don't break existing functionality
        
        # Invalid team operations should fail but not affect other teams
        with pytest.raises(ValueError):
            character_mapper.create_team_mapping("invalid_team", ["gordon_trader"])
        
        with pytest.raises(ValueError):
            scb_manager.get_team_scb("invalid_team", 2)
        
        # Invalid character operations should fail but not affect valid mappings
        with pytest.raises(ValueError):
            character_mapper.create_team_mapping("trader", ["invalid_character"])
        
        # Permission errors should not affect read operations
        with pytest.raises(PermissionError):
            scb_manager.set_team_scb("trader", {"test": "data"}, 1)
        
        # Verify all valid operations still work after errors
        for team_name in ["trader", "educator", "streamer"]:
            # Character mapping still works
            mapping = character_mapper.get_team_mapping(team_name)
            assert mapping.s2_team == team_name
            
            # SCB operations still work
            team_scb = scb_manager.get_team_scb(team_name, 1)  # S1 read
            assert len(team_scb.data) > 0
            
            # S2 write still works
            test_data = {"resilience_test": f"Team {team_name} operational"}
            success = scb_manager.set_team_scb(team_name, test_data, 2)
            assert success == True

    def test_performance_with_all_teams(self, integrated_system, complete_test_data):
        """Test performance with all teams operating concurrently"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        import threading
        
        results = []
        errors = []
        
        def team_operations(team_name: str, iteration: int):
            try:
                # Character mapping operations
                characters = complete_test_data['character_mappings'][team_name]
                mapping = character_mapper.create_team_mapping(f"{team_name}_{iteration}", characters)
                
                # SCB operations
                scb_data = complete_test_data['scb_data'][team_name].copy()
                scb_data['iteration'] = iteration
                success = scb_manager.set_team_scb(f"{team_name}_{iteration}", scb_data, 2)
                
                # Read operations
                retrieved_scb = scb_manager.get_team_scb(f"{team_name}_{iteration}", 1)
                
                results.append((team_name, iteration, len(retrieved_scb.data)))
                
            except Exception as e:
                errors.append((team_name, iteration, str(e)))
        
        # Create multiple threads for concurrent team operations
        threads = []
        for iteration in range(3):
            for team_name in ["trader", "educator", "streamer"]:
                thread = threading.Thread(target=team_operations, args=(team_name, iteration))
                threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        end_time = time.time()
        
        # Verify performance and correctness
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"
        assert len(results) == 9, "Not all operations completed successfully"  # 3 teams * 3 iterations
        assert end_time - start_time < 2.0, "Operations took too long"  # Should complete within 2 seconds

    def test_complete_workflow_all_teams(self, integrated_system, complete_test_data):
        """Test complete workflow from initialization to complex operations"""
        scb_manager = integrated_system['scb_manager']
        character_mapper = integrated_system['character_mapper']
        
        # Phase 1: System Initialization
        print("Phase 1: Initializing all teams...")
        
        for team_name, characters in complete_test_data['character_mappings'].items():
            # Create character mapping
            mapping = character_mapper.create_team_mapping(team_name, characters)
            assert mapping.is_active == True
            
            # Initialize team SCB
            scb_manager.set_team_scb(team_name, complete_test_data['scb_data'][team_name], 2)
        
        # Initialize common SCB
        scb_manager.set_common_scb(complete_test_data['common_scb'], 2)
        
        # Phase 2: S1 Operations (Read-only)
        print("Phase 2: Testing S1 operations...")
        
        for team_name in ["trader", "educator", "streamer"]:
            # S1 can read team and common SCB
            team_scb = scb_manager.get_team_scb(team_name, 1)
            common_scb = scb_manager.get_common_scb(1)
            
            assert len(team_scb.data) > 0
            assert common_scb.data["system_status"] == "active"
        
        # Phase 3: S2 Operations (Read-write)
        print("Phase 3: Testing S2 operations...")
        
        for team_name in ["trader", "educator", "streamer"]:
            # S2 can read and modify SCB
            current_data = scb_manager.get_team_scb(team_name, 2).data.copy()
            current_data["phase_3_update"] = f"Updated by {team_name} in phase 3"
            
            success = scb_manager.set_team_scb(team_name, current_data, 2)
            assert success == True
        
        # Phase 4: Character Management Operations
        print("Phase 4: Testing character management...")
        
        # Temporarily deactivate educator S1
        character_mapper.deactivate_s1_characters("educator")
        assert character_mapper.is_s1_active_for_team("educator") == False
        
        # Add more characters to streamer team
        current_mapping = character_mapper.get_team_mapping("streamer")
        updated_characters = current_mapping.s1_characters + ["dr_house"]
        character_mapper.update_team_mapping("streamer", updated_characters)
        
        updated_mapping = character_mapper.get_team_mapping("streamer")
        assert len(updated_mapping.s1_characters) == 3
        
        # Reactivate educator S1
        character_mapper.activate_s1_characters("educator")
        assert character_mapper.is_s1_active_for_team("educator") == True
        
        # Phase 5: Final Verification
        print("Phase 5: Final verification...")
        
        # Verify all teams are operational
        active_teams = character_mapper.get_active_teams()
        assert len(active_teams) == 3
        assert set(active_teams) == {"trader", "educator", "streamer"}
        
        # Verify SCB states are consistent
        for team_name in ["trader", "educator", "streamer"]:
            team_scb = scb_manager.get_team_scb(team_name, 2)
            assert "phase_3_update" in team_scb.data
        
        # Verify common SCB accessible to all
        common_scb = scb_manager.get_common_scb(1)
        assert len(common_scb.data["cross_team_insights"]) >= 3
        
        print("Complete workflow test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])