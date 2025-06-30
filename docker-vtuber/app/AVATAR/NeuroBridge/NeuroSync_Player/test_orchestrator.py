#!/usr/bin/env python3
"""
Autonomous Orchestrator Test Script
==================================

This script demonstrates the key capabilities of the Autonomous Orchestrator:
1. Autonomous decision making between speech and environment actions
2. Human-like interruption capabilities
3. Priority-based action execution
4. Real-time state monitoring

Run this script to see the orchestrator in action!
"""

import asyncio
import time
import logging
from autonomous_orchestrator import (
    create_autonomous_orchestrator,
    ActionType,
    Priority
)

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class OrchestratorDemo:
    """Demonstration class for Autonomous Orchestrator capabilities"""
    
    def __init__(self):
        self.orchestrator = create_autonomous_orchestrator()
        
    async def run_demo(self):
        """Run the complete orchestrator demonstration"""
        
        print("🎭" + "="*60)
        print("    AUTONOMOUS ORCHESTRATOR DEMONSTRATION")
        print("="*60 + "🎭")
        print()
        
        # Start the orchestrator
        print("🚀 Starting Autonomous Orchestrator...")
        await self.orchestrator.start()
        print("✅ Orchestrator started successfully!")
        print()
        
        # Run demonstration scenarios
        await self.demo_basic_functionality()
        await self.demo_interruption_capabilities()
        await self.demo_priority_system()
        await self.demo_decision_making()
        await self.demo_state_monitoring()
        
        # Stop the orchestrator
        print("🛑 Stopping Autonomous Orchestrator...")
        await self.orchestrator.stop()
        print("✅ Orchestrator stopped successfully!")
        print()
        print("🎯 Demonstration completed!")
        
    async def demo_basic_functionality(self):
        """Demonstrate basic orchestrator functionality"""
        
        print("📋 DEMO 1: Basic Functionality")
        print("-" * 40)
        
        # Test speech action
        print("🗣️ Testing speech action...")
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "Hello! This is a test speech action.",
            Priority.MEDIUM
        )
        
        await asyncio.sleep(1)
        
        # Test environment action
        print("🎮 Testing environment action...")
        self.orchestrator.queue_action(
            ActionType.ENVIRONMENT,
            "medieval castle with red hair",
            Priority.MEDIUM
        )
        
        await asyncio.sleep(2)
        print("✅ Basic functionality test completed!\n")
        
    async def demo_interruption_capabilities(self):
        """Demonstrate human-like interruption capabilities"""
        
        print("⚡ DEMO 2: Interruption Capabilities")
        print("-" * 40)
        
        # Start a long speech
        print("🗣️ Starting long speech...")
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "This is a very long speech that would normally take quite a while to complete. I'm going to keep talking for a bit to demonstrate how the system can handle interruptions gracefully...",
            Priority.MEDIUM
        )
        
        # Wait a moment, then interrupt with urgent message
        await asyncio.sleep(1)
        print("🚨 Interrupting with urgent message...")
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "URGENT: Emergency notification!",
            Priority.URGENT,
            interrupt_current=True
        )
        
        await asyncio.sleep(2)
        print("✅ Interruption test completed!\n")
        
    async def demo_priority_system(self):
        """Demonstrate priority-based decision making"""
        
        print("🎯 DEMO 3: Priority System")
        print("-" * 40)
        
        # Queue multiple actions with different priorities
        print("📝 Queuing multiple actions with different priorities...")
        
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "Low priority message",
            Priority.LOW
        )
        
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "Medium priority message",
            Priority.MEDIUM
        )
        
        self.orchestrator.queue_action(
            ActionType.SPEECH,
            "High priority message - should execute first!",
            Priority.HIGH
        )
        
        self.orchestrator.queue_action(
            ActionType.ENVIRONMENT,
            "Change to space station environment",
            Priority.MEDIUM
        )
        
        print("⏳ Waiting for priority-based execution...")
        await asyncio.sleep(3)
        print("✅ Priority system test completed!\n")
        
    async def demo_decision_making(self):
        """Demonstrate autonomous decision making"""
        
        print("🧠 DEMO 4: Autonomous Decision Making")
        print("-" * 40)
        
        # Test various input classifications
        test_inputs = [
            ("Hello there! How are you doing today?", "Regular conversation"),
            ("Change the hair color to blue and set a futuristic scene", "Environment change"),
            ("This is urgent! Please respond immediately!", "Urgent speech"),
            ("Set the lighting to evening mood with purple hair", "Environment change"),
            ("Can you tell me about the weather?", "Regular conversation")
        ]
        
        for text, description in test_inputs:
            print(f"🔍 Testing: {description}")
            print(f"   Input: '{text[:50]}...'")
            
            # Process through orchestrator
            self.orchestrator.process_external_input(text)
            
            await asyncio.sleep(0.5)
            
        print("✅ Decision making test completed!\n")
        
    async def demo_state_monitoring(self):
        """Demonstrate real-time state monitoring"""
        
        print("📊 DEMO 5: State Monitoring")
        print("-" * 40)
        
        # Get current state
        state = self.orchestrator.state_monitor.get_state_snapshot()
        
        print("📈 Current System State:")
        print(f"   🔊 Is Speaking: {state.is_speaking}")
        print(f"   📋 TTS Queue Size: {state.tts_queue_size}")
        print(f"   🎭 Blendshape Active: {state.blendshape_active}")
        print(f"   🎮 Current Environment: {state.current_environment}")
        print(f"   🔄 Environment Changing: {state.environment_changing}")
        print(f"   💬 Conversation Active: {state.conversation_active}")
        print(f"   ⏰ Last Input Time: {state.last_input_time}")
        
        # Test state updates
        print("\n🔄 Testing state updates...")
        
        # Simulate audio start
        self.orchestrator.state_monitor.update_audio_state(
            is_speaking=True,
            queue_size=2,
            estimated_end_time=time.time() + 5.0
        )
        
        # Simulate environment change
        self.orchestrator.state_monitor.update_environment_state(
            environment="cyberpunk_city",
            changing=True
        )
        
        # Get updated state
        updated_state = self.orchestrator.state_monitor.get_state_snapshot()
        
        print("📈 Updated System State:")
        print(f"   🔊 Is Speaking: {updated_state.is_speaking}")
        print(f"   🎮 Current Environment: {updated_state.current_environment}")
        print(f"   🔄 Environment Changing: {updated_state.environment_changing}")
        
        await asyncio.sleep(1)
        print("✅ State monitoring test completed!\n")


