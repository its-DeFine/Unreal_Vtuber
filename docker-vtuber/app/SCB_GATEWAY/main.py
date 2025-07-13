"""SCB Gateway – FastAPI micro-service
===================================

Thin HTTP front-end for Shared Cognitive Blackboard v2.

Routes
------
GET  /health                      – health probe
GET  /scb/global/slice           – global slice (query param tokens=int)
GET  /scb/team/{team}/slice      – team slice (query param tokens=int)
POST /scb/team/{team}/event      – append event to team slice
POST /scb/global/summary         – append 50-char S1 summary to global slice

Security: optional API key via `SCB_API_KEY` env var; must be provided in
`X-SCB-Key` header if set.
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from docker_vtuber.app.CORE.autogen_agent.autogen_agent.clients.scb_v2_client import (
    SCBv2Client,
)

app = FastAPI(title="SCB Gateway", version="0.1")

# CORS – allow all origins by default (internal service)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration & helpers
# ---------------------------------------------------------------------------

_SCB_API_KEY = os.getenv("SCB_API_KEY")  # optional key
_scb_client = SCBv2Client()


def _check_key(request: Request):
    if _SCB_API_KEY and request.headers.get("X-SCB-Key") != _SCB_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def _trim_window_by_token_budget(slice_obj: Dict[str, Any], token_budget: int) -> Dict[str, Any]:
    summary = slice_obj.get("summary", "")
    window: List[Dict[str, Any]] = slice_obj.get("window", [])

    remaining = token_budget
    selected: List[Dict[str, Any]] = []

    # naive token estimate by whitespace splitting
    def _tokens(text: str) -> int:
        return len(text.split())

    for entry in reversed(window):  # newest first
        t = str(entry.get("text", ""))
        est = _tokens(t)
        if remaining - est < 0:
            break
        selected.append(entry)
        remaining -= est

    slice_obj["window"] = list(reversed(selected))
    return slice_obj


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EventPayload(BaseModel):
    event_type: str = Field(..., examples=["tool_call"])
    text: str = Field(..., max_length=500)
    actor: str = Field("s2_agent")

class SummaryPayload(BaseModel):
    text: str = Field(..., max_length=50)
    actor: str = Field("s1")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/scb/global/slice")
async def get_global_slice(request: Request, tokens: int = 600):
    _check_key(request)
    slice_obj = _scb_client.get_slice("scb:global")
    slice_obj = _trim_window_by_token_budget(slice_obj, tokens)
    return slice_obj

@app.get("/scb/team/{team}/slice")
async def get_team_slice(request: Request, team: str, tokens: int = 600):
    _check_key(request)
    key = f"scb:team:{team}"
    slice_obj = _scb_client.get_slice(key)
    slice_obj = _trim_window_by_token_budget(slice_obj, tokens)
    return slice_obj

@app.post("/scb/team/{team}/event", status_code=201)
async def post_team_event(request: Request, team: str, payload: EventPayload):
    _check_key(request)
    key = f"scb:team:{team}"
    _scb_client.append_event(key, payload.dict())
    return {"status": "stored", "key": key}

@app.post("/scb/global/summary", status_code=201)
async def post_global_summary(request: Request, payload: SummaryPayload):
    _check_key(request)
    event = {"type": "speech_summary", "actor": payload.actor, "text": payload.text}
    _scb_client.append_event("scb:global", event)
    return {"status": "stored"} 