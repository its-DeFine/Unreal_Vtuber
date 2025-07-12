#!/usr/bin/env python3
"""
Test to verify the GraphFlow stimuli system reorganization.
Checks that all imports still work after moving files.
"""

import os
import sys
import importlib

# Add graphflow to path
graphflow_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../app/CORE/graphflow-stimuli-system'))
sys.path.insert(0, graphflow_path)


def test_imports():
    """Test that all major imports still work."""
    modules_to_test = [
        'src',
        'src.main',
        'src.api_server',
        'src.gateway.gateway_agent',
        'src.gateway.nodes.categorizer_node',
        'src.gateway.nodes.analyzer_node',
        'src.gateway.nodes.router_node',
        'src.gateway.nodes.executor_node',
        'src.integrations.system1_interface',
        'src.integrations.system2_interface',
        'src.models.stimuli',
        'src.models.decisions',
        'src.services.context_service',
        'src.utils.logging',
        'src.config.settings',
    ]
    
    print("🔍 Testing GraphFlow imports after reorganization...")
    print("=" * 60)
    
    failed = []
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {str(e)}")
            failed.append((module_name, str(e)))
    
    print("=" * 60)
    
    if failed:
        print(f"\n❌ {len(failed)} imports failed:")
        for module, error in failed:
            print(f"   - {module}: {error}")
        return False
    else:
        print(f"\n✅ All {len(modules_to_test)} imports successful!")
        return True


def test_file_structure():
    """Test that reorganized files are in correct locations."""
    print("\n🗂️  Testing file structure...")
    print("=" * 60)
    
    expected_structure = {
        'docs/api/API.md': 'API documentation',
        'docs/architecture/ARCHITECTURE.md': 'Architecture doc',
        'docs/guides/DEVELOPER_GUIDE.md': 'Developer guide',
        'docs/reports/SECURITY_AUDIT_REPORT.md': 'Security audit',
        'examples/stimuli_emulation_demo.py': 'Demo file',
        'scripts/run_tests.py': 'Test runner',
    }
    
    all_good = True
    for path, description in expected_structure.items():
        full_path = os.path.join(graphflow_path, path)
        if os.path.exists(full_path):
            print(f"✅ {path}")
        else:
            print(f"❌ {path} - {description} not found")
            all_good = False
    
    print("=" * 60)
    
    if all_good:
        print("\n✅ File structure verified!")
    else:
        print("\n❌ Some files are missing")
    
    return all_good


def main():
    """Run all tests."""
    print("\n🚀 GraphFlow Reorganization Verification")
    print("=" * 80)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test file structure
    structure_ok = test_file_structure()
    
    print("\n" + "=" * 80)
    print("📊 Summary:")
    print(f"   Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"   Overall: {'✅ PASS' if imports_ok and structure_ok else '❌ FAIL'}")
    print("=" * 80 + "\n")
    
    return 0 if imports_ok and structure_ok else 1


if __name__ == "__main__":
    exit(main())