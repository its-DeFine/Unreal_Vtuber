"""SQLite persistence layer for the agent-network server."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/agent-network.db")
LOG_PATH = os.getenv("LOG_PATH", "/data/events.jsonl")

_conn: sqlite3.Connection | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_hash(*parts: str) -> str:
    h = hashlib.sha256("".join(parts).encode()).hexdigest()
    return h[:16]


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _migrate(_conn)
    return _conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id       TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            persona        TEXT DEFAULT '',
            avatar_slug    TEXT DEFAULT '',
            orchestrator_id TEXT,
            capabilities   TEXT DEFAULT '[]',
            status         TEXT DEFAULT 'online',
            last_heartbeat TEXT,
            metrics        TEXT DEFAULT '{}',
            token          TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id         TEXT PRIMARY KEY,
            from_agent TEXT NOT NULL,
            to_agent   TEXT,
            type       TEXT DEFAULT 'chat',
            payload    TEXT DEFAULT '{}',
            ts         TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent, ts);

        CREATE TABLE IF NOT EXISTS calendar_events (
            event_id         TEXT PRIMARY KEY,
            title            TEXT NOT NULL,
            event_type       TEXT DEFAULT 'stream',
            participants     TEXT DEFAULT '[]',
            scheduled_at     TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 30,
            status           TEXT DEFAULT 'proposed',
            proposed_by      TEXT DEFAULT '',
            notes            TEXT,
            recurrence       TEXT
        );

        CREATE TABLE IF NOT EXISTS knowledge (
            id               TEXT PRIMARY KEY,
            contributor_id   TEXT NOT NULL,
            category         TEXT DEFAULT 'strategy',
            content          TEXT NOT NULL,
            embedding        TEXT,
            usefulness_score REAL DEFAULT 0.0,
            ts               TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS governance_proposals (
            proposal_id  TEXT PRIMARY KEY,
            proposer_id  TEXT NOT NULL,
            type         TEXT DEFAULT 'config_change',
            title        TEXT NOT NULL,
            description  TEXT DEFAULT '',
            payload      TEXT DEFAULT '{}',
            status       TEXT DEFAULT 'open',
            votes        TEXT DEFAULT '{}',
            created_at   TEXT NOT NULL,
            resolved_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS coaching_directives (
            id               TEXT PRIMARY KEY,
            from_orchestrator TEXT NOT NULL,
            to_agent         TEXT NOT NULL,
            directive        TEXT NOT NULL,
            priority         TEXT DEFAULT 'medium',
            ts               TEXT NOT NULL,
            acknowledged     INTEGER DEFAULT 0
        );
    """)


def _append_log(event_type: str, data: dict[str, Any]) -> None:
    """Append an event to the JSONL audit log."""
    try:
        Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        entry = {"type": event_type, "ts": _now_iso(), **data}
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Logging is best-effort


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def register_agent(
    agent_id: str,
    name: str,
    persona: str = "",
    avatar_slug: str = "",
    orchestrator_id: str | None = None,
    capabilities: list[str] | None = None,
) -> str:
    """Register or update an agent. Returns bearer token."""
    conn = get_conn()
    token = _short_hash(agent_id, _now_iso())
    conn.execute(
        """INSERT INTO agents (agent_id, name, persona, avatar_slug, orchestrator_id, capabilities, status, last_heartbeat, token)
           VALUES (?, ?, ?, ?, ?, ?, 'online', ?, ?)
           ON CONFLICT(agent_id) DO UPDATE SET
             name=excluded.name, persona=excluded.persona, avatar_slug=excluded.avatar_slug,
             orchestrator_id=excluded.orchestrator_id, capabilities=excluded.capabilities,
             status='online', last_heartbeat=excluded.last_heartbeat, token=excluded.token""",
        (agent_id, name, persona, avatar_slug, orchestrator_id,
         json.dumps(capabilities or []), _now_iso(), token),
    )
    conn.commit()
    _append_log("agent_register", {"agent_id": agent_id})
    return token


def heartbeat_agent(agent_id: str, status: str, metrics: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE agents SET status=?, last_heartbeat=?, metrics=? WHERE agent_id=?",
        (status, _now_iso(), json.dumps(metrics), agent_id),
    )
    conn.commit()


def list_agents() -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["capabilities"] = json.loads(d.get("capabilities") or "[]")
        d["metrics"] = json.loads(d.get("metrics") or "{}")
        d.pop("token", None)
        result.append(d)
    return result


