"""
SCB Client for Autonomous Orchestrator
=====================================

This client enables the orchestrator to read from the Shared Cognitive Blackboard
to incorporate System 2 insights into its decision-making process.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .scb_store import scb_store


@dataclass
class SCBContext:
    """Structured context from SCB for orchestrator decision-making"""
    recent_directives: List[Dict[str, Any]]
    emotional_state: Optional[str]
    environmental_suggestions: List[str]
    high_salience_events: List[Dict[str, Any]]
    summary: str
    urgent_flags: List[str]


class OrchestratorSCBClient:
    """
    SCB Client specifically for the Autonomous Orchestrator
    
    This client:
    1. Reads directives and context from System 2
    2. Extracts relevant decision-making information
    3. Does NOT write to SCB (that's the speech LLM's job)
    """
    
    def __init__(self, max_entries: int = 50):
        self.logger = logging.getLogger("OrchestratorSCBClient")
        self.max_entries = max_entries
        self.last_read_time = 0
        
    def get_context_for_decision(self) -> SCBContext:
        """Get structured context from SCB for orchestrator decision-making"""
        
        try:
            # Get recent entries
            entries = scb_store.get_log_entries(self.max_entries)
            summary = scb_store.get_summary()
            
            # Extract different types of information
            recent_directives = []
            high_salience_events = []
            emotional_indicators = []
            environmental_suggestions = []
            urgent_flags = []
            
            current_time = time.time()
            
            for entry in entries:
                entry_type = entry.get("type", "")
                actor = entry.get("actor", "")
                text = entry.get("text", "")
                salience = entry.get("salience", 0.5)
                ttl = entry.get("ttl", 0)
                entry_time = entry.get("t", 0)
                
                # Skip expired entries
                if ttl > 0 and (current_time - entry_time) > ttl:
                    continue
                
                # Process directives from System 2
                if entry_type == "directive" and actor in ["planner", "system2", "autogen"]:
                    recent_directives.append(entry)
                    
                    # Check for urgent keywords
                    if any(word in text.lower() for word in ["urgent", "immediately", "critical", "important"]):
                        urgent_flags.append(text)
                        
                    # Check for environmental suggestions
                    if any(word in text.lower() for word in ["scene", "environment", "setting", "atmosphere"]):
                        environmental_suggestions.append(text)
                
                # High salience events (user interactions, important system events)
                if salience >= 0.7:
                    high_salience_events.append(entry)
                
                # Emotional indicators
                if "emotion" in text.lower() or "feeling" in text.lower():
                    emotional_indicators.append(text)
                    
            # Determine emotional state from indicators
            emotional_state = self._analyze_emotional_state(emotional_indicators)
            
            # Update last read time
            self.last_read_time = current_time
            
            return SCBContext(
                recent_directives=recent_directives[:5],  # Last 5 directives
                emotional_state=emotional_state,
                environmental_suggestions=environmental_suggestions[:3],
                high_salience_events=high_salience_events[:5],
                summary=summary,
                urgent_flags=urgent_flags
            )
            
        except Exception as e:
            self.logger.error(f"Error reading SCB context: {e}")
            # Return empty context on error
            return SCBContext(
                recent_directives=[],
                emotional_state=None,
                environmental_suggestions=[],
                high_salience_events=[],
                summary="",
                urgent_flags=[]
            )
    
    def _analyze_emotional_state(self, indicators: List[str]) -> Optional[str]:
        """Analyze emotional indicators to determine overall state"""
        
        if not indicators:
            return None
            
        # Simple keyword-based analysis
        emotions = {
            "excited": ["excited", "energetic", "enthusiastic", "happy"],
            "calm": ["calm", "peaceful", "relaxed", "serene"],
            "concerned": ["worried", "concerned", "anxious", "uncertain"],
            "curious": ["curious", "interested", "wondering", "questioning"],
            "focused": ["focused", "concentrated", "attentive", "engaged"]
        }
        
        emotion_scores = {emotion: 0 for emotion in emotions}
        
        for indicator in indicators:
            indicator_lower = indicator.lower()
            for emotion, keywords in emotions.items():
                for keyword in keywords:
                    if keyword in indicator_lower:
                        emotion_scores[emotion] += 1
                        
        # Return the highest scoring emotion
        if max(emotion_scores.values()) > 0:
            return max(emotion_scores, key=emotion_scores.get)
            
        return None
    
    def format_context_for_prompt(self, context: SCBContext) -> str:
        """Format SCB context into a prompt addition for the orchestrator"""
        
        prompt_parts = []
        
        # Add urgent flags
        if context.urgent_flags:
            prompt_parts.append(f"URGENT: {'; '.join(context.urgent_flags)}")
            
        # Add recent directives
        if context.recent_directives:
            directive_texts = [d.get("text", "") for d in context.recent_directives[:3]]
            prompt_parts.append(f"System 2 Guidance: {'; '.join(directive_texts)}")
            
        # Add emotional context
        if context.emotional_state:
            prompt_parts.append(f"Current emotional context: {context.emotional_state}")
            
        # Add environmental suggestions
        if context.environmental_suggestions:
            prompt_parts.append(f"Environmental suggestions: {', '.join(context.environmental_suggestions[:2])}")
            
        # Add high salience events summary
        if context.high_salience_events:
            event_summary = f"Recent important events: {len(context.high_salience_events)} high-priority interactions"
            prompt_parts.append(event_summary)
            
        # Add summary if meaningful
        if context.summary and len(context.summary) > 10:
            prompt_parts.append(f"Context summary: {context.summary[:100]}...")
            
        return "\n".join(prompt_parts) if prompt_parts else ""
    
    def should_check_scb(self) -> bool:
        """Determine if enough time has passed to check SCB again"""
        # Check every 2 seconds to avoid excessive reads
        return (time.time() - self.last_read_time) > 2.0 