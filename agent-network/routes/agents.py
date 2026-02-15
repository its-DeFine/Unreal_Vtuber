"""Agent registration and heartbeat routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..auth import optional_auth, require_agent_or_admin
from ..models import AgentRegister, HeartbeatPayload

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register")
async def register(body: AgentRegister):
    token = db.register_agent(
        agent_id=body.agent_id,
        name=body.name,
        persona=body.persona,
        avatar_slug=body.avatar_slug,
        orchestrator_id=body.orchestrator_id,
        capabilities=body.capabilities,
    )
    return {"agent_id": body.agent_id, "token": token}


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatPayload,
    _caller: str = Depends(require_agent_or_admin),
):
    db.heartbeat_agent(body.agent_id, body.status, body.metrics)
    return {"ok": True}


@router.get("")
async def list_agents(_caller: str | None = Depends(optional_auth)):
    agents = db.list_agents()
    return {"agents": agents}


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    _caller: str | None = Depends(optional_auth),
):
    agent = db.get_agent(agent_id)
    if not agent:
        return {"error": "Agent not found"}, 404
    return agent
