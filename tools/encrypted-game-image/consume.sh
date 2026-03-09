#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

USE_COLOR="0"
USE_FX="0"
COLOR_MODE="auto"
FX_MODE="auto"

STYLE_RESET=""
STYLE_BOLD=""
STYLE_DIM=""
STYLE_RED=""
STYLE_GRN=""
STYLE_YLW=""
STYLE_CYN=""
STYLE_MAG=""

rollout_state_file_primary=""
rollout_state_file_fallback=""
cache_root_primary=""
cache_root_fallback=""
rollout_state_file_override=""
rollout_state_fallback_override=""
rollout_job_id=""
rollout_work_dir=""
artifact_local_path=""
artifact_partial_path=""
artifact_cache_dir=""
artifact_total_bytes=""
artifact_downloaded_bytes="0"
artifact_download_percent=""
artifact_resumed="0"
artifact_resume_from_bytes="0"
artifact_download_action=""
artifact_cache_mode="cache_resume"
artifact_can_resume=""
stream_no_cache="0"

usage() {
  cat <<'EOF'
Usage:
  consume.sh --payments-api-url <url> --image-ref <ref> [--artifact-url <url>] \
    [--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>] \
    [--invite-code-file <path> | --invite-code-env <ENV> | --invite-code <value>] \
    [--orch-id <id> --orch-address <0x...>]

Options:
  --payments-api-url     Payments backend base URL (example: http://<payments-host>:8081)
  --image-ref            Image ref registered in Payments licenses (example: ghcr.io/...:enc-v1)
  --artifact-url         Optional override: public/presigned URL to the encrypted artifact (.age). If omitted, Payments returns a fresh URL per lease.
  --orch-token           Orchestrator license token (NOT recommended; may leak via shell history)
  --orch-token-file      Read orchestrator license token from file (recommended). If missing and invite code is provided, this script will write the token here.
  --orch-token-env       Read orchestrator license token from env var name (recommended)
  --invite-code          One-time invite code (redeems into an orchestrator token)
  --invite-code-file     Read invite code from file (recommended)
  --invite-code-env      Read invite code from env var name (recommended)
  --orch-id              Orchestrator ID to register in Payments (required when redeeming invite)
  --orch-address         Orchestrator wallet address (0x...) (required when redeeming invite)
  --rollout-state-file   Explicit rollout state path to update while running
  --rollout-state-fallback Optional fallback rollout state path if primary is not writable
  --rollout-work-dir     Explicit working directory for rollout logs/probe artifacts
  --rollout-job-id       Rollout job id to persist in rollout state
  --stream-no-cache      Stream from the lease URL into age -> zstd -> docker load without caching the full .age artifact locally
  --no-heartbeat         Do not heartbeat the lease while loading
  --debug                Keep detailed stderr logs on disk (prints path on failure/success)
  --no-color             Disable ANSI colors
  --no-fx                Disable transition effects
EOF
}

die() {
  echo "${STYLE_RED}${STYLE_BOLD}✖${STYLE_RESET} $*" >&2
  exit 1
}

trim_whitespace() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

strip_wrapping_quotes() {
  local s="$1"
  if [[ "$s" == \"*\" && "$s" == *\" ]]; then
    s="${s#\"}"
    s="${s%\"}"
  fi
  if [[ "$s" == \'*\' && "$s" == *\' ]]; then
    s="${s#\'}"
    s="${s%\'}"
  fi
  printf '%s' "$s"
}

read_secret_file() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  tr -d '\n' < "$path"
}

normalize_secret() {
  local s="${1:-}"
  s="$(trim_whitespace "$s")"
  s="$(strip_wrapping_quotes "$s")"
  s="$(trim_whitespace "$s")"
  printf '%s' "$s"
}

write_secret_file() {
  local path="$1"
  local value="$2"
  local dir
  dir="$(dirname "$path")"
  umask 077
  mkdir -p "$dir"
  chmod 700 "$dir" 2>/dev/null || true
  printf '%s\n' "$value" > "$path"
  chmod 600 "$path" 2>/dev/null || true
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$dir" "$path" 2>/dev/null || true
  fi
}

write_json_file_atomic() {
  local path="$1"
  local json="$2"
  mkdir -p "$(dirname "$path")" 2>/dev/null || return 1
  local tmp
  tmp="$(mktemp "$(dirname "$path")/.tmp.XXXXXX" 2>/dev/null || true)"
  [[ -n "$tmp" ]] || return 1
  printf '%s\n' "$json" >"$tmp" || { rm -f "$tmp" >/dev/null 2>&1 || true; return 1; }
  mv "$tmp" "$path" || { rm -f "$tmp" >/dev/null 2>&1 || true; return 1; }
  return 0
}

write_state_json_best_effort() {
  local primary="$1"
  local fallback="$2"
  local json="$3"
  if write_json_file_atomic "$primary" "$json"; then
    printf '%s' "$primary"
    return 0
  fi
  if write_json_file_atomic "$fallback" "$json"; then
    printf '%s' "$fallback"
    return 0
  fi
  return 1
}

rollout_state_json() {
  python3 - <<'PY'
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ACTIVE_STATUSES = {"queued", "downloading", "decrypting", "loading", "applying"}
TERMINAL_STATUSES = {"downloaded", "staged", "applied", "error", "failed"}


def clean(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def read_existing(*paths: str) -> dict:
    for raw in paths:
        path = (raw or "").strip()
        if not path:
            continue
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            return data
    return {}


def int_or_none(name: str):
    raw = clean(name)
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def float_or_none(name: str):
    raw = clean(name)
    if not raw:
        return None
    try:
        return round(float(raw), 2)
    except Exception:
        return None


def value_bool_or_none(value):
    if isinstance(value, bool):
        return value
    raw = str(value or "").strip().lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return None


def resume_possible(data: dict, downloaded_bytes: int, total_bytes: int | None) -> bool:
    explicit = value_bool_or_none(data.get("can_resume"))
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


now = datetime.now(timezone.utc).isoformat()
existing = read_existing(clean("ROLLOUT_STATE_FILE_PRIMARY"), clean("ROLLOUT_STATE_FILE_FALLBACK"))
artifact_cache_mode = clean("ARTIFACT_CACHE_MODE") or (str(existing.get("artifact_cache_mode") or "").strip() or None)
artifact_can_resume = value_bool_or_none(clean("ARTIFACT_CAN_RESUME"))

status = clean("STATUS") or None
phase = clean("PHASE") or None
detail = clean("DETAIL") or None
job_id = clean("ROLLOUT_JOB_ID") or (str(existing.get("job_id") or "").strip() or None)
work_dir = clean("ROLLOUT_WORK_DIR") or (str(existing.get("work_dir") or "").strip() or None)
artifact_total_bytes = int_or_none("ARTIFACT_TOTAL_BYTES")
if artifact_total_bytes is None:
    current_total = existing.get("artifact_total_bytes")
    try:
        artifact_total_bytes = int(current_total) if current_total is not None else None
    except Exception:
        artifact_total_bytes = None
artifact_downloaded_bytes = int_or_none("ARTIFACT_DOWNLOADED_BYTES")
if artifact_downloaded_bytes is None:
    current_downloaded = existing.get("artifact_downloaded_bytes")
    try:
        artifact_downloaded_bytes = int(current_downloaded) if current_downloaded is not None else 0
    except Exception:
        artifact_downloaded_bytes = 0
artifact_download_percent = float_or_none("ARTIFACT_DOWNLOAD_PERCENT")
if artifact_download_percent is None and artifact_total_bytes and artifact_total_bytes > 0:
    artifact_download_percent = round(
        min(100.0, (float(artifact_downloaded_bytes) * 100.0) / float(artifact_total_bytes)),
        2,
    )
if artifact_download_percent is None:
    current_percent = existing.get("artifact_download_percent", existing.get("progress_percent"))
    try:
        artifact_download_percent = round(float(current_percent), 2) if current_percent is not None else 0.0
    except Exception:
        artifact_download_percent = 0.0

history = existing.get("history")
if not isinstance(history, list):
    history = []
previous_status = str(existing.get("status") or "").strip()
if status and status != previous_status:
    history = history + [{"status": status, "at": now}]

data = dict(existing)
updates = {
    "job_id": job_id,
    "status": status,
    "phase": phase,
    "detail": detail,
    "updated_at": now,
    "image_ref": clean("IMAGE_REF") or None,
    "payments_api_url": clean("PAYMENTS_API_URL") or None,
    "lease_id": clean("LEASE_ID") or None,
    "artifact_local_path": clean("ARTIFACT_LOCAL_PATH") or None,
    "artifact_partial_path": clean("ARTIFACT_PARTIAL_PATH") or None,
    "artifact_cache_dir": clean("ARTIFACT_CACHE_DIR") or None,
    "artifact_download_action": clean("ARTIFACT_DOWNLOAD_ACTION") or None,
    "artifact_cache_mode": artifact_cache_mode,
    "artifact_total_bytes": artifact_total_bytes,
    "artifact_downloaded_bytes": artifact_downloaded_bytes,
    "artifact_download_percent": artifact_download_percent,
    "artifact_resumed": value_bool_or_none(clean("ARTIFACT_RESUMED")),
    "artifact_resume_from_bytes": int_or_none("ARTIFACT_RESUME_FROM_BYTES"),
    "loaded_image_id": clean("LOADED_IMAGE_ID") or None,
    "work_dir": work_dir,
}
for key, value in updates.items():
    if value is not None:
        data[key] = value

data["history"] = history[-32:]
data["downloaded_bytes"] = artifact_downloaded_bytes
data["progress_percent"] = artifact_download_percent
if artifact_cache_mode == "stream_no_cache":
    for key in ("artifact_local_path", "artifact_partial_path", "artifact_cache_dir"):
        data.pop(key, None)
    data["artifact_resumed"] = False
    data["artifact_resume_from_bytes"] = 0
    data["can_resume"] = False
else:
    if artifact_can_resume is not None:
        data["can_resume"] = artifact_can_resume
    else:
        data["can_resume"] = resume_possible(data, artifact_downloaded_bytes, artifact_total_bytes)
if status:
    data["active"] = status in ACTIVE_STATUSES
    data["terminal"] = status in TERMINAL_STATUSES
    if status in TERMINAL_STATUSES:
        data["completed_at"] = now
        if status == "error":
            data["failed_at"] = now
        else:
            data.pop("failed_at", None)
    else:
        data.pop("completed_at", None)
        data.pop("failed_at", None)

print(json.dumps({k: v for k, v in data.items() if v is not None}, sort_keys=True))
PY
}

write_rollout_state() {
  local status="$1"
  local phase="$2"
  local detail="${3:-}"
  local loaded_image_id="${4:-}"
  local json=""
  json="$(
    STATUS="$status" \
    PHASE="$phase" \
    DETAIL="$detail" \
    LOADED_IMAGE_ID="$loaded_image_id" \
    ROLLOUT_JOB_ID="$rollout_job_id" \
    ROLLOUT_WORK_DIR="$rollout_work_dir" \
    ROLLOUT_STATE_FILE_PRIMARY="$rollout_state_file_primary" \
    ROLLOUT_STATE_FILE_FALLBACK="$rollout_state_file_fallback" \
    IMAGE_REF="$image_ref" \
    PAYMENTS_API_URL="$payments_api_url" \
    LEASE_ID="$lease_id" \
    ARTIFACT_LOCAL_PATH="$artifact_local_path" \
    ARTIFACT_PARTIAL_PATH="$artifact_partial_path" \
    ARTIFACT_CACHE_DIR="$artifact_cache_dir" \
    ARTIFACT_DOWNLOAD_ACTION="$artifact_download_action" \
    ARTIFACT_CACHE_MODE="$artifact_cache_mode" \
    ARTIFACT_CAN_RESUME="$artifact_can_resume" \
    ARTIFACT_TOTAL_BYTES="$artifact_total_bytes" \
    ARTIFACT_DOWNLOADED_BYTES="$artifact_downloaded_bytes" \
    ARTIFACT_DOWNLOAD_PERCENT="$artifact_download_percent" \
    ARTIFACT_RESUMED="$artifact_resumed" \
    ARTIFACT_RESUME_FROM_BYTES="$artifact_resume_from_bytes" \
    rollout_state_json
  )"
  write_state_json_best_effort "$rollout_state_file_primary" "$rollout_state_file_fallback" "$json" >/dev/null 2>&1 || true
}

prompt_input() {
  local prompt="$1"
  local default="${2:-}"
  local out=""
  if [[ -n "$default" ]]; then
    read -r -p "${prompt} [${default}]: " out </dev/tty || true
    out="$(trim_whitespace "$out")"
    if [[ -z "$out" ]]; then out="$default"; fi
  else
    read -r -p "${prompt}: " out </dev/tty || true
    out="$(trim_whitespace "$out")"
  fi
  printf '%s' "$out"
}

prompt_secret() {
  local prompt="$1"
  local out=""
  read -r -s -p "${prompt}: " out </dev/tty || true
  echo "" >/dev/tty || true
  out="$(trim_whitespace "$out")"
  printf '%s' "$out"
}

curl_json_post() {
  # Usage: curl_json_post <url> <payload_json> [header...]
  local url="$1"
  local payload="$2"
  shift 2

  local out http_code body
  out="$(curl -sS --connect-timeout 10 --max-time 60 -X POST \
    -H "Content-Type: application/json" \
    "$@" \
    -d "$payload" \
    -w $'\n%{http_code}' \
    "$url")" || return 1
  http_code="$(printf '%s' "$out" | tail -n1)"
  body="$(printf '%s' "$out" | sed '$d')"

  if [[ ! "$http_code" =~ ^[0-9]+$ ]]; then
    die "unexpected HTTP response from Payments (no status code)"
  fi
  if [[ "$http_code" -ge 400 ]]; then
    echo "" >&2
    echo "${STYLE_RED}${STYLE_BOLD}Payments error${STYLE_RESET} ${STYLE_DIM}(HTTP $http_code)${STYLE_RESET}" >&2
    echo "$body" >&2
    return 2
  fi
  printf '%s' "$body"
}

CURL_JSON_LAST_HTTP_CODE=""
CURL_JSON_LAST_BODY=""

curl_json_post_capture() {
  # Usage: curl_json_post_capture <url> <payload_json> [header...]
  # Sets globals CURL_JSON_LAST_HTTP_CODE and CURL_JSON_LAST_BODY.
  local url="$1"
  local payload="$2"
  shift 2

  local out http_code body
  out="$(curl -sS --connect-timeout 10 --max-time 60 -X POST \
    -H "Content-Type: application/json" \
    "$@" \
    -d "$payload" \
    -w $'\n%{http_code}' \
    "$url")" || return 1
  http_code="$(printf '%s' "$out" | tail -n1)"
  body="$(printf '%s' "$out" | sed '$d')"

  CURL_JSON_LAST_HTTP_CODE="$http_code"
  CURL_JSON_LAST_BODY="$body"

  if [[ ! "$http_code" =~ ^[0-9]+$ ]]; then
    return 3
  fi
  if [[ "$http_code" -ge 300 && "$http_code" -lt 400 ]]; then
    return 4
  fi
  if [[ "$http_code" -ge 400 ]]; then
    return 2
  fi
  return 0
}

is_tty() {
  [[ -t 2 ]]
}

supports_color() {
  is_tty || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  [[ -z "${NO_COLOR:-}" ]] || return 1
  return 0
}

supports_fx() {
  is_tty || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  [[ -z "${CI:-}" ]] || return 1
  return 0
}

init_ui() {
  case "$COLOR_MODE" in
    always) USE_COLOR="1" ;;
    never) USE_COLOR="0" ;;
    auto) if supports_color; then USE_COLOR="1"; else USE_COLOR="0"; fi ;;
    *) USE_COLOR="0" ;;
  esac

  case "$FX_MODE" in
    always) USE_FX="1" ;;
    never) USE_FX="0" ;;
    auto) if supports_fx; then USE_FX="1"; else USE_FX="0"; fi ;;
    *) USE_FX="0" ;;
  esac

  if [[ "$USE_COLOR" == "1" ]]; then
    STYLE_RESET=$'\033[0m'
    STYLE_BOLD=$'\033[1m'
    STYLE_DIM=$'\033[2m'
    STYLE_RED=$'\033[31m'
    STYLE_GRN=$'\033[32m'
    STYLE_YLW=$'\033[33m'
    STYLE_CYN=$'\033[36m'
    STYLE_MAG=$'\033[35m'
  fi
}

