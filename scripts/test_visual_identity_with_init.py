#!/usr/bin/env python3
"""
Test Visual Identity Application with Init Commands
==================================================

Verifies that initialization commands trigger proper visual identity changes.

Created: 2025-07-14
"""
import asyncio
import httpx
import time


async def test_visual_identity_application():
    """Test that init commands apply visual identity"""
    orchestrator_url = "http://localhost:8082"
    s1_url = "http://localhost:5001"
    
    # Test each character initialization
    test_cases = [
        {
            "command": "Initialize the System 1 Trader Agent",
            "expected_character": "sophia_trader_template",
            "expected_name": "Sophia Trader",
            "expected_visual": "golden_goddess"
        },
        {
            "command": "Switch to educator persona", 
            "expected_character": "diana_educator_template",
            "expected_name": "Diana Code",
            "expected_visual": "emerald_elegance"
        },
        {
            "command": "Start the streamer agent",
            "expected_character": "luna_streamer_template", 
            "expected_name": "Luna Streamer",
            "expected_visual": "ruby_sensation"
        }
    ]
    
    print("🎭 TESTING VISUAL IDENTITY WITH INITIALIZATION COMMANDS")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test in test_cases:
            print(f"\n📝 Testing: '{test['command']}'")
            print("-" * 50)
            
            # Send initialization command
            stimulus = {
                "stimulus_id": f"test_visual_{int(time.time()*1000)}",
                "text": test["command"],
                "context": {"source": "visual_test"}
            }
            
            try:
                # Send to orchestrator
                response = await client.post(f"{orchestrator_url}/process", json=stimulus)
                
                if response.status_code == 200:
                    result = response.json()
                    routing = result.get("routing_decision", {})
                    
                    if routing.get("system") == "s1":
                        print(f"✓ Routed to S1 with persona: {routing.get('config', {}).get('persona')}")
                        
                        # Wait for character switch to complete
                        await asyncio.sleep(2.0)
                        
                        # Check current character in S1
                        char_response = await client.get(f"{s1_url}/character/current")
                        
                        if char_response.status_code == 200:
                            current = char_response.json()
                            character = current.get('character', {})
                            visual = character.get('visual_identity', {})
                            
                            print(f"\n🔍 Character State:")
                            print(f"   ID: {character.get('id')}")
                            print(f"   Name: {character.get('name')}")
                            print(f"   Visual Preset: {visual.get('preset_name')}")
                            print(f"   TCP Commands: {len(visual.get('tcp_commands', []))}")
                            
                            # Verify expectations
                            if character.get('id') == test['expected_character']:
                                print(f"   ✅ Correct character ID")
                            else:
                                print(f"   ❌ Wrong character: expected {test['expected_character']}")
                                
                            if visual.get('preset_name') == test['expected_visual']:
                                print(f"   ✅ Correct visual preset")
                            else:
                                print(f"   ❌ Wrong visual: expected {test['expected_visual']}")
                                
                            # Show TCP commands
                            if visual.get('tcp_commands'):
                                print(f"\n   📡 TCP Commands being sent:")
                                for cmd in visual['tcp_commands'][:3]:  # First 3 commands
                                    print(f"      - {cmd['command']}")
                                if len(visual['tcp_commands']) > 3:
                                    print(f"      ... and {len(visual['tcp_commands']) - 3} more")
                                    
                        else:
                            print(f"❌ Could not check character state: {char_response.status_code}")
                    else:
                        print(f"❌ Not routed to S1: {routing.get('system')}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Visual identity test complete!")
    print("\nIf visual identities are not changing in Unreal Engine:")
    print("1. Check that Unreal Engine TCP server is running on port 7777")
    print("2. Verify UNREAL_TCP_HOST environment variable")
    print("3. Check docker logs for TCP connection errors")


if __name__ == "__main__":
    asyncio.run(test_visual_identity_application())