#!/usr/bin/env python3
"""
Test Initialization Commands
============================

Tests that initialization commands properly route to S1 with correct persona.

Created: 2025-07-14
"""
import asyncio
import httpx
import json


async def test_initialization_commands():
    """Test various initialization command patterns"""
    orchestrator_url = "http://localhost:8082"
    
    test_commands = [
        ("Initialize the System 1 Trader Agent", "trader", "sophia_trader_template"),
        ("Init S1 educator persona", "educator", "diana_educator_template"),
        ("Switch to system one streamer", "streamer", "luna_streamer_template"),
        ("Activate the trader agent", "trader", "sophia_trader_template"),
        ("Use System 1 educator", "educator", "diana_educator_template"),
        ("Start the streamer persona", "streamer", "luna_streamer_template"),
    ]
    
    print("🧪 TESTING INITIALIZATION COMMAND HANDLING")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for command, expected_persona, expected_character in test_commands:
            print(f"\n📝 Testing: '{command}'")
            print("-" * 50)
            
            stimulus = {
                "stimulus_id": f"test_{int(asyncio.get_event_loop().time()*1000)}",
                "text": command,
                "context": {"source": "test"}
            }
            
            try:
                # Send to orchestrator
                response = await client.post(f"{orchestrator_url}/process", json=stimulus)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check routing decision
                    routing = result.get("routing_decision", {})
                    system = routing.get("system")
                    persona = routing.get("config", {}).get("persona")
                    reasoning = routing.get("reasoning", "")
                    
                    print(f"✓ System: {system}")
                    print(f"✓ Persona: {persona}")
                    print(f"✓ Reasoning: {reasoning}")
                    
                    # Verify correct routing
                    if system == "s1" and persona == expected_persona:
                        print(f"✅ PASS: Correctly routed to S1 with {expected_persona} persona")
                        
                        # Check execution results
                        execution = result.get("execution_results", {})
                        s1_result = execution.get("s1", {})
                        if s1_result.get("success") or "character_id" in str(s1_result):
                            print(f"✅ S1 execution successful")
                        else:
                            print(f"⚠️ S1 execution had issues: {s1_result}")
                    else:
                        print(f"❌ FAIL: Expected S1/{expected_persona}, got {system}/{persona}")
                        
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Test complete!")


async def check_character_activation():
    """Check if character is actually activated in S1"""
    print("\n🔍 CHECKING S1 CHARACTER STATE")
    print("=" * 60)
    
    s1_url = "http://localhost:5001"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{s1_url}/character/current")
            
            if response.status_code == 200:
                current = response.json()
                character = current.get('character', {})
                print(f"Current character: {character.get('name', 'Unknown')}")
                print(f"Character ID: {character.get('id', 'Unknown')}")
                
                visual = character.get('visual_identity', {})
                if visual:
                    print(f"Visual preset: {visual.get('preset_name', 'None')}")
                    print(f"TCP commands: {len(visual.get('tcp_commands', []))}")
            else:
                print(f"Could not get current character: {response.status_code}")
                
    except Exception as e:
        print(f"Error checking S1: {e}")


if __name__ == "__main__":
    asyncio.run(test_initialization_commands())
    asyncio.run(check_character_activation())