note() {
  echo "${STYLE_MAG}${STYLE_BOLD}▸${STYLE_RESET} ${STYLE_CYN}$*${STYLE_RESET}" >&2
}

warn() {
  echo "${STYLE_YLW}${STYLE_BOLD}⚠${STYLE_RESET} $*" >&2
}

ok() {
  echo "${STYLE_GRN}${STYLE_BOLD}✓${STYLE_RESET} $*" >&2
}

fx_dots() {
  local msg="$1"
  if [[ "$USE_FX" != "1" ]]; then
    note "$msg"
    return
  fi
  printf "%s" "${STYLE_DIM}${msg}${STYLE_RESET}" >&2
  for _ in 1 2 3; do
    sleep 0.15
    printf "." >&2
  done
  printf "\n" >&2
}

banner() {
  if ! is_tty; then
    return
  fi
	cat >&2 <<EOF
${STYLE_MAG}${STYLE_BOLD}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${STYLE_RESET}
${STYLE_MAG}${STYLE_BOLD}┃  EMBODY // GAME IMAGE LOADER                ┃${STYLE_RESET}
${STYLE_MAG}${STYLE_BOLD}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${STYLE_RESET}
EOF
}

progress_pipe() {
  local script rc
  script="$(mktemp)"
  rc=0
  cat >"$script" <<'PY'
import os
import select
import sys
import time


def human_bytes(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TB"

def human_duration(seconds: float) -> str:
    seconds = max(float(seconds), 0.0)
    s = int(seconds + 0.5)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h}h{m:02d}m{sec:02d}s"
    if m > 0:
        return f"{m}m{sec:02d}s"
    return f"{sec}s"


label = sys.argv[1] if len(sys.argv) > 1 else "stream"
use_tty = sys.stderr.isatty()
term = os.environ.get("TERM", "")
use_color = use_tty and term != "dumb" and not os.environ.get("NO_COLOR")

RESET = "\033[0m" if use_color else ""
DIM = "\033[2m" if use_color else ""
CYN = "\033[36m" if use_color else ""
MAG = "\033[35m" if use_color else ""
GRN = "\033[32m" if use_color else ""
YLW = "\033[33m" if use_color else ""
BOLD = "\033[1m" if use_color else ""
WHT = "\033[97m" if use_color else ""

bar_len = 24
pulse_len = 6

fd = sys.stdin.fileno()
out = sys.stdout.buffer
err = sys.stderr

start = time.time()
last_update = start
last_bytes_at = start
total = 0
delta_bytes = 0

def print_status(now: float, final: bool = False) -> None:
    global last_update, last_bytes_at, total, delta_bytes
    elapsed = max(now - start, 0.0001)
    since = max(now - last_update, 0.0001)
    inst_bps = delta_bytes / since
    avg_bps = total / elapsed
    idle = now - last_bytes_at

    # Ping-pong pulse bar
    span = bar_len - 1
    phase = int((now * 10) % (2 * span))
    pos = phase if phase <= span else (2 * span - phase)
    bar = ["-"] * bar_len
    for i in range(pulse_len):
        bar[(pos + i) % bar_len] = "#"
    bar_s = "".join(bar)

    idle_s = ""
    if idle >= 5 and not final:
        idle_s = f" {YLW}idle {idle:.0f}s{RESET}"

    line = (
        f"{CYN}[{label}]{RESET} "
        f"{MAG}[{bar_s}]{RESET} "
        f"{GRN}{human_bytes(total)}{RESET} "
        f"{BOLD}{WHT}{human_bytes(inst_bps)}/s{RESET} "
        f"{DIM}(avg {BOLD}{WHT}{human_bytes(avg_bps)}/s{RESET}{DIM}){RESET} "
        f"{DIM}elapsed {BOLD}{WHT}{human_duration(elapsed)}{RESET}{DIM}{RESET}"
        f"{idle_s}"
    )

    if use_tty:
        err.write("\r\033[2K" + line)
        if final:
            err.write("\n")
        err.flush()
    else:
        # Log periodically without spamming non-TTY logs.
        if final or (now - last_update) >= 15:
            err.write(line + "\n")
            err.flush()

    last_update = now
    delta_bytes = 0


try:
    while True:
        now = time.time()
        # Update UI even when upstream stalls.
        timeout = 0.25 if use_tty else 1.0
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            print_status(time.time())
            continue
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        out.write(chunk)
        total += len(chunk)
        delta_bytes += len(chunk)
        last_bytes_at = now
        # Refresh UI at most ~4x/sec.
        if use_tty and (now - last_update) >= 0.25:
            print_status(now)
except BrokenPipeError:
    # Downstream closed the pipe (likely due to an error).
    sys.exit(1)
finally:
    # Final status line
    print_status(time.time(), final=True)
PY
  python3 "$script" "$@" || rc=$?
  rm -f "$script" >/dev/null 2>&1 || true
  return "$rc"
}

