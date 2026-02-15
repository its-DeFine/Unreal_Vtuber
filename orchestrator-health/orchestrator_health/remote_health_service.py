"""Expose local Docker service health over HTTP for remote monitoring and power control."""
from __future__ import annotations

import json
import hashlib
import hmac
import logging
import os
import ipaddress
import re
import shlex
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Health", version="1.0.0")
monitor = ServiceMonitor()
docker_client = monitor.docker_client

POWER_STATE_FILE = Path(os.environ.get("POWER_STATE_FILE", "/var/lib/vtuber/power-state/power_state.json"))
ROLLOUT_STATE_FILE = Path(os.environ.get("ROLLOUT_STATE_FILE", str(POWER_STATE_FILE.parent / "rollout_state.json")))
VERIFY_LAST_FILE = Path(os.environ.get("VERIFY_LAST_FILE", str(POWER_STATE_FILE.parent / "verify_last.json")))


def _read_json_file(path: Path) -> Optional[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:  # pragma: no cover - best-effort
        return None
    try:
        data = json.loads(raw)
    except Exception:  # pragma: no cover - best-effort
        return None
    return data if isinstance(data, dict) else None


def _write_json_file_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


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
_DOCKER_TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)

_NVIDIA_SMI_QUERY = [
    "nvidia-smi",
    "--query-gpu=index,uuid,name,memory.total,driver_version",
    "--format=csv,noheader,nounits",
]

_NVIDIA_SMI_STATS_QUERY = [
    "nvidia-smi",
    "--query-gpu=index,uuid,utilization.gpu,utilization.encoder,utilization.decoder,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
    "--format=csv,noheader,nounits",
]

_META_GPU_STATS_CACHE_LOCK = threading.Lock()
_META_GPU_STATS_CACHE: Optional[dict[str, Any]] = None
_META_GPU_STATS_CACHE_CAPTURED_MONO: Optional[float] = None


def _meta_gpu_stats_ttl_seconds() -> float:
    raw = (os.environ.get("META_GPU_STATS_TTL_SECONDS", "5") or "").strip()
    try:
        ttl_s = float(raw)
    except Exception:
        ttl_s = 5.0
    if ttl_s < 0:
        ttl_s = 0.0
    # Cap to keep "cached" meaningfully fresh; avoid hiding stale stats for long periods.
    if ttl_s > 600:
        ttl_s = 600.0
    return ttl_s


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
    console_variables_file: Optional[str] = Field(
        default=None,
        description="Optional override for VTUBER_CONSOLE_VARIABLES_FILE (relative path under the project dir).",
    )
    game_user_settings_file: Optional[str] = Field(
        default=None,
        description="Optional override for VTUBER_GAME_USER_SETTINGS_FILE (relative path under the project dir).",
    )
    embody_extra_args: Optional[str] = Field(
        default=None,
        description="Optional override for EMBODY_EXTRA_ARGS (Unreal cmdline; ex: -ResX=1280 -ResY=720).",
    )


class ClusterDownRequest(BaseModel):
    avatar_id: Optional[str] = Field(default=None, description="Matchmaker streamer id (ex: arthur-0).")
    project: Optional[str] = Field(default=None, description="Compose project name (ex: vtuber-arthur-0).")

    @model_validator(mode="after")
    def _validate_target(self) -> "ClusterDownRequest":
        if not (self.avatar_id or self.project):
            raise ValueError("avatar_id or project is required")
        return self


class OpsUpgradeRequest(BaseModel):
    ref: Optional[str] = Field(default=None, description="Optional git ref (tag/branch/sha) to checkout after fetching.")
    service_image_tag: Optional[str] = Field(
        default=None,
        description="Optional EMBODY_SERVICE_IMAGE_TAG to write into the host .env (used for service images).",
    )
    apply: bool = Field(default=False, description="If true, pull/recreate host-level containers after updating the repo.")
    recreate_game: bool = Field(
        default=False,
        description=(
            "If true (and apply=true), force-recreate the unreal-game container too. "
            "Refuses when unreal-game is currently running (sleep first)."
        ),
    )
    recreate_all: bool = Field(
        default=False,
        description=(
            "If true (and apply=true), force-recreate all services in the current compose project "
            "(excluding orchestrator-health + orchestrator-edge-rotator). "
            "Implies recreate_game. Refuses when unreal-game is currently running (sleep first)."
        ),
    )
    recreate_orchestrator_health: bool = Field(
        default=False,
        description=(
            "If true (and apply=true), schedule a force-recreate of orchestrator-health AFTER responding "
            "(via the executor container). This allows updating orchestrator-health itself without the "
            "HTTP request getting cut off mid-response. Causes a brief control-plane blip (~5-15s)."
        ),
    )
    recreate_orchestrator_edge_rotator: bool = Field(
        default=False,
        description=(
            "If true (and apply=true), schedule a force-recreate of orchestrator-edge-rotator AFTER "
            "responding (via a short-lived helper container). Useful for deterministic remote control-plane "
            "updates without waiting for watchtower."
        ),
    )

    @model_validator(mode="after")
    def _validate_upgrade_args(self) -> "OpsUpgradeRequest":
        if self.ref is not None:
            self.ref = self.ref.strip()
            if not self.ref:
                self.ref = None
            elif "\x00" in self.ref or "\n" in self.ref or "\r" in self.ref or any(ch.isspace() for ch in self.ref):
                raise ValueError("ref contains invalid whitespace/control characters")
            elif self.ref.startswith("-"):
                raise ValueError("ref must not start with '-'")
            elif len(self.ref) > 200:
                raise ValueError("ref is too long")

        if self.service_image_tag is not None:
            self.service_image_tag = self.service_image_tag.strip()
            if not self.service_image_tag:
                self.service_image_tag = None
            elif (
                "\x00" in self.service_image_tag
                or "\n" in self.service_image_tag
                or "\r" in self.service_image_tag
                or any(ch.isspace() for ch in self.service_image_tag)
            ):
                raise ValueError("service_image_tag contains invalid whitespace/control characters")
            elif not _DOCKER_TAG_RE.match(self.service_image_tag):
                raise ValueError("service_image_tag must be a docker tag (letters/digits/._-; max 128 chars)")

        return self


class OpsRolloutRequest(BaseModel):
    payments_api_url: Optional[str] = Field(default=None, description="Payments backend base URL override.")
    image_ref: Optional[str] = Field(default=None, description="Payments license image_ref override (enc-v1, etc).")
    no_verify: bool = Field(default=False, description="Skip post-rollout health verification.")
    stage_only: bool = Field(
        default=False,
        description="If true, allow downloading+loading the encrypted image while unreal-game is running. Does not restart containers.",
    )
    skip_download: bool = Field(
        default=False,
        description="If true, do not download/load; only apply an already-staged image (requires recreate_stopped).",
    )
    min_free_gb: int = Field(
        default=15,
        ge=0,
        le=1024,
        description="Require at least this many GiB free on the project filesystem before downloading/loading.",
    )
    recreate_stopped: bool = Field(
        default=False,
        description="If true, force-recreate stopped game containers after the image is loaded (keeps them stopped).",
    )


class OpsPullImageRequest(BaseModel):
    image: str = Field(min_length=1, description="Docker image ref to pull (ex: ghcr.io/...:tag).")


