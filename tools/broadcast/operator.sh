#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.broadcast.yml"

TARGET_HOME="${HOME}"
if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
  TARGET_HOME="$(getent passwd "${SUDO_USER}" 2>/dev/null | cut -d: -f6 || true)"
  [[ -n "$TARGET_HOME" ]] || TARGET_HOME="${HOME}"
fi

BROADCAST_DIR="${EMBODY_BROADCAST_DIR:-${TARGET_HOME}/.embody/broadcast}"
CONFIG_FILE="${BROADCAST_DIR}/config.json"
DESTINATION_FILE="${BROADCAST_DIR}/rtmp-url"
STATE_DIR="${BROADCAST_DIR}/state"
STATE_FILE="${STATE_DIR}/state.json"
PROJECT_NAME="${EMBODY_BROADCAST_PROJECT_NAME:-vtuber-broadcast}"
CONTAINER_NAME="vtuber-broadcast-bridge"
NETWORK_NAME="vtuber_network"

BROADCAST_ENABLED="0"
BROADCAST_MODE="rtmp"
BROADCAST_SIGNALING_URL="ws://vtuber-unreal-signaling:80"
BROADCAST_STREAMER_ID=""

usage() {
  cat <<'EOF'
Embody optional RTMP broadcast

Usage:
  ./scripts/embody_cli.sh broadcast configure [options]
  ./scripts/embody_cli.sh broadcast start
  ./scripts/embody_cli.sh broadcast stop
  ./scripts/embody_cli.sh broadcast status [--json]
  ./scripts/embody_cli.sh broadcast logs [--follow] [--tail N]
  ./scripts/embody_cli.sh broadcast recover
  ./scripts/embody_cli.sh broadcast menu

Configure a real destination (the URL is never accepted as a command-line value):
  broadcast configure                       Prompt for the RTMP URL without echo
  broadcast configure --url-file <path>     Copy it from a private file
  broadcast configure --url-env <NAME>      Read it from an environment variable
  broadcast configure --url-stdin           Read one line from standard input

Other configure modes:
  broadcast configure --test                Local fake source/sink; no game/account/GPU
  broadcast configure --disable             Stop, disable, and remove the stored URL

Optional source selection:
  --signaling-url <ws://...>                 Default: ws://vtuber-unreal-signaling:80
  --streamer-id <id>                         Default: first available streamer

Security:
  The destination is stored at ~/.embody/broadcast/rtmp-url with mode 0600.
  It is never written to config.json, Compose interpolation, process arguments,
  status output, or normal bridge logs. Use --url-file/--url-stdin for automation
  rather than putting a destination on a shell command line.
EOF
}

ensure_python() {
  command -v python3 >/dev/null 2>&1 || {
    echo "broadcast: missing dependency: python3" >&2
    return 1
  }
}

ensure_storage() {
  umask 077
  mkdir -p "$BROADCAST_DIR" "$STATE_DIR"
  chmod 700 "$BROADCAST_DIR" "$STATE_DIR" 2>/dev/null || true
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$BROADCAST_DIR" "$STATE_DIR" 2>/dev/null || true
  fi
}

load_config() {
  BROADCAST_ENABLED="0"
  BROADCAST_MODE="rtmp"
  BROADCAST_SIGNALING_URL="ws://vtuber-unreal-signaling:80"
  BROADCAST_STREAMER_ID=""
  [[ -f "$CONFIG_FILE" ]] || return 0
  ensure_python || return 1

  local line
  if ! line="$(CONFIG_FILE="$CONFIG_FILE" python3 - <<'PY'
import json
import os
import sys

path = os.environ.get("CONFIG_FILE") or ""
try:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
except Exception as exc:
    print(f"broadcast: invalid local config: {exc}", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(data, dict):
    print("broadcast: invalid local config (expected an object)", file=sys.stderr)
    raise SystemExit(1)
mode = str(data.get("mode") or "rtmp").strip().lower()
if mode not in {"rtmp", "test"}:
    print("broadcast: invalid local mode", file=sys.stderr)
    raise SystemExit(1)
signaling = str(data.get("signaling_url") or "ws://vtuber-unreal-signaling:80").strip()
streamer = str(data.get("streamer_id") or "").strip()
for value in (mode, signaling, streamer):
    if any(char in value for char in ("\t", "\r", "\n", "\x00")):
        print("broadcast: local config contains invalid control characters", file=sys.stderr)
        raise SystemExit(1)
print("\t".join(("1" if data.get("enabled") is True else "0", mode, signaling, streamer)))
PY
  )"; then
    return 1
  fi
  IFS=$'\t' read -r BROADCAST_ENABLED BROADCAST_MODE BROADCAST_SIGNALING_URL BROADCAST_STREAMER_ID <<<"$line"
}

