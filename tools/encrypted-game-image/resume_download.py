#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROBE_BYTES = 128
CONTENT_RANGE_RE = re.compile(r"bytes\s+\d+-\d+/(\d+|\*)", re.IGNORECASE)
ACTIVE_STATUSES = frozenset({"queued", "downloading", "decrypting", "loading", "applying"})
TERMINAL_STATUSES = frozenset({"downloaded", "staged", "applied", "error", "failed"})


class DownloadError(RuntimeError):
    pass


@dataclass
class ProbeResult:
    prefix: bytes
    prefix_sha256: str
    total_bytes: int | None
    etag: str | None
    last_modified: str | None
    status_code: int | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def human_bytes(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(max(num, 0.0))
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TB"


def human_duration(seconds: float) -> str:
    seconds = max(float(seconds), 0.0)
    whole = int(seconds + 0.5)
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def slugify(value: str) -> str:
    cleaned = [ch if ch.isalnum() else "-" for ch in value.lower()]
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:48] or "artifact"


def stable_ref_dir(root: Path, image_ref: str) -> Path:
    digest = hashlib.sha256(image_ref.encode("utf-8")).hexdigest()[:16]
    return root / f"{slugify(image_ref)}-{digest}"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def intish(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def floatish(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(str(value).strip()), 2)
    except Exception:
        return None


def boolish(value: Any) -> bool | None:
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


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    return os.access(path, os.W_OK | os.X_OK)


def choose_root(primary: Path, fallback: Path) -> Path:
    for candidate in (primary, fallback):
        if ensure_dir(candidate):
            return candidate
    raise DownloadError(f"unable to create cache directory in {primary} or {fallback}")


def read_existing_state(primary: Path, fallback: Path) -> dict[str, Any]:
    return read_json(primary) or read_json(fallback) or {}


def resume_possible(data: dict[str, Any], downloaded_bytes: int, total_bytes: int | None) -> bool:
    explicit = boolish(data.get("can_resume"))
    if explicit is not None:
        return explicit

    partial_path = str(data.get("artifact_partial_path") or "").strip()
    if partial_path:
        try:
            if Path(partial_path).exists() and Path(partial_path).stat().st_size > 0:
                return True
        except Exception:
            pass

    artifact_path = str(data.get("artifact_local_path") or "").strip()
    if artifact_path:
        try:
            size = Path(artifact_path).stat().st_size
            if size > 0 and (total_bytes is None or total_bytes <= 0 or size == total_bytes):
                return True
        except Exception:
            pass

    return downloaded_bytes > 0 and (total_bytes is None or downloaded_bytes <= total_bytes)


def merge_state_payload(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    updated_at = str(incoming.get("updated_at") or now_iso())
    status = str(incoming.get("status") or "").strip()
    previous_status = str(existing.get("status") or "").strip()

    history = existing.get("history")
    if not isinstance(history, list):
        history = []
    if status and status != previous_status:
        history = history + [{"status": status, "at": updated_at}]

    for key, value in incoming.items():
        if value is not None:
            merged[key] = value

    merged["history"] = history[-32:]
    total_bytes = intish(merged.get("artifact_total_bytes"))
    downloaded_bytes = intish(merged.get("artifact_downloaded_bytes"))
    if downloaded_bytes is None:
        downloaded_bytes = intish(merged.get("downloaded_bytes"))
    if downloaded_bytes is None:
        downloaded_bytes = 0
    progress_percent = floatish(merged.get("artifact_download_percent"))
    if progress_percent is None:
        progress_percent = floatish(merged.get("progress_percent"))
    if progress_percent is None and total_bytes and total_bytes > 0:
        progress_percent = round(min(100.0, (float(downloaded_bytes) * 100.0) / float(total_bytes)), 2)
    if progress_percent is None:
        progress_percent = 0.0

    merged["updated_at"] = updated_at
    merged["downloaded_bytes"] = downloaded_bytes
    merged["progress_percent"] = progress_percent
    merged["can_resume"] = resume_possible(merged, downloaded_bytes, total_bytes)

    if status:
        merged["active"] = status in ACTIVE_STATUSES
        merged["terminal"] = status in TERMINAL_STATUSES
        if status in TERMINAL_STATUSES:
            merged["completed_at"] = updated_at
            if status in {"error", "failed"}:
                merged["failed_at"] = updated_at
            else:
                merged.pop("failed_at", None)
        else:
            merged.pop("completed_at", None)
            merged.pop("failed_at", None)

    return {key: value for key, value in merged.items() if value is not None}


def write_state(primary: Path, fallback: Path, data: dict[str, Any]) -> Path | None:
    existing = read_existing_state(primary, fallback)
    merged = merge_state_payload(existing, data)
    for candidate in (primary, fallback):
        try:
            atomic_write_json(candidate, merged)
        except Exception:
            continue
        return candidate
    return None


def parse_header_file(path: Path) -> tuple[int | None, dict[str, str]]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise DownloadError(f"failed to read probe headers: {exc}") from exc

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in raw.splitlines():
        if line.startswith("HTTP/"):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current is not None:
            current.append(line)
    if current:
        blocks.append(current)
    if not blocks:
        return None, {}

    block = blocks[-1]
    status_code = None
    first = block[0] if block else ""
    parts = first.split()
    if len(parts) >= 2 and parts[1].isdigit():
        status_code = int(parts[1])

    headers: dict[str, str] = {}
    for line in block[1:]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return status_code, headers


def probe_remote(url: str, probe_prefix: Path, probe_headers: Path, probe_stderr: Path) -> ProbeResult:
    probe_prefix.parent.mkdir(parents=True, exist_ok=True)
    probe_headers.parent.mkdir(parents=True, exist_ok=True)
    probe_stderr.parent.mkdir(parents=True, exist_ok=True)

    with probe_stderr.open("wb") as err_fp:
        rc = subprocess.run(
            [
                "curl",
                "-fL",
                "--connect-timeout",
                "10",
                "--max-time",
                "20",
                "--retry",
                "2",
                "--retry-delay",
                "1",
                "--retry-connrefused",
                "--range",
                f"0-{PROBE_BYTES - 1}",
                "-D",
                str(probe_headers),
                "-o",
                str(probe_prefix),
                "-sS",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=err_fp,
            check=False,
        ).returncode
    if rc != 0:
        raise DownloadError("failed to fetch artifact header (URL expired or unreachable)")

    try:
        prefix = probe_prefix.read_bytes()
    except Exception as exc:
        raise DownloadError(f"failed to read artifact header probe: {exc}") from exc
    if not prefix.startswith(b"age-encryption.org/v1"):
        got = prefix.splitlines()[0].decode("utf-8", errors="replace") if prefix else "<empty>"
        raise DownloadError(
            f"artifact does not look age-encrypted (expected header age-encryption.org/v1, got: {got})"
        )

    status_code, headers = parse_header_file(probe_headers)
    total_bytes = None
    content_range = headers.get("content-range") or ""
    match = CONTENT_RANGE_RE.search(content_range)
    if match and match.group(1) != "*":
        total_bytes = int(match.group(1))
    else:
        content_length = (headers.get("content-length") or "").strip()
        if content_length.isdigit():
            total_bytes = int(content_length)

    return ProbeResult(
        prefix=prefix,
        prefix_sha256=hashlib.sha256(prefix).hexdigest(),
        total_bytes=total_bytes,
        etag=(headers.get("etag") or "").strip() or None,
        last_modified=(headers.get("last-modified") or "").strip() or None,
        status_code=status_code,
    )


def prefix_matches(path: Path, probe_prefix: bytes) -> bool:
    try:
        with path.open("rb") as fp:
            current = fp.read(len(probe_prefix))
    except Exception:
        return False
    if not current:
        return True
    return current == probe_prefix[: len(current)]


def metadata_matches(meta: dict[str, Any] | None, image_ref: str, probe: ProbeResult) -> bool:
    if not meta:
        return True
    if (meta.get("image_ref") or "") != image_ref:
        return False

    meta_total = meta.get("artifact_total_bytes")
    if probe.total_bytes is not None and meta_total is not None:
        try:
            if int(meta_total) != int(probe.total_bytes):
                return False
        except Exception:
            return False

    meta_etag = (meta.get("artifact_etag") or "")
    if meta_etag and probe.etag and meta_etag != probe.etag:
        return False

    meta_last_modified = (meta.get("artifact_last_modified") or "")
    if meta_last_modified and probe.last_modified and meta_last_modified != probe.last_modified:
        return False

    meta_prefix_sha = (meta.get("probe_prefix_sha256") or "")
    if meta_prefix_sha and meta_prefix_sha != probe.prefix_sha256:
        return False

    return True


def remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def build_state(
    *,
    status: str,
    phase: str,
    image_ref: str,
    payments_api_url: str,
    lease_id: str,
    cache_dir: Path,
    artifact_path: Path,
    partial_path: Path,
    total_bytes: int | None,
    downloaded_bytes: int,
    action: str,
    resumed: bool | None,
    resume_from_bytes: int | None,
    job_id: str | None = None,
    work_dir: Path | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    percent = None
    if total_bytes and total_bytes > 0:
        percent = round(min(100.0, (float(downloaded_bytes) * 100.0) / float(total_bytes)), 2)

    data: dict[str, Any] = {
        "status": status,
        "phase": phase,
        "updated_at": now_iso(),
        "image_ref": image_ref,
        "payments_api_url": payments_api_url,
        "lease_id": lease_id,
        "artifact_cache_dir": str(cache_dir),
        "artifact_local_path": str(artifact_path),
        "artifact_partial_path": str(partial_path),
        "artifact_download_action": action,
        "artifact_downloaded_bytes": int(downloaded_bytes),
        "artifact_total_bytes": int(total_bytes) if total_bytes is not None else None,
        "artifact_download_percent": percent,
        "artifact_resumed": resumed,
        "artifact_resume_from_bytes": int(resume_from_bytes) if resume_from_bytes is not None else None,
        "job_id": job_id,
        "work_dir": str(work_dir) if work_dir is not None else None,
        "downloaded_bytes": int(downloaded_bytes),
        "progress_percent": percent if percent is not None else 0.0,
    }
    if detail:
        data["detail"] = detail
    data["can_resume"] = resume_possible(data, int(downloaded_bytes), total_bytes)
    return {key: value for key, value in data.items() if value is not None}


def build_metadata(
    *,
    image_ref: str,
    lease_id: str,
    cache_dir: Path,
    artifact_path: Path,
    partial_path: Path,
    probe: ProbeResult,
    downloaded_bytes: int,
    complete: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": now_iso(),
        "image_ref": image_ref,
        "lease_id": lease_id,
        "cache_dir": str(cache_dir),
        "artifact_path": str(artifact_path),
        "partial_path": str(partial_path),
        "artifact_total_bytes": probe.total_bytes,
        "artifact_etag": probe.etag,
        "artifact_last_modified": probe.last_modified,
        "probe_prefix_sha256": probe.prefix_sha256,
        "downloaded_bytes": int(downloaded_bytes),
        "download_complete": bool(complete),
    }


class ProgressReporter:
    def __init__(self, label: str, total_bytes: int | None, resume_from: int, action: str) -> None:
        self.label = label
        self.total_bytes = total_bytes
        self.resume_from = max(int(resume_from), 0)
        self.action = action
        self.is_tty = sys.stderr.isatty()
        self.start = time.time()
        self.last_log = 0.0
        self.last_bytes = self.resume_from
        self.last_sample_at = self.start
        self.initial_banner_printed = False

    def note_start(self) -> None:
        if self.action == "reused_complete":
            sys.stderr.write(f"[{self.label}] using cached complete artifact\n")
            sys.stderr.flush()
            self.initial_banner_printed = True
            return
        if self.resume_from > 0:
            sys.stderr.write(
                f"[{self.label}] resuming at {human_bytes(self.resume_from)}"
                + (f" of {human_bytes(self.total_bytes)}" if self.total_bytes else "")
                + "\n"
            )
        else:
            sys.stderr.write(f"[{self.label}] starting download\n")
        sys.stderr.flush()
        self.initial_banner_printed = True

    def render(self, downloaded_bytes: int, *, final: bool = False) -> None:
        now = time.time()
        if (not final) and (now - self.last_log) < (0.5 if self.is_tty else 15.0):
            return

        elapsed = max(now - self.start, 0.001)
        delta_elapsed = max(now - self.last_sample_at, 0.001)
        delta_bytes = max(downloaded_bytes - self.last_bytes, 0)
        inst_bps = delta_bytes / delta_elapsed
        avg_bps = max(downloaded_bytes - self.resume_from, 0) / elapsed

        if self.total_bytes:
            pct = min(100.0, (float(downloaded_bytes) * 100.0) / float(self.total_bytes))
            line = (
                f"[{self.label}] {pct:6.2f}% {human_bytes(downloaded_bytes)}/{human_bytes(self.total_bytes)} "
                f"{human_bytes(inst_bps)}/s (avg {human_bytes(avg_bps)}/s) elapsed {human_duration(elapsed)}"
            )
        else:
            line = (
                f"[{self.label}] {human_bytes(downloaded_bytes)} "
                f"{human_bytes(inst_bps)}/s (avg {human_bytes(avg_bps)}/s) elapsed {human_duration(elapsed)}"
            )

        if self.is_tty:
            sys.stderr.write("\r\033[2K" + line)
            if final:
                sys.stderr.write("\n")
        else:
            sys.stderr.write(line + "\n")
        sys.stderr.flush()

        self.last_log = now
        self.last_bytes = downloaded_bytes
        self.last_sample_at = now


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume-safe encrypted artifact downloader")
    parser.add_argument("--url", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--payments-api-url", required=True)
    parser.add_argument("--lease-id", required=True)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--state-fallback", required=True)
    parser.add_argument("--cache-root-primary", required=True)
    parser.add_argument("--cache-root-fallback", required=True)
    parser.add_argument("--probe-prefix-path", required=True)
    parser.add_argument("--probe-headers-path", required=True)
    parser.add_argument("--probe-stderr-path", required=True)
    parser.add_argument("--download-stderr-path", required=True)
    parser.add_argument("--job-id", required=False)
    parser.add_argument("--work-dir", required=False)
    args = parser.parse_args()

    state_primary = Path(args.state_file)
    state_fallback = Path(args.state_fallback)
    cache_root_primary = Path(args.cache_root_primary)
    cache_root_fallback = Path(args.cache_root_fallback)
    probe_prefix_path = Path(args.probe_prefix_path)
    probe_headers_path = Path(args.probe_headers_path)
    probe_stderr_path = Path(args.probe_stderr_path)
    download_stderr_path = Path(args.download_stderr_path)
    work_dir = Path(args.work_dir) if args.work_dir else None
    state_context = {"job_id": (args.job_id or "").strip() or None, "work_dir": work_dir}

    try:
        cache_root = choose_root(cache_root_primary, cache_root_fallback)
        cache_dir = stable_ref_dir(cache_root, args.image_ref)
        cache_dir.mkdir(parents=True, exist_ok=True)
        if work_dir is not None:
            work_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = cache_dir / "artifact.age"
        partial_path = cache_dir / "artifact.age.part"
        metadata_path = cache_dir / "artifact.json"
        lock_path = cache_dir / ".download.lock"

        with lock_path.open("w", encoding="utf-8") as lock_fp:
            try:
                fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise DownloadError(f"another download already holds the lock for {cache_dir}") from exc

            probe = probe_remote(args.url, probe_prefix_path, probe_headers_path, probe_stderr_path)
            if probe.total_bytes is None or probe.total_bytes <= 0:
                raise DownloadError("artifact size unavailable from server; cannot compute resumable progress")

            metadata = read_json(metadata_path)
            if not metadata_matches(metadata, args.image_ref, probe):
                remove_if_exists(artifact_path)
                remove_if_exists(partial_path)
                metadata = None

            if artifact_path.exists() and (artifact_path.stat().st_size != probe.total_bytes or not prefix_matches(artifact_path, probe.prefix)):
                remove_if_exists(artifact_path)
            if partial_path.exists() and (
                partial_path.stat().st_size > probe.total_bytes or not prefix_matches(partial_path, probe.prefix)
            ):
                remove_if_exists(partial_path)

            action = "downloaded"
            resume_from = 0
            resumed = False

            if artifact_path.exists() and artifact_path.stat().st_size == probe.total_bytes:
                action = "reused_complete"
                resumed = bool(metadata and metadata.get("download_complete"))
                resume_from = int(metadata.get("downloaded_bytes") or 0) if metadata else 0
                reporter = ProgressReporter("download", probe.total_bytes, probe.total_bytes, action)
                reporter.note_start()
                state = build_state(
                    status="downloaded",
                    phase="downloaded",
                    image_ref=args.image_ref,
                    payments_api_url=args.payments_api_url,
                    lease_id=args.lease_id,
                    cache_dir=cache_dir,
                    artifact_path=artifact_path,
                    partial_path=partial_path,
                    total_bytes=probe.total_bytes,
                    downloaded_bytes=probe.total_bytes,
                    action=action,
                    resumed=resumed,
                    resume_from_bytes=resume_from,
                    **state_context,
                    detail="artifact already cached locally",
                )
                write_state(state_primary, state_fallback, state)
                atomic_write_json(
                    metadata_path,
                    build_metadata(
                        image_ref=args.image_ref,
                        lease_id=args.lease_id,
                        cache_dir=cache_dir,
                        artifact_path=artifact_path,
                        partial_path=partial_path,
                        probe=probe,
                        downloaded_bytes=probe.total_bytes,
                        complete=True,
                    ),
                )
            else:
                if partial_path.exists():
                    resume_from = partial_path.stat().st_size
                    resumed = resume_from > 0
                    action = "resumed" if resumed else "downloaded"
                elif metadata and metadata.get("download_complete") and metadata.get("downloaded_bytes"):
                    resume_from = int(metadata.get("downloaded_bytes") or 0)
                    resumed = resume_from > 0

                reporter = ProgressReporter("download", probe.total_bytes, resume_from, action)
                reporter.note_start()

                atomic_write_json(
                    metadata_path,
                    build_metadata(
                        image_ref=args.image_ref,
                        lease_id=args.lease_id,
                        cache_dir=cache_dir,
                        artifact_path=artifact_path,
                        partial_path=partial_path,
                        probe=probe,
                        downloaded_bytes=resume_from,
                        complete=False,
                    ),
                )
                write_state(
                    state_primary,
                    state_fallback,
                    build_state(
                        status="downloading",
                        phase="downloading",
                        image_ref=args.image_ref,
                        payments_api_url=args.payments_api_url,
                        lease_id=args.lease_id,
                        cache_dir=cache_dir,
                        artifact_path=artifact_path,
                        partial_path=partial_path,
                        total_bytes=probe.total_bytes,
                        downloaded_bytes=resume_from,
                        action=action,
                        resumed=resumed,
                        resume_from_bytes=resume_from,
                        **state_context,
                    ),
                )

                download_stderr_path.parent.mkdir(parents=True, exist_ok=True)
                with download_stderr_path.open("wb") as download_err_fp:
                    proc = subprocess.Popen(
                        [
                            "curl",
                            "-fL",
                            "--connect-timeout",
                            "10",
                            "--retry",
                            "3",
                            "--retry-delay",
                            "2",
                            "--retry-connrefused",
                            "-sS",
                            "-C",
                            "-",
                            "-o",
                            str(partial_path),
                            args.url,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=download_err_fp,
                    )

                    try:
                        while True:
                            rc = proc.poll()
                            downloaded = partial_path.stat().st_size if partial_path.exists() else 0
                            reporter.render(downloaded)
                            write_state(
                                state_primary,
                                state_fallback,
                                build_state(
                                    status="downloading",
                                    phase="downloading",
                                    image_ref=args.image_ref,
                                    payments_api_url=args.payments_api_url,
                                    lease_id=args.lease_id,
                                    cache_dir=cache_dir,
                                    artifact_path=artifact_path,
                                    partial_path=partial_path,
                                    total_bytes=probe.total_bytes,
                                    downloaded_bytes=downloaded,
                                    action=action,
                                    resumed=resumed,
                                    resume_from_bytes=resume_from,
                                    **state_context,
                                ),
                            )
                            if rc is not None:
                                break
                            time.sleep(0.5 if reporter.is_tty else 1.0)
                    finally:
                        if proc.poll() is None:
                            proc.kill()
                            proc.wait()

                downloaded = partial_path.stat().st_size if partial_path.exists() else 0
                reporter.render(downloaded, final=True)
                if proc.returncode != 0:
                    write_state(
                        state_primary,
                        state_fallback,
                        build_state(
                            status="error",
                            phase="downloading",
                            image_ref=args.image_ref,
                            payments_api_url=args.payments_api_url,
                            lease_id=args.lease_id,
                            cache_dir=cache_dir,
                            artifact_path=artifact_path,
                            partial_path=partial_path,
                            total_bytes=probe.total_bytes,
                            downloaded_bytes=downloaded,
                            action=action,
                            resumed=resumed,
                            resume_from_bytes=resume_from,
                            **state_context,
                            detail=f"artifact download failed (curl exit {proc.returncode})",
                        ),
                    )
                    atomic_write_json(
                        metadata_path,
                        build_metadata(
                            image_ref=args.image_ref,
                            lease_id=args.lease_id,
                            cache_dir=cache_dir,
                            artifact_path=artifact_path,
                            partial_path=partial_path,
                            probe=probe,
                            downloaded_bytes=downloaded,
                            complete=False,
                        ),
                    )
                    raise DownloadError(f"artifact download failed (curl exit {proc.returncode})")

                if downloaded != probe.total_bytes:
                    write_state(
                        state_primary,
                        state_fallback,
                        build_state(
                            status="error",
                            phase="downloading",
                            image_ref=args.image_ref,
                            payments_api_url=args.payments_api_url,
                            lease_id=args.lease_id,
                            cache_dir=cache_dir,
                            artifact_path=artifact_path,
                            partial_path=partial_path,
                            total_bytes=probe.total_bytes,
                            downloaded_bytes=downloaded,
                            action=action,
                            resumed=resumed,
                            resume_from_bytes=resume_from,
                            **state_context,
                            detail=(
                                f"artifact size mismatch after download (have {downloaded} bytes want {probe.total_bytes})"
                            ),
                        ),
                    )
                    raise DownloadError(
                        f"artifact size mismatch after download (have {downloaded} bytes want {probe.total_bytes})"
                    )

                shutil.move(str(partial_path), str(artifact_path))
                atomic_write_json(
                    metadata_path,
                    build_metadata(
                        image_ref=args.image_ref,
                        lease_id=args.lease_id,
                        cache_dir=cache_dir,
                        artifact_path=artifact_path,
                        partial_path=partial_path,
                        probe=probe,
                        downloaded_bytes=probe.total_bytes,
                        complete=True,
                    ),
                )
                write_state(
                    state_primary,
                    state_fallback,
                    build_state(
                        status="downloaded",
                        phase="downloaded",
                        image_ref=args.image_ref,
                        payments_api_url=args.payments_api_url,
                        lease_id=args.lease_id,
                        cache_dir=cache_dir,
                        artifact_path=artifact_path,
                        partial_path=partial_path,
                        total_bytes=probe.total_bytes,
                        downloaded_bytes=probe.total_bytes,
                        action=action,
                        resumed=resumed,
                        resume_from_bytes=resume_from,
                        **state_context,
                    ),
                )

            payload = {
                "artifact_path": str(artifact_path),
                "artifact_partial_path": str(partial_path),
                "artifact_cache_dir": str(cache_dir),
                "artifact_total_bytes": probe.total_bytes,
                "artifact_downloaded_bytes": probe.total_bytes,
                "artifact_download_percent": 100.0,
                "artifact_resumed": bool(resumed),
                "artifact_resume_from_bytes": int(resume_from),
                "artifact_download_action": action,
                "downloaded_bytes": probe.total_bytes,
                "progress_percent": 100.0,
                "can_resume": resume_possible(
                    {
                        "artifact_local_path": str(artifact_path),
                        "artifact_partial_path": str(partial_path),
                        "can_resume": True,
                    },
                    probe.total_bytes,
                    probe.total_bytes,
                ),
                "job_id": state_context["job_id"],
                "work_dir": str(work_dir) if work_dir is not None else None,
            }
            print(json.dumps(payload, sort_keys=True))
            return 0
    except DownloadError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