def _env_truthy(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _require_cluster_control_enabled() -> None:
    # Cluster deploy/down is powerful and should remain opt-in.
    if not _env_truthy("EXPERIMENTAL_REMOTE_CLUSTER_CONTROL", default=False):
        raise HTTPException(status_code=404, detail="cluster control not enabled")


def _require_remote_ops_enabled() -> None:
    if not _env_truthy("EXPERIMENTAL_REMOTE_OPS", default=True):
        raise HTTPException(status_code=404, detail="remote ops not enabled")


def _request_client_ip(request: Request) -> Optional[str]:
    """Extract a best-effort client IP for allowlist checks.

    Starlette's TestClient sets request.client.host="testclient". Map that to
    localhost so allowlist-gated endpoints can be unit-tested without weakening
    production auth behavior.
    """
    ip = request.client.host if request.client else None
    if ip == "testclient":
        return "127.0.0.1"
    return ip


def _require_auth(request: Request) -> None:
    allowed = _get_power_allowed_ips()
    if not allowed:
        return
    client_ip = _request_client_ip(request)
    if (not client_ip) or (not _ip_in_allowlist(client_ip, allowed)):
        raise HTTPException(status_code=403, detail="client address not allowed")


def _require_auth_strict(request: Request) -> None:
    allowed = _get_power_allowed_ips()
    if not allowed:
        raise HTTPException(status_code=403, detail="POWER_ALLOWED_IPS must be set for remote ops")
    client_ip = _request_client_ip(request)
    if (not client_ip) or (not _ip_in_allowlist(client_ip, allowed)):
        raise HTTPException(status_code=403, detail="client address not allowed")


def _get_ops_hmac_secret() -> Optional[bytes]:
    raw = (os.environ.get("OPS_HMAC_SECRET") or "").strip()
    if raw:
        return raw.encode("utf-8")
    path_raw = (os.environ.get("OPS_HMAC_SECRET_FILE") or "").strip()
    if not path_raw:
        return None
    try:
        value = Path(path_raw).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed reading OPS_HMAC_SECRET_FILE=%s: %s", path_raw, exc)
        return None
    return value.encode("utf-8") if value else None


def _ops_hmac_required() -> bool:
    return _env_truthy("OPS_HMAC_REQUIRED", default=False)


def _ops_hmac_ttl_seconds() -> int:
    raw = (os.environ.get("OPS_HMAC_TTL_SECONDS") or "").strip()
    if not raw:
        return 300
    try:
        ttl = int(raw)
    except ValueError:
        return 300
    return max(10, min(24 * 60 * 60, ttl))


async def _require_ops_hmac(request: Request) -> None:
    """Optional second-factor auth for dangerous endpoints.

    When enabled, the client must send:
      - X-Embody-Ops-Timestamp: unix epoch seconds
      - X-Embody-Ops-Signature: hex(hmac_sha256(secret, canonical_request))

    canonical_request:
      <ts>\\n<METHOD>\\n<PATH>\\n<sha256(body)>
    """

    secret = _get_ops_hmac_secret()
    required = _ops_hmac_required()
    if secret is None:
        if required:
            raise HTTPException(status_code=500, detail="OPS_HMAC_SECRET is required but not configured")
        return

    ts_raw = (request.headers.get("X-Embody-Ops-Timestamp") or "").strip()
    sig_raw = (request.headers.get("X-Embody-Ops-Signature") or "").strip()
    if not ts_raw or not sig_raw:
        if required:
            raise HTTPException(status_code=401, detail="ops signature required")
        return

    try:
        ts = int(ts_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid ops timestamp")

    now = int(time.time())
    ttl = _ops_hmac_ttl_seconds()
    if ts > now + 30 or now - ts > ttl:
        raise HTTPException(status_code=401, detail="ops signature expired")

    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()
    path = request.url.path
    canonical = f"{ts}\n{request.method.upper()}\n{path}\n{body_hash}".encode("utf-8")
    expected = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_raw):
        raise HTTPException(status_code=401, detail="invalid ops signature")


async def _require_ops_action(request: Request) -> None:
    _require_remote_ops_enabled()
    _require_auth_strict(request)
    await _require_ops_hmac(request)


async def _require_cluster_action(request: Request) -> None:
    _require_cluster_control_enabled()
    _require_auth_strict(request)
    await _require_ops_hmac(request)


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


def _validate_compose_project_name(project: str) -> str:
    project = project.strip()
    if not project:
        raise HTTPException(status_code=400, detail="project is required")
    if not _PROJECT_NAME_RE.match(project):
        raise HTTPException(status_code=400, detail="invalid project name")
    return project


def _slugify_avatar_id(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9_.-]+", "-", s)
    s = s.strip("-_.")
    return s


def _validate_compose_project_relpath(path: str, *, field: str) -> str:
    raw = (path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail=f"{field} is empty")
    if "\x00" in raw or "\n" in raw or "\r" in raw:
        raise HTTPException(status_code=400, detail=f"{field} contains invalid characters")
    if raw.startswith("/"):
        raise HTTPException(status_code=400, detail=f"{field} must be a relative path")

    parts = Path(raw).parts
    if any(part in ("..",) for part in parts):
        raise HTTPException(status_code=400, detail=f"{field} must not contain ..")
    if not raw.startswith("./pixel-streaming/config/"):
        raise HTTPException(status_code=400, detail=f"{field} must start with ./pixel-streaming/config/")
    return raw


def _cluster_ports(slot: int) -> dict[str, int]:
    return {
        "signaling": 8080 + slot,
        "runner": 9877 + slot,
        "recorder": 8889 + slot,
        "game_tcp": 7777 + slot,
        "openclaw_gateway": 18789 + slot,
        "openclaw_chat": 18801 + slot,
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
        executor = docker_client.containers.get(name)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cluster executor container not found (%s): %s", name, exc)
        raise HTTPException(status_code=503, detail=f"cluster executor not running: {name}") from exc
    try:
        executor.reload()
    except Exception:  # pragma: no cover - defensive
        pass
    if getattr(executor, "status", "") != "running":
        raise HTTPException(status_code=503, detail=f"cluster executor not running: {name}")
    return executor


def _cluster_executor_try_container() -> Optional[Any]:
    name = (os.environ.get("CLUSTER_EXECUTOR_CONTAINER") or "vtuber-orchestrator-edge-rotator").strip()
    try:
        executor = docker_client.containers.get(name)
    except Exception:
        return None
    try:
        executor.reload()
    except Exception:
        return None
    if getattr(executor, "status", "") != "running":
        return None
    return executor


def _cluster_executor_read_file(executor: Any, path: str) -> Optional[str]:
    try:
        result = executor.exec_run(["cat", path], demux=True)
    except Exception:  # noqa: BLE001
        return None
    if getattr(result, "exit_code", 1) != 0:
        return None
    stdout_b, _stderr_b = result.output or (b"", b"")
    return (stdout_b or b"").decode("utf-8", errors="replace").strip() or None


def _cluster_executor_exec(executor: Any, cmd: list[str], *, env: Optional[dict[str, str]] = None) -> dict[str, Any]:
    try:
        result = executor.exec_run(cmd, environment=env, demux=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"exec failed: {exc}") from exc
    stdout_b, stderr_b = result.output or (b"", b"")
    return {
        "exit_code": getattr(result, "exit_code", 1),
        "stdout": (stdout_b or b"").decode("utf-8", errors="replace"),
        "stderr": (stderr_b or b"").decode("utf-8", errors="replace"),
        "cmd": cmd,
    }


def _tail(text: str, *, max_lines: int = 200, max_chars: int = 50_000) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out


def _meta_gpu_stats_cache_get() -> Optional[dict[str, Any]]:
    ttl_s = _meta_gpu_stats_ttl_seconds()
    if ttl_s <= 0:
        return None
    now_mono = time.monotonic()

    with _META_GPU_STATS_CACHE_LOCK:
        payload = _META_GPU_STATS_CACHE
        captured_mono = _META_GPU_STATS_CACHE_CAPTURED_MONO
        if (payload is None) or (captured_mono is None):
            return None
        age_s = now_mono - captured_mono
        if age_s < 0 or age_s > ttl_s:
            return None
        out = dict(payload)

    out["timestamp"] = datetime.now(timezone.utc).isoformat()
    out["cached"] = True
    out["cache_age_s"] = age_s
    return out


def _meta_gpu_stats_cache_set(payload: dict[str, Any], *, captured_mono: float) -> None:
    global _META_GPU_STATS_CACHE, _META_GPU_STATS_CACHE_CAPTURED_MONO
    ttl_s = _meta_gpu_stats_ttl_seconds()
    if ttl_s <= 0:
        return
    with _META_GPU_STATS_CACHE_LOCK:
        _META_GPU_STATS_CACHE = dict(payload)
        _META_GPU_STATS_CACHE_CAPTURED_MONO = captured_mono


def _cluster_project_dir() -> str:
    project_dir = (os.environ.get("ORCHESTRATOR_PROJECT_DIR") or "/home/ubuntu/Unreal_Vtuber").strip()
    if not project_dir.startswith("/"):
        return ""
    return project_dir


def _detect_game_image_ref() -> str:
    """Best-effort: return the unreal-game image ref from any local container (single-stack or cluster)."""
    try:
        for container in docker_client.containers.list(all=True, filters={"label": ["com.docker.compose.service=unreal-game"]}):
            image_ref = (((container.attrs or {}).get("Config") or {}).get("Image") or "").strip()
            if image_ref:
                return image_ref
    except Exception:  # pragma: no cover - best-effort
        pass
    return "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest"


def _docker_image_id(image_ref: str) -> Optional[str]:
    try:
        return getattr(docker_client.images.get(image_ref), "id", None)
    except Exception:  # noqa: BLE001
        return None


def _executor_disk_free_bytes(executor: Any, path: str) -> Optional[int]:
    out = _cluster_executor_exec(executor, ["df", "-Pk", path])
    if out.get("exit_code") != 0:
        return None
    lines = (out.get("stdout") or "").splitlines()
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 4:
        return None
    try:
        available_k = int(parts[3])
    except Exception:
        return None
    if available_k < 0:
        return None
    return available_k * 1024


def _resolve_git_ref_from_packed_refs(packed: str, ref: str) -> Optional[str]:
    ref = ref.strip()
    if not ref:
        return None
    for line in packed.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, name = parts
        if name == ref and sha:
            return sha
    return None


def _git_head_info_from_executor(executor: Any, project_dir: str) -> Optional[dict[str, str]]:
    if not project_dir:
        return None
    head_path = f"{project_dir}/.git/HEAD"
    head = _cluster_executor_read_file(executor, head_path)
    if not head:
        return None
    head = head.strip()

    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        sha = _cluster_executor_read_file(executor, f"{project_dir}/.git/{ref}")
        if not sha:
            packed = _cluster_executor_read_file(executor, f"{project_dir}/.git/packed-refs")
            if packed:
                sha = _resolve_git_ref_from_packed_refs(packed, ref)
        if not sha:
            return {"mode": "ref", "ref": ref, "sha": ""}
        return {"mode": "ref", "ref": ref, "sha": sha.strip()}

    return {"mode": "detached", "ref": "", "sha": head}


def _container_meta(container: Any) -> dict[str, Any]:
    try:
        container.reload()
    except Exception:  # pragma: no cover - defensive
        pass
    labels = ((container.attrs or {}).get("Config", {}) or {}).get("Labels") or {}
    project = (labels.get("com.docker.compose.project") or "").strip() or None
    service = (labels.get("com.docker.compose.service") or "").strip() or None
    image_ref = (((container.attrs or {}).get("Config", {}) or {}).get("Image") or "").strip() or None
    image_id = None
    try:
        image_id = getattr(getattr(container, "image", None), "id", None)
    except Exception:  # pragma: no cover - defensive
        image_id = None
    return {
        "name": getattr(container, "name", ""),
        "status": getattr(container, "status", ""),
        "project": project,
        "service": service,
        "image": image_ref,
        "image_id": image_id,
    }


def _self_image_id() -> str:
    try:
        container = docker_client.containers.get(POWER_SELF_CONTAINER)
    except Exception:  # pragma: no cover - defensive
        container = None
        try:
            for candidate in docker_client.containers.list(all=True):
                if _is_self_container(candidate):
                    container = candidate
                    break
        except Exception:
            container = None
    if container is None:
        return ""
    try:
        image_id = getattr(getattr(container, "image", None), "id", None)
    except Exception:
        image_id = None
    return str(image_id or "").strip()


def _parse_nvidia_smi_csv(stdout: str) -> tuple[list[dict[str, Any]], Optional[str]]:
    gpus: list[dict[str, Any]] = []
    driver_version: Optional[str] = None
    for raw in (stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue
        raw_index, uuid, name, raw_mem, raw_driver = parts[:5]
        try:
            index = int(raw_index)
        except Exception:
            continue
        try:
            memory_total_mib = int(float(raw_mem))
        except Exception:
            memory_total_mib = None
        driver = raw_driver.strip() or None
        if driver and not driver_version:
            driver_version = driver
        gpus.append(
            {
                "index": index,
                "uuid": uuid.strip() or None,
                "name": name.strip() or None,
                "memory_total_mib": memory_total_mib,
                "driver_version": driver,
            }
        )
    return gpus, driver_version


def _parse_nvidia_smi_int(value: str) -> Optional[int]:
    token = (value or "").strip()
    if not token:
        return None
    lowered = token.lower()
    if lowered in {"n/a", "na"}:
        return None
    try:
        return int(float(token))
    except Exception:
        return None


def _parse_nvidia_smi_float(value: str) -> Optional[float]:
    token = (value or "").strip()
    if not token:
        return None
    lowered = token.lower()
    if lowered in {"n/a", "na"}:
        return None
    try:
        return float(token)
    except Exception:
        return None


def _parse_nvidia_smi_stats_csv(stdout: str) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for raw in (stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 10:
            continue
        (
            raw_index,
            raw_uuid,
            raw_util_gpu,
            raw_util_enc,
            raw_util_dec,
            raw_mem_used,
            raw_mem_total,
            raw_temp,
            raw_power_draw,
            raw_power_limit,
        ) = parts[:10]
        index = _parse_nvidia_smi_int(raw_index)
        if index is None:
            continue
        gpus.append(
            {
                "index": index,
                "uuid": raw_uuid.strip() or None,
                "utilization_gpu_pct": _parse_nvidia_smi_int(raw_util_gpu),
                "utilization_encoder_pct": _parse_nvidia_smi_int(raw_util_enc),
                "utilization_decoder_pct": _parse_nvidia_smi_int(raw_util_dec),
                "memory_used_mib": _parse_nvidia_smi_int(raw_mem_used),
                "memory_total_mib": _parse_nvidia_smi_int(raw_mem_total),
                "temperature_gpu_c": _parse_nvidia_smi_int(raw_temp),
                "power_draw_w": _parse_nvidia_smi_float(raw_power_draw),
                "power_limit_w": _parse_nvidia_smi_float(raw_power_limit),
            }
        )
    return gpus


def _gpu_inventory_from_executor(*, executor: Any, image_id: str) -> dict[str, Any]:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        image_id,
        *_NVIDIA_SMI_QUERY,
    ]
    out = _cluster_executor_exec(executor, cmd)
    out["stdout"] = _tail(out.get("stdout", ""))
    out["stderr"] = _tail(out.get("stderr", ""))
    if out["exit_code"] != 0:
        return {"ok": False, "error": "nvidia-smi failed", **out}
    gpus, driver_version = _parse_nvidia_smi_csv(out.get("stdout", ""))
    if not gpus:
        return {"ok": False, "error": "no GPUs detected", **out}
    return {
        "ok": True,
        "gpus": gpus,
        "driver_version": driver_version,
        **out,
    }


def _gpu_stats_from_executor(*, executor: Any, image_id: str) -> dict[str, Any]:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        image_id,
        *_NVIDIA_SMI_STATS_QUERY,
    ]
    out = _cluster_executor_exec(executor, cmd)
    out["stdout"] = _tail(out.get("stdout", ""))
    out["stderr"] = _tail(out.get("stderr", ""))
    if out["exit_code"] != 0:
        return {"ok": False, "error": "nvidia-smi failed", **out}
    gpus = _parse_nvidia_smi_stats_csv(out.get("stdout", ""))
    if not gpus:
        return {"ok": False, "error": "no GPUs detected", **out}
    return {
        "ok": True,
        "gpus": gpus,
        **out,
    }


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


def _host_compose_exec(*, project: str, args: list[str], env: Optional[dict[str, str]] = None) -> dict[str, Any]:
    project_dir = _cluster_project_dir()
    if not project_dir:
        raise HTTPException(status_code=500, detail="invalid ORCHESTRATOR_PROJECT_DIR")
    host_compose = (os.environ.get("HOST_COMPOSE_FILE") or "docker-compose.unreal.yml").strip()

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
        f"{project_dir}/{host_compose}",
        *args,
    ]

    executor = _cluster_executor_container()
    try:
        result = executor.exec_run(cmd, environment=env or {}, demux=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("Host compose exec failed (project=%s): %s", project, exc)
        raise HTTPException(status_code=500, detail=f"host compose exec failed: {exc}") from exc

    stdout_b, stderr_b = result.output or (b"", b"")
    stdout = (stdout_b or b"").decode("utf-8", errors="replace")
    stderr = (stderr_b or b"").decode("utf-8", errors="replace")
    exit_code = getattr(result, "exit_code", 1)
    return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr, "cmd": cmd}


def _env_list_to_dict(items: Any) -> dict[str, str]:
    if not isinstance(items, list):
        return {}
    out: dict[str, str] = {}
    for entry in items:
        raw = str(entry or "")
        if not raw or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        out[key] = value
    return out


def _container_env(container: Any) -> dict[str, str]:
    try:
        container.reload()
    except Exception:  # pragma: no cover - defensive
        pass
    env_list = (((container.attrs or {}).get("Config") or {}).get("Env") or [])
    return _env_list_to_dict(env_list)


def _container_host_port(container: Any, container_port: str) -> Optional[int]:
    try:
        container.reload()
    except Exception:  # pragma: no cover - defensive
        pass
    ports = ((container.attrs or {}).get("NetworkSettings") or {}).get("Ports") or {}
    bindings = ports.get(container_port)
    if not bindings:
        return None
    for binding in bindings:
        host_port_raw = (binding or {}).get("HostPort")
        try:
            return int(host_port_raw)
        except Exception:
            continue
    return None


def _container_mount_source(container: Any, destination: str) -> Optional[str]:
    try:
        container.reload()
    except Exception:  # pragma: no cover - defensive
        pass
    mounts = (container.attrs or {}).get("Mounts") or []
    for mount in mounts:
        if (mount or {}).get("Destination") == destination:
            source = (mount or {}).get("Source")
            return str(source) if source else None
    return None


def _relpath_under_project(source: Optional[str], project_dir: str) -> Optional[str]:
    if not source:
        return None
    if not source.startswith("/"):
        return None
    try:
        rel = Path(source).relative_to(Path(project_dir))
    except Exception:
        return None
    return f"./{rel.as_posix()}"


def _parse_matchmaker_streamer_id(extra_args: str) -> Optional[str]:
    extra_args = (extra_args or "").strip()
    if not extra_args:
        return None
    match = re.search(r"--matchmaker_streamer_id\s+([^\s]+)", extra_args)
    return match.group(1) if match else None


def _project_running_containers(project: str) -> list[str]:
    running: list[str] = []
    for container in docker_client.containers.list(all=True, filters={"label": [f"com.docker.compose.project={project}"]}):
        try:
            container.reload()
        except Exception:  # pragma: no cover - defensive
            continue
        if getattr(container, "status", "") == "running":
            running.append(getattr(container, "name", ""))
    return running


def _derive_cluster_recreate_env(*, project: str, project_dir: str) -> dict[str, str]:
    slug = project.removeprefix("vtuber-").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="project produces empty slug")

    game = _find_container("unreal-game", project_name=project)
    signaling = _find_container("unreal-signaling", project_name=project)
    recorder = _find_container("recorder-control", project_name=project)
    if game is None or signaling is None or recorder is None:
        raise HTTPException(status_code=404, detail=f"compose project missing required services: {project}")

    signaling_port = _container_host_port(signaling, "80/tcp")
    game_tcp_port = _container_host_port(game, "7777/tcp")
    runner_port = _container_host_port(game, "9877/tcp")
    recorder_port = _container_host_port(recorder, "8889/tcp")
    if not signaling_port or not game_tcp_port or not runner_port or not recorder_port:
        raise HTTPException(status_code=500, detail=f"failed to read published ports for: {project}")

    slot = signaling_port - 8080
    if slot < 0 or slot > 255:
        raise HTTPException(status_code=500, detail=f"invalid signaling port for slot calc: {signaling_port}")

    subnet = _cluster_subnet(slot)
    gateway = _cluster_gateway(slot)
    allow_csv = _cluster_allowlist_csv(gateway)

    session_dir = _container_mount_source(game, "/opt/embody/sessions")
    recordings_dir = _container_mount_source(recorder, "/recordings")

    session_base = (os.environ.get("VTUBER_SESSION_DIR") or "/home/ubuntu/vtuber_sessions").strip()
    recordings_base = (os.environ.get("VTUBER_RECORDINGS_DIR") or "/home/ubuntu/recordings").strip()
    if not session_dir:
        session_dir = f"{session_base.rstrip('/')}/{slug}"
    if not recordings_dir:
        recordings_dir = f"{recordings_base.rstrip('/')}/{slug}"

    signaling_env = _container_env(signaling)
    avatar_id = _parse_matchmaker_streamer_id(signaling_env.get("SIGNALING_EXTRA_ARGS", "")) or slug
    instance_args = f"--public_port {signaling_port} --matchmaker_streamer_id {avatar_id}"

    env = _container_env(game)
    gpu = (env.get("NVIDIA_VISIBLE_DEVICES") or "").strip()
    extra_args = (env.get("EMBODY_EXTRA_ARGS") or "").strip()

    out: dict[str, str] = {
        "VTUBER_AVATAR_SLUG": slug,
        "VTUBER_INSTANCE_PROJECT_NAME": project,
        "VTUBER_SIGNALING_PUBLIC_PORT": str(signaling_port),
        "VTUBER_RUNNER_PORT": str(runner_port),
        "VTUBER_RECORDER_PORT": str(recorder_port),
        "VTUBER_GAME_TCP_PORT": str(game_tcp_port),
        "VTUBER_SESSION_DIR": session_dir,
        "VTUBER_RECORDINGS_DIR": recordings_dir,
        "VTUBER_SIGNALING_INSTANCE_ARGS": instance_args,
        "VTUBER_DOCKER_SUBNET": subnet,
        "VTUBER_ALLOWED_ADDRESSES": allow_csv,
    }
    if gpu:
        out["NVIDIA_VISIBLE_DEVICES"] = gpu
    if extra_args and "\x00" not in extra_args and "\n" not in extra_args and "\r" not in extra_args:
        out["EMBODY_EXTRA_ARGS"] = extra_args

    console_src = _container_mount_source(game, "/opt/embody/Embody/Saved/Config/LinuxNoEditor/ConsoleVariables.ini")
    gus_src = _container_mount_source(game, "/opt/embody/Embody/Saved/Config/LinuxNoEditor/GameUserSettings.ini")

    console_rel = _relpath_under_project(console_src, project_dir)
    gus_rel = _relpath_under_project(gus_src, project_dir)
    if console_rel and console_rel.startswith("./pixel-streaming/config/"):
        out["VTUBER_CONSOLE_VARIABLES_FILE"] = console_rel
    if gus_rel and gus_rel.startswith("./pixel-streaming/config/"):
        out["VTUBER_GAME_USER_SETTINGS_FILE"] = gus_rel

    return out


