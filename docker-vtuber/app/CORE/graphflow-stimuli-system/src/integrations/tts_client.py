"""
Text-to-Speech (TTS) Client for GraphFlow.

This module provides a client for text-to-speech synthesis, supporting
Kokoro TTS integration with audio processing time estimation and
comprehensive error handling.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, Tuple, Union, List
from datetime import datetime
import json
import base64
from pathlib import Path
import tempfile
import wave
import io

from ..utils.logging import get_structured_logger
from ..utils.metrics import MetricsCollector


class TTSResult:
    """Result from TTS synthesis."""
    
    def __init__(
        self,
        audio_data: bytes,
        format: str,
        duration: float,
        sample_rate: int,
        metadata: Dict[str, Any]
    ):
        """
        Initialize TTS result.
        
        Args:
            audio_data: Raw audio data bytes
            format: Audio format (wav, mp3, etc.)
            duration: Audio duration in seconds
            sample_rate: Sample rate in Hz
            metadata: Additional metadata
        """
        self.audio_data = audio_data
        self.format = format
        self.duration = duration
        self.sample_rate = sample_rate
        self.metadata = metadata
        self.timestamp = datetime.now()
        
    def to_base64(self) -> str:
        """Convert audio data to base64 string."""
        return base64.b64encode(self.audio_data).decode('utf-8')
        
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save audio data to file."""
        path = Path(file_path)
        path.write_bytes(self.audio_data)
        
    def get_size_mb(self) -> float:
        """Get audio data size in megabytes."""
        return len(self.audio_data) / (1024 * 1024)


