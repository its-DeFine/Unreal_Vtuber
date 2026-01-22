"""Expose local Docker service health over HTTP for remote monitoring and power control."""
from __future__ import annotations

import logging
import os
import ipaddress
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Health", version="1.0.0")
monitor = ServiceMonitor()
docker_client = monitor.docker_client

POWER_STATE_FILE = Path(os.environ.get("POWER_STATE_FILE", "/var/lib/vtuber/power-state/power_state.json"))


def _parse_ip_list(primary_env: str, fallback_env: str | None = None, default: str = "") -> list[str]:
    raw = os.environ.get(primary_env)
    if raw is not None and not raw.strip():
        raw = None
    if (raw is None) and fallback_env:
        raw = os.environ.get(fallback_env)
        if raw is not None and not raw.strip():
            raw = None
    if raw is None:
        raw = default
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def _parse_csv(primary_env: str, default: str = "") -> list[str]:
    raw = os.environ.get(primary_env)
    if raw is None:
        raw = default
    return [token.strip() for token in raw.split(",") if token.strip()]


POWER_ALLOWED_IPS = _parse_ip_list("POWER_ALLOWED_IPS", fallback_env="VTUBER_ALLOWED_ADDRESSES")
POWER_ALLOWED_IPS_FILE_RAW = os.environ.get("POWER_ALLOWED_IPS_FILE", "").strip()
POWER_ALLOWED_IPS_FILE = Path(POWER_ALLOWED_IPS_FILE_RAW) if POWER_ALLOWED_IPS_FILE_RAW else None
POWER_KEEP_RUNNING_SERVICES = set(_parse_csv("POWER_KEEP_RUNNING_SERVICES"))
POWER_GAME_SERVICE = os.environ.get("POWER_GAME_SERVICE", "unreal-game")
POWER_GAME_CONTAINER = os.environ.get("POWER_GAME_CONTAINER", "vtuber-unreal-game")
POWER_RUNNER_SERVICE = os.environ.get("POWER_RUNNER_SERVICE", "vtuber-script-runner")
POWER_RUNNER_CONTAINER = os.environ.get("POWER_RUNNER_CONTAINER", "")
POWER_PROJECT_NAME = os.environ.get("POWER_PROJECT_NAME") or os.environ.get("COMPOSE_PROJECT_NAME", "")
POWER_SELF_CONTAINER = os.environ.get("POWER_SELF_CONTAINER", "vtuber-orchestrator-health")
POWER_SELF_SERVICE = os.environ.get("POWER_SELF_SERVICE", "orchestrator-health")
POWER_RESTART_RUNNER_ON_WAKE = os.environ.get("POWER_RESTART_RUNNER_ON_WAKE", "1") != "0"
POWER_STOP_RUNNER_ON_SLEEP = os.environ.get("POWER_STOP_RUNNER_ON_SLEEP", "1") != "0"
POWER_ALLOWED_PROJECT_PREFIXES = _parse_csv("POWER_ALLOWED_PROJECT_PREFIXES", default="vtuber-")

_AUTO_SLEEP_TIMER: threading.Timer | None = None
_AUTO_SLEEP_TIMERS_BY_PROJECT: dict[str, threading.Timer] = {}
_PROJECT_AWAKE_UNTIL: dict[str, datetime] = {}
_PROJECT_LAST_REASON: dict[str, str] = {}

_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class PowerState(BaseModel):
    state: Literal["awake", "sleeping"] = Field(default="awake")
    reason: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    awake_until: Optional[datetime] = None
    project: Optional[str] = Field(default=None, description="Compose project when power control is scoped.")


class PowerRequest(BaseModel):
    action: Literal["sleep", "wake"]
    reason: Optional[str] = None
    awake_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=60 * 60 * 24,
        description="If provided on wake, auto-sleep the stack after this many seconds.",
    )

class ClusterDeployRequest(BaseModel):
    avatar_id: str = Field(min_length=1, description="Matchmaker streamer id for this instance (ex: arthur-0).")
    slot: int = Field(ge=0, le=255, description="Port slot (ports are base+slot, subnet is 172.30.<slot>.0/24).")
    gpu: Optional[str] = Field(default=None, description="NVIDIA_VISIBLE_DEVICES value (ex: 0,1,all).")
    recreate: bool = Field(default=False, description="Pass --force-recreate to docker compose up.")


