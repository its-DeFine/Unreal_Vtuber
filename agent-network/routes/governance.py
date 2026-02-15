"""Governance proposals and voting routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..auth import require_admin, require_agent_or_admin
from ..models import GovernanceProposalCreate, GovernanceVote

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/proposals")
async def create_proposal(
    body: GovernanceProposalCreate,
    _caller: str = Depends(require_agent_or_admin),
):
    proposal_id = db.create_proposal(
        proposer_id=body.proposer_id or _caller,
        prop_type=body.type,
        title=body.title,
        description=body.description,
        payload=body.payload,
    )
    return {"proposal_id": proposal_id}


@router.get("/proposals")
async def list_proposals(
    status: str | None = Query(None),
    type: str | None = Query(None),
    _caller: str | None = None,
):
    proposals = db.list_proposals(status=status, prop_type=type)
    return {"proposals": proposals}


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    proposal = db.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/proposals/{proposal_id}/vote")
async def vote_on_proposal(
    proposal_id: str,
    body: GovernanceVote,
    _caller: str = Depends(require_admin),
):
    ok = db.vote_proposal(proposal_id, body.voter_id, body.vote)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot vote on this proposal")
    proposal = db.get_proposal(proposal_id)
    return {"ok": True, "status": proposal["status"] if proposal else "unknown"}


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(
    proposal_id: str,
    _caller: str = Depends(require_admin),
):
    ok = db.apply_proposal(proposal_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Proposal not approved or already applied")
    return {"applied": True}
