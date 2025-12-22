"""Expose local Docker service health over HTTP for remote monitoring and power control."""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
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


def _parse_ip_list(primary_env: str, fallback_env: str | None = None, default: str = "") -> list[str]:
    raw = os.environ.get(primary_env)
    if (raw is None) and fallback_env:
        raw = os.environ.get(fallback_env)
    if raw is None:
        raw = default
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


POWER_ALLOWED_IPS = _parse_ip_list("POWER_ALLOWED_IPS", fallback_env="VTUBER_ALLOWED_ADDRESSES")
POWER_GAME_SERVICE = os.environ.get("POWER_GAME_SERVICE", "unreal-game")
POWER_GAME_CONTAINER = os.environ.get("POWER_GAME_CONTAINER", "vtuber-unreal-game")
POWER_RUNNER_SERVICE = os.environ.get("POWER_RUNNER_SERVICE", "vtuber-script-runner")
POWER_RUNNER_CONTAINER = os.environ.get("POWER_RUNNER_CONTAINER", "")
POWER_PROJECT_NAME = os.environ.get("POWER_PROJECT_NAME") or os.environ.get("COMPOSE_PROJECT_NAME", "")
POWER_SELF_CONTAINER = os.environ.get("POWER_SELF_CONTAINER", "vtuber-orchestrator-health")
POWER_SELF_SERVICE = os.environ.get("POWER_SELF_SERVICE", "orchestrator-health")
POWER_RESTART_RUNNER_ON_WAKE = os.environ.get("POWER_RESTART_RUNNER_ON_WAKE", "1") != "0"
POWER_STOP_RUNNER_ON_SLEEP = os.environ.get("POWER_STOP_RUNNER_ON_SLEEP", "1") != "0"

_AUTO_SLEEP_TIMER: threading.Timer | None = None


class PowerState(BaseModel):
    state: Literal["awake", "sleeping"] = Field(default="awake")
    reason: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    awake_until: Optional[datetime] = None


class PowerRequest(BaseModel):
    action: Literal["sleep", "wake"]
    reason: Optional[str] = None
    awake_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=60 * 60 * 24,
        description="If provided on wake, auto-sleep the stack after this many seconds.",
    )


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


def _write_power_state(
    state: Literal["awake", "sleeping"],
    reason: Optional[str],
    *,
    awake_until: Optional[datetime] = None,
) -> PowerState:
    POWER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = PowerState(state=state, reason=reason, updated_at=datetime.now(timezone.utc), awake_until=awake_until)
    POWER_STATE_FILE.write_text(payload.model_dump_json())
    return payload


def _get_self_container() -> Optional[Any]:
    for candidate in (POWER_SELF_CONTAINER, os.environ.get("HOSTNAME", "")):
        if not candidate:
            continue
        try:
            return docker_client.containers.get(candidate)
        except Exception:  # noqa: BLE001
            continue
    return None


def _detect_compose_identity() -> None:
    global POWER_PROJECT_NAME, POWER_SELF_SERVICE
    if POWER_PROJECT_NAME:
        return
    self_container = _get_self_container()
    if self_container is None:
        return
    labels = getattr(self_container, "labels", {}) or {}
    project = labels.get("com.docker.compose.project")
    service = labels.get("com.docker.compose.service")
    if project:
        POWER_PROJECT_NAME = project
    if service:
        POWER_SELF_SERVICE = service


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


def _wait_for_running(
    container_name: str,
    service_name: str,
    *,
    timeout_seconds: int = 30,
    interval: float = 2.0,
    require_healthy: bool = False,
) -> str:
    deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        container = _find_container(service_name, container_name)
        if container is None:
            raise HTTPException(status_code=404, detail=f"{container_name} container not found")
        container.reload()
        if container.status == "running":
            health_payload = container.attrs.get("State", {}).get("Health")
            health = (health_payload or {}).get("Status", "unknown")
            if require_healthy and health_payload and health != "healthy":
                try:
                    import time

                    time.sleep(interval)
                except Exception:  # pragma: no cover - defensive
                    break
                continue
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

def _cancel_auto_sleep_timer() -> None:
    global _AUTO_SLEEP_TIMER
    if _AUTO_SLEEP_TIMER is None:
        return
    try:
        _AUTO_SLEEP_TIMER.cancel()
    except Exception:  # pragma: no cover - defensive
        pass
    _AUTO_SLEEP_TIMER = None


def _auto_sleep(reason: str) -> None:
    try:
        state = _read_power_state()
        if state.state != "awake":
            return
        _write_power_state("sleeping", reason, awake_until=None)
        _sleep_all_containers(reason=reason)
    except Exception:  # pragma: no cover - background thread
        logger.exception("Auto-sleep failed")


def _schedule_auto_sleep(seconds: int, reason: str) -> None:
    global _AUTO_SLEEP_TIMER
    _cancel_auto_sleep_timer()
    if seconds <= 0:
        return
    timer = threading.Timer(seconds, _auto_sleep, kwargs={"reason": reason})
    timer.daemon = True
    timer.start()
    _AUTO_SLEEP_TIMER = timer


def _list_project_containers() -> list[Any]:
    _detect_compose_identity()
    if not POWER_PROJECT_NAME:
        return []
    return docker_client.containers.list(all=True, filters={"label": [f"com.docker.compose.project={POWER_PROJECT_NAME}"]})


