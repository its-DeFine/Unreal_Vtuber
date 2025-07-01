"""
Base provider interfaces for the NeuroSync system.
Provides standardized interfaces for LLM, TTS, and Animation providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import asyncio
from enum import Enum


class ProviderStatus(Enum):
    """Provider status enumeration"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ProviderInfo:
    """Information about a provider"""
    name: str
    type: str  # llm, tts, animation
    status: ProviderStatus
    capabilities: Dict[str, Any]
    health_info: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """Base interface for all providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.status = ProviderStatus.UNINITIALIZED
        self.name = config.get('name', self.__class__.__name__)
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider.
        Returns True if initialization successful, False otherwise.
        """
        pass
        
    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the provider"""
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check provider health.
        Returns dict with keys: 'healthy' (bool), 'message' (str), 'details' (dict)
        """
        pass
        
    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Get provider information"""
        pass
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()


class LLMProvider(BaseProvider):
    """Base LLM provider interface"""
    
    @abstractmethod
    async def generate(self, 
                      prompt: str, 
                      context: Optional[Dict[str, Any]] = None,
                      **kwargs) -> str:
        """
        Generate text response from prompt.
        
        Args:
            prompt: The input prompt
            context: Optional context dictionary
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
        
    @abstractmethod
    async def generate_stream(self,
                            prompt: str,
                            context: Optional[Dict[str, Any]] = None,
                            **kwargs) -> asyncio.Queue:
        """
        Generate streaming text response.
        
        Returns:
            Queue that will receive text chunks
        """
        pass
        
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return provider capabilities.
        
        Expected keys:
        - streaming: bool
        - max_tokens: int
        - models: List[str]
        - supports_functions: bool
        - supports_images: bool
        """
        pass
        
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        pass


class TTSProvider(BaseProvider):
    """Base TTS provider interface"""
    
    @abstractmethod
    async def generate_audio(self, 
                           text: str, 
                           voice: Optional[str] = None,
                           **kwargs) -> bytes:
        """
        Generate audio from text.
        
        Args:
            text: Text to synthesize
            voice: Optional voice ID/name
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Audio data as bytes (WAV format)
        """
        pass
        
    @abstractmethod
    async def generate_audio_stream(self,
                                  text: str,
                                  voice: Optional[str] = None,
                                  **kwargs) -> asyncio.Queue:
        """
        Generate streaming audio.
        
        Returns:
            Queue that will receive audio chunks
        """
        pass
        
    @abstractmethod
    def get_voices(self) -> List[Dict[str, str]]:
        """
        Get available voices.
        
        Returns:
            List of dicts with keys: 'id', 'name', 'gender', 'language'
        """
        pass
        
    @abstractmethod
    def get_audio_format(self) -> Dict[str, Any]:
        """
        Get audio format information.
        
        Expected keys:
        - sample_rate: int
        - channels: int
        - format: str (e.g., 'wav', 'mp3')
        """
        pass


class AnimationProvider(BaseProvider):
    """Base animation provider interface"""
    
    @abstractmethod
    async def generate_blendshapes(self, 
                                 audio_data: bytes,
                                 **kwargs) -> List[List[float]]:
        """
        Generate facial blendshapes from audio.
        
        Args:
            audio_data: Audio data in WAV format
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of blendshape frames, each frame is a list of float values
        """
        pass
        
    @abstractmethod
    async def generate_blendshapes_stream(self,
                                        audio_data: bytes,
                                        **kwargs) -> asyncio.Queue:
        """
        Generate streaming blendshapes.
        
        Returns:
            Queue that will receive blendshape frames
        """
        pass
        
    @abstractmethod
    def get_blendshape_names(self) -> List[str]:
        """Get ordered list of blendshape names"""
        pass
        
    @abstractmethod
    def get_animation_fps(self) -> int:
        """Get animation frames per second"""
        pass
        
    @abstractmethod
    async def process_with_emotion(self,
                                 audio_data: bytes,
                                 emotion: str,
                                 intensity: float = 1.0,
                                 **kwargs) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Generate blendshapes with emotion overlay.
        
        Returns:
            Tuple of (blendshape_frames, emotion_metadata)
        """
        pass


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderInitializationError(ProviderError):
    """Raised when provider fails to initialize"""
    pass


class ProviderNotReadyError(ProviderError):
    """Raised when provider is not ready for operations"""
    pass


class ProviderTimeoutError(ProviderError):
    """Raised when provider operation times out"""
    pass 