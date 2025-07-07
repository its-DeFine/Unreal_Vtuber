#!/usr/bin/env python3
"""
GraphFlow External Stimuli System - Transmission and Handling Emulation Demo

This demonstration script simulates real-world stimuli transmission scenarios
to showcase the GraphFlow system's processing capabilities across different
categories, priorities, and sources.

Features demonstrated:
1. Multi-source stimuli generation (admin, users, systems, social media)
2. Real-time WebSocket and HTTP API stimuli submission
3. Priority-based processing validation
4. Emergency scenario handling
5. Concurrent stimuli processing
6. System performance monitoring
7. Graceful degradation simulation

Usage:
    python3 stimuli_emulation_demo.py
"""

import asyncio
import aiohttp
import json
import time
import random
import uuid
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import websockets

@dataclass
class StimuliTemplate:
    """Template for generating realistic stimuli."""
    category: str
    priority: str
    content_templates: List[str]
    source: str
    metadata_template: Dict[str, Any]

@dataclass
class EmulationResult:
    """Result from stimuli emulation."""
    stimuli_id: str
    category: str
    priority: str
    processing_time: float
    success: bool
    decision: str
    method: str  # "http" or "websocket"
    timestamp: datetime

class StimuliEmulationDemo:
    """Comprehensive stimuli transmission and handling emulation."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.ws_url = base_url.replace("http", "ws")
        self.api_key = "test-key-12345"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.session: aiohttp.ClientSession = None
        self.results: List[EmulationResult] = []
        
        # Initialize stimuli templates for realistic simulation
        self._init_stimuli_templates()
    
    def _init_stimuli_templates(self):
        """Initialize realistic stimuli templates for different scenarios."""
        self.stimuli_templates = [
            # Admin Commands
            StimuliTemplate(
                category="DIRECT_ADMIN",
                priority="critical",
                content_templates=[
                    "ADMIN: Change avatar to happy mode",
                    "ADMIN: Start scheduled maintenance",
                    "ADMIN: Enable debug logging",
                    "ADMIN: Update system configuration",
                    "ADMIN: Restart streaming service"
                ],
                source="admin_console",
                metadata_template={"admin_user": True, "authenticated": True}
            ),
            
            # User Interactions
            StimuliTemplate(
                category="USER_INTERACTION",
                priority="medium",
                content_templates=[
                    "Hello! How are you doing today?",
                    "Can you tell me about your latest project?",
                    "What's your favorite programming language?",
                    "Could you explain how AI works?",
                    "Thanks for the help yesterday!"
                ],
                source="chat_interface",
                metadata_template={"user_id": "user_{}", "session_active": True}
            ),
            
            # System Notifications
            StimuliTemplate(
                category="SYSTEM_NOTIFICATION",
                priority="high",
                content_templates=[
                    "System: Avatar state changed to speaking",
                    "System: High CPU usage detected: 85%",
                    "System: Memory usage threshold exceeded",
                    "System: Database backup completed successfully",
                    "System: Character model loaded successfully"
                ],
                source="monitoring_system",
                metadata_template={"system_metric": True, "automated": True}
            ),
            
            # Social Media
            StimuliTemplate(
                category="SOCIAL_MEDIA",
                priority="low",
                content_templates=[
                    "@MyBot thanks for the amazing stream!",
                    "Just followed @MyBot on Twitter!",
                    "Can't wait for the next coding session",
                    "@MyBot your voice synthesis is incredible",
                    "Love watching your AI development process"
                ],
                source="twitter_api",
                metadata_template={"platform": "twitter", "public": True}
            ),
            
            # Emergency Scenarios
            StimuliTemplate(
                category="EMERGENCY",
                priority="critical",
                content_templates=[
                    "EMERGENCY: Security breach detected in user authentication",
                    "EMERGENCY: Critical error in avatar rendering system",
                    "EMERGENCY: Database connection lost",
                    "EMERGENCY: Memory leak causing system instability",
                    "EMERGENCY: Network attack detected - implement countermeasures"
                ],
                source="security_monitor",
                metadata_template={"severity": "critical", "immediate_action": True}
            ),
            
            # Autonomous Triggers
            StimuliTemplate(
                category="AUTONOMOUS_TRIGGER",
                priority="medium",
                content_templates=[
                    "Scheduled reminder: Time for hourly status update",
                    "Auto-trigger: User engagement analysis complete",
                    "Scheduled: Backup configuration files",
                    "Auto-trigger: Performance metrics review",
                    "Scheduled: Clean temporary files"
                ],
                source="scheduler",
                metadata_template={"automated": True, "recurring": True}
            ),
            
            # Contextual Updates
            StimuliTemplate(
                category="CONTEXTUAL_UPDATE",
                priority="low",
                content_templates=[
                    "Weather update: Sunny, 22°C in user location",
                    "News update: New AI research paper published",
                    "Context: User's favorite artist released new album",
                    "Update: Stock market opened higher today",
                    "Context: Local tech meetup scheduled for tonight"
                ],
                source="context_service",
                metadata_template={"contextual": True, "passive": True}
            )
        ]
    
    def generate_stimuli(self, template: StimuliTemplate) -> Dict[str, Any]:
        """Generate realistic stimuli from template."""
        content = random.choice(template.content_templates)
        
        # Customize metadata
        metadata = template.metadata_template.copy()
        if "user_id" in str(metadata):
            metadata = {k: v.format(random.randint(1000, 9999)) if isinstance(v, str) else v 
                       for k, v in metadata.items()}
        
        # Add common metadata
        metadata.update({
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4()),
            "emulation": True
        })
        
        return {
            "content": content,
            "source": template.source,
            "priority": template.priority,
            "metadata": metadata
        }
    
    async def submit_via_http(self, stimuli_data: Dict[str, Any]) -> EmulationResult:
        """Submit stimuli via HTTP API."""
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.api_base}/stimuli/submit",
                headers=self.headers,
                json=stimuli_data
            ) as resp:
                
                response_data = await resp.json()
                processing_time = time.time() - start_time
                
                success = resp.status in [200, 201]
                decision = response_data.get("message", "unknown") if success else "failed"
                
                return EmulationResult(
                    stimuli_id=response_data.get("stimuli_id", "unknown"),
                    category=stimuli_data["metadata"].get("category", "unknown"),
                    priority=stimuli_data["priority"],
                    processing_time=processing_time,
                    success=success,
                    decision=decision,
                    method="http",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return EmulationResult(
                stimuli_id="error",
                category="unknown",
                priority=stimuli_data["priority"],
                processing_time=time.time() - start_time,
                success=False,
                decision=f"error: {str(e)}",
                method="http",
                timestamp=datetime.now()
            )
    
    async def submit_via_websocket(self, stimuli_data: Dict[str, Any]) -> EmulationResult:
        """Submit stimuli via WebSocket."""
        start_time = time.time()
        
        try:
            ws_uri = f"{self.ws_url}/ws/stimuli?token={self.api_key}"
            
            async with websockets.connect(ws_uri) as websocket:
                # Receive connection confirmation
                await websocket.recv()
                
                # Submit stimuli
                message = {
                    "type": "submit_stimuli",
                    "data": stimuli_data
                }
                
                await websocket.send(json.dumps(message))
                response = await websocket.recv()
                response_data = json.loads(response)
                
                processing_time = time.time() - start_time
                success = response_data.get("type") == "stimuli_response"
                
                decision = "unknown"
                if success and "data" in response_data:
                    decision = response_data["data"].get("decision", "unknown")
                
                return EmulationResult(
                    stimuli_id=response_data.get("stimuli_id", "unknown"),
                    category=stimuli_data["metadata"].get("category", "unknown"),
                    priority=stimuli_data["priority"],
                    processing_time=processing_time,
                    success=success,
                    decision=decision,
                    method="websocket",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return EmulationResult(
                stimuli_id="error",
                category="unknown",
                priority=stimuli_data["priority"],
                processing_time=time.time() - start_time,
                success=False,
                decision=f"error: {str(e)}",
                method="websocket",
                timestamp=datetime.now()
            )
    
    async def run_single_scenario(self, scenario_name: str, count: int = 5):
        """Run a single emulation scenario."""
        print(f"\n🎬 Running Scenario: {scenario_name}")
        print("=" * 50)
        
        scenario_results = []
        
        for i in range(count):
            # Select random template
            template = random.choice(self.stimuli_templates)
            stimuli_data = self.generate_stimuli(template)
            
            # Randomly choose submission method
            method = random.choice(["http", "websocket"])
            
            print(f"📤 Submitting {template.category} stimuli via {method.upper()}")
            print(f"   Content: {stimuli_data['content'][:50]}...")
            
            if method == "http":
                result = await self.submit_via_http(stimuli_data)
            else:
                result = await self.submit_via_websocket(stimuli_data)
            
            scenario_results.append(result)
            self.results.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"   {status} {result.processing_time:.3f}s - {result.decision}")
            
            # Add some delay for realistic timing
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Scenario summary
        successful = sum(1 for r in scenario_results if r.success)
        avg_time = sum(r.processing_time for r in scenario_results) / len(scenario_results)
        
        print(f"\n📊 Scenario Summary:")
        print(f"   Success Rate: {successful}/{count} ({successful/count*100:.1f}%)")
        print(f"   Average Processing Time: {avg_time:.3f}s")
    
    async def run_concurrent_stress_test(self, concurrent_count: int = 10):
        """Run concurrent stimuli submission stress test."""
        print(f"\n⚡ Concurrent Stress Test ({concurrent_count} simultaneous requests)")
        print("=" * 60)
        
        async def submit_random_stimuli():
            template = random.choice(self.stimuli_templates)
            stimuli_data = self.generate_stimuli(template)
            method = random.choice(["http", "websocket"])
            
            if method == "http":
                return await self.submit_via_http(stimuli_data)
            else:
                return await self.submit_via_websocket(stimuli_data)
        
        start_time = time.time()
        
        # Submit concurrent requests
        tasks = [submit_random_stimuli() for _ in range(concurrent_count)]
        stress_results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = sum(1 for r in stress_results if r.success)
        avg_processing_time = sum(r.processing_time for r in stress_results) / len(stress_results)
        throughput = concurrent_count / total_time
        
        self.results.extend(stress_results)
        
        print(f"📈 Stress Test Results:")
        print(f"   Total Requests: {concurrent_count}")
        print(f"   Successful: {successful} ({successful/concurrent_count*100:.1f}%)")
        print(f"   Total Time: {total_time:.3f}s")
        print(f"   Throughput: {throughput:.2f} requests/second")
        print(f"   Average Processing Time: {avg_processing_time:.3f}s")
    
    async def run_priority_demonstration(self):
        """Demonstrate priority-based processing."""
        print(f"\n🔥 Priority Processing Demonstration")
        print("=" * 45)
        
        priorities = ["critical", "high", "medium", "low"]
        
        for priority in priorities:
            # Find template with matching priority
            template = next((t for t in self.stimuli_templates if t.priority == priority), None)
            if not template:
                continue
            
            stimuli_data = self.generate_stimuli(template)
            print(f"🚨 Submitting {priority.upper()} priority stimuli")
            print(f"   Content: {stimuli_data['content'][:50]}...")
            
            result = await self.submit_via_http(stimuli_data)
            self.results.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"   {status} Processed in {result.processing_time:.3f}s")
            print(f"   Decision: {result.decision}")
            print()
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive emulation report."""
        print(f"\n📋 GraphFlow Stimuli Emulation Report")
        print("=" * 50)
        
        if not self.results:
            print("No results to report.")
            return
        
        # Overall statistics
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        success_rate = (successful_requests / total_requests) * 100
        
        print(f"🎯 Overall Performance:")
        print(f"   Total Stimuli Processed: {total_requests}")
        print(f"   Success Rate: {successful_requests}/{total_requests} ({success_rate:.1f}%)")
        
        # Timing analysis
        processing_times = [r.processing_time for r in self.results if r.success]
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            
            print(f"   Average Processing Time: {avg_time:.3f}s")
            print(f"   Fastest Processing: {min_time:.3f}s")
            print(f"   Slowest Processing: {max_time:.3f}s")
        
        # Method breakdown
        http_results = [r for r in self.results if r.method == "http"]
        ws_results = [r for r in self.results if r.method == "websocket"]
        
        print(f"\n📡 Transmission Methods:")
        print(f"   HTTP API: {len(http_results)} requests")
        print(f"   WebSocket: {len(ws_results)} requests")
        
        # Priority distribution
        priority_stats = {}
        for result in self.results:
            priority = result.priority
            if priority not in priority_stats:
                priority_stats[priority] = {"total": 0, "successful": 0}
            priority_stats[priority]["total"] += 1
            if result.success:
                priority_stats[priority]["successful"] += 1
        
        print(f"\n🔥 Priority Distribution:")
        for priority, stats in priority_stats.items():
            rate = (stats["successful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"   {priority.upper()}: {stats['successful']}/{stats['total']} ({rate:.1f}%)")
        
        # Recent activity timeline
        print(f"\n⏰ Recent Activity Timeline:")
        recent_results = sorted(self.results, key=lambda x: x.timestamp, reverse=True)[:5]
        for result in recent_results:
            status = "✅" if result.success else "❌"
            time_str = result.timestamp.strftime("%H:%M:%S")
            print(f"   {time_str} {status} {result.priority.upper()} via {result.method.upper()}")
        
        print(f"\n🎉 Emulation Complete! System demonstrated full processing capabilities.")
    
    async def run_complete_emulation(self):
        """Run the complete stimuli transmission and handling emulation."""
        print("🚀 GraphFlow External Stimuli System - Transmission & Handling Emulation")
        print("=" * 75)
        print("This demonstration showcases real-world stimuli processing scenarios")
        print("including multi-source submission, priority handling, and system resilience.")
        print()
        
        # Initialize session
        self.session = aiohttp.ClientSession()
        
        try:
            # Test basic connectivity
            async with self.session.get(f"{self.api_base}/health") as resp:
                if resp.status != 200:
                    print("❌ System not accessible. Please ensure GraphFlow is running.")
                    return
            
            print("✅ System connectivity verified")
            
            # Run different scenarios
            await self.run_single_scenario("Normal Operations", 8)
            await self.run_priority_demonstration()
            await self.run_single_scenario("Mixed Sources", 6)
            await self.run_concurrent_stress_test(12)
            await self.run_single_scenario("Emergency Response", 4)
            
            # Generate final report
            await self.generate_comprehensive_report()
            
        except Exception as e:
            print(f"❌ Emulation failed: {e}")
        
        finally:
            if self.session:
                await self.session.close()

async def main():
    """Main entry point for the emulation demo."""
    demo = StimuliEmulationDemo()
    await demo.run_complete_emulation()

if __name__ == "__main__":
    asyncio.run(main())