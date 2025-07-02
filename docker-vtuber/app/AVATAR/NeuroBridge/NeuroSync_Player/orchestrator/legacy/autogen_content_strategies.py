"""
AutoGen Content Generation Strategies
====================================

This module implements sophisticated content generation strategies for autonomous VTuber
content. It manages variety, timing, and contextual relevance of generated content.

Key Components:
- ContentStrategyManager: Main strategy selection and execution
- PersonaConfig: Persona-specific content configurations
- ContentStrategy: Different content generation approaches
- VarietyTracker: Ensures diverse content generation
- ContentTemplates: Template-based content generation
"""

import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import json
import hashlib

# Import state management components
from autogen_state_manager import (
    StateManager,
    ConversationContext,
    ActivityLevel,
    StreamPhase,
    calculate_time_of_day_factor,
    extract_keywords,
    calculate_content_relevance
)


class ContentType(Enum):
    """Types of autonomous content"""
    AMBIENT = "ambient"
    COMMENTARY = "commentary"
    ENGAGEMENT = "engagement"
    QUESTION = "question"
    REACTION = "reaction"
    STORY = "story"
    OBSERVATION = "observation"
    TUTORIAL = "tutorial"
    GREETING = "greeting"
    TRANSITION = "transition"


class ContentStrategy(Enum):
    """Content generation strategies"""
    CONTEXTUAL_FOLLOW_UP = "contextual_follow_up"
    INTEREST_BASED = "interest_based"
    TIME_AWARE = "time_aware"
    ACTIVITY_BASED = "activity_based"
    VIEWER_ENGAGEMENT = "viewer_engagement"
    VARIETY_FOCUSED = "variety_focused"
    ENERGY_MATCHING = "energy_matching"
    EDUCATIONAL = "educational"
    ENTERTAINING = "entertaining"
    INTERACTIVE = "interactive"


@dataclass
class ContentTemplate:
    """Template for content generation"""
    template: str
    variables: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    cooldown: float = 0.0  # Seconds before reuse
    last_used: float = 0.0
    
    def can_use(self) -> bool:
        """Check if template can be used based on cooldown"""
        return time.time() - self.last_used >= self.cooldown
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables"""
        try:
            self.last_used = time.time()
            return self.template.format(**kwargs)
        except KeyError as e:
            logging.warning(f"Missing template variable: {e}")
            return self.template


@dataclass
class IdleBehaviorConfig:
    """Configuration for idle behavior content"""
    min_idle_time: float = 10.0
    max_idle_time: float = 45.0
    content_types: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    energy_threshold: float = 0.5
    variety_requirement: float = 0.7
    
    def get_content_weights(self) -> Dict[str, float]:
        """Get content type weights"""
        return {
            content_type: config.get("weight", 0.1)
            for content_type, config in self.content_types.items()
        }


@dataclass
class PersonaConfig:
    """Configuration for a specific persona"""
    name: str
    orchestrator_prompt: str
    filter_threshold: float = 0.5
    idle_behavior: IdleBehaviorConfig = field(default_factory=IdleBehaviorConfig)
    preferred_strategies: List[ContentStrategy] = field(default_factory=list)
    content_style: Dict[str, Any] = field(default_factory=dict)
    energy_mapping: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set defaults based on persona"""
        if not self.preferred_strategies:
            # Default strategies based on persona type
            if "artist" in self.name.lower():
                self.preferred_strategies = [
                    ContentStrategy.ACTIVITY_BASED,
                    ContentStrategy.EDUCATIONAL,
                    ContentStrategy.CONTEXTUAL_FOLLOW_UP
                ]
            elif "interactive" in self.name.lower():
                self.preferred_strategies = [
                    ContentStrategy.VIEWER_ENGAGEMENT,
                    ContentStrategy.INTERACTIVE,
                    ContentStrategy.ENERGY_MATCHING
                ]
            else:
                self.preferred_strategies = [
                    ContentStrategy.VARIETY_FOCUSED,
                    ContentStrategy.TIME_AWARE,
                    ContentStrategy.INTEREST_BASED
                ]


