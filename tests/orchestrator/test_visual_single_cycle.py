#!/usr/bin/env python3
"""
Single Visual Identity Cycle Test
One careful cycle through all characters with proper timing
Created: 2025-07-14
"""
import httpx
import asyncio
import time

# Configuration
S1_URL = "http://localhost:5001"


async def single_cycle():
    """Perform one cycle through all characters with proper timing"""
    print("🎨 Visual Identity Single Cycle Test")
    print("=" * 60)
    print("This test will cycle through all three characters ONCE")
    print("with proper delays between switches\n")
    
    characters = [
        {
            "persona": "trader",
            "name": "Sophia Trader",
            "visual": "Golden Goddess",
            "description": "Blonde hair, professional look",
            "message": "Analyzing market patterns"
        },
        {
            "persona": "educator",
            "name": "Diana Educator",
            "visual": "Emerald Elegance",
            "description": "Green tones, academic style",
            "message": "Let's explore blockchain technology"
        },
        {
            "persona": "streamer",
            "name": "Luna Streamer",
            "visual": "Ruby Sensation",
            "description": "Red/pink hair, energetic look",
            "message": "Hey everyone! Great to see you!"
        }
    ]
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        for i, char in enumerate(characters):
            print(f"\n{'='*60}")
            print(f"CHARACTER {i+1}/3: {char['name']}")
            print(f"Visual: {char['visual']} - {char['description']}")
            print("="*60)
            
            # Send switch command
            print(f"\n1. Sending switch command...")
            payload = {
                "text": char['message'],
                "autonomous_context": f"Routed by orchestrator with persona: {char['persona']}"
            }
            
            try:
                response = await client.post(f"{S1_URL}/process_text", json=payload)
                
                if response.status_code == 200:
                    print(f"   ✅ Switch command sent")
                    
                    # Wait for processing
                    print("\n2. Waiting 3 seconds for character switch...")
                    await asyncio.sleep(3)
                    
                    # Verify switch
                    print("\n3. Verifying character...")
                    char_response = await client.get(f"{S1_URL}/character/current")
                    
                    if char_response.status_code == 200:
                        current = char_response.json().get('character', {})
                        visual = current.get('visual_identity', {})
                        
                        print(f"   ✅ Active: {current.get('name')}")
                        print(f"   ✅ Visual: {visual.get('preset_name', 'None')}")
                        
                        if visual and 'tcp_commands' in visual:
                            print(f"   ✅ Commands: {len(visual['tcp_commands'])} TCP commands sent")
                            print(f"   📡 First 3 commands: {', '.join(visual['tcp_commands'][:3])}")
                    
                    # Wait for visual changes
                    print("\n4. Waiting 5 seconds for visual changes to apply...")
                    await asyncio.sleep(5)
                    
                    # Hold for observation
                    print("\n5. OBSERVE UNREAL ENGINE NOW!")
                    print(f"   You should see: {char['description']}")
                    print("   Holding for 15 seconds...")
                    
                    for sec in range(15, 0, -1):
                        print(f"   {sec}...", end="\r", flush=True)
                        await asyncio.sleep(1)
                    
                    print("   Done!                    ")
                    
                else:
                    print(f"   ❌ Failed to switch: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Test Complete!")
    print("\nDid you see all three visual identities?")
    print("1. Sophia - Blonde hair (Golden Goddess)")
    print("2. Diana - Green tones (Emerald Elegance)")
    print("3. Luna - Red/pink hair (Ruby Sensation)")


if __name__ == "__main__":
    asyncio.run(single_cycle())