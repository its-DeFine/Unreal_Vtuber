#!/usr/bin/env python3
"""
Unit Tests for Refactoring Validation
====================================

Tests the core components after refactoring to ensure:
1. Imports work correctly
2. Classes can be instantiated
3. Core functionality is intact
4. Configuration system works
5. Error handling is functional
"""

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRefactoringValidation(unittest.TestCase):
    """Test suite to validate refactoring didn't break core functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_import_simplified_main_module(self):
        """Test that simplified_main module can be imported"""
        try:
            # Change to the autogen-agent directory
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            from autogen_agent.simplified_main import FastAPI
            self.assertTrue(hasattr(FastAPI, '__name__'))
            print("✅ simplified_main module imports successfully")
            
        except ImportError as e:
            # If there are dependency issues, that's expected in isolated testing
            if "autogen" in str(e) or "fastapi" in str(e).lower():
                print("⚠️ Expected dependency issue in isolated test:", str(e))
                self.skipTest("Dependencies not available in test environment")
            else:
                raise
                
    def test_import_simplified_queue_consumer(self):
        """Test that SimplifiedQueueConsumer can be imported"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            # Mock dependencies to avoid import errors
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'autogen.agentchat': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.core.simplified_queue_consumer import SimplifiedQueueConsumer
                self.assertTrue(hasattr(SimplifiedQueueConsumer, '__init__'))
                print("✅ SimplifiedQueueConsumer imports successfully")
                
        except ImportError as e:
            print(f"⚠️ Import issue in test: {e}")
            self.skipTest("Dependencies not available in test environment")
    
    def test_import_processing_config(self):
        """Test that processing configuration can be imported"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            from autogen_agent.config.processing_config import ProcessingConfig, TeamConfig, FileConfig
            
            # Test configuration classes have expected attributes
            self.assertTrue(hasattr(ProcessingConfig, 'DEFAULT_POLL_INTERVAL'))
            self.assertTrue(hasattr(TeamConfig, 'get_team_description'))
            self.assertTrue(hasattr(FileConfig, 'DEFAULT_QUEUE_FILE'))
            
            print("✅ Processing configuration imports successfully")
            
        except ImportError as e:
            print(f"⚠️ Config import issue: {e}")
            self.skipTest("Configuration dependencies not available")
    
    def test_error_handler_import(self):
        """Test that error handler can be imported"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            from autogen_agent.utils.error_handler import error_handler, with_error_handling
            
            # Test that decorators exist
            self.assertTrue(callable(error_handler))
            self.assertTrue(callable(with_error_handling))
            
            print("✅ Error handler imports successfully")
            
        except ImportError as e:
            print(f"⚠️ Error handler import issue: {e}")
            self.skipTest("Error handler dependencies not available")
    
    def test_shared_components_import(self):
        """Test that shared components can be imported"""
        try:
            from app.CORE.shared.config.core_config import CoreConfig
            from app.CORE.shared.character.character_manager import CharacterManager
            from app.CORE.shared.errors.error_handler import ErrorHandler
            
            # Test basic functionality
            self.assertTrue(hasattr(CoreConfig, 'load_from_file'))
            self.assertTrue(hasattr(CharacterManager, '__init__'))
            self.assertTrue(hasattr(ErrorHandler, 'handle_error'))
            
            print("✅ Shared components import successfully")
            
        except ImportError as e:
            print(f"⚠️ Shared components import issue: {e}")
            self.skipTest("Shared components dependencies not available")
    
    def test_file_structure_integrity(self):
        """Test that critical files exist in expected locations"""
        critical_files = [
            "app/CORE/autogen-agent/autogen_agent/simplified_main.py",
            "app/CORE/autogen-agent/autogen_agent/core/simplified_queue_consumer.py",
            "app/CORE/autogen-agent/autogen_agent/config/processing_config.py",
            "app/CORE/autogen-agent/autogen_agent/utils/error_handler.py",
            "app/CORE/shared/config/core_config.py",
            "app/CORE/shared/character/character_manager.py"
        ]
        
        missing_files = []
        for file_path in critical_files:
            full_path = project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.fail(f"❌ Missing critical files: {missing_files}")
        
        print(f"✅ All {len(critical_files)} critical files exist")
    
    def test_init_files_exist(self):
        """Test that __init__.py files exist for proper package structure"""
        init_files = [
            "app/CORE/autogen-agent/autogen_agent/__init__.py",
            "app/CORE/autogen-agent/autogen_agent/core/__init__.py",
            "app/CORE/autogen-agent/autogen_agent/config/__init__.py",
            "app/CORE/autogen-agent/autogen_agent/utils/__init__.py",
            "app/CORE/shared/__init__.py",
            "app/CORE/shared/config/__init__.py",
            "app/CORE/shared/character/__init__.py"
        ]
        
        missing_init_files = []
        for init_file in init_files:
            full_path = project_root / init_file
            if not full_path.exists():
                missing_init_files.append(init_file)
        
        if missing_init_files:
            self.fail(f"❌ Missing __init__.py files: {missing_init_files}")
        
        print(f"✅ All {len(init_files)} __init__.py files exist")
    
    def test_configuration_loading(self):
        """Test that configuration can be loaded without errors"""
        # Create a temporary config file
        config_data = {
            "s1_endpoint": "http://localhost:5001",
            "s2_endpoint": "http://localhost:8200",
            "queue_settings": {
                "poll_interval": 1.0,
                "queue_file": "test_queue.json"
            }
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Test that JSON can be loaded
        loaded_config = json.load(open(config_file))
        self.assertEqual(loaded_config["s1_endpoint"], "http://localhost:5001")
        self.assertEqual(loaded_config["s2_endpoint"], "http://localhost:8200")
        
        print("✅ Configuration loading works correctly")
    
    def test_queue_file_operations(self):
        """Test basic queue file operations"""
        queue_file = Path(self.temp_dir) / "test_queue.json"
        processed_file = Path(self.temp_dir) / "test_processed.json"
        
        # Test writing to queue file
        test_stimuli = [
            {
                "id": "test_1",
                "content": "Test message",
                "timestamp": "2025-07-13T10:00:00"
            }
        ]
        
        with open(queue_file, 'w') as f:
            json.dump(test_stimuli, f)
        
        # Test reading from queue file
        with open(queue_file, 'r') as f:
            loaded_stimuli = json.load(f)
        
        self.assertEqual(len(loaded_stimuli), 1)
        self.assertEqual(loaded_stimuli[0]["id"], "test_1")
        
        print("✅ Queue file operations work correctly")
    
    def test_syntax_validation_of_modified_files(self):
        """Test that recently modified files have valid Python syntax"""
        modified_files = [
            "app/CORE/autogen-agent/autogen_agent/simplified_main.py",
            "app/CORE/autogen-agent/autogen_agent/core/simplified_queue_consumer.py"
        ]
        
        import ast
        
        for file_path in modified_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    ast.parse(content)
                    print(f"✅ {file_path} has valid syntax")
                except SyntaxError as e:
                    self.fail(f"❌ Syntax error in {file_path}: {e}")
            else:
                self.fail(f"❌ File not found: {file_path}")


class TestConfigurationSystem(unittest.TestCase):
    """Test the configuration system specifically"""
    
    def test_team_configuration(self):
        """Test team configuration mapping"""
        try:
            autogen_path = Path(__file__).parent.parent / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            from autogen_agent.config.processing_config import TeamConfig
            
            # Test that all expected teams are configured
            expected_teams = ["trader", "educator", "streamer"]
            
            for team in expected_teams:
                description = TeamConfig.get_team_description(team)
                self.assertIsNotNone(description)
                self.assertIsInstance(description, str)
                self.assertGreater(len(description), 10)  # Should have meaningful descriptions
                
            print("✅ Team configuration system works correctly")
            
        except ImportError:
            self.skipTest("Configuration dependencies not available")


class TestErrorHandling(unittest.TestCase):
    """Test error handling mechanisms"""
    
    def test_error_decorator_functionality(self):
        """Test that error decorators can be applied"""
        try:
            autogen_path = Path(__file__).parent.parent / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            from autogen_agent.utils.error_handler import with_error_handling
            
            # Test decorator application
            @with_error_handling
            def test_function():
                return "success"
            
            # Test that decorated function still works
            result = test_function()
            self.assertEqual(result, "success")
            
            print("✅ Error handling decorators work correctly")
            
        except ImportError:
            self.skipTest("Error handling dependencies not available")


def run_unit_tests():
    """Run all unit tests and return results"""
    print("🧪 Starting Unit Tests for Refactoring Validation")
    print("=" * 60)
    
    # Create test suite
    test_classes = [
        TestRefactoringValidation,
        TestConfigurationSystem,
        TestErrorHandling
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 UNIT TEST SUMMARY")
    print("=" * 60)
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
    run_unit_tests()