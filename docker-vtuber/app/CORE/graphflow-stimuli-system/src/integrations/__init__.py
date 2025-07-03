"""Integration interfaces for external systems."""

from .system1_interface import System1Interface
from .system2_interface import System2Interface
from .vtuber_client import VTuberClient
from .tts_client import TTSClient, TTSResult as TTSClientResult
from .models import (
    SystemStatus,
    CharacterInfo,
    TTSResult,
    SpeechRequest,
    AnimationRequest,
    QueueStatus,
    System1Response,
    AvatarState,
    SystemMode
)
from .autogen_client import AutoGenClient, AgentType, TaskStatus
from .agent_manager import AgentManager, LoadBalancingStrategy
from .cognee_client import CogneeClient, MemoryQuery, MemoryType

__all__ = [
    "System1Interface",
    "System2Interface",
    "VTuberClient",
    "TTSClient",
    "TTSClientResult",
    "SystemStatus",
    "CharacterInfo",
    "TTSResult",
    "SpeechRequest",
    "AnimationRequest",
    "QueueStatus",
    "System1Response",
    "AvatarState",
    "SystemMode",
    "AutoGenClient",
    "AgentType",
    "TaskStatus",
    "AgentManager",
    "LoadBalancingStrategy",
    "CogneeClient",
    "MemoryQuery",
    "MemoryType"
]