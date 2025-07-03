"""
GraphFlow External Stimuli System data models.

This package contains all the core data models for the GraphFlow-based
external stimuli handling system including stimuli models, context analysis
models, and decision/execution models.
"""

# Import all models for easy access
from .stimuli import (
    ExternalStimuli,
    CategorizedStimuli,
    AnalyzedStimuli,
    RoutingDecision,
    StimuliCategory,
    Priority
)

from .context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis,
    ProcessingContext
)

from .decisions import (
    ProcessingDecision,
    ExecutionPlan,
    ExecutionResult,
    ProcessingResult,
    RetryPolicy
)

# Import System2 models
from .system2_models import (
    AgentStatusInfo,
    AgentStatus,
    AnalysisResult,
    AnalysisStatus,
    MemoryResult,
    EvolutionResult,
    System2Response
)

# Define what's available when using "from models import *"
__all__ = [
    # Stimuli models
    "ExternalStimuli",
    "CategorizedStimuli", 
    "AnalyzedStimuli",
    "RoutingDecision",
    "StimuliCategory",
    "Priority",
    
    # Context models
    "SystemStateAnalysis",
    "UserContextAnalysis",
    "EnvironmentalAnalysis",
    "ResourceAnalysis",
    "ProcessingContext",
    
    # Decision models
    "ProcessingDecision",
    "ExecutionPlan",
    "ExecutionResult",
    "ProcessingResult",
    "RetryPolicy",
    
    # System2 models
    "AgentStatusInfo",
    "AgentStatus",
    "AnalysisResult",
    "AnalysisStatus",
    "MemoryResult",
    "EvolutionResult",
    "System2Response"
]

# Version information
__version__ = "1.0.0"
__author__ = "GraphFlow Development Team"