def get_agent(agent_id: str) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["capabilities"] = json.loads(d.get("capabilities") or "[]")
    d["metrics"] = json.loads(d.get("metrics") or "{}")
    d.pop("token", None)
    return d


def validate_token(token: str) -> str | None:
    """Returns agent_id if token is valid, else None."""
    conn = get_conn()
    row = conn.execute("SELECT agent_id FROM agents WHERE token=?", (token,)).fetchone()
    return row["agent_id"] if row else None


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def send_message(from_agent: str, to_agent: str | None, msg_type: str, payload: dict[str, Any]) -> str:
    conn = get_conn()
    ts = _now_iso()
    msg_id = _short_hash(from_agent, to_agent or "broadcast", ts)
    conn.execute(
        "INSERT INTO messages (id, from_agent, to_agent, type, payload, ts) VALUES (?,?,?,?,?,?)",
        (msg_id, from_agent, to_agent, msg_type, json.dumps(payload), ts),
    )
    conn.commit()
    _append_log("message_send", {"id": msg_id, "from": from_agent, "to": to_agent})
    return msg_id


def get_messages(agent_id: str, since: str | None = None) -> list[dict[str, Any]]:
    conn = get_conn()
    if since:
        rows = conn.execute(
            "SELECT * FROM messages WHERE (to_agent=? OR to_agent IS NULL) AND ts>? ORDER BY ts",
            (agent_id, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM messages WHERE (to_agent=? OR to_agent IS NULL) ORDER BY ts DESC LIMIT 50",
            (agent_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.get("payload") or "{}")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def create_event(
    title: str, event_type: str, participants: list[str],
    scheduled_at: str, duration_minutes: int, proposed_by: str,
    notes: str | None, recurrence: str | None,
) -> str:
    conn = get_conn()
    event_id = _short_hash(title, scheduled_at, _now_iso())
    conn.execute(
        """INSERT INTO calendar_events
           (event_id, title, event_type, participants, scheduled_at, duration_minutes, status, proposed_by, notes, recurrence)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (event_id, title, event_type, json.dumps(participants), scheduled_at,
         duration_minutes, "proposed", proposed_by, notes, recurrence),
    )
    conn.commit()
    _append_log("event_create", {"event_id": event_id, "title": title})
    return event_id


def list_events(
    participant: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    conn = get_conn()
    query = "SELECT * FROM calendar_events WHERE 1=1"
    params: list[Any] = []
    if status:
        query += " AND status=?"
        params.append(status)
    if event_type:
        query += " AND event_type=?"
        params.append(event_type)
    query += " ORDER BY scheduled_at"
    rows = conn.execute(query, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["participants"] = json.loads(d.get("participants") or "[]")
        if participant and participant not in d["participants"]:
            continue
        result.append(d)
    return result


def get_event(event_id: str) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM calendar_events WHERE event_id=?", (event_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["participants"] = json.loads(d.get("participants") or "[]")
    return d


def update_event(event_id: str, updates: dict[str, Any]) -> bool:
    conn = get_conn()
    sets = []
    params: list[Any] = []
    for k, v in updates.items():
        if k in ("status", "title", "notes") and v is not None:
            sets.append(f"{k}=?")
            params.append(v)
    if not sets:
        return False
    params.append(event_id)
    conn.execute(f"UPDATE calendar_events SET {', '.join(sets)} WHERE event_id=?", params)
    conn.commit()
    _append_log("event_update", {"event_id": event_id, **updates})
    return True


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------

def contribute_knowledge(
    contributor_id: str, category: str, content: str,
    embedding: list[float] | None = None,
) -> str:
    conn = get_conn()
    ts = _now_iso()
    kid = _short_hash(contributor_id, content[:50], ts)
    conn.execute(
        "INSERT INTO knowledge (id, contributor_id, category, content, embedding, ts) VALUES (?,?,?,?,?,?)",
        (kid, contributor_id, category, content,
         json.dumps(embedding) if embedding else None, ts),
    )
    conn.commit()
    _append_log("knowledge_contribute", {"id": kid, "contributor": contributor_id})
    return kid


def query_knowledge(query_text: str, category: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Simple text search fallback; vector search added when embedder is available."""
    conn = get_conn()
    q = "SELECT * FROM knowledge WHERE content LIKE ?"
    params: list[Any] = [f"%{query_text}%"]
    if category:
        q += " AND category=?"
        params.append(category)
    q += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d.pop("embedding", None)
        result.append(d)
    return result


def recent_knowledge(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM knowledge ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d.pop("embedding", None)
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------

def create_proposal(
    proposer_id: str, prop_type: str, title: str,
    description: str, payload: dict[str, Any],
) -> str:
    conn = get_conn()
    ts = _now_iso()
    pid = _short_hash(proposer_id, title, ts)
    conn.execute(
        """INSERT INTO governance_proposals
           (proposal_id, proposer_id, type, title, description, payload, status, votes, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (pid, proposer_id, prop_type, title, description, json.dumps(payload), "open", "{}", ts),
    )
    conn.commit()
    _append_log("proposal_create", {"proposal_id": pid, "title": title})
    return pid


def list_proposals(status: str | None = None, prop_type: str | None = None) -> list[dict[str, Any]]:
    conn = get_conn()
    q = "SELECT * FROM governance_proposals WHERE 1=1"
    params: list[Any] = []
    if status:
        q += " AND status=?"
        params.append(status)
    if prop_type:
        q += " AND type=?"
        params.append(prop_type)
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.get("payload") or "{}")
        d["votes"] = json.loads(d.get("votes") or "{}")
        result.append(d)
    return result


def get_proposal(proposal_id: str) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM governance_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d.get("payload") or "{}")
    d["votes"] = json.loads(d.get("votes") or "{}")
    return d


def vote_proposal(proposal_id: str, voter_id: str, vote: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT votes, status FROM governance_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if not row or row["status"] != "open":
        return False
    votes = json.loads(row["votes"] or "{}")
    votes[voter_id] = vote
    conn.execute(
        "UPDATE governance_proposals SET votes=? WHERE proposal_id=?",
        (json.dumps(votes), proposal_id),
    )
    conn.commit()
    _append_log("proposal_vote", {"proposal_id": proposal_id, "voter": voter_id, "vote": vote})

    # Check if we should auto-resolve (simple majority of active orchestrators)
    approvals = sum(1 for v in votes.values() if v == "approve")
    rejections = sum(1 for v in votes.values() if v == "reject")
    total = len(votes)
    if total >= 1 and approvals > total / 2:
        conn.execute(
            "UPDATE governance_proposals SET status='approved', resolved_at=? WHERE proposal_id=?",
            (_now_iso(), proposal_id),
        )
        conn.commit()
    elif total >= 1 and rejections > total / 2:
        conn.execute(
            "UPDATE governance_proposals SET status='rejected', resolved_at=? WHERE proposal_id=?",
            (_now_iso(), proposal_id),
        )
        conn.commit()
    return True


def apply_proposal(proposal_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT status FROM governance_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if not row or row["status"] != "approved":
        return False
    conn.execute(
        "UPDATE governance_proposals SET status='applied', resolved_at=? WHERE proposal_id=?",
        (_now_iso(), proposal_id),
    )
    conn.commit()
    _append_log("proposal_apply", {"proposal_id": proposal_id})
    return True


# ---------------------------------------------------------------------------
# Coaching
# ---------------------------------------------------------------------------

def create_directive(
    from_orchestrator: str, to_agent: str, directive: str, priority: str = "medium",
) -> str:
    conn = get_conn()
    ts = _now_iso()
    did = _short_hash(from_orchestrator, to_agent, ts)
    conn.execute(
        "INSERT INTO coaching_directives (id, from_orchestrator, to_agent, directive, priority, ts) VALUES (?,?,?,?,?,?)",
        (did, from_orchestrator, to_agent, directive, priority, ts),
    )
    conn.commit()
    _append_log("coaching_create", {"id": did, "to_agent": to_agent})
    return did


def get_directives(agent_id: str, only_pending: bool = True) -> list[dict[str, Any]]:
    conn = get_conn()
    if only_pending:
        rows = conn.execute(
            "SELECT * FROM coaching_directives WHERE to_agent=? AND acknowledged=0 ORDER BY ts",
            (agent_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM coaching_directives WHERE to_agent=? ORDER BY ts DESC LIMIT 50",
            (agent_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_directive(agent_id: str, directive_id: str | None = None) -> int:
    conn = get_conn()
    if directive_id:
        conn.execute(
            "UPDATE coaching_directives SET acknowledged=1 WHERE id=? AND to_agent=?",
            (directive_id, agent_id),
        )
    else:
        conn.execute(
            "UPDATE coaching_directives SET acknowledged=1 WHERE to_agent=? AND acknowledged=0",
            (agent_id,),
        )
    conn.commit()
    return conn.total_changes
