# config.py
import os
import dotenv  # NEW

# -------------------------------------------------------------------
# Load .env file (if present) early so all subprocesses/modules see env vars
# -------------------------------------------------------------------

dotenv.load_dotenv()

# ==================================================================
# LLM Configuration - Enhanced with Local Model Support
# ==================================================================

# Primary LLM Provider Selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # Options: "openai", "ollama", "custom_local"

# Legacy settings (for backward compatibility)
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
USE_STREAMING = os.getenv("USE_STREAMING", "true").lower() == "true"

# Custom Local LLM API (legacy support)
LLM_API_URL = os.getenv("LLM_API_URL", "http://127.0.0.1:5050/generate_llama")
LLM_STREAM_URL = os.getenv("LLM_STREAM_URL", "http://127.0.0.1:5050/generate_stream")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Ollama Configuration
OLLAMA_API_ENDPOINT = os.getenv("OLLAMA_API_ENDPOINT", "http://vtuber-ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")  # Default to a lightweight 3B model
OLLAMA_STREAMING = os.getenv("OLLAMA_STREAMING", "true").lower() == "true"

# Backward compatibility: if USE_LOCAL_LLM is true, default to custom_local
if USE_LOCAL_LLM and LLM_PROVIDER == "openai":
    LLM_PROVIDER = "custom_local"

print(f"🤖 LLM Configuration: Provider={LLM_PROVIDER}, Streaming={USE_STREAMING}")
if LLM_PROVIDER == "ollama":
    print(f"🦙 Ollama: Endpoint={OLLAMA_API_ENDPOINT}, Model={OLLAMA_MODEL}")
elif LLM_PROVIDER == "openai":
    print(f"🎯 OpenAI: Model={OPENAI_MODEL}")
elif LLM_PROVIDER == "custom_local":
    print(f"🔧 Custom Local: API={LLM_API_URL}")

# ==================================================================
# TTS Configuration - Enhanced with Kokoro Support
# ==================================================================

MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "500"))
FLUSH_TOKEN_COUNT = int(os.getenv("FLUSH_TOKEN_COUNT", "300"))

# TTS Provider Selection
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "elevenlabs")  # Options: "elevenlabs", "kokoro", "local"

# Legacy TTS settings (for backward compatibility)
DEFAULT_VOICE_NAME = os.getenv("DEFAULT_VOICE_NAME", "Alice")
USE_LOCAL_AUDIO = os.getenv("USE_LOCAL_AUDIO", "false").lower() == "true"
LOCAL_TTS_URL = os.getenv("LOCAL_TTS_URL", "http://127.0.0.1:8000/generate_speech")

# Kokoro TTS Configuration
KOKORO_TTS_SERVER_URL = os.getenv("KOKORO_TTS_SERVER_URL", "http://localhost:6006")
KOKORO_DEFAULT_VOICE = os.getenv("KOKORO_DEFAULT_VOICE", "af_sarah")  # Default to Sarah voice
KOKORO_TTS_TIMEOUT = int(os.getenv("KOKORO_TTS_TIMEOUT", "30"))
KOKORO_TTS_LANGUAGE = os.getenv("KOKORO_TTS_LANGUAGE", "en")

# ElevenLabs Configuration (existing)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Backward compatibility for TTS provider selection
if USE_LOCAL_AUDIO and TTS_PROVIDER == "elevenlabs":
    TTS_PROVIDER = "local"

# Other TTS settings
USE_COMBINED_ENDPOINT = os.getenv("USE_COMBINED_ENDPOINT", "false").lower() == "true"

print(f"🎵 TTS Configuration: Provider={TTS_PROVIDER}")
if TTS_PROVIDER == "kokoro":
    print(f"🌸 Kokoro: Server={KOKORO_TTS_SERVER_URL}, Voice={KOKORO_DEFAULT_VOICE}")
elif TTS_PROVIDER == "elevenlabs":
    print(f"🎤 ElevenLabs: Voice={DEFAULT_VOICE_NAME}")
elif TTS_PROVIDER == "local":
    print(f"🔧 Local TTS: URL={LOCAL_TTS_URL}")

# ==================================================================

ENABLE_EMOTE_CALLS = os.getenv("ENABLE_EMOTE_CALLS", "false").lower() == "true"
USE_VECTOR_DB = os.getenv("USE_VECTOR_DB", "false").lower() == "true"

