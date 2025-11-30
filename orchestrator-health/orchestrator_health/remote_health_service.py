"""Expose local Docker service health over HTTP for remote monitoring and power control."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Health", version="1.0.0")
monitor = ServiceMonitor()
docker_client = monitor.docker_client

POWER_STATE_FILE = Path(os.environ.get("POWER_STATE_FILE", "/var/lib/vtuber/power-state/power_state.json"))
POWER_ALLOWED_IPS = [
    addr.strip()
    for addr in (os.environ.get("POWER_ALLOWED_IPS", "3.150.172.153").split(","))
    if addr.strip()
]
POWER_GAME_SERVICE = os.environ.get("POWER_GAME_SERVICE", "unreal-game")
POWER_GAME_CONTAINER = os.environ.get("POWER_GAME_CONTAINER", "vtuber-unreal-game")
POWER_RUNNER_SERVICE = os.environ.get("POWER_RUNNER_SERVICE", "vtuber-script-runner")
POWER_RUNNER_CONTAINER = os.environ.get("POWER_RUNNER_CONTAINER", "")
POWER_PROJECT_NAME = os.environ.get("POWER_PROJECT_NAME") or os.environ.get("COMPOSE_PROJECT_NAME", "")
POWER_RESTART_RUNNER_ON_WAKE = os.environ.get("POWER_RESTART_RUNNER_ON_WAKE", "1") != "0"
POWER_STOP_RUNNER_ON_SLEEP = os.environ.get("POWER_STOP_RUNNER_ON_SLEEP", "1") != "0"


class PowerState(BaseModel):
    state: Literal["awake", "sleeping"] = Field(default="awake")
    reason: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PowerRequest(BaseModel):
    action: Literal["sleep", "wake"]
    reason: Optional[str] = None


def _require_auth(request: Request) -> None:
    if not POWER_ALLOWED_IPS:
        return
    client_ip = request.client.host if request.client else None
    if client_ip not in POWER_ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="client address not allowed")


def _read_power_state() -> PowerState:
    if not POWER_STATE_FILE.exists():
        return PowerState()
    try:
        payload = PowerState.model_validate_json(POWER_STATE_FILE.read_bytes())
        return payload
    except Exception:  # noqa: BLE001 - fallback to sane default
        logger.warning("Failed to parse power state file %s; defaulting to awake", POWER_STATE_FILE)
        return PowerState()


def _write_power_state(state: Literal["awake", "sleeping"], reason: Optional[str]) -> PowerState:
    POWER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = PowerState(state=state, reason=reason, updated_at=datetime.now(timezone.utc))
    POWER_STATE_FILE.write_text(payload.model_dump_json())
    return payload


def _find_container(
    service_name: str,
    explicit_name: str | None = None,
) -> Optional[Any]:
    filters = {"label": [f"com.docker.compose.service={service_name}"]}
    if POWER_PROJECT_NAME:
        filters["label"].append(f"com.docker.compose.project={POWER_PROJECT_NAME}")
    containers = docker_client.containers.list(all=True, filters=filters)
    if containers:
        return containers[0]
    if explicit_name:
        try:
            return docker_client.containers.get(explicit_name)
        except Exception:  # noqa: BLE001
            return None
    return None


def _stop_container(container_name: str, service_name: str, timeout: int = 10) -> str:
    container = _find_container(service_name, container_name)
    if container is None:
        return "missing"
    try:
        if container.status == "running":
            container.stop(timeout=timeout)
            container.reload()
        return container.status
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to stop container %s (%s): %s", container_name, service_name, exc)
        raise HTTPException(status_code=500, detail=f"failed to stop {container_name}: {exc}")


def _start_container(container_name: str, service_name: str, timeout: int = 10) -> str:
    container = _find_container(service_name, container_name)
    if container is None:
        raise HTTPException(status_code=404, detail=f"{container_name} container not found")
    try:
        if container.status != "running":
            container.start()
            container.reload()
        return container.status
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to start container %s (%s): %s", container_name, service_name, exc)
        raise HTTPException(status_code=500, detail=f"failed to start {container_name}: {exc}")


def _wait_for_running(container_name: str, service_name: str, timeout_seconds: int = 30, interval: float = 2.0) -> str:
    deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        container = _find_container(service_name, container_name)
        if container is None:
            raise HTTPException(status_code=404, detail=f"{container_name} container not found")
        container.reload()
        if container.status == "running":
            health = container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
            return f"running ({health})"
        try:
            import time

            time.sleep(interval)
        except Exception:  # pragma: no cover - defensive
            break
    raise HTTPException(status_code=504, detail=f"{container_name} did not reach running state in time")


def _restart_runner_if_present() -> str:
    runner = _find_container(POWER_RUNNER_SERVICE, POWER_RUNNER_CONTAINER or None)
    if runner is None:
        logger.info("Runner container for service %s not found; skipping restart", POWER_RUNNER_SERVICE)
        return "missing"
    try:
        runner.restart(timeout=10)
        runner.reload()
        return runner.status
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to restart runner container (%s): %s", runner.name, exc)
        raise HTTPException(status_code=500, detail=f"failed to restart runner: {exc}")


@app.get("/health")
def read_health() -> dict:
    try:
        return monitor.check_services()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Remote health check failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/power", response_model=PowerState)
def read_power_state() -> PowerState:
    """Return the current power/sleep state."""
    return _read_power_state()


@app.post("/power", response_model=PowerState)
def change_power_state(payload: PowerRequest, request: Request) -> PowerState:
    """Put the game into sleep or wake it up."""
    _require_auth(request)
    action = payload.action

    if action == "sleep":
        state = _write_power_state("sleeping", payload.reason)
        runner_status = "skipped"
        if POWER_STOP_RUNNER_ON_SLEEP:
            runner_status = _stop_container(POWER_RUNNER_CONTAINER or "vtuber-script-runner", POWER_RUNNER_SERVICE)
        game_status = _stop_container(POWER_GAME_CONTAINER, POWER_GAME_SERVICE)
        logger.info("Sleep requested; game=%s runner=%s", game_status, runner_status)
        return state

    # wake
    state = _write_power_state("awake", payload.reason)
    game_status = _start_container(POWER_GAME_CONTAINER, POWER_GAME_SERVICE)
    logger.info("Wake requested; game=%s", game_status)
    _wait_for_running(POWER_GAME_CONTAINER, POWER_GAME_SERVICE)
    if POWER_RESTART_RUNNER_ON_WAKE:
        _restart_runner_if_present()
    return state


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ORCHESTRATOR_HEALTH_PORT", "9090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
