"""Minimal SCBv2 client for S1 to read team SCB context"""

import os
import json
import time
import redis


class SCBv2MinimalClient:
    """Minimal client for S1 to read context from team SCB"""
    
    def __init__(self):
        url = os.getenv("REDIS_SCB_URL", "redis://redis_scb:6379/0")
        self._redis = redis.from_url(url, decode_responses=True)
    
    def get_team_context(self, team: str = "educator", max_events: int = 5) -> str:
        """Get recent context from team SCB as a formatted string"""
        try:
            # Read team SCB
            key = f"scb:team:{team}"
            raw = self._redis.get(key)
            if not raw:
                return ""
            
            events = json.loads(raw)
            if not events:
                return ""
            
            # Get last N events
            recent_events = events[-max_events:] if len(events) > max_events else events
            
            # Format as context string
            context_lines = []
            for event in recent_events:
                event_type = event.get("type", "unknown")
                content = event.get("content", event.get("text", ""))
                if content:
                    context_lines.append(f"[{event_type}] {content}")
            
            return "\n".join(context_lines) if context_lines else ""
            
        except Exception as e:
            print(f"[S1] Failed to read SCB context: {e}")
            return "" 