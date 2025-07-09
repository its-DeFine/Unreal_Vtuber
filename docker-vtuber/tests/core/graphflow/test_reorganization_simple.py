#!/usr/bin/env python3
"""
Simple test to verify the GraphFlow stimuli system reorganization.
Only checks file structure, not runtime dependencies.
"""

import os


def test_reorganization():
    """Test that files were moved to correct locations."""
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                            '../../../app/CORE/graphflow-stimuli-system'))
    
    print("\n🔍 Verifying GraphFlow Reorganization")
    print("=" * 60)
    
    # Check that files were moved FROM root
    root_files_that_should_not_exist = [
        'PIPELINE_FLOW_ANALYSIS.md',
        'SECURITY_AUDIT_REPORT.md', 
        'VERIFICATION_REPORT.md',
        'stimuli_emulation_demo.py',
        'run_tests.py',
    ]
    
    # Check that files exist in NEW locations
    expected_new_locations = {
        'docs/reports/PIPELINE_FLOW_ANALYSIS.md': 'Pipeline analysis moved to reports',
        'docs/reports/SECURITY_AUDIT_REPORT.md': 'Security audit moved to reports',
        'docs/reports/VERIFICATION_REPORT.md': 'Verification report moved to reports',
        'docs/api/API.md': 'API docs in api folder',
        'docs/architecture/ARCHITECTURE.md': 'Architecture docs organized',
        'docs/guides/DEVELOPER_GUIDE.md': 'Developer guide organized',
        'examples/stimuli_emulation_demo.py': 'Demo moved to examples',
        'scripts/run_tests.py': 'Test runner moved to scripts',
    }
    
    # Check root directory is clean
    print("Checking root directory is clean...")
    root_clean = True
    for file in root_files_that_should_not_exist:
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            print(f"  ❌ {file} still in root (should be moved)")
            root_clean = False
        else:
            print(f"  ✅ {file} removed from root")
    
    print("\nChecking files in new locations...")
    all_moved = True
    for path, description in expected_new_locations.items():
        full_path = os.path.join(base_path, path)
        if os.path.exists(full_path):
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} - {description}")
            all_moved = False
    
    # Check documentation structure
    print("\nChecking documentation organization...")
    doc_folders = ['api', 'architecture', 'guides', 'reports']
    docs_ok = True
    for folder in doc_folders:
        folder_path = os.path.join(base_path, 'docs', folder)
        if os.path.isdir(folder_path):
            files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
            print(f"  ✅ docs/{folder}/ ({len(files)} files)")
        else:
            print(f"  ❌ docs/{folder}/ missing")
            docs_ok = False
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Root cleaned: {'✅ YES' if root_clean else '❌ NO'}")
    print(f"   Files moved: {'✅ YES' if all_moved else '❌ NO'}")
    print(f"   Docs organized: {'✅ YES' if docs_ok else '❌ NO'}")
    
    success = root_clean and all_moved and docs_ok
    print(f"   Overall: {'✅ PASS' if success else '❌ FAIL'}")
    print("=" * 60 + "\n")
    
    return success


if __name__ == "__main__":
    success = test_reorganization()
    exit(0 if success else 1)