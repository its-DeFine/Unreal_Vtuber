#!/usr/bin/env python3
"""
Test the fixed admin character tool parsing
"""

import sys
import traceback

# Add the path to the autogen_agent module
sys.path.insert(0, '/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

try:
    from autogen_agent.tools.character.admin_character_tool import AdminCharacterTool
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_fixed_parsing():
    """Test the fixed admin character tool parsing"""
    
    tool = AdminCharacterTool()
    
    # Test cases that previously caused "list index out of range" errors
    test_cases = [
        # Cases that should work
        ("admin: list characters", "list_characters"),
        ("admin: create character Bob", "create_character"),
        ("admin: switch character Alice", "switch_character"),
        
        # Cases that previously failed (case sensitivity)
        ("Admin: list characters", "list_characters"),
        ("ADMIN: LIST CHARACTERS", "list_characters"),
        ("Admin: Create Character Bob", "create_character"),
        ("ADMIN: SWITCH CHARACTER ALICE", "switch_character"),
        
        # Edge cases
        ("admin:", "unknown_admin_command"),
        ("admin: ", "unknown_admin_command"),
        ("list characters", "list_characters"),
        ("create character", "unknown_admin_command"),
        ("", "not_admin_command"),
        
        # Character detail extraction test cases
        ("admin: create character Bob role: doctor", "create_character"),
        ("admin: create character Alice role:", "create_character"),
        ("admin: create character Bob personality:", "create_character"),
        ("admin: create character Charlie role: teacher personality: patient", "create_character"),
    ]
    
    print("Testing fixed admin character tool parsing:")
    print("=" * 60)
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (test_input, expected_type) in enumerate(test_cases, 1):
        print(f"\n{i:2d}. Testing: '{test_input}'")
        print(f"    Expected: {expected_type}")
        
        try:
            result = tool.parse_admin_command(test_input)
            actual_type = result.get("type", "unknown")
            
            if actual_type == expected_type:
                print(f"    ✓ PASS: Got {actual_type}")
                success_count += 1
            else:
                print(f"    ❌ FAIL: Expected {expected_type}, got {actual_type}")
                
            # Show match result for debugging
            if "match" in result:
                print(f"    Match: {result['match']}")
                
        except Exception as e:
            print(f"    ❌ EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()
    
    print(f"\n" + "=" * 60)
    print(f"Results: {success_count}/{total_count} tests passed ({success_count/total_count*100:.1f}%)")
    
    return success_count == total_count

def test_character_details_extraction():
    """Test character details extraction with edge cases"""
    
    tool = AdminCharacterTool()
    
    test_cases = [
        ("create character Bob role: doctor", "Bob", "doctor"),
        ("create character Alice role: ", "Alice", "Alice Assistant"),  # Empty role should use default
        ("create character Charlie", "Charlie", "Charlie Assistant"),  # No role should use default
        ("create character Dave role: teacher personality: patient, kind", "Dave", "teacher"),
    ]
    
    print("\n" + "=" * 60)
    print("Testing character details extraction:")
    print("=" * 60)
    
    for i, (content, char_name, expected_role) in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{content}'")
        print(f"   Character: {char_name}")
        print(f"   Expected role: {expected_role}")
        
        try:
            char_data = tool.extract_character_details(content, char_name)
            actual_role = char_data.get("role", "unknown")
            
            if actual_role == expected_role:
                print(f"   ✓ PASS: Got role '{actual_role}'")
            else:
                print(f"   ❌ FAIL: Expected '{expected_role}', got '{actual_role}'")
                
            # Show personality traits for debugging
            traits = char_data.get("personality_traits", [])
            print(f"   Personality traits: {traits}")
            
        except Exception as e:
            print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    parsing_success = test_fixed_parsing()
    test_character_details_extraction()
    
    if parsing_success:
        print("\n🎉 All critical parsing tests passed! The 'list index out of range' error should be fixed.")
    else:
        print("\n❌ Some tests failed. Please review the fixes.")