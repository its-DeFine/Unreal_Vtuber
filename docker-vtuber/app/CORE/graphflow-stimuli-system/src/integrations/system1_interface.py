"""
System1 (Avatar/Speech) Interface for GraphFlow.

This module provides the interface for integrating with System1 (avatar and speech)
components, handling avatar responses, TTS, and character management.
"""

import asyncio
from typing import Dict, Any, Optional, Literal
from datetime import datetime

from ..config.settings import System1Config
from ..utils.logging import get_structured_logger
from .vtuber_client import VTuberClient
from .tts_client import TTSClient, TTSResult as TTSClientResult
from .models import (
    SystemStatus, CharacterInfo, TTSResult,
    AvatarState, SystemMode
)


class System1Interface:
    """
    Interface for System1 (Avatar/Speech) integration.
    
    Handles communication with:
    - VTuber avatar system
    - Text-to-speech engine
    - Character management
    - Mode switching
    """
    
    def __init__(self, config: System1Config):
        """
        Initialize System1 interface.
        
        Args:
            config: System1 configuration
        """
        self.config = config
        self.logger = get_structured_logger("system1_interface")
        
        # Initialize clients
        self.vtuber_client = VTuberClient(
            base_url=config.vtuber_endpoint,
            timeout=config.request_timeout,
            max_retries=config.max_retries
        )
        
        self.tts_client = TTSClient(
            base_url=config.tts_endpoint if hasattr(config, 'tts_endpoint') else None,
            default_voice=config.default_voice if hasattr(config, 'default_voice') else "kokoro"
        )
        
        # Cache for system status
        self._status_cache: Optional[SystemStatus] = None
        self._status_cache_ttl = 30  # seconds
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the System1 interface."""
        try:
            self.logger.info("Initializing System1 interface")
            
            # Initialize clients
            await self.vtuber_client.initialize()
            await self.tts_client.initialize()
            
            # Test connection
            status = await self.check_system_availability()
            if not status.is_available:
                self.logger.warning(
                    "System1 not available during initialization",
                    error=status.error_message
                )
            
            self.is_initialized = True
            self.logger.info("System1 interface initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize System1 interface: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the System1 interface."""
        self.logger.info("Shutting down System1 interface")
        
        try:
            await self.vtuber_client.close()
            await self.tts_client.close()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        self._status_cache = None
        self.is_initialized = False
    
    async def trigger_avatar_response(
        self, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Trigger avatar speech and animations.
        
        Args:
            content: Text content for speech
            metadata: Additional context for avatar control
            
        Returns:
            Success status of avatar activation
        """
        if not self.is_initialized:
            raise RuntimeError("System1 interface not initialized")
        
        try:
            # Determine emotion
            emotion = self._determine_emotion(content, metadata)
            
            # Trigger speech through VTuber client
            response = await self.vtuber_client.speak(
                text=content,
                character_id=metadata.get("character_id"),
                emotion=emotion,
                priority=metadata.get("priority", "normal"),
                metadata=metadata
            )
            
            if response.get("success", False):
                self.logger.info(
                    "Avatar response triggered successfully",
                    stimuli_id=metadata.get("stimuli_id"),
                    duration=response.get("estimated_duration")
                )
                return True
            else:
                self.logger.error(
                    "Avatar response failed",
                    error=response.get("error", "Unknown error")
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to trigger avatar response: {e}")
            return False
    
    async def check_system_availability(self) -> SystemStatus:
        """Check if System1 is available for requests."""
        # Check cache first
        if self._status_cache:
            cache_age = (datetime.now() - self._status_cache.last_activity).seconds if self._status_cache.last_activity else float('inf')
            if cache_age < self._status_cache_ttl:
                return self._status_cache
        
        if not self.is_initialized:
            return SystemStatus(
                is_available=False,
                error_message="Interface not initialized"
            )
        
        try:
            # Get status from VTuber client
            status_data = await self.vtuber_client.get_status()
            
            # Parse avatar state
            avatar_state = AvatarState.IDLE
            state_str = status_data.get("state", "idle").lower()
            for state in AvatarState:
                if state.value == state_str:
                    avatar_state = state
                    break
                    
            # Create status object
            status = SystemStatus(
                is_available=status_data.get("is_available", True),
                avatar_state=avatar_state,
                mode=SystemMode.REACTIVE,  # Will be updated when we get mode
                queue_size=status_data.get("queue_size", 0),
                active_character=status_data.get("active_character"),
                error_message=status_data.get("error"),
                last_activity=datetime.now(),
                metrics=status_data.get("metrics", {})
            )
            
        except Exception as e:
            self.logger.warning(f"System1 availability check failed: {e}")
            status = SystemStatus(
                is_available=False,
                error_message=str(e)
            )
        
        # Cache the result
        self._status_cache = status
        return status
    
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current avatar/speech system status."""
        if not self.is_initialized:
            return {"error": "Interface not initialized"}
        
        try:
            # Get detailed status from VTuber client
            detailed_status = await self.vtuber_client.get_detailed_status()
            
            # Also get current mode
            current_mode = await self.vtuber_client.get_mode()
            detailed_status["mode"] = current_mode
            
            return detailed_status
            
        except Exception as e:
            self.logger.error(f"Failed to get current status: {e}")
            return {
                "error": str(e),
                "is_speaking": False,
                "is_idle": True,
                "current_character": None,
                "mode": "unknown"
            }
    
    async def estimate_processing_time(self, content: str) -> float:
        """Estimate time required for processing content."""
        # Use TTS client for more accurate estimation
        tts_duration = await self.tts_client.estimate_duration(content)
        
        # Add processing overhead
        processing_time = await self.tts_client.estimate_processing_time(content)
        
        # Add animation buffer
        animation_buffer = 1.5
        
        return tts_duration + processing_time + animation_buffer
    
    async def load_character(self, character_id: str) -> bool:
        """Load a character preset by ID."""
        if not self.is_initialized:
            raise RuntimeError("System1 interface not initialized")
        
        try:
            # Get preset data if available
            preset_data = None
            if hasattr(self.config, 'character_presets') and self.config.character_presets:
                preset_data = self.config.character_presets.get(character_id)
                
            # Load character through VTuber client
            response = await self.vtuber_client.load_character(
                character_id=character_id,
                preset_data=preset_data
            )
            
            if response.get("success", False):
                self.logger.info(f"Character {character_id} loaded successfully")
                return True
            else:
                self.logger.error(
                    f"Failed to load character {character_id}",
                    error=response.get("error", "Unknown error")
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Character load error: {e}")
            return False
    
    async def set_mode(self, mode: Literal["reactive", "autonomous"]) -> bool:
        """Switch between reactive or autonomous mode."""
        if not self.is_initialized:
            raise RuntimeError("System1 interface not initialized")
        
        try:
            # Set mode through VTuber client
            response = await self.vtuber_client.set_mode(mode)
            
            if response.get("success", False):
                self.logger.info(f"Mode set to {mode}")
                
                # Clear status cache to force refresh
                self._status_cache = None
                
                return True
            else:
                self.logger.error(
                    f"Failed to set mode to {mode}",
                    error=response.get("error", "Unknown error")
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Mode change error: {e}")
            return False
    
    def _determine_emotion(self, content: str, metadata: Dict[str, Any]) -> str:
        """Determine appropriate emotion for avatar based on content."""
        # Simple emotion detection based on keywords
        content_lower = content.lower()
        
        # Check metadata for explicit emotion
        if "emotion" in metadata:
            return metadata["emotion"]
        
        # Keyword-based emotion detection
        if any(word in content_lower for word in ["happy", "joy", "great", "wonderful"]):
            return "happy"
        elif any(word in content_lower for word in ["sad", "sorry", "unfortunately"]):
            return "sad"
        elif any(word in content_lower for word in ["angry", "mad", "frustrated"]):
            return "angry"
        elif any(word in content_lower for word in ["surprise", "wow", "amazing"]):
            return "surprised"
        elif any(word in content_lower for word in ["think", "hmm", "consider"]):
            return "thinking"
        else:
            return "neutral"
    
    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> TTSResult:
        """
        Synthesize speech audio without triggering avatar.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional)
            emotion: Emotion to apply (optional)
            
        Returns:
            TTSResult with audio data
        """
        if not self.is_initialized:
            return TTSResult(
                success=False,
                error_message="Interface not initialized"
            )
        
        try:
            # Synthesize using TTS client
            tts_result = await self.tts_client.synthesize(
                text=text,
                voice=voice,
                emotion=emotion
            )
            
            # Convert to our TTSResult format
            return TTSResult(
                success=True,
                audio_data=tts_result.audio_data,
                duration=tts_result.duration,
                format=tts_result.format,
                sample_rate=tts_result.sample_rate,
                voice_used=voice or self.tts_client.default_voice,
                emotion_applied=emotion,
                processing_time=(datetime.now() - tts_result.timestamp).total_seconds()
            )
            
        except Exception as e:
            self.logger.error(f"Speech synthesis failed: {e}")
            return TTSResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_character_info(self, character_id: str) -> Optional[CharacterInfo]:
        """
        Get information about a specific character.
        
        Args:
            character_id: Character ID to query
            
        Returns:
            CharacterInfo if found, None otherwise
        """
        if not self.is_initialized:
            return None
        
        try:
            # Get character list
            characters = await self.vtuber_client.list_characters()
            
            # Find matching character
            for char_data in characters:
                if char_data.get("id") == character_id:
                    return CharacterInfo(
                        character_id=character_id,
                        name=char_data.get("name", character_id),
                        description=char_data.get("description", ""),
                        voice_profile=char_data.get("voice_profile", {}),
                        personality_traits=char_data.get("personality_traits", []),
                        emotional_range=char_data.get("emotional_range", []),
                        animation_sets=char_data.get("animation_sets", []),
                        metadata=char_data.get("metadata", {})
                    )
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get character info: {e}")
            return None
    
    async def stop_current_action(self) -> bool:
        """
        Stop current avatar speech/animation.
        
        Returns:
            Success status
        """
        if not self.is_initialized:
            return False
        
        try:
            response = await self.vtuber_client.stop_current_action()
            return response.get("success", False)
        except Exception as e:
            self.logger.error(f"Failed to stop current action: {e}")
            return False
    
    async def clear_queue(self) -> bool:
        """
        Clear the avatar action queue.
        
        Returns:
            Success status
        """
        if not self.is_initialized:
            return False
        
        try:
            response = await self.vtuber_client.clear_queue()
            return response.get("success", False)
        except Exception as e:
            self.logger.error(f"Failed to clear queue: {e}")
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Queue status information
        """
        if not self.is_initialized:
            return {"error": "Interface not initialized"}
        
        try:
            return await self.vtuber_client.get_queue_status()
        except Exception as e:
            self.logger.error(f"Failed to get queue status: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on System1 (Avatar/Speech) system.
        
        Returns:
            Health status information compatible with background task manager
        """
        if not self.is_initialized:
            return {
                "status": "unhealthy",
                "message": "Interface not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Use existing system availability check
            system_status = await self.check_system_availability()
            
            # Convert to format expected by background task manager
            if system_status.is_available:
                return {
                    "status": "healthy",
                    "message": "System1 (Avatar/Speech) is operational",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "avatar_state": system_status.avatar_state.value if system_status.avatar_state else "unknown",
                        "queue_size": system_status.queue_size,
                        "active_character": system_status.active_character,
                        "mode": system_status.mode.value if system_status.mode else "unknown",
                        "endpoint": self.config.vtuber_endpoint
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"System1 unavailable: {system_status.error_message}",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "error": system_status.error_message,
                        "endpoint": self.config.vtuber_endpoint
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": f"Health check error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "error": str(e),
                    "endpoint": self.config.vtuber_endpoint
                }
            }