def _recreate_stopped_game_projects(*, project_dir: str) -> list[dict[str, Any]]:
    _detect_compose_identity()
    host_project = (POWER_PROJECT_NAME or os.environ.get("COMPOSE_PROJECT_NAME") or "").strip()

    projects: set[str] = set()
    try:
        for container in docker_client.containers.list(all=True, filters={"label": ["com.docker.compose.service=unreal-game"]}):
            try:
                container.reload()
            except Exception:  # pragma: no cover - defensive
                continue
            if getattr(container, "status", "") == "running":
                continue
            labels = ((container.attrs or {}).get("Config") or {}).get("Labels") or {}
            project = (labels.get("com.docker.compose.project") or "").strip()
            if project:
                projects.add(project)
    except Exception:  # pragma: no cover - defensive
        projects = set()

    results: list[dict[str, Any]] = []

    for project in sorted(projects):
        if host_project and project == host_project:
            out = _host_compose_exec(
                project=project,
                args=["up", "--no-start", "--force-recreate", "unreal-game", "vtuber-script-runner", "vtuber-watchdog"],
            )
            out["project"] = project
            out["stdout"] = _tail(out.get("stdout", ""))
            out["stderr"] = _tail(out.get("stderr", ""))
            out["ok"] = out.get("exit_code") == 0
            results.append(out)
            continue

        running = _project_running_containers(project)
        if running:
            results.append({"project": project, "ok": False, "skipped": True, "detail": "project has running containers"})
            continue

        try:
            env = _derive_cluster_recreate_env(project=project, project_dir=project_dir)
        except HTTPException as exc:
            results.append({"project": project, "ok": False, "skipped": True, "detail": str(exc.detail)})
            continue

        out = _cluster_compose_instance(
            project=project,
            args=[
                "up",
                "--no-start",
                "--force-recreate",
                "unreal-game",
                "vtuber-script-runner",
                "vtuber-watchdog",
            ],
            env=env,
        )
        out["project"] = project
        out["stdout"] = _tail(out.get("stdout", ""))
        out["stderr"] = _tail(out.get("stderr", ""))
        out["ok"] = out.get("exit_code") == 0
        results.append(out)

    return results


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

