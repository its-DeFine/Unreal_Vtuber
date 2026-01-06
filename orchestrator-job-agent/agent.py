from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

LOG_FORMAT = "%(asctime)s [job-agent] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("job-agent")


def _env_str(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip()


def _env_float(key: str, default: float) -> float:
    raw = _env_str(key, "")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = _env_str(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env_str(key, "")
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


def _truncate(value: str, limit: int = 300) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


@dataclass
class AgentConfig:
    enabled: bool
    poll_seconds: float
    timeout_seconds: float
    base_url: str
    orchestrator_id: str
    token_file: str
    host_gateway: str
    runner_url: str
    recorder_url: str
    power_url: str
    recordings_api_token: str
    default_wake_seconds: int
    default_max_wait_seconds: int


def _load_config() -> AgentConfig:
    base_url = _env_str("JOB_AGENT_URL") or _env_str("PAYMENTS_API_URL")
    base_url = base_url.rstrip("/")
    host_gateway = _env_str("JOB_AGENT_HOST_GATEWAY", "172.18.0.1")
    runner_url = _env_str("JOB_AGENT_RUNNER_URL") or f"http://{host_gateway}:9877"
    recorder_url = _env_str("JOB_AGENT_RECORDER_URL") or f"http://{host_gateway}:8889"
    power_url = _env_str("JOB_AGENT_POWER_URL") or f"http://{host_gateway}:9090"

    return AgentConfig(
        enabled=_env_bool("JOB_AGENT_ENABLED", False),
        poll_seconds=max(2.0, _env_float("JOB_AGENT_POLL_SECONDS", 10.0)),
        timeout_seconds=max(2.0, _env_float("JOB_AGENT_TIMEOUT_SECONDS", 10.0)),
        base_url=base_url,
        orchestrator_id=_env_str("ORCHESTRATOR_ID"),
        token_file=_env_str("ORCHESTRATOR_TOKEN_FILE", "/var/lib/vtuber/embody/orch-license-token.txt"),
        host_gateway=host_gateway,
        runner_url=runner_url.rstrip("/"),
        recorder_url=recorder_url.rstrip("/"),
        power_url=power_url.rstrip("/"),
        recordings_api_token=_env_str("RECORDINGS_API_TOKEN"),
        default_wake_seconds=_env_int("JOB_AGENT_WAKE_SECONDS", 2400),
        default_max_wait_seconds=_env_int("JOB_AGENT_MAX_WAIT_SECONDS", 900),
    )


def _read_token(cfg: AgentConfig) -> str:
    token = _env_str("ORCHESTRATOR_TOKEN")
    if token:
        return token
    token_path = Path(cfg.token_file)
    try:
        return token_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except Exception as exc:
        logger.warning("Failed reading ORCHESTRATOR_TOKEN_FILE=%s: %s", token_path, exc)
        return ""


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _recorder_headers(cfg: AgentConfig) -> Dict[str, str]:
    if not cfg.recordings_api_token:
        return {}
    return {"Authorization": f"Bearer {cfg.recordings_api_token}"}


def _sanitize_label(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in raw.strip())
    return cleaned or "capture"


def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
    try:
        return response.json()
    except ValueError:
        return None


def _wait_for_ready(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    attempts: int,
    headers: Optional[Dict[str, str]] = None,
) -> bool:
    for _ in range(attempts):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def _claim_job(session: requests.Session, cfg: AgentConfig, token: str) -> Optional[Dict[str, Any]]:
    if not cfg.base_url:
        logger.error("JOB_AGENT_URL or PAYMENTS_API_URL is required")
        return None
    url = f"{cfg.base_url}/api/jobs/record/claim"
    payload: Dict[str, Any] = {}
    if cfg.orchestrator_id:
        payload["orchestrator_id"] = cfg.orchestrator_id
    try:
        resp = session.post(url, json=payload, headers=_auth_headers(token), timeout=cfg.timeout_seconds)
    except requests.RequestException as exc:
        logger.warning("Job claim failed: %s", exc)
        return None

    if resp.status_code == 204:
        return None
    if resp.status_code == 404:
        logger.warning("Job claim endpoint missing (status 404): %s", url)
        return None
    if resp.status_code == 401:
        logger.warning("Job claim unauthorized; check orchestrator token")
        return None
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.warning("Job claim failed (status %s): %s", resp.status_code, _truncate(resp.text))
        return None

    data = _safe_json(resp)
    if not isinstance(data, dict):
        logger.warning("Job claim returned non-JSON response")
        return None
    return data


def _post_status(
    session: requests.Session,
    cfg: AgentConfig,
    token: str,
    job_id: str,
    path: str,
    payload: Dict[str, Any],
) -> None:
    url = f"{cfg.base_url}{path.format(job_id=job_id)}"
    try:
        resp = session.post(url, json=payload, headers=_auth_headers(token), timeout=cfg.timeout_seconds)
    except requests.RequestException as exc:
        logger.warning("Status update failed for %s: %s", job_id, exc)
        return
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.warning("Status update failed for %s (status %s): %s", job_id, resp.status_code, _truncate(resp.text))


def _fetch_upload_url(
    session: requests.Session,
    cfg: AgentConfig,
    token: str,
    job_id: str,
    filename: str,
) -> Optional[Dict[str, Any]]:
    url = f"{cfg.base_url}/api/jobs/record/{job_id}/upload-url"
    try:
        resp = session.post(
            url,
            json={"filename": filename},
            headers=_auth_headers(token),
            timeout=cfg.timeout_seconds,
        )
    except requests.RequestException as exc:
        logger.warning("Upload-url request failed for %s: %s", job_id, exc)
        return None
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.warning("Upload-url failed for %s (status %s): %s", job_id, resp.status_code, _truncate(resp.text))
        return None
    return _safe_json(resp) or None


def _run_job(session: requests.Session, cfg: AgentConfig, token: str, job: Dict[str, Any]) -> None:
    job_id = str(job.get("job_id") or "").strip()
    if not job_id:
        logger.warning("Skipping job without job_id")
        return

    script = job.get("script")
    if not isinstance(script, dict) or not script.get("commands"):
        _post_status(session, cfg, token, job_id, "/api/jobs/record/{job_id}/fail", {"error": "missing script"})
        return

    wake_seconds = job.get("wake_seconds")
    if wake_seconds is None:
        wake_seconds = cfg.default_wake_seconds

    label = _sanitize_label(str(job.get("recording_label") or f"job_{job_id[:12]}"))[:64]
    session_id = f"job_{job_id[:12]}_{int(time.time())}"

    logger.info("Job %s: waking stack", job_id)
    try:
        session.post(
            f"{cfg.power_url}/power",
            json={"action": "wake", "reason": "job", "awake_seconds": int(wake_seconds)},
            timeout=cfg.timeout_seconds,
        )
    except requests.RequestException:
        logger.info("Job %s: power wake skipped", job_id)

    logger.info("Job %s: waiting for runner", job_id)
    if not _wait_for_ready(session, f"{cfg.runner_url}/health", timeout=cfg.timeout_seconds, attempts=60):
        _post_status(session, cfg, token, job_id, "/api/jobs/record/{job_id}/fail", {"error": "runner not ready"})
        return

    logger.info("Job %s: waiting for recorder", job_id)
    if not _wait_for_ready(
        session,
        f"{cfg.recorder_url}/",
        timeout=cfg.timeout_seconds,
        attempts=60,
        headers=rec_headers,
    ):
        _post_status(session, cfg, token, job_id, "/api/jobs/record/{job_id}/fail", {"error": "recorder not ready"})
        return

    rec_headers = _recorder_headers(cfg)
    rec_filename = ""
    started_at = time.time()
    try:
        start_payload: Dict[str, Any] = {"label": label}
        streamer_id = job.get("recording_streamer_id")
        if streamer_id:
            start_payload["streamer_id"] = streamer_id

        start_resp = session.post(
            f"{cfg.recorder_url}/recordings/start",
            json=start_payload,
            headers=rec_headers,
            timeout=cfg.timeout_seconds,
        )
        start_resp.raise_for_status()
        start_body = _safe_json(start_resp) or {}
        output_path = str(start_body.get("output") or "")
        rec_filename = output_path.rsplit("/", 1)[-1] if output_path else ""
        if not rec_filename:
            raise RuntimeError("recorder did not return output filename")

        runner_payload = dict(script)
        runner_payload["session_id"] = session_id
        exec_resp = session.post(
            f"{cfg.runner_url}/scripts/execute",
            json=runner_payload,
            timeout=cfg.timeout_seconds,
        )
        exec_resp.raise_for_status()

        max_wait = int(job.get("max_wait_seconds") or cfg.default_max_wait_seconds)
        deadline = time.monotonic() + max_wait
        state = ""
        while time.monotonic() < deadline:
            try:
                status_resp = session.get(
                    f"{cfg.runner_url}/scripts/{session_id}",
                    timeout=cfg.timeout_seconds,
                )
                if status_resp.status_code == 200:
                    payload = _safe_json(status_resp) or {}
                    state = str(payload.get("state") or "")
                    if state in {"completed", "failed"}:
                        break
            except requests.RequestException:
                pass
            time.sleep(1)

        if state != "completed":
            raise RuntimeError(f"runner did not complete (state={state or 'unknown'})")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Job %s failed: %s", job_id, exc)
        try:
            session.post(
                f"{cfg.recorder_url}/recordings/stop",
                headers=rec_headers,
                timeout=cfg.timeout_seconds,
            )
        except requests.RequestException:
            pass
        _post_status(
            session,
            cfg,
            token,
            job_id,
            "/api/jobs/record/{job_id}/fail",
            {"error": _truncate(str(exc))},
        )
        return

    # Stop recorder (best-effort)
    try:
        session.post(
            f"{cfg.recorder_url}/recordings/stop",
            headers=rec_headers,
            timeout=cfg.timeout_seconds,
        )
    except requests.RequestException:
        pass

    if not rec_filename:
        _post_status(
            session,
            cfg,
            token,
            job_id,
            "/api/jobs/record/{job_id}/fail",
            {"error": "recording filename missing"},
        )
        return

    upload_payload = _fetch_upload_url(session, cfg, token, job_id, rec_filename)
    if not upload_payload:
        _post_status(
            session,
            cfg,
            token,
            job_id,
            "/api/jobs/record/{job_id}/fail",
            {"error": "upload url missing"},
        )
        return

    upload_url = str(upload_payload.get("upload_url") or "")
    if not upload_url:
        _post_status(
            session,
            cfg,
            token,
            job_id,
            "/api/jobs/record/{job_id}/fail",
            {"error": "upload url missing"},
        )
        return

    try:
        upload_resp = session.post(
            f"{cfg.recorder_url}/recordings/{rec_filename}/upload",
            json={"upload_url": upload_url, "delete_after": bool(job.get("delete_after_upload", True))},
            headers=rec_headers,
            timeout=max(cfg.timeout_seconds, 30.0),
        )
        upload_resp.raise_for_status()
        upload_info = _safe_json(upload_resp) or {}
    except Exception as exc:  # noqa: BLE001
        _post_status(
            session,
            cfg,
            token,
            job_id,
            "/api/jobs/record/{job_id}/fail",
            {"error": f"upload failed: {_truncate(str(exc))}"},
        )
        return

    duration_ms = int((time.time() - started_at) * 1000)
    complete_payload: Dict[str, Any] = {
        "recording_filename": rec_filename,
        "artifact_hash": upload_info.get("sha256"),
        "duration_ms": duration_ms,
        "recording_label": label,
    }
    artifact_uri = upload_payload.get("artifact_uri")
    if artifact_uri:
        complete_payload["artifact_uri"] = artifact_uri

    _post_status(session, cfg, token, job_id, "/api/jobs/record/{job_id}/complete", complete_payload)
    logger.info("Job %s completed", job_id)


def main() -> None:
    cfg = _load_config()
    if not cfg.enabled:
        logger.info("JOB_AGENT_ENABLED=0; idle")
        while True:
            time.sleep(3600)

    session = requests.Session()
    logger.info(
        "Job agent online (poll=%.1fs, base_url=%s, runner=%s)",
        cfg.poll_seconds,
        cfg.base_url or "<unset>",
        cfg.runner_url,
    )

    while True:
        token = _read_token(cfg)
        if not token:
            logger.warning("Missing orchestrator token; waiting for %s", cfg.token_file)
            time.sleep(cfg.poll_seconds)
            continue

        job = _claim_job(session, cfg, token)
        if not job:
            time.sleep(cfg.poll_seconds)
            continue

        _run_job(session, cfg, token, job)


if __name__ == "__main__":
    main()
