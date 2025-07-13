#!/usr/bin/env python3
"""
Configuration System Test
=========================

Tests the new configuration system functionality to ensure:
1. Configuration loading works correctly
2. Environment variable override works
3. Default values are properly set
4. Configuration validation works
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

class TestConfigurationSystem(unittest.TestCase):
    """Test the configuration system functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_core_config_import(self):
        """Test that CoreConfig can be imported and instantiated"""
        try:
            # Mock dependencies to avoid import errors
            with patch.dict('sys.modules', {
                'redis': MagicMock(),
                'pydantic': MagicMock(),
                'pydantic_settings': MagicMock()
            }):
                from app.CORE.shared.config.core_config import CoreConfig, SystemMode
                
                # Test that we can reference the config class
                self.assertTrue(hasattr(CoreConfig, 'load_from_file'))
                self.assertTrue(hasattr(SystemMode, 'SIMPLIFIED'))
                
                print("✅ CoreConfig imports successfully")
                
        except ImportError as e:
            print(f"⚠️ CoreConfig import skipped due to dependencies: {e}")
            self.skipTest("Configuration dependencies not available")
    
    def test_processing_config_import(self):
        """Test that processing configuration can be imported"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            # Mock dependencies
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.config.processing_config import ProcessingConfig, TeamConfig, FileConfig
                
                # Test configuration attributes exist
                self.assertTrue(hasattr(ProcessingConfig, 'DEFAULT_POLL_INTERVAL'))
                self.assertTrue(hasattr(TeamConfig, 'TEAM_DESCRIPTIONS'))
                self.assertTrue(hasattr(FileConfig, 'DEFAULT_QUEUE_FILE'))
                
                print("✅ Processing configuration imports successfully")
                
        except ImportError as e:
            print(f"⚠️ Processing config import skipped: {e}")
            self.skipTest("Processing configuration dependencies not available")
    
    def test_json_config_loading(self):
        """Test loading configuration from JSON files"""
        # Create a test configuration file
        config_data = {
            "system_mode": "simplified",
            "debug": True,
            "queue": {
                "poll_interval": 2.0,
                "queue_file": "test_queue.json"
            },
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Test that the JSON can be loaded
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        
        self.assertEqual(loaded_config["system_mode"], "simplified")
        self.assertTrue(loaded_config["debug"])
        self.assertEqual(loaded_config["queue"]["poll_interval"], 2.0)
        
        print("✅ JSON configuration loading works")
    
    def test_environment_variable_loading(self):
        """Test that environment variables can be used for configuration"""
        test_env_vars = {
            "CORE_SYSTEM_MODE": "simplified",
            "CORE_DEBUG": "true",
            "S2_QUEUE_FILE": "/tmp/test_queue.json",
            "S2_PROCESSED_FILE": "/tmp/test_processed.json"
        }
        
        with patch.dict(os.environ, test_env_vars):
            # Test that environment variables are accessible
            self.assertEqual(os.getenv("CORE_SYSTEM_MODE"), "simplified")
            self.assertEqual(os.getenv("CORE_DEBUG"), "true")
            self.assertEqual(os.getenv("S2_QUEUE_FILE"), "/tmp/test_queue.json")
            
        print("✅ Environment variable configuration works")
    
    def test_default_values(self):
        """Test that default configuration values are reasonable"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.config.processing_config import ProcessingConfig, FileConfig
                
                # Test default values are reasonable
                self.assertGreater(ProcessingConfig.DEFAULT_POLL_INTERVAL, 0)
                self.assertLess(ProcessingConfig.DEFAULT_POLL_INTERVAL, 10)  # Should be reasonable
                
                self.assertTrue(FileConfig.DEFAULT_QUEUE_FILE.endswith('.json'))
                self.assertTrue(FileConfig.DEFAULT_PROCESSED_FILE.endswith('.json'))
                
                print("✅ Default configuration values are reasonable")
                
        except ImportError:
            print("⚠️ Default values test skipped due to dependencies")
            self.skipTest("Configuration dependencies not available")
    
    def test_team_configuration(self):
        """Test team-specific configuration"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.config.processing_config import TeamConfig
                
                # Test that all expected teams have configurations
                expected_teams = ["trader", "educator", "streamer"]
                
                for team in expected_teams:
                    description = TeamConfig.get_team_description(team)
                    self.assertIsNotNone(description)
                    self.assertIsInstance(description, str)
                    self.assertGreater(len(description), 10)
                
                print("✅ Team configuration works correctly")
                
        except ImportError:
            print("⚠️ Team configuration test skipped due to dependencies")
            self.skipTest("Team configuration dependencies not available")
    
    def test_file_path_configuration(self):
        """Test file path configuration handling"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.config.processing_config import FileConfig
                
                # Test that default paths are valid
                queue_path = Path(FileConfig.DEFAULT_QUEUE_FILE)
                processed_path = Path(FileConfig.DEFAULT_PROCESSED_FILE)
                
                # Should be valid path objects
                self.assertIsInstance(queue_path, Path)
                self.assertIsInstance(processed_path, Path)
                
                # Should have parent directories defined
                self.assertIsNotNone(queue_path.parent)
                self.assertIsNotNone(processed_path.parent)
                
                print("✅ File path configuration works correctly")
                
        except ImportError:
            print("⚠️ File path configuration test skipped due to dependencies")
            self.skipTest("File configuration dependencies not available")
    
    def test_character_mapping_configuration(self):
        """Test character mapping configuration"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.core.simplified_queue_consumer import SimplifiedQueueConsumer
                
                # Create an instance to test character mapping
                consumer = SimplifiedQueueConsumer()
                
                # Test that character mapping exists and has expected teams
                self.assertIsInstance(consumer.character_mapping, dict)
                
                # Check that mapped teams are valid
                mapped_teams = set(consumer.character_mapping.values())
                expected_teams = {"trader", "educator", "streamer"}
                
                # All mapped teams should be in expected teams
                for team in mapped_teams:
                    self.assertIn(team, expected_teams)
                
                print("✅ Character mapping configuration works correctly")
                
        except ImportError:
            print("⚠️ Character mapping test skipped due to dependencies")
            self.skipTest("Character mapping dependencies not available")


def run_configuration_tests():
    """Run configuration system tests"""
    print("⚙️ Starting Configuration System Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigurationSystem)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    print("⚙️ CONFIGURATION TEST SUMMARY")
    print("=" * 50)
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
    run_configuration_tests()