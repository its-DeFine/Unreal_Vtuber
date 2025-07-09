"""
Test setup utilities for AutoGen Agent tests
"""

import sys
import os

# Add the app directory to Python path
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app/CORE'))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Add autogen-agent directory too
autogen_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app/CORE/autogen-agent'))
if autogen_dir not in sys.path:
    sys.path.insert(0, autogen_dir)

# Common test configuration
TEST_CONFIG = {
    "AUTONOMY_LEVEL": "MODIFIER",
    "DARWIN_GODEL_REQUIRE_APPROVAL": "false",
    "AGENTNET_ENABLED": "false",  # Disable for tests
}

def setup_test_environment():
    """Setup test environment variables"""
    for key, value in TEST_CONFIG.items():
        os.environ[key] = value

def get_test_data_dir():
    """Get test data directory path"""
    return os.path.join(os.path.dirname(__file__), 'test_data')

def cleanup_test_files():
    """Clean up any test files created during tests"""
    test_files = [
        'autonomy_config.json',
        'enhanced_capabilities_test_report.json'
    ]
    
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass