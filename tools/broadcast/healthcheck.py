#!/usr/bin/env python3
"""Container healthcheck for the broadcast supervisor's sanitized state file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", required=True)
    parser.add_argument(
        "--max-age-seconds",
        type=float,
        default=float(os.environ.get("BROADCAST_HEALTH_MAX_AGE_SECONDS", "45")),
    )
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return 1

    if data.get("status") not in {"starting", "connecting", "streaming", "retrying"}:
        return 1
    heartbeat = _parse_time(data.get("heartbeat_at"))
    if heartbeat is None:
        return 1
    age = (datetime.now(timezone.utc) - heartbeat).total_seconds()
    return 0 if -5 <= age <= max(1.0, args.max_age_seconds) else 1


if __name__ == "__main__":
    sys.exit(main())
