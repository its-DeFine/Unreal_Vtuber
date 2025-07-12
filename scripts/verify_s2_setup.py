#!/usr/bin/env python3
"""
Verify S2 Setup
===============

Quick verification that S2 teams are properly configured.
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime


async def check_autogen_config(session):
    """Check AutoGen S2 configuration."""
    print("\n🔧 AutoGen S2 Configuration Check")
    print("-" * 40)
    
    try:
        # Check health endpoint
        async with session.get("http://localhost:8200/health") as response:
            if response.status == 200:
                data = await response.json()
                
                # Check S2 teams status
                if "s2_teams_status" in data:
                    s2_status = data["s2_teams_status"]
                    print(f"✅ S2 Teams Enabled: {s2_status.get('enabled')}")
                    print(f"✅ Queue Consumer: {s2_status.get('queue_consumer')}")
                    print(f"✅ Team Manager: {s2_status.get('team_manager')}")
                    print(f"✅ Orchestrator: {s2_status.get('orchestrator')}")
                    print(f"✅ Queue File: {s2_status.get('queue_file')}")
                    
                    # Check queue stats if available
                    if "queue_stats" in s2_status:
                        stats = s2_status["queue_stats"]
                        print(f"\n📊 Queue Statistics:")
                        print(f"   Batches Processed: {stats.get('batches_processed', 0)}")
                        print(f"   Batches Failed: {stats.get('batches_failed', 0)}")
                        print(f"   Service Running: {stats.get('service_running', False)}")
                        print(f"   Active Teams: {stats.get('active_teams', [])}")
                else:
                    print("❌ S2 teams status not found in health check")
                    print("   This means S2 teams mode is not enabled")
                    
                # Check stimuli processing
                if "stimuli_processing" in data:
                    stim_status = data["stimuli_processing"]
                    print(f"\n📡 Stimuli Processing:")
                    print(f"   Enabled: {stim_status.get('stimuli_processing', False)}")
                    print(f"   Ready: {stim_status.get('ready_for_stimuli', False)}")
                    
        # Check stimuli API endpoint
        print("\n🔌 API Endpoints Check")
        print("-" * 40)
        
        async with session.get("http://localhost:8200/api/stimuli/status") as response:
            if response.status == 200:
                print("✅ /api/stimuli/status endpoint is available")
                status = await response.json()
                print(f"   State: {status.get('autonomous_state')}")
                print(f"   Queue Size: {status.get('queue_size', 0)}")
            else:
                print(f"❌ /api/stimuli/status returned {response.status}")
                
    except Exception as e:
        print(f"❌ Error checking AutoGen: {e}")


async def check_graphflow_routing(session):
    """Test GraphFlow routing decisions."""
    print("\n🚦 GraphFlow Routing Check")
    print("-" * 40)
    
    test_cases = [
        {
            "name": "S2-only routing",
            "stimuli": {
                "content": "Analyze market trends",
                "metadata": {"force_s2": True}
            },
            "expected": "ANALYSIS_ONLY"
        },
        {
            "name": "S1-only routing", 
            "stimuli": {
                "content": "Say hello",
                "metadata": {"force_s1": True}
            },
            "expected": "AVATAR_ONLY"
        },
        {
            "name": "Default routing",
            "stimuli": {
                "content": "Explain quantum computing"
            },
            "expected": "AVATAR_AND_ANALYSIS"
        }
    ]
    
    for test in test_cases:
        try:
            async with session.post(
                "http://localhost:8000/api/v1/stimuli/submit",
                json=test["stimuli"]
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    decision = result.get("decision", "UNKNOWN")
                    status = "✅" if decision == test["expected"] else "❌"
                    print(f"{status} {test['name']}: {decision}")
                else:
                    print(f"❌ {test['name']}: HTTP {response.status}")
        except Exception as e:
            print(f"❌ {test['name']}: {e}")


async def check_queue_files():
    """Check queue file system."""
    print("\n📁 Queue File System Check")
    print("-" * 40)
    
    queue_dir = "/tmp/s2_queue"
    queue_file = f"{queue_dir}/s2_processing_queue.json"
    processed_file = f"{queue_dir}/s2_processed_stimuli.json"
    
    # Check directory
    if os.path.exists(queue_dir):
        print(f"✅ Queue directory exists: {queue_dir}")
        
        # Check permissions
        if os.access(queue_dir, os.W_OK):
            print("✅ Queue directory is writable")
        else:
            print("❌ Queue directory is not writable")
    else:
        print(f"❌ Queue directory missing: {queue_dir}")
        
    # Check queue file
    if os.path.exists(queue_file):
        print(f"✅ Queue file exists: {queue_file}")
        try:
            with open(queue_file, 'r') as f:
                data = json.load(f)
            print(f"   Items in queue: {len(data)}")
        except Exception as e:
            print(f"   Error reading queue: {e}")
    else:
        print(f"ℹ️  Queue file not yet created: {queue_file}")
        
    # Check processed file
    if os.path.exists(processed_file):
        print(f"✅ Processed file exists: {processed_file}")
        try:
            with open(processed_file, 'r') as f:
                data = json.load(f)
            print(f"   Processed items: {len(data)}")
        except Exception as e:
            print(f"   Error reading processed: {e}")
    else:
        print(f"ℹ️  Processed file not yet created: {processed_file}")


async def main():
    print("🔍 S2 Teams Setup Verification")
    print("="*50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiohttp.ClientSession() as session:
        # Check services
        print("\n🏥 Service Health Check")
        print("-" * 40)
        
        services = [
            ("GraphFlow", "http://localhost:8000/health"),
            ("NeuroSync S1", "http://localhost:5001/health"),
            ("AutoGen S2", "http://localhost:8200/health")
        ]
        
        all_healthy = True
        for name, url in services:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        print(f"✅ {name} is healthy")
                    else:
                        print(f"❌ {name} returned {response.status}")
                        all_healthy = False
            except Exception as e:
                print(f"❌ {name} is not reachable: {e}")
                all_healthy = False
        
        if not all_healthy:
            print("\n⚠️  Some services are not healthy!")
            print("Please ensure all containers are running:")
            print("  docker-compose -f docker-compose.all.yml up -d")
            return
        
        # Detailed checks
        await check_autogen_config(session)
        await check_graphflow_routing(session)
        await check_queue_files()
        
        print("\n" + "="*50)
        print("✅ Verification complete!")
        print("\nNext steps:")
        print("1. Run the comprehensive test: python3 scripts/test_all_routing_scenarios.py")
        print("2. Monitor queue processing: python3 scripts/monitor_s2_queue.py")


if __name__ == "__main__":
    asyncio.run(main())