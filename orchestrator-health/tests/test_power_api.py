import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def power_app(monkeypatch, tmp_path):
    # Clear env to defaults for predictable tests
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    app = svc.app
    return app, svc


def test_allowed_ips_fallbacks_to_vtuber(monkeypatch):
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1,2.2.2.2")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["1.1.1.1", "2.2.2.2"]


def test_allowed_ips_uses_primary_if_set(monkeypatch):
    monkeypatch.setenv("POWER_ALLOWED_IPS", "3.3.3.3")
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["3.3.3.3"]


def test_allowed_ips_empty_primary_falls_back_to_vtuber(monkeypatch):
    monkeypatch.setenv("POWER_ALLOWED_IPS", "")
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["1.1.1.1"]


def test_power_state_roundtrip(power_app):
    app, svc = power_app
    client = TestClient(app)
    # no auth enforcement when allowlist empty
    resp = client.post("/power", json={"action": "sleep", "reason": "pytest"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "sleeping"
    resp = client.get("/power")
    assert resp.status_code == 200
    assert resp.json()["state"] == "sleeping"


def test_ip_allowlist_supports_cidrs(power_app):
    _app, svc = power_app
    assert svc._ip_in_allowlist("1.1.1.1", ["1.1.1.1"])
    assert svc._ip_in_allowlist("1.1.1.1", ["1.1.1.0/24"])
    assert not svc._ip_in_allowlist("2.2.2.2", ["1.1.1.0/24"])


def test_allowed_ips_file_overrides_env(monkeypatch, tmp_path):
    allow_file = tmp_path / "allowed.txt"
    allow_file.write_text("10.0.0.0/8\n")
    monkeypatch.setenv("POWER_ALLOWED_IPS_FILE", str(allow_file))
    monkeypatch.setenv("POWER_ALLOWED_IPS", "1.1.1.1")

    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc._get_power_allowed_ips() == ["10.0.0.0/8"]


def test_wake_with_awake_seconds_sets_awake_until(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_wake_all_containers", lambda *args, **kwargs: {})
    scheduled: dict[str, object] = {}

    def fake_schedule(seconds: int, reason: str) -> None:
        scheduled["seconds"] = seconds
        scheduled["reason"] = reason

    monkeypatch.setattr(svc, "_schedule_auto_sleep", fake_schedule)

    resp = client.post("/power", json={"action": "wake", "awake_seconds": 10, "reason": "pytest"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "awake"
    assert data["awake_until"] is not None
    assert scheduled["seconds"] == 10
