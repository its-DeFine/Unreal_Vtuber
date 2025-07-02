"""
Orchestrator Package

This package contains the reactive orchestrator system for NeuroSync Player.
Organized into clean modules for better maintainability.

Structure:
- core/: Core orchestrator logic and state management
- api/: API routes and endpoints  
- character/: Character management and configuration
"""

from .core.orchestrator import ReactiveOrchestrator
from .core.events import ExternalEvent, ReactiveState
from .core.conversation import ConversationHistory

__all__ = [
    'ReactiveOrchestrator',
    'ExternalEvent', 
    'ReactiveState',
    'ConversationHistory'
]

__version__ = '1.0.0' 