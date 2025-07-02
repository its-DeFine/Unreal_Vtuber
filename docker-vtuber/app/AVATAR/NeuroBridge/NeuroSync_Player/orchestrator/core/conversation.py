"""
Conversation History Management

Handles conversation history storage, retrieval, and management for the orchestrator.
"""

from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional


class ConversationHistory:
    """Manages conversation history with efficient storage and retrieval"""
    
    def __init__(self, max_turns: int = 1000):
        self.max_turns = max_turns
        self.turns: deque = deque(maxlen=max_turns)
    
    def add_turn(self, speaker: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a conversation turn"""
        turn = {
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.turns.append(turn)
    
    def get_recent_turns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        return list(self.turns)[-limit:]
    
    def get_turns_by_speaker(self, speaker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get turns by specific speaker"""
        speaker_turns = [t for t in self.turns if t['speaker'] == speaker]
        return speaker_turns[-limit:]
    
    def clear(self):
        """Clear conversation history"""
        self.turns.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export conversation history"""
        return {
            "turns": list(self.turns),
            "total_turns": len(self.turns)
        }
    
    def format_for_prompt(self, turns: List[Dict[str, Any]]) -> str:
        """Format conversation history for prompt"""
        formatted = []
        for turn in turns:
            speaker = turn['speaker'].capitalize()
            text = turn['text']
            formatted.append(f"{speaker}: {text}")
        
        return '\n'.join(formatted) 