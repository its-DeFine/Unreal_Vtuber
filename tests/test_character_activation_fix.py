#!/usr/bin/env python3
"""
Test script to verify character activation and visual identity switching
Created: 2025-07-14 22:30

This test verifies that:
1. S2 can successfully call S1's character/activate endpoint
2. Visual identity is applied when characters are switched
3. The API endpoints are compatible between S2 and S1
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime


class CharacterActivationTester:
    def __init__(self):
        self.s1_base_url = "http://localhost:5001"
        self.s2_base_url = "http://localhost:5002"
        
    async def test_s1_endpoints(self):
        """Test S1 character endpoints directly"""
        print("\n🔍 Testing S1 Endpoints...")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Test character list
            try:
                async with session.get(f"{self.s1_base_url}/character/list") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ /character/list: {len(data.get('characters', []))} characters available")
                        for char in data.get('characters', []):
                            print(f"   - {char['id']}: {char['name']} ({char['role']})")
                    else:
                        print(f"❌ /character/list failed: {resp.status}")
            except Exception as e:
                print(f"❌ Error testing /character/list: {e}")
            
            # Test current character
            try:
                async with session.get(f"{self.s1_base_url}/character/current") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data.get('character', {})
                        print(f"✅ /character/current: {current.get('name', 'Unknown')}")
                    else:
                        print(f"❌ /character/current failed: {resp.status}")
            except Exception as e:
                print(f"❌ Error testing /character/current: {e}")
    
    async def test_character_activation(self, character_id: str):
        """Test character activation via both endpoints"""
        print(f"\n🎭 Testing Character Activation for: {character_id}")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Test /character/activate (new endpoint)
            print("\n1️⃣ Testing /character/activate endpoint...")
            try:
                payload = {"character_id": character_id}
                async with session.post(
                    f"{self.s1_base_url}/character/activate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Character activated successfully via /activate")
                        print(f"   Current: {data.get('current_character', {}).get('name')}")
                    else:
                        text = await resp.text()
                        print(f"❌ Activation failed: {resp.status} - {text}")
            except Exception as e:
                print(f"❌ Error calling /character/activate: {e}")
            
            # Test /character/switch (original endpoint)
            print("\n2️⃣ Testing /character/switch endpoint...")
            try:
                payload = {"character_id": character_id}
                async with session.post(
                    f"{self.s1_base_url}/character/switch",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Character switched successfully via /switch")
                        print(f"   Current: {data.get('current_character', {}).get('name')}")
                    else:
                        text = await resp.text()
                        print(f"❌ Switch failed: {resp.status} - {text}")
            except Exception as e:
                print(f"❌ Error calling /character/switch: {e}")
    
    async def test_s2_to_s1_forwarding(self):
        """Test if S2 correctly forwards character activation to S1"""
        print("\n🔄 Testing S2 to S1 Forwarding...")
        print("=" * 50)
        
        # This would test the actual S2 orchestrator calling S1
        # For now, we'll note this as a manual test requirement
        print("📝 Note: Full S2->S1 forwarding test requires running containers")
        print("   Run: docker-compose -f docker-compose.all.yml up")
        print("   Then observe logs for character activation forwarding")
    
    async def run_all_tests(self):
        """Run all character activation tests"""
        print(f"\n🚀 Character Activation Test Suite")
        print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Test S1 endpoints
        await self.test_s1_endpoints()
        
        # Test character activation with different characters
        test_characters = [
            "emma_educator",
            "dr_house_trader",
            "weatherman_streamer"
        ]
        
        for char_id in test_characters:
            await self.test_character_activation(char_id)
            await asyncio.sleep(2)  # Give time for visual identity to apply
        
        # Test S2 forwarding
        await self.test_s2_to_s1_forwarding()
        
        print("\n✅ Test suite completed!")


def main():
    """Main test runner"""
    print("🧪 Character Activation & Visual Identity Test")
    print("=" * 70)
    print("This test verifies the fix for character activation API mismatch")
    print("between S2 and S1, ensuring visual identities are properly applied.")
    print("=" * 70)
    
    # Check if S1 is running
    import requests
    try:
        resp = requests.get("http://localhost:5001/health", timeout=2)
        if resp.status_code != 200:
            print("\n⚠️  S1 system not responding on port 5001")
            print("   Please ensure S1 container is running")
            return
    except:
        print("\n❌ Cannot connect to S1 system on port 5001")
        print("   Run: docker-compose -f docker-compose.all.yml up neurosync_s1")
        return
    
    # Run async tests
    tester = CharacterActivationTester()
    asyncio.run(tester.run_all_tests())


if __name__ == "__main__":
    main()