#!/usr/bin/env bash
set -euo pipefail

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

usage() {
  cat <<'EOF'
Usage:
  consume.sh --payments-api-url <url> --image-ref <ref> [--artifact-url <url>] (--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>)

Options:
  --payments-api-url     Payments backend base URL (example: http://3.141.111.200:8081)
  --image-ref            Image ref registered in Payments licenses (example: ghcr.io/...:enc-v1)
  --artifact-url         Optional override: public/presigned URL to the encrypted artifact (.age). If omitted, Payments returns a fresh URL per lease.
  --orch-token           Orchestrator license token (NOT recommended; may leak via shell history)
  --orch-token-file      Read orchestrator license token from file (recommended)
  --orch-token-env       Read orchestrator license token from env var name (recommended)
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
  python3 - "$@" <<'PY'
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
        f"{DIM}@{RESET} {human_bytes(inst_bps)}/s "
        f"{DIM}(avg {human_bytes(avg_bps)}/s){RESET}"
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
}

docker_load_with_meter() {
  python3 - "$@" <<'PY'
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
        f"{DIM}@{RESET} {human_bytes(inst_bps)}/s "
        f"{DIM}(avg {human_bytes(avg_bps)}/s){RESET}"
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

    assert docker_proc.stdin is not None
    docker_proc.stdin.close()
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
}

payments_api_url=""
image_ref=""
artifact_url=""
orch_token=""
orch_token_file=""
orch_token_env=""
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
  orch_token="${!orch_token_env:-}"
fi
if [[ -n "$orch_token_file" ]]; then
  [[ -f "$orch_token_file" ]] || die "--orch-token-file not found: $orch_token_file"
  orch_token="$(tr -d '\n' < "$orch_token_file")"
fi
[[ -n "$orch_token" ]] || die "orchestrator token required (use --orch-token-file or --orch-token-env)"

payload="$(jq -nc --arg image_ref "$image_ref" '{image_ref:$image_ref}')"
fx_dots "Requesting a decryption lease from Payments"
lease_json="$(curl -fsS --connect-timeout 10 --max-time 60 -X POST \
  -H "Authorization: Bearer $orch_token" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  "$payments_api_url/api/licenses/lease")"

lease_id="$(echo "$lease_json" | jq -r '.lease_id // empty')"
secret_b64="$(echo "$lease_json" | jq -r '.secret_b64 // empty')"
artifact_url_from_lease="$(echo "$lease_json" | jq -r '.artifact_url // empty')"
lease_seconds="$(echo "$lease_json" | jq -r '.lease_seconds // 900')"

[[ -n "$lease_id" ]] || die "missing lease_id from payments response"
[[ -n "$secret_b64" ]] || die "missing secret_b64 from payments response"

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
if command -v base64 >/dev/null 2>&1 && base64 --help 2>&1 | grep -q -- ' -d'; then
  printf '%s' "$secret_b64" | base64 -d >"$identity_file"
elif command -v base64 >/dev/null 2>&1 && base64 --help 2>&1 | grep -q -- ' -D'; then
  printf '%s' "$secret_b64" | base64 -D >"$identity_file"
else
  die "base64 decode not available"
fi
if ! grep -q '^AGE-SECRET-KEY-1' "$identity_file" 2>/dev/null; then
  die "Payments returned an invalid decryption identity (secret_b64 decoded but no AGE-SECRET-KEY-1 line found)"
fi

note "Downloading artifact → decrypt → decompress → load game image (this can take a while)"
log_dir="$(mktemp -d)"
chmod 700 "$log_dir"
curl_err="$log_dir/curl.err"
age_err="$log_dir/age.err"
zstd_err="$log_dir/zstd.err"
curl_head_err="$log_dir/curl.head.err"
curl_head_prefix="$log_dir/curl.head.prefix"

print_err_tail() {
  local label="$1"
  local path="$2"
  if [[ -s "$path" ]]; then
    echo "" >&2
    echo "${STYLE_MAG}${STYLE_BOLD}${label}${STYLE_RESET}" >&2
    tail -n 60 "$path" >&2
  fi
}

note "Validating artifact header (expects age-encryption.org/v1)"
set +e
curl -fL --connect-timeout 10 --max-time 20 --retry 2 --retry-delay 1 --retry-connrefused -sS --range 0-127 "$artifact_url" \
  -o "$curl_head_prefix" 2>"$curl_head_err"
curl_head_rc="$?"
set -e
if [[ "$curl_head_rc" -ne 0 ]]; then
  print_err_tail "curl (header) stderr:" "$curl_head_err"
  die "failed to fetch artifact header (URL expired/unreachable). Re-run to request a fresh lease."
fi
artifact_header="$(head -n1 "$curl_head_prefix" || true)"
if [[ "$artifact_header" != age-encryption.org/v1* ]]; then
  print_err_tail "curl (header) stderr:" "$curl_head_err"
  die "artifact does not look age-encrypted (expected header age-encryption.org/v1, got: ${artifact_header:-<empty>})"
fi
ok "Artifact header OK"

set +e
curl -fL --connect-timeout 10 --retry 3 --retry-delay 2 --retry-connrefused -sS "$artifact_url" 2>"$curl_err" \
  | age --decrypt -i "$identity_file" 2>"$age_err" \
  | zstd -d -c 2>"$zstd_err" \
  | docker_load_with_meter "LOADING"
pipeline_rc=$? curl_rc="${PIPESTATUS[0]:-}" age_rc="${PIPESTATUS[1]:-}" zstd_rc="${PIPESTATUS[2]:-}" docker_rc="${PIPESTATUS[3]:-}"
set -e

if [[ "$pipeline_rc" -ne 0 ]]; then
  echo "" >&2
  echo "${STYLE_RED}${STYLE_BOLD}error:${STYLE_RESET} image load pipeline failed (curl=${curl_rc:-?} age=${age_rc:-?} zstd=${zstd_rc:-?} docker=${docker_rc:-?})." >&2
  if [[ "${curl_rc:-}" == "23" ]]; then
    echo "${STYLE_DIM}note:${STYLE_RESET} curl exit 23 usually means a broken pipe (downstream decrypt/decompress/load exited early)." >&2
  fi
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
  die "failed to load encrypted image; see errors above"
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
