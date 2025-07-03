"""
Context analysis models for GraphFlow stimuli processing.

This module defines data models for various context analyses including
system state, user context, environmental factors, and resource availability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SystemStateAnalysis:
    """
    Analysis of current system state.
    
    Provides comprehensive view of the system's current operational state
    including avatar status, processing queues, and overall availability.
    """
    
    is_speaking: bool
    """Whether the avatar is currently speaking."""
    
    is_idle: bool
    """Whether the system is in idle state."""
    
    is_busy: bool
    """Whether the system is busy processing other tasks."""
    
    has_errors: bool
    """Whether there are any system errors present."""
    
    queue_size: int
    """Number of items in the processing queue."""
    
    resource_utilization: Dict[str, float]
    """Current resource utilization metrics (CPU, memory, etc.)."""
    
    availability_score: float
    """Overall system availability score (0.0 to 1.0)."""
    
    active_processes: List[str] = field(default_factory=list)
    """List of currently active process identifiers."""
    
    last_activity_timestamp: Optional[datetime] = None
    """Timestamp of last system activity."""
    
    error_details: Optional[Dict[str, Any]] = None
    """Details about any current errors if present."""
    
    def __post_init__(self):
        """Validate system state analysis data."""
        if not 0.0 <= self.availability_score <= 1.0:
            raise ValueError(
                f"Availability score must be between 0.0 and 1.0, got {self.availability_score}"
            )
        
        # Validate resource utilization values
        for resource, utilization in self.resource_utilization.items():
            if not 0.0 <= utilization <= 1.0:
                raise ValueError(
                    f"Resource utilization for {resource} must be between 0.0 and 1.0, got {utilization}"
                )
    
    def is_available(self, threshold: float = 0.7) -> bool:
        """
        Check if system is available for processing.
        
        Args:
            threshold: Availability threshold (default: 0.7).
            
        Returns:
            bool: True if system is available.
        """
        return self.availability_score >= threshold and not self.has_errors


@dataclass
class UserContextAnalysis:
    """
    Analysis of user interaction context.
    
    Captures user engagement patterns, interaction history,
    and preferences to inform processing decisions.
    """
    
    interaction_frequency: float
    """Average interactions per minute."""
    
    engagement_level: str
    """Current engagement level: 'low', 'medium', or 'high'."""
    
    recent_topics: List[str]
    """List of recent conversation topics."""
    
    user_preference_match: float
    """How well the stimuli matches user preferences (0.0 to 1.0)."""
    
    historical_response_patterns: Dict[str, Any]
    """Historical patterns in user responses and interactions."""
    
    user_id: Optional[str] = None
    """Identifier for the user if available."""
    
    session_duration: Optional[float] = None
    """Current session duration in seconds."""
    
    sentiment_score: Optional[float] = None
    """User sentiment score (-1.0 to 1.0)."""
    
    interaction_context: Dict[str, Any] = field(default_factory=dict)
    """Additional interaction context metadata."""
    
    def __post_init__(self):
        """Validate user context analysis data."""
        valid_engagement_levels = {"low", "medium", "high"}
        if self.engagement_level not in valid_engagement_levels:
            raise ValueError(
                f"Engagement level must be one of {valid_engagement_levels}, got {self.engagement_level}"
            )
        
        if not 0.0 <= self.user_preference_match <= 1.0:
            raise ValueError(
                f"User preference match must be between 0.0 and 1.0, got {self.user_preference_match}"
            )
        
        if self.sentiment_score is not None:
            if not -1.0 <= self.sentiment_score <= 1.0:
                raise ValueError(
                    f"Sentiment score must be between -1.0 and 1.0, got {self.sentiment_score}"
                )
    
    def is_highly_engaged(self) -> bool:
        """
        Check if user is highly engaged.
        
        Returns:
            bool: True if user engagement is high.
        """
        return self.engagement_level == "high" and self.interaction_frequency > 0.5


@dataclass
class EnvironmentalAnalysis:
    """
    Analysis of environmental context.
    
    Captures environmental factors that may influence processing decisions
    such as mode settings, streaming status, and external events.
    """
    
    autonomous_mode_active: bool
    """Whether autonomous mode is currently active."""
    
    streaming_status: str
    """Current streaming status: 'live', 'offline', 'scheduled'."""
    
    time_of_day_factor: float
    """Time-based activity factor (0.0 to 1.0)."""
    
    recent_activity_level: str
    """Recent activity level: 'low', 'moderate', 'high'."""
    
    external_event_context: Dict[str, Any]
    """Context about any external events affecting the system."""
    
    platform_context: Optional[str] = None
    """Platform where the system is operating (e.g., 'twitch', 'youtube')."""
    
    audience_size: Optional[int] = None
    """Current audience size if streaming."""
    
    environmental_triggers: List[str] = field(default_factory=list)
    """List of active environmental triggers."""
    
    mode_settings: Dict[str, Any] = field(default_factory=dict)
    """Current mode configuration settings."""
    
    def __post_init__(self):
        """Validate environmental analysis data."""
        valid_streaming_statuses = {"live", "offline", "scheduled"}
        if self.streaming_status not in valid_streaming_statuses:
            raise ValueError(
                f"Streaming status must be one of {valid_streaming_statuses}, got {self.streaming_status}"
            )
        
        valid_activity_levels = {"low", "moderate", "high"}
        if self.recent_activity_level not in valid_activity_levels:
            raise ValueError(
                f"Activity level must be one of {valid_activity_levels}, got {self.recent_activity_level}"
            )
        
        if not 0.0 <= self.time_of_day_factor <= 1.0:
            raise ValueError(
                f"Time of day factor must be between 0.0 and 1.0, got {self.time_of_day_factor}"
            )
    
    def is_live_streaming(self) -> bool:
        """
        Check if currently live streaming.
        
        Returns:
            bool: True if streaming live.
        """
        return self.streaming_status == "live" and (self.audience_size or 0) > 0


@dataclass
class ResourceAnalysis:
    """
    Analysis of system resource availability.
    
    Provides detailed view of available computational resources
    and system capacity for processing stimuli.
    """
    
    cpu_availability: float
    """Available CPU capacity (0.0 to 1.0)."""
    
    memory_availability: float
    """Available memory capacity (0.0 to 1.0)."""
    
    agent_availability: Dict[str, bool]
    """Availability status of individual agents."""
    
    system1_availability: bool
    """Whether System1 (avatar/speech) is available."""
    
    system2_availability: bool
    """Whether System2 (multi-agent) is available."""
    
    estimated_processing_capacity: int
    """Estimated number of stimuli that can be processed concurrently."""
    
    gpu_availability: Optional[float] = None
    """Available GPU capacity if applicable (0.0 to 1.0)."""
    
    network_bandwidth_available: Optional[float] = None
    """Available network bandwidth in Mbps."""
    
    storage_availability: Optional[float] = None
    """Available storage capacity (0.0 to 1.0)."""
    
    resource_pressure_level: str = "normal"
    """Overall resource pressure: 'low', 'normal', 'high', 'critical'."""
    
    bottlenecks: List[str] = field(default_factory=list)
    """List of identified resource bottlenecks."""
    
    def __post_init__(self):
        """Validate resource analysis data."""
        # Validate availability metrics
        for metric_name, metric_value in [
            ("cpu_availability", self.cpu_availability),
            ("memory_availability", self.memory_availability),
            ("gpu_availability", self.gpu_availability),
            ("storage_availability", self.storage_availability)
        ]:
            if metric_value is not None and not 0.0 <= metric_value <= 1.0:
                raise ValueError(
                    f"{metric_name} must be between 0.0 and 1.0, got {metric_value}"
                )
        
        valid_pressure_levels = {"low", "normal", "high", "critical"}
        if self.resource_pressure_level not in valid_pressure_levels:
            raise ValueError(
                f"Resource pressure level must be one of {valid_pressure_levels}, "
                f"got {self.resource_pressure_level}"
            )
    
    def has_sufficient_resources(self, threshold: float = 0.3) -> bool:
        """
        Check if system has sufficient resources for processing.
        
        Args:
            threshold: Minimum resource threshold (default: 0.3).
            
        Returns:
            bool: True if resources are sufficient.
        """
        return (
            self.cpu_availability >= threshold and
            self.memory_availability >= threshold and
            self.estimated_processing_capacity > 0
        )
    
    def get_limiting_resource(self) -> Optional[str]:
        """
        Identify the most limiting resource.
        
        Returns:
            Optional[str]: Name of the limiting resource or None.
        """
        resources = {
            "cpu": self.cpu_availability,
            "memory": self.memory_availability
        }
        
        if self.gpu_availability is not None:
            resources["gpu"] = self.gpu_availability
            
        if resources:
            return min(resources.items(), key=lambda x: x[1])[0]
        
        return None


@dataclass
class ProcessingContext:
    """
    Combined processing context from all analyses.
    
    Aggregates all context analyses to provide a unified view
    for decision making.
    """
    
    flow_id: str = ""
    """ID of the processing flow."""
    
    parallel_analysis: bool = False
    """Whether analysis was done in parallel."""
    
    analysis_depth: str = "standard"
    """Depth of analysis performed."""
    
    system_state: Optional[SystemStateAnalysis] = None
    """System state analysis results."""
    
    user_context: Optional[UserContextAnalysis] = None
    """User context analysis results."""
    
    environment: Optional[EnvironmentalAnalysis] = None
    """Environmental analysis results."""
    
    resources: Optional[ResourceAnalysis] = None
    """Resource availability analysis results."""
    
    context_quality_score: float = 0.0
    """Overall quality score of the context (0.0 to 1.0)."""
    
    processing_recommendations: List[str] = field(default_factory=list)
    """List of processing recommendations based on context."""
    
    risk_factors: List[str] = field(default_factory=list)
    """Identified risk factors for processing."""
    
    optimization_hints: Dict[str, Any] = field(default_factory=dict)
    """Hints for optimizing processing based on context."""
    
    def __post_init__(self):
        """Calculate context quality score if not provided."""
        if self.context_quality_score == 0.0:
            self.context_quality_score = self._calculate_quality_score()
    
    def _calculate_quality_score(self) -> float:
        """
        Calculate overall context quality score.
        
        Returns:
            float: Quality score from 0.0 to 1.0.
        """
        scores = []
        
        if self.system_state:
            scores.append(self.system_state.availability_score)
        
        if self.user_context:
            scores.append(self.user_context.user_preference_match)
        
        if self.environment:
            scores.append(self.environment.time_of_day_factor)
        
        if self.resources:
            scores.append(
                (self.resources.cpu_availability + self.resources.memory_availability) / 2.0
            )
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def is_favorable_for_processing(self, threshold: float = 0.6) -> bool:
        """
        Check if context is favorable for processing.
        
        Args:
            threshold: Favorability threshold (default: 0.6).
            
        Returns:
            bool: True if context is favorable.
        """
        return (
            self.context_quality_score >= threshold and
            (not self.system_state or not self.system_state.has_errors) and
            (not self.resources or self.resources.has_sufficient_resources())
        )