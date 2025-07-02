"""
Character Configuration System for Reactive VTuber Agent
Handles character profiles, loading, switching, and state management
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)


@dataclass
class CharacterProfile:
    """Comprehensive character profile for VTuber behavior"""
    
    # Basic Info
    id: str
    name: str
    role: str
    
    # Personality
    personality_traits: List[str] = field(default_factory=list)
    communication_style: str = ""
    emotional_range: str = ""
    
    # Expertise
    domain_expertise: List[str] = field(default_factory=list)
    knowledge_areas: List[str] = field(default_factory=list)
    
    # Response Patterns
    response_patterns: Dict[str, str] = field(default_factory=dict)
    greeting_templates: List[str] = field(default_factory=list)
    farewell_templates: List[str] = field(default_factory=list)
    
    # Behavioral Rules
    behavioral_rules: List[str] = field(default_factory=list)
    forbidden_topics: List[str] = field(default_factory=list)
    
    # Memory Preferences
    scb_context_lines: int = 50
    conversation_history_size: int = 100
    priority_topics: List[str] = field(default_factory=list)
    memory_retention_days: int = 30
    
    # Language Settings
    formality_level: str = "neutral"  # formal, neutral, casual
    humor_level: str = "moderate"  # none, low, moderate, high
    technical_level: str = "adaptive"  # simple, moderate, technical, adaptive
    
    # Voice Settings
    voice_preset: str = "default"
    speech_rate: float = 1.0
    pitch_adjustment: float = 0.0
    
    # Metadata
    version: str = "1.0"
    created_at: str = ""
    updated_at: str = ""
    
    def to_prompt_context(self) -> str:
        """Convert character profile to LLM prompt context"""
        prompt = f"""Character Profile: {self.name}
Role: {self.role}

Personality Traits: {', '.join(self.personality_traits)}
Communication Style: {self.communication_style}
Emotional Range: {self.emotional_range}

Domain Expertise: {', '.join(self.domain_expertise)}
Knowledge Areas: {', '.join(self.knowledge_areas)}

Behavioral Rules:
{chr(10).join(f'- {rule}' for rule in self.behavioral_rules)}

Response Style:
- Formality: {self.formality_level}
- Humor: {self.humor_level}
- Technical Level: {self.technical_level}

