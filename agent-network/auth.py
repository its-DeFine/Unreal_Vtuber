"""Bearer-token authentication for the agent-network API."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from . import db

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


async def require_agent_or_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Returns the agent_id if valid agent token, or 'admin' if admin token."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    if ADMIN_TOKEN and token == ADMIN_TOKEN:
        return "admin"
    agent_id = db.validate_token(token)
    if agent_id:
        return agent_id
    raise HTTPException(status_code=403, detail="Invalid token")


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Requires admin token."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    if ADMIN_TOKEN and token == ADMIN_TOKEN:
        return "admin"
    raise HTTPException(status_code=403, detail="Admin token required")


async def optional_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """Returns agent_id/admin if token present, None otherwise."""
    token = _extract_token(authorization)
    if not token:
        return None
    if ADMIN_TOKEN and token == ADMIN_TOKEN:
        return "admin"
    return db.validate_token(token)
