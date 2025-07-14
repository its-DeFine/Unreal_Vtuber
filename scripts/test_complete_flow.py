#!/usr/bin/env python3
"""
Test Complete Visual Identity Flow
==================================

Tests the complete flow from orchestrator to visual identity commands.

Created: 2025-07-14
"""
import asyncio
import httpx
import time


async def test_complete_flow():
    """Test complete flow with detailed logging"""
    orchestrator_url = "http://localhost:8082"
    
    print("🎭 COMPLETE VISUAL IDENTITY FLOW TEST")
    print("=" * 60)
    
    # Wait for services to be ready
    print("Waiting for services to stabilize...")
    await asyncio.sleep(5)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test trader activation
        print("\n1️⃣ Testing: Initialize the System 1 Trader Agent")
        print("-" * 60)
        
        stimulus = {
            "stimulus_id": f"complete_test_{int(time.time()*1000)}",
            "text": "Initialize the System 1 Trader Agent",
            "context": {"source": "complete_test"}
        }
        
        response = await client.post(f"{orchestrator_url}/process", json=stimulus)
        
        if response.status_code == 200:
            result = response.json()
            routing = result.get("routing_decision", {})
            execution = result.get("execution_results", {})
            
            print(f"✅ Routed to: {routing.get('system')}")
            print(f"✅ Persona: {routing.get('config', {}).get('persona')}")
            print(f"✅ Character ID should be: sophia_trader_template")
            
            # Wait for processing
            print("\nWaiting 10 seconds for visual identity to apply...")
            await asyncio.sleep(10)
            
            # Check S1 state
            s1_response = await client.get("http://localhost:5001/character/current")
            
            if s1_response.status_code == 200:
                current = s1_response.json()
                character = current.get('character', {})
                visual = character.get('visual_identity', {})
                
                print(f"\n✅ Current Character:")
                print(f"   Name: {character.get('name')}")
                print(f"   ID: {character.get('id')}")
                print(f"   Visual: {visual.get('preset_name')}")
                print(f"   Commands: {visual.get('tcp_commands', [])}")
            else:
                print(f"❌ Could not check S1 state: {s1_response.status_code}")
                
        else:
            print(f"❌ Orchestrator error: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("📋 NOW CHECK THE LOGS:")
    print("1. docker logs vtuber_orchestrator --tail 50")
    print("2. docker logs neurosync_s1 --tail 50 | grep -E '(Sent command|visual|character)'")
    print("\nYou should see:")
    print("- Character activation attempt in orchestrator")
    print("- All 8 TCP commands being sent in S1")


if __name__ == "__main__":
    asyncio.run(test_complete_flow())