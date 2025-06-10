# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

"""
kokoro_tts.py
-------------
Kokoro TTS Client for NeuroSync Player integration.
Provides interface to Kokoro TTS server for ultra-efficient neural TTS.
"""

import io
import json
import requests
import logging
import os
from typing import Optional, Dict

# Configure logging
logger = logging.getLogger(__name__)

# Kokoro voices mapping (from the server you provided)
KOKORO_VOICES = {
    "Sarah": "af_sarah",
    "Bella": "af_bella", 
    "Nicole": "af_nicole",
    "Sky": "af_sky",
    "Adam": "am_adam",
    "Michael": "am_michael",
    "Emma": "bf_emma",
    "Isabella": "bf_isabella",
    "George": "bm_george",
    "Lewis": "bm_lewis"
}

# Default Kokoro TTS server configuration
DEFAULT_KOKORO_SERVER_URL = "http://localhost:6006"
DEFAULT_KOKORO_VOICE = "af_sarah"

def get_kokoro_config():
    """
    Get Kokoro TTS configuration from environment variables.
    """
    return {
        "server_url": os.getenv("KOKORO_TTS_SERVER_URL", DEFAULT_KOKORO_SERVER_URL),
        "default_voice": os.getenv("KOKORO_DEFAULT_VOICE", DEFAULT_KOKORO_VOICE),
        "timeout": int(os.getenv("KOKORO_TTS_TIMEOUT", "30")),
        "language": os.getenv("KOKORO_TTS_LANGUAGE", "en")
    }


def get_kokoro_voice_id_by_name(name: str) -> str:
    """
    Get Kokoro voice ID by name, with fallback to default voice.
    
    Args:
        name (str): Voice name (e.g., "Sarah", "Adam")
        
    Returns:
        str: Kokoro voice ID (e.g., "af_sarah", "am_adam")
    """
    # Try exact match first
    voice_id = KOKORO_VOICES.get(name)
    if voice_id:
        return voice_id
    
    # Try case-insensitive match
    for voice_name, voice_id in KOKORO_VOICES.items():
        if voice_name.lower() == name.lower():
            return voice_id
    
    # Try to find the voice ID directly (in case it's already a voice ID)
    if name in KOKORO_VOICES.values():
        return name
    
    # Fallback to default voice
    config = get_kokoro_config()
    logger.warning(f"Voice '{name}' not found in Kokoro voices, using default: {config['default_voice']}")
    return config["default_voice"]


def test_kokoro_connection() -> bool:
    """
    Test connection to Kokoro TTS server.
    
    Returns:
        bool: True if server is accessible, False otherwise
    """
    config = get_kokoro_config()
    try:
        response = requests.get(f"{config['server_url']}/health", timeout=5)
        if response.ok:
            health_data = response.json()
            logger.info(f"✅ Kokoro TTS server is online: {health_data.get('status', 'unknown')}")
            logger.info(f"🎯 Model: {health_data.get('model', 'N/A')}, Device: {health_data.get('device', 'N/A')}")
            return True
        else:
            logger.error(f"❌ Kokoro TTS server health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Cannot connect to Kokoro TTS server at {config['server_url']}: {e}")
        return False


def get_kokoro_voices() -> Dict[str, str]:
    """
    Get available Kokoro voices from the server.
    
    Returns:
        Dict[str, str]: Dictionary of voice name -> voice ID mappings
    """
    config = get_kokoro_config()
    try:
        response = requests.get(f"{config['server_url']}/voices", timeout=5)
        if response.ok:
            data = response.json()
            voices = data.get("voices", [])
            logger.info(f"🎤 Retrieved {len(voices)} Kokoro voices from server")
            
            # Build mapping from friendly names to voice IDs
            voice_mapping = {}
            for voice_id in voices:
                # Find friendly name for this voice ID
                for friendly_name, mapped_id in KOKORO_VOICES.items():
                    if mapped_id == voice_id:
                        voice_mapping[friendly_name] = voice_id
                        break
                else:
                    # No friendly name found, use the voice ID as name
                    voice_mapping[voice_id] = voice_id
            
            return voice_mapping
        else:
            logger.warning(f"⚠️ Could not retrieve voices from Kokoro server, using defaults")
            return KOKORO_VOICES
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Failed to get voices from Kokoro server: {e}, using defaults")
        return KOKORO_VOICES


