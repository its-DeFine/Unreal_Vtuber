# 📝 SCB v2 Redesign – Request for Comments (RFC)

*Version: 0.1 – Draft*
*Author: Core Engineering Team*
*Created: 2025-07-13*

---

## 1. Purpose

The goal of this RFC is to specify **SCB v2** – a dual-layer Shared Cognitive Blackboard that fulfils the Phase-3 requirements defined in `docs/TESTING_METHODOLOGY.md`:

* Team-local SCB slices (trader / educator / streamer)
* A global SCB slice readable by all systems
* Hard character budget per slice (default `SCB_MAX_CHARS = 1000`)
* Isolation guarantees (teams cannot read/write other teams’ SCBs)
* Minimal, well-defined API used consistently across S1, S2 and external services

This document describes the architecture, Redis schema, API surface, migration strategy and testing plan.  Feedback is welcome before implementation proceeds.

---

## 2. Background & Problems with SCB v1

| Issue | Impact |
|-------|--------|
| Single rolling log (`scb_store`) lacks isolation | S2 teams can accidentally overwrite each other’s context |
| No char-budget enforcement | SCB overflow causes context truncation in unpredictable ways |
| Multiple HTTP entry points (Flask, UI proxy) | Difficult to audit / secure |
| S1 writes full messages | Bloats SCB and leaks private data |

---

## 3. Design Overview

```
                ┌──────────────┐           Redis Keys
   S2 Teams ───▶│  SCB Client  │─┐       ┌───────────────────────────────┐
                └──────────────┘ │       │ scb:team:<team>  →   slice    │
                                  │       │ scb:global       →   slice    │
                ┌──────────────┐ │◀──────┤ …                         …   │
  S1 System ───▶│  SCB Client  │ │        └───────────────────────────────┘
                └──────────────┘ │
                                  │ REST (optional)
                ┌──────────────┐ │
   External ───▶│ SCB Gateway  │─┘
                └──────────────┘
```

* **SCB Client (v2)** – thin Python lib inside both S1 & S2 containers; talks to Redis.
* **SCB Gateway** – FastAPI micro-service exposing read/write endpoints for dashboards & tooling.  Uses the same client internally.
* **Redis schema** – each slice stored as a single *JSON string* under the key; clients enforce char limit on write.

---

## 4. Detailed Specification

### 4.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_SCB_URL` | `redis://redis:6379/0` | Redis connection URL |
| `SCB_MAX_CHARS` | `1000` | Hard limit per slice (UTF-8 characters) |

### 4.2 Redis Key Layout

```
scb:team:<team_name>   # e.g. scb:team:trader
scb:global             # global slice
```

Each value stores a **JSON object**:

```json
{
  "summary": "string",
  "window": [ { "t": 1720923127, "type": "event", "actor": "agent", "text": "..." }, ... ]
}
```

*Size enforcement*: prior to `SET`, the client measures `len(value.encode('utf-8'))` and trims the `window` oldest entries until within budget.

### 4.3 Client API

```python
class SCBv2Client:
    def set_slice(self, key: str, obj: dict) -> None
    def get_slice(self, key: str) -> dict
    def append_event(self, key: str, event: dict) -> None  # handles trimming
```

### 4.4 Access Control Matrix

| Operation          | S1  | S2 (own team) | S2 (other team) | External |
|--------------------|-----|---------------|-----------------|----------|
| Read team slice    | R   | R/W           | –               | –        |
| Read global slice  | R/W | R/W           | R/W             | R        |
| Write global slice | W*  | W             | –               | –        |

`W*` = S1 writes 50-char summary only.

### 4.5 SCB Gateway Endpoints (FastAPI)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/scb/global/slice` | Read global slice (query: `tokens=`) |
| GET | `/scb/team/{team}/slice` | Read team slice |
| POST | `/scb/team/{team}/event` | Append event to team slice |
| POST | `/scb/global/summary` | Append 50-char summary (S1) |
| GET | `/health` | Health probe |

Auth: optional API key header `X-SCB-Key` (same mechanism as v1).

---

## 5. Migration Strategy

1. **Ship `SCBv2Client`** in a backwards-compatible way (no code removal).  v2 lives in `autogen_agent/clients/scb_v2_client.py`.
2. **Refactor TeamSCBManager** to call v2 client.
3. **Implement SCB Gateway (FastAPI)**; leave old Flask routes returning `410 Gone`.
4. **Update UI proxy** to hit new endpoints.
5. **Delete legacy routes & stores** after two successful releases.

---

## 6. Testing Plan

* Unit tests: `tests/scb/` covering size trimming, isolation, ACL.
* Integration: `tests/integration/test_scb_flow.py` verifying S1+S2 behaviour.
* Performance: P95 < 5 ms for `get_slice` @ 200 rps (localhost).

---

## 7. Open Questions

1. Do we need per-team char limits or one global budget?
2. Should we compress slices in Redis to save RAM? (e.g. LZ4)
3. Do external tools need write access to team slices?

Please comment inline or add suggestions below.

---

## 8. Changelog

* **0.1** – Initial draft created. 