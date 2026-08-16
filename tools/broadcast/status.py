#!/usr/bin/env python3
"""Render a sanitized broadcast status snapshot for the operator CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from broadcast_bridge import SecretRedactor, validate_destination


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_destination(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _clean_text(value: Any, redactor: SecretRedactor) -> str | None:
    if value is None:
        return None
    cleaned = redactor(value).replace("\r", " ").replace("\n", " ").strip()
    return cleaned[:500] if cleaned else None


def build_snapshot(
    config_path: Path,
    state_path: Path,
    destination_path: Path,
    container_status: str,
    container_health: str,
) -> dict[str, Any]:
    config = _read_json(config_path)
    state = _read_json(state_path)
    enabled = config.get("enabled") is True
    mode = str(config.get("mode") or "rtmp").strip().lower()
    if mode not in {"rtmp", "test"}:
        mode = "invalid"

    destination = _read_destination(destination_path)
    redactor = SecretRedactor(destination)
    if mode == "test":
        destination_configured = True
    else:
        try:
            validate_destination(destination)
        except ValueError:
            destination_configured = False
        else:
            destination_configured = True

    bridge: dict[str, Any] = {}
    for key in ("status", "started_at", "updated_at", "heartbeat_at", "streamer_id"):
        cleaned = _clean_text(state.get(key), redactor)
        if cleaned is not None:
            bridge[key] = cleaned
    for key in ("attempts", "retry_in_seconds"):
        value = state.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bridge[key] = value
    if isinstance(state.get("connected"), bool):
        bridge["connected"] = state["connected"]
    last_error = _clean_text(state.get("last_error"), redactor)
    if last_error is not None:
        bridge["last_error"] = last_error

    return {
        "enabled": enabled,
        "mode": mode,
        "destination_configured": destination_configured,
        "container": {
            "name": "vtuber-broadcast-bridge",
            "status": container_status or "unknown",
            "health": container_health or "none",
        },
        "bridge": bridge,
    }


def print_human(snapshot: dict[str, Any]) -> None:
    enabled = snapshot["enabled"]
    mode = snapshot["mode"]
    destination = snapshot["destination_configured"]
    container = snapshot["container"]
    bridge = snapshot["bridge"]

    print(f"Broadcast:   {'enabled' if enabled else 'disabled'}")
    print(f"Mode:        {mode}")
    if mode == "test":
        print("Destination: fake sink (no external account)")
    else:
        print(f"Destination: {'configured (redacted)' if destination else 'not configured'}")
    print(f"Container:   {container['status']} (health={container['health']})")
    if bridge:
        print(f"Bridge:      {bridge.get('status', 'unknown')}")
        if "connected" in bridge:
            print(f"Connected:   {'yes' if bridge['connected'] else 'no'}")
        if "attempts" in bridge:
            print(f"Attempts:    {bridge['attempts']}")
        if bridge.get("heartbeat_at"):
            print(f"Heartbeat:   {bridge['heartbeat_at']}")
        if bridge.get("retry_in_seconds") is not None:
            print(f"Retry in:    {bridge['retry_in_seconds']}s")
        if bridge.get("last_error"):
            print(f"Last error:  {bridge['last_error']}")


def is_healthy(snapshot: dict[str, Any]) -> bool:
    if not snapshot["enabled"]:
        # Disabled is a normal, intentionally inactive state.
        return True
    if snapshot["mode"] not in {"rtmp", "test"} or not snapshot["destination_configured"]:
        return False
    container = snapshot["container"]
    if container["status"] != "running" or container["health"] == "unhealthy":
        return False
    return snapshot["bridge"].get("status") != "failed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--destination-file", required=True)
    parser.add_argument("--container-status", default="unknown")
    parser.add_argument("--container-health", default="none")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    snapshot = build_snapshot(
        Path(args.config),
        Path(args.state),
        Path(args.destination_file),
        args.container_status,
        args.container_health,
    )
    if args.json:
        print(json.dumps(snapshot, sort_keys=True))
    else:
        print_human(snapshot)
    return 0 if is_healthy(snapshot) else 1


if __name__ == "__main__":
    sys.exit(main())
