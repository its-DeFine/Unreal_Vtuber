"""
Category classifier helper for intelligent stimuli categorization.

This module provides feature extraction and classification logic
to support the Categorizer Node in determining stimuli categories.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from ...models.stimuli import StimuliCategory, ExternalStimuli


logger = logging.getLogger(__name__)


@dataclass
class CategoryFeatures:
    """Features extracted from stimuli for categorization."""
    
    content_length: int
    word_count: int
    has_question: bool
    has_command: bool
    has_greeting: bool
    has_urgency: bool
    source_type: str
    keywords: List[str]
    avatar_state_keywords: List[str]
    admin_keywords: List[str]
    social_keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary."""
        return {
            "content_length": self.content_length,
            "word_count": self.word_count,
            "has_question": self.has_question,
            "has_command": self.has_command,
            "has_greeting": self.has_greeting,
            "has_urgency": self.has_urgency,
            "source_type": self.source_type,
            "keywords": self.keywords,
            "avatar_state_keywords": self.avatar_state_keywords,
            "admin_keywords": self.admin_keywords,
            "social_keywords": self.social_keywords
        }


@dataclass
class CategoryResult:
    """Result of category classification."""
    
    category: StimuliCategory
    confidence: float
    reasoning: str
    method: str = "llm"  # "llm" or "keyword_fallback"


