"""Pydantic models for the agent-network API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentRegister(BaseModel):
    agent_id: str
    name: str
    persona: str = ""
    avatar_slug: str = ""
    orchestrator_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class Agent(BaseModel):
    agent_id: str
    name: str
    persona: str = ""
    avatar_slug: str = ""
    orchestrator_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    status: str = "online"
    last_heartbeat: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class HeartbeatPayload(BaseModel):
    agent_id: str
    status: str = "online"
    metrics: dict[str, Any] = Field(default_factory=dict)


class MessageSend(BaseModel):
    from_agent: str
    to_agent: str | None = None  # None = broadcast
    type: str = "chat"
    payload: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    id: str
    from_agent: str
    to_agent: str | None = None
    type: str = "chat"
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime


class CalendarEventCreate(BaseModel):
    title: str
    event_type: str = "stream"
    participants: list[str] = Field(default_factory=list)
    scheduled_at: datetime
    duration_minutes: int = 30
    proposed_by: str = ""
    notes: str | None = None
    recurrence: str | None = None


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    event_type: str
    participants: list[str] = Field(default_factory=list)
    scheduled_at: datetime
    duration_minutes: int = 30
    status: str = "proposed"
    proposed_by: str = ""
    notes: str | None = None
    recurrence: str | None = None


class CalendarEventUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    notes: str | None = None


class CalendarBookRequest(BaseModel):
    title: str
    event_type: str = "agent_meeting"
    participants: list[str]
    scheduled_at: datetime
    duration_minutes: int = 30
    proposed_by: str = ""
    notes: str | None = None


class KnowledgeContribute(BaseModel):
    contributor_id: str
    category: str = "strategy"
    content: str


class KnowledgeEntry(BaseModel):
    id: str
    contributor_id: str
    category: str
    content: str
    embedding: list[float] | None = None
    usefulness_score: float = 0.0
    ts: datetime


class KnowledgeQuery(BaseModel):
    query: str
    category: str | None = None
    limit: int = 10


class GovernanceProposalCreate(BaseModel):
    proposer_id: str = ""
    type: str = "config_change"
    title: str
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class GovernanceProposal(BaseModel):
    proposal_id: str
    proposer_id: str
    type: str
    title: str
    description: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "open"
    votes: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    resolved_at: datetime | None = None


class GovernanceVote(BaseModel):
    voter_id: str
    vote: str  # "approve" | "reject"


class CoachingDirectiveCreate(BaseModel):
    from_orchestrator: str
    to_agent: str
    directive: str
    priority: str = "medium"


class CoachingDirective(BaseModel):
    id: str
    from_orchestrator: str
    to_agent: str
    directive: str
    priority: str = "medium"
    ts: datetime
    acknowledged: bool = False
