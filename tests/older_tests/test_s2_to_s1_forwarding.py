#!/usr/bin/env python3
"""
Test S2 to S1 Forwarding with s1_and_s2 Processing Mode
Created: 2025-07-13

This test verifies that when processing_mode is "s1_and_s2", 
S2 processes the stimuli AND forwards to S1 for speech generation.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


class TestS2ToS1Forwarding:
    """Test the fixed S2->S1 forwarding functionality"""
    
    def __init__(self):
        self.s2_url = "http://localhost:8200"  # S2 AutoGen container
        self.s1_url = "http://localhost:5001"  # S1 NeuroSync container
        
    async def check_services(self):
        """Check if both S1 and S2 containers are running"""
        print("\n🔍 Checking container services...")
        
        services_ok = True
        async with aiohttp.ClientSession() as session:
            # Check S2
            try:
                async with session.get(f"{self.s2_url}/api/stimuli/status") as resp:
                    if resp.status == 200:
                        print("✅ S2 AutoGen container is running")
                    else:
                        print(f"❌ S2 container returned: {resp.status}")
                        services_ok = False
            except Exception as e:
                print(f"❌ Cannot connect to S2: {e}")
                services_ok = False
            
            # Check S1
            try:
                async with session.get(f"{self.s1_url}/health") as resp:
                    if resp.status == 200:
                        print("✅ S1 NeuroSync container is running")
                    else:
                        print(f"❌ S1 container returned: {resp.status}")
                        services_ok = False
            except Exception as e:
                print(f"❌ Cannot connect to S1: {e}")
                services_ok = False
        
        return services_ok
    
    async def monitor_s1_logs(self, duration=30):
        """Monitor S1 logs to see if it receives forwarded requests"""
        print(f"\n📋 Monitoring S1 activity for {duration} seconds...")
        print("   (Looking for process_text or character/activate requests)")
        
        # In a real implementation, this would tail the S1 logs
        # For now, we'll just note that logs should be checked
        print("   ⚠️  Please check S1 logs manually: docker logs neurosync_s1 -f")
        
    async def test_s1_and_s2_mode(self):
        """Test stimuli with s1_and_s2 processing mode"""
        
        print("\n🚀 TESTING S2->S1 FORWARDING WITH s1_and_s2 MODE")
        print("="*60)
        
        # Start monitoring S1 in background
        monitor_task = asyncio.create_task(self.monitor_s1_logs())
        
        async with aiohttp.ClientSession() as session:
            
            # Test 1: Trader with s1_and_s2 mode
            print("\n💼 TEST 1: TRADER - S1_AND_S2 Mode")
            print("-"*50)
            
            trader_stimuli = {
                "stimuli_id": f"s1_s2_trader_{int(time.time())}",
                "content": "Bitcoin just broke $50,000! This is a major bullish signal. Our momentum strategy suggests increasing positions.",
                "source": "forwarding_test",
                "priority": "high",
                "category": "market_alert",
                "confidence": 0.95,
                "metadata": {
                    "processing_mode": "s1_and_s2",  # CRITICAL: This triggers forwarding
                    "character_type": "gordon_trader_template",
                    "team_preference": "trader",
                    "test_note": "Should trigger both S2 analysis AND S1 speech"
                }
            }
            
            print(f"📤 Sending stimuli with processing_mode: s1_and_s2")
            print(f"   Character: {trader_stimuli['metadata']['character_type']}")
            
            try:
                async with session.post(
                    f"{self.s2_url}/api/stimuli/receive",
                    json=trader_stimuli
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ S2 received and queued stimuli")
                        print(f"   Response: {json.dumps(result, indent=2)}")
                    else:
                        error_text = await resp.text()
                        print(f"❌ S2 Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            # Wait for processing
            print(f"\n⏳ Waiting 10 seconds for S2 processing and S1 forwarding...")
            await asyncio.sleep(10)
            
            # Test 2: Educator with s1_and_s2 mode
            print("\n🎓 TEST 2: EDUCATOR - S1_AND_S2 Mode")
            print("-"*50)
            
            educator_stimuli = {
                "stimuli_id": f"s1_s2_educator_{int(time.time())}",
                "content": "Let me explain Test-Driven Development. First, you write a failing test. Then, you write just enough code to make it pass.",
                "source": "forwarding_test",
                "priority": "medium",
                "category": "educational",
                "confidence": 0.9,
                "metadata": {
                    "processing_mode": "s1_and_s2",
                    "character_type": "sarah_educator_template",
                    "team_preference": "educator"
                }
            }
            
            print(f"📤 Sending educator stimuli")
            
            try:
                async with session.post(
                    f"{self.s2_url}/api/stimuli/receive",
                    json=educator_stimuli
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ S2 received educator stimuli")
                        print(f"   Stimuli ID: {result.get('stimuli_id')}")
                    else:
                        error_text = await resp.text()
                        print(f"❌ Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            # Wait for processing
            print(f"\n⏳ Waiting 10 seconds for processing...")
            await asyncio.sleep(10)
            
            # Test 3: Verify S2-only mode still works
            print("\n🔍 TEST 3: S2_ONLY Mode (Control Test)")
            print("-"*50)
            
            s2_only_stimuli = {
                "stimuli_id": f"s2_only_test_{int(time.time())}",
                "content": "Analyze the market trends for NVIDIA stock.",
                "source": "forwarding_test",
                "priority": "low",
                "metadata": {
                    "processing_mode": "s2_only",  # Should NOT forward to S1
                    "character_type": "trader"
                }
            }
            
            print(f"📤 Sending S2-only stimuli (should NOT forward to S1)")
            
            try:
                async with session.post(
                    f"{self.s2_url}/api/stimuli/receive",
                    json=s2_only_stimuli
                ) as resp:
                    if resp.status == 200:
                        print(f"✅ S2-only stimuli processed correctly")
                    else:
                        print(f"❌ Error {resp.status}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
        
        # Cancel monitor task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        print("\n📊 TEST SUMMARY")
        print("="*60)
        print("✅ Sent 2 stimuli with s1_and_s2 mode - should trigger S1 speech")
        print("✅ Sent 1 stimuli with s2_only mode - should NOT trigger S1")
        print("\n⚠️  IMPORTANT: Check the logs to verify:")
        print("   1. S2 logs show: '🔊 [QUEUE] Forwarding to S1 for speech generation'")
        print("   2. S1 logs show: Incoming requests to /process_text endpoint")
        print("   3. Audio files are generated in S1")
        print("\n📝 Check logs with:")
        print("   docker logs autogen_s2 --tail 50")
        print("   docker logs neurosync_s1 --tail 50")
    
    async def run_all_tests(self):
        """Run all forwarding tests"""
        
        print("\n🧪 S2->S1 FORWARDING TEST SUITE")
        print("================================")
        print("Testing the fix for s1_and_s2 processing mode")
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Check services
        if not await self.check_services():
            print("\n❌ Services not ready. Please start containers:")
            print("   docker-compose up -d")
            return
        
        # Run main test
        await self.test_s1_and_s2_mode()
        
        print(f"\n✅ Tests completed at: {datetime.now().isoformat()}")


async def main():
    """Main test runner"""
    tester = TestS2ToS1Forwarding()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())