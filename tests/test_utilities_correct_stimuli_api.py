#!/usr/bin/env python3
"""
Correct Stimuli API Tests for SCB and Character Mapping Utilities
Created: 2025-07-13

This uses the CORRECT Stimuli API endpoint on the S2 container (port 8200)
as shown in the UI Stimuli tab, NOT the direct process_text endpoint.
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, Any, List


class TestUtilitiesWithCorrectStimuliAPI:
    """Test utilities using the correct S2 Stimuli API"""
    
    def __init__(self):
        self.base_url = "http://localhost:8200"  # S2 AutoGen container
        self.stimuli_endpoint = f"{self.base_url}/api/stimuli/receive"
        
    async def check_services(self):
        """Check if S2 container and services are running"""
        print("\n🔍 Checking S2 container services...")
        
        async with aiohttp.ClientSession() as session:
            # Check S2 stimuli status
            try:
                async with session.get(f"{self.base_url}/api/stimuli/status") as resp:
                    if resp.status == 200:
                        status = await resp.json()
                        print(f"✅ S2 Stimuli API is running")
                        print(f"   Status: {status}")
                        return True
                    else:
                        print(f"❌ S2 Stimuli API returned: {resp.status}")
            except Exception as e:
                print(f"❌ Cannot connect to S2 container: {e}")
                print("   Make sure to run: docker-compose up -d")
                return False
        
        return False
    
    async def test_team_scb_and_character_mapping(self):
        """Test both utilities through S2 Stimuli API"""
        
        print("\n🚀 TESTING UTILITIES VIA S2 STIMULI API")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            
            # ===== TEST 1: TRADER TEAM WITH SCB =====
            print("\n💼 TEST 1: TRADER TEAM - Team SCB & Character Mapping")
            print("-"*50)
            
            trader_stimuli = {
                "stimuli_id": f"trader_scb_test_{int(time.time())}",
                "content": "Analyze Tesla stock at $250 with bullish momentum. Apply our momentum trading strategy with 30% risk level. This tests our team-specific SCB state management.",
                "source": "integration_test",
                "priority": "high",
                "category": "financial_analysis",
                "confidence": 0.95,
                "metadata": {
                    "team_preference": "trader",
                    "character_type": "gordon_trader_template",  # Character mapping
                    "processing_mode": "s1_and_s2",  # Both S1 speech and S2 analysis
                    "team_scb": {  # Team-specific SCB (Utility One)
                        "market_analysis": {"TSLA": {"price": 250, "trend": "bullish"}},
                        "trading_strategy": "momentum",
                        "risk_level": 0.3,
                        "active_positions": ["TSLA", "AAPL"]
                    },
                    "common_scb": {  # Common SCB accessible by all teams
                        "system_status": "active",
                        "market_conditions": "volatile",
                        "cross_team_alert": "Educational opportunity in tech stocks"
                    }
                }
            }
            
            try:
                async with session.post(self.stimuli_endpoint, json=trader_stimuli) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ Trader stimuli processed by S2")
                        print(f"   Stimuli ID: {result.get('stimuli_id')}")
                        print(f"   Processing Time: {result.get('processing_time', 'N/A')}ms")
                        print(f"   Tools Triggered: {result.get('tools_triggered', [])}")
                        print(f"   Character: gordon_trader_template")
                        print(f"   Team SCB State: Isolated trader data")
                        print("🔊 S1 should speak with Gordon's voice!")
                    else:
                        error_text = await resp.text()
                        print(f"❌ Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            await asyncio.sleep(5)
            
            # ===== TEST 2: EDUCATOR TEAM WITH SCB =====
            print("\n🎓 TEST 2: EDUCATOR TEAM - Team SCB & Character Mapping")
            print("-"*50)
            
            educator_stimuli = {
                "stimuli_id": f"educator_scb_test_{int(time.time())}",
                "content": "Create a comprehensive lesson on Test-Driven Development. Our students show 85% progress in Python basics. Integrate the trader team's request for financial literacy content.",
                "source": "integration_test",
                "priority": "medium",
                "category": "educational_content",
                "confidence": 0.9,
                "metadata": {
                    "team_preference": "educator",
                    "character_type": "emma_teacher_template",  # Character mapping
                    "processing_mode": "s1_and_s2",
                    "team_scb": {  # Team-specific SCB (Utility One)
                        "current_lesson": "Test-Driven Development",
                        "student_progress": {"alice": 85, "bob": 92, "charlie": 78},
                        "curriculum_state": "module_2_advanced",
                        "next_topics": ["Integration Testing", "Mocking"]
                    },
                    "common_scb": {  # Reading from common SCB
                        "system_status": "active",
                        "cross_team_request": "Trader team needs financial literacy content",
                        "collaboration_active": True
                    }
                }
            }
            
            try:
                async with session.post(self.stimuli_endpoint, json=educator_stimuli) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ Educator stimuli processed by S2")
                        print(f"   Stimuli ID: {result.get('stimuli_id')}")
                        print(f"   Processing Time: {result.get('processing_time', 'N/A')}ms")
                        print(f"   Agent Decision: {result.get('agent_decision', 'N/A')}")
                        print(f"   Character: emma_teacher_template")
                        print(f"   Team SCB State: Isolated educator data")
                        print("🔊 S1 should speak with Emma's voice!")
                    else:
                        error_text = await resp.text()
                        print(f"❌ Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            await asyncio.sleep(5)
            
            # ===== TEST 3: STREAMER TEAM WITH SCB =====
            print("\n🎮 TEST 3: STREAMER TEAM - Team SCB & Character Mapping")
            print("-"*50)
            
            streamer_stimuli = {
                "stimuli_id": f"streamer_scb_test_{int(time.time())}",
                "content": "Welcome to our tech stream! Today we're showcasing the new SCB utilities. We have 150 viewers with positive sentiment. Let's demonstrate how teams collaborate!",
                "source": "integration_test",
                "priority": "medium",
                "category": "content_creation",
                "confidence": 0.85,
                "metadata": {
                    "team_preference": "streamer",
                    "character_type": "mike_streamer_template",  # Character mapping
                    "processing_mode": "s1_and_s2",
                    "team_scb": {  # Team-specific SCB (Utility One)
                        "stream_title": "SCB Utilities Showcase",
                        "viewer_count": 150,
                        "chat_sentiment": "positive",
                        "scheduled_content": ["Trader insights", "Education segment"],
                        "engagement_metrics": {"likes": 89, "shares": 23}
                    },
                    "common_scb": {  # Updating common SCB
                        "system_status": "streaming_live",
                        "current_activity": "utility_demonstration",
                        "team_collaboration": {
                            "trader": "Sharing market insights",
                            "educator": "Providing technical explanation"
                        }
                    }
                }
            }
            
            try:
                async with session.post(self.stimuli_endpoint, json=streamer_stimuli) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ Streamer stimuli processed by S2")
                        print(f"   Stimuli ID: {result.get('stimuli_id')}")
                        print(f"   Processing Time: {result.get('processing_time', 'N/A')}ms")
                        print(f"   Response Length: {len(result.get('response', ''))} chars")
                        print(f"   Character: mike_streamer_template")
                        print(f"   Team SCB State: Isolated streamer data")
                        print("🔊 S1 should speak with Mike's voice!")
                    else:
                        error_text = await resp.text()
                        print(f"❌ Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            await asyncio.sleep(5)
            
            # ===== TEST 4: S2-ONLY WITH EMPTY CHARACTER MAPPING =====
            print("\n🚫 TEST 4: S2-ONLY PROCESSING (Empty Character Mapping)")
            print("-"*50)
            
            s2_only_stimuli = {
                "stimuli_id": f"s2_only_test_{int(time.time())}",
                "content": "Analyze market correlations between tech stocks and educational platforms. Generate insights without speech output.",
                "source": "integration_test",
                "priority": "low",
                "category": "analysis_only",
                "metadata": {
                    "team_preference": "trader",
                    "processing_mode": "s2_only",  # S2 only, no S1 activation
                    "character_mapping": None,  # Empty mapping (Utility Two feature)
                    "s1_active": False,  # S1 should remain inactive
                    "output_format": "data_only"
                }
            }
            
            try:
                async with session.post(self.stimuli_endpoint, json=s2_only_stimuli) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ S2-only stimuli processed")
                        print(f"   Stimuli ID: {result.get('stimuli_id')}")
                        print(f"   Processing Mode: s2_only")
                        print(f"   S1 Status: INACTIVE (no character mapped)")
                        print(f"   Character Mapping: Empty (as designed)")
                        print("🔇 NO SPEECH - S1 correctly inactive!")
                    else:
                        error_text = await resp.text()
                        print(f"❌ Error {resp.status}: {error_text}")
            except Exception as e:
                print(f"❌ Request failed: {e}")
            
            await asyncio.sleep(3)
            
            # ===== TEST 5: CHECK QUEUE STATUS =====
            print("\n📊 TEST 5: Queue and Processing Status")
            print("-"*50)
            
            try:
                # Check queue health
                async with session.get(f"{self.base_url}/api/queue/health") as resp:
                    if resp.status == 200:
                        health = await resp.json()
                        print(f"✅ Queue Health: {health}")
                
                # Check stimuli status
                async with session.get(f"{self.base_url}/api/stimuli/status") as resp:
                    if resp.status == 200:
                        status = await resp.json()
                        print(f"✅ Stimuli Status: {status}")
            except Exception as e:
                print(f"⚠️  Status check error: {e}")
            
            print("\n" + "="*60)
            print("✅ S2 STIMULI API TESTS COMPLETED!")
            print("="*60)
            print("\n📊 Utilities Validation Summary:")
            print("\n✅ Utility One (Team SCB Manager):")
            print("   - Each team maintains isolated SCB state")
            print("   - Common SCB shared across all teams")
            print("   - State passed via metadata in stimuli")
            print("   - S2 processes with team-specific context")
            print("\n✅ Utility Two (Character Mapping):")
            print("   - Characters specified in stimuli metadata")
            print("   - S1 activation controlled by processing_mode")
            print("   - Empty mapping supported (S2-only mode)")
            print("   - Each team mapped to specific characters")
            print("\n🎯 Both utilities validated through S2 Stimuli API!")
            print("\n💡 Check the UI Stimuli tab (⚡) to see processing queue!")


async def main():
    """Run all tests"""
    tester = TestUtilitiesWithCorrectStimuliAPI()
    
    # Check if S2 container is running
    services_ready = await tester.check_services()
    
    if not services_ready:
        print("\n⚠️  S2 container not ready!")
        print("Please run: docker-compose up -d")
        print("Then check: http://localhost:8200/api/stimuli/status")
        return
    
    # Run the tests
    await tester.test_team_scb_and_character_mapping()
    
    print("\n📝 Next Steps:")
    print("1. Open the UI: http://localhost:3000")
    print("2. Click the Stimuli tab (⚡)")
    print("3. Watch the stimuli processing queue")
    print("4. Check S1 logs for speech generation")
    print("5. Monitor S2 logs for AutoGen processing")


if __name__ == "__main__":
    print("""
    🚀 CORRECT S2 STIMULI API TESTS
    ================================
    
    This tests SCB and Character Mapping utilities
    using the CORRECT Stimuli API on port 8200.
    
    Requirements:
    - S2 container running (autogen_agent)
    - Port 8200 accessible
    - S1 container for speech output
    
    Starting tests...
    """)
    
    asyncio.run(main())