write_config() {
  local enabled="$1" mode="$2" signaling="$3" streamer="$4"
  ensure_storage
  ensure_python
  CONFIG_FILE="$CONFIG_FILE" ENABLED="$enabled" MODE="$mode" SIGNALING="$signaling" STREAMER="$streamer" \
    python3 - <<'PY'
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ["CONFIG_FILE"])
data = {
    "version": 1,
    "enabled": os.environ.get("ENABLED") == "1",
    "mode": os.environ.get("MODE") or "rtmp",
    "signaling_url": os.environ.get("SIGNALING") or "ws://vtuber-unreal-signaling:80",
    "streamer_id": os.environ.get("STREAMER") or None,
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
fd, tmp_name = tempfile.mkstemp(prefix=".config.", dir=str(path.parent))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, path)
finally:
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        pass
PY
  chmod 600 "$CONFIG_FILE" 2>/dev/null || true
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$CONFIG_FILE" 2>/dev/null || true
  fi
}

validate_destination() {
  ensure_python || return 1
  PYTHONPATH="$SCRIPT_DIR" python3 -c \
    'import sys; from broadcast_bridge import validate_destination; validate_destination(sys.stdin.read())' \
    >/dev/null 2>&1
}

validate_signaling_url() {
  ensure_python || return 1
  python3 -c '
import sys
from urllib.parse import urlsplit
value = sys.stdin.read().strip()
try:
    parsed = urlsplit(value)
except Exception:
    raise SystemExit(1)
if parsed.scheme.lower() not in {"ws", "wss"} or not parsed.hostname:
    raise SystemExit(1)
if any(c in value for c in ("\r", "\n", "\x00", "\t")):
    raise SystemExit(1)
' >/dev/null 2>&1
}

validate_streamer_id() {
  local value="$1"
  # Bash variables cannot contain NUL; reject the remaining line-oriented
  # control characters that could corrupt the local JSON/tab parser.
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *$'\t'* ]]
}

