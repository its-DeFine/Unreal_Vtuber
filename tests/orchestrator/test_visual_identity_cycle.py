#!/usr/bin/env python3
"""
Visual Identity Cycling Test
Continuously cycles through all three female characters to demonstrate visual switching
Created: 2025-07-14
"""
import httpx
import asyncio
import time
from typing import Dict, List

# Configuration
S1_URL = "http://localhost:5001"


async def cycle_characters(duration_per_character: int = 10, total_cycles: int = 3):
    """
    Cycle through all three characters with visual identity switching
    
    Args:
        duration_per_character: Seconds to stay on each character
        total_cycles: Number of complete cycles through all characters
    """
    print("🎨 Visual Identity Cycling Test")
    print("=" * 60)
    print(f"Duration per character: {duration_per_character} seconds")
    print(f"Total cycles: {total_cycles}")
    print("\nPress Ctrl+C to stop early\n")
    
    # Character test cases
    characters = [
        {
            "persona": "trader",
            "name": "Sophia Trader",
            "visual": "Golden Goddess",
            "message": "Bitcoin is showing interesting patterns today"
        },
        {
            "persona": "educator",
            "name": "Diana Educator", 
            "visual": "Emerald Elegance",
            "message": "Let me explain how blockchain consensus works"
        },
        {
            "persona": "streamer",
            "name": "Luna Streamer",
            "visual": "Ruby Sensation", 
            "message": "Hey everyone! Welcome to the stream!"
        }
    ]
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        try:
            for cycle in range(total_cycles):
                print(f"\n🔄 CYCLE {cycle + 1}/{total_cycles}")
                print("=" * 60)
                
                for char in characters:
                    print(f"\n⏱️  Switching to: {char['name']}")
                    print(f"   Visual: {char['visual']}")
                    print(f"   Persona: {char['persona']}")
                    
                    # Send message to S1 with persona context
                    payload = {
                        "text": char['message'],
                        "autonomous_context": f"Routed by orchestrator with persona: {char['persona']}"
                    }
                    
                    try:
                        # Send request
                        response = await client.post(f"{S1_URL}/process_text", json=payload)
                        
                        if response.status_code == 200:
                            print(f"   ✅ Character switched successfully")
                            
                            # Get current character to confirm
                            char_response = await client.get(f"{S1_URL}/character/current")
                            if char_response.status_code == 200:
                                current = char_response.json().get('character', {})
                                visual = current.get('visual_identity', {})
                                
                                if visual:
                                    print(f"   🎨 Visual commands sent: {len(visual.get('tcp_commands', []))} commands")
                                    print(f"   📡 TCP Commands: {', '.join(visual.get('tcp_commands', [])[:3])}...")
                        else:
                            print(f"   ❌ Failed to switch: {response.status_code}")
                    
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                    
                    # Show countdown
                    print(f"\n   Displaying for {duration_per_character} seconds...")
                    for i in range(duration_per_character, 0, -1):
                        print(f"   {i}...", end="\r", flush=True)
                        await asyncio.sleep(1)
                    print("   Done!    ")
                
                if cycle < total_cycles - 1:
                    print(f"\n✨ Cycle {cycle + 1} complete! Starting next cycle...")
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Test stopped by user")
        
        print("\n" + "=" * 60)
        print("🎨 Visual Identity Cycling Complete!")


async def quick_demo():
    """Quick 30-second demo cycling through all characters"""
    print("🚀 Quick Visual Demo (30 seconds total)\n")
    await cycle_characters(duration_per_character=10, total_cycles=1)


async def extended_demo():
    """Extended demo for thorough testing"""
    print("🎬 Extended Visual Demo (3 minutes total)\n")
    await cycle_characters(duration_per_character=20, total_cycles=3)


async def main():
    """Main entry point with menu"""
    print("🎨 Visual Identity Cycling Test")
    print("=" * 60)
    print("1. Quick Demo (30 seconds)")
    print("2. Extended Demo (3 minutes)")
    print("3. Custom Settings")
    print("=" * 60)
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == "1":
        await quick_demo()
    elif choice == "2":
        await extended_demo()
    elif choice == "3":
        duration = int(input("Duration per character (seconds): "))
        cycles = int(input("Number of cycles: "))
        await cycle_characters(duration, cycles)
    else:
        print("Invalid choice. Running quick demo...")
        await quick_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")