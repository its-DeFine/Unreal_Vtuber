#!/usr/bin/env python3
"""
AI Model Services Package
=========================

Comprehensive AI model management and services for voice applications.
Provides LLM, TTS, STT capabilities with advanced memory management,
performance monitoring, and reliability features.

Features:
- Model Manager with GPU memory optimization
- LLM Service with Ollama integration
- TTS Service with Coqui TTS and real-time streaming
- STT Service with Whisper and streaming transcription
- Dynamic model loading and management
- Performance metrics and monitoring
- Request queue management
- Fallback and error recovery systems
"""

# Core components
from .core.model_manager import (
    ModelManager,
    BaseModel,
    ModelState,
    ModelType,
    GPUMemoryManager
)

from .core.dynamic_loader import (
    DynamicModelLoader,
    LoadingStrategy,
    UnloadingStrategy,
    ModelPreloader
)

from .core.fallback_manager import (
    FallbackManager,
    FallbackStrategy,
    CircuitState,
    FallbackConfig,
    ModelFallbackEntry
)

# Service implementations
from .llm.llm_service import (
    LLMService,
    LLMModel,
    OllamaClient,
    ChatSession
)

from .tts.tts_service import (
    TTSService,
    TTSModel,
    AudioProcessor,
    VoiceCloner
)

from .stt.stt_service import (
    STTService,
    STTModel,
    WhisperProcessor,
    AudioVAD
)

# Utilities
from .utils.request_queue import (
    RequestQueue,
    RequestPriority,
    QueuedRequest
)

from .utils.performance_metrics import (
    PerformanceMetrics,
    MetricType,
    MetricUnit,
    TimingContext,
    timed_operation,
    async_timed_operation
)

from .utils.audio_utils import (
    AudioProcessor as AudioUtilsProcessor,
    AudioFormat,
    AudioConfig
)

from .utils.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheck
)


# Version information
__version__ = "1.0.0"
__author__ = "Voice App Development Team"
__description__ = "AI Model Services for Real-Time Voice Applications"


# Package-level exports
__all__ = [
    # Core components
    "ModelManager",
    "BaseModel", 
    "ModelState",
    "ModelType",
    "GPUMemoryManager",
    "DynamicModelLoader",
    "LoadingStrategy",
    "UnloadingStrategy", 
    "ModelPreloader",
    "FallbackManager",
    "FallbackStrategy",
    "CircuitState",
    "FallbackConfig",
    "ModelFallbackEntry",
    
    # Services
    "LLMService",
    "LLMModel", 
    "OllamaClient",
    "ChatSession",
    "TTSService",
    "TTSModel",
    "AudioProcessor",
    "VoiceCloner",
    "STTService",
    "STTModel",
    "WhisperProcessor",
    "AudioVAD",
    
    # Utilities
    "RequestQueue",
    "RequestPriority",
    "QueuedRequest",
    "PerformanceMetrics",
    "MetricType",
    "MetricUnit", 
    "TimingContext",
    "timed_operation",
    "async_timed_operation",
    "AudioUtilsProcessor",
    "AudioFormat",
    "AudioConfig",
    "HealthMonitor",
    "HealthStatus",
    "HealthCheck",
]


# Convenience factory functions
def create_model_manager(
    max_gpu_memory_gb: float = 8.0,
    enable_monitoring: bool = True
) -> ModelManager:
    """
    Create a configured ModelManager instance
    
    Args:
        max_gpu_memory_gb: Maximum GPU memory to use
        enable_monitoring: Enable performance monitoring
        
    Returns:
        Configured ModelManager instance
    """
    gpu_manager = GPUMemoryManager(max_memory_gb=max_gpu_memory_gb)
    
    if enable_monitoring:
        metrics = PerformanceMetrics("model_manager")
        return ModelManager(gpu_manager=gpu_manager, metrics=metrics)
    else:
        return ModelManager(gpu_manager=gpu_manager)


