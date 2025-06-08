#!/usr/bin/env python3
"""
TTS Service with Real-Time Processing
===================================

Text-to-Speech service with real-time audio synthesis, streaming support,
voice cloning, and comprehensive audio processing capabilities using Coqui TTS.

Features:
- Real-time streaming audio synthesis
- Multiple voice models and configurations
- Voice cloning and speaker embedding
- Audio format conversion and optimization
- Batch processing for efficiency
- Performance monitoring and caching
- GPU acceleration with CUDA optimization
"""

import logging
import asyncio
import time
import io
import wave
import tempfile
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator, Tuple, Union
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

import torch
import torchaudio
import numpy as np
from TTS.api import TTS
from TTS.tts.configs.shared_configs import BaseDatasetConfig
from TTS.tts.datasets.formatters import ljspeech
import librosa
import soundfile as sf
from pydub import AudioSegment

from ..core.model_manager import BaseModel, ModelConfig, ModelState, track_inference_metrics
from ..utils.request_queue import QueuePriority


# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

@dataclass
class TTSConfig:
    """Configuration for TTS service"""
    model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    sample_rate: int = 22050
    audio_format: str = "wav"  # wav, mp3, flac
    chunk_size_ms: int = 100  # Streaming chunk size
    max_text_length: int = 1000
    enable_streaming: bool = True
    enable_voice_cloning: bool = False
    cache_enabled: bool = True
    cache_size_mb: int = 512
    speed_factor: float = 1.0  # Speech speed multiplier
    emotion: Optional[str] = None  # For models that support emotions
    language: str = "en"


@dataclass
class TTSRequest:
    """TTS synthesis request"""
    text: str
    voice_id: Optional[str] = None
    speed: Optional[float] = None
    emotion: Optional[str] = None
    output_format: str = "wav"
    streaming: bool = False
    language: Optional[str] = None
    speaker_embedding: Optional[np.ndarray] = None
    priority: QueuePriority = QueuePriority.NORMAL


@dataclass
class AudioChunk:
    """Audio chunk for streaming"""
    data: bytes
    sample_rate: int
    format: str
    chunk_index: int
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceProfile:
    """Voice profile for voice cloning"""
    voice_id: str
    name: str
    language: str
    gender: str
    speaker_embedding: np.ndarray
    sample_audio_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# AUDIO UTILITIES
# =============================================================================

class AudioProcessor:
    """Audio processing utilities for TTS"""
    
    @staticmethod
    def convert_format(
        audio_data: np.ndarray,
        sample_rate: int,
        target_format: str = "wav",
        bitrate: str = "128k"
    ) -> bytes:
        """Convert audio to different formats"""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                sf.write(temp_wav.name, audio_data, sample_rate)
                
                if target_format.lower() == "wav":
                    with open(temp_wav.name, "rb") as f:
                        result = f.read()
                else:
                    # Use pydub for format conversion
                    audio = AudioSegment.from_wav(temp_wav.name)
                    
                    with tempfile.NamedTemporaryFile(suffix=f".{target_format}", delete=False) as temp_out:
                        if target_format.lower() == "mp3":
                            audio.export(temp_out.name, format="mp3", bitrate=bitrate)
                        elif target_format.lower() == "flac":
                            audio.export(temp_out.name, format="flac")
                        else:
                            audio.export(temp_out.name, format=target_format)
                        
                        with open(temp_out.name, "rb") as f:
                            result = f.read()
                        
                        os.unlink(temp_out.name)
                
                os.unlink(temp_wav.name)
                return result
                
        except Exception as e:
            logging.error(f"Audio format conversion failed: {e}")
            raise
    
    @staticmethod
    def adjust_speed(audio_data: np.ndarray, sample_rate: int, speed_factor: float) -> np.ndarray:
        """Adjust audio playback speed"""
        if speed_factor == 1.0:
            return audio_data
        
        try:
            # Use librosa for time stretching
            return librosa.effects.time_stretch(audio_data, rate=speed_factor)
        except Exception as e:
            logging.error(f"Speed adjustment failed: {e}")
            return audio_data
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """Normalize audio to target dB level"""
        try:
            # Calculate current RMS
            rms = np.sqrt(np.mean(audio_data**2))
            
            if rms == 0:
                return audio_data
            
            # Convert target dB to linear scale
            target_rms = 10**(target_db / 20)
            
            # Apply normalization
            return audio_data * (target_rms / rms)
        except Exception as e:
            logging.error(f"Audio normalization failed: {e}")
            return audio_data
    
    @staticmethod
    def chunk_audio(
        audio_data: np.ndarray,
        sample_rate: int,
        chunk_size_ms: int = 100
    ) -> List[np.ndarray]:
        """Split audio into chunks for streaming"""
        chunk_size_samples = int(sample_rate * chunk_size_ms / 1000)
        chunks = []
        
        for i in range(0, len(audio_data), chunk_size_samples):
            chunk = audio_data[i:i + chunk_size_samples]
            chunks.append(chunk)
        
        return chunks


