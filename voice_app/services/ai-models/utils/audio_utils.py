#!/usr/bin/env python3
"""
Audio Utilities for AI Model Services
====================================

Common audio processing utilities and format handling for AI services.
Provides consistent audio processing across TTS and STT services.
"""

import logging
import io
import tempfile
import os
from enum import Enum
from dataclasses import dataclass
from typing import Union, Tuple, Optional, List
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment


# =============================================================================
# AUDIO FORMAT DEFINITIONS
# =============================================================================

class AudioFormat(Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    M4A = "m4a"
    AAC = "aac"


@dataclass
class AudioConfig:
    """Audio configuration parameters"""
    sample_rate: int = 22050
    channels: int = 1  # 1 = mono, 2 = stereo
    bit_depth: int = 16
    format: AudioFormat = AudioFormat.WAV
    normalize: bool = True
    remove_silence: bool = False


# =============================================================================
# AUDIO PROCESSOR
# =============================================================================

class AudioProcessor:
    """Comprehensive audio processing utilities"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.logger = logging.getLogger("audio_processor")
        
    def load_audio(
        self, 
        audio_input: Union[str, bytes, np.ndarray], 
        format: Optional[AudioFormat] = None,
        sample_rate: Optional[int] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio from various sources
        
        Args:
            audio_input: File path, bytes, or numpy array
            format: Audio format (if bytes input)
            sample_rate: Expected sample rate (if numpy input)
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            if isinstance(audio_input, str):
                # Load from file path
                audio_data, sr = sf.read(audio_input)
                self.logger.debug(f"Loaded audio from file: {audio_input}")
                
            elif isinstance(audio_input, bytes):
                # Load from bytes
                audio_io = io.BytesIO(audio_input)
                format_str = format.value if format else "wav"
                
                if format_str.lower() == "wav":
                    audio_data, sr = sf.read(audio_io)
                else:
                    # Use pydub for other formats
                    audio_segment = AudioSegment.from_file(audio_io, format=format_str)
                    audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                    sr = audio_segment.frame_rate
                    
                    # Convert to mono if stereo
                    if audio_segment.channels == 2:
                        audio_data = audio_data.reshape((-1, 2)).mean(axis=1)
                        
                self.logger.debug(f"Loaded audio from bytes ({format_str})")
                
            elif isinstance(audio_input, np.ndarray):
                # Use provided numpy array
                audio_data = audio_input.copy()
                sr = sample_rate or self.config.sample_rate
                self.logger.debug("Using provided numpy array")
                
            else:
                raise ValueError(f"Unsupported audio input type: {type(audio_input)}")
            
            # Convert to mono if stereo and config requires mono
            if len(audio_data.shape) > 1 and self.config.channels == 1:
                audio_data = audio_data.mean(axis=1)
            
            # Normalize to float32
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # Apply normalization if configured
            if self.config.normalize:
                audio_data = self.normalize_amplitude(audio_data)
            
            return audio_data, sr
            
        except Exception as e:
            self.logger.error(f"Failed to load audio: {e}")
            raise
    
    def save_audio(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int, 
        output_path: str,
        format: Optional[AudioFormat] = None,
        bitrate: str = "128k"
    ) -> bool:
        """
        Save audio to file
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate
            output_path: Output file path
            format: Audio format (auto-detected from extension if None)
            bitrate: Bitrate for compressed formats
            
        Returns:
            Success status
        """
        try:
            # Determine format from extension if not provided
            if format is None:
                extension = os.path.splitext(output_path)[1].lower().lstrip('.')
                try:
                    format = AudioFormat(extension)
                except ValueError:
                    format = AudioFormat.WAV
                    self.logger.warning(f"Unknown format '{extension}', using WAV")
            
            if format == AudioFormat.WAV:
                # Direct save for WAV
                sf.write(output_path, audio_data, sample_rate)
            else:
                # Use temporary WAV file and convert
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    sf.write(temp_wav.name, audio_data, sample_rate)
                    
                    # Convert using pydub
                    audio_segment = AudioSegment.from_wav(temp_wav.name)
                    
                    export_params = {"format": format.value}
                    if format in [AudioFormat.MP3, AudioFormat.AAC]:
                        export_params["bitrate"] = bitrate
                    
                    audio_segment.export(output_path, **export_params)
                    
                    # Clean up temp file
                    os.unlink(temp_wav.name)
            
            self.logger.info(f"Saved audio to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save audio: {e}")
            return False
    
    def convert_format(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        target_format: AudioFormat,
        bitrate: str = "128k"
    ) -> bytes:
        """
        Convert audio to different format
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate
            target_format: Target audio format
            bitrate: Bitrate for compressed formats
            
        Returns:
            Converted audio as bytes
        """
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                sf.write(temp_wav.name, audio_data, sample_rate)
                
                if target_format == AudioFormat.WAV:
                    # Read WAV file as bytes
                    with open(temp_wav.name, "rb") as f:
                        result = f.read()
                else:
                    # Convert using pydub
                    audio_segment = AudioSegment.from_wav(temp_wav.name)
                    
                    with tempfile.NamedTemporaryFile(suffix=f".{target_format.value}", delete=False) as temp_out:
                        export_params = {"format": target_format.value}
                        if target_format in [AudioFormat.MP3, AudioFormat.AAC]:
                            export_params["bitrate"] = bitrate
                        
                        audio_segment.export(temp_out.name, **export_params)
                        
                        with open(temp_out.name, "rb") as f:
                            result = f.read()
                        
                        os.unlink(temp_out.name)
                
                os.unlink(temp_wav.name)
                return result
                
        except Exception as e:
            self.logger.error(f"Audio format conversion failed: {e}")
            raise
    
    def resample(
        self, 
        audio_data: np.ndarray, 
        original_sr: int, 
        target_sr: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate
        
        Args:
            audio_data: Input audio data
            original_sr: Original sample rate
            target_sr: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if original_sr == target_sr:
            return audio_data
        
        try:
            return librosa.resample(audio_data, orig_sr=original_sr, target_sr=target_sr)
        except Exception as e:
            self.logger.error(f"Audio resampling failed: {e}")
            raise
    
    def normalize_amplitude(
        self, 
        audio_data: np.ndarray, 
        target_db: Optional[float] = None
    ) -> np.ndarray:
        """
        Normalize audio amplitude
        
        Args:
            audio_data: Input audio data
            target_db: Target dB level (None for peak normalization)
            
        Returns:
            Normalized audio data
        """
        try:
            if target_db is None:
                # Peak normalization to [-1, 1]
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    return audio_data / max_val
                return audio_data
            else:
                # RMS normalization to target dB
                rms = np.sqrt(np.mean(audio_data**2))
                if rms == 0:
                    return audio_data
                
                target_rms = 10**(target_db / 20)
                return audio_data * (target_rms / rms)
                
        except Exception as e:
            self.logger.error(f"Audio normalization failed: {e}")
            return audio_data
    
    def remove_dc_offset(self, audio_data: np.ndarray) -> np.ndarray:
        """Remove DC offset from audio"""
        return audio_data - np.mean(audio_data)
    
    def apply_fade(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        fade_in_ms: float = 0.0, 
        fade_out_ms: float = 0.0
    ) -> np.ndarray:
        """
        Apply fade in/out to audio
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate
            fade_in_ms: Fade in duration in milliseconds
            fade_out_ms: Fade out duration in milliseconds
            
        Returns:
            Audio with fade applied
        """
        try:
            result = audio_data.copy()
            
            # Apply fade in
            if fade_in_ms > 0:
                fade_in_samples = int(sample_rate * fade_in_ms / 1000)
                fade_in_samples = min(fade_in_samples, len(result))
                fade_curve = np.linspace(0, 1, fade_in_samples)
                result[:fade_in_samples] *= fade_curve
            
            # Apply fade out
            if fade_out_ms > 0:
                fade_out_samples = int(sample_rate * fade_out_ms / 1000)
                fade_out_samples = min(fade_out_samples, len(result))
                fade_curve = np.linspace(1, 0, fade_out_samples)
                result[-fade_out_samples:] *= fade_curve
            
            return result
            
        except Exception as e:
            self.logger.error(f"Fade application failed: {e}")
            return audio_data
    
    def trim_silence(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        threshold_db: float = -40.0,
        min_silence_ms: float = 100.0
    ) -> np.ndarray:
        """
        Trim silence from beginning and end of audio
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate
            threshold_db: Silence threshold in dB
            min_silence_ms: Minimum silence duration to trim
            
        Returns:
            Trimmed audio data
        """
        try:
            # Convert dB threshold to linear
            threshold_linear = 10**(threshold_db / 20)
            min_silence_samples = int(sample_rate * min_silence_ms / 1000)
            
            # Find non-silent regions
            abs_audio = np.abs(audio_data)
            non_silent = abs_audio > threshold_linear
            
            # Find start and end of non-silent regions
            non_silent_indices = np.where(non_silent)[0]
            
            if len(non_silent_indices) == 0:
                # All silence, return short silence
                return audio_data[:sample_rate // 10]  # 0.1 second
            
            start_idx = max(0, non_silent_indices[0] - min_silence_samples)
            end_idx = min(len(audio_data), non_silent_indices[-1] + min_silence_samples)
            
            return audio_data[start_idx:end_idx]
            
        except Exception as e:
            self.logger.error(f"Silence trimming failed: {e}")
            return audio_data
    
    def chunk_audio(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        chunk_duration_ms: float,
        overlap_ms: float = 0.0
    ) -> List[np.ndarray]:
        """
        Split audio into chunks
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate
            chunk_duration_ms: Chunk duration in milliseconds
            overlap_ms: Overlap between chunks in milliseconds
            
        Returns:
            List of audio chunks
        """
        chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        overlap_samples = int(sample_rate * overlap_ms / 1000)
        step_samples = chunk_samples - overlap_samples
        
        chunks = []
        for i in range(0, len(audio_data), step_samples):
            chunk = audio_data[i:i + chunk_samples]
            
            # Pad last chunk if necessary
            if len(chunk) < chunk_samples:
                padding = np.zeros(chunk_samples - len(chunk))
                chunk = np.concatenate([chunk, padding])
            
            chunks.append(chunk)
            
            # Break if we've processed all audio
            if i + len(chunk) >= len(audio_data):
                break
        
        return chunks
    
    def mix_audio(
        self, 
        audio_list: List[np.ndarray], 
        weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """
        Mix multiple audio signals
        
        Args:
            audio_list: List of audio arrays to mix
            weights: Optional weights for each audio signal
            
        Returns:
            Mixed audio data
        """
        if not audio_list:
            return np.array([])
        
        # Ensure all arrays have the same length
        max_length = max(len(audio) for audio in audio_list)
        padded_audio = []
        
        for audio in audio_list:
            if len(audio) < max_length:
                padding = np.zeros(max_length - len(audio))
                audio = np.concatenate([audio, padding])
            padded_audio.append(audio)
        
        # Apply weights if provided
        if weights:
            weights = weights[:len(padded_audio)]  # Trim to match audio count
            for i, weight in enumerate(weights):
                padded_audio[i] *= weight
        
        # Mix signals
        mixed = np.sum(padded_audio, axis=0)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 1.0:
            mixed = mixed / max_val
        
        return mixed.astype(np.float32)
    
    def get_audio_info(self, audio_data: np.ndarray, sample_rate: int) -> dict:
        """
        Get information about audio data
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate
            
        Returns:
            Dictionary with audio information
        """
        duration = len(audio_data) / sample_rate
        rms = np.sqrt(np.mean(audio_data**2))
        peak = np.max(np.abs(audio_data))
        
        # Calculate dB levels
        rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
        peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
        
        return {
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "num_samples": len(audio_data),
            "channels": 1 if len(audio_data.shape) == 1 else audio_data.shape[1],
            "dtype": str(audio_data.dtype),
            "rms": rms,
            "peak": peak,
            "rms_db": rms_db,
            "peak_db": peak_db,
            "dynamic_range_db": peak_db - rms_db if rms_db != -np.inf else 0
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_silence(duration_ms: float, sample_rate: int = 22050) -> np.ndarray:
    """Create silence of specified duration"""
    num_samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(num_samples, dtype=np.float32)


def create_tone(
    frequency: float, 
    duration_ms: float, 
    sample_rate: int = 22050,
    amplitude: float = 0.5
) -> np.ndarray:
    """Create a sine wave tone"""
    num_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, num_samples, False)
    tone = amplitude * np.sin(2 * np.pi * frequency * t)
    return tone.astype(np.float32)


def detect_clipping(audio_data: np.ndarray, threshold: float = 0.99) -> dict:
    """Detect audio clipping"""
    clipped_samples = np.sum(np.abs(audio_data) >= threshold)
    total_samples = len(audio_data)
    clipping_percentage = (clipped_samples / total_samples) * 100
    
    return {
        "clipped_samples": clipped_samples,
        "total_samples": total_samples,
        "clipping_percentage": clipping_percentage,
        "has_clipping": clipped_samples > 0
    } 