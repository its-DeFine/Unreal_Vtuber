#!/usr/bin/env python3
"""
Manual Visual Identity Cycling Test
Allows manual control of character switching for visual testing
Created: 2025-07-14
"""
import httpx
import asyncio
from typing import Dict, List

# Configuration
S1_URL = "http://localhost:5001"


async def switch_to_character(persona: str, message: str) -> bool:
    """Switch to a specific character"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        payload = {
            "text": message,
            "autonomous_context": f"Routed by orchestrator with persona: {persona}"
        }
        
        try:
            response = await client.post(f"{S1_URL}/process_text", json=payload)
            if response.status_code == 200:
                print(f"✅ Switched to {persona}")
                
                # Get current character
                char_response = await client.get(f"{S1_URL}/character/current")
                if char_response.status_code == 200:
                    char_data = char_response.json().get('character', {})
                    visual = char_data.get('visual_identity', {})
                    
                    print(f"   Character: {char_data.get('name')}")
                    print(f"   Visual: {visual.get('preset_name', 'None')}")
                    if visual:
                        print(f"   Commands: {len(visual.get('tcp_commands', []))} TCP commands")
                
                return True
            else:
                print(f"❌ Failed to switch: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def manual_control():
    """Manual character switching control"""
    print("🎮 Manual Visual Identity Control")
    print("=" * 60)
    print("\nCharacters available:")
    print("1. Sophia (trader) - Golden Goddess (blonde)")
    print("2. Diana (educator) - Emerald Elegance (green)")
    print("3. Luna (streamer) - Ruby Sensation (red)")
    print("\nCommands:")
    print("  1, 2, or 3 - Switch to that character")
    print("  q - Quit")
    print("=" * 60)
    
    characters = [
        {
            "persona": "trader",
            "name": "Sophia Trader",
            "message": "Let's check the market indicators"
        },
        {
            "persona": "educator",
            "name": "Diana Educator",
            "message": "Time for today's lesson"
        },
        {
            "persona": "streamer", 
            "name": "Luna Streamer",
            "message": "Hey everyone! Welcome!"
        }
    ]
    
    current_char = None
    
    while True:
        command = input("\n> ").strip().lower()
        
        if command == 'q':
            print("👋 Exiting...")
            break
        
        if command in ['1', '2', '3']:
            idx = int(command) - 1
            char = characters[idx]
            
            if current_char == char['persona']:
                print(f"Already on {char['name']}")
                continue
            
            print(f"\nSwitching to {char['name']}...")
            success = await switch_to_character(char['persona'], char['message'])
            
            if success:
                current_char = char['persona']
                print("\n⏰ Wait 2-3 seconds for visual changes in Unreal Engine")
            
        else:
            print("Invalid command. Use 1, 2, 3, or q")


async def auto_cycle_once():
    """Automatically cycle through all characters once"""
    print("🔄 Auto-cycling through all characters...")
    print("Watch Unreal Engine for visual changes\n")
    
    characters = [
        ("trader", "Sophia Trader", "Market analysis time"),
        ("educator", "Diana Educator", "Let's learn together"),
        ("streamer", "Luna Streamer", "Hey chat!")
    ]
    
    for persona, name, message in characters:
        print(f"\n{'='*40}")
        print(f"Switching to: {name}")
        await switch_to_character(persona, message)
        
        print("\nWaiting 10 seconds for visual changes...")
        await asyncio.sleep(10)
    
    print("\n✅ Auto-cycle complete!")


async def main():
    """Main menu"""
    print("🎨 Visual Identity Test Tool")
    print("=" * 60)
    print("1. Manual control (switch on demand)")
    print("2. Auto-cycle once (10 seconds each)")
    print("3. Exit")
    print("=" * 60)
    
    choice = input("Select option: ").strip()
    
    if choice == "1":
        await manual_control()
    elif choice == "2":
        await auto_cycle_once()
    else:
        print("Exiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")