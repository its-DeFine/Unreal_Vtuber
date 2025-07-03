"""
Stimuli Categorizer Node for GraphFlow Pipeline.

This node handles the categorization of incoming stimuli using LLM analysis
and pattern matching to determine the appropriate category.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ...models.stimuli import ExternalStimuli, CategorizedStimuli, StimuliCategory
from ...config.settings import CategorizerConfig
from ...utils.logging import get_structured_logger


class StimuliCategorizerNode:
    """
    GraphFlow node for stimuli categorization.
    
    This node takes raw external stimuli and categorizes them using:
    - LLM-based analysis for intelligent categorization
    - Keyword pattern matching as fallback
    - Special handling for avatar state notifications
    """
    
    def __init__(self, config: CategorizerConfig, llm_config: Dict[str, Any]):
        """
        Initialize the categorizer node.
        
        Args:
            config: Categorizer configuration
            llm_config: LLM client configuration
        """
        self.config = config
        self.llm_config = llm_config
        self.logger = get_structured_logger("categorizer_node")
        
        # Initialize keyword patterns
        self._init_keyword_patterns()
        
        # Cache for categorization results
        self._category_cache: Dict[str, CategorizedStimuli] = {}
        self._cache_lock = asyncio.Lock()
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the categorizer node."""
        try:
            # In a real implementation, initialize LLM client here
            self.logger.info("Initializing categorizer node")
            
            self.is_initialized = True
            self.logger.info("Categorizer node initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize categorizer node: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the categorizer node."""
        self.logger.info("Shutting down categorizer node")
        
        # Clear cache
        async with self._cache_lock:
            self._category_cache.clear()
        
        self.is_initialized = False
    
    async def process(self, stimuli: ExternalStimuli) -> CategorizedStimuli:
        """
        Categorize incoming stimuli.
        
        Process:
        1. Check cache for recent similar stimuli
        2. Extract content features
        3. Apply LLM-based classification (if enabled)
        4. Fall back to keyword matching if needed
        5. Validate and return categorized stimuli
        
        Args:
            stimuli: External stimuli to categorize
            
        Returns:
            CategorizedStimuli with category and confidence
        """
        start_time = datetime.now()
        
        try:
            # Check cache first
            if self.config.cache_enabled:
                cached = await self._check_cache(stimuli)
                if cached:
                    return cached
            
            # Extract features
            features = self._extract_features(stimuli)
            
            # Categorize
            if self.config.use_llm:
                category_result = await self._apply_llm_classification(features)
            else:
                category_result = self._apply_keyword_classification(features)
            
            # Validate category
            if not self._validate_category(
                category_result['category'], 
                category_result['confidence']
            ):
                # Use fallback
                category_result = {
                    'category': StimuliCategory[self.config.fallback_category],
                    'confidence': 0.5,
                    'method': 'fallback'
                }
            
            # Create categorized stimuli
            categorized = CategorizedStimuli(
                **stimuli.__dict__,
                category=category_result['category'],
                confidence=category_result['confidence'],
                classification_metadata={
                    'method': category_result.get('method', 'unknown'),
                    'features': features,
                    'processing_time': (datetime.now() - start_time).total_seconds()
                }
            )
            
            # Cache result
            if self.config.cache_enabled:
                await self._cache_result(stimuli, categorized)
            
            self.logger.info(
                "Stimuli categorized",
                stimuli_id=stimuli.id,
                category=categorized.category.value,
                confidence=categorized.confidence,
                method=category_result.get('method')
            )
            
            return categorized
            
        except Exception as e:
            self.logger.error(
                f"Categorization failed for stimuli {stimuli.id}: {e}"
            )
            # Return with fallback category
            return CategorizedStimuli(
                **stimuli.__dict__,
                category=StimuliCategory[self.config.fallback_category],
                confidence=0.0,
                classification_metadata={'error': str(e)}
            )
    
    def _init_keyword_patterns(self) -> None:
        """Initialize keyword patterns for classification."""
        # Default patterns if not provided in config
        if not self.config.keyword_patterns:
            self.config.keyword_patterns = {
                "DIRECT_ADMIN": ["admin", "command", "set", "configure", "change"],
                "USER_INTERACTION": ["hello", "hi", "how", "what", "why", "tell", "ask"],
                "SYSTEM_NOTIFICATION": ["system", "status", "speaking", "idle", "busy", "error"],
                "AUTONOMOUS_TRIGGER": ["auto", "trigger", "scheduled", "periodic"],
                "EMERGENCY": ["emergency", "urgent", "critical", "alert", "warning"],
                "CONTEXTUAL_UPDATE": ["update", "context", "info", "note", "fyi"]
            }
    
    def _extract_features(self, stimuli: ExternalStimuli) -> Dict[str, Any]:
        """Extract features for classification."""
        content_lower = stimuli.content.lower()
        
        return {
            'content': stimuli.content,
            'content_lower': content_lower,
            'content_length': len(stimuli.content),
            'word_count': len(stimuli.content.split()),
            'source': stimuli.source,
            'priority': stimuli.priority.value,
            'has_metadata': bool(stimuli.metadata),
            'metadata_keys': list(stimuli.metadata.keys()) if stimuli.metadata else [],
            # Check for special indicators
            'has_question': any(q in content_lower for q in ['?', 'what', 'how', 'why', 'when', 'where']),
            'has_command': any(c in content_lower for c in ['please', 'set', 'change', 'update', 'configure']),
            'is_greeting': any(g in content_lower for g in ['hello', 'hi', 'hey', 'good morning', 'good evening'])
        }
    
    async def _apply_llm_classification(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM for intelligent categorization."""
        # In a real implementation, this would call the LLM
        # For now, simulate with keyword matching
        self.logger.debug("LLM classification not implemented, using keyword fallback")
        return self._apply_keyword_classification(features)
    
    def _apply_keyword_classification(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Apply keyword-based classification."""
        content_lower = features['content_lower']
        best_match = None
        best_score = 0.0
        
        # Check each category's keywords
        for category_name, keywords in self.config.keyword_patterns.items():
            score = 0
            matches = 0
            
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    matches += 1
                    # Weight by keyword position (earlier = higher weight)
                    position = content_lower.find(keyword.lower())
                    position_weight = 1.0 - (position / len(content_lower))
                    score += position_weight
            
            if matches > 0:
                # Normalize score
                normalized_score = (score / len(keywords)) * (matches / len(keywords))
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_match = category_name
        
        # Special handling for avatar state notifications
        if features['source'] == 'system' and any(
            state in content_lower 
            for state in ['speaking', 'idle', 'busy', 'character_loaded']
        ):
            return {
                'category': StimuliCategory.SYSTEM_NOTIFICATION,
                'confidence': 0.95,
                'method': 'system_state_detection'
            }
        
        # Check source-based categorization
        if features['source'] == 'admin_console':
            return {
                'category': StimuliCategory.DIRECT_ADMIN,
                'confidence': 0.9,
                'method': 'source_based'
            }
        
        if best_match:
            return {
                'category': StimuliCategory[best_match],
                'confidence': min(0.9, best_score + 0.3),  # Add base confidence
                'method': 'keyword_matching'
            }
        
        # Default fallback
        return {
            'category': StimuliCategory[self.config.fallback_category],
            'confidence': 0.3,
            'method': 'no_match_fallback'
        }
    
    def _validate_category(self, category: StimuliCategory, confidence: float) -> bool:
        """Validate categorization result."""
        return confidence >= self.config.confidence_threshold
    
    async def _check_cache(self, stimuli: ExternalStimuli) -> Optional[CategorizedStimuli]:
        """Check cache for similar stimuli."""
        # Simple content-based cache key
        cache_key = f"{stimuli.source}:{hash(stimuli.content[:50])}"
        
        async with self._cache_lock:
            if cache_key in self._category_cache:
                cached = self._category_cache[cache_key]
                # Check if cache is still valid
                cache_age = (datetime.now() - cached.timestamp).seconds
                if cache_age < self.config.cache_ttl:
                    # Return copy with new stimuli ID
                    return CategorizedStimuli(
                        **stimuli.__dict__,
                        category=cached.category,
                        confidence=cached.confidence * 0.95,  # Slightly reduce confidence
                        classification_metadata={
                            **cached.classification_metadata,
                            'cached': True,
                            'cache_age': cache_age
                        }
                    )
        
        return None
    
    async def _cache_result(
        self, 
        stimuli: ExternalStimuli, 
        categorized: CategorizedStimuli
    ) -> None:
        """Cache categorization result."""
        cache_key = f"{stimuli.source}:{hash(stimuli.content[:50])}"
        
        async with self._cache_lock:
            self._category_cache[cache_key] = categorized
            
            # Limit cache size
            if len(self._category_cache) > 1000:
                # Remove oldest entries
                sorted_items = sorted(
                    self._category_cache.items(),
                    key=lambda x: x[1].timestamp
                )
                for key, _ in sorted_items[:100]:
                    del self._category_cache[key]