class ClusterDownRequest(BaseModel):
    avatar_id: Optional[str] = Field(default=None, description="Matchmaker streamer id (ex: arthur-0).")
    project: Optional[str] = Field(default=None, description="Compose project name (ex: vtuber-arthur-0).")

    @model_validator(mode="after")
    def _validate_target(self) -> "ClusterDownRequest":
        if not (self.avatar_id or self.project):
            raise ValueError("avatar_id or project is required")
        return self


def _env_truthy(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _require_cluster_control_enabled() -> None:
    if not _env_truthy("EXPERIMENTAL_REMOTE_CLUSTER_CONTROL", default=False):
        raise HTTPException(status_code=404, detail="cluster control not enabled")


def _require_auth(request: Request) -> None:
    allowed = _get_power_allowed_ips()
    if not allowed:
        return
    client_ip = request.client.host if request.client else None
    if (not client_ip) or (not _ip_in_allowlist(client_ip, allowed)):
        raise HTTPException(status_code=403, detail="client address not allowed")


def _get_power_allowed_ips() -> list[str]:
    if POWER_ALLOWED_IPS_FILE is None:
        return POWER_ALLOWED_IPS
    try:
        raw = POWER_ALLOWED_IPS_FILE.read_text().strip()
    except FileNotFoundError:
        return POWER_ALLOWED_IPS
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read POWER_ALLOWED_IPS_FILE=%s: %s", POWER_ALLOWED_IPS_FILE, exc)
        return POWER_ALLOWED_IPS

    entries = [addr.strip() for addr in raw.split(",") if addr.strip()]
    return entries or POWER_ALLOWED_IPS


def _ip_in_allowlist(client_ip: str, allowlist: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for token in allowlist:
        try:
            network = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if ip in network:
            return True
    return False


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


def _validate_power_project(project: str) -> str:
    project = project.strip()
    if not project:
        raise HTTPException(status_code=400, detail="project is required")
    if not _PROJECT_NAME_RE.match(project):
        raise HTTPException(status_code=400, detail="invalid project name")
    if POWER_ALLOWED_PROJECT_PREFIXES and not any(project.startswith(prefix) for prefix in POWER_ALLOWED_PROJECT_PREFIXES):
        raise HTTPException(status_code=403, detail="project not allowed")
    return project


def _slugify_avatar_id(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9_.-]+", "-", s)
    s = s.strip("-_.")
    return s


def _cluster_ports(slot: int) -> dict[str, int]:
    return {
        "signaling": 8080 + slot,
        "runner": 9877 + slot,
        "recorder": 8889 + slot,
        "game_tcp": 7777 + slot,
    }


def _cluster_subnet(slot: int) -> str:
    return f"172.30.{slot}.0/24"


def _cluster_gateway(slot: int) -> str:
    return f"172.30.{slot}.1"


def _cluster_allowlist_csv(gateway: str) -> str:
    allow_csv = (os.environ.get("VTUBER_ALLOWED_ADDRESSES") or "").strip()
    edge_local = (os.environ.get("EDGE_LOCAL_ALLOWLIST") or "").strip()

    local_allow = ["127.0.0.1", "::1", "172.17.0.1", "172.18.0.1"]

    items: list[str] = []
    if allow_csv:
        items.extend([token.strip() for token in allow_csv.split(",") if token.strip()])
    else:
        items.extend(local_allow)

    for token in local_allow:
        if token not in items:
            items.append(token)

    if edge_local:
        for token in [part.strip() for part in edge_local.split(",") if part.strip()]:
            if token not in items:
                items.append(token)

    gateway = gateway.strip()
    if gateway and gateway not in items:
        items.append(gateway)

    return ",".join(items)


def _docker_port_conflicts(want_ports: set[int], *, ignore_project: str | None = None) -> dict[int, str]:
    conflicts: dict[int, str] = {}
    for container in docker_client.containers.list(all=True):
        try:
            container.reload()
            if ignore_project:
                labels = (container.attrs or {}).get("Config", {}).get("Labels") or {}
                project = (labels.get("com.docker.compose.project") or "").strip()
                if project and project == ignore_project:
                    continue
            ports = (container.attrs or {}).get("NetworkSettings", {}).get("Ports") or {}
        except Exception:  # noqa: BLE001
            continue

        for bindings in ports.values():
            if not bindings:
                continue
            for binding in bindings:
                host_port_raw = (binding or {}).get("HostPort")
                try:
                    host_port = int(host_port_raw)
                except Exception:
                    continue
                if host_port in want_ports and host_port not in conflicts:
                    conflicts[host_port] = getattr(container, "name", "<unknown>")
    return conflicts


def _cluster_executor_container() -> Any:
    name = (os.environ.get("CLUSTER_EXECUTOR_CONTAINER") or "vtuber-orchestrator-edge-rotator").strip()
    try:
        return docker_client.containers.get(name)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cluster executor container not found (%s): %s", name, exc)
        raise HTTPException(status_code=503, detail=f"cluster executor not running: {name}") from exc


def _cluster_compose_instance(*, project: str, args: list[str], env: dict[str, str]) -> dict[str, Any]:
    project_dir = (os.environ.get("ORCHESTRATOR_PROJECT_DIR") or "/home/ubuntu/Unreal_Vtuber").strip()
    instance_compose = (os.environ.get("CLUSTER_INSTANCE_COMPOSE_FILE") or "docker-compose.unreal.instance.yml").strip()
    if not project_dir.startswith("/"):
        raise HTTPException(status_code=500, detail="invalid ORCHESTRATOR_PROJECT_DIR (must be absolute)")

    cmd = [
        "docker",
        "compose",
        "-p",
        project,
        "--project-directory",
        project_dir,
        "--env-file",
        f"{project_dir}/.env",
        "-f",
        f"{project_dir}/{instance_compose}",
        *args,
    ]

    executor = _cluster_executor_container()
    try:
        result = executor.exec_run(cmd, environment=env, demux=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cluster compose exec failed (project=%s): %s", project, exc)
        raise HTTPException(status_code=500, detail=f"cluster compose exec failed: {exc}") from exc

    stdout_b, stderr_b = result.output or (b"", b"")
    stdout = (stdout_b or b"").decode("utf-8", errors="replace")
    stderr = (stderr_b or b"").decode("utf-8", errors="replace")
    exit_code = getattr(result, "exit_code", 1)
    return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr, "cmd": cmd}


def _find_container(
    service_name: str,
    explicit_name: str | None = None,
    *,
    project_name: str | None = None,
) -> Optional[Any]:
    filters = {"label": [f"com.docker.compose.service={service_name}"]}
    project = project_name or POWER_PROJECT_NAME
    if project:
        filters["label"].append(f"com.docker.compose.project={project}")
    containers = docker_client.containers.list(all=True, filters=filters)
    if containers:
        return containers[0]
    if explicit_name:
        try:
            return docker_client.containers.get(explicit_name)
        except Exception:  # noqa: BLE001
            return None
    return None


def _stop_container(container_name: str, service_name: str, timeout: int = 10, *, project_name: str | None = None) -> str:
    container = _find_container(service_name, container_name, project_name=project_name)
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


def _start_container(container_name: str, service_name: str, timeout: int = 10, *, project_name: str | None = None) -> str:
    container = _find_container(service_name, container_name, project_name=project_name)
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
    project_name: str | None = None,
) -> str:
    deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        container = _find_container(service_name, container_name, project_name=project_name)
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


def _list_project_containers(project_name: str | None = None) -> list[Any]:
    _detect_compose_identity()
    project = project_name or POWER_PROJECT_NAME
    if not project:
        return []
    return docker_client.containers.list(all=True, filters={"label": [f"com.docker.compose.project={project}"]})


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


def _should_keep_running(container: Any) -> bool:
    if not POWER_KEEP_RUNNING_SERVICES:
        return False
    try:
        if container.name in POWER_KEEP_RUNNING_SERVICES:
            return True
        service = (container.labels or {}).get("com.docker.compose.service", "")
        if service and service in POWER_KEEP_RUNNING_SERVICES:
            return True
    except Exception:  # pragma: no cover - defensive
        return False
    return False


def _sleep_all_containers(*, reason: str | None = None, project_name: str | None = None) -> dict[str, str]:
    """Stop every container in this compose project except this orchestrator-health container."""
    containers = _list_project_containers(project_name)
    if not containers:
        if project_name:
            raise HTTPException(status_code=404, detail=f"compose project not found: {project_name}")
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
        if _should_keep_running(container):
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


def _wake_all_containers(*, timeout_seconds: int = 90, project_name: str | None = None) -> dict[str, str]:
    """Start the entire stack in dependency order (except orchestrator-health)."""
    containers = _list_project_containers(project_name)
    if not containers:
        if project_name:
            raise HTTPException(status_code=404, detail=f"compose project not found: {project_name}")
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
        container = _find_container(service_name, explicit_container, project_name=project_name)
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
                project_name=project_name,
            )

    # Start any remaining stopped containers in this project (best-effort).
    for container in _list_project_containers(project_name):
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