def create_llm_service(
    model_manager: ModelManager,
    primary_model: str = "llama3.2:7b",
    fallback_model: str = "llama3.2:3b",
    ollama_host: str = "http://localhost:11434"
) -> LLMService:
    """
    Create a configured LLM service
    
    Args:
        model_manager: ModelManager instance
        primary_model: Primary LLM model name
        fallback_model: Fallback LLM model name
        ollama_host: Ollama server host
        
    Returns:
        Configured LLMService instance
    """
    client = OllamaClient(host=ollama_host)
    return LLMService(
        model_manager=model_manager,
        ollama_client=client,
        primary_model=primary_model,
        fallback_model=fallback_model
    )


def create_tts_service(
    model_manager: ModelManager,
    model_name: str = "tts_models/en/ljspeech/tacotron2-DDC_ph",
    enable_voice_cloning: bool = True,
    cache_size_mb: int = 512
) -> TTSService:
    """
    Create a configured TTS service
    
    Args:
        model_manager: ModelManager instance
        model_name: TTS model name
        enable_voice_cloning: Enable voice cloning features
        cache_size_mb: Audio cache size in MB
        
    Returns:
        Configured TTSService instance
    """
    return TTSService(
        model_manager=model_manager,
        model_name=model_name,
        enable_voice_cloning=enable_voice_cloning,
        cache_size_mb=cache_size_mb
    )


def create_stt_service(
    model_manager: ModelManager,
    model_name: str = "openai/whisper-large-v3",
    enable_vad: bool = True,
    language: str = "en"
) -> STTService:
    """
    Create a configured STT service
    
    Args:
        model_manager: ModelManager instance  
        model_name: Whisper model name
        enable_vad: Enable voice activity detection
        language: Default language for transcription
        
    Returns:
        Configured STTService instance
    """
    return STTService(
        model_manager=model_manager,
        model_name=model_name,
        enable_vad=enable_vad,
        default_language=language
    )


def create_complete_ai_system(
    max_gpu_memory_gb: float = 8.0,
    llm_models: tuple = ("llama3.2:7b", "llama3.2:3b"),
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC_ph",
    stt_model: str = "openai/whisper-large-v3",
    ollama_host: str = "http://localhost:11434",
    enable_fallback: bool = True
) -> dict:
    """
    Create a complete AI system with all services
    
    Args:
        max_gpu_memory_gb: Maximum GPU memory to use
        llm_models: Tuple of (primary, fallback) LLM models
        tts_model: TTS model name
        stt_model: STT model name 
        ollama_host: Ollama server host
        enable_fallback: Enable fallback management
        
    Returns:
        Dictionary with all configured services
    """
    # Create core components
    model_manager = create_model_manager(max_gpu_memory_gb, True)
    performance_metrics = PerformanceMetrics("ai_system")
    request_queue = RequestQueue()
    
    # Create services
    llm_service = create_llm_service(
        model_manager, llm_models[0], llm_models[1], ollama_host
    )
    
    tts_service = create_tts_service(
        model_manager, tts_model, True, 512
    )
    
    stt_service = create_stt_service(
        model_manager, stt_model, True, "en"
    )
    
    # Create fallback manager if enabled
    fallback_manager = None
    if enable_fallback:
        fallback_manager = FallbackManager(
            model_manager, performance_metrics
        )
        
        # Register fallback chains
        fallback_manager.register_fallback_chain("llm", [
            (llm_models[0], 1, {"max_concurrent_requests": 5}),
            (llm_models[1], 2, {"max_concurrent_requests": 10})
        ])
        
        fallback_manager.register_fallback_chain("tts", [
            (tts_model, 1, {"max_concurrent_requests": 3})
        ])
        
        fallback_manager.register_fallback_chain("stt", [
            (stt_model, 1, {"max_concurrent_requests": 5})
        ])
    
    return {
        "model_manager": model_manager,
        "performance_metrics": performance_metrics,
        "request_queue": request_queue,
        "llm_service": llm_service,
        "tts_service": tts_service,
        "stt_service": stt_service,
        "fallback_manager": fallback_manager,
        "services": {
            "llm": llm_service,
            "tts": tts_service,
            "stt": stt_service
        }
    } 