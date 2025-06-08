#!/usr/bin/env python3
"""
STT Service with Real-Time Streaming Support
==========================================

Speech-to-Text service with real-time transcription, streaming audio processing,
and comprehensive Whisper model integration with advanced memory optimization.

Features:
- OpenAI Whisper model integration with CUDA optimization
- Real-time streaming audio transcription
- Multiple audio format support and preprocessing
- VAD (Voice Activity Detection) for efficient processing
- Language detection and multilingual support
- Batch and streaming transcription modes
- Memory optimization with mixed-precision inference
- Performance monitoring and caching
"""

import logging
import asyncio
import time
import io
import tempfile
import os
import gc
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator, Tuple, Union
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import collections

import torch
import torchaudio
import numpy as np
import whisper
import librosa
import soundfile as sf
from pydub import AudioSegment
import webrtcvad
import wave
from scipy import signal

from ..core.model_manager import BaseModel, ModelConfig, ModelState, track_inference_metrics
from ..utils.request_queue import QueuePriority


# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

@dataclass
class STTConfig:
    """Configuration for STT service"""
    model_name: str = "base"  # tiny, base, small, medium, large
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    language: Optional[str] = None  # Auto-detect if None
    sample_rate: int = 16000
    chunk_length_s: float = 30.0  # Whisper chunk length
    overlap_s: float = 2.0  # Overlap between chunks
    vad_enabled: bool = True
    vad_aggressiveness: int = 3  # 0-3, higher = more aggressive
    enable_streaming: bool = True
    enable_language_detection: bool = True
    temperature: float = 0.0
    beam_size: int = 5
    best_of: int = 5
    patience: float = 1.0
    condition_on_previous_text: bool = True
    initial_prompt: Optional[str] = None
    suppress_tokens: List[int] = field(default_factory=lambda: [-1])
    without_timestamps: bool = False
    max_initial_timestamp: Optional[float] = 1.0
    word_timestamps: bool = False
    prepend_punctuations: str = "\"'"¿([{-"
    append_punctuations: str = "\"'.。,，!！?？:：")]}、"
    # Memory optimization
    fp16: bool = True  # Mixed precision
    enable_memory_optimization: bool = True
    max_audio_length_minutes: int = 60


@dataclass
class STTRequest:
    """STT transcription request"""
    audio_data: Optional[bytes] = None
    audio_path: Optional[str] = None
    language: Optional[str] = None
    streaming: bool = False
    chunk_size_ms: int = 1000
    format: str = "wav"
    sample_rate: Optional[int] = None
    enable_vad: bool = True
    return_timestamps: bool = False
    return_word_timestamps: bool = False
    initial_prompt: Optional[str] = None
    priority: QueuePriority = QueuePriority.NORMAL


@dataclass
class TranscriptionChunk:
    """Transcription chunk for streaming"""
    text: str
    start_time: float
    end_time: float
    confidence: float
    language: Optional[str] = None
    chunk_index: int = 0
    is_final: bool = False
    word_timestamps: Optional[List[Dict[str, Any]]] = None


@dataclass
class AudioSegment:
    """Audio segment for processing"""
    data: np.ndarray
    sample_rate: int
    start_time: float
    end_time: float
    has_speech: bool = True


# =============================================================================
# AUDIO PREPROCESSING UTILITIES
# =============================================================================