def get_kokoro_audio(text: str, voice_name: str) -> Optional[bytes]:
    """
    Generate audio using Kokoro TTS.
    
    Args:
        text (str): Text to synthesize
        voice_name (str): Voice name to use
        
    Returns:
        bytes: WAV audio data, or None if generation failed
    """
    if not text or not text.strip():
        logger.warning("❌ Kokoro TTS: Empty text provided")
        return None
    
    config = get_kokoro_config()
    voice_id = get_kokoro_voice_id_by_name(voice_name)
    
    logger.info(f"🎵 Kokoro TTS generating audio: {text[:50]}{'...' if len(text) > 50 else ''}")
    logger.debug(f"🎤 Using voice: {voice_name} -> {voice_id}")
    
    # Prepare request payload
    payload = {
        "text": text,
        "voice": voice_id,
        "language": config["language"]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Make request to Kokoro TTS server
        response = requests.post(
            f"{config['server_url']}/tts",
            headers=headers,
            json=payload,
            timeout=config["timeout"]
        )
        
        if response.status_code == 200:
            audio_data = response.content
            logger.info(f"✅ Kokoro TTS: Generated {len(audio_data)} bytes of audio")
            return audio_data
        else:
            logger.error(f"❌ Kokoro TTS API error: HTTP {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"❌ Error details: {error_data}")
            except:
                logger.error(f"❌ Error response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Kokoro TTS request timed out after {config['timeout']} seconds")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Kokoro TTS request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error during Kokoro TTS generation: {e}")
        return None


def validate_kokoro_setup() -> bool:
    """
    Validate that Kokoro TTS is properly set up and accessible.
    
    Returns:
        bool: True if setup is valid, False otherwise
    """
    logger.info("🔍 Validating Kokoro TTS setup...")
    
    # Test server connection
    if not test_kokoro_connection():
        return False
    
    # Test TTS generation with a simple phrase
    try:
        test_audio = get_kokoro_audio("Hello, this is a test.", "Sarah")
        if test_audio and len(test_audio) > 0:
            logger.info("✅ Kokoro TTS validation successful!")
            return True
        else:
            logger.error("❌ Kokoro TTS test generation failed")
            return False
    except Exception as e:
        logger.error(f"❌ Kokoro TTS validation failed: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🎵 Kokoro TTS Client Test")
    print("=" * 50)
    
    # Test configuration
    config = get_kokoro_config()
    print(f"Server URL: {config['server_url']}")
    print(f"Default Voice: {config['default_voice']}")
    
    # Test connection
    print("\n🔍 Testing connection...")
    if test_kokoro_connection():
        print("✅ Connection successful!")
        
        # Get available voices
        print("\n🎤 Available voices:")
        voices = get_kokoro_voices()
        for name, voice_id in voices.items():
            print(f"  • {name}: {voice_id}")
        
        # Test TTS generation
        print("\n🎵 Testing TTS generation...")
        test_text = "Hello! This is Kokoro TTS generating speech with ultra-efficient neural networks."
        audio_data = get_kokoro_audio(test_text, "Sarah")
        
        if audio_data:
            print(f"✅ Generated {len(audio_data)} bytes of audio")
            
            # Save test audio to file
            with open("/tmp/kokoro_test.wav", "wb") as f:
                f.write(audio_data)
            print("💾 Test audio saved to /tmp/kokoro_test.wav")
        else:
            print("❌ TTS generation failed")
    else:
        print("❌ Connection failed")
        print("\n💡 Make sure the Kokoro TTS server is running:")
        print("   python kokoro_tts_server.py") 