docker_load_with_meter() {
  local script rc
  script="$(mktemp)"
  rc=0
  cat >"$script" <<'PY'
import os
import select
import subprocess
import sys
import time


def human_bytes(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TB"

def human_duration(seconds: float) -> str:
    seconds = max(float(seconds), 0.0)
    s = int(seconds + 0.5)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h}h{m:02d}m{sec:02d}s"
    if m > 0:
        return f"{m}m{sec:02d}s"
    return f"{sec}s"


label = sys.argv[1] if len(sys.argv) > 1 else "LOAD"
use_tty = sys.stderr.isatty()
term = os.environ.get("TERM", "")
use_color = use_tty and term != "dumb" and not os.environ.get("NO_COLOR")

RESET = "\033[0m" if use_color else ""
DIM = "\033[2m" if use_color else ""
RED = "\033[31m" if use_color else ""
GRN = "\033[32m" if use_color else ""
YLW = "\033[33m" if use_color else ""
CYN = "\033[36m" if use_color else ""
MAG = "\033[35m" if use_color else ""
BOLD = "\033[1m" if use_color else ""
WHT = "\033[97m" if use_color else ""

bar_len = 28
pulse_len = 7

fd = sys.stdin.fileno()
err = sys.stderr

start = time.time()
last_update = start
last_bytes_at = start
total = 0
delta_bytes = 0

docker_proc = None
docker_out = b""
docker_err = b""


def render(now: float, *, final: bool = False) -> None:
    global last_update, delta_bytes, total
    elapsed = max(now - start, 0.0001)
    since = max(now - last_update, 0.0001)
    inst_bps = delta_bytes / since
    avg_bps = total / elapsed
    idle = now - last_bytes_at

    span = bar_len - 1
    phase = int((now * 12) % (2 * span))
    pos = phase if phase <= span else (2 * span - phase)

    bar = ["░"] * bar_len
    for i in range(pulse_len):
        bar[(pos + i) % bar_len] = "█"
    bar_s = "".join(bar)

    idle_s = ""
    if idle >= 5 and not final:
        idle_s = f" {YLW}idle {idle:.0f}s{RESET}"

    line = (
        f"{MAG}{label}{RESET} "
        f"{CYN}⟦{bar_s}⟧{RESET} "
        f"{GRN}{human_bytes(total)}{RESET} "
        f"{BOLD}{WHT}{human_bytes(inst_bps)}/s{RESET} "
        f"{DIM}(avg {BOLD}{WHT}{human_bytes(avg_bps)}/s{RESET}{DIM}){RESET} "
        f"{DIM}elapsed {BOLD}{WHT}{human_duration(elapsed)}{RESET}{DIM}{RESET}"
        f"{idle_s}"
    )

    if use_tty:
        err.write("\r\033[2K" + line)
        if final:
            err.write("\n")
        err.flush()
    else:
        if final or (now - last_update) >= 15:
            err.write(line + "\n")
            err.flush()

    last_update = now
    delta_bytes = 0


def hint_block() -> str:
    return (
        f"{DIM}Hints:{RESET}\n"
        f"  - Ensure the artifact URL is a full https URL (if you pasted `PRESIGNED_URL=...`, remove the prefix).\n"
        f"  - If it's a presigned URL, it may be expired; request a fresh one.\n"
        f"  - Verify the URL is reachable from this host: `curl -fL --range 0-63 <url> | head -n1` should print `age-encryption.org/v1`.\n"
        f"    (For presigned GET URLs, `curl -I`/HEAD may 403 even when the URL is valid.)\n"
        f"  - If decryption fails, the token/artifact may not match the image ref; ask your admin.\n"
    )


try:
    while True:
        now = time.time()
        timeout = 0.25 if use_tty else 1.0
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            render(time.time())
            continue
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break

        if docker_proc is None:
            docker_proc = subprocess.Popen(
                ["docker", "load"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        assert docker_proc.stdin is not None
        docker_proc.stdin.write(chunk)
        total += len(chunk)
        delta_bytes += len(chunk)
        last_bytes_at = now

        if use_tty and (now - last_update) >= 0.25:
            render(now)

    if docker_proc is None:
        render(time.time(), final=True)
        err.write(f"{RED}error:{RESET} received 0 bytes after decrypt/decompress; cannot load image.\n")
        err.write(hint_block())
        sys.exit(1)

    # NOTE: Python's subprocess.communicate() may try to flush stdin; avoid
    # "ValueError: flush of closed file" by detaching stdin before calling it.
    stdin = docker_proc.stdin
    docker_proc.stdin = None
    if stdin is not None:
        stdin.close()
    docker_out, docker_err = docker_proc.communicate()
    render(time.time(), final=True)

    rc = docker_proc.returncode or 0
    if rc != 0:
        # Print docker output after the meter so it doesn't get overwritten.
        if docker_err:
            err.write(docker_err.decode("utf-8", errors="replace").rstrip() + "\n")
        err.write(hint_block())
        sys.exit(rc)

    if docker_out:
        err.write(docker_out.decode("utf-8", errors="replace").rstrip() + "\n")
except BrokenPipeError:
    sys.exit(1)
PY
  python3 "$script" "$@" || rc=$?
  rm -f "$script" >/dev/null 2>&1 || true
  return "$rc"
}

payments_api_url=""
image_ref=""
artifact_url=""
orch_token=""
orch_token_file=""
orch_token_env=""
invite_code=""
invite_code_file=""
invite_code_env=""
orch_id=""
orch_address=""
heartbeat="1"
debug="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --payments-api-url)
      payments_api_url="${2:-}"
      shift 2
      ;;
    --image-ref)
      image_ref="${2:-}"
      shift 2
      ;;
    --artifact-url)
      artifact_url="${2:-}"
      shift 2
      ;;
    --orch-token)
      orch_token="${2:-}"
      shift 2
      ;;
    --orch-token-file)
      orch_token_file="${2:-}"
      shift 2
      ;;
    --orch-token-env)
      orch_token_env="${2:-}"
      shift 2
      ;;
    --invite-code)
      invite_code="${2:-}"
      shift 2
      ;;
    --invite-code-file)
      invite_code_file="${2:-}"
      shift 2
      ;;
    --invite-code-env)
      invite_code_env="${2:-}"
      shift 2
      ;;
    --orch-id)
      orch_id="${2:-}"
      shift 2
      ;;
    --orch-address)
      orch_address="${2:-}"
      shift 2
      ;;
    --rollout-state-file)
      rollout_state_file_override="${2:-}"
      shift 2
      ;;
    --rollout-state-fallback)
      rollout_state_fallback_override="${2:-}"
      shift 2
      ;;
    --rollout-work-dir)
      rollout_work_dir="${2:-}"
      shift 2
      ;;
    --rollout-job-id)
      rollout_job_id="${2:-}"
      shift 2
      ;;
    --stream-no-cache)
      stream_no_cache="1"
      shift 1
      ;;
    --no-heartbeat)
      heartbeat="0"
      shift 1
      ;;
    --debug)
      debug="1"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --no-color)
      COLOR_MODE="never"
      shift 1
      ;;
    --no-fx)
      FX_MODE="never"
      shift 1
      ;;
    *)
      die "unknown arg: $1"
      ;;
  esac
