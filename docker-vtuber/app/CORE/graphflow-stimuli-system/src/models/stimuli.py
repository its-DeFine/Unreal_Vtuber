"""
Core data models for external stimuli handling in GraphFlow system.

This module defines the core stimuli models including base stimuli,
categorized stimuli, analyzed stimuli, and routing decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from .context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis,
    ProcessingContext
)
from .decisions import ProcessingDecision, ExecutionPlan, ExecutionResult


class StimuliCategory(Enum):
    """Categories for external stimuli classification."""
    
    DIRECT_ADMIN = "direct_admin"  # Direct commands from admin
    USER_INTERACTION = "user_interaction"  # User chat or interaction
    SYSTEM_NOTIFICATION = "system_notification"  # Avatar state notifications
    SOCIAL_MEDIA = "social_media"  # Social media mentions and interactions
    AUTONOMOUS_TRIGGER = "autonomous_trigger"  # Autonomous mode triggers
    EMERGENCY = "emergency"  # Emergency/high-priority events
    CONTEXTUAL_UPDATE = "contextual_update"  # Context or environment updates
    UNKNOWN = "unknown"  # Cannot be categorized


class Priority(Enum):
    """Priority levels for stimuli processing."""
    
    CRITICAL = "critical"  # Immediate processing required
    HIGH = "high"  # High priority processing
    MEDIUM = "medium"  # Normal priority processing
    LOW = "low"  # Low priority, can be deferred
    MINIMAL = "minimal"  # Background processing only


@dataclass
class ExternalStimuli:
    """
    Base model for external stimuli.
    
    Represents any external input to the GraphFlow system that needs
    to be processed and potentially trigger avatar or agent responses.
    """
    
    content: str
    """The actual content/text of the stimuli."""
    
    source: str
    """Source identifier (e.g., 'user_chat', 'admin_console', 'social_media')."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for the stimuli."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """Timestamp when the stimuli was created."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the stimuli (user_id, platform, context, etc.)."""
    
    priority: Priority = Priority.MEDIUM
    """Processing priority level."""
    
    def validate(self) -> bool:
        """
        Validate stimuli data.
        
        Returns:
            bool: True if valid, False otherwise.
        """
        # Content must not be empty
        if not self.content or not self.content.strip():
            return False
            
        # Source must be specified
        if not self.source or not self.source.strip():
            return False
            
        # ID must be valid UUID format
        try:
            uuid.UUID(self.id)
        except ValueError:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the stimuli.
        """
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "priority": self.priority.value
        }


@dataclass
class CategorizedStimuli(ExternalStimuli):
    """
    Stimuli with categorization results.
    
    Extends ExternalStimuli with category classification information
    from the Categorizer Node processing.
    """
    
    category: StimuliCategory = StimuliCategory.UNKNOWN
    """The assigned category for this stimuli."""
    
    confidence: float = 0.0
    """Confidence score for the categorization (0.0 to 1.0)."""
    
    classification_metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata from the classification process."""
    
    def __post_init__(self):
        """Validate confidence score after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if categorization has high confidence.
        
        Args:
            threshold: Confidence threshold (default: 0.8).
            
        Returns:
            bool: True if confidence exceeds threshold.
        """
        return self.confidence >= threshold


@dataclass
class AnalyzedStimuli(CategorizedStimuli):
    """
    Stimuli with context analysis.
    
    Extends CategorizedStimuli with comprehensive context analysis
    from the Analyzer Node processing.
    """
    
    system_state_analysis: Optional[SystemStateAnalysis] = None
    """Analysis of current system state."""
    
    user_context_analysis: Optional[UserContextAnalysis] = None
    """Analysis of user interaction context."""
    
    environmental_analysis: Optional[EnvironmentalAnalysis] = None
    """Analysis of environmental context."""
    
    resource_analysis: Optional[ResourceAnalysis] = None
    """Analysis of system resource availability."""
    
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    """Timestamp when the analysis was completed."""
    
    processing_context: Optional[ProcessingContext] = None
    """Combined processing context from all analyses."""
    
    def get_context_score(self) -> float:
        """
        Calculate overall context favorability score.
        
        Returns:
            float: Score from 0.0 to 1.0 indicating processing favorability.
        """
        scores = []
        
        if self.system_state_analysis:
            scores.append(self.system_state_analysis.availability_score)
            
        if self.user_context_analysis:
            # Convert engagement level to score
            engagement_scores = {"low": 0.3, "medium": 0.6, "high": 0.9}
            scores.append(engagement_scores.get(
                self.user_context_analysis.engagement_level, 0.5
            ))
            
        if self.resource_analysis:
            # Average resource availability
            resource_score = (
                self.resource_analysis.cpu_availability +
                self.resource_analysis.memory_availability
            ) / 2.0
            scores.append(resource_score)
            
        return sum(scores) / len(scores) if scores else 0.5


@dataclass
class RoutingDecision:
    """
    Decision routing result.
    
    Represents the routing decision made by the Router Node
    including the execution plan and confidence.
    """
    
    stimuli_id: str
    """ID of the stimuli being routed."""
    
    decision: ProcessingDecision
    """The processing decision (e.g., AVATAR_AND_ANALYSIS)."""
    
    execution_plan: ExecutionPlan
    """Detailed execution plan for the decision."""
    
    confidence_score: float
    """Confidence in the routing decision (0.0 to 1.0)."""
    
    reasoning: str
    """Human-readable explanation of the routing decision."""
    
    decision_timestamp: datetime = field(default_factory=datetime.now)
    """Timestamp when the decision was made."""
    
    override_applied: bool = False
    """Whether any override rules were applied."""
    
    def __post_init__(self):
        """Validate routing decision data."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.confidence_score}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation.
        """
        return {
            "stimuli_id": self.stimuli_id,
            "decision": self.decision.value,
            "execution_plan": self.execution_plan.to_dict(),
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "decision_timestamp": self.decision_timestamp.isoformat(),
            "override_applied": self.override_applied
        }


@dataclass
class ProcessingResult:
    """
    Overall result of stimuli processing through the GraphFlow pipeline.
    
    Aggregates all execution results and provides a complete view
    of the stimuli processing outcome.
    """
    
    stimuli_id: str
    """ID of the processed stimuli."""
    
    success: bool
    """Overall success status."""
    
    category: StimuliCategory
    """Category assigned to the stimuli."""
    
    decision: ProcessingDecision
    """The processing decision that was made."""
    
    execution_results: List['ExecutionResult']
    """List of execution results from all operations."""
    
    processing_time: float
    """Total time taken for processing in seconds."""
    
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    """Confidence scores from various stages."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional processing metadata."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """Timestamp when processing completed."""
    
    def get_failed_operations(self) -> List['ExecutionResult']:
        """
        Get list of failed execution operations.
        
        Returns:
            List of failed execution results.
        """
        return [
            result for result in self.execution_results 
            if not result.success
        ]
    
    def get_success_rate(self) -> float:
        """
        Calculate success rate of executions.
        
        Returns:
            float: Success rate from 0.0 to 1.0.
        """
        if not self.execution_results:
            return 0.0
            
        successful = sum(
            1 for result in self.execution_results 
            if result.success
        )
        return successful / len(self.execution_results)