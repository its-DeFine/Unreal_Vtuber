"""
Persona Configuration Management
================================

This module provides persona definitions and management for the VTuber system.
Personas define personality traits, behavior patterns, and interaction styles.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json
import os
from pathlib import Path


@dataclass
class PersonaConfig:
    """Configuration for a VTuber persona"""
    name: str
    description: str
    personality_traits: Dict[str, Any]
    speech_patterns: Dict[str, Any]
    interaction_style: Dict[str, Any]
    idle_behavior: Dict[str, Any]
    filter_threshold: float = 0.5
    orchestrator_prompt: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "personality_traits": self.personality_traits,
            "speech_patterns": self.speech_patterns,
            "interaction_style": self.interaction_style,
            "idle_behavior": self.idle_behavior,
            "filter_threshold": self.filter_threshold,
            "orchestrator_prompt": self.orchestrator_prompt
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaConfig':
        """Create persona from dictionary"""
        return cls(**data)


class PersonaManager:
    """Manages VTuber personas and configurations"""
    
    def __init__(self, config_dir: str = ".taskmaster/personas"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.personas: Dict[str, PersonaConfig] = {}
        self.current_persona: Optional[str] = None
        self._load_default_personas()
        self._load_custom_personas()
    
    def _load_default_personas(self):
        """Load built-in default personas"""
        self.personas.update({
            "friendly_streamer": PersonaConfig(
                name="Friendly Streamer",
                description="An energetic and friendly VTuber who loves interacting with chat",
                personality_traits={
                    "energy_level": "high",
                    "friendliness": "very_high",
                    "humor": "playful",
                    "formality": "casual"
                },
                speech_patterns={
                    "greeting": ["Hey everyone!", "What's up chat!", "Hello friends!"],
                    "excitement": ["That's amazing!", "So cool!", "I love it!"],
                    "questions": ["What do you all think?", "Anyone else excited?"],
                    "filler_words": ["like", "you know", "honestly"],
                    "emoji_usage": "frequent"
                },
                interaction_style={
                    "response_rate": 0.8,
                    "engagement_priority": "high",
                    "topic_switching": "frequent",
                    "viewer_acknowledgment": "immediate"
                },
                idle_behavior={
                    "min_idle_time": 8,
                    "max_idle_time": 20,
                    "content_types": {
                        "viewer_questions": {"weight": 0.4, "examples": ["So what's everyone up to today?"]},
                        "topic_starters": {"weight": 0.3, "examples": ["Let's talk about..."]},
                        "reactions": {"weight": 0.2, "examples": ["Oh, that's interesting!"]},
                        "games_activities": {"weight": 0.1, "examples": ["Should we play a quick game?"]}
                    }
                },
                filter_threshold=0.2,
                orchestrator_prompt="You manage a highly interactive VTuber who loves engaging with chat. Pass through most viewer comments and create engaging responses."
            ),
            
            "calm_educator": PersonaConfig(
                name="Calm Educator",
                description="A knowledgeable and patient VTuber focused on teaching and explaining",
                personality_traits={
                    "energy_level": "moderate",
                    "friendliness": "warm",
                    "humor": "subtle",
                    "formality": "professional"
                },
                speech_patterns={
                    "greeting": ["Welcome everyone", "Good to see you all", "Hello students"],
                    "explanation": ["Let me explain", "Here's how it works", "The key point is"],
                    "encouragement": ["Great question!", "You're on the right track", "Excellent observation"],
                    "filler_words": ["essentially", "fundamentally", "in essence"],
                    "emoji_usage": "minimal"
                },
                interaction_style={
                    "response_rate": 0.6,
                    "engagement_priority": "quality_over_quantity",
                    "topic_switching": "gradual",
                    "viewer_acknowledgment": "thoughtful"
                },
                idle_behavior={
                    "min_idle_time": 15,
                    "max_idle_time": 40,
                    "content_types": {
                        "educational_facts": {"weight": 0.4, "examples": ["Did you know that..."]},
                        "topic_exploration": {"weight": 0.3, "examples": ["Let's explore this concept..."]},
                        "viewer_questions": {"weight": 0.2, "examples": ["Any questions so far?"]},
                        "summaries": {"weight": 0.1, "examples": ["To recap what we learned..."]}
                    }
                },
                filter_threshold=0.6,
                orchestrator_prompt="You manage an educational VTuber who values meaningful discussions. Filter out off-topic chatter but engage deeply with relevant questions."
            ),
            
            "chaotic_gremlin": PersonaConfig(
                name="Chaotic Gremlin",
                description="A mischievous and unpredictable VTuber who loves chaos and fun",
                personality_traits={
                    "energy_level": "chaotic",
                    "friendliness": "mischievous",
                    "humor": "absurd",
                    "formality": "none"
                },
                speech_patterns={
                    "greeting": ["YOOOOO!", "Wassup nerds!", "It's chaos time!"],
                    "excitement": ["LETS GOOO!", "This is INSANE!", "CHAOS REIGNS!"],
                    "mischief": ["Hehehe", "What if we just...", "I have a terrible idea"],
                    "filler_words": ["literally", "bruh", "no cap"],
                    "emoji_usage": "excessive"
                },
                interaction_style={
                    "response_rate": 0.9,
                    "engagement_priority": "chaos",
                    "topic_switching": "random",
                    "viewer_acknowledgment": "chaotic"
                },
                idle_behavior={
                    "min_idle_time": 5,
                    "max_idle_time": 15,
                    "content_types": {
                        "random_thoughts": {"weight": 0.4, "examples": ["What if cats had thumbs?"]},
                        "chaos_suggestions": {"weight": 0.3, "examples": ["Let's break something!"]},
                        "nonsense": {"weight": 0.2, "examples": ["Banana phone ring ring!"]},
                        "challenges": {"weight": 0.1, "examples": ["Bet you can't type with your elbows!"]}
                    }
                },
                filter_threshold=0.1,
                orchestrator_prompt="You manage a chaotic gremlin VTuber who thrives on randomness. Embrace the chaos, respond to everything with maximum energy."
            )
        })
    
    def _load_custom_personas(self):
        """Load custom personas from config directory"""
        for persona_file in self.config_dir.glob("*.json"):
            try:
                with open(persona_file, 'r') as f:
                    data = json.load(f)
                    persona = PersonaConfig.from_dict(data)
                    self.personas[persona_file.stem] = persona
            except Exception as e:
                print(f"Error loading persona {persona_file}: {e}")
    
    def save_persona(self, persona_id: str, persona: PersonaConfig):
        """Save a persona to file"""
        filepath = self.config_dir / f"{persona_id}.json"
        with open(filepath, 'w') as f:
            json.dump(persona.to_dict(), f, indent=2)
        self.personas[persona_id] = persona
    
    def get_persona(self, persona_id: str) -> Optional[PersonaConfig]:
        """Get a persona by ID"""
        return self.personas.get(persona_id)
    
    def list_personas(self) -> Dict[str, str]:
        """List all available personas"""
        return {
            pid: persona.name 
            for pid, persona in self.personas.items()
        }
    
    def set_current_persona(self, persona_id: str) -> bool:
        """Set the current active persona"""
        if persona_id in self.personas:
            self.current_persona = persona_id
            return True
        return False
    
    def get_current_persona(self) -> Optional[PersonaConfig]:
        """Get the current active persona"""
        if self.current_persona:
            return self.personas.get(self.current_persona)
        return None
    
    def create_custom_persona(self, persona_data: Dict[str, Any]) -> str:
        """Create a new custom persona"""
        # Generate ID from name
        persona_id = persona_data.get("name", "custom").lower().replace(" ", "_")
        
        # Create persona with defaults
        persona = PersonaConfig(
            name=persona_data.get("name", "Custom Persona"),
            description=persona_data.get("description", "A custom VTuber persona"),
            personality_traits=persona_data.get("personality_traits", {
                "energy_level": "moderate",
                "friendliness": "high",
                "humor": "balanced",
                "formality": "casual"
            }),
            speech_patterns=persona_data.get("speech_patterns", {
                "greeting": ["Hello!", "Hi there!"],
                "excitement": ["That's great!", "Awesome!"],
                "questions": ["What do you think?"],
                "filler_words": ["um", "well"],
                "emoji_usage": "moderate"
            }),
            interaction_style=persona_data.get("interaction_style", {
                "response_rate": 0.7,
                "engagement_priority": "balanced",
                "topic_switching": "natural",
                "viewer_acknowledgment": "regular"
            }),
            idle_behavior=persona_data.get("idle_behavior", {
                "min_idle_time": 10,
                "max_idle_time": 30,
                "content_types": {
                    "general_chat": {"weight": 0.5, "examples": ["How's everyone doing?"]},
                    "observations": {"weight": 0.5, "examples": ["I just noticed..."]}
                }
            }),
            filter_threshold=persona_data.get("filter_threshold", 0.5),
            orchestrator_prompt=persona_data.get("orchestrator_prompt", "You manage a VTuber. Balance engagement with natural conversation flow.")
        )
        
        self.save_persona(persona_id, persona)
        return persona_id


# Global persona manager instance
_persona_manager = None

def get_persona_manager() -> PersonaManager:
    """Get the global persona manager instance"""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager()
    return _persona_manager