@app.get("/meta")
def read_meta(request: Request) -> dict[str, Any]:
    """Return best-effort deployment metadata (images + git head) for remote debugging."""
    _require_auth(request)
    project_dir = _cluster_project_dir()
    instance_compose = (os.environ.get("CLUSTER_INSTANCE_COMPOSE_FILE") or "docker-compose.unreal.instance.yml").strip()

    executor = _cluster_executor_try_container()
    git_info: Optional[dict[str, str]] = None
    if executor is not None:
        git_info = _git_head_info_from_executor(executor, project_dir)

    containers: list[dict[str, Any]] = []
    try:
        for container in docker_client.containers.list(all=True):
            containers.append(_container_meta(container))
    except Exception:  # pragma: no cover - defensive
        containers = []

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": {
            "EMBODY_SERVICE_IMAGE_TAG": (os.environ.get("EMBODY_SERVICE_IMAGE_TAG") or "").strip() or None,
            "ORCHESTRATOR_PROJECT_DIR": project_dir or None,
            "CLUSTER_INSTANCE_COMPOSE_FILE": instance_compose or None,
        },
        "git": git_info,
        "containers": containers,
        "rollout": _read_json_file(ROLLOUT_STATE_FILE),
        "verify_last": _read_json_file(VERIFY_LAST_FILE),
    }