def _cancel_project_auto_sleep_timer(project: str) -> None:
    timer = _AUTO_SLEEP_TIMERS_BY_PROJECT.pop(project, None)
    if timer is None:
        return
    try:
        timer.cancel()
    except Exception:  # pragma: no cover - defensive
        pass


def _auto_sleep_project(*, project: str, reason: str) -> None:
    try:
        _PROJECT_AWAKE_UNTIL.pop(project, None)
        _sleep_all_containers(reason=reason, project_name=project)
    except Exception:  # pragma: no cover - background thread
        logger.exception("Project auto-sleep failed (project=%s)", project)


def _schedule_project_auto_sleep(seconds: int, *, project: str, reason: str) -> None:
    _cancel_project_auto_sleep_timer(project)
    if seconds <= 0:
        return
    timer = threading.Timer(seconds, _auto_sleep_project, kwargs={"project": project, "reason": reason})
    timer.daemon = True
    timer.start()
    _AUTO_SLEEP_TIMERS_BY_PROJECT[project] = timer


def _power_state_from_project(project: str) -> PowerState:
    containers = _list_project_containers(project)
    if not containers:
        raise HTTPException(status_code=404, detail=f"compose project not found: {project}")

    running = False
    for container in containers:
        if _is_self_container(container):
            continue
        try:
            container.reload()
        except Exception:  # pragma: no cover - defensive
            pass
        if getattr(container, "status", "") == "running":
            running = True
            break

    awake_until = _PROJECT_AWAKE_UNTIL.get(project)
    if awake_until and awake_until < datetime.now(timezone.utc):
        _PROJECT_AWAKE_UNTIL.pop(project, None)
        awake_until = None

    return PowerState(
        state="awake" if running else "sleeping",
        reason=_PROJECT_LAST_REASON.get(project),
        updated_at=datetime.now(timezone.utc),
        awake_until=awake_until,
        project=project,
    )


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


