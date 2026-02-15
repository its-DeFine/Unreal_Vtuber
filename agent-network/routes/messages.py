"""Cross-agent messaging routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import db
from ..auth import require_agent_or_admin
from ..models import MessageSend

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/send")
async def send_message(
    body: MessageSend,
    _caller: str = Depends(require_agent_or_admin),
):
    msg_id = db.send_message(body.from_agent, body.to_agent, body.type, body.payload)
    return {"id": msg_id}


@router.get("/{agent_id}")
async def get_messages(
    agent_id: str,
    since: str | None = Query(None),
    _caller: str = Depends(require_agent_or_admin),
):
    messages = db.get_messages(agent_id, since=since)
    return {"messages": messages}
