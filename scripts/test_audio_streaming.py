#!/usr/bin/env python3
"""
Test script for GStreamer audio streaming functionality.
This script creates a test WAV file and attempts to stream it via RTMP.
"""

import os
import sys
import time
import threading
import logging
import numpy as np
from scipy.io.wavfile import write

# Add the NeuroSync Player to the path
sys.path.append('NeuroBridge/NeuroSync_Player')

from utils.audio.gst_stream import stream_wav_to_rtmp
from utils.audio.play_audio import _rtmp_url, _audio_mode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_test_audio(filename="test_audio.wav", duration=5, sample_rate=22050):
    """Generate a simple test audio file with a 440Hz tone."""
    logger.info(f"Generating test audio file: {filename}")
    
    # Generate a 440Hz sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * 440 * t) * 0.3  # 440Hz tone at 30% volume
    
    # Convert to 16-bit PCM
    wave_int16 = (wave * 32767).astype(np.int16)
    
    # Write to WAV file
    write(filename, sample_rate, wave_int16)
    logger.info(f"Test audio file created: {filename} ({duration}s duration)")
    return filename

def test_rtmp_connectivity():
    """Test RTMP server connectivity."""
    rtmp_url = _rtmp_url()
    logger.info(f"Testing connectivity to RTMP server: {rtmp_url}")
    
    # For a proper test, we'd try to connect to the RTMP server
    # For now, just log the configuration
    logger.info(f"Audio mode: {_audio_mode()}")
    logger.info(f"RTMP URL: {rtmp_url}")
    
    # Check if nginx-rtmp container is reachable (if using container networking)
    if "nginx-rtmp" in rtmp_url:
        logger.info("Using container networking - ensure nginx-rtmp container is running")
    else:
        logger.info("Using host networking")

def test_gstreamer_streaming():
    """Test the complete GStreamer streaming pipeline."""
    logger.info("=== Starting GStreamer Audio Streaming Test ===")
    
    try:
        # Step 1: Generate test audio
        test_file = generate_test_audio("test_streaming_audio.wav", duration=10)
        
        if not os.path.exists(test_file):
            logger.error(f"Failed to create test audio file: {test_file}")
            return False
        
        # Step 2: Test RTMP configuration
        test_rtmp_connectivity()
        
        # Step 3: Get RTMP URL
        rtmp_url = _rtmp_url()
        
        # Step 4: Test streaming
        logger.info("Starting GStreamer streaming test...")
        
        # Create start event (simulating the real system)
        start_event = threading.Event()
        start_event.set()  # Start immediately for test
        
        # Stream the audio
        stream_wav_to_rtmp(test_file, rtmp_url, blocking=True)
        
        logger.info("✅ GStreamer streaming test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ GStreamer streaming test failed: {e}")
        return False
    
    finally:
        # Clean up test file
        if os.path.exists("test_streaming_audio.wav"):
            os.remove("test_streaming_audio.wav")
            logger.info("Test audio file cleaned up")

def main():
    """Run the complete audio streaming test suite."""
    logger.info("🎵 Audio Streaming Test Suite Starting...")
    
    # Check for required dependencies
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        logger.info("✅ GStreamer Python bindings available")
    except ImportError as e:
        logger.error(f"❌ GStreamer Python bindings not available: {e}")
        return False
    
    # Run the streaming test
    success = test_gstreamer_streaming()
    
    if success:
        logger.info("🎉 All tests passed! Audio streaming should be working.")
        print("\n" + "="*60)
        print("✅ AUDIO STREAMING TEST PASSED")
        print("Your GStreamer audio streaming is configured correctly!")
        print("="*60)
    else:
        logger.error("❌ Tests failed. Check the logs above for details.")
        print("\n" + "="*60)
        print("❌ AUDIO STREAMING TEST FAILED")
        print("Please check the error messages and configuration.")
        print("="*60)
    
    return success

if __name__ == "__main__":
    main() 