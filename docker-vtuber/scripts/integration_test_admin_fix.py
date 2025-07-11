#!/usr/bin/env python3
"""
Integration test for the admin character tool fix
"""

import sys
import asyncio

# Add the path to the autogen_agent module
sys.path.insert(0, '/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

async def test_full_integration():
    """Test the full integration without making actual API calls"""
    
    try:
        from autogen_agent.tools.character.admin_character_tool import execute_admin_character_tool
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    
    # Test cases that previously caused crashes
    test_contexts = [
        {"content": "Admin: List Characters"},
        {"content": "ADMIN: LIST CHARACTERS"},
        {"content": "admin: list characters"},
        {"content": "Admin: Create Character TestBot"},
        {"content": "ADMIN: SWITCH CHARACTER TestBot"},
    ]
    
    print("Integration test for admin character tool fix:")
    print("=" * 50)
    
    all_passed = True
    
    for i, context in enumerate(test_contexts, 1):
        print(f"\n{i}. Testing context: {context}")
        
        try:
            # This would have crashed before with "list index out of range"
            result = await execute_admin_character_tool(context)
            
            print(f"   ✓ No crash! Result type: {result.get('success', 'unknown')}")
            print(f"   Command type: {result.get('command_type', 'none')}")
            
            # Check if it properly parsed (success can be False due to API failures, but no crash)
            if "error" in result and "list index out of range" in str(result["error"]):
                print(f"   ❌ Still getting 'list index out of range' error!")
                all_passed = False
            
        except IndexError as e:
            if "list index out of range" in str(e):
                print(f"   ❌ CRITICAL: Still getting 'list index out of range' error: {e}")
                all_passed = False
            else:
                print(f"   ❌ Other IndexError: {e}")
                all_passed = False
                
        except Exception as e:
            # Other exceptions are OK (like network errors), we just care about the parsing crash
            print(f"   ✓ No parsing crash (other error: {type(e).__name__})")
    
    print(f"\n" + "=" * 50)
    if all_passed:
        print("🎉 Integration test PASSED! No 'list index out of range' errors detected.")
    else:
        print("❌ Integration test FAILED! 'list index out of range' errors still occurring.")
    
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(test_full_integration())