#!/usr/bin/env python3
"""
Example usage of Kokoro TTS integration with NeuroSync Player.

This example demonstrates:
1. How to configure TTS provider selection
2. Direct usage of Kokoro TTS functions
3. Integration with the TTS worker system

Before running this example:
1. Set environment variables:
   export TTS_PROVIDER=kokoro
   export KOKORO_TTS_SERVER_URL=http://localhost:6006

2. Make sure your Kokoro TTS server is running
"""

import os
import sys
import time
from queue import Queue
from threading import Thread

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_tts_config
from utils.tts.kokoro_tts import get_kokoro_audio
from utils.tts.tts_bridge import tts_worker

def example_direct_usage():
    """Example of using Kokoro TTS directly."""
    print("🎯 Example 1: Direct Kokoro TTS Usage")
    print("-" * 40)
    
    # Test text
    text = "Hello! This is an example of Kokoro TTS integration with NeuroSync Player."
    
    # Different voices to test
    voices = ["Sarah", "Adam", "Emma"]
    
    for voice in voices:
        print(f"🎭 Generating audio with voice: {voice}")
        
        # Generate audio
        audio_bytes = get_kokoro_audio(text, voice)
        
        if audio_bytes:
            print(f"   ✅ Success! Generated {len(audio_bytes)} bytes of audio")
            
            # Save to file for testing
            filename = f"example_kokoro_{voice.lower()}.wav"
            with open(filename, 'wb') as f:
                f.write(audio_bytes)
            print(f"   💾 Saved audio to: {filename}")
        else:
            print(f"   ❌ Failed to generate audio")
        
        print()

def example_tts_worker():
    """Example of using the TTS worker system."""
    print("🔄 Example 2: TTS Worker System")
    print("-" * 40)
    
    # Create queues for communication
    chunk_queue = Queue()
    audio_queue = Queue()
    
    # Start the TTS worker thread
    print("🚀 Starting TTS worker thread...")
    tts_thread = Thread(
        target=tts_worker,
        args=(chunk_queue, audio_queue, None, "Sarah", False)  # None = use config system
    )
    tts_thread.daemon = True
    tts_thread.start()
    
    # Example conversation chunks
    conversation_chunks = [
        "Welcome to the NeuroSync Player demo!",
        "This system can process multiple text chunks in sequence.",
        "Each chunk is converted to audio with facial animation data.",
        "The TTS worker handles everything automatically.",
        "Thank you for trying the Kokoro TTS integration!"
    ]
    
    print(f"📝 Processing {len(conversation_chunks)} conversation chunks...")
    
    # Add chunks to the queue
    for i, chunk in enumerate(conversation_chunks, 1):
        print(f"   📤 Queuing chunk {i}: '{chunk[:30]}...'")
        chunk_queue.put(chunk)
    
    # Process results
    processed_count = 0
    start_time = time.time()
    
    print("\n🎵 Processing audio results...")
    while processed_count < len(conversation_chunks):
        try:
            # Get result with timeout
            audio_bytes, facial_data = audio_queue.get(timeout=10)
            processed_count += 1
            
            print(f"   ✅ Chunk {processed_count}: {len(audio_bytes)} bytes audio")
            
            # Save example audio file
            filename = f"example_chunk_{processed_count}.wav"
            with open(filename, 'wb') as f:
                f.write(audio_bytes)
            
            if facial_data:
                print(f"      🎭 Facial data type: {type(facial_data)}")
            else:
                print(f"      ⚠️ No facial data (NeuroSync API may not be running)")
            
        except Exception as e:
            print(f"   ❌ Timeout or error processing chunk: {e}")
            break
    
    # Stop the worker
    chunk_queue.put(None)
    
    elapsed_time = time.time() - start_time
    print(f"\n📊 Results:")
    print(f"   • Processed: {processed_count}/{len(conversation_chunks)} chunks")
    print(f"   • Time taken: {elapsed_time:.2f} seconds")
    print(f"   • Average per chunk: {elapsed_time/processed_count:.2f} seconds")

def example_configuration():
    """Example of configuration management."""
    print("⚙️ Example 3: Configuration Management")
    print("-" * 40)
    
    # Get current TTS configuration
    config = get_tts_config()
    
    print("📋 Current TTS Configuration:")
    print(f"   • Provider: {config['provider']}")
    print(f"   • Voice: {config['voice']}")
    
    if config['provider'] == 'kokoro':
        print(f"   • Server URL: {config.get('kokoro_server_url', 'N/A')}")
        print(f"   • Timeout: {config.get('kokoro_timeout', 'N/A')} seconds")
        print(f"   • Language: {config.get('kokoro_language', 'N/A')}")
        
        print("\n✅ Kokoro TTS is configured and ready to use!")
    else:
        print(f"\n⚠️ Current provider is '{config['provider']}', not 'kokoro'")
        print("💡 To use Kokoro TTS, set: export TTS_PROVIDER=kokoro")
    
    print("\n🔧 Environment variables that affect TTS:")
    env_vars = [
        'TTS_PROVIDER',
        'KOKORO_TTS_SERVER_URL',
        'KOKORO_DEFAULT_VOICE',
        'KOKORO_TTS_TIMEOUT',
        'KOKORO_TTS_LANGUAGE'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"   • {var}: {value}")

def main():
    """Run all examples."""
    print("🎙️ Kokoro TTS Integration Examples")
    print("=" * 50)
    
    # Show configuration first
    example_configuration()
    
    print("\n")
    
    # Check if Kokoro is configured
    config = get_tts_config()
    if config['provider'] == 'kokoro':
        # Run Kokoro-specific examples
        example_direct_usage()
        print()
        example_tts_worker()
    else:
        print("⚠️ Kokoro TTS is not configured. Skipping audio generation examples.")
        print("💡 Set TTS_PROVIDER=kokoro to run the full examples.")
        
        response = input("\nRun TTS worker example with current provider anyway? (y/n): ")
        if response.lower() == 'y':
            print()
            example_tts_worker()
    
    print("\n🎉 Examples completed!")
    print("📁 Check the current directory for generated audio files.")

if __name__ == "__main__":
    main() 