#!/usr/bin/env python3
"""
Test script for Kokoro TTS integration with NeuroSync Player.

This script tests:
1. Configuration loading and TTS provider selection
2. Kokoro TTS server connectivity
3. Audio generation with different voices
4. Integration with the TTS worker system

Usage:
    python test_kokoro_integration.py

Prerequisites:
    - Kokoro TTS server running on configured URL (default: http://localhost:6006)
    - Set environment variables:
        export TTS_PROVIDER=kokoro
        export KOKORO_TTS_SERVER_URL=http://localhost:6006  # if different
"""

import os
import sys
import time
from queue import Queue
from threading import Thread

# Add the current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_tts_config
from utils.tts.kokoro_tts import get_kokoro_audio, test_kokoro_connection
from utils.tts.tts_bridge import tts_worker

def test_configuration():
    """Test that configuration is loaded correctly."""
    print("🔧 Testing configuration...")
    
    config = get_tts_config()
    print(f"   Provider: {config['provider']}")
    print(f"   Voice: {config['voice']}")
    print(f"   Server URL: {config.get('kokoro_server_url', 'N/A')}")
    print(f"   Timeout: {config.get('kokoro_timeout', 'N/A')}")
    print(f"   Language: {config.get('kokoro_language', 'N/A')}")
    
    if config['provider'] != 'kokoro':
        print("   ⚠️ TTS_PROVIDER is not set to 'kokoro'. Test may use different provider.")
        print("   💡 Set environment variable: export TTS_PROVIDER=kokoro")
    
    return config

def test_kokoro_server_connection():
    """Test direct connection to Kokoro TTS server."""
    print("\n🌐 Testing Kokoro TTS server connection...")
    
    try:
        if test_kokoro_connection():
            print("   ✅ Kokoro TTS server is accessible")
            return True
        else:
            print("   ❌ Kokoro TTS server is not accessible")
            return False
    except Exception as e:
        print(f"   ❌ Error testing connection: {e}")
        return False

def test_audio_generation():
    """Test audio generation with Kokoro TTS."""
    print("\n🎵 Testing audio generation...")
    
    test_text = "Hello! This is a test of the Kokoro TTS integration with NeuroSync Player."
    test_voices = ["af_sarah", "am_adam", "bf_emma", "bm_george"]
    
    for voice in test_voices:
        print(f"   Testing voice: {voice}")
        try:
            audio_bytes = get_kokoro_audio(test_text, voice)
            if audio_bytes:
                print(f"      ✅ Generated {len(audio_bytes)} bytes of audio")
                
                # Save test audio file
                output_file = f"test_kokoro_{voice}.wav"
                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)
                print(f"      💾 Saved audio to {output_file}")
            else:
                print(f"      ❌ Failed to generate audio")
        except Exception as e:
            print(f"      ❌ Error: {e}")

def test_tts_worker_integration():
    """Test integration with the TTS worker system."""
    print("\n🔄 Testing TTS worker integration...")
    
    # Create queues
    chunk_queue = Queue()
    audio_queue = Queue()
    
    # Start TTS worker thread
    print("   Starting TTS worker thread...")
    tts_thread = Thread(
        target=tts_worker,
        args=(chunk_queue, audio_queue, None, "af_sarah", False)  # None means use config system
    )
    tts_thread.daemon = True
    tts_thread.start()
    
    # Add test chunks
    test_chunks = [
        "Hello from the TTS worker integration test.",
        "This tests the full pipeline from text to audio and facial data.",
        "If you see this message, the integration is working correctly!"
    ]
    
    for chunk in test_chunks:
        chunk_queue.put(chunk)
    
    # Process results
    results_processed = 0
    timeout_start = time.time()
    timeout_duration = 30  # 30 seconds timeout
    
    while results_processed < len(test_chunks):
        if time.time() - timeout_start > timeout_duration:
            print(f"   ⚠️ Timeout after {timeout_duration} seconds")
            break
            
        if not audio_queue.empty():
            try:
                audio_bytes, facial_data = audio_queue.get(timeout=1)
                results_processed += 1
                print(f"   ✅ Processed chunk {results_processed}: {len(audio_bytes)} bytes audio")
                if facial_data:
                    print(f"      ✅ Got facial data: {type(facial_data)}")
                else:
                    print(f"      ⚠️ No facial data (this is expected if NeuroSync API is not running)")
                
            except Exception as e:
                print(f"   ❌ Error processing result: {e}")
                break
        else:
            time.sleep(0.1)  # Short sleep to avoid busy waiting
    
    # Signal worker to stop
    chunk_queue.put(None)
    
    print(f"   📊 Successfully processed {results_processed}/{len(test_chunks)} chunks")

def main():
    """Run all tests."""
    print("🧪 Kokoro TTS Integration Test Suite")
    print("=" * 50)
    
    # Test configuration
    config = test_configuration()
    
    # Test server connection
    if config['provider'] == 'kokoro':
        connection_ok = test_kokoro_server_connection()
        
        if connection_ok:
            # Test audio generation
            test_audio_generation()
            
            # Test TTS worker integration
            test_tts_worker_integration()
        else:
            print("\n❌ Cannot proceed with tests - Kokoro server is not accessible")
            print("💡 Make sure Kokoro TTS server is running and accessible")
    else:
        print(f"\n⚠️ TTS provider is '{config['provider']}', not 'kokoro'")
        print("💡 To test Kokoro TTS, set: export TTS_PROVIDER=kokoro")
        print("🔄 You can still run the TTS worker integration test with current provider")
        
        response = input("Run TTS worker integration test anyway? (y/n): ")
        if response.lower() == 'y':
            test_tts_worker_integration()
    
    print("\n✅ Test suite completed!")
    print("📝 Check the generated test audio files and console output for results.")

if __name__ == "__main__":
    main() 