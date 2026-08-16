import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.broadcast.broadcast_bridge import SecretRedactor, StateStore, validate_destination


DESTINATION = "rtmps://stream.example.test/live/super-private-stream-key?token=also-private"


def test_validate_destination_accepts_rtmp_and_rejects_non_rtmp():
    assert validate_destination(DESTINATION) == DESTINATION
    for value in ("", "https://stream.example.test/key", "rtmp:///missing-host", "rtmp://host/key\nother"):
        try:
            validate_destination(value)
        except ValueError:
            pass
        else:  # pragma: no cover - assertion detail
            raise AssertionError(f"expected destination to be rejected: {value!r}")


def test_redactor_removes_complete_url_and_key_fragments():
    redact = SecretRedactor(DESTINATION)
    message = f"sink failed for {DESTINATION}; key=super-private-stream-key; token=also-private"
    cleaned = redact(message)
    assert "rtmps://" not in cleaned
    assert "super-private-stream-key" not in cleaned
    assert "also-private" not in cleaned
    assert "[redacted" in cleaned


def test_state_store_never_persists_destination(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path, "rtmp", SecretRedactor(DESTINATION))
    store.update("retrying", last_error=f"could not connect to {DESTINATION}", attempts=2)
    raw = path.read_text(encoding="utf-8")
    assert DESTINATION not in raw
    assert "super-private-stream-key" not in raw
    data = json.loads(raw)
    assert data["status"] == "retrying"
    assert data["attempts"] == 2
    assert "redacted" in data["last_error"]


def test_local_test_pipeline_reaches_streaming_without_external_services(tmp_path):
    pytest.importorskip("gi")
    script = Path(__file__).resolve().parents[1] / "broadcast_bridge.py"
    state = tmp_path / "state.json"
    process = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={
            **os.environ,
            "BROADCAST_MODE": "test",
            "BROADCAST_STATE_FILE": str(state),
            "GST_DEBUG": "0",
        },
    )
    try:
        deadline = time.monotonic() + 8
        payload = {}
        while time.monotonic() < deadline:
            if state.exists():
                payload = json.loads(state.read_text(encoding="utf-8"))
                if payload.get("status") == "streaming":
                    break
            if process.poll() is not None:
                break
            time.sleep(0.1)
        assert payload.get("status") == "streaming"
        assert payload.get("connected") is True
    finally:
        process.terminate()
        output, _ = process.communicate(timeout=8)
        assert DESTINATION not in output
    assert process.returncode == 0


def test_status_json_is_sanitized(tmp_path):
    config = tmp_path / "config.json"
    state = tmp_path / "state.json"
    destination = tmp_path / "rtmp-url"
    config.write_text(
        json.dumps({"enabled": True, "mode": "rtmp", "signaling_url": "ws://local:80"}),
        encoding="utf-8",
    )
    destination.write_text(DESTINATION, encoding="utf-8")
    state.write_text(
        json.dumps(
            {
                "status": "retrying",
                "connected": False,
                "attempts": 3,
                "last_error": f"provider rejected {DESTINATION}",
            }
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "status.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config),
            "--state",
            str(state),
            "--destination-file",
            str(destination),
            "--container-status",
            "running",
            "--container-health",
            "healthy",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert DESTINATION not in result.stdout
    assert "super-private-stream-key" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["destination_configured"] is True
    assert payload["container"]["status"] == "running"
    assert payload["bridge"]["status"] == "retrying"
