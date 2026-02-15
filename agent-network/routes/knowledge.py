"""Shared knowledge base routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import db
from ..auth import require_agent_or_admin
from ..models import KnowledgeContribute, KnowledgeQuery

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/contribute")
async def contribute(
    body: KnowledgeContribute,
    _caller: str = Depends(require_agent_or_admin),
):
    kid = db.contribute_knowledge(
        contributor_id=body.contributor_id,
        category=body.category,
        content=body.content,
    )
    return {"id": kid}


@router.post("/query")
async def query(
    body: KnowledgeQuery,
    _caller: str | None = None,
):
    results = db.query_knowledge(body.query, category=body.category, limit=body.limit)
    return {"results": results}


@router.get("/recent")
async def recent(
    limit: int = Query(20, le=100),
    _caller: str | None = None,
):
    entries = db.recent_knowledge(limit=limit)
    return {"entries": entries}
