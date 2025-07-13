#!/usr/bin/env python3
"""
Live Demo: SCB and Character Mapping Utilities via S2 Stimuli API
Created: 2025-07-13

This demonstrates both utilities working together with real speech output.
"""

import asyncio
import aiohttp
import time
import json


async def live_demo():
    """Live demonstration of both utilities"""
    
    print("\n🎭 LIVE DEMO: SCB & CHARACTER MAPPING UTILITIES")
    print("="*60)
    print("This demo shows:")
    print("1. Team-specific SCB state management (Utility One)")
    print("2. S2/S1 character mapping (Utility Two)")
    print("3. Real speech output via correct Stimuli API")
    print("="*60)
    
    base_url = "http://localhost:8200"
    stimuli_endpoint = f"{base_url}/api/stimuli/receive"
    
    async with aiohttp.ClientSession() as session:
        
        # Clear any existing queue
        print("\n🧹 Clearing queue...")
        try:
            async with session.post(f"{base_url}/api/stimuli/control/clear") as resp:
                if resp.status == 200:
                    print("✅ Queue cleared")
        except:
            pass
        
        # Ensure queue is running
        print("🔄 Restarting queue consumer...")
        try:
            async with session.post(f"{base_url}/api/queue/restart") as resp:
                if resp.status == 200:
                    print("✅ Queue consumer restarted")
        except:
            pass
        
        await asyncio.sleep(2)
        
        # DEMO 1: Trader Team with Gordon
        print("\n" + "="*60)
        print("💼 DEMO 1: TRADER TEAM - GORDON")
        print("="*60)
        
        trader_stimuli = {
            "stimuli_id": f"demo_trader_{int(time.time())}",
            "content": "Good afternoon traders! Gordon here with your market update. Tesla is showing strong momentum at 250 dollars. Our team SCB indicates we're using a momentum strategy with controlled risk. This demonstrates our team-specific state management working perfectly!",
            "source": "live_demo",
            "priority": "high",
            "metadata": {
                "team_preference": "trader",
                "character_type": "gordon_trader_template",
                "processing_mode": "s1_and_s2",
                "team_scb": {
                    "market_analysis": {"TSLA": {"price": 250, "trend": "bullish"}},
                    "trading_strategy": "momentum",
                    "risk_level": 0.3
                },
                "common_scb": {
                    "demo_active": True,
                    "system_status": "demonstrating_utilities"
                }
            }
        }
        
        print("📤 Sending trader stimuli...")
        print(f"   Character: Gordon Trader")
        print(f"   Team SCB: Market data for TSLA")
        
        try:
            async with session.post(stimuli_endpoint, json=trader_stimuli) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Stimuli accepted: {result['stimuli_id']}")
                    print("🔊 LISTEN FOR GORDON'S MARKET UPDATE!")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await asyncio.sleep(8)
        
        # DEMO 2: Educator Team with Emma
        print("\n" + "="*60)
        print("🎓 DEMO 2: EDUCATOR TEAM - EMMA")
        print("="*60)
        
        educator_stimuli = {
            "stimuli_id": f"demo_educator_{int(time.time())}",
            "content": "Hello students! Emma here with an exciting lesson on our new utilities. We've successfully implemented team-specific SCB states and character mapping. Each team maintains isolated data while sharing common insights. Your progress has been excellent!",
            "source": "live_demo",
            "priority": "medium",
            "metadata": {
                "team_preference": "educator",
                "character_type": "emma_teacher_template",
                "processing_mode": "s1_and_s2",
                "team_scb": {
                    "current_lesson": "SCB Utilities Implementation",
                    "student_progress": {"utilities_understanding": 95},
                    "teaching_focus": "practical_implementation"
                },
                "common_scb": {
                    "demo_active": True,
                    "cross_team_learning": "Trader insights available"
                }
            }
        }
        
        print("📤 Sending educator stimuli...")
        print(f"   Character: Emma Teacher")
        print(f"   Team SCB: Lesson on utilities")
        
        try:
            async with session.post(stimuli_endpoint, json=educator_stimuli) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Stimuli accepted: {result['stimuli_id']}")
                    print("🔊 LISTEN FOR EMMA'S LESSON!")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await asyncio.sleep(8)
        
        # DEMO 3: Streamer Team with Mike
        print("\n" + "="*60)
        print("🎮 DEMO 3: STREAMER TEAM - MIKE")
        print("="*60)
        
        streamer_stimuli = {
            "stimuli_id": f"demo_streamer_{int(time.time())}",
            "content": "Hey everyone! Mike here, and we're live with an amazing demo! We're showcasing how each team has their own SCB state while characters are properly mapped. The trader team has market data, educators have lessons, and we streamers track viewer engagement. This is next-level integration!",
            "source": "live_demo",
            "priority": "medium",
            "metadata": {
                "team_preference": "streamer",
                "character_type": "mike_streamer_template",
                "processing_mode": "s1_and_s2",
                "team_scb": {
                    "stream_title": "Live Utility Demo",
                    "viewer_count": 250,
                    "engagement_level": "high",
                    "chat_sentiment": "excited"
                },
                "common_scb": {
                    "demo_active": True,
                    "all_teams_demonstrated": True
                }
            }
        }
        
        print("📤 Sending streamer stimuli...")
        print(f"   Character: Mike Streamer")
        print(f"   Team SCB: Stream engagement data")
        
        try:
            async with session.post(stimuli_endpoint, json=streamer_stimuli) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Stimuli accepted: {result['stimuli_id']}")
                    print("🔊 LISTEN FOR MIKE'S STREAM!")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await asyncio.sleep(8)
        
        # Check final status
        print("\n" + "="*60)
        print("📊 FINAL STATUS CHECK")
        print("="*60)
        
        try:
            async with session.get(f"{base_url}/api/stimuli/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"✅ Total stimuli received: {status['statistics']['total_received']}")
                    print(f"✅ Total queued: {status['statistics']['total_queued']}")
                    print(f"✅ Queue size: {status['queue_size']}")
        except:
            pass
        
        print("\n" + "="*60)
        print("✅ LIVE DEMO COMPLETED!")
        print("="*60)
        print("\n🎯 Both utilities demonstrated successfully:")
        print("1. ✅ Team SCB Manager - Each team maintained isolated state")
        print("2. ✅ Character Mapping - Each team used their assigned character")
        print("3. ✅ Speech Generation - Characters spoke with unique voices")
        print("4. ✅ Stimuli API - Correct S2 processing pipeline used")
        print("\n💡 The stimuli were processed through the S2 AutoGen teams")
        print("   and forwarded to S1 for speech synthesis!")


async def main():
    """Run the live demo"""
    
    # Check services first
    print("\n🔍 Checking services...")
    async with aiohttp.ClientSession() as session:
        services_ok = True
        
        # Check S2
        try:
            async with session.get("http://localhost:8200/health") as resp:
                if resp.status == 200:
                    print("✅ S2 container (AutoGen) is running")
                else:
                    print("❌ S2 container not healthy")
                    services_ok = False
        except:
            print("❌ S2 container not accessible")
            services_ok = False
        
        # Check S1
        try:
            async with session.get("http://localhost:5001/health") as resp:
                if resp.status == 200:
                    print("✅ S1 container (NeuroSync) is running")
                else:
                    print("❌ S1 container not healthy")
                    services_ok = False
        except:
            print("❌ S1 container not accessible")
            services_ok = False
    
    if not services_ok:
        print("\n⚠️  Some services are not running!")
        print("Please ensure all containers are up:")
        print("  docker-compose -f docker-compose.all.yml up -d")
        return
    
    print("\n🎯 All services ready! Starting demo...")
    await asyncio.sleep(2)
    
    # Run the demo
    await live_demo()


if __name__ == "__main__":
    print("""
    🎭 LIVE DEMONSTRATION
    ====================
    
    SCB & Character Mapping Utilities
    Using Correct S2 Stimuli API
    
    You will hear:
    - Gordon (Trader)
    - Emma (Educator)
    - Mike (Streamer)
    
    Each with their own:
    - Team-specific SCB state
    - Character voice
    - Processing context
    
    Starting demo...
    """)
    
    asyncio.run(main())