path_is_inside_repo() {
  local path="$1"
  ensure_python || return 1
  PATH_TO_CHECK="$path" REPO_ROOT="$REPO_ROOT" python3 - <<'PY'
import os
from pathlib import Path
path = Path(os.environ["PATH_TO_CHECK"]).expanduser().resolve(strict=False)
repo = Path(os.environ["REPO_ROOT"]).resolve(strict=False)
try:
    path.relative_to(repo)
except ValueError:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

store_destination() {
  local value="$1"
  ensure_storage
  if path_is_inside_repo "$DESTINATION_FILE"; then
    echo "broadcast: refusing to store an RTMP destination inside the git checkout" >&2
    echo "broadcast: use the default ~/.embody/broadcast directory or set EMBODY_BROADCAST_DIR outside the repo" >&2
    return 1
  fi

  local tmp
  tmp="$(mktemp "${BROADCAST_DIR}/.rtmp-url.XXXXXX")"
  chmod 600 "$tmp"
  # printf is a shell builtin, so the value is not added to another process's
  # argument vector or environment.
  printf '%s' "$value" >"$tmp"
  mv "$tmp" "$DESTINATION_FILE"
  chmod 600 "$DESTINATION_FILE" 2>/dev/null || true
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$DESTINATION_FILE" 2>/dev/null || true
  fi
}

require_docker() {
  command -v docker >/dev/null 2>&1 || {
    echo "broadcast: missing dependency: docker" >&2
    return 1
  }
  docker info >/dev/null 2>&1 || {
    echo "broadcast: Docker daemon is not reachable" >&2
    return 1
  }
  docker compose version >/dev/null 2>&1 || {
    echo "broadcast: docker compose plugin is not available" >&2
    return 1
  }
}

broadcast_compose() {
  ensure_storage
  local destination_mount="/dev/null"
  if [[ "$BROADCAST_MODE" == "rtmp" && -f "$DESTINATION_FILE" ]]; then
    destination_mount="$DESTINATION_FILE"
  fi

  EMBODY_BROADCAST_MODE="$BROADCAST_MODE" \
  EMBODY_BROADCAST_SIGNALING_URL="$BROADCAST_SIGNALING_URL" \
  EMBODY_BROADCAST_STREAMER_ID="$BROADCAST_STREAMER_ID" \
  EMBODY_BROADCAST_RTMP_URL_FILE="$destination_mount" \
  EMBODY_BROADCAST_STATE_DIR="$STATE_DIR" \
    docker compose \
      --project-directory "$REPO_ROOT" \
      --project-name "$PROJECT_NAME" \
      -f "$COMPOSE_FILE" "$@"
}

stop_enabled_config_before_change() {
  if [[ "$BROADCAST_ENABLED" != "1" ]]; then
    return 0
  fi
  echo "broadcast: stopping the existing optional broadcast before changing configuration..." >&2
  require_docker || {
    echo "broadcast: configuration was not changed because the existing broadcast could not be stopped safely" >&2
    return 1
  }
  broadcast_compose down --remove-orphans
}

cmd_configure() {
  local selection="" url_file="" url_env="" signaling="" streamer=""
  local destination=""

  load_config
  signaling="$BROADCAST_SIGNALING_URL"
  streamer="$BROADCAST_STREAMER_ID"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --test)
        [[ -z "$selection" ]] || { echo "broadcast: choose only one configure mode" >&2; return 1; }
        selection="test"
        shift
        ;;
      --disable)
        [[ -z "$selection" ]] || { echo "broadcast: choose only one configure mode" >&2; return 1; }
        selection="disable"
        shift
        ;;
      --url-file)
        [[ -z "$selection" ]] || { echo "broadcast: choose only one destination input" >&2; return 1; }
        url_file="${2:-}"
        [[ -n "$url_file" ]] || { echo "broadcast: --url-file requires a path" >&2; return 1; }
        selection="url-file"
        shift 2
        ;;
      --url-env)
        [[ -z "$selection" ]] || { echo "broadcast: choose only one destination input" >&2; return 1; }
        url_env="${2:-}"
        [[ "$url_env" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "broadcast: --url-env requires a valid environment variable name" >&2; return 1; }
        selection="url-env"
        shift 2
        ;;
      --url-stdin)
        [[ -z "$selection" ]] || { echo "broadcast: choose only one destination input" >&2; return 1; }
        selection="url-stdin"
        shift
        ;;
      --signaling-url)
        signaling="${2:-}"
        [[ -n "$signaling" ]] || { echo "broadcast: --signaling-url requires a value" >&2; return 1; }
        shift 2
        ;;
      --streamer-id)
        streamer="${2:-}"
        [[ -n "$streamer" ]] || { echo "broadcast: --streamer-id requires a value" >&2; return 1; }
        shift 2
        ;;
      -h|--help|help)
        usage
        return 0
        ;;
      --url|--destination|--stream-key)
        echo "broadcast: refusing destination credentials on the command line" >&2
        echo "broadcast: use an echo-free prompt, --url-file, --url-env, or --url-stdin" >&2
        return 1
        ;;
      *)
        echo "broadcast: unknown configure option: $1" >&2
        return 1
        ;;
    esac
  done

  if ! printf '%s' "$signaling" | validate_signaling_url; then
    echo "broadcast: signaling URL must use ws:// or wss:// and include a host" >&2
    return 1
  fi
  if ! validate_streamer_id "$streamer"; then
    echo "broadcast: streamer id contains invalid control characters" >&2
    return 1
  fi

  if [[ -z "$selection" ]]; then
    if [[ -t 0 && -t 1 ]]; then
      read -r -s -p "RTMP/RTMPS destination URL (input hidden): " destination || true
      echo ""
      selection="prompt"
    else
      echo "broadcast: non-interactive configuration requires --url-file, --url-env, --url-stdin, --test, or --disable" >&2
      return 1
    fi
  fi

  case "$selection" in
    disable)
      stop_enabled_config_before_change
      rm -f "$DESTINATION_FILE"
      write_config "0" "rtmp" "$signaling" "$streamer"
      echo "Broadcast disabled. The optional broadcast Compose project is stopped."
      ;;
    test)
      stop_enabled_config_before_change
      rm -f "$DESTINATION_FILE"
      write_config "1" "test" "$signaling" "$streamer"
      echo "Broadcast configured in local test mode (fake source and fake sink)."
      echo "Next: ./scripts/embody_cli.sh broadcast start"
      ;;
    url-file)
      [[ -f "$url_file" ]] || { echo "broadcast: destination input file not found" >&2; return 1; }
      destination="$(<"$url_file")"
      ;;
    url-env)
      destination="${!url_env:-}"
      ;;
    url-stdin)
      IFS= read -r destination || true
      ;;
    prompt)
      ;;
    *)
      echo "broadcast: internal configure mode error" >&2
      return 1
      ;;
  esac

  if [[ "$selection" == "url-file" || "$selection" == "url-env" || "$selection" == "url-stdin" || "$selection" == "prompt" ]]; then
    if ! printf '%s' "$destination" | validate_destination; then
      echo "broadcast: destination must be a non-empty rtmp:// or rtmps:// URL with a host" >&2
      return 1
    fi
    stop_enabled_config_before_change
    store_destination "$destination"
    unset destination
    write_config "1" "rtmp" "$signaling" "$streamer"
    echo "Broadcast destination configured (value redacted)."
    echo "Stored privately at: $DESTINATION_FILE (mode 600)"
    echo "Next: ./scripts/embody_cli.sh broadcast start"
  fi
}

