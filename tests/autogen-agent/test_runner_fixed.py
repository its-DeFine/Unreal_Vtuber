#!/usr/bin/env python3
"""
Fixed Test Runner for Full Utility Engineering
Handles event loop issues properly
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_suite_full_utility import TestSuiteFullUtility

def run_tests():
    """Run tests with proper event loop handling"""
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create test suite
        test_suite = TestSuiteFullUtility()
        
        # Run tests
        loop.run_until_complete(test_suite.run_all_tests())
        
    finally:
        # Cleanup
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for cancellation
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
        except Exception as e:
            print(f"Warning during cleanup: {e}")
            
        finally:
            loop.close()

if __name__ == "__main__":
    run_tests()