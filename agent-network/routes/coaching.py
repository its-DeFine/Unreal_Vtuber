"""Orchestrator coaching directive routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db
from ..auth import require_admin, require_agent_or_admin
from ..models import CoachingDirectiveCreate

router = APIRouter(prefix="/coaching", tags=["coaching"])


@router.post("/directive")
async def create_directive(
    body: CoachingDirectiveCreate,
    _caller: str = Depends(require_admin),
):
    did = db.create_directive(
        from_orchestrator=body.from_orchestrator,
        to_agent=body.to_agent,
        directive=body.directive,
        priority=body.priority,
    )
    return {"id": did}


@router.get("/{agent_id}")
async def get_directives(
    agent_id: str,
    _caller: str = Depends(require_agent_or_admin),
):
    directives = db.get_directives(agent_id, only_pending=True)
    return {"directives": directives}


@router.post("/{agent_id}/acknowledge")
async def acknowledge(
    agent_id: str,
    _caller: str = Depends(require_agent_or_admin),
):
    count = db.acknowledge_directive(agent_id)
    return {"acknowledged": count}
