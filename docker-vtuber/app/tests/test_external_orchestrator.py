#!/usr/bin/env python3
"""
Test script for External Autonomous Orchestrator
"""

import asyncio
import sys
import signal
from autonomous_orchestrator_external import ExternalOrchestrator


class OrchestratorTester:
    """Test harness for the external orchestrator"""
    
    def __init__(self):
        self.orchestrator = ExternalOrchestrator()
        self.running = True
        
    async def run_test_scenario(self):
        """Run a test scenario demonstrating orchestrator capabilities"""
        
        print("🧪 Starting External Orchestrator Test")
        print("=" * 50)
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start orchestrator in the background
        orchestrator_task = asyncio.create_task(self.orchestrator.start())
        
        # Give it a moment to initialize
        await asyncio.sleep(2)
        
        # Simulate external inputs
        test_prompts = [
            "Hello! How are you doing today?",
            "Can you tell me about the weather?",
            "What's your favorite topic to discuss?",
            "Let's talk about space exploration!",
            "Tell me a fun fact!"
        ]
        
        print("📝 Sending test prompts...")
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🎯 Test {i}: {prompt}")
            await self.orchestrator.process_external_input(prompt)
            
            # Wait between prompts to see orchestrator responses
            await asyncio.sleep(5)
        
        print("\n⏰ Now letting orchestrator run autonomously...")
        print("   (It should start generating idle content after 8 seconds)")
        print("   Press Ctrl+C to stop")
        
        # Let it run until interrupted
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            print("\n🛑 Test stopped by user")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signal"""
        print("\n👋 Received interrupt signal, stopping...")
        self.running = False
        
        # Stop the orchestrator
        asyncio.create_task(self.orchestrator.stop())


async def test_api_connections():
    """Test API connections to VTuber and Game systems"""
    
    print("🔍 Testing API connections...")
    
    from autonomous_orchestrator_external import VTuberAPI, GameAPI
    
    # Test VTuber API
    async with VTuberAPI() as vtuber:
        print("📡 Testing VTuber API...")
        status = await vtuber.get_status()
        if status:
            print(f"✅ VTuber API: Connected (status keys: {list(status.keys())})")
        else:
            print("❌ VTuber API: Failed to connect")
    
    # Test Game API
    async with GameAPI() as game:
        print("🎮 Testing Game API...")
        health = await game.get_health()
        if health and health.get("status") != "error":
            print(f"✅ Game API: Connected (status: {health.get('status', 'unknown')})")
        else:
            print("❌ Game API: Failed to connect")
    
    print()


async def test_manual_control():
    """Test manual control of the VTuber system"""
    
    print("🎮 Testing manual VTuber control...")
    
    from autonomous_orchestrator_external import VTuberAPI
    
    async with VTuberAPI() as vtuber:
        
        # Test sending speech
        test_message = "Hello! This is a test message from the external orchestrator."
        print(f"📤 Sending test message: {test_message}")
        
        success = await vtuber.send_speech(test_message, {"test": True})
        if success:
            print("✅ Speech sent successfully!")
        else:
            print("❌ Failed to send speech")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Check status after sending
        status = await vtuber.get_status()
        if status:
            current_action = status.get("current_action", {})
            print(f"📊 VTuber status after speech:")
            print(f"   Speaking: {current_action.get('is_speaking', False)}")
            print(f"   Queue size: {current_action.get('tts_queue_size', 0)}")
    
    print()


async def main():
    """Main test function"""
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "scenario"
    
    print("🧠 External Autonomous Orchestrator - Test Suite")
    print("=" * 60)
    
    if mode == "api":
        await test_api_connections()
        
    elif mode == "manual":
        await test_manual_control()
        
    elif mode == "scenario":
        tester = OrchestratorTester()
        await tester.run_test_scenario()
        
    else:
        print("Usage:")
        print("  python test_external_orchestrator.py [api|manual|scenario]")
        print()
        print("Modes:")
        print("  api      - Test API connections")
        print("  manual   - Test manual VTuber control")
        print("  scenario - Run full orchestrator test scenario (default)")


if __name__ == "__main__":
    asyncio.run(main()) 