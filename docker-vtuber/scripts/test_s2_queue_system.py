#!/usr/bin/env python3
"""
Test S2 Queue System
===================

Tests the complete S2 queue processing pipeline:
1. Send stimuli to GraphFlow
2. Verify routing decision
3. Check queue file creation
4. Monitor queue processing
"""

import os
import sys
import json
import time
import asyncio
import aiohttp
import argparse
from datetime import datetime
from pathlib import Path


async def check_service_health(session, service_name, url):
    """Check if a service is healthy."""
    try:
        async with session.get(url, timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ {service_name} is healthy: {data}")
                return True
            else:
                print(f"❌ {service_name} returned status {response.status}")
                return False
    except Exception as e:
        print(f"❌ {service_name} health check failed: {e}")
        return False


async def send_s2_stimuli(session, content, character_id=None):
    """Send stimuli targeted for S2 processing."""
    
    graphflow_url = "http://localhost:8000/api/v1/stimuli/submit"
    
    # Create stimuli with S2-specific metadata
    stimuli_data = {
        "content": content,
        "source": "test_script",
        "priority": "high",
        "metadata": {
            "force_s2": True,
            "target_systems": ["s2"],
            "s2_teams_mode": True,
            "test_timestamp": datetime.now().isoformat()
        }
    }
    
    if character_id:
        stimuli_data["metadata"]["character_id"] = character_id
    
    print(f"\n📤 Sending S2 stimuli: {content[:50]}...")
    print(f"   Metadata: {stimuli_data['metadata']}")
    
    try:
        async with session.post(graphflow_url, json=stimuli_data, timeout=10) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ GraphFlow response: {result}")
                return result
            else:
                text = await response.text()
                print(f"❌ GraphFlow error: {response.status} - {text}")
                return None
    except Exception as e:
        print(f"❌ Failed to send stimuli: {e}")
        return None


async def check_queue_file(queue_path="/tmp/s2_queue/s2_processing_queue.json"):
    """Check the contents of the S2 queue file."""
    
    queue_file = Path(queue_path)
    
    print(f"\n📁 Checking queue file: {queue_file}")
    
    if not queue_file.exists():
        print(f"❌ Queue file does not exist!")
        return []
    
    try:
        with open(queue_file, 'r') as f:
            queue_data = json.load(f)
        
        print(f"✅ Queue has {len(queue_data)} items")
        
        for i, item in enumerate(queue_data[-3:], 1):  # Show last 3 items
            print(f"\n   Item {i}:")
            print(f"   - Prompt: {item.get('prompt', '')[:50]}...")
            print(f"   - Timestamp: {item.get('timestamp', 'N/A')}")
            print(f"   - Source: {item.get('source', 'N/A')}")
            print(f"   - Mode: {item.get('processing_mode', 'N/A')}")
            if item.get('metadata', {}).get('character_id'):
                print(f"   - Character: {item['metadata']['character_id']}")
        
        return queue_data
        
    except Exception as e:
        print(f"❌ Error reading queue file: {e}")
        return []


async def monitor_queue_processing(session, duration=30):
    """Monitor queue processing for a specified duration."""
    
    print(f"\n🔄 Monitoring queue processing for {duration} seconds...")
    
    autogen_status_url = "http://localhost:8200/api/stimuli/status"
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Check AutoGen status
        try:
            async with session.get(autogen_status_url, timeout=5) as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"\n⏱️ [{int(time.time() - start_time)}s] AutoGen Status:")
                    print(f"   - State: {status.get('autonomous_state', 'unknown')}")
                    print(f"   - Queue size: {status.get('queue_size', 0)}")
                    print(f"   - Stats: {status.get('statistics', {})}")
        except Exception as e:
            print(f"   ⚠️ Could not get AutoGen status: {e}")
        
        # Check queue file
        queue_data = await check_queue_file()
        
        # Check processed file
        processed_file = Path("/tmp/s2_queue/s2_processed_stimuli.json")
        if processed_file.exists():
            try:
                with open(processed_file, 'r') as f:
                    processed = json.load(f)
                print(f"   - Processed items: {len(processed)}")
                if processed:
                    last_processed = processed[-1]
                    print(f"   - Last processed: {last_processed.get('timestamp', 'N/A')}")
                    print(f"   - Status: {last_processed.get('status', 'N/A')}")
            except:
                pass
        
        await asyncio.sleep(5)


async def test_character_specific_teams(session):
    """Test different character-specific teams."""
    
    print("\n🎭 Testing Character-Specific Teams")
    print("="*50)
    
    character_tests = [
        {
            "character_id": "dr._house_doctor_template",
            "stimuli": "What's the current Bitcoin price trend and should I invest?",
            "expected_team": "TRADER"
        },
        {
            "character_id": "weatherman_template", 
            "stimuli": "How can I grow my streaming audience and improve engagement?",
            "expected_team": "STREAMER"
        },
        {
            "character_id": "emma_teacher_template",
            "stimuli": "Explain quantum computing in simple terms for beginners",
            "expected_team": "TEACHER"
        }
    ]
    
    for test in character_tests:
        print(f"\n🧪 Testing {test['expected_team']} team with character: {test['character_id']}")
        
        # Send stimuli
        result = await send_s2_stimuli(
            session, 
            test['stimuli'], 
            character_id=test['character_id']
        )
        
        if result:
            print(f"   Expected team: {test['expected_team']}")
            
            # Wait a bit for queue processing
            await asyncio.sleep(2)
            
            # Check queue
            await check_queue_file()


async def main():
    parser = argparse.ArgumentParser(description="Test S2 Queue System")
    parser.add_argument("--monitor-time", type=int, default=30, 
                       help="Time to monitor queue processing (seconds)")
    parser.add_argument("--test-characters", action="store_true",
                       help="Test character-specific teams")
    args = parser.parse_args()
    
    async with aiohttp.ClientSession() as session:
        print("🚀 S2 Queue System Test")
        print("="*50)
        
        # Check service health
        print("\n📋 Checking Service Health")
        graphflow_healthy = await check_service_health(
            session, "GraphFlow", "http://localhost:8000/health"
        )
        autogen_healthy = await check_service_health(
            session, "AutoGen", "http://localhost:8200/health"
        )
        
        if not graphflow_healthy:
            print("\n❌ GraphFlow is not healthy. Please ensure it's running.")
            return
        
        # Test basic S2 stimuli
        print("\n📤 Testing Basic S2 Stimuli")
        result = await send_s2_stimuli(
            session,
            "Analyze the implications of quantum computing on cryptocurrency security"
        )
        
        # Check queue
        await asyncio.sleep(2)
        await check_queue_file()
        
        # Test character-specific teams if requested
        if args.test_characters:
            await test_character_specific_teams(session)
        
        # Monitor processing
        await monitor_queue_processing(session, args.monitor_time)
        
        print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())