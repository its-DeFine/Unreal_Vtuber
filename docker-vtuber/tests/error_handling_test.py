#!/usr/bin/env python3
"""
Error Handling Test Suite
=========================

Tests the error handling mechanisms to ensure:
1. Error decorators work correctly
2. Exception handling is robust
3. Error logging functions properly
4. Graceful degradation occurs
"""

import sys
import os
import unittest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestErrorHandling(unittest.TestCase):
    """Test error handling mechanisms"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.DEBUG)
    
    def tearDown(self):
        """Clean up test environment"""
        logging.getLogger().removeHandler(self.handler)
        self.handler.close()
    
    def test_error_handler_import(self):
        """Test that error handler components can be imported"""
        try:
            autogen_path = project_root / "app" / "CORE" / "autogen-agent"
            sys.path.insert(0, str(autogen_path))
            
            with patch.dict('sys.modules', {
                'autogen': MagicMock(),
                'openai': MagicMock()
            }):
                from autogen_agent.utils.error_handler import error_handler, with_error_handling
                
                # Test that decorators exist and are callable
                self.assertTrue(callable(error_handler))
                self.assertTrue(callable(with_error_handling))
                
                print("✅ Error handler imports successfully")
                
        except ImportError as e:
            print(f"⚠️ Error handler import skipped: {e}")
            self.skipTest("Error handler dependencies not available")
    
    def test_basic_exception_handling(self):
        """Test basic exception handling without decorators"""
        def safe_divide(a, b):
            try:
                return a / b
            except ZeroDivisionError as e:
                logging.error(f"Division by zero: {e}")
                return None
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                return None
        
        # Test normal operation
        result = safe_divide(10, 2)
        self.assertEqual(result, 5.0)
        
        # Test error handling
        result = safe_divide(10, 0)
        self.assertIsNone(result)
        
        # Check that error was logged
        log_content = self.log_stream.getvalue()
        self.assertIn("Division by zero", log_content)
        
        print("✅ Basic exception handling works correctly")
    
    def test_logging_functionality(self):
        """Test that logging functionality works"""
        # Test different log levels
        test_logger = logging.getLogger("test_logger")
        
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        
        log_content = self.log_stream.getvalue()
        
        # Should contain log messages
        self.assertIn("Debug message", log_content)
        self.assertIn("Info message", log_content)
        self.assertIn("Warning message", log_content)
        self.assertIn("Error message", log_content)
        
        print("✅ Logging functionality works correctly")
    
    def test_file_error_handling(self):
        """Test file operation error handling"""
        def safe_file_read(file_path):
            try:
                with open(file_path, 'r') as f:
                    return f.read()
            except FileNotFoundError as e:
                logging.error(f"File not found: {e}")
                return None
            except PermissionError as e:
                logging.error(f"Permission denied: {e}")
                return None
            except Exception as e:
                logging.error(f"File operation error: {e}")
                return None
        
        # Test with non-existent file
        result = safe_file_read("/non/existent/file.txt")
        self.assertIsNone(result)
        
        # Check that error was logged
        log_content = self.log_stream.getvalue()
        self.assertIn("File not found", log_content)
        
        # Test with existing file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        result = safe_file_read(str(test_file))
        self.assertEqual(result, "test content")
        
        print("✅ File error handling works correctly")
    
    def test_network_error_simulation(self):
        """Test network error handling simulation"""
        def mock_api_call(url, timeout=30):
            import random
            import time
            
            # Simulate network delays and errors
            time.sleep(0.01)  # Small delay
            
            if "bad_endpoint" in url:
                raise ConnectionError("Connection failed")
            elif random.random() < 0.1:  # 10% chance of timeout
                raise TimeoutError("Request timed out")
            else:
                return {"status": "success", "data": "mock_data"}
        
        def safe_api_call(url, retries=3):
            for attempt in range(retries):
                try:
                    return mock_api_call(url)
                except (ConnectionError, TimeoutError) as e:
                    logging.warning(f"API call attempt {attempt + 1} failed: {e}")
                    if attempt == retries - 1:
                        logging.error(f"API call failed after {retries} attempts")
                        return None
                except Exception as e:
                    logging.error(f"Unexpected API error: {e}")
                    return None
            return None
        
        # Test successful call
        result = safe_api_call("http://good_endpoint.com")
        self.assertIsNotNone(result)
        
        # Test failed call
        result = safe_api_call("http://bad_endpoint.com")
        self.assertIsNone(result)
        
        log_content = self.log_stream.getvalue()
        self.assertIn("Connection failed", log_content)
        
        print("✅ Network error simulation works correctly")
    
    def test_json_error_handling(self):
        """Test JSON parsing error handling"""
        def safe_json_parse(json_string):
            try:
                import json
                return json.loads(json_string)
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {e}")
                return None
            except Exception as e:
                logging.error(f"Unexpected JSON error: {e}")
                return None
        
        # Test valid JSON
        result = safe_json_parse('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})
        
        # Test invalid JSON
        result = safe_json_parse('{"invalid": json}')
        self.assertIsNone(result)
        
        log_content = self.log_stream.getvalue()
        self.assertIn("JSON decode error", log_content)
        
        print("✅ JSON error handling works correctly")
    
    def test_graceful_degradation(self):
        """Test graceful degradation when components fail"""
        class MockService:
            def __init__(self, should_fail=False):
                self.should_fail = should_fail
                self.fallback_used = False
            
            def primary_method(self):
                if self.should_fail:
                    raise RuntimeError("Primary service failed")
                return "primary_result"
            
            def fallback_method(self):
                self.fallback_used = True
                return "fallback_result"
            
            def safe_operation(self):
                try:
                    return self.primary_method()
                except Exception as e:
                    logging.warning(f"Primary method failed, using fallback: {e}")
                    return self.fallback_method()
        
        # Test normal operation
        service = MockService(should_fail=False)
        result = service.safe_operation()
        self.assertEqual(result, "primary_result")
        self.assertFalse(service.fallback_used)
        
        # Test fallback operation
        service = MockService(should_fail=True)
        result = service.safe_operation()
        self.assertEqual(result, "fallback_result")
        self.assertTrue(service.fallback_used)
        
        log_content = self.log_stream.getvalue()
        self.assertIn("using fallback", log_content)
        
        print("✅ Graceful degradation works correctly")
    
    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        class RecoverableService:
            def __init__(self):
                self.error_count = 0
                self.max_errors = 2
            
            def unreliable_operation(self):
                self.error_count += 1
                if self.error_count <= self.max_errors:
                    raise RuntimeError(f"Operation failed (attempt {self.error_count})")
                return "success_after_recovery"
            
            def operation_with_retry(self, max_retries=3):
                for attempt in range(max_retries):
                    try:
                        return self.unreliable_operation()
                    except RuntimeError as e:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            logging.error("All retry attempts failed")
                            raise
                return None
        
        service = RecoverableService()
        
        # Should succeed after retries
        result = service.operation_with_retry()
        self.assertEqual(result, "success_after_recovery")
        
        log_content = self.log_stream.getvalue()
        self.assertIn("Attempt 1 failed", log_content)
        self.assertIn("Attempt 2 failed", log_content)
        
        print("✅ Error recovery works correctly")
    
    def test_context_manager_error_handling(self):
        """Test error handling in context managers"""
        class SafeResource:
            def __init__(self, should_fail_on_exit=False):
                self.should_fail_on_exit = should_fail_on_exit
                self.entered = False
                self.exited = False
                self.cleanup_done = False
            
            def __enter__(self):
                self.entered = True
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.exited = True
                try:
                    self.cleanup()
                except Exception as e:
                    logging.error(f"Cleanup failed: {e}")
                    # Don't suppress the original exception
                    return False
                
                if self.should_fail_on_exit:
                    raise RuntimeError("Exit failed")
                return False
            
            def cleanup(self):
                self.cleanup_done = True
                if self.should_fail_on_exit:
                    raise RuntimeError("Cleanup failed")
        
        # Test normal operation
        with SafeResource() as resource:
            self.assertTrue(resource.entered)
        
        self.assertTrue(resource.exited)
        self.assertTrue(resource.cleanup_done)
        
        # Test error handling
        try:
            with SafeResource(should_fail_on_exit=True) as resource:
                pass
        except RuntimeError:
            pass  # Expected
        
        log_content = self.log_stream.getvalue()
        self.assertIn("Cleanup failed", log_content)
        
        print("✅ Context manager error handling works correctly")


def run_error_handling_tests():
    """Run error handling tests"""
    print("🚨 Starting Error Handling Tests")
    print("=" * 40)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 40)
    print("🚨 ERROR HANDLING TEST SUMMARY")
    print("=" * 40)
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
    run_error_handling_tests()