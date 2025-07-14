#!/usr/bin/env python3
"""
Slow Visual Identity Test
Carefully paced character switching with confirmation
Created: 2025-07-14
"""
import httpx
import asyncio
import time
from typing import Dict, List

# Configuration
S1_URL = "http://localhost:5001"


async def slow_character_switch():
    """
    Slowly switch between characters with pauses for visual processing
    """
    print("🎨 Slow Visual Identity Switching Test")
    print("=" * 60)
    print("This test will slowly switch between characters")
    print("with confirmation at each step\n")
    
    # Character test cases
    characters = [
        {
            "persona": "trader",
            "name": "Sophia Trader",
            "visual": "Golden Goddess (Blonde hair, professional)",
            "message": "Let's analyze the market trends",
            "tcp_preview": ["PRS.Fem1", "HCR.0.9", "HCG.0.8"]  # Blonde
        },
        {
            "persona": "educator",
            "name": "Diana Educator", 
            "visual": "Emerald Elegance (Green tones, academic)",
            "message": "Time for a blockchain lesson",
            "tcp_preview": ["PRS.Fem", "OF.TeacherOutfit", "HCR.0.2"]  # Green tones
        },
        {
            "persona": "streamer",
            "name": "Luna Streamer",
            "visual": "Ruby Sensation (Red/Pink hair, energetic)", 
            "message": "Hey chat! Ready for fun?",
            "tcp_preview": ["PRS.Fem", "OF.PopStar", "HCR.0.95"]  # Red hair
        }
    ]
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        print("🔍 Starting character switching sequence...\n")
        
        for idx, char in enumerate(characters):
            print(f"\n{'='*60}")
            print(f"📍 CHARACTER {idx + 1}/3: {char['name']}")
            print(f"{'='*60}")
            
            print(f"\n1️⃣  Preparing to switch...")
            print(f"   Target: {char['name']}")
            print(f"   Visual: {char['visual']}")
            print(f"   Key commands: {', '.join(char['tcp_preview'])}")
            
            # Wait before switching
            print("\n   Waiting 3 seconds before switch...")
            await asyncio.sleep(3)
            
            # Send the switch command
            print(f"\n2️⃣  Sending character switch command...")
            payload = {
                "text": char['message'],
                "autonomous_context": f"Routed by orchestrator with persona: {char['persona']}"
            }
            
            try:
                response = await client.post(f"{S1_URL}/process_text", json=payload)
                
                if response.status_code == 200:
                    print(f"   ✅ Switch command sent successfully")
                    
                    # Wait for visual identity to apply
                    print("\n3️⃣  Waiting for visual identity to apply...")
                    print("   Processing TCP commands...")
                    await asyncio.sleep(2)
                    
                    # Verify the switch
                    print("\n4️⃣  Verifying character switch...")
                    char_response = await client.get(f"{S1_URL}/character/current")
                    
                    if char_response.status_code == 200:
                        current = char_response.json().get('character', {})
                        visual = current.get('visual_identity', {})
                        
                        print(f"   ✅ Current character: {current.get('name')}")
                        print(f"   ✅ Character ID: {current.get('id')}")
                        
                        if visual:
                            print(f"   ✅ Visual preset: {visual.get('preset_name')}")
                            print(f"   ✅ Total TCP commands: {len(visual.get('tcp_commands', []))}")
                            
                            # Show all TCP commands
                            print("\n   📡 Full TCP command list:")
                            for cmd in visual.get('tcp_commands', []):
                                print(f"      - {cmd}")
                        else:
                            print("   ⚠️  No visual identity found")
                else:
                    print(f"   ❌ Switch failed: {response.status_code}")
            
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Hold on this character
            if idx < len(characters) - 1:
                print(f"\n5️⃣  Holding on {char['name']} for 15 seconds...")
                print("   Watch for visual changes in Unreal Engine")
                print("   (Hair color, outfit, style should change)")
                
                for i in range(15, 0, -1):
                    print(f"   Next switch in: {i} seconds...", end="\r", flush=True)
                    await asyncio.sleep(1)
                print("   Ready for next character!      ")
            else:
                print(f"\n✅ Final character reached: {char['name']}")
                print("   Test complete!")
        
        print(f"\n{'='*60}")
        print("🎨 All characters tested!")
        print("\nDid you see all three visual identities?")
        print("- Sophia (Golden/Blonde)")
        print("- Diana (Emerald/Green)")  
        print("- Luna (Ruby/Red)")


async def main():
    """Run the slow visual identity test"""
    await slow_character_switch()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")