class ContentTemplateLibrary:
    """Library of content templates organized by type and strategy"""
    
    def __init__(self):
        self.templates: Dict[ContentType, List[ContentTemplate]] = defaultdict(list)
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize default template library"""
        
        # Ambient content templates
        self.templates[ContentType.AMBIENT] = [
            ContentTemplate("Hmm, interesting...", cooldown=300),
            ContentTemplate("*{action} thoughtfully*", ["action"], cooldown=180),
            ContentTemplate("This is {adjective}.", ["adjective"], cooldown=240),
            ContentTemplate("Let me think about that...", cooldown=300),
            ContentTemplate("*glances around {adverb}*", ["adverb"], cooldown=180)
        ]
        
        # Commentary templates
        self.templates[ContentType.COMMENTARY] = [
            ContentTemplate("I'm really enjoying this {activity}!", ["activity"], cooldown=600),
            ContentTemplate("The {subject} here is {adjective}.", ["subject", "adjective"], cooldown=480),
            ContentTemplate("You know what I love about {topic}? {reason}.", ["topic", "reason"], cooldown=720),
            ContentTemplate("This reminds me of {memory}.", ["memory"], cooldown=900),
            ContentTemplate("I think {observation} is really {adjective}.", ["observation", "adjective"], cooldown=600)
        ]
        
        # Engagement templates
        self.templates[ContentType.ENGAGEMENT] = [
            ContentTemplate("What do you all think about {topic}?", ["topic"], cooldown=900),
            ContentTemplate("Anyone else {experience}?", ["experience"], cooldown=720),
            ContentTemplate("I'm curious - {question}?", ["question"], cooldown=600),
            ContentTemplate("Let's hear your thoughts on {subject}!", ["subject"], cooldown=900),
            ContentTemplate("Quick poll - {choice_a} or {choice_b}?", ["choice_a", "choice_b"], cooldown=1200)
        ]
        
        # Question templates
        self.templates[ContentType.QUESTION] = [
            ContentTemplate("Have you ever {action}?", ["action"], cooldown=600),
            ContentTemplate("What's your favorite {category}?", ["category"], cooldown=720),
            ContentTemplate("How do you usually {activity}?", ["activity"], cooldown=600),
            ContentTemplate("Does anyone know {knowledge}?", ["knowledge"], cooldown=900),
            ContentTemplate("What would you do if {scenario}?", ["scenario"], cooldown=1200)
        ]
        
        # Reaction templates
        self.templates[ContentType.REACTION] = [
            ContentTemplate("Oh wow, {exclamation}!", ["exclamation"], cooldown=300),
            ContentTemplate("That's {adjective}!", ["adjective"], cooldown=180),
            ContentTemplate("I didn't expect {event}!", ["event"], cooldown=480),
            ContentTemplate("*{reaction} in {emotion}*", ["reaction", "emotion"], cooldown=240),
            ContentTemplate("Wait, did you see {observation}?", ["observation"], cooldown=360)
        ]
        
        # Story templates
        self.templates[ContentType.STORY] = [
            ContentTemplate("This one time, {beginning}...", ["beginning"], cooldown=1800),
            ContentTemplate("I remember when {memory}.", ["memory"], cooldown=1500),
            ContentTemplate("Fun fact: {fact}!", ["fact"], cooldown=1200),
            ContentTemplate("Speaking of {topic}, {anecdote}.", ["topic", "anecdote"], cooldown=1800),
            ContentTemplate("Let me tell you about {story_topic}...", ["story_topic"], cooldown=2400)
        ]
        
        # Observation templates
        self.templates[ContentType.OBSERVATION] = [
            ContentTemplate("I notice {observation} today.", ["observation"], cooldown=600),
            ContentTemplate("It's interesting how {phenomenon}.", ["phenomenon"], cooldown=720),
            ContentTemplate("Have you noticed {pattern}?", ["pattern"], cooldown=900),
            ContentTemplate("The {subject} seems {adjective} right now.", ["subject", "adjective"], cooldown=480),
            ContentTemplate("I'm seeing a lot of {trend} lately.", ["trend"], cooldown=1200)
        ]
        
        # Greeting templates
        self.templates[ContentType.GREETING] = [
            ContentTemplate("Welcome, {names}! Great to see you!", ["names"], cooldown=60),
            ContentTemplate("Hey {names}, thanks for joining!", ["names"], cooldown=60),
            ContentTemplate("Look who's here - {names}!", ["names"], cooldown=60),
            ContentTemplate("{greeting} everyone! How's it going?", ["greeting"], cooldown=300),
            ContentTemplate("Nice to see some {adjective} faces!", ["adjective"], cooldown=180)
        ]
        
        # Transition templates
        self.templates[ContentType.TRANSITION] = [
            ContentTemplate("Alright, let's {action}!", ["action"], cooldown=600),
            ContentTemplate("Time to switch to {new_topic}.", ["new_topic"], cooldown=480),
            ContentTemplate("Moving on to {next_thing}...", ["next_thing"], cooldown=600),
            ContentTemplate("Let's talk about {topic} now.", ["topic"], cooldown=720),
            ContentTemplate("Changing gears to {subject}!", ["subject"], cooldown=600)
        ]
    
    def get_templates(self, content_type: ContentType, count: int = None) -> List[ContentTemplate]:
        """Get templates for a specific content type"""
        templates = self.templates.get(content_type, [])
        available = [t for t in templates if t.can_use()]
        
        if count and len(available) > count:
            return random.sample(available, count)
        return available
    
    def add_custom_template(self, content_type: ContentType, template: ContentTemplate):
        """Add a custom template to the library"""
        self.templates[content_type].append(template)


class VarietyTracker:
    """Tracks content variety to ensure diverse generation"""
    
    def __init__(self, history_size: int = 50):
        self.recent_content: deque = deque(maxlen=history_size)
        self.content_hashes: deque = deque(maxlen=history_size)
        self.type_counts: Dict[ContentType, int] = defaultdict(int)
        self.strategy_counts: Dict[ContentStrategy, int] = defaultdict(int)
        self.topic_counts: Dict[str, int] = defaultdict(int)
        self.last_reset: float = time.time()
        self.reset_interval: float = 3600  # Reset counts hourly
    
    def add_content(self, content: str, content_type: ContentType, 
                    strategy: ContentStrategy, topics: List[str] = None):
        """Track generated content"""
        content_hash = hashlib.md5(content.lower().encode()).hexdigest()[:16]
        
        self.recent_content.append({
            "content": content,
            "type": content_type,
            "strategy": strategy,
            "topics": topics or [],
            "timestamp": time.time(),
            "hash": content_hash
        })
        
        self.content_hashes.append(content_hash)
        self.type_counts[content_type] += 1
        self.strategy_counts[strategy] += 1
        
        if topics:
            for topic in topics:
                self.topic_counts[topic] += 1
        
        # Check if we should reset counts
        if time.time() - self.last_reset > self.reset_interval:
            self._reset_counts()
    
    def _reset_counts(self):
        """Reset tracking counts while preserving recent history"""
        self.type_counts.clear()
        self.strategy_counts.clear()
        self.topic_counts.clear()
        self.last_reset = time.time()
        
        # Rebuild counts from recent history
        for item in self.recent_content:
            self.type_counts[item["type"]] += 1
            self.strategy_counts[item["strategy"]] += 1
            for topic in item.get("topics", []):
                self.topic_counts[topic] += 1
    
    def get_variety_score(self) -> float:
        """Calculate variety score (0-1)"""
        if not self.recent_content:
            return 1.0
        
        # Check hash uniqueness
        unique_hashes = len(set(self.content_hashes))
        hash_variety = unique_hashes / len(self.content_hashes) if self.content_hashes else 1.0
        
        # Check type distribution
        type_variety = len(self.type_counts) / len(ContentType) if self.type_counts else 0.0
        
        # Check strategy distribution
        strategy_variety = len(self.strategy_counts) / len(ContentStrategy) if self.strategy_counts else 0.0
        
        # Combined score
        return (hash_variety * 0.5 + type_variety * 0.25 + strategy_variety * 0.25)
    
    def get_underused_types(self, threshold: float = 0.1) -> List[ContentType]:
        """Get content types that are underused"""
        total_content = sum(self.type_counts.values())
        if total_content == 0:
            return list(ContentType)
        
        underused = []
        for content_type in ContentType:
            usage_ratio = self.type_counts.get(content_type, 0) / total_content
            if usage_ratio < threshold:
                underused.append(content_type)
        
        return underused
    
    def get_overused_topics(self, threshold: int = 5) -> Set[str]:
        """Get topics that have been overused"""
        return {topic for topic, count in self.topic_counts.items() if count > threshold}
    
    def should_avoid_content(self, content: str, threshold: float = 0.8) -> bool:
        """Check if content is too similar to recent content"""
        content_hash = hashlib.md5(content.lower().encode()).hexdigest()[:16]
        
        # Direct hash match
        if content_hash in self.content_hashes:
            return True
        
        # Similarity check (simple keyword overlap)
        content_keywords = set(extract_keywords(content))
        
        for recent in list(self.recent_content)[-10:]:  # Check last 10
            recent_keywords = set(extract_keywords(recent["content"]))
            if not recent_keywords:
                continue
                
            overlap = len(content_keywords & recent_keywords) / len(recent_keywords)
            if overlap > threshold:
                return True
        
        return False


class ContentStrategyManager:
    """Manages content generation strategies and selection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.template_library = ContentTemplateLibrary()
        self.variety_tracker = VarietyTracker()
        
        # Load persona configurations
        self.personas = config.get("personas", {})
        self.current_persona = config.get("current_persona", "interactive_streamer")
        
        # Strategy weights based on context
        self.strategy_weights: Dict[ContentStrategy, float] = {
            strategy: 1.0 for strategy in ContentStrategy
        }
        
        # Content type mappings
        self.strategy_to_types: Dict[ContentStrategy, List[ContentType]] = {
            ContentStrategy.CONTEXTUAL_FOLLOW_UP: [ContentType.COMMENTARY, ContentType.OBSERVATION],
            ContentStrategy.INTEREST_BASED: [ContentType.QUESTION, ContentType.ENGAGEMENT],
            ContentStrategy.TIME_AWARE: [ContentType.GREETING, ContentType.TRANSITION],
            ContentStrategy.ACTIVITY_BASED: [ContentType.COMMENTARY, ContentType.TUTORIAL],
            ContentStrategy.VIEWER_ENGAGEMENT: [ContentType.QUESTION, ContentType.ENGAGEMENT],
            ContentStrategy.VARIETY_FOCUSED: list(ContentType),  # All types
            ContentStrategy.ENERGY_MATCHING: [ContentType.REACTION, ContentType.AMBIENT],
            ContentStrategy.EDUCATIONAL: [ContentType.TUTORIAL, ContentType.OBSERVATION],
            ContentStrategy.ENTERTAINING: [ContentType.STORY, ContentType.REACTION],
            ContentStrategy.INTERACTIVE: [ContentType.QUESTION, ContentType.ENGAGEMENT]
        }
    
    def update_persona(self, persona_name: str):
        """Update current persona"""
        if persona_name in self.personas:
            self.current_persona = persona_name
            self.logger.info(f"Updated persona to: {persona_name}")
            self._update_strategy_weights()
    
    def _update_strategy_weights(self):
        """Update strategy weights based on current persona"""
        persona_config = self.personas.get(self.current_persona)
        if not persona_config:
            return
        
        # Reset weights
        for strategy in ContentStrategy:
            self.strategy_weights[strategy] = 0.5
        
        # Boost preferred strategies
        for strategy in persona_config.preferred_strategies:
            self.strategy_weights[strategy] = 1.5
    
    def select_strategy(self, state_manager: StateManager) -> ContentStrategy:
        """Select appropriate content strategy based on current state"""
        state = state_manager.state
        
        # Calculate strategy scores based on context
        strategy_scores: Dict[ContentStrategy, float] = {}
        
        for strategy in ContentStrategy:
            score = self._calculate_strategy_score(strategy, state_manager)
            strategy_scores[strategy] = score
        
        # Add variety bonus to underused strategies
        strategy_usage = self.variety_tracker.strategy_counts
        total_usage = sum(strategy_usage.values()) or 1
        
        for strategy, score in strategy_scores.items():
            usage_ratio = strategy_usage.get(strategy, 0) / total_usage
            variety_bonus = max(0, 0.2 - usage_ratio) * 5  # Bonus for underused
            strategy_scores[strategy] = score + variety_bonus
        
        # Select strategy probabilistically
        strategies = list(strategy_scores.keys())
        weights = [strategy_scores[s] for s in strategies]
        
        if sum(weights) == 0:
            return random.choice(strategies)
        
        return random.choices(strategies, weights=weights)[0]
    
    def _calculate_strategy_score(self, strategy: ContentStrategy, 
                                  state_manager: StateManager) -> float:
        """Calculate score for a specific strategy"""
        state = state_manager.state
        base_score = self.strategy_weights[strategy]
        
        # Contextual adjustments
        if strategy == ContentStrategy.CONTEXTUAL_FOLLOW_UP:
            # Good when there are recent topics
            if state.conversation_context.recent_topics:
                base_score *= 1.5
            else:
                base_score *= 0.3
                
        elif strategy == ContentStrategy.INTEREST_BASED:
            # Good when we know user interests
            interest_count = len(state.conversation_context.user_interests)
            base_score *= min(1 + interest_count * 0.2, 2.0)
            
        elif strategy == ContentStrategy.TIME_AWARE:
            # Good for greetings and transitions
            if state.stream_phase in [StreamPhase.STARTING, StreamPhase.WARMING_UP]:
                base_score *= 1.8
                
        elif strategy == ContentStrategy.ACTIVITY_BASED:
            # Good when there's a clear activity
            if state.conversation_context.current_activity != "chatting":
                base_score *= 1.6
                
        elif strategy == ContentStrategy.VIEWER_ENGAGEMENT:
            # Good when viewer count is high or growing
            if state.viewer_metrics.join_rate > 0:
                base_score *= 1.4
                
        elif strategy == ContentStrategy.ENERGY_MATCHING:
            # Match conversation energy
            energy_diff = abs(state.conversation_context.conversation_energy - 0.5)
            base_score *= (1 + energy_diff)
            
        elif strategy == ContentStrategy.VARIETY_FOCUSED:
            # Always decent, especially when variety is low
            variety_score = self.variety_tracker.get_variety_score()
            if variety_score < 0.5:
                base_score *= 1.5
        
        # Time of day factor
        time_factor = calculate_time_of_day_factor()
        base_score *= time_factor
        
        # Stream phase factor
        if state.stream_phase == StreamPhase.ACTIVE:
            base_score *= 1.2
        elif state.stream_phase == StreamPhase.WINDING_DOWN:
            base_score *= 0.8
        
        return max(0, base_score)
    
    def generate_content(self, strategy: ContentStrategy, 
                        state_manager: StateManager) -> Optional[str]:
        """Generate content using selected strategy"""
        # Get appropriate content types for strategy
        content_types = self.strategy_to_types.get(strategy, [ContentType.AMBIENT])
        
        # Filter by variety needs
        underused_types = self.variety_tracker.get_underused_types()
        if underused_types:
            # Prefer underused types that match strategy
            preferred_types = [t for t in content_types if t in underused_types]
            if preferred_types:
                content_types = preferred_types
        
        # Select content type
        content_type = random.choice(content_types) if content_types else ContentType.AMBIENT
        
        # Generate content based on type and strategy
        content = self._generate_typed_content(content_type, strategy, state_manager)
        
        if content and not self.variety_tracker.should_avoid_content(content):
            # Track the content
            topics = state_manager.get_recent_topics(3)
            self.variety_tracker.add_content(content, content_type, strategy, topics)
            return content
        
        # Fallback to simple generation if needed
        return self._generate_fallback_content(content_type)
    
    def _generate_typed_content(self, content_type: ContentType, 
                               strategy: ContentStrategy,
                               state_manager: StateManager) -> Optional[str]:
        """Generate content of specific type"""
        templates = self.template_library.get_templates(content_type)
        if not templates:
            return None
        
        state = state_manager.state
        context = state.conversation_context
        
        # Try multiple templates until one works
        for _ in range(min(3, len(templates))):
            template = random.choice(templates)
            
            try:
                # Prepare variables based on content type
                variables = self._prepare_template_variables(
                    content_type, strategy, state_manager
                )
                
                # Format template
                content = template.format(**variables)
                
                # Validate content
                if len(content) > 150:  # Too long
                    content = content[:147] + "..."
                
                return content
                
            except Exception as e:
                self.logger.debug(f"Template formatting failed: {e}")
                continue
        
        return None
    
    def _prepare_template_variables(self, content_type: ContentType,
                                   strategy: ContentStrategy,
                                   state_manager: StateManager) -> Dict[str, Any]:
        """Prepare variables for template formatting"""
        state = state_manager.state
        context = state.conversation_context
        
        variables = {}
        
        # Common variables
        variables["time_of_day"] = self._get_time_of_day_greeting()
        variables["viewer_count"] = state.viewer_metrics.current_count
        variables["activity"] = context.current_activity
        
        # Type-specific variables
        if content_type == ContentType.AMBIENT:
            variables["action"] = random.choice(["looks", "gazes", "peers", "glances"])
            variables["adjective"] = random.choice(["nice", "interesting", "cool", "fun"])
            variables["adverb"] = random.choice(["thoughtfully", "curiously", "happily"])
            
        elif content_type == ContentType.COMMENTARY:
            topics = list(context.recent_topics) or ["this"]
            variables["topic"] = random.choice(topics) if topics else "this"
            variables["subject"] = random.choice(["atmosphere", "vibe", "energy", "mood"])
            variables["adjective"] = random.choice(["great", "wonderful", "amazing", "perfect"])
            variables["observation"] = "the way things are going"
            variables["reason"] = "it brings people together"
            variables["memory"] = "something similar happening before"
            
        elif content_type == ContentType.ENGAGEMENT:
            topics = list(context.recent_topics) or ["this topic"]
            variables["topic"] = random.choice(topics) if topics else "this"
            variables["subject"] = variables["topic"]
            variables["question"] = "what brings you here today"
            variables["experience"] = "enjoyed streams like this"
            variables["choice_a"] = "option A"
            variables["choice_b"] = "option B"
            
        elif content_type == ContentType.QUESTION:
            variables["action"] = "tried something like this"
            variables["category"] = random.choice(["game", "movie", "book", "hobby"])
            variables["activity"] = "spend your free time"
            variables["knowledge"] = "about this topic"
            variables["scenario"] = "you could do anything"
            
        elif content_type == ContentType.REACTION:
            variables["exclamation"] = random.choice(["amazing", "incredible", "cool"])
            variables["adjective"] = random.choice(["awesome", "fantastic", "great"])
            variables["event"] = "that happening"
            variables["reaction"] = random.choice(["laughs", "smiles", "nods"])
            variables["emotion"] = random.choice(["delight", "surprise", "amusement"])
            variables["observation"] = "what just happened"
            
        elif content_type == ContentType.STORY:
            variables["beginning"] = "I was doing something similar"
            variables["memory"] = "the first time I tried this"
            variables["fact"] = "this is actually pretty common"
            variables["topic"] = random.choice(list(context.recent_topics) or ["that"])
            variables["anecdote"] = "something funny happened"
            variables["story_topic"] = "an interesting experience"
            
        elif content_type == ContentType.GREETING:
            recent_chatters = list(state.viewer_metrics.active_chatters)[-3:]
            variables["names"] = ", ".join(recent_chatters) if recent_chatters else "everyone"
            variables["greeting"] = self._get_time_of_day_greeting()
            variables["adjective"] = random.choice(["new", "familiar", "friendly"])
            
        elif content_type == ContentType.TRANSITION:
            variables["action"] = random.choice(["try something new", "switch things up", "move forward"])
            variables["new_topic"] = "something different"
            variables["next_thing"] = "the next part"
            variables["topic"] = "another subject"
            variables["subject"] = "a new direction"
        
        return variables
    
    def _generate_fallback_content(self, content_type: ContentType) -> str:
        """Generate simple fallback content"""
        fallbacks = {
            ContentType.AMBIENT: "Hmm...",
            ContentType.COMMENTARY: "This is nice.",
            ContentType.ENGAGEMENT: "How's everyone doing?",
            ContentType.QUESTION: "Any thoughts?",
            ContentType.REACTION: "Oh, interesting!",
            ContentType.STORY: "That reminds me...",
            ContentType.OBSERVATION: "I just noticed something.",
            ContentType.GREETING: "Welcome!",
            ContentType.TRANSITION: "Let's continue."
        }
        
        return fallbacks.get(content_type, "...")
    
    def _get_time_of_day_greeting(self) -> str:
        """Get appropriate time of day greeting"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return random.choice(["Good morning", "Morning"])
        elif 12 <= hour < 17:
            return random.choice(["Good afternoon", "Hey there"])
        elif 17 <= hour < 22:
            return random.choice(["Good evening", "Evening"])
        else:
            return random.choice(["Hey", "Hello"])
    
    def record_content_generation(self, strategy: ContentStrategy, content: str):
        """Record successful content generation for analytics"""
        # This is called by the orchestrator after content is queued
        # Additional tracking can be added here
        pass
    
    def get_content_analytics(self) -> Dict[str, Any]:
        """Get content generation analytics"""
        return {
            "variety_score": self.variety_tracker.get_variety_score(),
            "content_types": dict(self.variety_tracker.type_counts),
            "strategies_used": dict(self.variety_tracker.strategy_counts),
            "recent_content_count": len(self.variety_tracker.recent_content),
            "overused_topics": list(self.variety_tracker.get_overused_topics()),
            "underused_types": [t.value for t in self.variety_tracker.get_underused_types()]
        }


# Utility functions for content generation

def generate_contextual_response(topic: str, persona: str) -> str:
    """Generate a contextual response for a topic"""
    responses = {
        "focused_artist": {
            "default": f"Let me focus on {topic} for a moment.",
            "art": f"The artistic aspects of {topic} are fascinating.",
            "technique": f"There's an interesting technique related to {topic}."
        },
        "interactive_streamer": {
            "default": f"Oh, {topic}! What does everyone think?",
            "game": f"{topic} is such a fun topic to explore!",
            "chat": f"I love talking about {topic} with you all!"
        },
        "casual_gamer": {
            "default": f"Speaking of {topic}, that's interesting.",
            "game": f"{topic} really affects the gameplay here.",
            "strategy": f"When it comes to {topic}, I usually..."
        }
    }
    
    persona_responses = responses.get(persona, responses["interactive_streamer"])
    
    # Try to match topic category
    for keyword, response in persona_responses.items():
        if keyword in topic.lower():
            return response
    
    return persona_responses["default"]


def adjust_content_for_energy(content: str, target_energy: float) -> str:
    """Adjust content tone based on target energy level"""
    if target_energy > 0.7:
        # High energy - add excitement
        if not content.endswith("!"):
            content = content.rstrip(".") + "!"
        content = content.replace("nice", "amazing")
        content = content.replace("good", "fantastic")
        
    elif target_energy < 0.3:
        # Low energy - more mellow
        content = content.replace("!", ".")
        content = content.lower()
        
    return content


def validate_content_appropriateness(content: str) -> bool:
    """Validate that content is appropriate for streaming"""
    # Simple validation - can be expanded
    inappropriate_terms = [
        "offensive", "inappropriate", "banned", "prohibited"
        # Add actual terms to filter
    ]
    
    content_lower = content.lower()
    return not any(term in content_lower for term in inappropriate_terms)


# Export main components
__all__ = [
    'ContentStrategyManager',
    'ContentType',
    'ContentStrategy',
    'PersonaConfig',
    'IdleBehaviorConfig',
    'ContentTemplate',
    'ContentTemplateLibrary',
    'VarietyTracker',
    'generate_contextual_response',
    'adjust_content_for_energy',
    'validate_content_appropriateness'
]