class TTSClient:
    """
    Text-to-Speech client for audio synthesis.
    
    Supports:
    - Kokoro TTS integration
    - Multiple voice profiles
    - Emotion and style control
    - Audio format conversion
    - Processing time estimation
    - Caching for repeated text
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_voice: str = "kokoro",
        cache_enabled: bool = True,
        max_cache_size: int = 100
    ):
        """
        Initialize TTS client.
        
        Args:
            base_url: Optional base URL for TTS service
            default_voice: Default voice to use
            cache_enabled: Whether to enable caching
            max_cache_size: Maximum cache entries
        """
        self.base_url = base_url
        self.default_voice = default_voice
        self.cache_enabled = cache_enabled
        self.max_cache_size = max_cache_size
        
        self.logger = get_structured_logger("tts_client")
        self.metrics = MetricsCollector()
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache for TTS results
        self._cache: Dict[str, TTSResult] = {}
        self._cache_keys: list = []  # For LRU
        
        # Voice configuration
        self.voice_configs = {
            "kokoro": {
                "model": "kokoro-v0.19",
                "sample_rate": 24000,
                "format": "wav",
                "supports_emotions": True
            },
            "default": {
                "model": "espeak",
                "sample_rate": 22050,
                "format": "wav",
                "supports_emotions": False
            }
        }
        
        # Processing time estimation constants
        self.words_per_minute = 150  # Average speaking rate
        self.processing_overhead = 0.5  # Seconds of overhead
        
    async def initialize(self) -> None:
        """Initialize the TTS client."""
        if self.base_url and not self.session:
            timeout = aiohttp.ClientTimeout(total=60.0)  # Longer timeout for audio
            self.session = aiohttp.ClientSession(timeout=timeout)
            
        self.logger.info("TTS client initialized", default_voice=self.default_voice)
        
    async def close(self) -> None:
        """Close the TTS client."""
        if self.session:
            await self.session.close()
            self.session = None
            
        self._cache.clear()
        self._cache_keys.clear()
        
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        emotion: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        format: str = "wav",
        cache_key: Optional[str] = None
    ) -> TTSResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (defaults to default_voice)
            emotion: Optional emotion (happy, sad, angry, etc.)
            speed: Speech speed multiplier
            pitch: Pitch adjustment
            volume: Volume adjustment
            format: Output audio format
            cache_key: Optional cache key override
            
        Returns:
            TTSResult with audio data and metadata
        """
        # Use provided voice or default
        voice = voice or self.default_voice
        
        # Check cache
        if self.cache_enabled:
            cache_key = cache_key or self._generate_cache_key(
                text, voice, emotion, speed, pitch, volume, format
            )
            
            if cache_key in self._cache:
                self.logger.debug("TTS cache hit", cache_key=cache_key)
                self.metrics.increment_counter("tts_cache_hits")
                return self._cache[cache_key]
                
        # Record start time
        start_time = datetime.now()
        
        try:
            # Synthesize based on voice type
            if voice == "kokoro" and self.base_url:
                result = await self._synthesize_kokoro(
                    text, emotion, speed, pitch, volume, format
                )
            else:
                # Fallback to local TTS
                result = await self._synthesize_local(
                    text, voice, speed, pitch, volume, format
                )
                
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_tts_synthesis(
                voice=voice,
                text_length=len(text),
                audio_duration=result.duration,
                processing_time=duration
            )
            
            # Cache result
            if self.cache_enabled and cache_key:
                self._add_to_cache(cache_key, result)
                
            return result
            
        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}", voice=voice)
            raise
            
    async def estimate_duration(self, text: str) -> float:
        """
        Estimate audio duration for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated duration in seconds
        """
        # Count words
        words = len(text.split())
        
        # Calculate speaking time
        minutes = words / self.words_per_minute
        seconds = minutes * 60.0
        
        # Add small buffer for pauses
        return seconds * 1.1
        
    async def estimate_processing_time(self, text: str) -> float:
        """
        Estimate processing time for TTS synthesis.
        
        Args:
            text: Text to process
            
        Returns:
            Estimated processing time in seconds
        """
        # Estimate based on text length
        char_count = len(text)
        
        # Rough estimation: 0.01 seconds per character + overhead
        processing_time = (char_count * 0.01) + self.processing_overhead
        
        # Cap at reasonable maximum
        return min(processing_time, 10.0)
        
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices.
        
        Returns:
            List of voice configurations
        """
        voices = []
        
        # Add configured voices
        for voice_id, config in self.voice_configs.items():
            voices.append({
                "id": voice_id,
                "name": voice_id.capitalize(),
                "model": config["model"],
                "sample_rate": config["sample_rate"],
                "supports_emotions": config["supports_emotions"],
                "formats": [config["format"]]
            })
            
        # Query remote service if available
        if self.base_url and self.session:
            try:
                async with self.session.get(f"{self.base_url}/voices") as response:
                    if response.status == 200:
                        remote_voices = await response.json()
                        voices.extend(remote_voices.get("voices", []))
            except Exception as e:
                self.logger.warning(f"Failed to fetch remote voices: {e}")
                
        return voices
        
    async def validate_text(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate text for TTS synthesis.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check empty text
        if not text or not text.strip():
            return False, "Text cannot be empty"
            
        # Check length
        if len(text) > 5000:
            return False, "Text exceeds maximum length of 5000 characters"
            
        # Check for problematic characters
        if any(ord(char) > 127 for char in text) and not self._supports_unicode():
            return False, "Text contains unsupported Unicode characters"
            
        return True, None
        
    async def _synthesize_kokoro(
        self,
        text: str,
        emotion: Optional[str],
        speed: float,
        pitch: float,
        volume: float,
        format: str
    ) -> TTSResult:
        """Synthesize using Kokoro TTS service."""
        if not self.session:
            raise RuntimeError("HTTP session not initialized for Kokoro TTS")
            
        endpoint = f"{self.base_url}/synthesize"
        
        payload = {
            "text": text,
            "voice": "kokoro",
            "emotion": emotion,
            "speed": speed,
            "pitch": pitch,
            "volume": volume,
            "format": format
        }
        
        async with self.session.post(endpoint, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Kokoro TTS failed: {response.status} - {error_text}")
                
            # Get audio data
            audio_data = await response.read()
            
            # Parse response headers for metadata
            content_type = response.headers.get("Content-Type", "audio/wav")
            
            # Extract duration from audio data
            duration = self._extract_audio_duration(audio_data, format)
            
            # Get additional metadata if provided
            metadata = {}
            if "X-Audio-Metadata" in response.headers:
                try:
                    metadata = json.loads(response.headers["X-Audio-Metadata"])
                except:
                    pass
                    
            return TTSResult(
                audio_data=audio_data,
                format=format,
                duration=duration,
                sample_rate=self.voice_configs["kokoro"]["sample_rate"],
                metadata={
                    **metadata,
                    "voice": "kokoro",
                    "emotion": emotion,
                    "content_type": content_type
                }
            )
            
    async def _synthesize_local(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch: float,
        volume: float,
        format: str
    ) -> TTSResult:
        """Synthesize using local TTS engine."""
        # This is a placeholder for local TTS synthesis
        # In a real implementation, this would use pyttsx3, espeak, or similar
        
        # For now, create a simple stub
        duration = await self.estimate_duration(text)
        
        # Generate silent audio as placeholder
        sample_rate = self.voice_configs.get(voice, self.voice_configs["default"])["sample_rate"]
        num_samples = int(duration * sample_rate)
        
        # Create WAV data
        with io.BytesIO() as buffer:
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b'\x00' * (num_samples * 2))  # Silent audio
                
            audio_data = buffer.getvalue()
            
        return TTSResult(
            audio_data=audio_data,
            format=format,
            duration=duration,
            sample_rate=sample_rate,
            metadata={
                "voice": voice,
                "synthesizer": "local",
                "is_placeholder": True
            }
        )
        
    def _extract_audio_duration(self, audio_data: bytes, format: str) -> float:
        """Extract duration from audio data."""
        if format == "wav":
            try:
                with io.BytesIO(audio_data) as buffer:
                    with wave.open(buffer, 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        return frames / float(rate)
            except:
                # Fallback estimation
                return len(audio_data) / (44100 * 2)  # Assume 44.1kHz, 16-bit
        else:
            # For other formats, use rough estimation
            return len(audio_data) / (128 * 1024 / 8)  # Assume 128kbps
            
    def _generate_cache_key(
        self,
        text: str,
        voice: str,
        emotion: Optional[str],
        speed: float,
        pitch: float,
        volume: float,
        format: str
    ) -> str:
        """Generate cache key for TTS request."""
        # Create a unique key based on all parameters
        key_parts = [
            text[:100],  # First 100 chars of text
            voice,
            emotion or "none",
            f"{speed:.2f}",
            f"{pitch:.2f}", 
            f"{volume:.2f}",
            format
        ]
        
        return "|".join(key_parts)
        
    def _add_to_cache(self, key: str, result: TTSResult) -> None:
        """Add result to cache with LRU eviction."""
        if key in self._cache:
            # Move to end (most recently used)
            self._cache_keys.remove(key)
            self._cache_keys.append(key)
        else:
            # Add new entry
            self._cache[key] = result
            self._cache_keys.append(key)
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_cache_size:
                oldest_key = self._cache_keys.pop(0)
                del self._cache[oldest_key]
                
    def _supports_unicode(self) -> bool:
        """Check if current voice supports Unicode."""
        # Kokoro supports Unicode
        return self.default_voice == "kokoro"
        
    def clear_cache(self) -> None:
        """Clear the TTS cache."""
        self._cache.clear()
        self._cache_keys.clear()
        self.logger.info("TTS cache cleared")