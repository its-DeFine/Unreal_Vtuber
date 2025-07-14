#!/usr/bin/env python3
"""
Test Character Switch and Visual Identity
=========================================

Tests switching between characters and visual identity application.

Created: 2025-07-14
"""
import asyncio
import httpx
import time


async def test_character_switches():
    """Test switching between different characters"""
    orchestrator_url = "http://localhost:8082"
    
    print("🎭 CHARACTER SWITCH AND VISUAL IDENTITY TEST")
    print("=" * 60)
    
    test_sequence = [
        ("Switch to educator persona", "educator", "diana_educator_template", "emerald_elegance"),
        ("Initialize the System 1 Trader Agent", "trader", "sophia_trader_template", "golden_goddess"),
        ("Activate streamer mode", "streamer", "luna_streamer_template", "ruby_sensation")
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for command, expected_persona, expected_char, expected_visual in test_sequence:
            print(f"\n📝 Testing: '{command}'")
            print("-" * 60)
            
            # Send command
            stimulus = {
                "stimulus_id": f"switch_test_{int(time.time()*1000)}",
                "text": command,
                "context": {"source": "switch_test"}
            }
            
            response = await client.post(f"{orchestrator_url}/process", json=stimulus)
            
            if response.status_code == 200:
                result = response.json()
                routing = result.get("routing_decision", {})
                
                print(f"✅ Routed to: {routing.get('system')}")
                print(f"✅ Persona: {routing.get('config', {}).get('persona')}")
                
                # Wait for character switch
                print("⏳ Waiting 5 seconds for character switch...")
                await asyncio.sleep(5)
                
                # Check current character
                s1_response = await client.get("http://localhost:5001/character/current")
                
                if s1_response.status_code == 200:
                    current = s1_response.json()
                    character = current.get('character', {})
                    visual = character.get('visual_identity', {})
                    
                    print(f"\n✅ Current State:")
                    print(f"   Character: {character.get('name')} ({character.get('id')})")
                    print(f"   Visual: {visual.get('preset_name')}")
                    
                    if character.get('id') == expected_char:
                        print(f"   ✅ Correct character!")
                    else:
                        print(f"   ❌ Wrong character (expected {expected_char})")
                    
                    if visual.get('preset_name') == expected_visual:
                        print(f"   ✅ Correct visual identity!")
                    else:
                        print(f"   ❌ Wrong visual (expected {expected_visual})")
                else:
                    print(f"❌ Could not check S1 state: {s1_response.status_code}")
            else:
                print(f"❌ Orchestrator error: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("📋 CHECK THE LOGS FOR TCP COMMANDS:")
    print("docker logs neurosync_s1 --tail 100 | grep 'Sent command'")
    print("\nFor each character switch, you should see 8 TCP commands!")


if __name__ == "__main__":
    asyncio.run(test_character_switches())