class CategoryClassifier:
    """
    Helper class for stimuli categorization.
    
    Provides feature extraction and fallback classification methods
    to support intelligent categorization of external stimuli.
    """
    
    # Keyword patterns for different categories
    ADMIN_KEYWORDS = [
        "set", "configure", "change", "update", "modify",
        "admin", "command", "execute", "enable", "disable",
        "load character", "switch mode", "restart", "shutdown"
    ]
    
    USER_INTERACTION_KEYWORDS = [
        "hello", "hi", "hey", "how are you", "what's up",
        "tell me", "explain", "help", "please", "thanks",
        "can you", "would you", "could you", "will you"
    ]
    
    AVATAR_STATE_KEYWORDS = [
        "speaking", "idle", "busy", "character_loaded",
        "avatar_state", "system_state", "mode_changed",
        "started_speaking", "stopped_speaking", "error_state"
    ]
    
    SOCIAL_MEDIA_KEYWORDS = [
        "tweet", "post", "comment", "mention", "tagged",
        "replied", "shared", "liked", "follower", "retweet",
        "instagram", "twitter", "youtube", "tiktok", "facebook"
    ]
    
    AUTONOMOUS_KEYWORDS = [
        "autonomous", "self", "auto", "scheduled", "periodic",
        "idle_trigger", "time_based", "routine", "automated"
    ]
    
    EMERGENCY_KEYWORDS = [
        "emergency", "urgent", "critical", "alert", "warning",
        "immediate", "asap", "now", "help!", "stop!", "error!"
    ]
    
    CONTEXTUAL_KEYWORDS = [
        "update", "info", "notification", "status", "report",
        "log", "event", "change", "new", "updated"
    ]
    
    def __init__(self):
        """Initialize the category classifier."""
        self.greeting_pattern = re.compile(
            r'\b(hello|hi|hey|good\s+(morning|afternoon|evening)|greetings)\b',
            re.IGNORECASE
        )
        self.question_pattern = re.compile(
            r'.*\?$|^(what|when|where|who|why|how|can|could|would|will|do|does|is|are)\b',
            re.IGNORECASE
        )
        self.command_pattern = re.compile(
            r'^(set|configure|change|update|modify|enable|disable|load|switch|restart|shutdown)\b',
            re.IGNORECASE
        )
        self.urgency_pattern = re.compile(
            r'\b(urgent|emergency|critical|immediately|asap|now|help!|stop!)\b',
            re.IGNORECASE
        )
    
    def extract_features(self, stimuli: ExternalStimuli) -> CategoryFeatures:
        """
        Extract features from stimuli for classification.
        
        Args:
            stimuli: External stimuli to analyze.
            
        Returns:
            CategoryFeatures object with extracted features.
        """
        content = stimuli.content.strip()
        words = content.split()
        
        # Extract keyword matches
        content_lower = content.lower()
        
        avatar_keywords = [kw for kw in self.AVATAR_STATE_KEYWORDS 
                          if kw in content_lower]
        admin_keywords = [kw for kw in self.ADMIN_KEYWORDS 
                         if kw in content_lower]
        social_keywords = [kw for kw in self.SOCIAL_MEDIA_KEYWORDS 
                          if kw in content_lower]
        
        # Extract all significant keywords
        all_keywords = []
        for word in words:
            word_lower = word.lower().strip('.,!?')
            if len(word_lower) > 3:  # Skip short words
                all_keywords.append(word_lower)
        
        features = CategoryFeatures(
            content_length=len(content),
            word_count=len(words),
            has_question=bool(self.question_pattern.match(content)),
            has_command=bool(self.command_pattern.match(content)),
            has_greeting=bool(self.greeting_pattern.search(content)),
            has_urgency=bool(self.urgency_pattern.search(content)),
            source_type=stimuli.source,
            keywords=all_keywords[:10],  # Top 10 keywords
            avatar_state_keywords=avatar_keywords,
            admin_keywords=admin_keywords,
            social_keywords=social_keywords
        )
        
        logger.debug(f"Extracted features for stimuli {stimuli.id}: {features.to_dict()}")
        return features
    
    def create_llm_prompt(self, stimuli: ExternalStimuli, features: CategoryFeatures) -> str:
        """
        Create a prompt for LLM-based categorization.
        
        Args:
            stimuli: The stimuli to categorize.
            features: Extracted features.
            
        Returns:
            Formatted prompt for LLM.
        """
        prompt = f"""Categorize the following external stimuli into one of these categories:

1. DIRECT_ADMIN - Direct administrative commands (e.g., "set avatar color", "load character")
2. USER_INTERACTION - User chat messages, questions, or conversations
3. SYSTEM_NOTIFICATION - Avatar state changes (speaking, idle, busy, character_loaded)
4. SOCIAL_MEDIA - Social media mentions, posts, or interactions
5. AUTONOMOUS_TRIGGER - Self-generated or scheduled events
6. EMERGENCY - Urgent or critical messages requiring immediate attention
7. CONTEXTUAL_UPDATE - General updates, logs, or informational messages

Stimuli Content: "{stimuli.content}"
Source: {stimuli.source}
Priority: {stimuli.priority.value}

Additional Context:
- Content length: {features.content_length} characters
- Has question: {features.has_question}
- Has command: {features.has_command}
- Has urgency: {features.has_urgency}
- Avatar state keywords found: {features.avatar_state_keywords}
- Admin keywords found: {features.admin_keywords}
- Social keywords found: {features.social_keywords}

IMPORTANT: Avatar state notifications (speaking, idle, busy, character_loaded) should ALWAYS be categorized as SYSTEM_NOTIFICATION with high confidence.

Respond with a JSON object containing:
- "category": The category name (e.g., "USER_INTERACTION")
- "confidence": A confidence score between 0.0 and 1.0
- "reasoning": A brief explanation of your categorization

Example response:
{{"category": "USER_INTERACTION", "confidence": 0.95, "reasoning": "Greeting message from user"}}"""
        
        return prompt
    
    def keyword_based_fallback(
        self,
        stimuli: ExternalStimuli,
        features: CategoryFeatures
    ) -> CategoryResult:
        """
        Fallback categorization based on keywords and patterns.
        
        Used when LLM is unavailable or as a validation check.
        
        Args:
            stimuli: The stimuli to categorize.
            features: Extracted features.
            
        Returns:
            CategoryResult with fallback classification.
        """
        content_lower = stimuli.content.lower()
        
        # Priority 1: Check for emergency keywords
        if features.has_urgency or any(kw in content_lower for kw in ["emergency", "urgent", "critical"]):
            return CategoryResult(
                category=StimuliCategory.EMERGENCY,
                confidence=0.85,
                reasoning="Emergency keywords detected",
                method="keyword_fallback"
            )
        
        # Priority 2: Check for avatar state notifications
        if features.avatar_state_keywords:
            return CategoryResult(
                category=StimuliCategory.SYSTEM_NOTIFICATION,
                confidence=0.95,
                reasoning=f"Avatar state keywords: {features.avatar_state_keywords}",
                method="keyword_fallback"
            )
        
        # Priority 3: Check for admin commands
        if features.admin_keywords and (features.has_command or stimuli.source == "admin_console"):
            return CategoryResult(
                category=StimuliCategory.DIRECT_ADMIN,
                confidence=0.8,
                reasoning=f"Admin command keywords: {features.admin_keywords}",
                method="keyword_fallback"
            )
        
        # Priority 4: Check for social media
        if features.social_keywords or stimuli.source in ["twitter", "instagram", "social_media"]:
            return CategoryResult(
                category=StimuliCategory.SOCIAL_MEDIA,
                confidence=0.75,
                reasoning=f"Social media keywords or source",
                method="keyword_fallback"
            )
        
        # Priority 5: Check for autonomous triggers
        if any(kw in content_lower for kw in self.AUTONOMOUS_KEYWORDS) or stimuli.source == "autonomous":
            return CategoryResult(
                category=StimuliCategory.AUTONOMOUS_TRIGGER,
                confidence=0.7,
                reasoning="Autonomous trigger patterns detected",
                method="keyword_fallback"
            )
        
        # Priority 6: Check for user interaction
        if features.has_greeting or features.has_question or stimuli.source == "user_chat":
            return CategoryResult(
                category=StimuliCategory.USER_INTERACTION,
                confidence=0.7,
                reasoning="User interaction patterns detected",
                method="keyword_fallback"
            )
        
        # Default: Contextual update
        return CategoryResult(
            category=StimuliCategory.CONTEXTUAL_UPDATE,
            confidence=0.5,
            reasoning="No specific patterns matched, treating as contextual update",
            method="keyword_fallback"
        )
    
    def parse_llm_response(self, llm_response: str) -> Optional[CategoryResult]:
        """
        Parse LLM response into CategoryResult.
        
        Args:
            llm_response: Raw LLM response string.
            
        Returns:
            CategoryResult if parsing successful, None otherwise.
        """
        try:
            # Try to extract JSON from the response
            # Handle cases where LLM adds extra text
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                data = json.loads(json_str)
                
                # Validate required fields
                if all(key in data for key in ["category", "confidence", "reasoning"]):
                    # Map category string to enum
                    category_str = data["category"].upper()
                    try:
                        category = StimuliCategory[category_str]
                    except KeyError:
                        logger.warning(f"Invalid category from LLM: {category_str}")
                        return None
                    
                    # Validate confidence
                    confidence = float(data["confidence"])
                    if not 0.0 <= confidence <= 1.0:
                        logger.warning(f"Invalid confidence from LLM: {confidence}")
                        return None
                    
                    return CategoryResult(
                        category=category,
                        confidence=confidence,
                        reasoning=data["reasoning"],
                        method="llm"
                    )
            
            logger.error(f"Failed to find valid JSON in LLM response: {llm_response}")
            return None
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
    
    def calculate_confidence_adjustment(
        self,
        result: CategoryResult,
        features: CategoryFeatures,
        stimuli: ExternalStimuli
    ) -> float:
        """
        Calculate confidence adjustment based on feature alignment.
        
        Args:
            result: Initial category result.
            features: Extracted features.
            stimuli: Original stimuli.
            
        Returns:
            Adjusted confidence score.
        """
        confidence = result.confidence
        
        # Boost confidence for strong keyword matches
        if result.category == StimuliCategory.SYSTEM_NOTIFICATION and features.avatar_state_keywords:
            confidence = min(0.99, confidence + 0.2)
        
        elif result.category == StimuliCategory.DIRECT_ADMIN and features.admin_keywords:
            confidence = min(0.95, confidence + 0.15)
        
        elif result.category == StimuliCategory.EMERGENCY and features.has_urgency:
            confidence = min(0.98, confidence + 0.2)
        
        # Reduce confidence for mismatched source
        if result.category == StimuliCategory.DIRECT_ADMIN and stimuli.source != "admin_console":
            confidence = max(0.5, confidence - 0.2)
        
        elif result.category == StimuliCategory.SOCIAL_MEDIA and stimuli.source not in ["twitter", "instagram", "social_media"]:
            confidence = max(0.4, confidence - 0.3)
        
        return confidence