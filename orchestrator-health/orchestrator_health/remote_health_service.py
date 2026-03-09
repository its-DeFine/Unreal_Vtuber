"""Expose local Docker service health over HTTP for remote monitoring and power control."""
from __future__ import annotations

import json
import hashlib
import hmac
import io
import logging
import os
import ipaddress
import re
import shlex
import tarfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Optional
from urllib.parse import urlparse

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


POWER_ALLOWED_IPS = _parse_ip_list("POWER_ALLOWED_IPS")
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
_SECRETISH_ENV_NAME_RE = re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|PRIVATE[_-]?KEY)", re.IGNORECASE)


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


def _meta_unreal_game_log_tail_lines() -> int:
    raw = (os.environ.get("META_UNREAL_GAME_LOG_TAIL_LINES", "80") or "").strip()
    try:
        value = int(raw)
    except Exception:
        value = 80
    if value < 1:
        value = 1
    if value > 200:
        value = 200
    return value


def _meta_unreal_game_log_tail_chars() -> int:
    raw = (os.environ.get("META_UNREAL_GAME_LOG_TAIL_CHARS", "12000") or "").strip()
    try:
        value = int(raw)
    except Exception:
        value = 12_000
    if value < 256:
        value = 256
    if value > 50_000:
        value = 50_000
    return value


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
    ops_allow_cidrs: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional exact CIDR/IP allowlist for remote ops access. When provided, writes "
            "EDGE_OPS_ALLOW_CIDRS, EDGE_POWER_EXTRA_CIDRS, EDGE_FIREWALL_EXTRA_CIDRS and POWER_ALLOWED_IPS "
            "in the host .env. If apply=true, also auto-recreates orchestrator-health + edge-rotator."
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

        if self.ops_allow_cidrs is not None:
            normalized: list[str] = []
            seen: set[str] = set()
            for raw in self.ops_allow_cidrs:
                token = (raw or "").strip()
                if not token:
                    continue
                try:
                    net = ipaddress.ip_network(token, strict=False)
                except ValueError as exc:
                    raise ValueError("ops_allow_cidrs entries must be valid IPv4/IPv6 CIDR or IP") from exc
                canon = str(net)
                if canon in seen:
                    continue
                seen.add(canon)
                normalized.append(canon)
            self.ops_allow_cidrs = normalized or None

        return self


class OpsRolloutRequest(BaseModel):
    payments_api_url: Optional[str] = Field(default=None, description="Payments backend base URL override.")
    image_ref: Optional[str] = Field(default=None, description="Payments license image_ref override (enc-v1, etc).")
    orch_token: Optional[str] = Field(
        default=None,
        description="Optional ephemeral orchestrator token override injected into the executor environment.",
    )
    stream_no_cache: bool = Field(
        default=False,
        description=(
            "If true, request the encrypted artifact stream/no-cache consume path. "
            "Disables cached-artifact resume seeding for this rollout."
        ),
    )
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
    cleanup_stopped_game: bool = Field(
        default=False,
        description=(
            "If true, and recreate_stopped=true, remove stopped unreal-game containers and the current game image "
            "before loading the next encrypted image."
        ),
    )
    prune_unused_docker: bool = Field(
        default=False,
        description=(
            "If true, and cleanup_stopped_game=true, prune stopped containers and unused images before loading "
            "the next encrypted image."
        ),
    )

    @model_validator(mode="after")
    def _validate_rollout_args(self) -> "OpsRolloutRequest":
        if self.orch_token is not None:
            if any(ord(ch) < 32 or ord(ch) == 127 for ch in self.orch_token):
                raise ValueError("orch_token contains invalid control characters")
            self.orch_token = self.orch_token.strip()
            if not self.orch_token:
                self.orch_token = None
        return self


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
    # Keep legacy handler semantics, but enforce explicit allowlist presence.
    _require_auth_strict(request)


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
    allowlist, _source = _resolve_power_allowlist()
    return allowlist


def _derive_legacy_power_allowlist() -> list[str]:
    # Backward-compatible baseline for older deployments that did not set POWER_ALLOWED_IPS.
    # Keep this narrow: localhost + explicit control-plane CIDRs/IP.
    derived = ["127.0.0.1/32", "::1/128"]

    raw_extra = (os.environ.get("EDGE_POWER_EXTRA_CIDRS") or "").strip()
    if raw_extra:
        for token in [part.strip() for part in raw_extra.split(",") if part.strip()]:
            try:
                derived.append(str(ipaddress.ip_network(token, strict=False)))
            except ValueError:
                continue

    payments_url = (os.environ.get("PAYMENTS_API_URL") or "").strip()
    if payments_url:
        candidate = payments_url if "://" in payments_url else f"http://{payments_url}"
        try:
            host = (urlparse(candidate).hostname or "").strip()
            if host:
                ip = ipaddress.ip_address(host)
                if ip.version == 4:
                    derived.append(f"{ip}/32")
                else:
                    derived.append(f"{ip}/128")
        except Exception:
            pass

    deduped: list[str] = []
    seen: set[str] = set()
    for token in derived:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _resolve_power_allowlist() -> tuple[list[str], str]:
    if POWER_ALLOWED_IPS_FILE is None:
        if POWER_ALLOWED_IPS:
            return POWER_ALLOWED_IPS, "env"
        return _derive_legacy_power_allowlist(), "derived"
    try:
        raw = POWER_ALLOWED_IPS_FILE.read_text().strip()
    except FileNotFoundError:
        if POWER_ALLOWED_IPS:
            return POWER_ALLOWED_IPS, "env_file_missing"
        return _derive_legacy_power_allowlist(), "derived_file_missing"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read POWER_ALLOWED_IPS_FILE=%s: %s", POWER_ALLOWED_IPS_FILE, exc)
        if POWER_ALLOWED_IPS:
            return POWER_ALLOWED_IPS, "env_file_error"
        return _derive_legacy_power_allowlist(), "derived_file_error"

    entries = [addr.strip() for addr in raw.split(",") if addr.strip()]
    if entries:
        return entries, "file"
    if POWER_ALLOWED_IPS:
        return POWER_ALLOWED_IPS, "env"
    return _derive_legacy_power_allowlist(), "derived"


def _power_allowlist_diagnostics() -> dict[str, Any]:
    allowlist, source = _resolve_power_allowlist()
    deduped: list[str] = []
    seen: set[str] = set()
    for token in allowlist:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return {
        "power_allowlist_source": source,
        "power_allowlist_count": len(deduped),
    }


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


