"""Central calendar / scheduling routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import db
from ..auth import require_agent_or_admin
from ..models import CalendarBookRequest, CalendarEventCreate, CalendarEventUpdate

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/events")
async def create_event(
    body: CalendarEventCreate,
    _caller: str = Depends(require_agent_or_admin),
):
    event_id = db.create_event(
        title=body.title,
        event_type=body.event_type,
        participants=body.participants,
        scheduled_at=body.scheduled_at.isoformat(),
        duration_minutes=body.duration_minutes,
        proposed_by=body.proposed_by,
        notes=body.notes,
        recurrence=body.recurrence,
    )
    return {"event_id": event_id}


@router.get("/events")
async def list_events(
    participant: str | None = Query(None),
    status: str | None = Query(None),
    event_type: str | None = Query(None),
    _caller: str | None = None,
):
    events = db.list_events(participant=participant, status=status, event_type=event_type)
    return {"events": events}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    event = db.get_event(event_id)
    if not event:
        return {"error": "Event not found"}, 404
    return event


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    body: CalendarEventUpdate,
    _caller: str = Depends(require_agent_or_admin),
):
    updated = db.update_event(event_id, body.model_dump(exclude_none=True))
    return {"updated": updated}


@router.post("/book")
async def book_appointment(
    body: CalendarBookRequest,
    _caller: str = Depends(require_agent_or_admin),
):
    event_id = db.create_event(
        title=body.title,
        event_type=body.event_type,
        participants=body.participants,
        scheduled_at=body.scheduled_at.isoformat(),
        duration_minutes=body.duration_minutes,
        proposed_by=body.proposed_by,
        notes=body.notes,
        recurrence=None,
    )
    return {"event_id": event_id, "status": "proposed"}


@router.get("/availability/{agent_id}")
async def get_availability(agent_id: str):
    events = db.list_events(participant=agent_id, status="confirmed")
    return {"agent_id": agent_id, "busy_slots": events}
