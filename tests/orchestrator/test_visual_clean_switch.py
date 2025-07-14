#!/usr/bin/env python3
"""
Clean Visual Identity Switching Test
Ensures speech stops before character/visual switches
Created: 2025-07-14
"""
import httpx
import asyncio
import time

# Configuration
S1_URL = "http://localhost:5001"


async def stop_speech(client: httpx.AsyncClient) -> bool:
    """Stop any current speech playback"""
    try:
        response = await client.post(
            f"{S1_URL}/speech/control",
            json={"action": "stop"}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   🛑 Stopped {result.get('streams_stopped', 0)} audio streams")
            return True
        else:
            print(f"   ⚠️  Could not stop speech: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️  Error stopping speech: {e}")
        return False


async def switch_character_cleanly(client: httpx.AsyncClient, persona: str, message: str) -> bool:
    """Switch character with proper speech stopping"""
    # First stop any current speech
    print("   Stopping current speech...")
    await stop_speech(client)
    
    # Small pause to ensure stop is processed
    await asyncio.sleep(0.5)
    
    # Now switch character
    print(f"   Switching to {persona}...")
    payload = {
        "text": message,
        "autonomous_context": f"Routed by orchestrator with persona: {persona}"
    }
    
    try:
        response = await client.post(f"{S1_URL}/process_text", json=payload)
        if response.status_code == 200:
            print(f"   ✅ Switched to {persona}")
            return True
        else:
            print(f"   ❌ Failed to switch: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def clean_visual_cycle():
    """Cycle through characters with clean speech transitions"""
    print("🎨 Clean Visual Identity Switching Test")
    print("=" * 60)
    print("This test ensures speech stops cleanly between character switches\n")
    
    characters = [
        {
            "persona": "trader",
            "name": "Sophia Trader",
            "visual": "Golden Goddess (blonde)",
            "message": "Let me analyze the current market trends for you."
        },
        {
            "persona": "educator",
            "name": "Diana Educator",
            "visual": "Emerald Elegance (green)",
            "message": "Today's lesson will cover blockchain fundamentals."
        },
        {
            "persona": "streamer",
            "name": "Luna Streamer",
            "visual": "Ruby Sensation (red/pink)",
            "message": "Hey everyone! Welcome to the stream! Let's have some fun!"
        }
    ]
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # Initial status check
        print("📊 Checking initial speech status...")
        try:
            status_response = await client.post(
                f"{S1_URL}/speech/control",
                json={"action": "status"}
            )
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   Active streams: {status.get('active_streams', 0)}")
                print(f"   Status: {status.get('status', 'unknown')}")
        except:
            pass
        
        print("\n🔄 Starting clean character cycle...\n")
        
        for i, char in enumerate(characters):
            print(f"{'='*60}")
            print(f"CHARACTER {i+1}/3: {char['name']}")
            print(f"Visual: {char['visual']}")
            print("="*60)
            
            # Clean switch
            success = await switch_character_cleanly(client, char['persona'], char['message'])
            
            if success:
                # Wait for visual to apply
                print("   ⏳ Waiting 3 seconds for visual identity...")
                await asyncio.sleep(3)
                
                # Verify character
                try:
                    char_response = await client.get(f"{S1_URL}/character/current")
                    if char_response.status_code == 200:
                        current = char_response.json().get('character', {})
                        visual = current.get('visual_identity', {})
                        print(f"   ✅ Active: {current.get('name')}")
                        print(f"   ✅ Visual: {visual.get('preset_name', 'None')}")
                except:
                    pass
                
                # Let character speak briefly
                print(f"\n   🎤 {char['name']} is speaking...")
                print("   👀 Watch Unreal Engine - visual should match!")
                
                # Hold for observation
                for sec in range(10, 0, -1):
                    print(f"   Next switch in: {sec} seconds...", end="\r", flush=True)
                    await asyncio.sleep(1)
                print("   Ready for next character!      ")
            
            print()  # Empty line between characters
        
        # Final cleanup
        print("\n🧹 Final cleanup...")
        await stop_speech(client)
        
        print(f"\n{'='*60}")
        print("✅ Clean switching test complete!")
        print("\nDid the speech stop cleanly between character switches?")
        print("Did each visual identity appear without overlap?")


async def main():
    """Run the clean visual switching test"""
    await clean_visual_cycle()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")