@app.get("/meta/gpu")
def read_meta_gpu(request: Request) -> dict[str, Any]:
    """Return NVIDIA GPU inventory (best-effort) via nvidia-smi inside a GPU-enabled container."""
    _require_auth_strict(request)

    image_id = _self_image_id()
    if not image_id:
        return {
            "ok": False,
            "error": "self image not found",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    executor = _cluster_executor_try_container()
    if executor is None:
        return {
            "ok": False,
            "error": "cluster executor not running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    payload = _gpu_inventory_from_executor(executor=executor, image_id=image_id)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


@app.get("/meta/gpu/stats")
def read_meta_gpu_stats(request: Request) -> dict[str, Any]:
    """Return NVIDIA GPU stats (best-effort) via nvidia-smi inside a GPU-enabled container.

    Cached for META_GPU_STATS_TTL_SECONDS to avoid spamming nvidia-smi during long soak tests.
    """
    _require_auth_strict(request)

    cached = _meta_gpu_stats_cache_get()
    if cached is not None:
        return cached

    image_id = _self_image_id()
    if not image_id:
        payload: dict[str, Any] = {"ok": False, "error": "self image not found"}
    else:
        executor = _cluster_executor_try_container()
        if executor is None:
            payload = {"ok": False, "error": "cluster executor not running"}
        else:
            payload = _gpu_stats_from_executor(executor=executor, image_id=image_id)

    captured_mono = time.monotonic()
    captured_at = datetime.now(timezone.utc).isoformat()
    payload["captured_at"] = captured_at
    payload["timestamp"] = captured_at
    payload["cached"] = False
    payload["cache_age_s"] = 0.0

    _meta_gpu_stats_cache_set(payload, captured_mono=captured_mono)
    return payload


@app.post("/ops/upgrade")
def ops_upgrade(
    payload: OpsUpgradeRequest,
    request: Request,
    _: Any = Depends(_require_ops_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: update the repo (ff-only) and optionally recreate host-level containers."""
    if payload.recreate_orchestrator_health and (not payload.apply):
        raise HTTPException(status_code=400, detail="recreate_orchestrator_health requires apply=true")
    if payload.recreate_orchestrator_edge_rotator and (not payload.apply):
        raise HTTPException(status_code=400, detail="recreate_orchestrator_edge_rotator requires apply=true")
    project_dir = _cluster_project_dir()
    if not project_dir:
        raise HTTPException(status_code=500, detail="invalid ORCHESTRATOR_PROJECT_DIR")

    executor = _cluster_executor_container()
    steps: list[dict[str, Any]] = []

    def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
        out = _cluster_executor_exec(executor, cmd)
        out["name"] = name
        out["stdout"] = _tail(out.get("stdout", ""))
        out["stderr"] = _tail(out.get("stderr", ""))
        steps.append(out)
        return out

    git_cmd = ["git", "-c", f"safe.directory={project_dir}", "-C", project_dir]
    env_file = f"{project_dir}/.env"

    repo = run_step("git_is_repo", [*git_cmd, "rev-parse", "--is-inside-work-tree"])
    if repo["exit_code"] != 0:
        return {"ok": False, "exit_code": repo["exit_code"], "steps": steps}

    dirty = run_step("git_status", [*git_cmd, "status", "--porcelain"])
    if dirty["exit_code"] == 0 and (dirty.get("stdout") or "").strip():
        return {"ok": False, "exit_code": 409, "detail": "dirty working tree", "steps": steps}

    before = run_step("git_head_before", [*git_cmd, "rev-parse", "--short", "HEAD"])

    if payload.ref:
        fetch = run_step("git_fetch", [*git_cmd, "fetch", "-q", "--tags", "origin"])
        if fetch["exit_code"] != 0:
            return {"ok": False, "exit_code": fetch["exit_code"], "steps": steps}

        requested_ref = payload.ref
        resolved_ref = requested_ref
        if not _GIT_SHA_RE.match(requested_ref) and not requested_ref.startswith("refs/") and "/" not in requested_ref:
            has_tag = run_step(
                "git_has_tag",
                [*git_cmd, "show-ref", "--quiet", "--verify", f"refs/tags/{requested_ref}"],
            )
            if has_tag["exit_code"] != 0:
                has_origin_branch = run_step(
                    "git_has_origin_branch",
                    [*git_cmd, "show-ref", "--quiet", "--verify", f"refs/remotes/origin/{requested_ref}"],
                )
                if has_origin_branch["exit_code"] == 0:
                    resolved_ref = f"origin/{requested_ref}"

        checkout = run_step("git_checkout", [*git_cmd, "checkout", "-q", "--detach", resolved_ref])
        if checkout["exit_code"] != 0 and resolved_ref != requested_ref:
            checkout = run_step("git_checkout_fallback", [*git_cmd, "checkout", "-q", "--detach", requested_ref])
        if checkout["exit_code"] != 0:
            return {"ok": False, "exit_code": checkout["exit_code"], "steps": steps}

        after = run_step("git_head_after", [*git_cmd, "rev-parse", "--short", "HEAD"])
    else:
        fetch = run_step("git_fetch", [*git_cmd, "fetch", "-q", "origin", "main"])
        if fetch["exit_code"] != 0:
            return {"ok": False, "exit_code": fetch["exit_code"], "steps": steps}
        pull = run_step("git_pull", [*git_cmd, "pull", "-q", "--ff-only", "origin", "main"])
        if pull["exit_code"] != 0:
            return {"ok": False, "exit_code": pull["exit_code"], "steps": steps}
        after = run_step("git_head_after", [*git_cmd, "rev-parse", "--short", "HEAD"])

    if payload.service_image_tag:
        code = (
            "import pathlib,sys\n"
            "path=pathlib.Path(sys.argv[1])\n"
            "tag=sys.argv[2]\n"
            "key='EMBODY_SERVICE_IMAGE_TAG'\n"
            "lines=path.read_text(encoding='utf-8').splitlines(True) if path.exists() else []\n"
            "out=[]\n"
            "found=False\n"
            "for line in lines:\n"
            "    if line.startswith(f'{key}='):\n"
            "        out.append(f'{key}={tag}\\n')\n"
            "        found=True\n"
            "    else:\n"
            "        out.append(line)\n"
            "if not found:\n"
            "    if out and not out[-1].endswith('\\n'):\n"
            "        out[-1]=out[-1]+'\\n'\n"
            "    out.append(f'{key}={tag}\\n')\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(''.join(out), encoding='utf-8')\n"
        )
        set_tag = run_step("set_service_image_tag", ["python3", "-c", code, env_file, payload.service_image_tag])
        if set_tag["exit_code"] != 0:
            return {"ok": False, "exit_code": set_tag["exit_code"], "steps": steps}

    if payload.apply:
        _detect_compose_identity()
        host_project = (POWER_PROJECT_NAME or os.environ.get("COMPOSE_PROJECT_NAME") or "unreal_vtuber").strip()
        host_project = _validate_compose_project_name(host_project)
        compose_file = f"{project_dir}/docker-compose.unreal.yml"
        power_state = _read_power_state()

        containers = []
        try:
            containers = _list_project_containers(host_project)
        except Exception:  # pragma: no cover - defensive
            containers = []

        existing_services: set[str] = set()
        running_game: list[str] = []
        base_game_running = False
        want_recreate_game = payload.recreate_game or payload.recreate_all
        for container in containers:
            labels = getattr(container, "labels", {}) or {}
            service = (labels.get("com.docker.compose.service") or "").strip()
            if service:
                existing_services.add(service)
            if service == "unreal-game":
                try:
                    container.reload()
                except Exception:  # pragma: no cover - defensive
                    pass
                status = getattr(container, "status", "")
                if status == "running":
                    base_game_running = True
                    if want_recreate_game:
                        running_game.append(getattr(container, "name", "<unknown>"))

        if want_recreate_game and running_game:
            raise HTTPException(
                status_code=409,
                detail=(
                    "refusing to recreate unreal-game while running: "
                    f"{', '.join(sorted(set(running_game)))} (sleep first)"
                ),
            )

        excluded = {POWER_SELF_SERVICE, "orchestrator-edge-rotator"}
        if not want_recreate_game:
            excluded.add("unreal-game")
        ordered = [
            "turn-server",
            "unreal-signaling",
            "vtuber-script-runner",
            "recorder-control",
            "vtuber-watchdog",
            "vtuber-auto-updater",
            "orchestrator-registration",
        ]
        if payload.recreate_all:
            # Full stack recreate: pull/recreate every service we currently have running (except
            # the caller + executor). Avoid pulling the game image (potentially large); only recreate it.
            excluded_pull = set(excluded)
            excluded_pull.add("unreal-game")

            services_pull = [svc for svc in ordered if svc in existing_services and svc not in excluded_pull]
            for svc in sorted(existing_services):
                if svc in excluded_pull or svc in services_pull:
                    continue
                services_pull.append(svc)

            services_recreate = [svc for svc in ordered if svc in existing_services and svc not in excluded]
            for svc in sorted(existing_services):
                if svc in excluded or svc in services_recreate:
                    continue
                services_recreate.append(svc)
        else:
            if existing_services:
                services_pull = [svc for svc in ordered if svc in existing_services and svc not in excluded]
            else:
                services_pull = [
                    svc
                    for svc in ("turn-server", "vtuber-auto-updater", "orchestrator-registration")
                    if svc not in excluded
                ]

            # Avoid pulling the game image (potentially large). Only recreate it.
            services_recreate = list(services_pull)
            if want_recreate_game and "unreal-game" not in services_recreate:
                services_recreate.append("unreal-game")

        # If the stack is "awake", avoid trying to start base port-binding services when those host
        # ports are already owned by another compose project (e.g. cluster-mode instances vtuber-*) or
        # any other container. This prevents apply=true from failing on cluster boxes with port conflicts
        # (8080/7777/9877/8889, etc).
        #
        # When the base stack is sleeping, we use `docker compose up --no-start` which is safe to recreate
        # even port-binding services. So only apply this filter when we would otherwise start them.
        if (power_state.state != "sleeping") and (not want_recreate_game):
            conflicts: dict[int, str] = {}
            try:
                conflicts = _docker_port_conflicts({8080, 8888, 7777, 9877, 8889}, ignore_project=host_project)
            except Exception:  # pragma: no cover - best-effort
                conflicts = {}

            if conflicts:
                skip = {
                    "unreal-signaling",
                    "unreal-game",
                    "vtuber-script-runner",
                    "recorder-control",
                    "orchestrator-registration",
                }
                services_recreate = [svc for svc in services_recreate if svc not in skip]

        if services_pull:
            run_step(
                "compose_pull",
                [
                    "docker",
                    "compose",
                    "-p",
                    host_project,
                    "--project-directory",
                    project_dir,
                    "--env-file",
                    env_file,
                    "-f",
                    compose_file,
                    "pull",
                    *services_pull,
                ],
            )
        if services_recreate:
            recreate_args = [
                "docker",
                "compose",
                "-p",
                host_project,
                "--project-directory",
                project_dir,
                "--env-file",
                env_file,
                "-f",
                compose_file,
                "up",
            ]
            if power_state.state == "sleeping":
                recreate_args.append("--no-start")
            else:
                recreate_args.append("-d")
            recreate_args.extend(["--no-deps", "--force-recreate", *services_recreate])
            run_step("compose_recreate", recreate_args)

        compose_base = [
            "docker",
            "compose",
            "-p",
            host_project,
            "--project-directory",
            project_dir,
            "--env-file",
            env_file,
            "-f",
            compose_file,
        ]

        if payload.recreate_orchestrator_health:
            # Schedule a self-recreate AFTER returning (and after a small delay),
            # otherwise the HTTP response can get cut off mid-flight.
            self_service = (POWER_SELF_SERVICE or "orchestrator-health").strip() or "orchestrator-health"
            log_path = "/var/lib/vtuber/power-state/ops-recreate-orchestrator-health.log"
            pull_cmd = " ".join(shlex.quote(arg) for arg in [*compose_base, "pull", self_service])
            up_cmd = " ".join(
                shlex.quote(arg) for arg in [*compose_base, "up", "-d", "--no-deps", "--force-recreate", self_service]
            )
            shell_cmd = f"sleep 2; {pull_cmd} && {up_cmd}"

            # Run the self-recreate asynchronously inside the executor container.
            # Uses start_new_session=True to detach from the exec_run lifecycle.
            code = (
                "import subprocess,sys\n"
                "log=sys.argv[1]\n"
                "cmd=sys.argv[2:]\n"
                "f=open(log,'ab', buffering=0)\n"
                "subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)\n"
                "print('scheduled')\n"
            )
            run_step(
                "schedule_recreate_orchestrator_health",
                ["python3", "-c", code, log_path, "bash", "-lc", shell_cmd],
            )

        if payload.recreate_orchestrator_edge_rotator:
            edge_service = "orchestrator-edge-rotator"
            log_path = "/var/lib/vtuber/power-state/ops-recreate-orchestrator-edge-rotator.log"
            pull_cmd = " ".join(shlex.quote(arg) for arg in [*compose_base, "pull", edge_service])
            up_cmd = " ".join(
                shlex.quote(arg) for arg in [*compose_base, "up", "-d", "--no-deps", "--force-recreate", edge_service]
            )
            shell_cmd = f"sleep 2; ({pull_cmd} && {up_cmd}) >> {shlex.quote(log_path)} 2>&1"

            helper_image = ""
            try:
                helper_image = (getattr(getattr(executor, "image", None), "id", "") or "").strip()
            except Exception:
                helper_image = ""
            if not helper_image:
                helper_image = (
                    "ghcr.io/its-define/unreal_vtuber/orchestrator-edge-rotator:"
                    f"{payload.service_image_tag or os.environ.get('EMBODY_SERVICE_IMAGE_TAG', 'latest')}"
                )

            helper_name = f"vtuber-ops-recreate-edge-rotator-{int(time.time())}"
            run_step(
                "schedule_recreate_orchestrator_edge_rotator",
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    helper_name,
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    "-v",
                    f"{project_dir}:{project_dir}",
                    "-v",
                    "/var/lib/vtuber/power-state:/var/lib/vtuber/power-state",
                    "-w",
                    project_dir,
                    helper_image,
                    "sh",
                    "-lc",
                    shell_cmd,
                ],
            )

    return {
        "ok": True,
        "exit_code": 0,
        "before": (before.get("stdout") or "").strip() or None,
        "after": (after.get("stdout") or "").strip() or None,
        "steps": steps,
    }


@app.post("/ops/rollout")
def ops_rollout(
    payload: OpsRolloutRequest,
    request: Request,
    _: Any = Depends(_require_ops_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: load a new encrypted game image via a Payments lease.

    By default this only loads the image (cluster-safe; no restarts). Optionally, it can force-recreate stopped
    game containers so the next wake/start uses the updated image.
    """
    project_dir = _cluster_project_dir()
    if not project_dir:
        raise HTTPException(status_code=500, detail="invalid ORCHESTRATOR_PROJECT_DIR")

    if payload.stage_only and payload.recreate_stopped:
        raise HTTPException(status_code=400, detail="stage_only cannot be combined with recreate_stopped")
    if payload.skip_download and payload.stage_only:
        raise HTTPException(status_code=400, detail="skip_download and stage_only are mutually exclusive")
    if payload.skip_download and not payload.recreate_stopped:
        raise HTTPException(status_code=400, detail="skip_download requires recreate_stopped=true")

    payments_url = (payload.payments_api_url or os.environ.get("PAYMENTS_API_URL") or "").strip()
    if not payments_url:
        raise HTTPException(status_code=400, detail="payments_api_url is required (or set PAYMENTS_API_URL)")
    if "\x00" in payments_url or "\n" in payments_url or "\r" in payments_url:
        raise HTTPException(status_code=400, detail="payments_api_url contains invalid characters")

    image_ref = (payload.image_ref or "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1").strip()
    if "\x00" in image_ref or "\n" in image_ref or "\r" in image_ref:
        raise HTTPException(status_code=400, detail="image_ref contains invalid characters")

    running = []
    try:
        for container in docker_client.containers.list(
            all=True, filters={"label": ["com.docker.compose.service=unreal-game"]}
        ):
            try:
                container.reload()
            except Exception:  # pragma: no cover - defensive
                pass
            if getattr(container, "status", "") == "running":
                running.append(getattr(container, "name", ""))
    except Exception:  # pragma: no cover - defensive
        running = []
    if running and (not payload.stage_only):
        raise HTTPException(status_code=409, detail=f"refusing rollout while unreal-game is running: {', '.join(running)}")

    executor = _cluster_executor_container()
    game_image = _detect_game_image_ref()

    free_bytes = None
    if (not payload.skip_download) and payload.min_free_gb > 0:
        free_bytes = _executor_disk_free_bytes(executor, project_dir)
        if free_bytes is not None:
            want = payload.min_free_gb * 1024 * 1024 * 1024
            if free_bytes < want:
                raise HTTPException(
                    status_code=507,
                    detail=(
                        f"insufficient disk space on project filesystem: free={free_bytes}B want>={want}B "
                        f"(min_free_gb={payload.min_free_gb})"
                    ),
                )

    out: dict[str, Any] = {
        "ok": True,
        "mode": "stage" if payload.stage_only else ("apply" if payload.recreate_stopped else "load"),
        "disk_free_bytes": free_bytes,
        "game_image": game_image,
    }

    state: dict[str, Any] = {
        "status": "unknown",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "image_ref": image_ref,
        "payments_api_url": payments_url,
        "game_image": game_image,
    }

    if payload.skip_download:
        existing = _read_json_file(ROLLOUT_STATE_FILE)
        if not existing or existing.get("status") not in ("staged", "applied"):
            raise HTTPException(status_code=409, detail="no staged rollout found (run /ops/rollout with stage_only first)")
        if (existing.get("image_ref") or "").strip() and (existing.get("image_ref") or "").strip() != image_ref:
            raise HTTPException(status_code=409, detail="staged rollout image_ref does not match request image_ref")
        state = existing
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["loaded_image_id"] = _docker_image_id(game_image)
        _write_json_file_atomic(ROLLOUT_STATE_FILE, state)
    else:
        token_path = "/root/.embody/orch-license-token.txt"
        cmd = [
            "bash",
            f"{project_dir}/tools/encrypted-game-image/consume.sh",
            "--payments-api-url",
            payments_url,
            "--image-ref",
            image_ref,
            "--orch-token-file",
            token_path,
        ]
        download = _cluster_executor_exec(executor, cmd)
        download["stdout"] = _tail(download.get("stdout", ""))
        download["stderr"] = _tail(download.get("stderr", ""))
        download["ok"] = download.get("exit_code") == 0
        out["download"] = download
        if not download["ok"]:
            out["ok"] = False
            state["status"] = "error"
            state["detail"] = "download/load failed"
            _write_json_file_atomic(ROLLOUT_STATE_FILE, state)
            return out

        state["status"] = "staged"
        state["loaded_image_id"] = _docker_image_id(game_image)
        _write_json_file_atomic(ROLLOUT_STATE_FILE, state)

    if payload.recreate_stopped:
        state = _read_json_file(ROLLOUT_STATE_FILE) or state
        state["apply_requested_at"] = datetime.now(timezone.utc).isoformat()
        recreate = _recreate_stopped_game_projects(project_dir=project_dir)
        out["recreate"] = recreate
        state["status"] = "applied"
        state["applied_at"] = datetime.now(timezone.utc).isoformat()
        state["loaded_image_id"] = _docker_image_id(game_image)
        _write_json_file_atomic(ROLLOUT_STATE_FILE, state)

    return out


@app.post("/ops/pull-image")
def ops_pull_image(
    payload: OpsPullImageRequest,
    request: Request,
    _: Any = Depends(_require_ops_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: docker pull an image ref (useful for unencrypted game updates)."""

    image = payload.image.strip()
    if not image or "\x00" in image or "\n" in image or "\r" in image or " " in image:
        raise HTTPException(status_code=400, detail="invalid image ref")

    executor = _cluster_executor_container()
    out = _cluster_executor_exec(executor, ["docker", "pull", image])
    out["stdout"] = _tail(out.get("stdout", ""))
    out["stderr"] = _tail(out.get("stderr", ""))
    out["ok"] = out.get("exit_code") == 0
    return out


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
        try:
            statuses = _sleep_all_containers(reason=payload.reason)
            logger.info("Sleep requested; stopped=%s", statuses)
        except Exception as exc:  # noqa: BLE001
            # Treat power state as a desired state. If stopping containers fails, we still want the
            # caller to get a consistent response (200 + the persisted state) and debug via /meta.
            logger.exception("Sleep requested but stop failed: %s", exc)
        return state

    # wake
    _cancel_auto_sleep_timer()
    awake_until: Optional[datetime] = None
    if payload.awake_seconds:
        awake_until = datetime.now(timezone.utc) + timedelta(seconds=payload.awake_seconds)
    state = _write_power_state("awake", payload.reason, awake_until=awake_until)
    try:
        statuses = _wake_all_containers(timeout_seconds=120)
        logger.info("Wake requested; started=%s", statuses)
    except Exception as exc:  # noqa: BLE001
        # Avoid returning 500 after persisting "awake" state, which is confusing for remote callers.
        # Debug actual container state via /meta.
        logger.exception("Wake requested but start failed: %s", exc)
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
        try:
            _sleep_all_containers(reason=payload.reason, project_name=project)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Project sleep requested but stop failed (project=%s): %s", project, exc)
        return _power_state_from_project(project)

    # wake
    _cancel_project_auto_sleep_timer(project)
    awake_until: Optional[datetime] = None
    if payload.awake_seconds:
        awake_until = datetime.now(timezone.utc) + timedelta(seconds=payload.awake_seconds)
    if payload.reason:
        _PROJECT_LAST_REASON[project] = payload.reason
    try:
        _wake_all_containers(timeout_seconds=120, project_name=project)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Project wake requested but start failed (project=%s): %s", project, exc)
    if awake_until is not None:
        _PROJECT_AWAKE_UNTIL[project] = awake_until
        _schedule_project_auto_sleep(payload.awake_seconds or 0, project=project, reason="auto-sleep after wake TTL")
    return _power_state_from_project(project)


@app.post("/cluster/deploy")
def cluster_deploy_instance(
    payload: ClusterDeployRequest,
    request: Request,
    _: Any = Depends(_require_cluster_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: create/start a cluster-mode avatar compose project (vtuber-<slug>)."""
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
    if payload.console_variables_file:
        env["VTUBER_CONSOLE_VARIABLES_FILE"] = _validate_compose_project_relpath(
            payload.console_variables_file, field="console_variables_file"
        )
    if payload.game_user_settings_file:
        env["VTUBER_GAME_USER_SETTINGS_FILE"] = _validate_compose_project_relpath(
            payload.game_user_settings_file, field="game_user_settings_file"
        )
    if payload.embody_extra_args:
        extra_args = payload.embody_extra_args.strip()
        if "\x00" in extra_args or "\n" in extra_args or "\r" in extra_args:
            raise HTTPException(status_code=400, detail="embody_extra_args contains invalid characters")
        env["EMBODY_EXTRA_ARGS"] = extra_args
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
        "overrides": {
            "console_variables_file": (payload.console_variables_file or "").strip() or None,
            "game_user_settings_file": (payload.game_user_settings_file or "").strip() or None,
            "embody_extra_args": (payload.embody_extra_args or "").strip() or None,
        },
        "ports": ports,
        "subnet": subnet,
        "gateway": gateway,
    }


@app.post("/cluster/down")
def cluster_down_instance(
    payload: ClusterDownRequest,
    request: Request,
    _: Any = Depends(_require_cluster_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: stop/remove a cluster-mode avatar compose project (vtuber-<slug>)."""
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
