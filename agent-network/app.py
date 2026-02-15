"""
agent-network server — Central hub for inter-agent communication,
scheduling, knowledge sharing, governance, and orchestrator coaching.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .routes import agents, calendar, coaching, governance, knowledge, leaderboard, messages

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, agent_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[agent_id] = ws

    def disconnect(self, agent_id: str):
        self._connections.pop(agent_id, None)

    async def send_to(self, agent_id: str, data: dict):
        ws = self._connections.get(agent_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(agent_id)

    async def broadcast(self, data: dict, exclude: str | None = None):
        for aid, ws in list(self._connections.items()):
            if aid == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(aid)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB is initialised
    db.get_conn()
    yield
    # Shutdown: nothing special needed


app = FastAPI(
    title="Embody Agent Network",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount route modules
# ---------------------------------------------------------------------------

app.include_router(agents.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(governance.router, prefix="/api/v1")
app.include_router(coaching.router, prefix="/api/v1")
app.include_router(leaderboard.router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/api/v1/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(agent_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Relay message to target or broadcast
            to = msg.get("to_agent")
            if to:
                await manager.send_to(to, msg)
            else:
                await manager.broadcast(msg, exclude=agent_id)
    except WebSocketDisconnect:
        manager.disconnect(agent_id)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
