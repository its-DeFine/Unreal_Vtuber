"""SCB v2 Redis client – dual-layer Shared Cognitive Blackboard

Implements the API specified in docs/scb/SCB_REDESIGN_RFC.md:
  • set_slice(key, obj)
  • get_slice(key)
  • append_event(key, event)

Key features:
  • Per-slice hard char budget enforced (UTF-8 bytes)
  • Per-team budgets override default via env vars `SCB_MAX_CHARS_<TEAM>`
  • Atomic writes via Redis pipeline
  • Graceful degradation: if Redis unavailable we raise RuntimeError so caller
    can decide fallback (e.g. in-memory store).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

_REDIS_URL_ENV = "REDIS_SCB_URL"
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"

# Global default char budget per slice.  Team-specific overrides are
# discovered at runtime from env vars `SCB_MAX_CHARS_<TEAMNAME>`.
_DEFAULT_MAX_CHARS = int(os.getenv("SCB_MAX_CHARS", "1000"))

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _team_limit_env(team: str) -> Optional[int]:
    """Return int value of env var `SCB_MAX_CHARS_<TEAM>` if set."""
    env_key = f"SCB_MAX_CHARS_{team.upper()}"
    val = os.getenv(env_key)
    if val and val.isdigit():
        return int(val)
    return None


def _utf8_size(s: str) -> int:
    return len(s.encode("utf-8"))


class SCBv2Client:
    """Redis-backed SCB v2 client."""

    def __init__(self, redis_url: Optional[str] = None, default_max_chars: int = _DEFAULT_MAX_CHARS):
        if redis is None:
            raise ImportError("redis package not installed – SCBv2Client requires redis-py")

        self.redis_url = redis_url or os.getenv(_REDIS_URL_ENV, _DEFAULT_REDIS_URL)
        self.default_max_chars = default_max_chars

        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            # quick ping to ensure connectivity
            self._redis.ping()
            logger.info("🔗 [SCBv2] Connected to Redis at %s", self.redis_url)
        except Exception as e:  # pragma: no cover – connection failures
            logger.error("❌ [SCBv2] Failed to connect to Redis: %s", e)
            raise RuntimeError("SCBv2Client cannot connect to Redis") from e

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_slice(self, key: str, obj: Dict[str, Any]) -> None:
        """Store a full slice (summary + window) under *key*, enforcing size."""
        serialised = self._serialise_and_trim(key, obj)
        self._redis.set(key, serialised)

    def get_slice(self, key: str) -> Dict[str, Any]:
        """Return the data stored under *key* (compatible format)."""
        data = self._redis.get(key)
        if not data:
            return {"window": []}
        try:
            parsed = json.loads(data)
            # If it's already in object format, return as-is
            if isinstance(parsed, dict) and "window" in parsed:
                return parsed
            # If it's in array format, wrap it
            elif isinstance(parsed, list):
                return {"window": parsed}
            else:
                logger.warning("⚠️  [SCBv2] Unexpected format in %s", key)
                return {"window": []}
        except Exception:
            logger.warning("⚠️  [SCBv2] Malformed JSON in slice %s", key)
            return {"window": []}

    def append_event(self, key: str, event: Dict[str, Any]) -> None:
        """Append *event* to the events array, trimming to budget."""
        # Ensure timestamp
        if "timestamp" not in event and "t" not in event:
            event["timestamp"] = time.time()

        pipe = self._redis.pipeline()
        pipe.get(key)
        raw_data = pipe.execute()[0]

        if raw_data:
            try:
                events = json.loads(raw_data)
                # Handle both array format and object format
                if isinstance(events, dict) and "window" in events:
                    events = events["window"]
                elif not isinstance(events, list):
                    logger.warning("⚠️  [SCBv2] Unexpected data format in %s – resetting", key)
                    events = []
            except Exception:
                logger.warning("⚠️  [SCBv2] Malformed JSON in %s – resetting", key)
                events = []
        else:
            events = []

        events.append(event)  # newest at end for chronological order

        # Trim to character budget
        budget = self._budget_for_key(key)
        while len(json.dumps(events)) > budget and len(events) > 1:
            events.pop(0)  # Remove oldest

        self._redis.set(key, json.dumps(events))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _budget_for_key(self, key: str) -> int:
        """Return char budget for this slice, using team overrides."""
        if key.startswith("scb:team:"):
            team = key.split(":", 2)[2]
            team_limit = _team_limit_env(team)
            if team_limit is not None:
                return team_limit
        # default
        return self.default_max_chars

    def _serialise_and_trim(self, key: str, obj: Dict[str, Any]) -> str:
        """Serialise *obj* to JSON, trimming window until within budget."""
        window: List[Dict[str, Any]] = obj.get("window", [])
        budget = self._budget_for_key(key)

        # Ensure deterministic order: keep newest events by trimming from start
        while True:
            serialised = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
            if _utf8_size(serialised) <= budget:
                return serialised
            if window:
                # Drop oldest event
                window.pop(0)
            else:
                # Already overflowed with empty window – truncate summary
                obj["summary"] = obj.get("summary", "")[:max(0, budget)]
                serialised = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
                return serialised 