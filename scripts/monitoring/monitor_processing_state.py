#!/usr/bin/env python3
"""
Processing State Monitor for S2 System
======================================

Real-time monitoring of System 2 processing state to help debug
stimuli processing issues and track system capacity.

Created: 2025-07-14
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any
import httpx
import argparse


class ProcessingStateMonitor:
    """Monitor System 2 processing state in real-time"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.endpoints = {
            "processing_state": f"{base_url}/api/stimuli/processing-state",
            "orchestrator_status": f"{base_url}/api/stimuli/status",
            "queue_health": f"{base_url}/api/queue/health"
        }
        self.previous_state = None
        
    async def fetch_processing_state(self) -> Dict[str, Any]:
        """Fetch current processing state from API"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.endpoints["processing_state"])
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def fetch_orchestrator_status(self) -> Dict[str, Any]:
        """Fetch orchestrator status"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.endpoints["orchestrator_status"])
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def fetch_queue_health(self) -> Dict[str, Any]:
        """Fetch queue health information"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.endpoints["queue_health"])
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds is None:
            return "N/A"
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def print_state_change(self, current_state: Dict[str, Any]):
        """Print state change notification"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if current_state.get("error"):
            print(f"🔴 [{timestamp}] ERROR: {current_state['error']}")
            return
        
        is_processing = current_state.get("is_processing", False)
        stimuli_id = current_state.get("current_stimuli_id")
        duration = current_state.get("processing_duration_seconds")
        
        if is_processing:
            print(f"🟡 [{timestamp}] PROCESSING: {stimuli_id} ({self.format_duration(duration)})")
        else:
            print(f"🟢 [{timestamp}] IDLE: Ready to accept new stimuli")
    
    def print_detailed_status(self, processing_state: Dict[str, Any], 
                            orchestrator_status: Dict[str, Any],
                            queue_health: Dict[str, Any]):
        """Print detailed status information"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n📊 [{timestamp}] DETAILED STATUS")
        print("=" * 50)
        
        # Processing State
        if processing_state.get("error"):
            print(f"🔴 Processing State: ERROR - {processing_state['error']}")
        else:
            is_processing = processing_state.get("is_processing", False)
            stimuli_id = processing_state.get("current_stimuli_id")
            duration = processing_state.get("processing_duration_seconds")
            can_accept = processing_state.get("can_accept_new_stimuli", False)
            
            status_icon = "🟡" if is_processing else "🟢"
            print(f"{status_icon} Processing State: {'BUSY' if is_processing else 'IDLE'}")
            print(f"   Current Stimuli: {stimuli_id or 'None'}")
            print(f"   Duration: {self.format_duration(duration)}")
            print(f"   Can Accept New: {'Yes' if can_accept else 'No'}")
            
            # Queue Consumer Stats
            consumer_stats = processing_state.get("queue_consumer_stats", {})
            print(f"   Processed: {consumer_stats.get('processed', 0)}")
            print(f"   Failed: {consumer_stats.get('failed', 0)}")
            print(f"   Teams: {', '.join(consumer_stats.get('teams_available', []))}")
            print(f"   Task Status: {consumer_stats.get('task_status', 'unknown')}")
        
        # Orchestrator Status
        if orchestrator_status.get("error"):
            print(f"🔴 Orchestrator: ERROR - {orchestrator_status['error']}")
        else:
            queue_size = orchestrator_status.get("queue_size", 0)
            autonomous_state = orchestrator_status.get("autonomous_state", "unknown")
            print(f"📝 Orchestrator: {autonomous_state}")
            print(f"   Queue Size: {queue_size}")
            
            stats = orchestrator_status.get("statistics", {})
            print(f"   Total Received: {stats.get('total_received', 0)}")
            print(f"   Total Queued: {stats.get('total_queued', 0)}")
            print(f"   Total Errors: {stats.get('total_errors', 0)}")
        
        # Queue Health
        if queue_health.get("error"):
            print(f"🔴 Queue Health: ERROR - {queue_health['error']}")
        else:
            overall_health = queue_health.get("overall_health", "unknown")
            consumer_running = queue_health.get("consumer_running", False)
            task_status = queue_health.get("task_status", "unknown")
            teams_count = queue_health.get("teams_count", 0)
            
            health_icon = "🟢" if overall_health == "healthy" else "🟡" if overall_health == "degraded" else "🔴"
            print(f"{health_icon} Queue Health: {overall_health}")
            print(f"   Consumer Running: {'Yes' if consumer_running else 'No'}")
            print(f"   Task Status: {task_status}")
            print(f"   Teams Count: {teams_count}")
        
        print("=" * 50)
    
    async def monitor_realtime(self, interval: float = 2.0, detailed: bool = False):
        """Monitor processing state in real-time"""
        print(f"🔍 Starting real-time monitoring (interval: {interval}s)")
        print(f"📡 Monitoring: {self.base_url}")
        
        if detailed:
            print("📊 Detailed mode enabled")
        
        print("\nPress Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                current_state = await self.fetch_processing_state()
                
                # Check for state changes
                if self.previous_state is None or current_state != self.previous_state:
                    self.print_state_change(current_state)
                    self.previous_state = current_state
                
                # Print detailed status if requested
                if detailed:
                    orchestrator_status = await self.fetch_orchestrator_status()
                    queue_health = await self.fetch_queue_health()
                    self.print_detailed_status(current_state, orchestrator_status, queue_health)
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
    
    async def check_once(self):
        """Check processing state once and exit"""
        processing_state = await self.fetch_processing_state()
        orchestrator_status = await self.fetch_orchestrator_status()
        queue_health = await self.fetch_queue_health()
        
        self.print_detailed_status(processing_state, orchestrator_status, queue_health)


async def main():
    parser = argparse.ArgumentParser(description="Monitor S2 processing state")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for S2 API (default: http://localhost:8000)")
    parser.add_argument("--interval", type=float, default=2.0,
                       help="Monitoring interval in seconds (default: 2.0)")
    parser.add_argument("--detailed", action="store_true",
                       help="Show detailed status information")
    parser.add_argument("--once", action="store_true",
                       help="Check once and exit (no continuous monitoring)")
    
    args = parser.parse_args()
    
    monitor = ProcessingStateMonitor(args.url)
    
    if args.once:
        await monitor.check_once()
    else:
        await monitor.monitor_realtime(args.interval, args.detailed)


if __name__ == "__main__":
    asyncio.run(main())