"""
Simple response class for stimuli processing.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class StimuliResponse:
    """Response from stimuli processing"""
    stimuli_id: str
    success: bool
    processing_time: float
    tools_triggered: List[str]
    agent_decision: Optional[str] = None
    response_content: Optional[str] = None
    error_message: Optional[str] = None