def _redact_sensitive_text(text: str) -> str:
    if not text:
        return ""
    out = text
    sensitive_values: list[str] = []
    for key, value in os.environ.items():
        if not value or len(value) < 6:
            continue
        if _SECRETISH_ENV_NAME_RE.search(key):
            sensitive_values.append(value)
    for value in sorted(set(sensitive_values), key=len, reverse=True):
        out = out.replace(value, "[redacted]")
    out = re.sub(r"(?im)\b(authorization\s*:\s*bearer\s+)[^\s]+", r"\1[redacted]", out)
    out = re.sub(
        r"(?im)\b((?:api[_-]?key|token|secret|password|passwd|access[_-]?key|private[_-]?key)\s*[=:]\s*)([^\s]+)",
        r"\1[redacted]",
        out,
    )
    return out


ROLLOUT_ACTIVE_STATUSES = frozenset({"queued", "downloading", "decrypting", "loading", "applying"})
ROLLOUT_TERMINAL_STATUSES = frozenset({"staged", "applied", "failed"})
ROLLOUT_STATUS_DETAILS = {
    "queued": "rollout job queued",
    "downloading": "requesting decryption lease / downloading artifact",
    "decrypting": "artifact stream is being decrypted",
    "loading": "docker image load in progress",
    "staged": "encrypted image loaded and staged",
    "applying": "recreating stopped game projects",
    "applied": "staged image applied to stopped game projects",
}
_ROLLOUT_JOB_LOCK = threading.Lock()
_ROLLOUT_JOB_THREAD: threading.Thread | None = None
_ROLLOUT_JOB_ID: str | None = None
_ROLLOUT_RESUME_FIELDS = frozenset(
    {
        "artifact_local_path",
        "artifact_partial_path",
        "artifact_cache_dir",
        "artifact_download_action",
        "artifact_total_bytes",
        "artifact_downloaded_bytes",
        "artifact_download_percent",
        "artifact_resumed",
        "artifact_resume_from_bytes",
        "downloaded_bytes",
        "progress_percent",
        "can_resume",
        "loaded_image_id",
        "lease_id",
        "work_dir",
    }
)


def _rollout_is_active_status(status: str) -> bool:
    return status in ROLLOUT_ACTIVE_STATUSES


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(str(value).strip()), 2)
    except Exception:
        return None


