"""
Data models for orchestrator
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
from datetime import datetime


class StimulusRequest(BaseModel):
    """Incoming stimulus request"""
    stimulus_id: str = Field(..., description="Unique stimulus identifier")
    text: str = Field(..., description="The stimulus text to process")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: Literal["low", "normal", "high"] = Field(default="normal")


class RoutingDecision(BaseModel):
    """Routing decision made by orchestrator"""
    stimulus_id: str
    stimulus_text: str = Field(..., description="Original stimulus text")
    system: Literal["s1", "s2", "both"]
    config: Dict[str, Any] = Field(..., description="System-specific configuration")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Brief explanation of routing decision")
    latency_ms: int = Field(..., description="Decision latency in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "stimulus_id": "stim_123",
                "system": "s1",
                "config": {
                    "persona": "trader"
                },
                "confidence": 0.95,
                "reasoning": "Real-time market query requiring immediate response",
                "latency_ms": 8
            }
        }


class ExecutionResult(BaseModel):
    """Result from executing a routing decision"""
    stimulus_id: str
    decision: RoutingDecision
    results: Dict[str, Any]
    total_latency_ms: int
    success: bool
    error: Optional[str] = None


class HealthStatus(BaseModel):
    """Health check status"""
    status: Literal["healthy", "degraded", "unhealthy"]
    apis: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)