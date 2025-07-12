"""
Unified Stimuli Processing System
===============================

Consolidates all stimuli processing logic into a single, clean architecture.
"""

from .stimuli_processor import (
    StimuliProcessor,
    StimuliRequest,
    ProcessingResult,
    ProcessingMode,
    TeamType,
    StimuliRouter,
    ProcessingStrategy,
    S1ProcessingStrategy,
    S2ProcessingStrategy,
    process_stimuli_unified,
    enqueue_for_s2_team
)

__all__ = [
    "StimuliProcessor",
    "StimuliRequest",
    "ProcessingResult", 
    "ProcessingMode",
    "TeamType",
    "StimuliRouter",
    "ProcessingStrategy",
    "S1ProcessingStrategy",
    "S2ProcessingStrategy",
    "process_stimuli_unified",
    "enqueue_for_s2_team"
]