ensure_enabled_and_valid() {
  load_config
  if [[ "$BROADCAST_ENABLED" != "1" ]]; then
    echo "broadcast: disabled or not configured" >&2
    echo "broadcast: run './scripts/embody_cli.sh broadcast configure' or 'broadcast configure --test'" >&2
    return 1
  fi
  if [[ "$BROADCAST_MODE" == "rtmp" ]]; then
    [[ -s "$DESTINATION_FILE" ]] || {
      echo "broadcast: destination file is missing; configure the broadcast again" >&2
      return 1
    }
    if ! validate_destination <"$DESTINATION_FILE"; then
      echo "broadcast: stored destination is invalid; configure the broadcast again" >&2
      return 1
    fi
    chmod 600 "$DESTINATION_FILE" 2>/dev/null || true
  fi
}

ensure_network() {
  if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    docker network create "$NETWORK_NAME" >/dev/null
  fi
}

start_or_recover() {
  local action="$1"
  shift
  if [[ $# -gt 0 ]]; then
    case "$1" in
      -h|--help|help)
        echo "Usage: ./scripts/embody_cli.sh broadcast ${action}"
        return 0
        ;;
      *)
        echo "broadcast: unknown ${action} option: $1" >&2
        return 1
        ;;
    esac
  fi
  ensure_enabled_and_valid
  require_docker
  [[ -f "$COMPOSE_FILE" ]] || { echo "broadcast: missing compose file: $COMPOSE_FILE" >&2; return 1; }
  ensure_network
  rm -f "$STATE_FILE" 2>/dev/null || true
  broadcast_compose up -d --force-recreate broadcast-bridge
  if [[ "$action" == "recover" ]]; then
    echo "Broadcast bridge recreated; its retry supervisor is active."
  else
    echo "Broadcast bridge started; its retry supervisor is active."
  fi
  if [[ "${EMBODY_BROADCAST_START_WAIT_SECONDS:-1}" != "0" ]]; then
    sleep "${EMBODY_BROADCAST_START_WAIT_SECONDS:-1}"
  fi
  cmd_status
}

