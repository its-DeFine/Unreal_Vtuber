#!/usr/bin/env python3
"""
Basic S2 Queue Test
==================

Simple test to verify S2 queue functionality.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_s2_queue():
    """Test basic S2 queue functionality."""
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Basic S2 Queue Test")
        print("="*50)
        
        # 1. Check AutoGen health
        print("\n1. Checking AutoGen health...")
        try:
            async with session.get("http://localhost:8200/health") as response:
                if response.status == 200:
                    data = await response.json()
                    if "s2_teams_status" in data:
                        s2_status = data["s2_teams_status"]
                        print(f"   ✅ S2 Teams Enabled: {s2_status.get('enabled')}")
                        print(f"   ✅ Queue Consumer: {s2_status.get('queue_consumer')}")
                        print(f"   ✅ Orchestrator: {s2_status.get('orchestrator')}")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Send direct S2 stimuli
        print("\n2. Sending stimuli directly to S2 API...")
        try:
            s2_data = {
                "stimuli_id": "test_basic_001",
                "content": "Test basic S2 processing",
                "source": "basic_test",
                "priority": "high"
            }
            
            async with session.post(
                "http://localhost:8200/api/stimuli/receive",
                json=s2_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ S2 API Response: {result.get('agent_decision')}")
                    print(f"   Response: {result.get('response_content')}")
                else:
                    text = await response.text()
                    print(f"   ❌ S2 API Error {response.status}: {text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Send via GraphFlow
        print("\n3. Sending S2 stimuli via GraphFlow...")
        try:
            graphflow_data = {
                "content": "Analyze market trends for testing",
                "source": "test",
                "metadata": {
                    "force_s2": True,
                    "target_systems": ["s2"]
                }
            }
            
            async with session.post(
                "http://localhost:8000/api/v1/stimuli/submit",
                json=graphflow_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ GraphFlow Decision: {result.get('decision')}")
                    print(f"   Message: {result.get('message')}")
                else:
                    print(f"   ❌ GraphFlow Error: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Check queue status
        print("\n4. Checking queue status...")
        await asyncio.sleep(5)  # Wait for processing
        
        try:
            async with session.get("http://localhost:8200/api/stimuli/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"   Queue Size: {status.get('queue_size', 0)}")
                    stats = status.get('statistics', {})
                    print(f"   Total Queued: {stats.get('total_queued', 0)}")
                    print(f"   Total Errors: {stats.get('total_errors', 0)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "="*50)
        print("✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_s2_queue())