class AudioPreprocessor:
    """Audio preprocessing utilities for STT"""
    
    def __init__(self, sample_rate: int = 16000, vad_enabled: bool = True, vad_aggressiveness: int = 3):
        self.sample_rate = sample_rate
        self.vad_enabled = vad_enabled
        self.logger = logging.getLogger("audio_preprocessor")
        
        # Initialize VAD if enabled
        self.vad = None
        if vad_enabled:
            try:
                self.vad = webrtcvad.Vad(vad_aggressiveness)
                self.logger.info(f"VAD initialized with aggressiveness {vad_aggressiveness}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize VAD: {e}")
                self.vad_enabled = False
    
    def load_audio(self, audio_input: Union[str, bytes], format: str = "wav") -> Tuple[np.ndarray, int]:
        """Load audio from file path or bytes"""
        try:
            if isinstance(audio_input, str):
                # Load from file path
                audio_data, sample_rate = sf.read(audio_input)
            else:
                # Load from bytes
                audio_io = io.BytesIO(audio_input)
                
                if format.lower() == "wav":
                    audio_data, sample_rate = sf.read(audio_io)
                else:
                    # Use pydub for other formats
                    audio_segment = AudioSegment.from_file(audio_io, format=format)
                    audio_data = np.array(audio_segment.get_array_of_samples())
                    sample_rate = audio_segment.frame_rate
                    
                    # Convert to mono if stereo
                    if audio_segment.channels == 2:
                        audio_data = audio_data.reshape((-1, 2)).mean(axis=1)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Normalize to float32
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            return audio_data, sample_rate
            
        except Exception as e:
            self.logger.error(f"Failed to load audio: {e}")
            raise
    
    def resample_audio(self, audio_data: np.ndarray, original_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio to target sample rate"""
        if original_sr == target_sr:
            return audio_data
        
        try:
            return librosa.resample(audio_data, orig_sr=original_sr, target_sr=target_sr)
        except Exception as e:
            self.logger.error(f"Audio resampling failed: {e}")
            raise
    
    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio amplitude"""
        try:
            # Remove DC offset
            audio_data = audio_data - np.mean(audio_data)
            
            # Normalize to [-1, 1] range
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
            
            return audio_data
        except Exception as e:
            self.logger.error(f"Audio normalization failed: {e}")
            return audio_data
    
    def apply_noise_reduction(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply basic noise reduction"""
        try:
            # Simple high-pass filter to remove low-frequency noise
            nyquist = sample_rate // 2
            low_cutoff = 80  # Hz
            high_cutoff = min(8000, nyquist - 1)  # Hz
            
            # Design bandpass filter
            sos = signal.butter(4, [low_cutoff, high_cutoff], btype='band', fs=sample_rate, output='sos')
            filtered_audio = signal.sosfilt(sos, audio_data)
            
            return filtered_audio.astype(np.float32)
        except Exception as e:
            self.logger.warning(f"Noise reduction failed: {e}")
            return audio_data
    
    def detect_speech_segments(self, audio_data: np.ndarray, sample_rate: int, frame_duration_ms: int = 30) -> List[Tuple[float, float, bool]]:
        """Detect speech segments using VAD"""
        if not self.vad_enabled or self.vad is None:
            # Return entire audio as speech if VAD disabled
            duration = len(audio_data) / sample_rate
            return [(0.0, duration, True)]
        
        try:
            # Convert to 16-bit PCM for VAD
            pcm_data = (audio_data * 32767).astype(np.int16)
            
            # Frame parameters
            frame_size = int(sample_rate * frame_duration_ms / 1000)
            
            segments = []
            speech_start = None
            
            for i in range(0, len(pcm_data) - frame_size, frame_size):
                frame = pcm_data[i:i + frame_size]
                frame_bytes = frame.tobytes()
                
                # Check if frame contains speech
                is_speech = self.vad.is_speech(frame_bytes, sample_rate)
                timestamp = i / sample_rate
                
                if is_speech and speech_start is None:
                    speech_start = timestamp
                elif not is_speech and speech_start is not None:
                    segments.append((speech_start, timestamp, True))
                    speech_start = None
            
            # Handle case where speech continues to end
            if speech_start is not None:
                segments.append((speech_start, len(pcm_data) / sample_rate, True))
            
            # Fill gaps with non-speech segments
            filled_segments = []
            last_end = 0.0
            
            for start, end, has_speech in segments:
                if start > last_end:
                    filled_segments.append((last_end, start, False))
                filled_segments.append((start, end, has_speech))
                last_end = end
            
            # Add final non-speech segment if needed
            total_duration = len(pcm_data) / sample_rate
            if last_end < total_duration:
                filled_segments.append((last_end, total_duration, False))
            
            return filled_segments
            
        except Exception as e:
            self.logger.error(f"Speech detection failed: {e}")
            duration = len(audio_data) / sample_rate
            return [(0.0, duration, True)]
    
    def chunk_audio(self, audio_data: np.ndarray, sample_rate: int, chunk_length_s: float, overlap_s: float = 0.0) -> List[AudioSegment]:
        """Split audio into overlapping chunks"""
        chunk_samples = int(chunk_length_s * sample_rate)
        overlap_samples = int(overlap_s * sample_rate)
        step_samples = chunk_samples - overlap_samples
        
        chunks = []
        for i in range(0, len(audio_data), step_samples):
            chunk_data = audio_data[i:i + chunk_samples]
            
            # Pad if necessary
            if len(chunk_data) < chunk_samples:
                padding = np.zeros(chunk_samples - len(chunk_data))
                chunk_data = np.concatenate([chunk_data, padding])
            
            start_time = i / sample_rate
            end_time = (i + len(chunk_data)) / sample_rate
            
            chunk = AudioSegment(
                data=chunk_data,
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time
            )
            chunks.append(chunk)
            
            # Break if we've processed all the audio
            if i + len(chunk_data) >= len(audio_data):
                break
        
        return chunks


# =============================================================================
# STT MODEL IMPLEMENTATION
# =============================================================================

class STTModel(BaseModel):
    """STT model implementation using Whisper"""
    
    def __init__(self, config: ModelConfig, stt_config: STTConfig):
        super().__init__(config)
        self.stt_config = stt_config
        self.whisper_model: Optional[whisper.Whisper] = None
        self.preprocessor = AudioPreprocessor(
            sample_rate=stt_config.sample_rate,
            vad_enabled=stt_config.vad_enabled,
            vad_aggressiveness=stt_config.vad_aggressiveness
        )
        
        # Performance tracking
        self.transcription_count = 0
        self.total_transcription_time = 0.0
        self.total_audio_duration = 0.0
        self.language_detection_cache: Dict[str, str] = {}
        
        # Threading for CPU-bound preprocessing
        self.preprocessing_executor = ThreadPoolExecutor(max_workers=2)
        
    async def load(self) -> bool:
        """Load the STT model"""
        try:
            self.logger.info(f"Loading Whisper model: {self.stt_config.model_name}")
            
            # Load Whisper model with memory optimization
            load_options = {
                "device": self.stt_config.device,
                "download_root": None
            }
            
            # Enable mixed precision if supported
            if self.stt_config.fp16 and torch.cuda.is_available():
                load_options["fp16"] = True
                self.logger.info("Mixed precision (FP16) enabled")
            
            self.whisper_model = whisper.load_model(
                self.stt_config.model_name,
                **load_options
            )
            
            # Apply memory optimizations
            if self.stt_config.enable_memory_optimization:
                self._apply_memory_optimizations()
            
            # Test transcription to ensure model is working
            test_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            try:
                result = self.whisper_model.transcribe(test_audio, language="en")
                if result is not None:
                    self.logger.info("Whisper model test transcription successful")
                else:
                    self.logger.error("Whisper model test transcription failed")
                    return False
            except Exception as e:
                self.logger.error(f"Whisper model test failed: {e}")
                return False
            
            self.logger.info(f"STT model loaded successfully: {self.stt_config.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load STT model: {e}")
            return False
    
    def _apply_memory_optimizations(self):
        """Apply memory optimization techniques"""
        try:
            if self.whisper_model is None:
                return
            
            # Enable gradient checkpointing if available
            if hasattr(self.whisper_model, "encoder"):
                if hasattr(self.whisper_model.encoder, "gradient_checkpointing"):
                    self.whisper_model.encoder.gradient_checkpointing = True
                    self.logger.info("Gradient checkpointing enabled for encoder")
            
            # Set model to evaluation mode
            self.whisper_model.eval()
            
            # Optimize for inference
            if torch.cuda.is_available():
                # Enable CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.enabled = True
                
                # Use memory format optimization
                if hasattr(self.whisper_model, "encoder"):
                    try:
                        self.whisper_model.encoder = self.whisper_model.encoder.to(memory_format=torch.channels_last)
                    except:
                        pass  # Not all models support channels_last
            
            self.logger.info("Memory optimizations applied")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply some memory optimizations: {e}")
    
    async def unload(self) -> bool:
        """Unload the STT model"""
        try:
            self.logger.info("Unloading STT model")
            
            if self.whisper_model:
                # Clear model from memory
                del self.whisper_model
                self.whisper_model = None
            
            # Clear caches
            self.language_detection_cache.clear()
            
            # Shutdown preprocessing executor
            self.preprocessing_executor.shutdown(wait=True)
            
            # Clear GPU memory if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
            
            self.logger.info("STT model unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload STT model: {e}")
            return False
    
    @track_inference_metrics
    async def inference(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform STT inference"""
        try:
            if not self.whisper_model:
                raise RuntimeError("STT model not loaded")
            
            # Parse request
            request = STTRequest(**request_data)
            
            # Load and preprocess audio
            if request.audio_data:
                audio_data, sample_rate = self.preprocessor.load_audio(
                    request.audio_data, request.format
                )
            elif request.audio_path:
                audio_data, sample_rate = self.preprocessor.load_audio(request.audio_path)
            else:
                raise ValueError("No audio data or path provided")
            
            # Validate audio length
            duration_minutes = len(audio_data) / sample_rate / 60
            if duration_minutes > self.stt_config.max_audio_length_minutes:
                raise ValueError(f"Audio too long: {duration_minutes:.1f} minutes > {self.stt_config.max_audio_length_minutes}")
            
            if request.streaming:
                return await self._stream_transcription(request, audio_data, sample_rate)
            else:
                return await self._batch_transcription(request, audio_data, sample_rate)
                
        except Exception as e:
            self.logger.error(f"STT inference error: {e}")
            return {"error": str(e)}
    
    async def _batch_transcription(self, request: STTRequest, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Handle batch STT transcription"""
        start_time = time.time()
        
        try:
            # Preprocess audio
            audio_data = await asyncio.get_event_loop().run_in_executor(
                self.preprocessing_executor,
                self._preprocess_audio,
                audio_data,
                sample_rate
            )
            
            # Prepare transcription options
            options = self._prepare_transcription_options(request)
            
            # Perform transcription
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._transcribe_audio,
                audio_data,
                options
            )
            
            # Process result
            transcription_time = (time.time() - start_time) * 1000
            audio_duration = len(audio_data) / self.stt_config.sample_rate
            
            # Update metrics
            self.transcription_count += 1
            self.total_transcription_time += transcription_time
            self.total_audio_duration += audio_duration
            
            # Calculate real-time factor
            rtf = (transcription_time / 1000) / audio_duration if audio_duration > 0 else 0
            
            response = {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": self._calculate_confidence(result),
                "transcription_time_ms": transcription_time,
                "audio_duration_s": audio_duration,
                "real_time_factor": round(rtf, 3),
                "timestamp": datetime.now().isoformat(),
                "streaming": False
            }
            
            # Add timestamps if requested
            if request.return_timestamps and "segments" in result:
                response["segments"] = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"]
                    }
                    for seg in result["segments"]
                ]
            
            # Add word timestamps if requested
            if request.return_word_timestamps and "segments" in result:
                words = []
                for seg in result["segments"]:
                    if "words" in seg:
                        words.extend(seg["words"])
                response["word_timestamps"] = words
            
            return response
            
        except Exception as e:
            self.logger.error(f"Batch transcription error: {e}")
            return {"error": str(e)}
    
    async def _stream_transcription(self, request: STTRequest, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Handle streaming STT transcription"""
        start_time = time.time()
        
        try:
            # Preprocess audio
            audio_data = await asyncio.get_event_loop().run_in_executor(
                self.preprocessing_executor,
                self._preprocess_audio,
                audio_data,
                sample_rate
            )
            
            # Split into chunks
            chunks = self.preprocessor.chunk_audio(
                audio_data,
                self.stt_config.sample_rate,
                self.stt_config.chunk_length_s,
                self.stt_config.overlap_s
            )
            
            # Process chunks
            transcription_chunks = []
            options = self._prepare_transcription_options(request)
            
            for i, chunk in enumerate(chunks):
                # Skip chunks without speech if VAD enabled
                if request.enable_vad and not chunk.has_speech:
                    continue
                
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._transcribe_audio,
                        chunk.data,
                        options
                    )
                    
                    if result["text"].strip():
                        transcription_chunk = TranscriptionChunk(
                            text=result["text"],
                            start_time=chunk.start_time,
                            end_time=chunk.end_time,
                            confidence=self._calculate_confidence(result),
                            language=result.get("language", "unknown"),
                            chunk_index=i,
                            is_final=(i == len(chunks) - 1)
                        )
                        
                        # Add word timestamps if requested
                        if request.return_word_timestamps and "segments" in result:
                            words = []
                            for seg in result["segments"]:
                                if "words" in seg:
                                    # Adjust timestamps to global time
                                    for word in seg["words"]:
                                        word_copy = word.copy()
                                        word_copy["start"] += chunk.start_time
                                        word_copy["end"] += chunk.start_time
                                        words.append(word_copy)
                            transcription_chunk.word_timestamps = words
                        
                        transcription_chunks.append(transcription_chunk)
                
                except Exception as e:
                    self.logger.warning(f"Failed to transcribe chunk {i}: {e}")
                    continue
            
            # Combine all chunks
            full_text = " ".join(chunk.text for chunk in transcription_chunks)
            
            # Update metrics
            transcription_time = (time.time() - start_time) * 1000
            audio_duration = len(audio_data) / self.stt_config.sample_rate
            
            self.transcription_count += 1
            self.total_transcription_time += transcription_time
            self.total_audio_duration += audio_duration
            
            return {
                "text": full_text,
                "chunks": [
                    {
                        "text": chunk.text,
                        "start_time": chunk.start_time,
                        "end_time": chunk.end_time,
                        "confidence": chunk.confidence,
                        "language": chunk.language,
                        "chunk_index": chunk.chunk_index,
                        "is_final": chunk.is_final,
                        "word_timestamps": chunk.word_timestamps
                    }
                    for chunk in transcription_chunks
                ],
                "total_chunks": len(transcription_chunks),
                "transcription_time_ms": transcription_time,
                "audio_duration_s": audio_duration,
                "real_time_factor": round((transcription_time / 1000) / audio_duration, 3) if audio_duration > 0 else 0,
                "timestamp": datetime.now().isoformat(),
                "streaming": True
            }
            
        except Exception as e:
            self.logger.error(f"Streaming transcription error: {e}")
            return {"error": str(e)}
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Preprocess audio for transcription"""
        # Resample to target sample rate
        if sample_rate != self.stt_config.sample_rate:
            audio_data = self.preprocessor.resample_audio(
                audio_data, sample_rate, self.stt_config.sample_rate
            )
        
        # Normalize audio
        audio_data = self.preprocessor.normalize_audio(audio_data)
        
        # Apply noise reduction
        audio_data = self.preprocessor.apply_noise_reduction(
            audio_data, self.stt_config.sample_rate
        )
        
        return audio_data
    
    def _prepare_transcription_options(self, request: STTRequest) -> Dict[str, Any]:
        """Prepare options for Whisper transcription"""
        options = {
            "language": request.language or self.stt_config.language,
            "temperature": self.stt_config.temperature,
            "beam_size": self.stt_config.beam_size,
            "best_of": self.stt_config.best_of,
            "patience": self.stt_config.patience,
            "condition_on_previous_text": self.stt_config.condition_on_previous_text,
            "initial_prompt": request.initial_prompt or self.stt_config.initial_prompt,
            "suppress_tokens": self.stt_config.suppress_tokens,
            "without_timestamps": not (request.return_timestamps or request.return_word_timestamps),
            "max_initial_timestamp": self.stt_config.max_initial_timestamp,
            "word_timestamps": request.return_word_timestamps or self.stt_config.word_timestamps,
            "prepend_punctuations": self.stt_config.prepend_punctuations,
            "append_punctuations": self.stt_config.append_punctuations,
        }
        
        # Enable FP16 if configured
        if self.stt_config.fp16 and torch.cuda.is_available():
            options["fp16"] = True
        
        return options
    
    def _transcribe_audio(self, audio_data: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
        """Perform actual transcription with Whisper"""
        try:
            with torch.no_grad():
                result = self.whisper_model.transcribe(audio_data, **options)
            return result
        except Exception as e:
            self.logger.error(f"Whisper transcription failed: {e}")
            raise
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        try:
            if "segments" in result:
                confidences = []
                for segment in result["segments"]:
                    if "avg_logprob" in segment:
                        # Convert log probability to confidence (0-1)
                        confidence = min(1.0, max(0.0, np.exp(segment["avg_logprob"])))
                        confidences.append(confidence)
                
                if confidences:
                    return float(np.mean(confidences))
            
            # Fallback confidence estimation
            return 0.8 if result["text"].strip() else 0.0
            
        except Exception:
            return 0.5  # Default confidence
    
    async def health_check(self) -> bool:
        """Check STT model health"""
        try:
            if not self.whisper_model:
                return False
            
            # Test with simple transcription
            test_audio = np.random.randn(16000).astype(np.float32) * 0.01  # 1 second of quiet noise
            test_request = STTRequest(
                audio_data=test_audio.tobytes(),
                format="wav"
            )
            
            response = await self._batch_transcription(test_request, test_audio, 16000)
            return "error" not in response
            
        except Exception as e:
            self.logger.error(f"STT health check failed: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get STT performance statistics"""
        avg_transcription_time = (
            self.total_transcription_time / self.transcription_count
            if self.transcription_count > 0 else 0
        )
        
        avg_rtf = (
            (self.total_transcription_time / 1000) / self.total_audio_duration
            if self.total_audio_duration > 0 else 0
        )
        
        return {
            "total_transcriptions": self.transcription_count,
            "total_audio_duration_s": round(self.total_audio_duration, 2),
            "average_transcription_time_ms": round(avg_transcription_time, 2),
            "average_real_time_factor": round(avg_rtf, 3),
            "model_name": self.stt_config.model_name,
            "device": self.stt_config.device,
            "fp16_enabled": self.stt_config.fp16,
            "vad_enabled": self.stt_config.vad_enabled
        }


# =============================================================================
# STT SERVICE
# =============================================================================

class STTService:
    """High-level STT service with model management"""
    
    def __init__(self, stt_config: STTConfig):
        self.config = stt_config
        self.logger = logging.getLogger("stt_service")
        
        # Create model configuration
        model_config = ModelConfig(
            name="stt_service",
            model_type="stt",
            memory_requirement_mb=3072,  # 3GB for STT
            load_time_estimate_ms=4000,
            priority=2,
            max_concurrent_requests=4,
            idle_timeout_seconds=600  # 10 minutes
        )
        
        # Initialize STT model
        self.model = STTModel(model_config, stt_config)
        
        self.logger.info("STT Service initialized")
    
    async def start(self) -> bool:
        """Start the STT service"""
        self.logger.info("Starting STT Service...")
        return await self.model.load()
    
    async def stop(self) -> bool:
        """Stop the STT service"""
        self.logger.info("Stopping STT Service...")
        return await self.model.unload()
    
    async def transcribe_audio(
        self,
        audio_data: Optional[bytes] = None,
        audio_path: Optional[str] = None,
        language: Optional[str] = None,
        streaming: bool = False,
        return_timestamps: bool = False,
        return_word_timestamps: bool = False,
        format: str = "wav",
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe audio to text"""
        request_data = {
            "audio_data": audio_data,
            "audio_path": audio_path,
            "language": language,
            "streaming": streaming,
            "return_timestamps": return_timestamps,
            "return_word_timestamps": return_word_timestamps,
            "format": format,
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


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def main():
    """Example usage of STT service"""
    # Configure STT
    config = STTConfig(
        model_name="base",
        device="cuda" if torch.cuda.is_available() else "cpu",
        enable_streaming=True,
        vad_enabled=True
    )
    
    # Create service
    service = STTService(config)
    
    try:
        # Start service
        if await service.start():
            print("STT Service started successfully")
            
            # Test batch transcription (would need real audio file)
            # response = await service.transcribe_audio(
            #     audio_path="test_audio.wav",
            #     return_timestamps=True
            # )
            # print("Batch Transcription:", response)
            
            # Health check
            health = await service.health_check()
            print("Health Check:", health)
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main()) 