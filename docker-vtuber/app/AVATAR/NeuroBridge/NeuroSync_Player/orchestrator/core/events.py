"""
Event Management for Reactive Orchestrator

Contains event classes and state management for the orchestrator system.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque
from typing import Dict, Any, List


@dataclass
class ExternalEvent:
    """Represents an external input event"""
    id: str
    event_type: str  # email, calendar, task, chat, system
    source: str
    priority: str  # high, medium, low
    data: Dict[str, Any]
    timestamp: datetime
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "priority": self.priority,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed
        }


@dataclass
class ReactiveState:
    """Tracks the current state of the reactive system"""
    last_speech_time: float = 0.0
    last_response_text: str = ""
    recent_responses: deque = field(default_factory=lambda: deque(maxlen=20))
    event_queue: List[ExternalEvent] = field(default_factory=list)
    is_speaking: bool = False
    conversation_context: List[Dict[str, Any]] = field(default_factory=list)
    scb_context: str = None
    active_topic: str = None
    
    def add_response(self, text: str):
        """Add a response to history"""
        self.recent_responses.append({
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self.last_response_text = text
        self.last_speech_time = time.time() 