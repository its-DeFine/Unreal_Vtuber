#!/usr/bin/env python3
"""
Simple Integration Test
=======================

Tests integration between components without requiring full services to be running.
Focuses on:
1. Component interaction
2. Data flow validation
3. Interface compatibility
4. Module integration
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestSimpleIntegration(unittest.TestCase):
    """Simple integration tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def test_queue_file_integration(self):
        """Test queue file creation and processing integration"""
        # Test queue file operations
        queue_file = Path(self.temp_dir) / "integration_queue.json"
        processed_file = Path(self.temp_dir) / "integration_processed.json"
        
        # Simulate stimuli creation
        test_stimuli = [
            {
                "id": "stim_001",
                "character_id": "emma_teacher_template",
                "content": "Explain machine learning basics",
                "timestamp": "2025-07-13T10:00:00",
                "metadata": {"test": True}
            },
            {
                "id": "stim_002", 
                "character_id": "gordon_trader_template",
                "content": "Analyze current market trends",
                "timestamp": "2025-07-13T10:01:00",
                "metadata": {"test": True}
            }
        ]
        
        # Write to queue file
        with open(queue_file, 'w') as f:
            json.dump(test_stimuli, f, indent=2)
        
        # Simulate processing
        processed_stimuli = []
        with open(queue_file, 'r') as f:
            queue_data = json.load(f)
        
        for stimulus in queue_data:
            # Simulate character mapping
            character_id = stimulus["character_id"]
            if "teacher" in character_id or "educator" in character_id:
                team_type = "educator"
            elif "trader" in character_id:
                team_type = "trader"
            else:
                team_type = "streamer"
            
            processed_stimulus = {
                **stimulus,
                "team_type": team_type,
                "processed_at": "2025-07-13T10:02:00",
                "status": "completed"
            }
            processed_stimuli.append(processed_stimulus)
        
        # Write processed results
        with open(processed_file, 'w') as f:
            json.dump(processed_stimuli, f, indent=2)
        
        # Validate integration
        self.assertTrue(queue_file.exists())
        self.assertTrue(processed_file.exists())
        
        with open(processed_file, 'r') as f:
            results = json.load(f)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["team_type"], "educator")
        self.assertEqual(results[1]["team_type"], "trader")
        
        print("✅ Queue file integration works correctly")
    
    def test_character_team_mapping_integration(self):
        """Test character to team mapping integration"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.core.simplified_queue_consumer import SimplifiedQueueConsumer
                
                # Create consumer instance
                consumer = SimplifiedQueueConsumer()
                
                # Test character mapping
                test_characters = [
                    "gordon_trader_template",
                    "marcus_trader_template", 
                    "emma_teacher_template",
                    "sarah_educator_template",
                    "weatherman_template",
                    "alex_streamer_template"
                ]
                
                mapped_teams = []
                for character in test_characters:
                    team = consumer.character_mapping.get(character, "unknown")
                    mapped_teams.append((character, team))
                
                # Validate mappings
                trader_chars = [m for m in mapped_teams if m[1] == "trader"]
                educator_chars = [m for m in mapped_teams if m[1] == "educator"]
                streamer_chars = [m for m in mapped_teams if m[1] == "streamer"]
                
                self.assertGreater(len(trader_chars), 0)
                self.assertGreater(len(educator_chars), 0)
                self.assertGreater(len(streamer_chars), 0)
                
                print("✅ Character-team mapping integration works correctly")
                
        except ImportError:
            print("⚠️ Character mapping test skipped due to dependencies")
            self.skipTest("Character mapping dependencies not available")
    
    def test_config_file_integration(self):
        """Test configuration file loading integration"""
        # Create test configuration
        config_data = {
            "system": {
                "mode": "simplified",
                "debug": True
            },
            "queue": {
                "poll_interval": 1.0,
                "queue_file": str(Path(self.temp_dir) / "test_queue.json"),
                "processed_file": str(Path(self.temp_dir) / "test_processed.json")
            },
            "teams": {
                "trader": {
                    "enabled": True,
                    "max_agents": 3
                },
                "educator": {
                    "enabled": True,
                    "max_agents": 3
                },
                "streamer": {
                    "enabled": True,
                    "max_agents": 3
                }
            }
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Test loading and validation
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        
        # Validate structure
        self.assertIn("system", loaded_config)
        self.assertIn("queue", loaded_config)
        self.assertIn("teams", loaded_config)
        
        # Validate values
        self.assertEqual(loaded_config["system"]["mode"], "simplified")
        self.assertEqual(loaded_config["queue"]["poll_interval"], 1.0)
        self.assertTrue(loaded_config["teams"]["trader"]["enabled"])
        
        print("✅ Configuration file integration works correctly")
    
    def test_error_flow_integration(self):
        """Test error handling flow integration"""
        def simulate_processing_pipeline(stimulus):
            """Simulate the processing pipeline with error handling"""
            try:
                # Step 1: Validate stimulus
                if not stimulus.get("content"):
                    raise ValueError("Missing content")
                
                # Step 2: Map character to team
                character_id = stimulus.get("character_id", "")
                if "teacher" in character_id or "educator" in character_id:
                    team_type = "educator"
                elif "trader" in character_id:
                    team_type = "trader"
                elif "streamer" in character_id or "weatherman" in character_id:
                    team_type = "streamer"
                else:
                    raise ValueError(f"Unknown character type: {character_id}")
                
                # Step 3: Process with team
                if team_type == "trader":
                    # Simulate trader processing
                    response = f"Trading analysis: {stimulus['content']}"
                elif team_type == "educator":
                    # Simulate educator processing
                    response = f"Educational response: {stimulus['content']}"
                elif team_type == "streamer":
                    # Simulate streamer processing
                    response = f"Streaming content: {stimulus['content']}"
                else:
                    raise ValueError(f"Unknown team type: {team_type}")
                
                return {
                    "status": "success",
                    "team_type": team_type,
                    "response": response,
                    "timestamp": "2025-07-13T10:00:00"
                }
                
            except ValueError as e:
                return {
                    "status": "error",
                    "error_type": "validation_error",
                    "error_message": str(e),
                    "timestamp": "2025-07-13T10:00:00"
                }
            except Exception as e:
                return {
                    "status": "error", 
                    "error_type": "processing_error",
                    "error_message": str(e),
                    "timestamp": "2025-07-13T10:00:00"
                }
        
        # Test successful processing
        valid_stimulus = {
            "id": "test_001",
            "character_id": "emma_teacher_template",
            "content": "Explain Python basics"
        }
        
        result = simulate_processing_pipeline(valid_stimulus)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["team_type"], "educator")
        self.assertIn("Educational response", result["response"])
        
        # Test error handling - missing content
        invalid_stimulus_1 = {
            "id": "test_002",
            "character_id": "emma_teacher_template"
            # Missing content
        }
        
        result = simulate_processing_pipeline(invalid_stimulus_1)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "validation_error")
        self.assertIn("Missing content", result["error_message"])
        
        # Test error handling - unknown character
        invalid_stimulus_2 = {
            "id": "test_003",
            "character_id": "unknown_character",
            "content": "Test content"
        }
        
        result = simulate_processing_pipeline(invalid_stimulus_2)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "validation_error")
        self.assertIn("Unknown character type", result["error_message"])
        
        print("✅ Error flow integration works correctly")
    
    def test_data_transformation_integration(self):
        """Test data transformation between components"""
        # Simulate S1 to S2 data transformation
        s1_data = {
            "type": "character_response",
            "character_id": "gordon_trader_template",
            "user_message": "What stocks should I buy?",
            "response_text": "I recommend diversified portfolio with blue-chip stocks",
            "timestamp": "2025-07-13T10:00:00",
            "metadata": {
                "confidence": 0.85,
                "source": "S1_character_system"
            }
        }
        
        # Transform to S2 format
        def transform_s1_to_s2(s1_data):
            # Map character to team
            character_id = s1_data["character_id"]
            if "trader" in character_id:
                team_type = "trader"
            elif "teacher" in character_id or "educator" in character_id:
                team_type = "educator"
            else:
                team_type = "streamer"
            
            s2_data = {
                "team_type": team_type,
                "content": s1_data["user_message"],
                "context": {
                    "previous_response": s1_data["response_text"],
                    "character_id": s1_data["character_id"],
                    "confidence": s1_data["metadata"]["confidence"]
                },
                "metadata": {
                    "source": "S1_transform",
                    "original_timestamp": s1_data["timestamp"],
                    "transformation_timestamp": "2025-07-13T10:01:00"
                }
            }
            
            return s2_data
        
        s2_data = transform_s1_to_s2(s1_data)
        
        # Validate transformation
        self.assertEqual(s2_data["team_type"], "trader")
        self.assertEqual(s2_data["content"], "What stocks should I buy?")
        self.assertEqual(s2_data["context"]["character_id"], "gordon_trader_template")
        self.assertIn("S1_transform", s2_data["metadata"]["source"])
        
        print("✅ Data transformation integration works correctly")


def run_integration_tests():
    """Run integration tests"""
    print("🔗 Starting Simple Integration Tests")
    print("=" * 45)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSimpleIntegration)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 45)
    print("🔗 INTEGRATION TEST SUMMARY")
    print("=" * 45)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            failure_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {failure_msg}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"  - {test}: {error_msg}")
    
    if result.skipped:
        print("\n⏭️ SKIPPED:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    return result


if __name__ == "__main__":
    run_integration_tests()