@app.get("/power/projects/{project}", response_model=PowerState)
def read_project_power_state(project: str) -> PowerState:
    """Return the current power/sleep state for a specific compose project."""
    project = _validate_power_project(project)
    return _power_state_from_project(project)


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


@app.post("/power/projects/{project}", response_model=PowerState)
def change_project_power_state(project: str, payload: PowerRequest, request: Request) -> PowerState:
    """Sleep/wake a specific compose project (e.g. a cluster instance)."""
    _require_auth(request)
    project = _validate_power_project(project)

    if payload.action == "sleep":
        _cancel_project_auto_sleep_timer(project)
        _PROJECT_AWAKE_UNTIL.pop(project, None)
        if payload.reason:
            _PROJECT_LAST_REASON[project] = payload.reason
        _sleep_all_containers(reason=payload.reason, project_name=project)
        return _power_state_from_project(project)

    # wake
    _cancel_project_auto_sleep_timer(project)
    awake_until: Optional[datetime] = None
    if payload.awake_seconds:
        awake_until = datetime.now(timezone.utc) + timedelta(seconds=payload.awake_seconds)
    if payload.reason:
        _PROJECT_LAST_REASON[project] = payload.reason
    _wake_all_containers(timeout_seconds=120, project_name=project)
    if awake_until is not None:
        _PROJECT_AWAKE_UNTIL[project] = awake_until
        _schedule_project_auto_sleep(payload.awake_seconds or 0, project=project, reason="auto-sleep after wake TTL")
    return _power_state_from_project(project)


