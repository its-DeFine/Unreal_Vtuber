"""
Data models for System1 integration.

This module defines dataclasses and models used for System1 (Avatar/Speech)
integration responses and status information.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum


class AvatarState(Enum):
    """Avatar state enumeration."""
    IDLE = "idle"
    SPEAKING = "speaking"
    ANIMATING = "animating"
    LOADING = "loading"
    ERROR = "error"
    BUSY = "busy"


class SystemMode(Enum):
    """System operation mode."""
    REACTIVE = "reactive"
    AUTONOMOUS = "autonomous"


@dataclass
class SystemStatus:
    """
    System1 availability and status information.
    
    Attributes:
        is_available: Whether the system is available for requests
        avatar_state: Current avatar state
        mode: Current operation mode
        queue_size: Number of pending requests
        active_character: Currently loaded character ID
        error_message: Error message if system is unavailable
        last_activity: Timestamp of last activity
        metrics: Performance metrics
    """
    is_available: bool
    avatar_state: AvatarState = AvatarState.IDLE
    mode: SystemMode = SystemMode.REACTIVE
    queue_size: int = 0
    active_character: Optional[str] = None
    error_message: Optional[str] = None
    last_activity: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_busy(self) -> bool:
        """Check if system is busy."""
        return self.avatar_state in [AvatarState.SPEAKING, AvatarState.ANIMATING]
        
    @property
    def is_ready(self) -> bool:
        """Check if system is ready for new requests."""
        return self.is_available and self.avatar_state == AvatarState.IDLE
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_available": self.is_available,
            "avatar_state": self.avatar_state.value,
            "mode": self.mode.value,
            "queue_size": self.queue_size,
            "active_character": self.active_character,
            "error_message": self.error_message,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "metrics": self.metrics,
            "is_busy": self.is_busy,
            "is_ready": self.is_ready
        }


@dataclass
class CharacterInfo:
    """
    Character preset information.
    
    Attributes:
        character_id: Unique character identifier
        name: Display name
        description: Character description
        voice_profile: Voice configuration
        personality_traits: Personality characteristics
        emotional_range: Supported emotions
        animation_sets: Available animations
        metadata: Additional character data
    """
    character_id: str
    name: str
    description: str = ""
    voice_profile: Dict[str, Any] = field(default_factory=dict)
    personality_traits: List[str] = field(default_factory=list)
    emotional_range: List[str] = field(default_factory=list)
    animation_sets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def supports_emotion(self) -> bool:
        """Check if character supports emotional expressions."""
        return len(self.emotional_range) > 0
        
    def get_default_emotion(self) -> str:
        """Get default emotion for character."""
        return self.metadata.get("default_emotion", "neutral")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
            "voice_profile": self.voice_profile,
            "personality_traits": self.personality_traits,
            "emotional_range": self.emotional_range,
            "animation_sets": self.animation_sets,
            "metadata": self.metadata
        }


@dataclass
class TTSResult:
    """
    Text-to-speech synthesis result.
    
    Attributes:
        success: Whether synthesis was successful
        audio_url: URL to access synthesized audio
        audio_data: Raw audio data (if inline delivery)
        duration: Audio duration in seconds
        format: Audio format (wav, mp3, etc.)
        sample_rate: Sample rate in Hz
        voice_used: Voice profile used
        emotion_applied: Emotion applied to speech
        processing_time: Time taken to synthesize
        error_message: Error message if failed
    """
    success: bool
    audio_url: Optional[str] = None
    audio_data: Optional[bytes] = None
    duration: float = 0.0
    format: str = "wav"
    sample_rate: int = 24000
    voice_used: str = "default"
    emotion_applied: Optional[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    
    @property
    def has_audio(self) -> bool:
        """Check if result contains audio."""
        return self.success and (self.audio_url is not None or self.audio_data is not None)
        
    def get_size_mb(self) -> float:
        """Get audio size in megabytes."""
        if self.audio_data:
            return len(self.audio_data) / (1024 * 1024)
        return 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "audio_url": self.audio_url,
            "has_audio_data": self.audio_data is not None,
            "duration": self.duration,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "voice_used": self.voice_used,
            "emotion_applied": self.emotion_applied,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
            "size_mb": self.get_size_mb() if self.audio_data else None
        }


@dataclass
class SpeechRequest:
    """
    Speech synthesis request.
    
    Attributes:
        text: Text to synthesize
        character_id: Character to use
        emotion: Emotion to apply
        priority: Request priority
        animation: Animation to trigger
        metadata: Additional request metadata
    """
    text: str
    character_id: Optional[str] = None
    emotion: str = "neutral"
    priority: str = "normal"
    animation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate request parameters."""
        if not self.text or not self.text.strip():
            return False, "Text cannot be empty"
            
        if len(self.text) > 5000:
            return False, "Text exceeds maximum length"
            
        if self.priority not in ["high", "normal", "low"]:
            return False, f"Invalid priority: {self.priority}"
            
        return True, None


@dataclass
class AnimationRequest:
    """
    Animation trigger request.
    
    Attributes:
        animation_name: Name of animation to trigger
        duration: Duration override
        blend_time: Blend time with current animation
        loop: Whether to loop animation
        parameters: Animation-specific parameters
    """
    animation_name: str
    duration: Optional[float] = None
    blend_time: float = 0.5
    loop: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueStatus:
    """
    Processing queue status.
    
    Attributes:
        size: Current queue size
        estimated_wait_time: Estimated wait time in seconds
        position: Position in queue (if applicable)
        items: Queue items summary
    """
    size: int
    estimated_wait_time: float
    position: Optional[int] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.size == 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "size": self.size,
            "estimated_wait_time": self.estimated_wait_time,
            "position": self.position,
            "is_empty": self.is_empty,
            "items": self.items
        }


@dataclass
class System1Response:
    """
    Generic response from System1 operations.
    
    Attributes:
        success: Whether operation was successful
        operation: Operation performed
        result: Operation result data
        error: Error information if failed
        timestamp: Response timestamp
    """
    success: bool
    operation: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "operation": self.operation,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }