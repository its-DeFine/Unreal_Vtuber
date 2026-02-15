"""Agent leaderboard / KPI rankings route."""

from __future__ import annotations

from fastapi import APIRouter

from .. import db

router = APIRouter(tags=["leaderboard"])


def _compute_score(agent: dict) -> float:
    """Composite score from metrics: engagement, uptime, contributions, governance."""
    m = agent.get("metrics") or {}
    score = 0.0
    # Engagement: chat count weighted
    score += min(float(m.get("chat_count", 0)) / 100, 1.0) * 30
    # Uptime: uptime_s weighted (cap at 24 h)
    score += min(float(m.get("uptime_s", 0)) / 86400, 1.0) * 25
    # Container health: bonus for all healthy
    containers = m.get("container_health", [])
    if containers:
        healthy = sum(1 for c in containers if c.get("state") == "running")
        score += (healthy / len(containers)) * 20
    else:
        score += 10  # neutral if no data
    # Status bonus
    if agent.get("status") == "online":
        score += 15
    # Participation bonus (has capabilities)
    caps = agent.get("capabilities") or []
    score += min(len(caps), 5) * 2
    return round(score, 2)


@router.get("/leaderboard")
async def leaderboard():
    agents = db.list_agents()
    ranked = []
    for a in agents:
        ranked.append({
            "agent_id": a["agent_id"],
            "name": a["name"],
            "status": a["status"],
            "score": _compute_score(a),
            "metrics": a.get("metrics", {}),
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return {"leaderboard": ranked}
