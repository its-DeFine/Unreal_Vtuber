#!/usr/bin/env python3
"""
Test Character Visual Identity Application
==========================================

This script tests that each character gets their unique visual identity applied.

Created: 2025-07-14
"""

import asyncio
import httpx
import time


async def test_character_visuals():
    """Test that each character has their unique visual identity"""
    print("🎭 TESTING CHARACTER VISUAL IDENTITIES")
    print("=" * 60)
    
    orchestrator_url = "http://localhost:8082"
    
    # Test cases for each character
    test_cases = [
        {
            "name": "Sophia (Trader)",
            "text": "What are the latest trading opportunities in crypto?",
            "expected_character": "sophia_trader_template",
            "expected_visual": "golden_goddess"
        },
        {
            "name": "Diana (Educator)",
            "text": "Please explain blockchain technology in detail",
            "expected_character": "diana_educator_template", 
            "expected_visual": "emerald_elegance"
        },
        {
            "name": "Luna (Streamer)",
            "text": "Let's have some fun! Tell me a joke!",
            "expected_character": "luna_streamer_template",
            "expected_visual": "ruby_sensation"
        }
    ]
    
    for test in test_cases:
        print(f"\n📋 Testing: {test['name']}")
        print("-" * 40)
        
        request = {
            "stimulus_id": f"visual_test_{int(time.time())}",
            "text": test["text"],
            "context": {"test": "character_visual"}
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send request
                response = await client.post(f"{orchestrator_url}/process", json=request)
                
                if response.status_code == 200:
                    result = response.json()
                    routing = result.get("routing_decision", {})
                    
                    print(f"✅ Routed to: {routing.get('system')}")
                    
                    # For S1 responses, check visual identity
                    if routing.get('system') == 's1':
                        persona = routing.get('config', {}).get('persona')
                        print(f"   Persona: {persona}")
                        print(f"   Expected character: {test['expected_character']}")
                        print(f"   Expected visual: {test['expected_visual']}")
                        
                        # Give time for visual identity to apply
                        await asyncio.sleep(2.0)
                        
                        # Check character status
                        char_response = await client.get("http://localhost:5001/character/current")
                        if char_response.status_code == 200:
                            current_char = char_response.json()
                            actual_id = current_char.get('character', {}).get('id')
                            actual_visual = current_char.get('character', {}).get('visual_identity', {}).get('preset_name')
                            
                            if actual_id == test['expected_character']:
                                print(f"   ✅ Correct character activated: {actual_id}")
                            else:
                                print(f"   ❌ Wrong character: {actual_id}")
                            
                            if actual_visual == test['expected_visual']:
                                print(f"   ✅ Correct visual applied: {actual_visual}")
                            else:
                                print(f"   ❌ Wrong visual: {actual_visual}")
                else:
                    print(f"❌ Request failed: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Wait between tests
        await asyncio.sleep(3.0)
    
    print("\n" + "=" * 60)
    print("🎉 Character visual identity test complete!")
    print("\nNote: Check Unreal Engine to verify visual changes:")
    print("- Sophia: Golden hair, default outfit")
    print("- Diana: Green hair, maid dress")
    print("- Luna: Red/pink hair, pop star outfit")


if __name__ == "__main__":
    asyncio.run(test_character_visuals())