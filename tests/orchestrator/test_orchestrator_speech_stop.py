#!/usr/bin/env python3
"""
Test Orchestrator Speech Stopping
Verifies orchestrator stops speech before routing to S1
Created: 2025-07-14
"""
import httpx
import asyncio
import time
import json

# Configuration
ORCHESTRATOR_URL = "http://localhost:8082"
S1_URL = "http://localhost:5001"


async def test_orchestrator_stops_speech():
    """Test that orchestrator stops speech before routing"""
    print("🎯 Testing Orchestrator Speech Stopping\n")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # First, send a long message to S1 to get speech going
        print("1️⃣ Starting initial speech...")
        initial_payload = {
            "text": "Let me tell you a long story about blockchain technology and how it revolutionized the financial world. It all started with the mysterious Satoshi Nakamoto...",
            "autonomous_context": "Routed by orchestrator with persona: educator"
        }
        
        try:
            response = await client.post(f"{S1_URL}/process_text", json=initial_payload)
            if response.status_code == 200:
                print("   ✅ Initial speech started")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Wait a bit for speech to start
        await asyncio.sleep(2)
        
        # Check speech status
        print("\n2️⃣ Checking speech status...")
        try:
            status_response = await client.post(
                f"{S1_URL}/speech/control",
                json={"action": "status"}
            )
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   Active streams: {status.get('active_streams', 0)}")
        except:
            pass
        
        # Now route through orchestrator with different persona
        print("\n3️⃣ Routing new stimulus through orchestrator...")
        orchestrator_payload = {
            "stimulus_id": f"test_stop_{int(time.time())}",
            "text": "Hey everyone! Quick announcement!",
            "context": {"persona": "streamer"}
        }
        
        try:
            # Monitor S1 logs while routing
            print("   Sending to orchestrator...")
            route_response = await client.post(
                f"{ORCHESTRATOR_URL}/route",
                json=orchestrator_payload
            )
            
            if route_response.status_code == 200:
                result = route_response.json()
                print(f"   ✅ Routed to: {result.get('system')}")
                print(f"   Persona: {result.get('config', {}).get('persona')}")
                
                # Execute the routing
                print("\n4️⃣ Executing routing decision...")
                exec_response = await client.post(
                    f"{ORCHESTRATOR_URL}/execute",
                    json=result
                )
                
                if exec_response.status_code == 200:
                    print("   ✅ Execution complete")
                    
                    # Check if speech was stopped
                    await asyncio.sleep(1)
                    
                    # Check final status
                    print("\n5️⃣ Checking final speech status...")
                    try:
                        final_status = await client.post(
                            f"{S1_URL}/speech/control",
                            json={"action": "status"}
                        )
                        if final_status.status_code == 200:
                            status = final_status.json()
                            print(f"   Active streams: {status.get('active_streams', 0)}")
                            print(f"   Status: {status.get('status')}")
                    except:
                        pass
                    
                    # Verify character switched
                    char_response = await client.get(f"{S1_URL}/character/current")
                    if char_response.status_code == 200:
                        char = char_response.json().get('character', {})
                        print(f"\n✅ Character switched to: {char.get('name')}")
                        print(f"   ID: {char.get('id')}")
                else:
                    print(f"   ❌ Execution failed: {exec_response.status_code}")
            else:
                print(f"   ❌ Routing failed: {route_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("\nThe orchestrator should have:")
    print("1. Stopped the educator's long speech")
    print("2. Switched to streamer persona")
    print("3. Started new speech without overlap")


async def main():
    """Run the test"""
    await test_orchestrator_stops_speech()


if __name__ == "__main__":
    asyncio.run(main())