done

if [[ "$stream_no_cache" == "1" ]]; then
  artifact_cache_mode="stream_no_cache"
  artifact_can_resume="0"
  artifact_download_action="stream_no_cache"
fi

if [[ -z "$payments_api_url" ]] && is_tty; then
  payments_api_url="$(prompt_input "Payments API URL" "${PAYMENTS_API_URL:-http://<payments-host>:8081}")"
fi
if [[ -z "$image_ref" ]] && is_tty; then
  image_ref="$(prompt_input "Image ref (must exist in Payments licenses)" "${IMAGE_REF:-}")"
fi

payments_api_url="$(normalize_secret "$payments_api_url")"
image_ref="$(normalize_secret "$image_ref")"
rollout_state_file_override="$(trim_whitespace "$rollout_state_file_override")"
rollout_state_fallback_override="$(trim_whitespace "$rollout_state_fallback_override")"
rollout_work_dir="$(trim_whitespace "$rollout_work_dir")"
rollout_job_id="$(trim_whitespace "$rollout_job_id")"

[[ -n "$payments_api_url" ]] || die "--payments-api-url is required"
[[ -n "$image_ref" ]] || die "--image-ref is required"
artifact_url="$(trim_whitespace "$artifact_url")"
artifact_url="${artifact_url#PRESIGNED_URL=}"
artifact_url="${artifact_url#ARTIFACT_URL=}"
artifact_url="$(strip_wrapping_quotes "$artifact_url")"
artifact_url="$(trim_whitespace "$artifact_url")"
if [[ -n "$artifact_url" ]] && [[ "$artifact_url" != http://* && "$artifact_url" != https://* ]]; then
  die "--artifact-url must be an http(s) URL (or omit it to let Payments provide one)"
fi
command -v curl >/dev/null 2>&1 || die "missing dependency: curl"
command -v jq >/dev/null 2>&1 || die "missing dependency: jq"
command -v zstd >/dev/null 2>&1 || die "missing dependency: zstd"
command -v docker >/dev/null 2>&1 || die "missing dependency: docker"
command -v age >/dev/null 2>&1 || die "missing dependency: age"
command -v python3 >/dev/null 2>&1 || die "missing dependency: python3"

init_ui
banner

if [[ -n "$orch_token_env" ]]; then
  orch_token="$(normalize_secret "${!orch_token_env:-}")"
fi
if [[ -n "$orch_token_file" ]]; then
  orch_token="$(normalize_secret "$(read_secret_file "$orch_token_file" 2>/dev/null || true)")"
fi

if [[ -n "$invite_code_env" ]]; then
  invite_code="$(normalize_secret "${!invite_code_env:-}")"
fi
if [[ -n "$invite_code_file" ]]; then
  invite_code="$(normalize_secret "$(read_secret_file "$invite_code_file" 2>/dev/null || true)")"
fi

# Determine the correct "home" to use for caching when running under sudo.
# Note: this script may run in minimal containers where $USER is unset.
target_user="${SUDO_USER:-${USER:-}}"
if [[ -z "$target_user" ]]; then
  target_user="$(id -un 2>/dev/null || echo root)"
fi
target_home=""
if command -v getent >/dev/null 2>&1; then
  target_home="$(getent passwd "$target_user" 2>/dev/null | cut -d: -f6 || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$(eval echo "~${target_user}" 2>/dev/null || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$HOME"
fi

if [[ -n "$rollout_state_file_override" ]]; then
  rollout_state_file_primary="$rollout_state_file_override"
else
  rollout_state_file_primary="${ROLLOUT_STATE_FILE:-/var/lib/vtuber/power-state/rollout_state.json}"
fi
if [[ -n "$rollout_state_fallback_override" ]]; then
  rollout_state_file_fallback="$rollout_state_fallback_override"
else
  rollout_state_file_fallback="${target_home}/.embody/rollout_state.json"
fi
cache_root_primary="${ENCRYPTED_GAME_IMAGE_CACHE_DIR:-$(dirname "$rollout_state_file_primary")/encrypted-game-image-cache}"
cache_root_fallback="${target_home}/.embody/encrypted-game-image-cache"
if [[ -z "$rollout_work_dir" ]] && [[ -n "$rollout_job_id" ]]; then
  rollout_work_dir="$(dirname "$rollout_state_file_primary")/rollout-work/${rollout_job_id}"
fi
download_helper="${SCRIPT_DIR}/resume_download.py"
if [[ "$stream_no_cache" != "1" ]]; then
  [[ -f "$download_helper" ]] || die "missing helper: $download_helper"
fi

# Auto-load a cached token if nothing was provided explicitly.
default_token_file="$target_home/.embody/orch-license-token.txt"
if [[ -z "$orch_token" ]] && [[ -z "$orch_token_file" ]] && [[ -f "$default_token_file" ]]; then
  orch_token="$(normalize_secret "$(read_secret_file "$default_token_file" 2>/dev/null || true)")"
  orch_token_file="$default_token_file"
fi

redeem_invite_to_token() {
  # Uses invite_code + orch_id + orch_address and writes token to orch_token_file (default: ~/.embody/orch-license-token.txt)
  [[ -n "$invite_code" ]] || return 1
  [[ -n "$orch_id" ]] || return 1
  [[ -n "$orch_address" ]] || return 1

  redeem_payload="$(jq -nc --arg code "$invite_code" --arg orchestrator_id "$orch_id" --arg address "$orch_address" '{code:$code,orchestrator_id:$orchestrator_id,address:$address}')"
  fx_dots "Redeeming invite code → orchestrator token"
  redeem_json="$(curl_json_post "$payments_api_url/api/licenses/invites/redeem" "$redeem_payload")" || return 2
  orch_token="$(normalize_secret "$(echo "$redeem_json" | jq -r '.token // empty')")"
  [[ -n "$orch_token" ]] || return 3

  if [[ -z "$orch_token_file" ]]; then
    orch_token_file="$default_token_file"
  fi
  write_secret_file "$orch_token_file" "$orch_token"
  ok "Invite redeemed; token stored at ${orch_token_file}"
  return 0
}

if [[ -z "$orch_token" ]]; then
  if [[ -z "$invite_code" ]] && is_tty; then
    note "No cached orchestrator token found; redeem an invite code once to mint a token."
    invite_code="$(prompt_secret "Invite code")"
    invite_code="$(normalize_secret "$invite_code")"
  fi
  if [[ -z "$orch_id" ]] && is_tty; then
    orch_id="$(prompt_input "Orchestrator ID (string identifier)" "${ORCHESTRATOR_ID:-}")"
    orch_id="$(normalize_secret "$orch_id")"
  fi
  if [[ -z "$orch_address" ]] && is_tty; then
    orch_address="$(prompt_input "Orchestrator wallet address (0x...)" "${ORCHESTRATOR_ADDRESS:-}")"
    orch_address="$(normalize_secret "$orch_address")"
  fi

  [[ -n "$invite_code" ]] || die "orchestrator token required (provide --orch-token-file/env, or redeem an invite code via --invite-code-file/env)"
  [[ -n "$orch_id" ]] || die "--orch-id is required when redeeming an invite code"
  [[ -n "$orch_address" ]] || die "--orch-address is required when redeeming an invite code"

  redeem_invite_to_token || die "failed to redeem invite code"
fi

payload="$(jq -nc --arg image_ref "$image_ref" '{image_ref:$image_ref}')"
fx_dots "Requesting a decryption lease from Payments"
lease_rc="0"
curl_json_post_capture "$payments_api_url/api/licenses/lease" "$payload" -H "Authorization: Bearer $orch_token" || lease_rc="$?"
lease_http_code="${CURL_JSON_LAST_HTTP_CODE:-}"
lease_body="${CURL_JSON_LAST_BODY:-}"

if [[ "$lease_rc" == "1" ]]; then
  die "failed to request lease (network error)"
elif [[ "$lease_rc" == "3" ]]; then
  die "failed to request lease (unexpected HTTP response; no status code)"
elif [[ "$lease_rc" == "4" ]]; then
  echo "" >&2
  echo "${STYLE_RED}${STYLE_BOLD}Payments error${STYLE_RESET} ${STYLE_DIM}(HTTP $lease_http_code)${STYLE_RESET}" >&2
  echo "$lease_body" >&2
  die "failed to request lease (unexpected redirect; check PAYMENTS_API_URL)"
elif [[ "$lease_rc" == "2" ]]; then
  echo "" >&2
  echo "${STYLE_RED}${STYLE_BOLD}Payments error${STYLE_RESET} ${STYLE_DIM}(HTTP $lease_http_code)${STYLE_RESET}" >&2
  echo "$lease_body" >&2

  if [[ ("$lease_http_code" == "401" || "$lease_http_code" == "403") && is_tty ]]; then
    warn "Payments rejected your cached token; redeem a fresh invite code (you only need to do this once per machine)."
    invite_code=""
    orch_token=""

    invite_code="$(prompt_secret "Invite code")"
    invite_code="$(normalize_secret "$invite_code")"
    if [[ -z "$orch_id" ]]; then
      orch_id="$(prompt_input "Orchestrator ID (string identifier)" "${ORCHESTRATOR_ID:-}")"
      orch_id="$(normalize_secret "$orch_id")"
    fi
    if [[ -z "$orch_address" ]]; then
      orch_address="$(prompt_input "Orchestrator wallet address (0x...)" "${ORCHESTRATOR_ADDRESS:-}")"
      orch_address="$(normalize_secret "$orch_address")"
    fi

    [[ -n "$invite_code" ]] || die "orchestrator token required (no invite code provided)"
    [[ -n "$orch_id" ]] || die "--orch-id is required when redeeming an invite code"
    [[ -n "$orch_address" ]] || die "--orch-address is required when redeeming an invite code"

    redeem_invite_to_token || die "failed to redeem invite code"

    fx_dots "Retrying decryption lease request"
    lease_rc="0"
    curl_json_post_capture "$payments_api_url/api/licenses/lease" "$payload" -H "Authorization: Bearer $orch_token" || lease_rc="$?"
    lease_http_code="${CURL_JSON_LAST_HTTP_CODE:-}"
    lease_body="${CURL_JSON_LAST_BODY:-}"

    if [[ "$lease_rc" != "0" ]]; then
      echo "" >&2
      echo "${STYLE_RED}${STYLE_BOLD}Payments error${STYLE_RESET} ${STYLE_DIM}(HTTP ${lease_http_code:-unknown})${STYLE_RESET}" >&2
      echo "$lease_body" >&2
      die "failed to request lease after redeem"
    fi
  else
    die "failed to request lease"
  fi
fi

lease_json="$lease_body"

lease_id="$(echo "$lease_json" | jq -r '.lease_id // .leaseId // .lease.lease_id // .lease.leaseId // .lease.id // empty' 2>/dev/null || true)"
secret_b64="$(echo "$lease_json" | jq -r '.secret_b64 // .secretB64 // .lease.secret_b64 // .lease.secretB64 // empty' 2>/dev/null || true)"
artifact_url_from_lease="$(echo "$lease_json" | jq -r '.artifact_url // .artifactUrl // .lease.artifact_url // .lease.artifactUrl // empty' 2>/dev/null || true)"
lease_seconds="$(echo "$lease_json" | jq -r '.lease_seconds // .leaseSeconds // .lease.lease_seconds // .lease.leaseSeconds // 900' 2>/dev/null || echo "900")"

describe_lease_response_best_effort() {
  local json="$1"
  local keys preview
  keys="$(echo "$json" | jq -r 'keys | join(",")' 2>/dev/null || true)"
  if [[ -n "$keys" ]]; then
    echo "Payments lease response keys: ${keys}" >&2
    preview="$(echo "$json" | jq -c '{
      lease_id: (.lease_id // .leaseId // .lease.lease_id // .lease.leaseId // .lease.id // null),
      expires_at: (.expires_at // .expiresAt // .lease.expires_at // .lease.expiresAt // null),
      lease_seconds: (.lease_seconds // .leaseSeconds // .lease.lease_seconds // .lease.leaseSeconds // null),
      secret_present: ((.secret_b64 // .secretB64 // .lease.secret_b64 // .lease.secretB64 // null) != null),
      artifact_url_present: ((.artifact_url // .artifactUrl // .lease.artifact_url // .lease.artifactUrl // null) != null),
      detail: (.detail // null)
    }' 2>/dev/null || true)"
    if [[ -n "$preview" ]]; then
      echo "Payments lease response preview: ${preview}" >&2
    fi
  else
    echo "Payments lease response (non-JSON): $(printf '%.200s' "$json")" >&2
  fi
}

if [[ -z "$lease_id" ]]; then
  describe_lease_response_best_effort "$lease_json"
  die "missing lease_id from payments response"
fi
if [[ -z "$secret_b64" ]]; then
  describe_lease_response_best_effort "$lease_json"
  die "missing secret_b64 from payments response"
fi

if [[ -z "$artifact_url" ]]; then
  artifact_url="$artifact_url_from_lease"
  artifact_url="$(trim_whitespace "$artifact_url")"
  artifact_url="${artifact_url#PRESIGNED_URL=}"
  artifact_url="${artifact_url#ARTIFACT_URL=}"
  artifact_url="$(strip_wrapping_quotes "$artifact_url")"
  artifact_url="$(trim_whitespace "$artifact_url")"
fi
[[ -n "$artifact_url" ]] || die "Payments did not provide an artifact_url for this image_ref; ask your admin to configure the artifact in Payments"
if [[ "$artifact_url" != http://* && "$artifact_url" != https://* ]]; then
  die "invalid artifact_url from Payments (expected http(s))"
fi
ok "Lease acquired (lease_id=${lease_id}, seconds=${lease_seconds})"

hb_pid=""
identity_file=""
log_dir=""
cleanup() {
  if [[ -n "$hb_pid" ]]; then
    kill "$hb_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$identity_file" ]]; then
    rm -f "$identity_file" >/dev/null 2>&1 || true
  fi
  if [[ -n "$log_dir" ]] && [[ "$debug" != "1" ]]; then
    rm -rf "$log_dir" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ "$heartbeat" == "1" ]]; then
  # Heartbeat at ~1/3 lease duration, minimum 30s.
  interval="$((lease_seconds / 3))"
  if [[ "$interval" -lt 30 ]]; then interval="30"; fi

  (
    while true; do
      sleep "$interval" || break
      curl -fsS --connect-timeout 5 --max-time 10 -X POST \
        -H "Authorization: Bearer $orch_token" \
        "$payments_api_url/api/licenses/lease/$lease_id/heartbeat" >/dev/null || true
    done
  ) &
  hb_pid="$!"
fi

identity_file="$(mktemp)"
chmod 600 "$identity_file"

# secret_b64 is expected to be base64(identity-file-bytes)
if command -v base64 >/dev/null 2>&1; then
  if ! printf '%s' "$secret_b64" | base64 -d >"$identity_file" 2>/dev/null; then
    printf '%s' "$secret_b64" | base64 -D >"$identity_file" 2>/dev/null || die "base64 decode not available"
  fi
else
  die "base64 decode not available"
fi
if ! grep -q '^AGE-SECRET-KEY-1' "$identity_file" 2>/dev/null; then
  die "Payments returned an invalid decryption identity (secret_b64 decoded but no AGE-SECRET-KEY-1 line found)"
fi

if [[ "$stream_no_cache" == "1" ]]; then
  note "Streaming encrypted artifact from the lease URL → decrypt → decompress → load game image (no local cache or resume)"
else
  note "Downloading encrypted artifact to local cache (resume-safe) → decrypt → decompress → load game image (this can take a while)"
fi
if [[ -n "$rollout_work_dir" ]]; then
  log_dir="${rollout_work_dir}/logs"
  mkdir -p "$log_dir"
else
  log_dir="$(mktemp -d)"
fi
chmod 700 "$log_dir"
curl_err="$log_dir/curl.err"
age_err="$log_dir/age.err"
zstd_err="$log_dir/zstd.err"
curl_head_err="$log_dir/curl.head.err"
curl_head_prefix="$log_dir/curl.head.prefix"
curl_head_headers="$log_dir/curl.head.headers"

print_err_tail() {
  local label="$1"
  local path="$2"
  if [[ -s "$path" ]]; then
    echo "" >&2
    echo "${STYLE_MAG}${STYLE_BOLD}${label}${STYLE_RESET}" >&2
    tail -n 60 "$path" >&2
  fi
}

extract_total_bytes_from_headers() {
  local headers_path="$1"
  python3 - "$headers_path" <<'PY'
import re
import sys
from pathlib import Path

content_range_re = re.compile(r"bytes\s+\d+-\d+/(\d+|\*)", re.IGNORECASE)
try:
    raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
except Exception:
    print("", end="")
    raise SystemExit(0)

blocks = []
current = []
for line in raw.splitlines():
    if line.startswith("HTTP/"):
        if current:
            blocks.append(current)
        current = [line]
        continue
    current.append(line)
if current:
    blocks.append(current)

headers = {}
if blocks:
    for line in blocks[-1][1:]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

content_range = headers.get("content-range", "")
match = content_range_re.search(content_range)
if match and match.group(1) != "*":
    print(match.group(1), end="")
else:
    content_length = headers.get("content-length", "")
    if content_length.isdigit():
        print(content_length, end="")
PY
}

probe_artifact_prefix_preview() {
  local prefix_path="$1"
  python3 - "$prefix_path" <<'PY'
import sys
from pathlib import Path

try:
    prefix = Path(sys.argv[1]).read_bytes()
except Exception:
    print("<unreadable>", end="")
    raise SystemExit(0)

line = prefix.splitlines()[0].decode("utf-8", errors="replace") if prefix else "<empty>"
print(line, end="")
PY
}

probe_artifact_header() {
  local url="$1"
  local prefix_path="$2"
  local headers_path="$3"
  local stderr_path="$4"

  mkdir -p "$(dirname "$prefix_path")" "$(dirname "$headers_path")" "$(dirname "$stderr_path")"

  if ! curl -fL \
    --connect-timeout 10 \
    --max-time 20 \
    --retry 2 \
    --retry-delay 1 \
    --retry-connrefused \
    --range 0-127 \
    -D "$headers_path" \
    -o "$prefix_path" \
    -sS \
    "$url" 2>"$stderr_path"; then
    return 1
  fi

  python3 - "$prefix_path" <<'PY'
import sys
from pathlib import Path

prefix = Path(sys.argv[1]).read_bytes()
if not prefix.startswith(b"age-encryption.org/v1"):
    raise SystemExit(1)
PY
}

cache_dir_for_image_ref() {
  local root="$1"
  local ref="$2"
  python3 - "$root" "$ref" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
image_ref = sys.argv[2]
slug = "".join(ch if ch.isalnum() else "-" for ch in image_ref.lower())
while "--" in slug:
    slug = slug.replace("--", "-")
slug = slug.strip("-")[:48] or "artifact"
digest = hashlib.sha256(image_ref.encode("utf-8")).hexdigest()[:16]
print(root / f"{slug}-{digest}", end="")
PY
}

remove_stream_cache_for_image_ref() {
  local ref="$1"
  local root=""
  local cache_dir=""

  for root in "$cache_root_primary" "$cache_root_fallback"; do
    [[ -n "$root" ]] || continue
    cache_dir="$(cache_dir_for_image_ref "$root" "$ref")"
    case "$cache_dir" in
      "$root"/*) ;;
      *)
        warn "Skipping unexpected cache cleanup target outside root: $cache_dir"
        continue
        ;;
    esac
    if [[ -e "$cache_dir" ]]; then
      if rm -rf -- "$cache_dir"; then
        ok "Removed cached encrypted artifact dir $cache_dir for stream/no-cache mode"
      else
        warn "Failed to remove cached encrypted artifact dir $cache_dir; continuing without cache cleanup"
      fi
    fi
  done
}

if [[ "$stream_no_cache" == "1" ]]; then
  note "Validating artifact header for stream/no-cache mode"
  artifact_local_path=""
  artifact_partial_path=""
  artifact_cache_dir=""
  artifact_total_bytes=""
  artifact_downloaded_bytes="0"
  artifact_download_percent="0"
  artifact_resume_from_bytes="0"
  artifact_resumed="0"
  write_rollout_state "downloading" "downloading" "Validating artifact header for stream/no-cache mode"

  set +e
  probe_artifact_header "$artifact_url" "$curl_head_prefix" "$curl_head_headers" "$curl_head_err"
  probe_rc="$?"
  set -e
  if [[ "$probe_rc" -ne 0 ]]; then
    write_rollout_state "error" "downloading" "artifact header probe failed for stream/no-cache mode"
    print_err_tail "curl (header) stderr:" "$curl_head_err"
    if [[ "$probe_rc" -eq 1 ]]; then
      echo "" >&2
      echo "${STYLE_RED}${STYLE_BOLD}error:${STYLE_RESET} failed to fetch artifact header (URL expired or unreachable)." >&2
    else
      echo "" >&2
      echo "${STYLE_RED}${STYLE_BOLD}error:${STYLE_RESET} artifact does not look age-encrypted (expected header age-encryption.org/v1, got: $(probe_artifact_prefix_preview "$curl_head_prefix"))." >&2
    fi
    echo "" >&2
    if [[ "$debug" == "1" ]]; then
      note "Debug logs kept at: $log_dir"
    else
      note "Debug logs saved at: $log_dir"
      debug="1"
    fi
    die "failed to validate encrypted artifact for stream/no-cache mode; see errors above"
  fi

  artifact_total_bytes="$(extract_total_bytes_from_headers "$curl_head_headers")"
  if [[ -n "$artifact_total_bytes" ]]; then
    ok "Validated encrypted artifact header (${artifact_total_bytes} bytes total)"
  else
    ok "Validated encrypted artifact header"
  fi

  remove_stream_cache_for_image_ref "$image_ref"
  note "Streaming encrypted artifact directly into decrypt → decompress → docker load (no local cache or resume)"
  write_rollout_state "loading" "loading" "Streaming encrypted artifact directly into docker load (no local cache)"

  set +e
  curl -fL \
    --connect-timeout 10 \
    --retry 2 \
    --retry-delay 1 \
    --retry-connrefused \
    -sS \
    "$artifact_url" 2>"$curl_err" \
    | progress_pipe "download" \
    | age --decrypt -i "$identity_file" 2>"$age_err" \
    | zstd -d -c 2>"$zstd_err" \
    | docker_load_with_meter "LOADING"
  pipeline_rc=$? curl_rc="${PIPESTATUS[0]:-}" meter_rc="${PIPESTATUS[1]:-}" age_rc="${PIPESTATUS[2]:-}" zstd_rc="${PIPESTATUS[3]:-}" docker_rc="${PIPESTATUS[4]:-}"
  set -e

  if [[ "$pipeline_rc" -ne 0 ]]; then
    write_rollout_state "error" "loading" "streaming decrypt/decompress/load failed"
    echo "" >&2
    echo "${STYLE_RED}${STYLE_BOLD}error:${STYLE_RESET} image load pipeline failed (curl=${curl_rc:-?} meter=${meter_rc:-?} age=${age_rc:-?} zstd=${zstd_rc:-?} docker=${docker_rc:-?})." >&2
    print_err_tail "curl stderr:" "$curl_err"
    print_err_tail "age stderr:" "$age_err"
    print_err_tail "zstd stderr:" "$zstd_err"
    echo "" >&2
    if [[ "$debug" == "1" ]]; then
      note "Debug logs kept at: $log_dir"
    else
      note "Debug logs saved at: $log_dir"
      debug="1"
    fi
    die "failed to stream-load encrypted image; see errors above"
  fi

  if [[ -n "$artifact_total_bytes" ]]; then
    artifact_downloaded_bytes="$artifact_total_bytes"
  fi
  artifact_download_percent="100"
  write_rollout_state "staged" "staged" "Encrypted artifact streamed and image loaded into docker"
else
  note "Validating artifact header and downloading with resume support"
  download_cmd=(
    python3 "$download_helper"
    --url "$artifact_url"
    --image-ref "$image_ref"
    --payments-api-url "$payments_api_url"
    --lease-id "$lease_id"
    --state-file "$rollout_state_file_primary"
    --state-fallback "$rollout_state_file_fallback"
    --cache-root-primary "$cache_root_primary"
    --cache-root-fallback "$cache_root_fallback"
    --probe-prefix-path "$curl_head_prefix"
    --probe-headers-path "$curl_head_headers"
    --probe-stderr-path "$curl_head_err"
    --download-stderr-path "$curl_err"
  )
  if [[ -n "$rollout_job_id" ]]; then
    download_cmd+=(--job-id "$rollout_job_id")
  fi
  if [[ -n "$rollout_work_dir" ]]; then
    download_cmd+=(--work-dir "$rollout_work_dir")
  fi
  set +e
  download_json="$("${download_cmd[@]}")"
  download_rc="$?"
  set -e
  if [[ "$download_rc" -ne 0 ]]; then
    write_rollout_state "error" "downloading" "artifact download failed"
    print_err_tail "curl (header) stderr:" "$curl_head_err"
    print_err_tail "curl stderr:" "$curl_err"
    echo "" >&2
    if [[ "$debug" == "1" ]]; then
      note "Debug logs kept at: $log_dir"
    else
      note "Debug logs saved at: $log_dir"
      debug="1"
    fi
    die "failed to download encrypted artifact; see errors above"
  fi

  artifact_local_path="$(printf '%s' "$download_json" | jq -r '.artifact_path // empty' 2>/dev/null || true)"
  artifact_partial_path="$(printf '%s' "$download_json" | jq -r '.artifact_partial_path // empty' 2>/dev/null || true)"
  artifact_cache_dir="$(printf '%s' "$download_json" | jq -r '.artifact_cache_dir // empty' 2>/dev/null || true)"
  artifact_total_bytes="$(printf '%s' "$download_json" | jq -r '.artifact_total_bytes // empty' 2>/dev/null || true)"
  artifact_downloaded_bytes="$(printf '%s' "$download_json" | jq -r '.artifact_downloaded_bytes // 0' 2>/dev/null || echo "0")"
  artifact_download_percent="$(printf '%s' "$download_json" | jq -r '.artifact_download_percent // empty' 2>/dev/null || true)"
  artifact_resume_from_bytes="$(printf '%s' "$download_json" | jq -r '.artifact_resume_from_bytes // 0' 2>/dev/null || echo "0")"
  artifact_download_action="$(printf '%s' "$download_json" | jq -r '.artifact_download_action // empty' 2>/dev/null || true)"
  artifact_resumed="$(printf '%s' "$download_json" | jq -r 'if .artifact_resumed then "1" else "0" end' 2>/dev/null || echo "0")"

  [[ -n "$artifact_local_path" ]] || die "download helper did not return an artifact path"
  [[ -f "$artifact_local_path" ]] || die "download helper reported a missing artifact path: $artifact_local_path"

  case "$artifact_download_action" in
    reused_complete)
      ok "Using cached complete encrypted artifact at $artifact_local_path"
      ;;
    resumed)
      ok "Resumed encrypted artifact download from ${artifact_resume_from_bytes} bytes"
      ;;
    *)
      ok "Encrypted artifact downloaded to $artifact_local_path"
      ;;
  esac

  write_rollout_state "loading" "loading" "Decrypting cached artifact and streaming into docker load"

  set +e
  age --decrypt -i "$identity_file" "$artifact_local_path" 2>"$age_err" \
    | zstd -d -c 2>"$zstd_err" \
    | docker_load_with_meter "LOADING"
  pipeline_rc=$? age_rc="${PIPESTATUS[0]:-}" zstd_rc="${PIPESTATUS[1]:-}" docker_rc="${PIPESTATUS[2]:-}"
  set -e

  if [[ "$pipeline_rc" -ne 0 ]]; then
    write_rollout_state "error" "loading" "decrypt/decompress/load failed"
    echo "" >&2
    echo "${STYLE_RED}${STYLE_BOLD}error:${STYLE_RESET} image load pipeline failed (age=${age_rc:-?} zstd=${zstd_rc:-?} docker=${docker_rc:-?})." >&2
    print_err_tail "age stderr:" "$age_err"
    print_err_tail "zstd stderr:" "$zstd_err"
    echo "" >&2
    if [[ "$debug" == "1" ]]; then
      note "Debug logs kept at: $log_dir"
    else
      note "Debug logs saved at: $log_dir"
      debug="1"
    fi
    die "failed to load encrypted image; see errors above"
  fi

  artifact_downloaded_bytes="${artifact_total_bytes:-$artifact_downloaded_bytes}"
  artifact_download_percent="100"
  write_rollout_state "staged" "staged" "Encrypted artifact downloaded and image loaded into docker"
fi

if [[ "$debug" == "1" ]]; then
  note "Debug logs kept at: $log_dir"
else
  rm -rf "$log_dir" >/dev/null 2>&1 || true
  log_dir=""
fi

if is_tty; then
  cat >&2 <<EOF
${STYLE_MAG}${STYLE_BOLD}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${STYLE_RESET}
${STYLE_GRN}${STYLE_BOLD}┃  IMAGE LOADED // AUTHORIZED                  ┃${STYLE_RESET}
${STYLE_MAG}${STYLE_BOLD}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${STYLE_RESET}
EOF
fi
echo "Loaded encrypted image via lease_id=$lease_id"
