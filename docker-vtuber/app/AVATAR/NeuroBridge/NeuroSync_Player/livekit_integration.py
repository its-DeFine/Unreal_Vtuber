#!/usr/bin/env python3
"""
LiveKit Integration for llm_to_face.py
Provides seamless integration between LiveKit real-time agent and S1 system
"""

import os
import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional
import threading
import queue
import time

logger = logging.getLogger(__name__)

# Configuration
USE_LIVEKIT = os.getenv("USE_LIVEKIT_AGENT", "false").lower() == "true"
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "ws://livekit-agent:8201")
ENABLE_LIVEKIT_BLENDSHAPES = os.getenv("ENABLE_LIVEKIT_BLENDSHAPES", "true").lower() == "true"

# Global WebSocket connection (singleton)
_livekit_ws = None
_livekit_lock = threading.Lock()
_event_loop = None
_loop_thread = None


class LiveKitIntegration:
    """
    Integration class for LiveKit real-time agent
    Handles WebSocket communication and response processing
    """
    
    def __init__(self):
        self.ws = None
        self.loop = None
        self.is_connected = False
        self.response_queue = queue.Queue()
        
    async def connect(self):
        """Connect to LiveKit agent"""
        try:
            logger.info(f"🎙️ Connecting to LiveKit at {LIVEKIT_WS_URL}")
            self.ws = await websockets.connect(LIVEKIT_WS_URL)
            self.is_connected = True
            logger.info("✅ Connected to LiveKit agent")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to LiveKit: {e}")
            self.is_connected = False
            return False
    
    async def process_text_async(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process text through LiveKit (async)"""
        if not self.is_connected:
            if not await self.connect():
                raise ConnectionError("Cannot connect to LiveKit agent")
        
        try:
            # Prepare message
            message = {
                "type": "text",
                "text": text,
                "context": context
            }
            
            # Send to LiveKit
            await self.ws.send(json.dumps(message))
            logger.info(f"📤 Sent to LiveKit: {text[:100]}...")
            
            # Wait for response
            response_data = await self.ws.recv()
            response = json.loads(response_data)
            
            logger.info(f"📥 LiveKit response: {response.get('response', '')[:100]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing with LiveKit: {e}")
            # Try to reconnect on next request
            self.is_connected = False
            raise
    
    def process_text(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process text through LiveKit (sync wrapper)"""
        # Run async function in event loop
        if not self.loop:
            self.loop = asyncio.new_event_loop()
            
        return self.loop.run_until_complete(
            self.process_text_async(text, context)
        )
    
    async def disconnect(self):
        """Disconnect from LiveKit"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            logger.info("🔌 Disconnected from LiveKit")


# Global singleton instance
_livekit_integration = None


def get_livekit_integration() -> Optional[LiveKitIntegration]:
    """Get or create LiveKit integration singleton"""
    global _livekit_integration
    
    if not USE_LIVEKIT:
        return None
        
    if _livekit_integration is None:
        _livekit_integration = LiveKitIntegration()
        
    return _livekit_integration


def process_with_livekit(
    user_input: str,
    chunk_queue,
    audio_queue,
    autonomous_context=None,
    direct_speech=False,
    **kwargs
) -> Dict[str, Any]:
    """
    Process text using LiveKit instead of traditional LLM
    
    This function:
    1. Sends text to LiveKit agent
    2. Gets response with emotion and blendshapes
    3. Puts response text into TTS queue
    4. Returns metadata for logging
    """
    
    if not USE_LIVEKIT:
        return None
        
    logger.info("🎙️ Processing with LiveKit real-time agent")
    
    try:
        # Get LiveKit integration
        livekit = get_livekit_integration()
        if not livekit:
            logger.error("LiveKit integration not available")
            return None
        
        # Process text through LiveKit
        result = livekit.process_text(
            text=user_input,
            context={
                "autonomous_context": autonomous_context,
                "direct_speech": direct_speech
            }
        )
        
        # Extract components
        response_text = result.get("response", "")
        emotion = result.get("emotion", "neutral")
        blendshapes = result.get("blendshapes", [])
        tcp_commands = result.get("tcp_commands", [])
        
        logger.info(f"✅ LiveKit generated: {len(response_text)} chars, {len(blendshapes)} frames")
        
        # Put response text into chunk queue for TTS processing
        if response_text and chunk_queue:
            # Clean the text for TTS
            cleaned_text = clean_text_for_tts(response_text)
            
            # Split into chunks if needed (for better streaming)
            chunks = split_into_chunks(cleaned_text)
            
            for chunk in chunks:
                chunk_queue.put(chunk)
                logger.info(f"📢 Queued for TTS: {chunk[:50]}...")
        
        # Handle blendshapes if enabled
        if ENABLE_LIVEKIT_BLENDSHAPES and blendshapes:
            # Send blendshapes to Unreal in background
            threading.Thread(
                target=send_blendshapes_to_unreal_async,
                args=(blendshapes,),
                daemon=True
            ).start()
            logger.info(f"📊 Sending {len(blendshapes)} blendshapes to Unreal")
        
        # Log emotion and commands
        logger.info(f"😊 Emotion: {emotion}, Commands: {tcp_commands}")
        
        # Return response data
        return {
            "status": "livekit_processed",
            "message": "Processed via LiveKit real-time agent",
            "response": response_text,
            "emotion": emotion,
            "blendshapes_count": len(blendshapes),
            "tcp_commands": tcp_commands,
            "llm_provider": "livekit"
        }
        
    except Exception as e:
        logger.error(f"❌ LiveKit processing failed: {e}")
        return None


def clean_text_for_tts(text: str) -> str:
    """Clean text for TTS processing"""
    if not text:
        return text
        
    # Remove asterisks and stage directions
    cleaned = text.replace('*', '')
    
    # Remove brackets
    cleaned = cleaned.replace('[', '').replace(']', '')
    cleaned = cleaned.replace('(', '').replace(')', '')
    
    # Clean up extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()


def split_into_chunks(text: str, max_chunk_size: int = 100) -> list:
    """Split text into chunks for streaming TTS"""
    if len(text) <= max_chunk_size:
        return [text]
        
    chunks = []
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            if current_chunk:
                current_chunk += ". "
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk + ".")
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk + ".")
        
    return chunks


def send_blendshapes_to_unreal_async(blendshapes: list):
    """Send blendshapes to Unreal in background"""
    try:
        # Import here to avoid circular dependency
        import sys
        import os
        
        # Add path for livekit modules
        livekit_path = "/app/NeuroBridge/NeuroSync_Player/livekit-agent/src"
        if os.path.exists(livekit_path) and livekit_path not in sys.path:
            sys.path.insert(0, livekit_path)
        
        from livekit_to_unreal_bridge import LiveKitToUnrealBridge
        
        # Create bridge and send
        bridge = LiveKitToUnrealBridge()
        
        if bridge.connect():
            success = bridge.send_blendshapes_to_unreal(blendshapes)
            if success:
                logger.info("✅ Blendshapes sent to Unreal")
            else:
                logger.warning("⚠️ Failed to send blendshapes to Unreal")
            bridge.disconnect()
        else:
            logger.warning("⚠️ Could not connect to Unreal (may not be running)")
            
    except Exception as e:
        logger.error(f"Error sending blendshapes: {e}")


def should_use_livekit(autonomous_context=None) -> bool:
    """
    Determine if LiveKit should be used for this request
    
    Returns True if:
    - LiveKit is enabled globally
    - Not a duplicate orchestrator request
    - Not from S2 system
    """
    if not USE_LIVEKIT:
        return False
    
    # Skip if this is from orchestrator (to prevent loops)
    if autonomous_context:
        context_str = str(autonomous_context)
        if any(x in context_str for x in ["orchestrator", "autogen", "s2_system"]):
            logger.info("Skipping LiveKit for orchestrator request")
            return False
    
    return True


# Integration function for llm_to_face.py
def integrate_livekit_with_llm_to_face(
    user_input: str,
    chat_history,
    full_history,
    llm_config,
    chunk_queue,
    audio_queue,
    vector_db_instance,
    base_system_message: str = "",
    autonomous_context=None,
    flush: bool = True
) -> Any:
    """
    Main integration function to be called from llm_to_face.py
    
    This replaces process_turn when LiveKit is enabled
    """
    
    if not should_use_livekit(autonomous_context):
        # Fall back to original process_turn
        from utils.llm.turn_processing import process_turn
        return process_turn(
            user_input, chat_history, full_history, llm_config,
            chunk_queue, audio_queue, vector_db_instance,
            base_system_message, autonomous_context, flush
        )
    
    # Process with LiveKit
    result = process_with_livekit(
        user_input=user_input,
        chunk_queue=chunk_queue,
        audio_queue=audio_queue,
        autonomous_context=autonomous_context
    )
    
    if result:
        # Update chat history with LiveKit response
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": result.get("response", "")})
        
        # Log to SCB if available
        from utils.scb import scb_store
        scb_store.append_chat(user_input, actor="user")
        scb_store.append_chat(result.get("response", ""), actor="assistant")
        
        return chat_history
    else:
        # Fall back to original if LiveKit fails
        logger.warning("LiveKit failed, falling back to traditional LLM")
        from utils.llm.turn_processing import process_turn
        return process_turn(
            user_input, chat_history, full_history, llm_config,
            chunk_queue, audio_queue, vector_db_instance,
            base_system_message, autonomous_context, flush
        )


# Initialization message
if USE_LIVEKIT:
    logger.info("🎙️ LiveKit integration enabled")
    logger.info(f"   WebSocket URL: {LIVEKIT_WS_URL}")
    logger.info(f"   Blendshapes: {'enabled' if ENABLE_LIVEKIT_BLENDSHAPES else 'disabled'}")
else:
    logger.info("📝 LiveKit integration disabled (using traditional LLM)")