# =============================================================================
# TTS MODEL IMPLEMENTATION
# =============================================================================

class TTSModel(BaseModel):
    """TTS model implementation using Coqui TTS"""
    
    def __init__(self, config: ModelConfig, tts_config: TTSConfig):
        super().__init__(config)
        self.tts_config = tts_config
        self.tts_model: Optional[TTS] = None
        self.audio_processor = AudioProcessor()
        
        # Voice management
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        self.default_voice_id = "default"
        
        # Performance tracking
        self.synthesis_count = 0
        self.total_synthesis_time = 0.0
        self.total_characters_processed = 0
        self.cache: Dict[str, Tuple[np.ndarray, int]] = {}
        
        # Threading for CPU-bound audio processing
        self.audio_executor = ThreadPoolExecutor(max_workers=2)
        
    async def load(self) -> bool:
        """Load the TTS model"""
        try:
            self.logger.info(f"Loading TTS model: {self.tts_config.model_name}")
            
            # Initialize TTS model
            self.tts_model = TTS(
                model_name=self.tts_config.model_name,
                progress_bar=False,
                gpu=torch.cuda.is_available()
            )
            
            # Move to specified device
            if hasattr(self.tts_model, 'to'):
                self.tts_model.to(self.tts_config.device)
            
            # Test synthesis to ensure model is working
            test_text = "Hello, this is a test."
            try:
                test_audio = self._synthesize_audio(test_text)
                if test_audio is not None and len(test_audio) > 0:
                    self.logger.info("TTS model test synthesis successful")
                else:
                    self.logger.error("TTS model test synthesis failed")
                    return False
            except Exception as e:
                self.logger.error(f"TTS model test failed: {e}")
                return False
            
            self.logger.info(f"TTS model loaded successfully: {self.tts_config.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load TTS model: {e}")
            return False
    
    async def unload(self) -> bool:
        """Unload the TTS model"""
        try:
            self.logger.info("Unloading TTS model")
            
            if self.tts_model:
                # Clear model from memory
                del self.tts_model
                self.tts_model = None
            
            # Clear cache
            self.cache.clear()
            
            # Clear voice profiles
            self.voice_profiles.clear()
            
            # Shutdown audio processing executor
            self.audio_executor.shutdown(wait=True)
            
            # Clear GPU memory if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("TTS model unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload TTS model: {e}")
            return False
    
    @track_inference_metrics
    async def inference(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform TTS inference"""
        try:
            if not self.tts_model:
                raise RuntimeError("TTS model not loaded")
            
            # Parse request
            request = TTSRequest(**request_data)
            
            # Validate text length
            if len(request.text) > self.tts_config.max_text_length:
                raise ValueError(f"Text too long: {len(request.text)} > {self.tts_config.max_text_length}")
            
            if request.streaming:
                return await self._stream_synthesis(request)
            else:
                return await self._batch_synthesis(request)
                
        except Exception as e:
            self.logger.error(f"TTS inference error: {e}")
            return {"error": str(e)}
    
    async def _batch_synthesis(self, request: TTSRequest) -> Dict[str, Any]:
        """Handle batch TTS synthesis"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(request)
            if self.tts_config.cache_enabled and cache_key in self.cache:
                audio_data, sample_rate = self.cache[cache_key]
                self.logger.debug(f"Cache hit for TTS request: {cache_key[:50]}...")
            else:
                # Synthesize audio
                audio_data = self._synthesize_audio(
                    request.text,
                    speaker_embedding=request.speaker_embedding,
                    emotion=request.emotion,
                    language=request.language
                )
                
                if audio_data is None:
                    raise RuntimeError("Audio synthesis failed")
                
                sample_rate = self.tts_config.sample_rate
                
                # Cache result
                if self.tts_config.cache_enabled:
                    self.cache[cache_key] = (audio_data, sample_rate)
                    self._manage_cache_size()
            
            # Apply speed adjustment
            if request.speed and request.speed != 1.0:
                audio_data = self.audio_processor.adjust_speed(
                    audio_data, sample_rate, request.speed
                )
            
            # Normalize audio
            audio_data = self.audio_processor.normalize_audio(audio_data)
            
            # Convert to requested format
            audio_bytes = await asyncio.get_event_loop().run_in_executor(
                self.audio_executor,
                self.audio_processor.convert_format,
                audio_data,
                sample_rate,
                request.output_format
            )
            
            # Update metrics
            synthesis_time = (time.time() - start_time) * 1000
            self.synthesis_count += 1
            self.total_synthesis_time += synthesis_time
            self.total_characters_processed += len(request.text)
            
            # Calculate performance metrics
            chars_per_second = len(request.text) / (synthesis_time / 1000) if synthesis_time > 0 else 0
            
            return {
                "audio_data": audio_bytes,
                "sample_rate": sample_rate,
                "format": request.output_format,
                "synthesis_time_ms": synthesis_time,
                "text_length": len(request.text),
                "chars_per_second": round(chars_per_second, 2),
                "timestamp": datetime.now().isoformat(),
                "voice_id": request.voice_id or self.default_voice_id,
                "streaming": False
            }
            
        except Exception as e:
            self.logger.error(f"Batch synthesis error: {e}")
            return {"error": str(e)}
    
    async def _stream_synthesis(self, request: TTSRequest) -> Dict[str, Any]:
        """Handle streaming TTS synthesis"""
        start_time = time.time()
        
        try:
            # For now, synthesize full audio and chunk it
            # Real streaming would require model-level streaming support
            audio_data = self._synthesize_audio(
                request.text,
                speaker_embedding=request.speaker_embedding,
                emotion=request.emotion,
                language=request.language
            )
            
            if audio_data is None:
                raise RuntimeError("Audio synthesis failed")
            
            sample_rate = self.tts_config.sample_rate
            
            # Apply speed adjustment
            if request.speed and request.speed != 1.0:
                audio_data = self.audio_processor.adjust_speed(
                    audio_data, sample_rate, request.speed
                )
            
            # Normalize audio
            audio_data = self.audio_processor.normalize_audio(audio_data)
            
            # Split into chunks
            chunks = self.audio_processor.chunk_audio(
                audio_data, sample_rate, self.tts_config.chunk_size_ms
            )
            
            # Convert chunks to bytes
            audio_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_bytes = await asyncio.get_event_loop().run_in_executor(
                    self.audio_executor,
                    self.audio_processor.convert_format,
                    chunk,
                    sample_rate,
                    request.output_format
                )
                
                audio_chunk = AudioChunk(
                    data=chunk_bytes,
                    sample_rate=sample_rate,
                    format=request.output_format,
                    chunk_index=i,
                    is_final=(i == len(chunks) - 1)
                )
                audio_chunks.append(audio_chunk)
            
            # Update metrics
            synthesis_time = (time.time() - start_time) * 1000
            self.synthesis_count += 1
            self.total_synthesis_time += synthesis_time
            self.total_characters_processed += len(request.text)
            
            return {
                "chunks": [
                    {
                        "data": chunk.data,
                        "sample_rate": chunk.sample_rate,
                        "format": chunk.format,
                        "chunk_index": chunk.chunk_index,
                        "is_final": chunk.is_final
                    }
                    for chunk in audio_chunks
                ],
                "total_chunks": len(audio_chunks),
                "synthesis_time_ms": synthesis_time,
                "text_length": len(request.text),
                "timestamp": datetime.now().isoformat(),
                "voice_id": request.voice_id or self.default_voice_id,
                "streaming": True
            }
            
        except Exception as e:
            self.logger.error(f"Streaming synthesis error: {e}")
            return {"error": str(e)}
    
    def _synthesize_audio(
        self,
        text: str,
        speaker_embedding: Optional[np.ndarray] = None,
        emotion: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """Core audio synthesis using TTS model"""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Perform synthesis
                if speaker_embedding is not None:
                    # Use speaker embedding for voice cloning
                    self.tts_model.tts_to_file(
                        text=text,
                        file_path=temp_path,
                        speaker_embedding=speaker_embedding
                    )
                else:
                    # Standard synthesis
                    self.tts_model.tts_to_file(
                        text=text,
                        file_path=temp_path
                    )
                
                # Load synthesized audio
                audio_data, sample_rate = sf.read(temp_path)
                
                # Ensure sample rate matches configuration
                if sample_rate != self.tts_config.sample_rate:
                    audio_data = librosa.resample(
                        audio_data,
                        orig_sr=sample_rate,
                        target_sr=self.tts_config.sample_rate
                    )
                
                return audio_data.astype(np.float32)
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            self.logger.error(f"Audio synthesis failed: {e}")
            return None
    
    def _get_cache_key(self, request: TTSRequest) -> str:
        """Generate cache key for request"""
        key_components = [
            request.text,
            request.voice_id or self.default_voice_id,
            str(request.speed or 1.0),
            request.emotion or "",
            request.language or self.tts_config.language
        ]
        return "|".join(key_components)
    
    def _manage_cache_size(self):
        """Manage cache size to stay within limits"""
        if not self.tts_config.cache_enabled:
            return
        
        # Estimate cache size (rough approximation)
        estimated_size_mb = len(self.cache) * 1.0  # Assume ~1MB per cached item
        
        if estimated_size_mb > self.tts_config.cache_size_mb:
            # Remove oldest items (simple FIFO)
            items_to_remove = len(self.cache) // 4  # Remove 25%
            cache_keys = list(self.cache.keys())
            
            for key in cache_keys[:items_to_remove]:
                del self.cache[key]
            
            self.logger.info(f"Cache pruned: removed {items_to_remove} items")
    
    async def health_check(self) -> bool:
        """Check TTS model health"""
        try:
            if not self.tts_model:
                return False
            
            # Test with simple synthesis
            test_request = TTSRequest(
                text="Health check test.",
                output_format="wav"
            )
            
            response = await self._batch_synthesis(test_request)
            return "error" not in response and "audio_data" in response
            
        except Exception as e:
            self.logger.error(f"TTS health check failed: {e}")
            return False
    
    def add_voice_profile(self, voice_profile: VoiceProfile) -> bool:
        """Add a voice profile for voice cloning"""
        try:
            self.voice_profiles[voice_profile.voice_id] = voice_profile
            self.logger.info(f"Added voice profile: {voice_profile.voice_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add voice profile: {e}")
            return False
    
    def remove_voice_profile(self, voice_id: str) -> bool:
        """Remove a voice profile"""
        if voice_id in self.voice_profiles:
            del self.voice_profiles[voice_id]
            self.logger.info(f"Removed voice profile: {voice_id}")
            return True
        return False
    
    def get_voice_profiles(self) -> List[Dict[str, Any]]:
        """Get list of available voice profiles"""
        return [
            {
                "voice_id": profile.voice_id,
                "name": profile.name,
                "language": profile.language,
                "gender": profile.gender,
                "created_at": profile.created_at.isoformat()
            }
            for profile in self.voice_profiles.values()
        ]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get TTS performance statistics"""
        avg_synthesis_time = (
            self.total_synthesis_time / self.synthesis_count
            if self.synthesis_count > 0 else 0
        )
        
        avg_chars_per_second = (
            self.total_characters_processed / (self.total_synthesis_time / 1000)
            if self.total_synthesis_time > 0 else 0
        )
        
        return {
            "total_syntheses": self.synthesis_count,
            "total_characters_processed": self.total_characters_processed,
            "average_synthesis_time_ms": round(avg_synthesis_time, 2),
            "average_chars_per_second": round(avg_chars_per_second, 2),
            "cache_size": len(self.cache),
            "voice_profiles": len(self.voice_profiles),
            "model_name": self.tts_config.model_name,
            "device": self.tts_config.device
        }


# =============================================================================
# TTS SERVICE
# =============================================================================

class TTSService:
    """High-level TTS service with model management"""
    
    def __init__(self, tts_config: TTSConfig):
        self.config = tts_config
        self.logger = logging.getLogger("tts_service")
        
        # Create model configuration
        model_config = ModelConfig(
            name="tts_service",
            model_type="tts",
            memory_requirement_mb=2048,  # 2GB for TTS
            load_time_estimate_ms=3000,
            priority=2,
            max_concurrent_requests=6,
            idle_timeout_seconds=300  # 5 minutes
        )
        
        # Initialize TTS model
        self.model = TTSModel(model_config, tts_config)
        
        self.logger.info("TTS Service initialized")
    
    async def start(self) -> bool:
        """Start the TTS service"""
        self.logger.info("Starting TTS Service...")
        return await self.model.load()
    
    async def stop(self) -> bool:
        """Stop the TTS service"""
        self.logger.info("Stopping TTS Service...")
        return await self.model.unload()
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: Optional[float] = None,
        emotion: Optional[str] = None,
        output_format: str = "wav",
        streaming: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Synthesize speech from text"""
        request_data = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "emotion": emotion,
            "output_format": output_format,
            "streaming": streaming,
            **kwargs
        }
        
        return await self.model.inference(request_data)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        health_ok = await self.model.health_check()
        stats = self.model.get_performance_stats()
        
        return {
            "status": "healthy" if health_ok else "unhealthy",
            "model_loaded": self.model.state == ModelState.LOADED,
            "performance": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def add_voice(self, voice_profile: VoiceProfile) -> bool:
        """Add a voice profile for voice cloning"""
        return self.model.add_voice_profile(voice_profile)
    
    def remove_voice(self, voice_id: str) -> bool:
        """Remove a voice profile"""
        return self.model.remove_voice_profile(voice_id)
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voice profiles"""
        return self.model.get_voice_profiles()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def main():
    """Example usage of TTS service"""
    # Configure TTS
    config = TTSConfig(
        model_name="tts_models/en/ljspeech/tacotron2-DDC",
        device="cuda" if torch.cuda.is_available() else "cpu",
        enable_streaming=True
    )
    
    # Create service
    service = TTSService(config)
    
    try:
        # Start service
        if await service.start():
            print("TTS Service started successfully")
            
            # Test batch synthesis
            response = await service.synthesize_speech(
                text="Hello, this is a test of the text to speech system.",
                output_format="wav"
            )
            print("Batch Synthesis:", {k: v for k, v in response.items() if k != "audio_data"})
            
            # Test streaming synthesis
            stream_response = await service.synthesize_speech(
                text="This is a streaming test.",
                streaming=True
            )
            print("Streaming Synthesis:", {
                k: v for k, v in stream_response.items() 
                if k not in ["chunks"]
            })
            
            # Health check
            health = await service.health_check()
            print("Health Check:", health)
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main()) 