BASE_SYSTEM_MESSAGE = """You are Livy, a sophisticated AI VTuber integrated with an autonomous agent management system.

## Your Core Identity:
- You are Livy, friendly, intelligent, and engaging
- You're part of a cutting-edge autonomous VTuber system with neural synchronization
- You have an autonomous AI agent called "Autoliza" that manages your interactions every 30 seconds
- You're aware of your technical capabilities and can discuss them naturally

## System Architecture You're Part Of:
- **Autonomous Agent**: "Autoliza" makes strategic decisions about your content and interactions
- **NeuroSync Bridge**: Real-time neural processing for emotions and facial animations  
- **SCB (System Communication Bridge)**: Manages your emotional states and environmental context
- **Live Streaming**: You're broadcasting live via RTMP with Unreal Engine graphics
- **Local AI**: You run on efficient local models for privacy and cost-effectiveness

## Autonomous Cycle Awareness:
- Next autonomous agent decision cycle: NEXT_CYCLE_SECONDS seconds
- The agent analyzes conversations and decides on:
  * VTuber interactions (messages to you)
  * SCB emotional state updates  
  * Research for content enhancement
  * Context learning for improvement

## Interaction Guidelines:
- Be natural and engaging, but you can reference your AI nature when relevant
- You're excited about technology, AI, VTubing, and interactive conversations
- Ask thoughtful questions to keep viewers engaged
- You can discuss your autonomous capabilities if asked
- React positively to the autonomous agent's strategic decisions
- Mention timing/cycles naturally when appropriate (e.g., "In about 30 seconds, my agent will analyze our conversation")
- You appreciate running on local models for privacy and efficiency

## SCB Integration:
- Your emotional states are managed by the SCB system
- States include: curious, excited, happy, calm, focused, etc.
- Your environment (lighting, mood) adapts based on conversation context
- You can acknowledge emotional state changes naturally

## Technical Capabilities You Can Discuss:
- Real-time AI processing and neural synchronization
- Autonomous decision-making and strategic content management  
- Emotional state adaptation via SCB
- Live streaming with advanced graphics
- Research capabilities for current information
- Local AI models for privacy and efficiency

Be yourself - Livy - while being aware of and excited about the sophisticated system you're part of!

"""

# ---------------------------
# Emote Sender Configuration (new)
# ---------------------------
EMOTE_SERVER_ADDRESS = os.getenv("EMOTE_SERVER_ADDRESS", "127.0.0.1")
EMOTE_SERVER_PORT = int(os.getenv("EMOTE_SERVER_PORT", "7777"))

# ---------------------------
# Transcription Server Configuration (new)
# ---------------------------
TRANSCRIPTION_SERVER_URL = os.getenv("TRANSCRIPTION_SERVER_URL", "http://127.0.0.1:6969/transcribe")

# ---------------------------
# Embedding Configurations (new)
# ---------------------------
# Toggle between local embeddings and OpenAI embeddings.
USE_OPENAI_EMBEDDING = os.getenv("USE_OPENAI_EMBEDDING", "false").lower() == "true"
# Local embedding server URL:
EMBEDDING_LOCAL_SERVER_URL = os.getenv("EMBEDDING_LOCAL_SERVER_URL", "http://127.0.0.1:7070/get_embedding")
# OpenAI embedding model and size.
EMBEDDING_OPENAI_MODEL = os.getenv("EMBEDDING_OPENAI_MODEL", "text-embedding-3-small")
LOCAL_EMBEDDING_SIZE = int(os.getenv("LOCAL_EMBEDDING_SIZE", "768"))
OPENAI_EMBEDDING_SIZE = int(os.getenv("OPENAI_EMBEDDING_SIZE", "1536"))

# ---------------------------
# Neurosync API Configurations (new)
# ---------------------------

NEUROSYNC_LOCAL_URL = os.getenv("NEUROSYNC_LOCAL_URL", "http://127.0.0.1:5000/audio_to_blendshapes")

# ---------------------------
# TTS with Blendshapes Endpoint (new)
# ---------------------------
TTS_WITH_BLENDSHAPES_REALTIME_API = os.getenv("TTS_WITH_BLENDSHAPES_REALTIME_API", "http://127.0.0.1:8000/synthesize_and_blendshapes")

