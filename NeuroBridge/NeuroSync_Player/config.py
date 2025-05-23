# config.py
import os
import dotenv  # NEW

# -------------------------------------------------------------------
# Load .env file (if present) early so all subprocesses/modules see env vars
# -------------------------------------------------------------------

dotenv.load_dotenv()

USE_LOCAL_LLM = False
USE_STREAMING = True
LLM_API_URL = "http://127.0.0.1:5050/generate_llama"
LLM_STREAM_URL = "http://127.0.0.1:5050/generate_stream"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")

MAX_CHUNK_LENGTH = 500
FLUSH_TOKEN_COUNT = 300

DEFAULT_VOICE_NAME = 'Alice'
USE_LOCAL_AUDIO = False
LOCAL_TTS_URL = "http://127.0.0.1:8000/generate_speech" 
USE_COMBINED_ENDPOINT = False

ENABLE_EMOTE_CALLS = False
USE_VECTOR_DB = False


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

Be yourself - Livy - while being aware of and excited about the sophisticated system you're part of!

"""

# ---------------------------
# Emote Sender Configuration (new)
# ---------------------------
EMOTE_SERVER_ADDRESS = "127.0.0.1"
EMOTE_SERVER_PORT = 7777

# ---------------------------
# Transcription Server Configuration (new)
# ---------------------------
TRANSCRIPTION_SERVER_URL = "http://127.0.0.1:6969/transcribe"

# ---------------------------
# Embedding Configurations (new)
# ---------------------------
# Toggle between local embeddings and OpenAI embeddings.
USE_OPENAI_EMBEDDING = False
# Local embedding server URL:
EMBEDDING_LOCAL_SERVER_URL = "http://127.0.0.1:7070/get_embedding"
# OpenAI embedding model and size.
EMBEDDING_OPENAI_MODEL = "text-embedding-3-small"
LOCAL_EMBEDDING_SIZE = 768
OPENAI_EMBEDDING_SIZE = 1536

# ---------------------------
# Neurosync API Configurations (new)
# ---------------------------

NEUROSYNC_LOCAL_URL = "http://127.0.0.1:5000/audio_to_blendshapes" # if using the realtime api below, you can still access this endpoint from it, just change the port to 6969

# ---------------------------
# TTS with Blendshapes Endpoint (new)
# ---------------------------
TTS_WITH_BLENDSHAPES_REALTIME_API = "http://127.0.0.1:8000/synthesize_and_blendshapes"

### ignore these
NEUROSYNC_API_KEY = "YOUR-NEUROSYNC-API-KEY" # ignore this 
NEUROSYNC_REMOTE_URL = "https://api.neurosync.info/audio_to_blendshapes" #ignore this


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
    Returns a dictionary of LLM configuration parameters.
    
    If no system_message is provided, it defaults to BASE_SYSTEM_MESSAGE.
    """
    if system_message is None:
        system_message = BASE_SYSTEM_MESSAGE
    return {
        "USE_VECTOR_DB":USE_VECTOR_DB,
        "USE_LOCAL_LLM": USE_LOCAL_LLM,
        "USE_STREAMING": USE_STREAMING,
        "LLM_API_URL": LLM_API_URL,
        "LLM_STREAM_URL": LLM_STREAM_URL,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "max_chunk_length": MAX_CHUNK_LENGTH,
        "flush_token_count": FLUSH_TOKEN_COUNT,
        "system_message": system_message,
        "next_cycle_seconds": next_cycle_seconds,
    }


def setup_warnings():
    """
    Set up common warning filters.
    """
    import warnings
    warnings.filterwarnings(
        "ignore", 
        message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work"
    )
