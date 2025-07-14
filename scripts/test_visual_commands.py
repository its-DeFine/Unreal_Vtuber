#!/usr/bin/env python3
"""
Test Visual Identity Commands
=============================

Tests that all 8 TCP commands are sent for visual identity.

Created: 2025-07-14
"""
import asyncio
import httpx
import time


async def test_visual_commands():
    """Test that all visual identity commands are sent"""
    orchestrator_url = "http://localhost:8082"
    
    print("🎨 TESTING VISUAL IDENTITY COMMAND SENDING")
    print("=" * 60)
    
    # Test switching to trader (golden goddess)
    print("\n📋 Switching to Sophia Trader (golden_goddess)")
    print("Expected commands:")
    print("  1. PRS.Fem1")
    print("  2. OF.Default")
    print("  3. HCR.0.9")
    print("  4. HCG.0.8")
    print("  5. HCB.0.2")
    print("  6. HS.Buzz")
    print("  7. EC.0.12")
    print("  8. ES.35000.0")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        stimulus = {
            "stimulus_id": f"visual_test_{int(time.time()*1000)}",
            "text": "Initialize the System 1 Trader Agent",
            "context": {"source": "visual_test"}
        }
        
        response = await client.post(f"{orchestrator_url}/process", json=stimulus)
        
        if response.status_code == 200:
            print("✅ Command sent to orchestrator")
            print("\nWaiting 5 seconds for visual identity to apply...")
            await asyncio.sleep(5)
            
            print("\nNOW CHECK THE DOCKER LOGS:")
            print("docker logs neurosync_s1 --tail 50 | grep 'Sent command'")
            print("\nYou should see all 8 commands being sent!")
        else:
            print(f"❌ Failed: {response.status_code}")


if __name__ == "__main__":
    asyncio.run(test_visual_commands())