async def run_interactive_demo():
    """Run an interactive demonstration where user can test commands"""
    
    print("\n🎮 INTERACTIVE MODE")
    print("=" * 50)
    print("Commands:")
    print("  speech <text>     - Queue speech action")
    print("  env <prompt>      - Queue environment action")  
    print("  urgent <text>     - Queue urgent speech")
    print("  interrupt         - Interrupt current actions")
    print("  status            - Show orchestrator status")
    print("  quit              - Exit interactive mode")
    print("-" * 50)
    
    orchestrator = create_autonomous_orchestrator()
    await orchestrator.start()
    
    try:
        while True:
            try:
                command = input("\n🎭 Enter command: ").strip()
                
                if command.lower() == 'quit':
                    break
                elif command.lower() == 'status':
                    state = orchestrator.state_monitor.get_state_snapshot()
                    print(f"📊 Status: Speaking={state.is_speaking}, Environment={state.current_environment}")
                    print(f"   Pending actions: {len(orchestrator.pending_actions)}")
                elif command.lower() == 'interrupt':
                    orchestrator.queue_action(ActionType.INTERRUPT, "Manual interrupt", Priority.URGENT)
                    print("⚡ Interrupt requested")
                elif command.startswith('speech '):
                    text = command[7:]
                    orchestrator.queue_action(ActionType.SPEECH, text, Priority.MEDIUM)
                    print(f"🗣️ Speech queued: {text[:30]}...")
                elif command.startswith('env '):
                    prompt = command[4:]
                    orchestrator.queue_action(ActionType.ENVIRONMENT, prompt, Priority.MEDIUM)
                    print(f"🎮 Environment queued: {prompt[:30]}...")
                elif command.startswith('urgent '):
                    text = command[7:]
                    orchestrator.queue_action(ActionType.SPEECH, text, Priority.URGENT, interrupt_current=True)
                    print(f"🚨 Urgent speech queued: {text[:30]}...")
                else:
                    print("❓ Unknown command. Type 'quit' to exit.")
                    
                await asyncio.sleep(0.1)  # Give orchestrator time to process
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    finally:
        await orchestrator.stop()
        print("✅ Interactive demo ended")


def main():
    """Main function to run the demonstration"""
    
    print("🎭 Autonomous Orchestrator Test Suite")
    print("=====================================")
    print()
    print("Choose a demonstration mode:")
    print("1. Automated Demo (shows all features)")
    print("2. Interactive Demo (manual testing)")
    print("3. Quick Test (basic functionality only)")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            demo = OrchestratorDemo()
            asyncio.run(demo.run_demo())
        elif choice == "2":
            asyncio.run(run_interactive_demo())
        elif choice == "3":
            asyncio.run(quick_test())
        else:
            print("❌ Invalid choice. Please run again and select 1, 2, or 3.")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")


async def quick_test():
    """Quick test of basic orchestrator functionality"""
    
    print("⚡ Quick Test Mode")
    print("-" * 30)
    
    orchestrator = create_autonomous_orchestrator()
    
    print("🚀 Starting orchestrator...")
    await orchestrator.start()
    
    print("📝 Testing basic actions...")
    orchestrator.queue_action(ActionType.SPEECH, "Quick test message", Priority.MEDIUM)
    orchestrator.queue_action(ActionType.ENVIRONMENT, "test environment", Priority.MEDIUM)
    
    await asyncio.sleep(2)
    
    print("🛑 Stopping orchestrator...")
    await orchestrator.stop()
    
    print("✅ Quick test completed!")


if __name__ == "__main__":
    main() 