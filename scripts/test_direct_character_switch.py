#!/usr/bin/env python3
"""
Direct Character Switch Test
============================

Tests character switching and visual identity application directly.

Created: 2025-07-14
"""
import asyncio
import httpx
import json


async def test_direct_switch():
    """Test direct character switching via S1 API"""
    s1_url = "http://localhost:5001"
    
    print("🔍 DIRECT CHARACTER SWITCH TEST")
    print("=" * 60)
    
    characters = [
        ("sophia_trader_template", "Sophia Trader", "golden_goddess"),
        ("diana_educator_template", "Diana Code", "emerald_elegance"),
        ("luna_streamer_template", "Luna Streamer", "ruby_sensation")
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get current character first
        current_resp = await client.get(f"{s1_url}/character/current")
        if current_resp.status_code == 200:
            current = current_resp.json()
            print(f"Current character: {current.get('character', {}).get('name')}")
            print("-" * 60)
        
        for char_id, name, expected_visual in characters:
            print(f"\n📋 Switching to: {name} ({char_id})")
            
            # Switch character
            response = await client.post(
                f"{s1_url}/character/activate",
                json={"character_id": char_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Response: {json.dumps(result, indent=2)}")
                
                # Wait a bit
                await asyncio.sleep(2)
                
                # Check current character
                current_resp = await client.get(f"{s1_url}/character/current")
                if current_resp.status_code == 200:
                    current = current_resp.json()
                    character = current.get('character', {})
                    visual = character.get('visual_identity', {})
                    
                    print(f"\n✓ Character: {character.get('name')}")
                    print(f"✓ Visual: {visual.get('preset_name')}")
                    print(f"✓ TCP Commands: {visual.get('tcp_commands', [])}")
                    
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_direct_switch())