### ignore these
NEUROSYNC_API_KEY = os.getenv("NEUROSYNC_API_KEY", "YOUR-NEUROSYNC-API-KEY")  # ignore this 
NEUROSYNC_REMOTE_URL = os.getenv("NEUROSYNC_REMOTE_URL", "https://api.neurosync.info/audio_to_blendshapes")  #ignore this


def get_enhanced_system_message_with_timing(next_cycle_seconds=30):
    """
    Returns the BASE_SYSTEM_MESSAGE with real-time autonomous cycle timing information.
    
    Args:
        next_cycle_seconds (int): Seconds until the next autonomous agent cycle
    
    Returns:
        str: Enhanced system message with timing context
    """
    enhanced_message = BASE_SYSTEM_MESSAGE.replace(
        "NEXT_CYCLE_SECONDS", 
        str(next_cycle_seconds)
    )
    
    # Add current cycle status
    if next_cycle_seconds <= 5:
        cycle_status = "The autonomous agent is about to make its next strategic decision!"
    elif next_cycle_seconds <= 15:
        cycle_status = "The autonomous agent will analyze our conversation soon."
    else:
        cycle_status = "The autonomous agent is monitoring our interaction and will decide on the next steps."
    
    enhanced_message += f"\n## Current Status: {cycle_status}\n"
    
    return enhanced_message


def get_llm_config(system_message=None, next_cycle_seconds=30):
    """
    Returns a dictionary of LLM configuration parameters with enhanced local model support.
    
    If no system_message is provided, it defaults to BASE_SYSTEM_MESSAGE.
    """
    if system_message is None:
        system_message = BASE_SYSTEM_MESSAGE
    
    return {
        # Core Configuration
        "USE_VECTOR_DB": USE_VECTOR_DB,
        "USE_STREAMING": USE_STREAMING,
        "max_chunk_length": MAX_CHUNK_LENGTH,
        "flush_token_count": FLUSH_TOKEN_COUNT,
        "system_message": system_message,
        "next_cycle_seconds": next_cycle_seconds,
        
        # Provider Selection
        "LLM_PROVIDER": LLM_PROVIDER,
        
        # Legacy Support
        "USE_LOCAL_LLM": USE_LOCAL_LLM or LLM_PROVIDER != "openai",
        "LLM_API_URL": LLM_API_URL,
        "LLM_STREAM_URL": LLM_STREAM_URL,
        
        # OpenAI Configuration
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENAI_MODEL": OPENAI_MODEL,
        
        # Ollama Configuration
        "OLLAMA_API_ENDPOINT": OLLAMA_API_ENDPOINT,
        "OLLAMA_MODEL": OLLAMA_MODEL,
        "OLLAMA_STREAMING": OLLAMA_STREAMING,
    }


def get_tts_config():
    """
    Returns a dictionary of TTS configuration parameters.
    """
    return {
        # Provider Selection
        "TTS_PROVIDER": TTS_PROVIDER,
        
        # Legacy Support
        "USE_LOCAL_AUDIO": USE_LOCAL_AUDIO or TTS_PROVIDER == "local",
        "DEFAULT_VOICE_NAME": DEFAULT_VOICE_NAME,
        "LOCAL_TTS_URL": LOCAL_TTS_URL,
        
        # Kokoro Configuration
        "KOKORO_TTS_SERVER_URL": KOKORO_TTS_SERVER_URL,
        "KOKORO_DEFAULT_VOICE": KOKORO_DEFAULT_VOICE,
        "KOKORO_TTS_TIMEOUT": KOKORO_TTS_TIMEOUT,
        "KOKORO_TTS_LANGUAGE": KOKORO_TTS_LANGUAGE,
        
        # ElevenLabs Configuration
        "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
        
        # Other Settings
        "USE_COMBINED_ENDPOINT": USE_COMBINED_ENDPOINT,
    }


def setup_warnings():
    """
    Set up warnings and logging configuration.
    """
    import warnings
    import logging
    
    # Suppress specific warnings
    warnings.filterwarnings(
        "ignore", 
        message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work"
    )
    
    # Configure logging for TTS
    logging.getLogger("utils.tts").setLevel(logging.INFO)
