#!/usr/bin/env python3
"""
Kokoro TTS Server - Fixed Implementation
Provides text-to-speech functionality for VTuber agents
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import edge_tts
import asyncio
import base64
import io
import logging
from typing import Optional
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kokoro TTS Service", version="1.0.0")

# Available voices
VOICE_MAP = {
    "af_sarah": "en-US-AriaNeural",      # Female
    "af_john": "en-US-GuyNeural",        # Male
    "af_emma": "en-US-JennyNeural",      # Female
    "af_david": "en-US-DavisNeural",     # Male
    "default": "en-US-AriaNeural"
}

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "af_sarah"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"
    volume: Optional[str] = "+0%"

class TTSResponse(BaseModel):
    audio: str  # base64 encoded audio
    sample_rate: int
    duration: Optional[float] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "kokoro_tts", "version": "1.0.0"}

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using edge-tts
    Returns base64 encoded audio
    """
    try:
        # Validate input
        if not request.text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Get voice
        voice = VOICE_MAP.get(request.voice, VOICE_MAP["default"])
        
        logger.info(f"TTS request: {request.text[:50]}... with voice {voice}")
        
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Generate speech
            communicate = edge_tts.Communicate(
                request.text,
                voice,
                rate=request.rate,
                pitch=request.pitch,
                volume=request.volume
            )
            
            await communicate.save(tmp_path)
            
            # Read and encode audio
            with open(tmp_path, "rb") as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
            
            # Clean up
            os.unlink(tmp_path)
            
            return TTSResponse(
                audio=audio_base64,
                sample_rate=24000,  # edge-tts default
                duration=None  # Could calculate if needed
            )
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e
            
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices")
async def list_voices():
    """List available voices"""
    return {
        "voices": list(VOICE_MAP.keys()),
        "default": "af_sarah",
        "voice_map": VOICE_MAP
    }

@app.post("/tts/stream")
async def text_to_speech_stream(request: TTSRequest):
    """
    Stream TTS audio (for future real-time streaming)
    """
    # Placeholder for streaming implementation
    return {"message": "Streaming not yet implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8880)