@app.post("/cluster/deploy")
def cluster_deploy_instance(payload: ClusterDeployRequest, request: Request) -> dict[str, Any]:
    """EXPERIMENTAL: create/start a cluster-mode avatar compose project (vtuber-<slug>)."""
    _require_auth(request)
    _require_cluster_control_enabled()

    avatar_id = payload.avatar_id.strip()
    slug = _slugify_avatar_id(avatar_id)
    if not slug:
        raise HTTPException(status_code=400, detail="avatar_id produces empty slug")
    project = _validate_power_project(f"vtuber-{slug}")

    ports = _cluster_ports(payload.slot)
    want_ports = {ports["signaling"], ports["runner"], ports["recorder"], ports["game_tcp"]}
    conflicts = _docker_port_conflicts(want_ports, ignore_project=project)
    if conflicts:
        items = ", ".join(f"{p}->{name}" for p, name in sorted(conflicts.items()))
        raise HTTPException(status_code=409, detail=f"host port conflict: {items}")

    subnet = _cluster_subnet(payload.slot)
    gateway = _cluster_gateway(payload.slot)
    allow_csv = _cluster_allowlist_csv(gateway)

    session_base = (os.environ.get("VTUBER_SESSION_DIR") or "/home/ubuntu/vtuber_sessions").strip()
    recordings_base = (os.environ.get("VTUBER_RECORDINGS_DIR") or "/home/ubuntu/recordings").strip()

    env = {
        "VTUBER_AVATAR_ID": avatar_id,
        "VTUBER_AVATAR_SLUG": slug,
        "VTUBER_INSTANCE_PROJECT_NAME": project,
        "VTUBER_SIGNALING_PUBLIC_PORT": str(ports["signaling"]),
        "VTUBER_RUNNER_PORT": str(ports["runner"]),
        "VTUBER_RECORDER_PORT": str(ports["recorder"]),
        "VTUBER_GAME_TCP_PORT": str(ports["game_tcp"]),
        "VTUBER_SESSION_DIR": f"{session_base.rstrip('/')}/{slug}",
        "VTUBER_RECORDINGS_DIR": f"{recordings_base.rstrip('/')}/{slug}",
        "VTUBER_SIGNALING_INSTANCE_ARGS": f"--public_port {ports['signaling']} --matchmaker_streamer_id {avatar_id}",
        "VTUBER_DOCKER_SUBNET": subnet,
        "VTUBER_ALLOWED_ADDRESSES": allow_csv,
    }
    if payload.gpu:
        env["NVIDIA_VISIBLE_DEVICES"] = payload.gpu.strip() or "all"

    args = ["up", "-d"]
    if payload.recreate:
        args.insert(1, "--force-recreate")

    out = _cluster_compose_instance(project=project, args=args, env=env)
    if out["exit_code"] != 0:
        detail = (out.get("stderr") or out.get("stdout") or "").strip()
        if detail:
            detail = "\n".join(detail.splitlines()[-10:]).strip()
        raise HTTPException(status_code=500, detail=f"cluster deploy failed: {detail or 'unknown error'}")

    return {
        "project": project,
        "avatar_id": avatar_id,
        "slot": payload.slot,
        "gpu": (payload.gpu or "").strip() or None,
        "ports": ports,
        "subnet": subnet,
        "gateway": gateway,
    }


@app.post("/cluster/down")
def cluster_down_instance(payload: ClusterDownRequest, request: Request) -> dict[str, Any]:
    """EXPERIMENTAL: stop/remove a cluster-mode avatar compose project (vtuber-<slug>)."""
    _require_auth(request)
    _require_cluster_control_enabled()

    project = payload.project
    slug: str | None = None
    if not project:
        avatar_id = (payload.avatar_id or "").strip()
        slug = _slugify_avatar_id(avatar_id)
        if not slug:
            raise HTTPException(status_code=400, detail="avatar_id produces empty slug")
        project = f"vtuber-{slug}"

    project = _validate_power_project(project)
    if slug is None:
        slug = project.removeprefix("vtuber-")
    slug = slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project produces empty slug")

    out = _cluster_compose_instance(
        project=project,
        args=["down"],
        env={"VTUBER_AVATAR_SLUG": slug, "VTUBER_INSTANCE_PROJECT_NAME": project},
    )
    if out["exit_code"] != 0:
        detail = (out.get("stderr") or out.get("stdout") or "").strip()
        if detail:
            detail = "\n".join(detail.splitlines()[-10:]).strip()
        raise HTTPException(status_code=500, detail=f"cluster down failed: {detail or 'unknown error'}")

    return {"project": project, "state": "sleeping"}


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ORCHESTRATOR_HEALTH_PORT", "9090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
