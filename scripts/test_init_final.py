#!/usr/bin/env python3
"""
Final Test of Init Commands
===========================

Tests that everything works end-to-end after fixes.

Created: 2025-07-14
"""
import asyncio
import httpx
import time


async def test_complete_flow():
    """Test complete flow from init command to visual identity"""
    orchestrator_url = "http://localhost:8082"
    
    print("🚀 FINAL TEST: INIT COMMANDS → CHARACTER SWITCH → VISUAL IDENTITY")
    print("=" * 70)
    
    test_sequence = [
        ("Initialize the System 1 Trader Agent", "sophia_trader_template", "golden_goddess"),
        ("Switch to educator persona", "diana_educator_template", "emerald_elegance"),
        ("Activate streamer mode", "luna_streamer_template", "ruby_sensation"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for command, expected_char, expected_visual in test_sequence:
            print(f"\n📝 Command: '{command}'")
            print("-" * 60)
            
            # Send to orchestrator
            stimulus = {
                "stimulus_id": f"final_test_{int(time.time()*1000)}",
                "text": command,
                "context": {"source": "final_test"}
            }
            
            response = await client.post(f"{orchestrator_url}/process", json=stimulus)
            
            if response.status_code == 200:
                result = response.json()
                routing = result.get("routing_decision", {})
                system = routing.get("system")
                persona = routing.get("config", {}).get("persona")
                
                print(f"✓ Routed to: {system}")
                print(f"✓ Persona: {persona}")
                
                # Wait for processing
                await asyncio.sleep(3.0)
                
                # Check S1 state
                s1_response = await client.get("http://localhost:5001/character/current")
                
                if s1_response.status_code == 200:
                    current = s1_response.json()
                    character = current.get('character', {})
                    visual = character.get('visual_identity', {})
                    
                    print(f"\n✅ Results:")
                    print(f"   Character: {character.get('name')} ({character.get('id')})")
                    print(f"   Visual: {visual.get('preset_name')}")
                    print(f"   Commands: {len(visual.get('tcp_commands', []))}")
                    
                    # Verify expectations
                    if character.get('id') == expected_char:
                        print(f"   ✅ Correct character!")
                    else:
                        print(f"   ❌ Wrong character (expected {expected_char})")
                        
                    if visual.get('preset_name') == expected_visual:
                        print(f"   ✅ Correct visual!")
                    else:
                        print(f"   ❌ Wrong visual (expected {expected_visual})")
                        
                else:
                    print(f"❌ Could not check S1 state: {s1_response.status_code}")
            else:
                print(f"❌ Orchestrator error: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("🏁 Test complete!")
    
    # Check for any errors in the logs
    print("\n📋 Checking for errors...")
    try:
        # This would normally check logs, but for now we'll just remind to check manually
        print("   Please check docker logs for any 'bool object is not subscriptable' errors")
        print("   Command: docker logs neurosync_s1 --tail 50 | grep -i error")
    except:
        pass


if __name__ == "__main__":
    asyncio.run(test_complete_flow())