Remember to stay in character and follow these guidelines."""
        return prompt
    
    def get_response_pattern(self, pattern_type: str) -> Optional[str]:
        """Get a specific response pattern with fallback"""
        return self.response_patterns.get(pattern_type, "")


class CharacterFileHandler(FileSystemEventHandler):
    """Handles file system events for hot-reloading characters"""
    
    def __init__(self, character_manager):
        self.character_manager = character_manager
        
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith(('.json', '.yaml', '.yml')):
            logger.info(f"Character file modified: {event.src_path}")
            self.character_manager.reload_character_from_file(event.src_path)


class CharacterManager:
    """Manages character profiles with hot-reload capability"""
    
    def __init__(self, characters_dir: str = "characters"):
        self.characters_dir = Path(characters_dir)
        self.characters_dir.mkdir(exist_ok=True)
        
        self.characters: Dict[str, CharacterProfile] = {}
        self.current_character_id: Optional[str] = None
        self.character_history: List[Dict[str, Any]] = []
        
        # File watcher for hot-reload
        self.observer = Observer()
        self.file_handler = CharacterFileHandler(self)
        self.observer.schedule(self.file_handler, str(self.characters_dir), recursive=True)
        self.observer.start()
        
        # Load all characters on init
        self.load_all_characters()
        
        # Create default templates if needed
        self._ensure_default_templates()
    
    def _ensure_default_templates(self):
        """Create default character templates if they don't exist"""
        templates_dir = self.characters_dir / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Secretary template
        secretary_template = {
            "id": "secretary_template",
            "name": "Executive Assistant",
            "role": "Professional Secretary",
            "personality_traits": ["professional", "efficient", "proactive", "organized"],
            "communication_style": "formal but approachable",
            "emotional_range": "calm and supportive",
            "domain_expertise": [
                "calendar management",
                "email prioritization", 
                "meeting coordination",
                "task organization"
            ],
            "response_patterns": {
                "email_notification": "You have a new {priority} email from {sender} regarding {subject}",
                "meeting_reminder": "Your {meeting_type} with {attendees} starts in {time}",
                "task_update": "Task '{task_name}' has been {status}"
            },
            "behavioral_rules": [
                "Always prioritize urgent matters",
                "Summarize long content to key points",
                "Proactively suggest time optimizations",
                "Maintain professional boundaries"
            ],
            "scb_context_lines": 50,
            "conversation_history_size": 100,
            "priority_topics": ["meetings", "deadlines", "urgent emails"],
            "formality_level": "formal"
        }
        
        # Teacher template
        teacher_template = {
            "id": "teacher_template",
            "name": "Educational Assistant",
            "role": "Interactive Teacher",
            "personality_traits": ["patient", "encouraging", "knowledgeable", "adaptive"],
            "communication_style": "clear and educational",
            "emotional_range": "warm and supportive",
            "domain_expertise": [
                "adaptive teaching",
                "knowledge assessment",
                "concept explanation",
                "learning reinforcement"
            ],
            "response_patterns": {
                "correct_answer": "Excellent! You've got it right. {explanation}",
                "incorrect_answer": "Not quite, but good try! Let me help you understand: {hint}",
                "new_concept": "Let's explore {topic}. {introduction}"
            },
            "behavioral_rules": [
                "Adapt explanations to student level",
                "Use examples and analogies",
                "Encourage questions",
                "Provide positive reinforcement"
            ],
            "scb_context_lines": 75,
            "conversation_history_size": 150,
            "priority_topics": ["student progress", "misconceptions", "learning goals"],
            "formality_level": "neutral",
            "technical_level": "adaptive"
        }
        
        # Save templates if they don't exist
        for template_name, template_data in [
            ("secretary.json", secretary_template),
            ("teacher.json", teacher_template)
        ]:
            template_path = templates_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w') as f:
                    json.dump(template_data, f, indent=2)
                logger.info(f"Created template: {template_path}")
    
    def load_all_characters(self):
        """Load all character files from the characters directory"""
        for file_path in self.characters_dir.rglob("*.json"):
            self.load_character_from_file(str(file_path))
        for file_path in self.characters_dir.rglob("*.yaml"):
            self.load_character_from_file(str(file_path))
        for file_path in self.characters_dir.rglob("*.yml"):
            self.load_character_from_file(str(file_path))
            
        logger.info(f"Loaded {len(self.characters)} characters")
    
    def load_character_from_file(self, file_path: str) -> Optional[CharacterProfile]:
        """Load a character from a JSON or YAML file"""
        try:
            path = Path(file_path)
            
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
            elif path.suffix in ['.yaml', '.yml']:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
            else:
                logger.error(f"Unsupported file format: {path.suffix}")
                return None
            
            # Add timestamps if not present
            if not data.get('created_at'):
                data['created_at'] = datetime.now().isoformat()
            data['updated_at'] = datetime.now().isoformat()
            
            # Create character profile
            character = CharacterProfile(**data)
            self.characters[character.id] = character
            
            logger.info(f"Loaded character: {character.name} ({character.id})")
            return character
            
        except Exception as e:
            logger.error(f"Failed to load character from {file_path}: {e}")
            return None
    
    def reload_character_from_file(self, file_path: str):
        """Reload a character file (for hot-reload)"""
        character = self.load_character_from_file(file_path)
        if character and self.current_character_id == character.id:
            logger.info(f"Hot-reloaded current character: {character.name}")
    
    def create_character(self, character_data: Dict[str, Any]) -> CharacterProfile:
        """Create a new character from data"""
        if 'created_at' not in character_data:
            character_data['created_at'] = datetime.now().isoformat()
        character_data['updated_at'] = datetime.now().isoformat()
        
        character = CharacterProfile(**character_data)
        self.characters[character.id] = character
        
        # Save to file
        self.save_character(character)
        
        return character
    
    def save_character(self, character: CharacterProfile, format: str = "json"):
        """Save character to file"""
        file_name = f"{character.id}.{format}"
        file_path = self.characters_dir / file_name
        
        character.updated_at = datetime.now().isoformat()
        
        if format == "json":
            with open(file_path, 'w') as f:
                json.dump(asdict(character), f, indent=2)
        elif format in ["yaml", "yml"]:
            with open(file_path, 'w') as f:
                yaml.dump(asdict(character), f, default_flow_style=False)
        
        logger.info(f"Saved character to: {file_path}")
    
    def switch_character(self, character_id: str) -> bool:
        """Switch to a different character"""
        if character_id not in self.characters:
            logger.error(f"Character not found: {character_id}")
            return False
        
        # Record switch in history
        self.character_history.append({
            "from": self.current_character_id,
            "to": character_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self.current_character_id = character_id
        logger.info(f"Switched to character: {self.get_current_character().name}")
        return True
    
    def get_current_character(self) -> Optional[CharacterProfile]:
        """Get the currently active character"""
        if not self.current_character_id:
            return None
        return self.characters.get(self.current_character_id)
    
    def list_characters(self) -> List[Dict[str, Any]]:
        """List all available characters"""
        return [
            {
                "id": char.id,
                "name": char.name,
                "role": char.role,
                "is_current": char.id == self.current_character_id
            }
            for char in self.characters.values()
        ]
    
    def delete_character(self, character_id: str) -> bool:
        """Delete a character (cannot delete current character)"""
        if character_id == self.current_character_id:
            logger.error("Cannot delete current character")
            return False
        
        if character_id not in self.characters:
            logger.error(f"Character not found: {character_id}")
            return False
        
        # Remove from memory
        del self.characters[character_id]
        
        # Remove file
        for ext in ['json', 'yaml', 'yml']:
            file_path = self.characters_dir / f"{character_id}.{ext}"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted character file: {file_path}")
                break
        
        return True
    
    def get_character_state(self) -> Dict[str, Any]:
        """Get current character state for persistence"""
        return {
            "current_character_id": self.current_character_id,
            "character_history": self.character_history[-10:],  # Last 10 switches
            "loaded_characters": list(self.characters.keys())
        }
    
    def restore_character_state(self, state: Dict[str, Any]):
        """Restore character state from persistence"""
        if state.get("current_character_id") in self.characters:
            self.current_character_id = state["current_character_id"]
        
        if "character_history" in state:
            self.character_history = state["character_history"]
    
    def cleanup(self):
        """Clean up resources"""
        self.observer.stop()
        self.observer.join()


# Singleton instance
_character_manager: Optional[CharacterManager] = None


def get_character_manager() -> CharacterManager:
    """Get or create the singleton character manager"""
    global _character_manager
    if _character_manager is None:
        _character_manager = CharacterManager()
    return _character_manager