def _bool_or_none(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    clean = str(value).strip().lower()
    if clean in {"1", "true", "yes", "y", "on"}:
        return True
    if clean in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _rollout_can_resume(
    state: dict[str, Any],
    *,
    downloaded_bytes: Optional[int],
    artifact_total_bytes: Optional[int],
) -> bool:
    explicit = _bool_or_none(state.get("can_resume"))
    if explicit is not None:
        return explicit

    partial_path = str(state.get("artifact_partial_path") or "").strip()
    if partial_path:
        try:
            if Path(partial_path).exists() and Path(partial_path).stat().st_size > 0:
                return True
        except Exception:
            pass

    artifact_path = str(state.get("artifact_local_path") or "").strip()
    if artifact_path:
        try:
            size = Path(artifact_path).stat().st_size
            if size > 0 and (artifact_total_bytes is None or artifact_total_bytes <= 0 or size == artifact_total_bytes):
                return True
        except Exception:
            pass

    if downloaded_bytes is None:
        downloaded_bytes = _int_or_none(state.get("artifact_downloaded_bytes"))
    if downloaded_bytes is None:
        downloaded_bytes = _int_or_none(state.get("downloaded_bytes"))
    if downloaded_bytes is None or downloaded_bytes <= 0:
        return False
    if artifact_total_bytes is None:
        return True
    return downloaded_bytes <= artifact_total_bytes


def _normalize_rollout_progress(state: dict[str, Any]) -> dict[str, Any]:
    out = dict(state)
    artifact_total_bytes = _int_or_none(out.get("artifact_total_bytes"))
    downloaded_bytes = _int_or_none(out.get("downloaded_bytes"))
    if downloaded_bytes is None:
        downloaded_bytes = _int_or_none(out.get("artifact_downloaded_bytes"))
    if downloaded_bytes is None:
        downloaded_bytes = 0

    progress_percent = _float_or_none(out.get("progress_percent"))
    if progress_percent is None:
        progress_percent = _float_or_none(out.get("artifact_download_percent"))
    if progress_percent is None and artifact_total_bytes and artifact_total_bytes > 0:
        progress_percent = round(min(100.0, (float(downloaded_bytes) * 100.0) / float(artifact_total_bytes)), 2)
    if progress_percent is None:
        progress_percent = 0.0

    out["artifact_total_bytes"] = artifact_total_bytes
    out["downloaded_bytes"] = downloaded_bytes
    out["progress_percent"] = progress_percent
    out["can_resume"] = _rollout_can_resume(
        out,
        downloaded_bytes=downloaded_bytes,
        artifact_total_bytes=artifact_total_bytes,
    )
    return out


def _rollout_resume_fields(
    existing: Optional[dict[str, Any]],
    *,
    image_ref: str,
    stream_no_cache: bool = False,
) -> dict[str, Any]:
    if not existing:
        return {}
    if str(existing.get("image_ref") or "").strip() != image_ref:
        return {}

    seeded: dict[str, Any] = {}
    if not stream_no_cache:
        normalized = _normalize_rollout_progress(existing)
        for key in _ROLLOUT_RESUME_FIELDS:
            value = normalized.get(key)
            if value is not None:
                seeded[key] = value

    previous_job_id = str(existing.get("job_id") or "").strip()
    if previous_job_id:
        seeded["resume_from_job_id"] = previous_job_id
    return seeded


def _rollout_work_dir(job_id: str) -> Path:
    return ROLLOUT_STATE_FILE.parent / "rollout-work" / job_id


def _read_rollout_state_with_runtime() -> Optional[dict[str, Any]]:
    state = _read_json_file(ROLLOUT_STATE_FILE)
    if state is None:
        return None

    status = str(state.get("status") or "").strip()
    with _ROLLOUT_JOB_LOCK:
        global _ROLLOUT_JOB_THREAD, _ROLLOUT_JOB_ID
        thread = _ROLLOUT_JOB_THREAD
        matches_runtime = bool(thread is not None and _ROLLOUT_JOB_ID and state.get("job_id") == _ROLLOUT_JOB_ID)
        worker_active = bool(matches_runtime and (thread.is_alive() or _rollout_is_active_status(status)))
        if matches_runtime and thread is not None and (not thread.is_alive()) and (not _rollout_is_active_status(status)):
            _ROLLOUT_JOB_THREAD = None
            _ROLLOUT_JOB_ID = None

    out = _normalize_rollout_progress(state)
    out["worker_active"] = worker_active
    out["active"] = _rollout_is_active_status(status)
    out["terminal"] = status in ROLLOUT_TERMINAL_STATUSES
    return out


def _init_rollout_state(
    *,
    job_id: str,
    mode: str,
    image_ref: str,
    payments_url: str,
    game_image: str,
    disk_free_bytes: Optional[int],
    stage_only: bool,
    skip_download: bool,
    stream_no_cache: bool,
    recreate_stopped: bool,
    cleanup_stopped_game: bool,
    prune_unused_docker: bool,
    no_verify: bool,
    loaded_image_id: Optional[str] = None,
    resume_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    state: dict[str, Any] = {
        "job_id": job_id,
        "status": "queued",
        "detail": ROLLOUT_STATUS_DETAILS["queued"],
        "mode": mode,
        "image_ref": image_ref,
        "payments_api_url": payments_url,
        "game_image": game_image,
        "disk_free_bytes": disk_free_bytes,
        "stage_only": stage_only,
        "skip_download": skip_download,
        "stream_no_cache": stream_no_cache,
        "recreate_stopped": recreate_stopped,
        "cleanup_stopped_game": cleanup_stopped_game,
        "prune_unused_docker": prune_unused_docker,
        "no_verify": no_verify,
        "requested_at": now,
        "updated_at": now,
        "history": [{"status": "queued", "at": now}],
        "active": True,
        "terminal": False,
    }
    if resume_state:
        state.update(resume_state)
    state["downloaded_bytes"] = _int_or_none(state.get("downloaded_bytes")) or 0
    state["progress_percent"] = _float_or_none(state.get("progress_percent")) or 0.0
    state["can_resume"] = _rollout_can_resume(
        state,
        downloaded_bytes=_int_or_none(state.get("downloaded_bytes")),
        artifact_total_bytes=_int_or_none(state.get("artifact_total_bytes")),
    )
    if loaded_image_id:
        state["loaded_image_id"] = loaded_image_id
    return state


def _update_rollout_state(
    job_id: str,
    *,
    status: Optional[str] = None,
    detail: Optional[str] = None,
    **fields: Any,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with _ROLLOUT_JOB_LOCK:
        state = _read_json_file(ROLLOUT_STATE_FILE) or {"job_id": job_id, "history": []}
        state["job_id"] = job_id

        if status is not None:
            history = state.get("history")
            if not isinstance(history, list):
                history = []
            current_status = str(state.get("status") or "").strip()
            if current_status != status:
                history.append({"status": status, "at": now})
            state["history"] = history[-32:]
            state["status"] = status
            state["active"] = _rollout_is_active_status(status)
            state["terminal"] = status in ROLLOUT_TERMINAL_STATUSES
            if status == "failed":
                state["failed_at"] = now
                state["completed_at"] = now
            elif status in ROLLOUT_TERMINAL_STATUSES:
                state["completed_at"] = now
                state.pop("failed_at", None)

        if detail is not None:
            state["detail"] = detail

        state.update(fields)
        state["updated_at"] = now
        _write_json_file_atomic(ROLLOUT_STATE_FILE, state)
        return state


def _fail_rollout_state(job_id: str, detail: str, **fields: Any) -> dict[str, Any]:
    return _update_rollout_state(job_id, status="failed", detail=detail, **fields)


def _rollout_status_from_output_line(line: str) -> Optional[str]:
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line or "")
    clean = clean.replace("\r", "\n").strip()
    if not clean:
        return None
    if "LOADING" in clean:
        return "loading"
    if "Validating artifact header" in clean:
        return "decrypting"
    if (
        "Downloading artifact" in clean
        or "Requesting a decryption lease from Payments" in clean
        or "Retrying decryption lease request" in clean
    ):
        return "downloading"
    return None


def _emit_rollout_statuses_from_output(
    out: dict[str, Any],
    *,
    on_status: Optional[Callable[[str], None]] = None,
) -> None:
    if on_status is None:
        return
    for text in (str(out.get("stdout") or ""), str(out.get("stderr") or "")):
        for line in text.replace("\r", "\n").splitlines():
            status = _rollout_status_from_output_line(line)
            if status:
                on_status(status)


def _consume_exec_stream_text(
    chunk: str,
    *,
    remainder: str,
    on_status: Optional[Callable[[str], None]] = None,
) -> tuple[str, str]:
    text = (remainder + chunk).replace("\r", "\n")
    lines = text.splitlines(keepends=True)
    next_remainder = ""
    if lines and not lines[-1].endswith("\n"):
        next_remainder = lines.pop()
    if on_status is not None:
        for line in lines:
            status = _rollout_status_from_output_line(line)
            if status:
                on_status(status)
    return "".join(lines), next_remainder


def _cluster_executor_exec_stream(
    executor: Any,
    cmd: list[str],
    *,
    env: Optional[dict[str, str]] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    api = getattr(getattr(executor, "client", None), "api", None) or getattr(docker_client, "api", None)
    executor_id = getattr(executor, "id", None)
    if api is None or not executor_id:
        out = _cluster_executor_exec(executor, cmd, env=env)
        _emit_rollout_statuses_from_output(out, on_status=on_status)
        return out

    try:
        created = api.exec_create(
            executor_id,
            cmd,
            stdout=True,
            stderr=True,
            stdin=False,
            tty=False,
            environment=env or None,
        )
        exec_id = created["Id"] if isinstance(created, dict) else created
        stream = api.exec_start(exec_id, stream=True, demux=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"exec failed: {exc}") from exc

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    stdout_remainder = ""
    stderr_remainder = ""

    try:
        for item in stream:
            stdout_b: bytes | None
            stderr_b: bytes | None
            if isinstance(item, tuple):
                stdout_b, stderr_b = item
            else:
                stdout_b, stderr_b = item, None

            if stdout_b:
                kept, stdout_remainder = _consume_exec_stream_text(
                    stdout_b.decode("utf-8", errors="replace"),
                    remainder=stdout_remainder,
                    on_status=on_status,
                )
                if kept:
                    stdout_parts.append(kept)
            if stderr_b:
                kept, stderr_remainder = _consume_exec_stream_text(
                    stderr_b.decode("utf-8", errors="replace"),
                    remainder=stderr_remainder,
                    on_status=on_status,
                )
                if kept:
                    stderr_parts.append(kept)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"exec stream failed: {exc}") from exc

    if stdout_remainder:
        if on_status is not None:
            status = _rollout_status_from_output_line(stdout_remainder)
            if status:
                on_status(status)
        stdout_parts.append(stdout_remainder)
    if stderr_remainder:
        if on_status is not None:
            status = _rollout_status_from_output_line(stderr_remainder)
            if status:
                on_status(status)
        stderr_parts.append(stderr_remainder)

    try:
        inspected = api.exec_inspect(exec_id)
        exit_code = int(inspected.get("ExitCode", 1))
    except Exception:  # pragma: no cover - defensive
        exit_code = 1

    return {
        "exit_code": exit_code,
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
        "cmd": cmd,
    }


def _make_rollout_thread(**kwargs: Any) -> threading.Thread:
    job_id = str(kwargs.get("job_id") or "rollout")
    return threading.Thread(
        target=_run_rollout_job,
        kwargs=kwargs,
        name=f"rollout-{job_id[:8]}",
        daemon=True,
    )


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


def _container_log_tail(container: Any, *, tail_lines: int = 120, max_chars: int = 20_000) -> str:
    try:
        raw = container.logs(stdout=True, stderr=True, tail=tail_lines, timestamps=True)
    except Exception:  # pragma: no cover - defensive
        return ""
    if isinstance(raw, (bytes, bytearray)):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw or "")
    return _tail(_redact_sensitive_text(text), max_lines=tail_lines, max_chars=max_chars)


def _container_put_text_file(container: Any, path: str, content: str, *, mode: int = 0o755) -> None:
    normalized = path.strip()
    if not normalized.startswith("/"):
        raise ValueError("path must be absolute")
    parent = os.path.dirname(normalized)
    name = os.path.basename(normalized)
    data = content.encode("utf-8")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        info.mode = mode
        tar.addfile(info, io.BytesIO(data))
    archive.seek(0)
    ok = container.put_archive(parent, archive.read())
    if ok is False:
        raise RuntimeError(f"docker put_archive returned false for {normalized}")


def _container_diagnostics(container: Any) -> dict[str, Any]:
    meta = _container_meta(container)
    attrs = container.attrs or {}
    state = (attrs.get("State") or {}) if isinstance(attrs, dict) else {}
    health_payload = (state.get("Health") or {}) if isinstance(state, dict) else {}
    return {
        **meta,
        "running": bool(state.get("Running", False)),
        "restarting": bool(state.get("Restarting", False)),
        "oom_killed": bool(state.get("OOMKilled", False)),
        "dead": bool(state.get("Dead", False)),
        "paused": bool(state.get("Paused", False)),
        "exit_code": state.get("ExitCode"),
        "error": (state.get("Error") or "").strip() or None,
        "started_at": (state.get("StartedAt") or "").strip() or None,
        "finished_at": (state.get("FinishedAt") or "").strip() or None,
        "health_status": (health_payload.get("Status") or "").strip() or None,
        "restart_count": attrs.get("RestartCount"),
        "log_tail": _container_log_tail(container),
    }


def _patched_unreal_game_start_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

PIXEL_STREAMING_URL="${PIXEL_STREAMING_URL:-ws://127.0.0.1:8888}"
USE_XVFB="${USE_XVFB:-1}"
DISPLAY_VALUE="${DISPLAY:-:99}"
XVFB_RESOLUTION="${XVFB_RESOLUTION:-1920x1080x24}"
ULIMIT_NOFILE_VALUE="${ULIMIT_NOFILE:-1048576}"

HOST_LIBRARY_PATHS_DEFAULT="/host-libs/usr/lib/x86_64-linux-gnu:/host-libs/lib/x86_64-linux-gnu:/host-libs/usr/lib/nvidia:/host-libs/lib64:/host-libs/usr/lib64"
IFS=":" read -r -a HOST_LIBRARY_PATHS <<< "${HOST_LIB_PATHS:-$HOST_LIBRARY_PATHS_DEFAULT}"
for path in "${HOST_LIBRARY_PATHS[@]}"; do
  if [ -d "${path}" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${path}"
  fi
done

if [ -z "${VK_ICD_FILENAMES:-}" ] && [ -f /host-libs/usr/share/vulkan/icd.d/nvidia_icd.json ]; then
  export VK_ICD_FILENAMES="/host-libs/usr/share/vulkan/icd.d/nvidia_icd.json"
fi

if [ -z "${VK_LAYER_PATH:-}" ]; then
  layer_dirs=(
    "/host-libs/usr/share/vulkan/implicit_layer.d"
    "/host-libs/usr/share/vulkan/explicit_layer.d"
  )
  accumulated=()
  for dir in "${layer_dirs[@]}"; do
    if [ -d "${dir}" ]; then
      accumulated+=("${dir}")
    fi
  done
  if [ ${#accumulated[@]} -gt 0 ]; then
    export VK_LAYER_PATH="$(IFS=:; echo "${accumulated[*]}")"
  fi
fi

OPENCV_RUNTIME_DIR="/opt/embody/Engine/Plugins/Runtime/OpenCV/Binaries/ThirdParty/Linux/x86_64-unknown-linux-gnu/opencv/lib"
if [ -d "${OPENCV_RUNTIME_DIR}" ]; then
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${OPENCV_RUNTIME_DIR}"
fi

WHISPER_RUNTIME_DIR="/opt/embody/Embody/Source/ThirdParty/Lib/Linux/whisper/x64"
if [ -d "${WHISPER_RUNTIME_DIR}" ]; then
  for lib in \
    libwhisper.so \
    libggml.so \
    libggml-base.so \
    libggml-cpu.so \
    libggml-cuda.so
  do
    if [ -f "${WHISPER_RUNTIME_DIR}/${lib}" ] && [ ! -e "${WHISPER_RUNTIME_DIR}/${lib}.0" ]; then
      ln -sf "${lib}" "${WHISPER_RUNTIME_DIR}/${lib}.0" || true
    fi
  done
  if [ -f "${WHISPER_RUNTIME_DIR}/libwhisper.so" ] && [ ! -e "${WHISPER_RUNTIME_DIR}/libwhisper.so.1" ]; then
    ln -sf libwhisper.so "${WHISPER_RUNTIME_DIR}/libwhisper.so.1" || true
  fi
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}${WHISPER_RUNTIME_DIR}"
fi

xvfb_pid=""
embody_pid=""
cleanup() {
  set +e
  if [ -n "${embody_pid}" ] && kill -0 "${embody_pid}" 2>/dev/null; then
    kill "${embody_pid}" 2>/dev/null || true
    wait "${embody_pid}" 2>/dev/null || true
  fi
  if [ -n "${xvfb_pid}" ] && kill -0 "${xvfb_pid}" 2>/dev/null; then
    kill "${xvfb_pid}" 2>/dev/null || true
    wait "${xvfb_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ "${USE_XVFB}" != "0" ]; then
  mkdir -p /tmp/.X11-unix || true
  chmod 1777 /tmp/.X11-unix 2>/dev/null || true
  rm -f /tmp/.X99-lock 2>/dev/null || true
  echo "Starting Xvfb on ${DISPLAY_VALUE} with ${XVFB_RESOLUTION}"
  Xvfb "${DISPLAY_VALUE}" -screen 0 "${XVFB_RESOLUTION}" &
  xvfb_pid=$!
  export DISPLAY="${DISPLAY_VALUE}"
else
  echo "USE_XVFB=0, not starting Xvfb"
fi

ulimit -n "${ULIMIT_NOFILE_VALUE}" || true

cd /opt/embody

if [ -n "${EMBODY_EXTRA_ARGS:-}" ]; then
  # shellcheck disable=SC2086
  set -- ${EMBODY_EXTRA_ARGS} "$@"
fi

./Embody.sh -RenderOffScreen -PixelStreamingURL="${PIXEL_STREAMING_URL}" -Log "$@" &
embody_pid=$!
wait "${embody_pid}"
"""


def _unreal_game_diagnostics(*, project_name: str | None = None) -> dict[str, Any]:
    container = _find_container(POWER_GAME_SERVICE, POWER_GAME_CONTAINER or None, project_name=project_name)
    if container is None:
        return {
            "found": False,
            "detail": f"{POWER_GAME_SERVICE} container not found",
            "service": POWER_GAME_SERVICE,
            "container_name": POWER_GAME_CONTAINER or None,
            "logs_tail": "",
        }

    try:
        container.reload()
    except Exception:  # pragma: no cover - defensive
        pass

    meta = _container_meta(container)
    attrs = container.attrs or {}
    state = (attrs.get("State") or {}) if isinstance(attrs, dict) else {}
    health = (state.get("Health") or {}) if isinstance(state, dict) else {}
    restart_count_raw = attrs.get("RestartCount", 0) if isinstance(attrs, dict) else 0
    try:
        restart_count = int(restart_count_raw or 0)
    except Exception:
        restart_count = 0

    log_tail_lines = _meta_unreal_game_log_tail_lines()
    log_tail_chars = _meta_unreal_game_log_tail_chars()
    logs_tail = ""
    logs_error: Optional[str] = None
    try:
        raw_logs = container.logs(stdout=True, stderr=True, tail=log_tail_lines, timestamps=True)
        if isinstance(raw_logs, bytes):
            logs_tail = raw_logs.decode("utf-8", errors="replace")
        else:
            logs_tail = str(raw_logs or "")
        logs_tail = _tail(_redact_sensitive_text(logs_tail), max_lines=log_tail_lines, max_chars=log_tail_chars)
    except Exception as exc:  # pragma: no cover - defensive
        logs_error = str(exc)

    return {
        "found": True,
        "service": POWER_GAME_SERVICE,
        "container": {
            **meta,
            "restart_count": restart_count,
            "state": {
                "status": state.get("Status"),
                "running": state.get("Running"),
                "restarting": state.get("Restarting"),
                "oom_killed": state.get("OOMKilled"),
                "dead": state.get("Dead"),
                "exit_code": state.get("ExitCode"),
                "error": state.get("Error"),
                "started_at": state.get("StartedAt"),
                "finished_at": state.get("FinishedAt"),
                "health_status": health.get("Status"),
            },
        },
        "logs_tail": logs_tail,
        "log_tail_lines": log_tail_lines,
        "log_tail_chars": len(logs_tail),
        "logs_error": logs_error,
    }


def _hotfix_unreal_game_whisper_runtime(*, project_name: str | None = None) -> dict[str, Any]:
    container = _find_container(POWER_GAME_SERVICE, POWER_GAME_CONTAINER or None, project_name=project_name)
    if container is None:
        raise HTTPException(status_code=404, detail=f"{POWER_GAME_SERVICE} container not found")
    try:
        container.reload()
    except Exception:
        pass
    _container_put_text_file(container, "/usr/local/bin/start-embody.sh", _patched_unreal_game_start_script(), mode=0o755)
    container.restart(timeout=10)
    try:
        container.reload()
    except Exception:
        pass
    return {
        "ok": True,
        "detail": "patched start-embody.sh copied into unreal-game container and container restarted",
        "container": _container_diagnostics(container),
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


def _container_compose_project(container: Any) -> str:
    labels = ((container.attrs or {}).get("Config") or {}).get("Labels") or {}
    return str(labels.get("com.docker.compose.project") or "").strip()


def _stopped_unreal_game_containers() -> list[Any]:
    try:
        containers = docker_client.containers.list(all=True, filters={"label": ["com.docker.compose.service=unreal-game"]})
    except Exception:  # pragma: no cover - defensive
        return []

    stopped: list[Any] = []
    for container in containers:
        try:
            container.reload()
        except Exception:  # pragma: no cover - defensive
            continue
        if getattr(container, "status", "") == "running":
            continue
        stopped.append(container)
    return stopped


def _stopped_unreal_game_projects(*, containers: Optional[list[Any]] = None) -> list[str]:
    projects: set[str] = set()
    for container in containers if containers is not None else _stopped_unreal_game_containers():
        project = _container_compose_project(container)
        if project:
            projects.add(project)
    return sorted(projects)


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


def _recreate_stopped_game_projects(
    *,
    project_dir: str,
    project_names: Optional[list[str]] = None,
    project_envs: Optional[dict[str, dict[str, str]]] = None,
) -> list[dict[str, Any]]:
    _detect_compose_identity()
    host_project = (POWER_PROJECT_NAME or os.environ.get("COMPOSE_PROJECT_NAME") or "").strip()
    projects = sorted(set(project_names or _stopped_unreal_game_projects()))
    project_envs = project_envs or {}

    results: list[dict[str, Any]] = []

    for project in projects:
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
            env = project_envs.get(project) or _derive_cluster_recreate_env(project=project, project_dir=project_dir)
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


def _cleanup_stopped_game_rollout_targets(*, project_dir: str, game_image: str) -> dict[str, Any]:
    _detect_compose_identity()
    host_project = (POWER_PROJECT_NAME or os.environ.get("COMPOSE_PROJECT_NAME") or "").strip()
    stopped_containers = _stopped_unreal_game_containers()
    project_names = _stopped_unreal_game_projects(containers=stopped_containers)

    removable_projects: set[str] = set()
    project_envs: dict[str, dict[str, str]] = {}
    skipped_projects: list[dict[str, str]] = []

    for project in project_names:
        if host_project and project == host_project:
            removable_projects.add(project)
            continue
        try:
            project_envs[project] = _derive_cluster_recreate_env(project=project, project_dir=project_dir)
            removable_projects.add(project)
        except HTTPException as exc:
            skipped_projects.append({"project": project, "detail": str(exc.detail)})

    removed_containers: list[dict[str, Any]] = []
    for container in stopped_containers:
        project = _container_compose_project(container)
        if not project or project not in removable_projects:
            continue
        name = str(getattr(container, "name", "") or "")
        try:
            container.remove(v=True)
            removed_containers.append({"project": project, "container": name, "removed": True})
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            removed_containers.append({"project": project, "container": name, "removed": False, "detail": str(exc)})

    current_image_id = _docker_image_id(game_image)
    image_cleanup: dict[str, Any] = {
        "requested_ref": game_image,
        "requested_id": current_image_id,
        "target": current_image_id or game_image,
        "removed": False,
    }
    if image_cleanup["target"]:
        try:
            docker_client.images.remove(image_cleanup["target"], force=True, noprune=False)
            image_cleanup["removed"] = True
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            image_cleanup["detail"] = str(exc)

    return {
        "project_names": project_names,
        "project_envs": project_envs,
        "removed_containers": removed_containers,
        "skipped_projects": skipped_projects,
        "image": image_cleanup,
    }


def _docker_storage_report() -> dict[str, Any]:
    try:
        raw = docker_client.api.df()
    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        return {"ok": False, "detail": str(exc)}

    images = raw.get("Images") or []
    containers = raw.get("Containers") or []
    volumes = raw.get("Volumes") or []
    build_cache = raw.get("BuildCache") or []
    return {
        "ok": True,
        "layers_size": raw.get("LayersSize"),
        "images_count": len(images),
        "containers_count": len(containers),
        "volumes_count": len(volumes),
        "build_cache_count": len(build_cache),
        "images_bytes": sum(int(item.get("Size") or 0) for item in images if isinstance(item, dict)),
        "containers_bytes": sum(int(item.get("SizeRootFs") or 0) for item in containers if isinstance(item, dict)),
        "build_cache_bytes": sum(int(item.get("Size") or 0) for item in build_cache if isinstance(item, dict)),
    }


def _prune_unused_docker_state() -> dict[str, Any]:
    result: dict[str, Any] = {"before": _docker_storage_report()}
    try:
        result["containers"] = docker_client.containers.prune()
    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        result["containers"] = {"ok": False, "detail": str(exc)}
    try:
        result["images"] = docker_client.images.prune(filters={"dangling": False})
    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        result["images"] = {"ok": False, "detail": str(exc)}
    result["after"] = _docker_storage_report()
    return result


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

    game_diagnostics = None
    try:
        game_container = _find_container("unreal-game", project_name=POWER_PROJECT_NAME)
        if game_container is not None:
            game_diagnostics = _container_diagnostics(game_container)
    except Exception:  # pragma: no cover - defensive
        game_diagnostics = None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": {
            "EMBODY_SERVICE_IMAGE_TAG": (os.environ.get("EMBODY_SERVICE_IMAGE_TAG") or "").strip() or None,
            "ORCHESTRATOR_PROJECT_DIR": project_dir or None,
            "CLUSTER_INSTANCE_COMPOSE_FILE": instance_compose or None,
        },
        "auth": _power_allowlist_diagnostics(),
        "git": git_info,
        "containers": containers,
        "game_diagnostics": game_diagnostics,
        "rollout": _read_rollout_state_with_runtime(),
        "verify_last": _read_json_file(VERIFY_LAST_FILE),
    }


@app.get("/meta/unreal-game/diagnostics")
def read_meta_unreal_game_diagnostics(request: Request) -> dict[str, Any]:
    """Return bounded recent diagnostics for the host unreal-game container."""
    _require_auth(request)
    payload = _unreal_game_diagnostics()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


@app.post("/ops/unreal-game/fix-whisper-runtime")
def fix_unreal_game_whisper_runtime(request: Request) -> dict[str, Any]:
    """Hotfix the running unreal-game container with the patched launcher and restart it."""
    _require_remote_ops_enabled()
    _require_auth(request)
    payload = _hotfix_unreal_game_whisper_runtime(project_name=POWER_PROJECT_NAME or None)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


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

    ops_allowlist_requested = payload.ops_allow_cidrs is not None
    if ops_allowlist_requested:
        allowlist = payload.ops_allow_cidrs or []
        allow_csv = ",".join(allowlist)
        power_allow_tokens = ["127.0.0.1/32", "::1/128", *allowlist]
        deduped_power_allow: list[str] = []
        seen_power_allow: set[str] = set()
        for token in power_allow_tokens:
            if token in seen_power_allow:
                continue
            seen_power_allow.add(token)
            deduped_power_allow.append(token)
        power_allow_csv = ",".join(deduped_power_allow)
        updates = json.dumps(
            {
                "EDGE_OPS_ALLOW_CIDRS": allow_csv,
                "EDGE_POWER_EXTRA_CIDRS": allow_csv,
                "EDGE_FIREWALL_EXTRA_CIDRS": allow_csv,
                "POWER_ALLOWED_IPS": power_allow_csv,
            },
            separators=(",", ":"),
        )
        code = (
            "import json,pathlib,sys\n"
            "path=pathlib.Path(sys.argv[1])\n"
            "updates=json.loads(sys.argv[2])\n"
            "lines=path.read_text(encoding='utf-8').splitlines(True) if path.exists() else []\n"
            "out=[]\n"
            "seen=set()\n"
            "for line in lines:\n"
            "    replaced=False\n"
            "    for key,val in updates.items():\n"
            "        if line.startswith(f'{key}='):\n"
            "            if key not in seen:\n"
            "                out.append(f'{key}={val}\\n')\n"
            "                seen.add(key)\n"
            "            replaced=True\n"
            "            break\n"
            "    if not replaced:\n"
            "        out.append(line)\n"
            "for key,val in updates.items():\n"
            "    if key in seen:\n"
            "        continue\n"
            "    if out and not out[-1].endswith('\\n'):\n"
            "        out[-1]=out[-1]+'\\n'\n"
            "    out.append(f'{key}={val}\\n')\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(''.join(out), encoding='utf-8')\n"
        )
        set_ops_allow = run_step("set_ops_allow_cidrs", ["python3", "-c", code, env_file, updates])
        if set_ops_allow["exit_code"] != 0:
            return {"ok": False, "exit_code": set_ops_allow["exit_code"], "steps": steps}

    if payload.apply:
        recreate_orchestrator_health = payload.recreate_orchestrator_health or ops_allowlist_requested
        recreate_orchestrator_edge_rotator = payload.recreate_orchestrator_edge_rotator or ops_allowlist_requested
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

        if recreate_orchestrator_health:
            # Schedule a self-recreate AFTER returning (and after a small delay),
            # otherwise the HTTP response can get cut off mid-flight.
            self_service = (POWER_SELF_SERVICE or "orchestrator-health").strip() or "orchestrator-health"
            log_path = "/var/lib/vtuber/power-state/ops-recreate-orchestrator-health.log"
            pull_cmd = " ".join(shlex.quote(arg) for arg in [*compose_base, "pull", self_service])
            up_cmd = " ".join(
                shlex.quote(arg) for arg in [*compose_base, "up", "-d", "--no-deps", "--force-recreate", self_service]
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

            helper_name = f"vtuber-ops-recreate-orchestrator-health-{int(time.time())}"
            run_step(
                "schedule_recreate_orchestrator_health",
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

        if recreate_orchestrator_edge_rotator:
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


def _run_rollout_job(
    *,
    job_id: str,
    project_dir: str,
    payments_url: str,
    image_ref: str,
    game_image: str,
    skip_download: bool,
    stream_no_cache: bool,
    recreate_stopped: bool,
    cleanup_stopped_game: bool,
    prune_unused_docker: bool,
    orch_token: Optional[str],
    rollout_state_file: str,
    rollout_work_dir: str,
) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        loaded_image_id = _docker_image_id(game_image)
        recreate_project_names: Optional[list[str]] = None
        recreate_project_envs: Optional[dict[str, dict[str, str]]] = None

        if skip_download:
            _update_rollout_state(
                job_id,
                status="applying",
                detail=ROLLOUT_STATUS_DETAILS["applying"],
                started_at=started_at,
                apply_requested_at=started_at,
                loaded_image_id=loaded_image_id,
            )
            recreate = _recreate_stopped_game_projects(project_dir=project_dir)
            failed_projects = sorted(
                {
                    str(item.get("project") or "<unknown>")
                    for item in recreate
                    if (not item.get("ok", False)) and (not item.get("skipped", False))
                }
            )
            if failed_projects:
                _fail_rollout_state(
                    job_id,
                    f"failed to apply staged rollout: {', '.join(failed_projects)}",
                    recreate=recreate,
                    loaded_image_id=_docker_image_id(game_image),
                )
                return

            _update_rollout_state(
                job_id,
                status="applied",
                detail=ROLLOUT_STATUS_DETAILS["applied"],
                recreate=recreate,
                applied_at=datetime.now(timezone.utc).isoformat(),
                loaded_image_id=_docker_image_id(game_image),
            )
            return

        _update_rollout_state(
            job_id,
            status="downloading",
            detail=ROLLOUT_STATUS_DETAILS["downloading"],
            started_at=started_at,
        )

        if cleanup_stopped_game:
            cleanup = _cleanup_stopped_game_rollout_targets(project_dir=project_dir, game_image=game_image)
            if prune_unused_docker:
                cleanup["prune"] = _prune_unused_docker_state()
            recreate_project_names = list(cleanup.get("project_names") or [])
            raw_project_envs = cleanup.get("project_envs") or {}
            if isinstance(raw_project_envs, dict):
                recreate_project_envs = {
                    str(project): env
                    for project, env in raw_project_envs.items()
                    if isinstance(project, str) and isinstance(env, dict)
                }
            _update_rollout_state(
                job_id,
                cleanup={
                    "project_names": recreate_project_names,
                    "removed_containers": cleanup.get("removed_containers") or [],
                    "skipped_projects": cleanup.get("skipped_projects") or [],
                    "image": cleanup.get("image") or {},
                    "prune": cleanup.get("prune") or {},
                },
                cleanup_requested_at=datetime.now(timezone.utc).isoformat(),
                cleanup_completed_at=datetime.now(timezone.utc).isoformat(),
            )

        token_path = "/root/.embody/orch-license-token.txt"
        cmd_env = None
        Path(rollout_work_dir).mkdir(parents=True, exist_ok=True)
        cmd = [
            "bash",
            f"{project_dir}/tools/encrypted-game-image/consume.sh",
            "--payments-api-url",
            payments_url,
            "--image-ref",
            image_ref,
            "--rollout-state-file",
            rollout_state_file,
            "--rollout-work-dir",
            rollout_work_dir,
            "--rollout-job-id",
            job_id,
        ]
        if orch_token:
            cmd.extend(["--orch-token-env", "ORCH_TOKEN"])
            cmd_env = {"ORCH_TOKEN": orch_token}
        else:
            cmd.extend(["--orch-token-file", token_path])
        if stream_no_cache:
            cmd.append("--stream-no-cache")

        download = _cluster_executor_exec_stream(
            _cluster_executor_container(),
            cmd,
            env=cmd_env,
            on_status=lambda status: _update_rollout_state(
                job_id,
                status=status,
                detail=ROLLOUT_STATUS_DETAILS.get(status),
            ),
        )
        download["stdout"] = _tail(download.get("stdout", ""))
        download["stderr"] = _tail(download.get("stderr", ""))
        download["ok"] = download.get("exit_code") == 0

        if not download["ok"]:
            _fail_rollout_state(
                job_id,
                "download/load failed",
                download=download,
                download_exit_code=download.get("exit_code"),
                download_stdout_tail=download.get("stdout"),
                download_stderr_tail=download.get("stderr"),
            )
            return

        loaded_image_id = _docker_image_id(game_image)
        _update_rollout_state(
            job_id,
            status="staged",
            detail=ROLLOUT_STATUS_DETAILS["staged"],
            staged_at=datetime.now(timezone.utc).isoformat(),
            loaded_image_id=loaded_image_id,
            download=download,
            download_exit_code=download.get("exit_code"),
            download_stdout_tail=download.get("stdout"),
            download_stderr_tail=download.get("stderr"),
        )

        if not recreate_stopped:
            return

        _update_rollout_state(
            job_id,
            status="applying",
            detail=ROLLOUT_STATUS_DETAILS["applying"],
            apply_requested_at=datetime.now(timezone.utc).isoformat(),
            loaded_image_id=loaded_image_id,
        )
        recreate = _recreate_stopped_game_projects(
            project_dir=project_dir,
            project_names=recreate_project_names,
            project_envs=recreate_project_envs,
        )
        failed_projects = sorted(
            {
                str(item.get("project") or "<unknown>")
                for item in recreate
                if (not item.get("ok", False)) and (not item.get("skipped", False))
            }
        )
        if failed_projects:
            _fail_rollout_state(
                job_id,
                f"failed to apply staged rollout: {', '.join(failed_projects)}",
                recreate=recreate,
                loaded_image_id=_docker_image_id(game_image),
            )
            return

        _update_rollout_state(
            job_id,
            status="applied",
            detail=ROLLOUT_STATUS_DETAILS["applied"],
            recreate=recreate,
            applied_at=datetime.now(timezone.utc).isoformat(),
            loaded_image_id=_docker_image_id(game_image),
        )
    except HTTPException as exc:
        _fail_rollout_state(job_id, str(exc.detail), error_status_code=exc.status_code)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Rollout job %s failed", job_id)
        _fail_rollout_state(job_id, f"unexpected rollout failure: {exc}", error_type=exc.__class__.__name__)
    finally:
        with _ROLLOUT_JOB_LOCK:
            global _ROLLOUT_JOB_THREAD, _ROLLOUT_JOB_ID
            if _ROLLOUT_JOB_ID == job_id:
                _ROLLOUT_JOB_THREAD = None
                _ROLLOUT_JOB_ID = None


@app.post("/ops/rollout", status_code=202)
def ops_rollout(
    payload: OpsRolloutRequest,
    request: Request,
    _: Any = Depends(_require_ops_action),
) -> dict[str, Any]:
    """EXPERIMENTAL: load a new encrypted game image via a Payments lease.

    By default this queues an async rollout job and persists progress so callers can observe status via /meta.
    Optionally, it can force-recreate stopped game containers so the next wake/start uses the updated image.
    """
    project_dir = _cluster_project_dir()
    if not project_dir:
        raise HTTPException(status_code=500, detail="invalid ORCHESTRATOR_PROJECT_DIR")

    if payload.cleanup_stopped_game and not payload.recreate_stopped:
        raise HTTPException(status_code=400, detail="cleanup_stopped_game requires recreate_stopped=true")
    if payload.prune_unused_docker and not payload.cleanup_stopped_game:
        raise HTTPException(status_code=400, detail="prune_unused_docker requires cleanup_stopped_game=true")
    if payload.cleanup_stopped_game and payload.stage_only:
        raise HTTPException(status_code=400, detail="cleanup_stopped_game cannot be combined with stage_only")
    if payload.cleanup_stopped_game and payload.skip_download:
        raise HTTPException(status_code=400, detail="cleanup_stopped_game cannot be combined with skip_download")
    if payload.stage_only and payload.recreate_stopped:
        raise HTTPException(status_code=400, detail="stage_only cannot be combined with recreate_stopped")
    if payload.skip_download and payload.stage_only:
        raise HTTPException(status_code=400, detail="skip_download and stage_only are mutually exclusive")
    if payload.skip_download and not payload.recreate_stopped:
        raise HTTPException(status_code=400, detail="skip_download requires recreate_stopped=true")
    if payload.stream_no_cache and payload.skip_download:
        raise HTTPException(status_code=400, detail="stream_no_cache cannot be combined with skip_download")

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
    mode = "stage" if payload.stage_only else ("apply" if payload.recreate_stopped else "load")

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

    loaded_image_id = None
    resume_state = _rollout_resume_fields(
        _read_json_file(ROLLOUT_STATE_FILE),
        image_ref=image_ref,
        stream_no_cache=payload.stream_no_cache,
    )
    if payload.skip_download:
        existing = _read_json_file(ROLLOUT_STATE_FILE)
        if not existing or existing.get("status") not in ("staged", "applied"):
            raise HTTPException(status_code=409, detail="no staged rollout found (run /ops/rollout with stage_only first)")
        if (existing.get("image_ref") or "").strip() and (existing.get("image_ref") or "").strip() != image_ref:
            raise HTTPException(status_code=409, detail="staged rollout image_ref does not match request image_ref")
        loaded_image_id = str(existing.get("loaded_image_id") or "").strip() or _docker_image_id(game_image)

    job_id = uuid.uuid4().hex
    state = _init_rollout_state(
        job_id=job_id,
        mode=mode,
        image_ref=image_ref,
        payments_url=payments_url,
        game_image=game_image,
        disk_free_bytes=free_bytes,
        stage_only=payload.stage_only,
        skip_download=payload.skip_download,
        stream_no_cache=payload.stream_no_cache,
        recreate_stopped=payload.recreate_stopped,
        cleanup_stopped_game=payload.cleanup_stopped_game,
        prune_unused_docker=payload.prune_unused_docker,
        no_verify=payload.no_verify,
        loaded_image_id=loaded_image_id,
        resume_state=resume_state,
    )

    rollout_work_dir = _rollout_work_dir(job_id)
    worker_kwargs = {
        "job_id": job_id,
        "project_dir": project_dir,
        "payments_url": payments_url,
        "image_ref": image_ref,
        "game_image": game_image,
        "skip_download": payload.skip_download,
        "stream_no_cache": payload.stream_no_cache,
        "recreate_stopped": payload.recreate_stopped,
        "cleanup_stopped_game": payload.cleanup_stopped_game,
        "prune_unused_docker": payload.prune_unused_docker,
        "orch_token": payload.orch_token,
        "rollout_state_file": str(ROLLOUT_STATE_FILE),
        "rollout_work_dir": str(rollout_work_dir),
    }

    with _ROLLOUT_JOB_LOCK:
        global _ROLLOUT_JOB_THREAD, _ROLLOUT_JOB_ID
        if _ROLLOUT_JOB_THREAD is not None:
            current = _read_json_file(ROLLOUT_STATE_FILE)
            current_status = str((current or {}).get("status") or "").strip() or "queued"
            active_for_current = bool(
                _ROLLOUT_JOB_THREAD.is_alive()
                or (
                    current
                    and _ROLLOUT_JOB_ID
                    and current.get("job_id") == _ROLLOUT_JOB_ID
                    and _rollout_is_active_status(current_status)
                )
            )
            if active_for_current:
                raise HTTPException(status_code=409, detail=f"rollout already in progress ({current_status})")
            _ROLLOUT_JOB_THREAD = None
            _ROLLOUT_JOB_ID = None

        _write_json_file_atomic(ROLLOUT_STATE_FILE, state)
        thread = _make_rollout_thread(**worker_kwargs)
        _ROLLOUT_JOB_THREAD = thread
        _ROLLOUT_JOB_ID = job_id

    try:
        thread.start()
    except Exception as exc:  # pragma: no cover - defensive
        with _ROLLOUT_JOB_LOCK:
            if _ROLLOUT_JOB_ID == job_id:
                _ROLLOUT_JOB_THREAD = None
                _ROLLOUT_JOB_ID = None
        _fail_rollout_state(job_id, f"failed to start rollout worker: {exc}")
        raise HTTPException(status_code=500, detail="failed to start rollout worker") from exc

    return {
        "ok": True,
        "accepted": True,
        "job_id": job_id,
        "status": "queued",
        "mode": mode,
        "disk_free_bytes": free_bytes,
        "game_image": game_image,
        "rollout": _read_rollout_state_with_runtime(),
    }


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
