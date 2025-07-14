#!/usr/bin/env python3
"""
Test Visual Identity Switching
Tests that characters switch appearance when persona changes
Created: 2025-07-14
"""
import httpx
import asyncio
import json
import time
from typing import Dict, Any

# Configuration
ORCHESTRATOR_URL = "http://localhost:8082"
S1_URL = "http://localhost:5001"
S2_URL = "http://localhost:8001"


async def test_visual_identity_switching():
    """Test that visual identity changes when character switches"""
    print("🎨 Testing Visual Identity Switching\n")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # Test personas in sequence
        test_cases = [
            {
                "persona": "trader",
                "message": "Let's analyze the Bitcoin price movements today",
                "expected_character": "sophia_trader_template",
                "expected_visual": "golden_goddess"
            },
            {
                "persona": "educator", 
                "message": "Today I'll teach you about blockchain fundamentals",
                "expected_character": "diana_educator_template",
                "expected_visual": "emerald_elegance"
            },
            {
                "persona": "streamer",
                "message": "Hey chat! Let's play some games together!",
                "expected_character": "luna_streamer_template", 
                "expected_visual": "ruby_sensation"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"📍 Testing persona: {test_case['persona']}")
            print(f"💬 Message: {test_case['message']}")
            
            # Send stimulus through orchestrator with specific persona
            payload = {
                "stimulus_id": f"visual_test_{test_case['persona']}_{int(time.time())}",
                "text": test_case['message'],
                "context": {
                    "user_id": "test_visual_identity",
                    "persona": test_case['persona']
                }
            }
            
            try:
                # Send to orchestrator
                print(f"\n📤 Sending to orchestrator...")
                response = await client.post(f"{ORCHESTRATOR_URL}/route", json=payload)
                print(f"   Response: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   Result: {json.dumps(result, indent=2)}")
                    system = result.get('system', 'unknown')
                    print(f"   Routed to: {system}")
                    
                    # Only check S1 if routed there
                    if system != 's1' and system != 'both':
                        print(f"   Skipping S1 check - routed to {system}")
                        continue
                    
                    # Wait for character switch to happen
                    await asyncio.sleep(2)
                    
                    # Check current character in S1
                    try:
                        char_response = await client.get(f"{S1_URL}/character/current")
                        if char_response.status_code == 200:
                            char_data = char_response.json()
                            current_char = char_data.get('character', {})
                        
                            print(f"\n✅ Character switched to: {current_char.get('name')}")
                            print(f"   Character ID: {current_char.get('id')}")
                            
                            # Verify correct character
                            if current_char.get('id') == test_case['expected_character']:
                                print(f"   ✓ Correct character for {test_case['persona']} persona")
                            else:
                                print(f"   ✗ Wrong character! Expected: {test_case['expected_character']}")
                            
                            # Check visual identity
                            visual_identity = current_char.get('visual_identity', {})
                            if visual_identity:
                                print(f"\n🎨 Visual Identity Applied:")
                                print(f"   Preset: {visual_identity.get('preset_name')}")
                                print(f"   Commands: {visual_identity.get('tcp_commands', [])}")
                                
                                if visual_identity.get('preset_name') == test_case['expected_visual']:
                                    print(f"   ✓ Correct visual preset for {test_case['persona']}")
                                else:
                                    print(f"   ✗ Wrong preset! Expected: {test_case['expected_visual']}")
                            else:
                                print(f"   ⚠️  No visual identity defined")
                        else:
                            print(f"   ⚠️  Could not get character: {char_response.status_code}")
                            print(f"      Response: {char_response.text}")
                    except Exception as e:
                        print(f"   ❌ Error checking character: {e}")
                            
                else:
                    print(f"   ❌ Orchestrator error: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Wait between tests
            await asyncio.sleep(3)
        
        print(f"\n{'='*60}")
        print("🎨 Visual Identity Testing Complete!")


async def check_tcp_connection():
    """Check if TCP connection to Unreal is available"""
    print("\n🔌 Checking TCP Connection to Unreal Engine...")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        try:
            # Check S1 health (which includes TCP status)
            response = await client.get(f"{S1_URL}/health")
            if response.status_code == 200:
                health = response.json()
                if 'tcp_controller' in health:
                    print("   ✓ TCP controller is available")
                else:
                    print("   ⚠️  TCP controller not initialized")
            else:
                print("   ❌ Could not check health status")
        except Exception as e:
            print(f"   ❌ Error checking TCP: {e}")


async def test_direct_s1_character_switching():
    """Test character switching by sending directly to S1"""
    print("\n🎯 Testing Direct S1 Character Switching\n")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        test_cases = [
            {
                "persona": "trader",
                "message": "Quick Bitcoin update"
            },
            {
                "persona": "educator",
                "message": "Quick blockchain fact"
            },
            {
                "persona": "streamer",
                "message": "Hey everyone!"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🔄 Testing direct S1 with persona: {test_case['persona']}")
            
            # Send directly to S1 with persona in autonomous_context
            payload = {
                "text": test_case['message'],
                "autonomous_context": f"Routed by orchestrator with persona: {test_case['persona']}"
            }
            
            try:
                response = await client.post(f"{S1_URL}/process_text", json=payload)
                print(f"   Response: {response.status_code}")
                
                if response.status_code == 200:
                    # Check character immediately
                    char_response = await client.get(f"{S1_URL}/character/current")
                    if char_response.status_code == 200:
                        char_data = char_response.json()
                        current_char = char_data.get('character', {})
                        print(f"   Current character: {current_char.get('name')} ({current_char.get('id')})")
                        
                        # Check visual identity
                        visual = current_char.get('visual_identity', {})
                        if visual:
                            print(f"   Visual preset: {visual.get('preset_name')}")
                        else:
                            print(f"   No visual identity")
                    else:
                        print(f"   Could not check character: {char_response.status_code}")
                else:
                    print(f"   Error: {response.text}")
                    
            except Exception as e:
                print(f"   Error: {e}")
            
            await asyncio.sleep(1)


async def main():
    """Run all visual identity tests"""
    print("🎨 Visual Identity Switching Test Suite")
    print("=" * 60)
    
    # Check TCP connection first
    await check_tcp_connection()
    
    # Test direct S1 character switching first
    await test_direct_s1_character_switching()
    
    # Run visual identity switching tests through orchestrator
    await test_visual_identity_switching()


if __name__ == "__main__":
    asyncio.run(main())