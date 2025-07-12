#!/usr/bin/env python3
"""
Monitor S2 Queue Status
======================

Real-time monitoring of the S2 queue system.
"""

import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path


def check_queue_files():
    """Check the S2 queue files."""
    
    queue_file = Path("/tmp/s2_queue/s2_processing_queue.json")
    processed_file = Path("/tmp/s2_queue/s2_processed_stimuli.json")
    
    print(f"\n📁 Queue Files Status ({datetime.now().strftime('%H:%M:%S')})")
    print("-" * 50)
    
    # Check queue file
    if queue_file.exists():
        try:
            with open(queue_file, 'r') as f:
                queue_data = json.load(f)
            print(f"✅ Queue file: {len(queue_data)} pending items")
            
            if queue_data:
                latest = queue_data[-1]
                print(f"   Latest: {latest.get('timestamp', 'N/A')} - {latest.get('prompt', '')[:50]}...")
                
        except Exception as e:
            print(f"❌ Error reading queue: {e}")
    else:
        print("❌ Queue file does not exist")
    
    # Check processed file
    if processed_file.exists():
        try:
            with open(processed_file, 'r') as f:
                processed_data = json.load(f)
            print(f"✅ Processed file: {len(processed_data)} completed items")
            
            if processed_data:
                latest = processed_data[-1]
                print(f"   Latest: {latest.get('timestamp', 'N/A')} - Status: {latest.get('status', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error reading processed: {e}")
    else:
        print("❓ Processed file does not exist")


async def check_autogen_status(session):
    """Check AutoGen service status."""
    
    try:
        # Check health
        async with session.get("http://localhost:8200/health", timeout=5) as response:
            if response.status == 200:
                health = await response.json()
                print(f"\n🤖 AutoGen Health: {health.get('status', 'unknown')}")
                
                if health.get('s2_teams_status'):
                    s2_status = health['s2_teams_status']
                    print(f"   S2 Teams: {s2_status.get('enabled', False)}")
                    print(f"   Queue Consumer: {s2_status.get('queue_consumer', False)}")
                    print(f"   Team Manager: {s2_status.get('team_manager', False)}")
        
        # Check stimuli status
        async with session.get("http://localhost:8200/api/stimuli/status", timeout=5) as response:
            if response.status == 200:
                status = await response.json()
                print(f"\n📊 Stimuli Status:")
                print(f"   State: {status.get('autonomous_state', 'unknown')}")
                print(f"   Queue Size: {status.get('queue_size', 0)}")
                stats = status.get('statistics', {})
                if stats:
                    print(f"   Received: {stats.get('total_received', 0)}")
                    print(f"   Queued: {stats.get('total_queued', 0)}")
                    print(f"   Errors: {stats.get('total_errors', 0)}")
                    
    except Exception as e:
        print(f"\n⚠️ Could not check AutoGen status: {e}")


async def monitor_loop(duration=None):
    """Main monitoring loop."""
    
    print("🔍 S2 Queue Monitor")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # Check queue files
                check_queue_files()
                
                # Check AutoGen status
                await check_autogen_status(session)
                
                # Show uptime
                uptime = int(time.time() - start_time)
                print(f"\n⏱️ Monitoring for {uptime}s")
                
                # Check duration limit
                if duration and uptime >= duration:
                    print("\n✅ Monitoring duration reached")
                    break
                
                # Wait before next check
                await asyncio.sleep(5)
                print("\n" + "="*50)
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitoring stopped")
                break
            except Exception as e:
                print(f"\n❌ Monitor error: {e}")
                await asyncio.sleep(5)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor S2 Queue Status")
    parser.add_argument("--duration", type=int, help="Monitor duration in seconds")
    args = parser.parse_args()
    
    asyncio.run(monitor_loop(args.duration))


if __name__ == "__main__":
    main()