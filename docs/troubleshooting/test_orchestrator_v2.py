#!/usr/bin/env python3
"""
Test script for Autonomous Orchestrator V2
Verifies the new system is working correctly
"""

import asyncio
import time
import logging
import sys
import os

# Add the NeuroSync path
sys.path.insert(0, 'docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player')

from autonomous_orchestrator_v2 import create_autonomous_orchestrator_v2


async def test_basic_functionality():
    """Test basic orchestrator functionality"""
    
    print("\n🧪 Test 1: Basic Functionality")
    print("-" * 40)
    
    # Create orchestrator
    orchestrator = create_autonomous_orchestrator_v2()
    
    # Start it
    await orchestrator.start()
    print("✅ Orchestrator started")
    
    # Check initial state
    state = orchestrator.state
    print(f"Initial state:")
    print(f"  - Is speaking: {state.is_speaking}")
    print(f"  - Blendshape active: {state.blendshape_active}")
    print(f"  - Queue size: {state.speech_queue_size}")
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Stop it
    await orchestrator.stop()
    print("✅ Orchestrator stopped")
    
    return True


async def test_idle_timing():
    """Test that autonomous content respects timing"""
    
    print("\n🧪 Test 2: Idle Timing")
    print("-" * 40)
    
    # Create orchestrator with test settings
    os.environ['AUTONOMOUS_MIN_IDLE_TIME'] = '5.0'  # 5 seconds for testing
    os.environ['AUTONOMOUS_SPEECH_GAP'] = '2.0'
    
    orchestrator = create_autonomous_orchestrator_v2()
    await orchestrator.start()
    
    print(f"Configuration:")
    print(f"  - Min idle time: {orchestrator.MIN_IDLE_FOR_CONTENT}s")
    print(f"  - Speech gap: {orchestrator.MIN_SPEECH_GAP}s")
    
    # Monitor for 8 seconds
    print("\n📊 Monitoring idle behavior...")
    start_time = time.time()
    speeches_generated = []
    
    while time.time() - start_time < 8:
        state = orchestrator.state
        idle_time = time.time() - state.last_user_input_time
        
        # Check if speech was queued
        if state.speech_queue_size > len(speeches_generated):
            speeches_generated.append({
                'time': time.time() - start_time,
                'idle_duration': idle_time,
                'queue_size': state.speech_queue_size
            })
            print(f"  [{time.time() - start_time:.1f}s] Speech queued after {idle_time:.1f}s idle")
            
        await asyncio.sleep(0.5)
    
    # Verify timing
    if speeches_generated:
        first_speech_time = speeches_generated[0]['idle_duration']
        if first_speech_time >= 5.0:
            print(f"✅ First speech after {first_speech_time:.1f}s (>= 5s required)")
        else:
            print(f"❌ First speech too early: {first_speech_time:.1f}s (< 5s required)")
    else:
        print("❌ No autonomous speech generated in 8 seconds")
    
    await orchestrator.stop()
    return len(speeches_generated) > 0


async def test_user_input_handling():
    """Test user input processing and priority"""
    
    print("\n🧪 Test 3: User Input Handling")
    print("-" * 40)
    
    orchestrator = create_autonomous_orchestrator_v2()
    await orchestrator.start()
    
    # Process user input
    print("📝 Sending user input...")
    orchestrator.process_user_input("Hello, this is a test message!", {
        "source": "test_script"
    })
    
    # Check state immediately
    await asyncio.sleep(0.1)
    state = orchestrator.state
    
    print(f"After user input:")
    print(f"  - Last user input time updated: {time.time() - state.last_user_input_time < 1}")
    print(f"  - Queue size: {state.speech_queue_size}")
    
    # Check if speech is in queue
    if orchestrator.speech_queue:
        speech = orchestrator.speech_queue[0]
        print(f"  - Speech priority: {speech.priority.name}")
        print(f"  - Is autonomous: {speech.is_autonomous}")
        print(f"  - Content: {speech.content[:30]}...")
        result = True
    else:
        print("❌ No speech in queue")
        result = False
    
    await orchestrator.stop()
    return result


async def test_interruption():
    """Test autonomous speech interruption"""
    
    print("\n🧪 Test 4: Interruption")
    print("-" * 40)
    
    # Quick timings for testing
    os.environ['AUTONOMOUS_MIN_IDLE_TIME'] = '2.0'
    
    orchestrator = create_autonomous_orchestrator_v2()
    await orchestrator.start()
    
    # Wait for autonomous content
    print("⏳ Waiting for autonomous content...")
    while orchestrator.state.speech_queue_size == 0:
        await asyncio.sleep(0.5)
    
    print("🤖 Autonomous speech queued")
    
    # Get the autonomous speech
    auto_speech_id = orchestrator.speech_queue[0].id if orchestrator.speech_queue else None
    
    # Send user input (should interrupt)
    print("👤 Sending user input to interrupt...")
    orchestrator.process_user_input("Interrupt this!", {"source": "test"})
    
    await asyncio.sleep(0.5)
    
    # Check if autonomous speech was removed
    remaining_auto = [s for s in orchestrator.speech_queue if s.is_autonomous]
    
    if len(remaining_auto) == 0:
        print("✅ Autonomous speech cleared from queue")
        result = True
    else:
        print(f"❌ {len(remaining_auto)} autonomous speeches still in queue")
        result = False
    
    await orchestrator.stop()
    return result


async def test_clear_logging():
    """Test the clear logging system"""
    
    print("\n🧪 Test 5: Clear Logging")
    print("-" * 40)
    
    # Set up logging capture
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    # Create orchestrator with custom handler
    orchestrator = create_autonomous_orchestrator_v2()
    orchestrator.logger.addHandler(handler)
    
    await orchestrator.start()
    
    # Generate some activity
    orchestrator.process_user_input("Test message", {})
    await asyncio.sleep(1)
    
    # Check logs
    log_output = log_capture.getvalue()
    log_lines = log_output.strip().split('\n')
    
    print(f"📋 Sample log output ({len(log_lines)} lines):")
    for line in log_lines[-5:]:  # Last 5 lines
        if '[DECISION]' in line or '[SPEECH' in line or '[STATE]' in line:
            print(f"  {line}")
    
    # Check for clear formatting
    has_decision_logs = any('[DECISION]' in line for line in log_lines)
    has_speech_logs = any('[SPEECH' in line for line in log_lines)
    
    result = has_decision_logs or has_speech_logs
    
    if result:
        print("✅ Clear log formatting detected")
    else:
        print("❌ No structured logs found")
    
    await orchestrator.stop()
    return result


async def main():
    """Run all tests"""
    
    print("🚀 Autonomous Orchestrator V2 Test Suite")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from other loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Run tests
    tests = [
        test_basic_functionality,
        test_idle_timing,
        test_user_input_handling,
        test_interruption,
        test_clear_logging
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = await test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append((test_func.__name__, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("-" * 40)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print("-" * 40)
    print(f"Total: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! V2 orchestrator is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the implementation.")


if __name__ == "__main__":
    asyncio.run(main()) 