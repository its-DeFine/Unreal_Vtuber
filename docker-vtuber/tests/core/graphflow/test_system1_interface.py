"""
Test script for System1 (Avatar/Speech) integration interface.

This script tests the basic functionality of the System1Interface
including VTuber client and TTS client operations.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integrations import System1Interface, SystemStatus, CharacterInfo, TTSResult
from config.settings import System1Config


async def test_system1_interface():
    """Test System1 interface functionality."""
    print("=== Testing System1 Interface ===\n")
    
    # Create test configuration
    config = System1Config(
        vtuber_endpoint="http://neurosync:5001",
        request_timeout=30.0,
        connection_timeout=10.0,
        max_retries=3,
        retry_delay=1.0
    )
    
    # Initialize interface
    interface = System1Interface(config)
    
    try:
        print("1. Initializing System1 interface...")
        await interface.initialize()
        print("   ✓ Interface initialized successfully\n")
        
        # Test system availability
        print("2. Checking system availability...")
        status = await interface.check_system_availability()
        print(f"   - Available: {status.is_available}")
        print(f"   - Avatar State: {status.avatar_state.value}")
        print(f"   - Mode: {status.mode.value}")
        print(f"   - Queue Size: {status.queue_size}")
        if status.error_message:
            print(f"   - Error: {status.error_message}")
        print()
        
        # Test current status
        print("3. Getting current status...")
        current_status = await interface.get_current_status()
        print(f"   - Status: {current_status}")
        print()
        
        # Test processing time estimation
        print("4. Testing processing time estimation...")
        test_text = "Hello, this is a test message for the avatar system."
        estimated_time = await interface.estimate_processing_time(test_text)
        print(f"   - Text: '{test_text}'")
        print(f"   - Estimated processing time: {estimated_time:.2f} seconds")
        print()
        
        # Test speech synthesis (without avatar)
        print("5. Testing speech synthesis...")
        tts_result = await interface.synthesize_speech(
            text="This is a test of text-to-speech synthesis.",
            emotion="happy"
        )
        print(f"   - Success: {tts_result.success}")
        if tts_result.success:
            print(f"   - Duration: {tts_result.duration:.2f} seconds")
            print(f"   - Format: {tts_result.format}")
            print(f"   - Sample Rate: {tts_result.sample_rate} Hz")
            print(f"   - Voice Used: {tts_result.voice_used}")
            print(f"   - Emotion Applied: {tts_result.emotion_applied}")
        else:
            print(f"   - Error: {tts_result.error_message}")
        print()
        
        # Test avatar response (if available)
        if status.is_available and status.is_ready:
            print("6. Testing avatar response...")
            success = await interface.trigger_avatar_response(
                content="Hello! I am testing the avatar system.",
                metadata={
                    "stimuli_id": "test-001",
                    "priority": "normal",
                    "source": "test_script"
                }
            )
            print(f"   - Avatar response triggered: {success}")
            print()
        else:
            print("6. Skipping avatar response test (system not ready)")
            print()
        
        # Test character operations
        print("7. Testing character operations...")
        
        # Get character info (example)
        char_info = await interface.get_character_info("default")
        if char_info:
            print(f"   - Character found: {char_info.name}")
            print(f"   - ID: {char_info.character_id}")
            print(f"   - Supports emotion: {char_info.supports_emotion}")
            print(f"   - Default emotion: {char_info.get_default_emotion()}")
        else:
            print("   - Character 'default' not found")
        
        # Try loading a character
        print("\n   - Attempting to load character 'default'...")
        load_success = await interface.load_character("default")
        print(f"   - Character load success: {load_success}")
        print()
        
        # Test mode switching
        print("8. Testing mode switching...")
        
        # Get current mode
        current_status = await interface.get_current_status()
        current_mode = current_status.get("mode", "unknown")
        print(f"   - Current mode: {current_mode}")
        
        # Try switching mode
        new_mode = "autonomous" if current_mode == "reactive" else "reactive"
        print(f"   - Switching to {new_mode} mode...")
        mode_success = await interface.set_mode(new_mode)
        print(f"   - Mode switch success: {mode_success}")
        print()
        
        # Test queue operations
        print("9. Testing queue operations...")
        
        # Get queue status
        queue_status = await interface.get_queue_status()
        print(f"   - Queue status: {queue_status}")
        
        # Test stop action
        print("   - Testing stop current action...")
        stop_success = await interface.stop_current_action()
        print(f"   - Stop success: {stop_success}")
        
        # Test clear queue
        print("   - Testing clear queue...")
        clear_success = await interface.clear_queue()
        print(f"   - Clear queue success: {clear_success}")
        print()
        
        print("=== All tests completed ===")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Shutdown interface
        print("\nShutting down interface...")
        await interface.shutdown()
        print("✓ Interface shutdown complete")


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n=== Testing Error Handling ===\n")
    
    # Test with invalid endpoint
    config = System1Config(
        vtuber_endpoint="http://invalid-host:9999",
        request_timeout=5.0,
        connection_timeout=2.0,
        max_retries=2,
        retry_delay=0.5
    )
    
    interface = System1Interface(config)
    
    try:
        print("1. Testing initialization with invalid endpoint...")
        await interface.initialize()
        print("   - Interface initialized (connection test may have been skipped)")
        
        print("\n2. Testing operations with unavailable system...")
        
        # Test availability check
        status = await interface.check_system_availability()
        print(f"   - System available: {status.is_available}")
        print(f"   - Error: {status.error_message}")
        
        # Test avatar trigger with unavailable system
        print("\n3. Testing avatar trigger with unavailable system...")
        success = await interface.trigger_avatar_response(
            content="Test message",
            metadata={"test": True}
        )
        print(f"   - Avatar trigger success: {success} (expected: False)")
        
        # Test uninitialized interface
        print("\n4. Testing operations on uninitialized interface...")
        uninitialized_interface = System1Interface(config)
        
        try:
            await uninitialized_interface.trigger_avatar_response(
                content="Test",
                metadata={}
            )
        except RuntimeError as e:
            print(f"   ✓ Caught expected error: {e}")
        
    finally:
        await interface.shutdown()
    
    print("\n=== Error handling tests completed ===")


if __name__ == "__main__":
    print("Starting System1 Interface tests...\n")
    
    # Run main tests
    asyncio.run(test_system1_interface())
    
    # Run error handling tests
    asyncio.run(test_error_handling())
    
    print("\nAll tests completed!")