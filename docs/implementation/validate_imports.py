#!/usr/bin/env python3
"""
Validate that V2 imports work correctly
This can be run in the container to test the import fixes
"""

import sys
import os

# Add the NeuroSync_Player path
sys.path.insert(0, '/app/NeuroBridge/NeuroSync_Player')

def test_wrapper_imports():
    """Test that wrapper exports the necessary classes"""
    print("🧪 Testing autonomous_orchestrator_wrapper imports...")
    
    try:
        from autonomous_orchestrator_wrapper import (
            ActionType, 
            Priority, 
            AutonomousOrchestratorCompat,
            create_autonomous_orchestrator
        )
        print("✅ All wrapper imports successful!")
        
        # Test enum values
        print(f"ActionType.SPEECH = {ActionType.SPEECH.value}")
        print(f"Priority.HIGH = {Priority.HIGH.value}")
        
        return True
    except ImportError as e:
        print(f"❌ Wrapper import failed: {e}")
        return False

def test_integration_imports():
    """Test that orchestrator_integration imports work"""
    print("\n🧪 Testing orchestrator_integration imports...")
    
    try:
        from orchestrator_integration import (
            OrchestrationWrapper, 
            OrchestrationConfig
        )
        print("✅ Integration imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Integration import failed: {e}")
        return False

def test_v2_imports():
    """Test that V2 orchestrator imports work"""
    print("\n🧪 Testing autonomous_orchestrator_v2 imports...")
    
    try:
        from autonomous_orchestrator_v2 import (
            create_autonomous_orchestrator_v2,
            AutonomousOrchestratorV2
        )
        print("✅ V2 imports successful!")
        return True
    except ImportError as e:
        print(f"❌ V2 import failed: {e}")
        return False

def main():
    """Run all import tests"""
    print("🔍 V2 Orchestrator Import Validation")
    print("=" * 40)
    
    all_passed = True
    
    # Test individual components
    all_passed &= test_v2_imports()
    all_passed &= test_wrapper_imports()
    all_passed &= test_integration_imports()
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All imports working correctly!")
        print("The V2 orchestrator should deploy successfully.")
    else:
        print("❌ Some imports failed!")
        print("Check the error messages above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 