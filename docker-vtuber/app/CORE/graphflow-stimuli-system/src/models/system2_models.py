"""
System2 Integration Models for GraphFlow.

This module contains data models specific to System2 (multi-agent)
integration including agent status, analysis results, and memory results.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    """Status of an AutoGen agent."""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class AnalysisStatus(Enum):
    """Status of an analysis task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentStatusInfo:
    """
    Detailed status information for an AutoGen agent.
    
    Attributes:
        agent_id: Unique identifier for the agent
        agent_type: Type of agent (cognitive_ai, programmer, observer)
        status: Current agent status
        current_task: ID of currently processing task (if any)
        queue_size: Number of tasks in agent's queue
        last_active: Timestamp of last activity
        error_count: Number of recent errors
        performance_metrics: Performance statistics
    """
    agent_id: str
    agent_type: str
    status: AgentStatus
    current_task: Optional[str] = None
    queue_size: int = 0
    last_active: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return self.status in [AgentStatus.ACTIVE, AgentStatus.IDLE]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "current_task": self.current_task,
            "queue_size": self.queue_size,
            "last_active": self.last_active.isoformat(),
            "error_count": self.error_count,
            "performance_metrics": self.performance_metrics
        }


@dataclass
class AnalysisResult:
    """
    Result from System2 agent analysis.
    
    Attributes:
        task_id: Unique identifier for the analysis task
        stimuli_id: ID of the analyzed stimuli
        status: Current analysis status
        agent_id: ID of agent that performed analysis
        analysis_type: Type of analysis performed
        results: Analysis results and findings
        recommendations: Recommended actions
        confidence_score: Confidence in analysis results
        processing_time: Time taken for analysis
        timestamp: When analysis was completed
        metadata: Additional metadata
    """
    task_id: str
    stimuli_id: str
    status: AnalysisStatus
    agent_id: str
    analysis_type: str
    results: Dict[str, Any]
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_complete(self) -> bool:
        """Check if analysis is complete."""
        return self.status == AnalysisStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if analysis failed."""
        return self.status == AnalysisStatus.FAILED
    
    def get_primary_recommendation(self) -> Optional[Dict[str, Any]]:
        """Get the primary recommendation if available."""
        if self.recommendations:
            return max(self.recommendations, key=lambda r: r.get("priority", 0))
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "stimuli_id": self.stimuli_id,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "analysis_type": self.analysis_type,
            "results": self.results,
            "recommendations": self.recommendations,
            "confidence_score": self.confidence_score,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class MemoryResult:
    """
    Result from Cognee memory system query.
    
    Attributes:
        memory_id: Unique identifier for the memory
        content: Memory content
        relevance: Relevance score (0-1)
        memory_type: Type of memory (episodic, semantic, etc.)
        timestamp: When memory was created
        metadata: Additional memory metadata
        related_memories: IDs of related memories
        embeddings: Vector embeddings (if available)
    """
    memory_id: str
    content: str
    relevance: float
    memory_type: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_memories: List[str] = field(default_factory=list)
    embeddings: Optional[List[float]] = None
    
    def is_highly_relevant(self, threshold: float = 0.8) -> bool:
        """Check if memory is highly relevant."""
        return self.relevance >= threshold
    
    def get_context_window(self, before_minutes: int = 5, after_minutes: int = 5) -> Dict[str, datetime]:
        """Get time window around this memory."""
        return {
            "start": self.timestamp - timedelta(minutes=before_minutes),
            "end": self.timestamp + timedelta(minutes=after_minutes)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "relevance": self.relevance,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "related_memories": self.related_memories,
            "has_embeddings": self.embeddings is not None
        }


@dataclass
class EvolutionResult:
    """
    Result from evolution engine analysis.
    
    Attributes:
        evolution_id: Unique identifier for evolution analysis
        stimuli_id: ID of stimuli that triggered evolution
        evolution_type: Type of evolution analysis
        insights: Key insights discovered
        adaptations: Suggested system adaptations
        learning_points: Points for system learning
        impact_score: Predicted impact of adaptations
        confidence: Confidence in evolution recommendations
        timestamp: When evolution analysis completed
    """
    evolution_id: str
    stimuli_id: str
    evolution_type: str
    insights: List[Dict[str, Any]]
    adaptations: List[Dict[str, Any]] = field(default_factory=list)
    learning_points: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def has_high_impact(self, threshold: float = 0.7) -> bool:
        """Check if evolution has high impact potential."""
        return self.impact_score >= threshold
    
    def get_top_adaptations(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get top N adaptations by priority."""
        sorted_adaptations = sorted(
            self.adaptations,
            key=lambda a: a.get("priority", 0),
            reverse=True
        )
        return sorted_adaptations[:n]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evolution_id": self.evolution_id,
            "stimuli_id": self.stimuli_id,
            "evolution_type": self.evolution_type,
            "insights": self.insights,
            "adaptations": self.adaptations,
            "learning_points": self.learning_points,
            "impact_score": self.impact_score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class System2Response:
    """
    Aggregated response from System2 processing.
    
    Combines results from multiple agents, memory queries,
    and evolution analysis into a unified response.
    """
    stimuli_id: str
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    memory_results: List[MemoryResult] = field(default_factory=list)
    evolution_result: Optional[EvolutionResult] = None
    agent_statuses: Dict[str, AgentStatusInfo] = field(default_factory=dict)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_consensus_recommendation(self) -> Optional[Dict[str, Any]]:
        """Get consensus recommendation from all analyses."""
        if not self.analysis_results:
            return None
        
        # Collect all recommendations
        all_recommendations = []
        for result in self.analysis_results:
            if result.is_complete():
                all_recommendations.extend(result.recommendations)
        
        if not all_recommendations:
            return None
        
        # Find most common recommendation type
        recommendation_types = {}
        for rec in all_recommendations:
            rec_type = rec.get("type", "unknown")
            if rec_type not in recommendation_types:
                recommendation_types[rec_type] = []
            recommendation_types[rec_type].append(rec)
        
        # Return the most common type with highest average confidence
        best_type = max(recommendation_types.keys(), key=lambda t: len(recommendation_types[t]))
        best_recommendations = recommendation_types[best_type]
        
        # Average the confidence scores
        avg_confidence = sum(r.get("confidence", 0) for r in best_recommendations) / len(best_recommendations)
        
        return {
            "type": best_type,
            "confidence": avg_confidence,
            "count": len(best_recommendations),
            "details": best_recommendations[0]  # Use first as representative
        }
    
    def get_relevant_memories(self, threshold: float = 0.7) -> List[MemoryResult]:
        """Get memories above relevance threshold."""
        return [m for m in self.memory_results if m.relevance >= threshold]
    
    def has_evolution_insights(self) -> bool:
        """Check if evolution analysis produced insights."""
        return self.evolution_result is not None and len(self.evolution_result.insights) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stimuli_id": self.stimuli_id,
            "analysis_results": [r.to_dict() for r in self.analysis_results],
            "memory_results": [m.to_dict() for m in self.memory_results],
            "evolution_result": self.evolution_result.to_dict() if self.evolution_result else None,
            "agent_statuses": {k: v.to_dict() for k, v in self.agent_statuses.items()},
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_analyses": len(self.analysis_results),
                "completed_analyses": sum(1 for r in self.analysis_results if r.is_complete()),
                "total_memories": len(self.memory_results),
                "relevant_memories": len(self.get_relevant_memories()),
                "has_evolution": self.has_evolution_insights(),
                "consensus_recommendation": self.get_consensus_recommendation()
            }
        }


# Add to imports for backward compatibility
from datetime import timedelta