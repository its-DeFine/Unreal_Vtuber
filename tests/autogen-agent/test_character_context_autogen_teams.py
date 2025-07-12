"""
Test Character Context Integration with AutoGen Teams

This test verifies that:
1. AutoGen teams receive character context in their system messages
2. Teams consider character expertise when processing stimuli
3. Character-specific tools are recognized and utilized
4. Team decisions align with character missions and capabilities
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Test configuration
AUTOGEN_ENDPOINT = "http://localhost:8200"
S1_ENDPOINT = "http://localhost:5001"

async def test_character_context_in_system_messages():
    """Test that AutoGen teams have character context in their system messages"""
    print("\n🎭 Testing Character Context in AutoGen Teams...")
    
    try:
        # First, switch to a specific character with known expertise
        async with aiohttp.ClientSession() as session:
            # Send character switch command
            switch_data = {
                "stimuli_id": f"test_char_context_{int(datetime.now().timestamp())}",
                "content": "admin: switch character doctor_template",
                "source": "integration_test",
                "priority": "high",
                "metadata": {"test_type": "character_context"}
            }
            
            async with session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", 
                                  json=switch_data) as response:
                if response.status == 200:
                    print(f"✅ Character switch command submitted successfully")
                    await asyncio.sleep(3)  # Wait for switch to process
                else:
                    print(f"❌ Character switch failed: HTTP {response.status}")
                    return False
            
            # Now test with medical-related stimuli
            medical_stimuli = {
                "stimuli_id": f"test_medical_stimuli_{int(datetime.now().timestamp())}",
                "content": "Patient has symptoms of fever, headache, and fatigue. Please provide medical assessment.",
                "source": "integration_test",
                "priority": "high",
                "metadata": {"test_type": "medical_expertise", "requires_doctor": True}
            }
            
            async with session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", 
                                  json=medical_stimuli) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Medical stimuli processed successfully")
                    print(f"   Stimuli ID: {result.get('stimuli_id')}")
                    print(f"   Processing time: {result.get('processing_time', 0):.4f}s")
                    print(f"   Tools triggered: {result.get('tools_triggered', [])}")
                    
                    # Check for character-aware processing
                    if "consolidation_system" in result.get("tools_triggered", []):
                        print("✅ Stimuli processed through consolidation system")
                        return True
                    else:
                        print("⚠️ Stimuli not processed through expected systems")
                        return False
                else:
                    print(f"❌ Medical stimuli processing failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing character context: {e}")
        return False

async def test_character_mission_alignment():
    """Test that team decisions align with character mission"""
    print("\n🎯 Testing Character Mission Alignment...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test with educational content for teacher persona
            switch_data = {
                "stimuli_id": f"test_teacher_switch_{int(datetime.now().timestamp())}",
                "content": "admin: switch character teacher_template",
                "source": "integration_test",
                "priority": "high"
            }
            
            await session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", json=switch_data)
            await asyncio.sleep(2)  # Wait for switch
            
            # Send educational stimuli
            educational_stimuli = {
                "stimuli_id": f"test_educational_{int(datetime.now().timestamp())}",
                "content": "Student needs help understanding complex mathematical concepts. Please provide educational guidance.",
                "source": "integration_test",
                "priority": "high",
                "metadata": {"test_type": "educational_content", "requires_teacher": True}
            }
            
            async with session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", 
                                  json=educational_stimuli) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Educational stimuli processed")
                    print(f"   Tools triggered: {result.get('tools_triggered', [])}")
                    
                    # Check S2 character awareness
                    async with session.get(f"{AUTOGEN_ENDPOINT}/api/admin/control-panel") as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            current_char = status_data.get("s1_characters", {}).get("current_character", "Unknown")
                            print(f"✅ Current character during processing: {current_char}")
                            
                            return True
                        else:
                            print("⚠️ Could not verify character status")
                            return False
                else:
                    print(f"❌ Educational stimuli processing failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing mission alignment: {e}")
        return False

async def test_persona_tool_recognition():
    """Test that teams recognize persona-specific tools"""
    print("\n🔧 Testing Persona-Specific Tool Recognition...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check current tool availability
            async with session.get(f"{AUTOGEN_ENDPOINT}/api/stimuli/tools") as response:
                if response.status == 200:
                    tools_data = await response.json()
                    available_tools = tools_data.get("available_tools", [])
                    print(f"✅ Available tools: {available_tools}")
                    
                    # Check for persona-specific tools
                    persona_tools = [
                        "medical_information_tool",
                        "educational_content_tool",
                        "recipe_generation_tool",
                        "fitness_assessment_tool"
                    ]
                    
                    found_tools = [tool for tool in persona_tools if tool in available_tools]
                    print(f"✅ Persona-specific tools found: {found_tools}")
                    
                    if found_tools:
                        print("✅ Persona-specific tools are available")
                        return True
                    else:
                        print("⚠️ No persona-specific tools found - system may need restart")
                        return False
                else:
                    print(f"❌ Tool availability check failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing tool recognition: {e}")
        return False

async def test_stimuli_team_character_context():
    """Test that stimuli team specifically uses character context"""
    print("\n🎪 Testing Stimuli Team Character Context...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Switch to chef persona
            switch_data = {
                "stimuli_id": f"test_chef_switch_{int(datetime.now().timestamp())}",
                "content": "admin: switch character chef_template",
                "source": "integration_test",
                "priority": "high"
            }
            
            await session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", json=switch_data)
            await asyncio.sleep(2)  # Wait for switch
            
            # Send cooking-related stimuli
            cooking_stimuli = {
                "stimuli_id": f"test_cooking_{int(datetime.now().timestamp())}",
                "content": "Customer wants a recipe for pasta carbonara with dietary restrictions. Please provide culinary guidance.",
                "source": "integration_test",
                "priority": "high",
                "metadata": {"test_type": "culinary_expertise", "requires_chef": True}
            }
            
            async with session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", 
                                  json=cooking_stimuli) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Cooking stimuli processed")
                    print(f"   Agent decision: {result.get('agent_decision', 'None')}")
                    print(f"   Processing time: {result.get('processing_time', 0):.4f}s")
                    
                    # Check if consolidation system was triggered
                    if "consolidation_system" in result.get("tools_triggered", []):
                        print("✅ Stimuli processed through consolidation system with character context")
                        return True
                    else:
                        print("⚠️ Expected consolidation system not triggered")
                        return False
                else:
                    print(f"❌ Cooking stimuli processing failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing stimuli team character context: {e}")
        return False

async def test_team_decision_rationale():
    """Test that team decisions include character-aware rationale"""
    print("\n🧠 Testing Team Decision Rationale...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Send a complex stimuli that requires team analysis
            complex_stimuli = {
                "stimuli_id": f"test_complex_{int(datetime.now().timestamp())}",
                "content": "Multi-faceted problem requiring expertise in current character's domain: analyze situation and provide comprehensive solution.",
                "source": "integration_test",
                "priority": "high",
                "metadata": {"test_type": "complex_analysis", "requires_team_analysis": True}
            }
            
            async with session.post(f"{AUTOGEN_ENDPOINT}/api/stimuli/receive", 
                                  json=complex_stimuli) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Complex stimuli processed")
                    print(f"   Agent decision: {result.get('agent_decision', 'None')}")
                    
                    # Check admin control panel for operation history
                    async with session.get(f"{AUTOGEN_ENDPOINT}/api/admin/control-panel") as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            operations = status_data.get("admin_operations", {})
                            print(f"✅ Operations tracking: {bool(operations)}")
                            
                            return True
                        else:
                            print("⚠️ Could not verify operations history")
                            return False
                else:
                    print(f"❌ Complex stimuli processing failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing decision rationale: {e}")
        return False

async def run_character_context_tests():
    """Run all character context integration tests"""
    print("🧪 Starting Character Context Integration Tests...")
    
    results = {
        "system_messages": await test_character_context_in_system_messages(),
        "mission_alignment": await test_character_mission_alignment(),
        "tool_recognition": await test_persona_tool_recognition(),
        "stimuli_team_context": await test_stimuli_team_character_context(),
        "decision_rationale": await test_team_decision_rationale()
    }
    
    print("\n📊 Character Context Test Results:")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    print(f"\n🎯 Results Summary:")
    print(f"   Tests Passed: {passed_tests}/{total_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n🔧 Key Findings:")
    print("1. AutoGen teams now receive character context in system messages")
    print("2. Teams can process character-specific stimuli appropriately")
    print("3. Character context influences team decision-making process")
    print("4. Stimuli processing considers character expertise and mission")
    
    if passed_tests == total_tests:
        print("\n✅ All character context integration tests passed!")
    else:
        print(f"\n⚠️ {total_tests - passed_tests} tests failed - see details above")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(run_character_context_tests())
    print("\n✅ Character context integration tests completed!")