cmd_stop() {
  if [[ $# -gt 0 ]]; then
    case "$1" in
      -h|--help|help)
        echo "Usage: ./scripts/embody_cli.sh broadcast stop"
        return 0
        ;;
      *)
        echo "broadcast: unknown stop option: $1" >&2
        return 1
        ;;
    esac
  fi
  load_config
  require_docker
  broadcast_compose down --remove-orphans
  echo "Broadcast bridge stopped. WebRTC/signaling and recorder services were not changed."
}

container_snapshot() {
  local output
  if ! command -v docker >/dev/null 2>&1; then
    printf '%s\t%s\n' "unavailable" "none"
    return 0
  fi
  if ! docker info >/dev/null 2>&1; then
    printf '%s\t%s\n' "unavailable" "none"
    return 0
  fi
  output="$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  if [[ -z "$output" ]]; then
    printf '%s\t%s\n' "absent" "none"
    return 0
  fi
  printf '%s\t%s\n' "${output%%|*}" "${output#*|}"
}

cmd_status() {
  local json="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json="1"; shift ;;
      -h|--help|help)
        echo "Usage: ./scripts/embody_cli.sh broadcast status [--json]"
        return 0
        ;;
      *) echo "broadcast: unknown status option: $1" >&2; return 1 ;;
    esac
  done

  ensure_python
  ensure_storage
  local container_status container_health rc
  IFS=$'\t' read -r container_status container_health < <(container_snapshot)
  local args=(
    --config "$CONFIG_FILE"
    --state "$STATE_FILE"
    --destination-file "$DESTINATION_FILE"
    --container-status "$container_status"
    --container-health "$container_health"
  )
  [[ "$json" == "1" ]] && args+=(--json)
  if python3 "$SCRIPT_DIR/status.py" "${args[@]}"; then
    rc=0
  else
    rc=$?
  fi
  return "$rc"
}

cmd_logs() {
  local follow="0" tail="100"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--follow) follow="1"; shift ;;
      --tail)
        tail="${2:-}"
        [[ "$tail" =~ ^[0-9]+$ ]] || { echo "broadcast: --tail requires a non-negative integer" >&2; return 1; }
        shift 2
        ;;
      -h|--help|help)
        echo "Usage: ./scripts/embody_cli.sh broadcast logs [--follow] [--tail N]"
        return 0
        ;;
      *) echo "broadcast: unknown logs option: $1" >&2; return 1 ;;
    esac
  done
  require_docker
  local args=(logs --tail "$tail")
  [[ "$follow" == "1" ]] && args+=(-f)
  docker "${args[@]}" "$CONTAINER_NAME"
}

cmd_menu() {
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "broadcast: menu requires an interactive terminal" >&2
    return 1
  fi
  while true; do
    echo ""
    cmd_status || true
    cat <<'EOF'

Broadcast actions:
  1) Configure RTMP destination (hidden prompt)
  2) Configure local test mode
  3) Start
  4) Stop
  5) Recover (force recreate)
  6) Logs
  7) Disable and remove destination
  q) Back
EOF
    printf '> '
    local choice
    read -r choice || return 0
    case "$choice" in
      1) cmd_configure ;;
      2) cmd_configure --test ;;
      3) start_or_recover start || true ;;
      4) cmd_stop || true ;;
      5) start_or_recover recover || true ;;
      6) cmd_logs || true ;;
      7) cmd_configure --disable ;;
      q|Q) return 0 ;;
      *) echo "Unknown option." ;;
    esac
  done
}

main() {
  local command="${1:-status}"
  shift || true
  case "$command" in
    configure|config) cmd_configure "$@" ;;
    start|up) start_or_recover start "$@" ;;
    stop|down) cmd_stop "$@" ;;
    status|inspect|ps) cmd_status "$@" ;;
    logs) cmd_logs "$@" ;;
    recover|restart) start_or_recover recover "$@" ;;
    menu) cmd_menu "$@" ;;
    -h|--help|help) usage ;;
    *)
      echo "broadcast: unknown command: $command" >&2
      usage >&2
      return 1
      ;;
  esac
}

main "$@"