def _is_self_container(container: Any) -> bool:
    try:
        if container.name == POWER_SELF_CONTAINER:
            return True
        if (container.labels or {}).get("com.docker.compose.service") == POWER_SELF_SERVICE:
            return True
        hostname = os.environ.get("HOSTNAME")
        if hostname and container.id.startswith(hostname):
            return True
    except Exception:  # pragma: no cover - defensive
        return False
    return False


def _sleep_all_containers(*, reason: str | None = None) -> dict[str, str]:
    """Stop every container in this compose project except this orchestrator-health container."""
    containers = _list_project_containers()
    if not containers:
        # Fallback: preserve legacy behavior (game + runner) when project discovery fails.
        results: dict[str, str] = {}
        if POWER_STOP_RUNNER_ON_SLEEP:
            results["runner"] = _stop_container(POWER_RUNNER_CONTAINER or "vtuber-script-runner", POWER_RUNNER_SERVICE)
        results["game"] = _stop_container(POWER_GAME_CONTAINER, POWER_GAME_SERVICE)
        return results

    start_order = [
        "turn-server",
        "unreal-signaling",
        "unreal-game",
        "vtuber-script-runner",
        "recorder-control",
        "vtuber-watchdog",
        "vtuber-auto-updater",
        "orchestrator-registration",
    ]
    rank = {svc: idx for idx, svc in enumerate(start_order)}

    def stop_key(container: Any) -> tuple[int, str]:
        service = (container.labels or {}).get("com.docker.compose.service", "")
        idx = rank.get(service)
        return (-(idx if idx is not None else -1), container.name)

    results: dict[str, str] = {}
    for container in sorted(containers, key=stop_key):
        if _is_self_container(container):
            continue
        try:
            container.reload()
            if container.status == "running":
                container.stop(timeout=10)
                container.reload()
            results[container.name] = container.status
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to stop container %s: %s", getattr(container, "name", "<unknown>"), exc)
            raise HTTPException(status_code=500, detail=f"failed to stop {getattr(container, 'name', '<unknown>')}: {exc}")
    return results


def _wake_all_containers(*, timeout_seconds: int = 90) -> dict[str, str]:
    """Start the entire stack in dependency order (except orchestrator-health)."""
    containers = _list_project_containers()
    if not containers:
        # Fallback: legacy behavior (game + runner)
        results: dict[str, str] = {}
        results["game"] = _start_container(POWER_GAME_CONTAINER, POWER_GAME_SERVICE)
        _wait_for_running(POWER_GAME_CONTAINER, POWER_GAME_SERVICE, timeout_seconds=timeout_seconds)
        if POWER_RESTART_RUNNER_ON_WAKE:
            results["runner"] = _restart_runner_if_present()
        return results

    # Known compose services in dependency order.
    services = [
        ("turn-server", "vtuber-turn-server", False),
        ("unreal-signaling", "vtuber-unreal-signaling", True),
        ("unreal-game", "vtuber-unreal-game", False),
        ("vtuber-script-runner", "vtuber-script-runner", False),
        ("recorder-control", "vtuber-recorder-control", False),
        ("vtuber-watchdog", "vtuber-watchdog", False),
        ("vtuber-auto-updater", "vtuber-auto-updater", False),
        ("orchestrator-registration", "vtuber-orchestrator-registration", False),
    ]

    results: dict[str, str] = {}
    for service_name, explicit_container, needs_healthy in services:
        if service_name == POWER_SELF_SERVICE:
            continue
        container = _find_container(service_name, explicit_container)
        if container is None:
            continue
        if _is_self_container(container):
            continue
        container.reload()
        if container.status != "running":
            container.start()
            container.reload()
        results[container.name] = container.status
        if service_name in ("turn-server", "unreal-signaling", "unreal-game"):
            _wait_for_running(
                explicit_container,
                service_name,
                timeout_seconds=timeout_seconds,
                require_healthy=needs_healthy,
            )

    # Start any remaining stopped containers in this project (best-effort).
    for container in _list_project_containers():
        if _is_self_container(container):
            continue
        service = (container.labels or {}).get("com.docker.compose.service", "")
        if service in {svc for svc, _, _ in services}:
            continue
        container.reload()
        if container.status != "running":
            container.start()
            container.reload()
        results[container.name] = container.status

    return results


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
        _cancel_auto_sleep_timer()
        state = _write_power_state("sleeping", payload.reason, awake_until=None)
        statuses = _sleep_all_containers(reason=payload.reason)
        logger.info("Sleep requested; stopped=%s", statuses)
        return state

    # wake
    _cancel_auto_sleep_timer()
    awake_until: Optional[datetime] = None
    if payload.awake_seconds:
        awake_until = datetime.now(timezone.utc) + timedelta(seconds=payload.awake_seconds)
    state = _write_power_state("awake", payload.reason, awake_until=awake_until)
    statuses = _wake_all_containers(timeout_seconds=120)
    logger.info("Wake requested; started=%s", statuses)
    if payload.awake_seconds:
        _schedule_auto_sleep(payload.awake_seconds, reason="auto-sleep after wake TTL")
    return state


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ORCHESTRATOR_HEALTH_PORT", "9090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
