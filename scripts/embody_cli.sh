#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${REPO_ROOT}/.env"
TURN_ENV_FILE="${REPO_ROOT}/.env.turn"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.unreal.yml"
INSTANCE_COMPOSE_FILE="${REPO_ROOT}/docker-compose.unreal.instance.yml"
START_SCRIPT="${REPO_ROOT}/scripts/start_vtuber_unreal.sh"
ONBOARD_SCRIPT="${REPO_ROOT}/scripts/embody_onboard.sh"

TARGET_HOME="${HOME}"
if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
  TARGET_HOME="$(getent passwd "${SUDO_USER}" 2>/dev/null | cut -d: -f6 || true)"
  if [[ -z "$TARGET_HOME" ]]; then
    TARGET_HOME="$(eval echo "~${SUDO_USER}" 2>/dev/null || true)"
  fi
  [[ -n "$TARGET_HOME" ]] || TARGET_HOME="${HOME}"
fi

TOKEN_FILE_DEFAULT="${TARGET_HOME}/.embody/orch-license-token.txt"
PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT="${TARGET_HOME}/.embody/payments-viewer-token.txt"
REGISTRATION_STATE_FILE_DEFAULT="${TARGET_HOME}/.embody/orchestrator-registration.json"
VERIFY_LAST_FILE_DEFAULT="/var/lib/vtuber/power-state/verify_last.json"
VERIFY_LAST_FILE_FALLBACK="${TARGET_HOME}/.embody/verify_last.json"
ROLLOUT_STATE_FILE_DEFAULT="/var/lib/vtuber/power-state/rollout_state.json"
ROLLOUT_STATE_FILE_FALLBACK="${TARGET_HOME}/.embody/rollout_state.json"
CLUSTER_CONFIG_FILE_DEFAULT="${TARGET_HOME}/.embody/cluster.json"
DEFAULT_PAYMENTS_API_URL="http://3.141.111.200:8081"
DEFAULT_LICENSE_IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"

CLUSTER_MAX_SLOTS="20"
CLUSTER_SIGNALING_PORT_BASE="8080"
CLUSTER_RUNNER_PORT_BASE="9877"
CLUSTER_RECORDER_PORT_BASE="8889"
CLUSTER_GAME_TCP_PORT_BASE="7777"
CLUSTER_HOST_PROJECT_NAME="vtuber-host"

USE_COLOR="0"
STYLE_RESET=""
STYLE_BOLD=""
STYLE_DIM=""
STYLE_RED=""
STYLE_GRN=""
STYLE_YEL=""
STYLE_CYN=""
STYLE_MAG=""
STYLE_WHT=""
LAST_GIT_FETCH_AT="0"

usage() {
  cat <<'EOF'
Embody Orchestrator CLI

Usage:
  ./scripts/embody_cli.sh                  # Interactive dashboard (setup + status + actions)
  ./scripts/embody_cli.sh setup [args...]  # Run onboarding wizard
  ./scripts/embody_cli.sh overview         # Show a one-shot status dashboard
  ./scripts/embody_cli.sh upgrade          # Pull/recreate service containers (repo auto-updates on launch)
  ./scripts/embody_cli.sh license          # Show license token status
  ./scripts/embody_cli.sh license redeem   # Redeem invite code → store token
  ./scripts/embody_cli.sh rollout          # Rollout encrypted game image (wraps tools/encrypted-game-image/rollout.sh)
  ./scripts/embody_cli.sh register         # Register orchestrator in Payments (cached; skip when already registered)
  ./scripts/embody_cli.sh verify           # Full health/consistency checks (optionally auto-fix)
  ./scripts/embody_cli.sh power            # Sleep/wake via orchestrator-health /power
  ./scripts/embody_cli.sh cluster <cmd>    # Multi-instance cluster mode (plan/list/up/down/status/logs)

Day-to-day commands:
  ./scripts/embody_cli.sh start [--gpu <id|all|none>]   # Start stack (defaults to detached)
  ./scripts/embody_cli.sh stop
  ./scripts/embody_cli.sh restart
  ./scripts/embody_cli.sh status
  ./scripts/embody_cli.sh logs [service]
  ./scripts/embody_cli.sh health
  ./scripts/embody_cli.sh test
  ./scripts/embody_cli.sh config
  ./scripts/embody_cli.sh capacity
  ./scripts/embody_cli.sh payments         # Payments checks + token helper
  ./scripts/embody_cli.sh allowlists       # Check/fix Payments allowlists for /power + runner/recorder

Notes:
  - Onboarding is stored in `scripts/embody_onboard.sh` (called by `setup`).
  - License token default path: `~/.embody/orch-license-token.txt`
EOF
}

is_tty() {
  [[ -t 0 && -t 1 ]]
}

supports_color() {
  is_tty || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  [[ -z "${NO_COLOR:-}" ]] || return 1
  return 0
}

init_ui() {
  USE_COLOR="0"
  STYLE_RESET=""
  STYLE_BOLD=""
  STYLE_DIM=""
  STYLE_RED=""
  STYLE_GRN=""
  STYLE_YEL=""
  STYLE_CYN=""
  STYLE_MAG=""
  STYLE_WHT=""

  if supports_color; then
    USE_COLOR="1"
    STYLE_RESET=$'\033[0m'
    STYLE_BOLD=$'\033[1m'
    STYLE_DIM=$'\033[2m'
    STYLE_RED=$'\033[31m'
    STYLE_GRN=$'\033[32m'
    STYLE_YEL=$'\033[1;33m'
    STYLE_CYN=$'\033[1;36m'
    STYLE_MAG=$'\033[1;35m'
    STYLE_WHT=$'\033[1;37m'
  fi
}

ui_hr() {
  if [[ "$USE_COLOR" == "1" ]]; then
    printf '%s\n' "${STYLE_MAG}${STYLE_BOLD}════════════════════════════════════════════════════════════${STYLE_RESET}"
  else
    printf '%s\n' "============================================================"
  fi
}

ui_title() {
  local msg="$1"
  ui_hr
  if [[ "$USE_COLOR" == "1" ]]; then
    printf '%s\n' "${STYLE_MAG}${STYLE_BOLD}${msg}${STYLE_RESET}"
  else
    printf '%s\n' "$msg"
  fi
  ui_hr
}

ui_section() {
  local msg="$1"
  if [[ "$USE_COLOR" == "1" ]]; then
    printf '\n%s\n' "${STYLE_CYN}${STYLE_BOLD}${msg}${STYLE_RESET}"
  else
    printf '\n%s\n' "$msg"
  fi
}

ui_kv() {
  local key="$1" value="$2"
  if [[ "$USE_COLOR" == "1" ]]; then
    printf '%s%-22s%s %s\n' "${STYLE_DIM}" "${key}:" "${STYLE_RESET}" "$value"
  else
    printf '%-22s %s\n' "${key}:" "$value"
  fi
}

ui_check() {
  local name="$1" status="$2" detail="${3:-}"
  local tag=""
  case "$status" in
    OK)
      tag="${STYLE_GRN}${STYLE_BOLD}OK${STYLE_RESET}"
      ;;
    WARN)
      tag="${STYLE_YEL}${STYLE_BOLD}WARN${STYLE_RESET}"
      ;;
    FAIL)
      tag="${STYLE_RED}${STYLE_BOLD}FAIL${STYLE_RESET}"
      ;;
    SKIP)
      tag="${STYLE_DIM}${STYLE_BOLD}SKIP${STYLE_RESET}"
      ;;
    *)
      tag="${status}"
      ;;
  esac

  if [[ -n "$detail" ]]; then
    printf '%-18s %s %s\n' "${name}:" "$tag" "$detail"
  else
    printf '%-18s %s\n' "${name}:" "$tag"
  fi
}

ui_menu_item() {
  local key="$1" label="$2"
  if [[ "$USE_COLOR" == "1" ]]; then
    printf '  %s%s%s) %s%s%s\n' "${STYLE_MAG}${STYLE_BOLD}" "$key" "${STYLE_RESET}" "${STYLE_WHT}" "$label" "${STYLE_RESET}"
  else
    printf '  %s) %s\n' "$key" "$label"
  fi
}

prompt_default() {
  local label="$1" default="${2:-}" out=""
  if [[ -n "$default" ]]; then
    read -r -p "${label} [${default}]: " out || true
  else
    read -r -p "${label}: " out || true
  fi
  out="$(trim_whitespace "${out:-}")"
  if [[ -z "$out" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$out"
  fi
}

prompt_secret() {
  local label="$1" out=""
  read -r -s -p "${label}: " out || true
  echo ""
  out="$(trim_whitespace "${out:-}")"
  printf '%s' "$out"
}

prompt_yes_no() {
  local label="$1" default="${2:-y}" out=""
  local hint="[y/N]"
  if [[ "$default" == "y" ]]; then
    hint="[Y/n]"
  fi
  read -r -p "${label} ${hint}: " out || true
  out="$(trim_whitespace "${out:-}")"
  out="${out:-$default}"
  case "$out" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

read_env_value() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 1
  awk -v k="$key" -F= '
    $1 == k {
      sub(k "=", "", $0)
      print $0
      exit
    }
  ' "$file"
}

trim_whitespace() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

strip_inline_comment() {
  local s="$1"
  s="${s%%#*}"
  trim_whitespace "$s"
}

normalize_gpu_devices_csv() {
  local raw="${1:-}"
  raw="$(trim_whitespace "$raw")"
  raw="${raw// /}"
  if [[ -z "$raw" || "$raw" == "all" ]]; then
    printf '%s' "all"
    return 0
  fi
  if [[ "$raw" == "none" ]]; then
    printf '%s' "none"
    return 0
  fi
  printf '%s' "$raw"
}

get_vram_per_instance_mib() {
  local raw="${EMBODY_VRAM_PER_INSTANCE_MIB:-8192}"
  raw="$(trim_whitespace "${raw:-}")"
  if [[ ! "$raw" =~ ^[0-9]+$ ]]; then
    raw="8192"
  fi
  if [[ "$raw" -lt 1024 ]]; then
    raw="8192"
  fi
  printf '%s' "$raw"
}

get_auto_gpu_util_max_percent() {
  local raw="${EMBODY_AUTO_GPU_UTIL_MAX:-20}"
  raw="$(trim_whitespace "${raw:-}")"
  if [[ ! "$raw" =~ ^[0-9]+$ ]]; then
    raw="20"
  fi
  if [[ "$raw" -gt 100 ]]; then
    raw="100"
  fi
  printf '%s' "$raw"
}

extract_host_from_url() {
  local raw="$1"
  URL="$raw" python3 - <<'PY'
import os
from urllib.parse import urlparse

raw = (os.environ.get("URL") or "").strip()
if not raw:
    print("")
    raise SystemExit(0)
if "://" not in raw:
    raw = "http://" + raw
try:
    parsed = urlparse(raw)
except Exception:
    print("")
    raise SystemExit(0)
print(parsed.hostname or "")
PY
}

is_ipv4() {
  local candidate="$1"
  ADDR="$candidate" python3 - <<'PY'
import ipaddress
import os

raw = (os.environ.get("ADDR") or "").strip()
try:
    ip = ipaddress.ip_address(raw)
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if ip.version == 4 else 1)
PY
}

csv_has_token() {
  local csv="$1" token="$2"
  CSV="$csv" TOKEN="$token" python3 - <<'PY'
import os
csv = os.environ.get("CSV") or ""
token = (os.environ.get("TOKEN") or "").strip()
items = [part.strip() for part in csv.split(",") if part.strip()]
print("1" if token and token in items else "0")
PY
}

csv_add_token() {
  local csv="$1" token="$2"
  CSV="$csv" TOKEN="$token" python3 - <<'PY'
import os

csv = os.environ.get("CSV") or ""
token = (os.environ.get("TOKEN") or "").strip()
items = [part.strip() for part in csv.split(",") if part.strip()]
if token and token not in items:
    items.append(token)
print(",".join(items))
PY
}

upsert_env_kv() {
  local file="$1" key="$2" value="$3"
  [[ -f "$file" ]] || return 1
  local tmp
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { found=0 }
    $0 ~ ("^" key "=") {
      print key "=" value
      found=1
      next
    }
    { print }
    END { if (!found) print key "=" value }
  ' "$file" >"$tmp"
  mv "$tmp" "$file"
}

extract_first_nonlocal_allowlist_token() {
  local csv="$1"
  local raw token
  IFS=',' read -r -a raw <<<"$csv"
  for token in "${raw[@]}"; do
    token="$(trim_whitespace "$token")"
    token="$(strip_inline_comment "$token")"
    [[ -n "$token" ]] || continue
    case "$token" in
      127.0.0.1|::1|172.17.0.1|172.18.0.1) continue ;;
    esac
    printf '%s' "$token"
    return 0
  done
  return 1
}

read_file_trim() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  local value
  value="$(tr -d '\n' < "$path" 2>/dev/null || true)"
  value="$(trim_whitespace "${value:-}")"
  printf '%s' "$value"
}

first_existing_path() {
  local primary="$1" fallback="$2"
  if [[ -f "$primary" ]]; then
    printf '%s' "$primary"
    return 0
  fi
  if [[ -f "$fallback" ]]; then
    printf '%s' "$fallback"
    return 0
  fi
  printf '%s' "$primary"
  return 0
}

write_json_file_atomic() {
  local path="$1" json="$2"
  mkdir -p "$(dirname "$path")" 2>/dev/null || return 1
  local tmp
  tmp="$(mktemp "$(dirname "$path")/.tmp.XXXXXX" 2>/dev/null || true)"
  [[ -n "$tmp" ]] || return 1
  printf '%s\n' "$json" >"$tmp" || { rm -f "$tmp" >/dev/null 2>&1 || true; return 1; }
  mv "$tmp" "$path" || { rm -f "$tmp" >/dev/null 2>&1 || true; return 1; }
  return 0
}

write_state_json_best_effort() {
  local primary="$1" fallback="$2" json="$3"
  if write_json_file_atomic "$primary" "$json"; then
    echo "$primary"
    return 0
  fi
  if write_json_file_atomic "$fallback" "$json"; then
    echo "$fallback"
    return 0
  fi
  return 1
}

read_payments_viewer_token() {
  local token=""
  if [[ -n "${PAYMENTS_VIEWER_TOKEN:-}" ]]; then
    token="${PAYMENTS_VIEWER_TOKEN}"
  elif [[ -n "${PAYMENTS_ADMIN_TOKEN:-}" ]]; then
    token="${PAYMENTS_ADMIN_TOKEN}"
  elif [[ -f "$PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT" ]]; then
    token="$(read_file_trim "$PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT" || true)"
  fi
  token="$(trim_whitespace "${token:-}")"
  printf '%s' "$token"
}

read_orchestrator_token() {
  local token=""
  if [[ -n "${ORCHESTRATOR_TOKEN:-}" ]]; then
    token="${ORCHESTRATOR_TOKEN}"
  elif [[ -f "$TOKEN_FILE_DEFAULT" ]]; then
    token="$(read_file_trim "$TOKEN_FILE_DEFAULT" || true)"
  fi
  token="$(trim_whitespace "${token:-}")"
  printf '%s' "$token"
}

get_orchestrator_id() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ID" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  printf '%s' "$raw"
}

get_orchestrator_address() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ADDRESS" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  printf '%s' "$raw"
}

get_gpu_devices() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "NVIDIA_VISIBLE_DEVICES" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  printf '%s' "$raw"
}

get_payments_api_url() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "PAYMENTS_API_URL" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  printf '%s' "$raw"
}

get_edge_config_url() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "EDGE_CONFIG_URL" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  printf '%s' "$raw"
}

has_setup_state() {
  [[ -f "$COMPOSE_FILE" ]] || return 1
  [[ -f "$ENV_FILE" ]] || return 1
  local orch_id orch_addr
  orch_id="$(get_orchestrator_id)"
  orch_addr="$(get_orchestrator_address)"
  [[ -n "$orch_id" && -n "$orch_addr" ]] || return 1
  return 0
}

has_license_token() {
  [[ -s "$TOKEN_FILE_DEFAULT" ]]
}

detect_game_image_from_compose() {
  awk '
    /^[[:space:]]*unreal-game:[[:space:]]*$/ { in_game=1; next }
    in_game && /^[[:space:]]*image:[[:space:]]*/ {
      sub(/^[[:space:]]*image:[[:space:]]*/, "", $0)
      gsub(/[[:space:]]+$/, "", $0)
      print $0
      exit
    }
    in_game && /^[^[:space:]]/ { in_game=0 }
  ' "$1"
}

docker_image_present() {
  local ref="$1"
  command -v docker >/dev/null 2>&1 || return 1
  docker image inspect "$ref" >/dev/null 2>&1
}

df_available_bytes() {
  local path="$1"
  command -v df >/dev/null 2>&1 || return 1
  local out line avail_k
  out="$(df -Pk "$path" 2>/dev/null || true)"
  line="$(printf '%s\n' "$out" | tail -n 1 || true)"
  avail_k="$(printf '%s\n' "$line" | awk '{print $4}' 2>/dev/null || true)"
  if [[ ! "$avail_k" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  printf '%s' $(( avail_k * 1024 ))
}

docker_root_dir() {
  command -v docker >/dev/null 2>&1 || return 1
  docker info --format '{{.DockerRootDir}}' 2>/dev/null || true
}

docker_disk_free_bytes() {
  local root
  root="$(trim_whitespace "$(docker_root_dir 2>/dev/null || true)")"
  if [[ -n "$root" && -d "$root" ]]; then
    df_available_bytes "$root" || return 1
    return 0
  fi
  df_available_bytes "$REPO_ROOT" || return 1
}

require_min_free_gb() {
  local min_gb="$1" context="${2:-operation}"
  [[ -n "$min_gb" ]] || return 0
  if [[ ! "$min_gb" =~ ^[0-9]+$ ]]; then
    echo "${context}: invalid min_free_gb (expected integer GiB): ${min_gb}" >&2
    return 1
  fi
  if [[ "$min_gb" -le 0 ]]; then
    return 0
  fi
  local free
  free="$(docker_disk_free_bytes 2>/dev/null || true)"
  if [[ ! "$free" =~ ^[0-9]+$ ]]; then
    echo "${context}: warning: could not determine free disk; continuing." >&2
    return 0
  fi
  local want=$(( min_gb * 1024 * 1024 * 1024 ))
  if [[ "$free" -lt "$want" ]]; then
    echo "${context}: insufficient disk space: free=${free}B want>=${want}B (min_free_gb=${min_gb})" >&2
    return 1
  fi
  return 0
}

git_cmd() {
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]] && command -v sudo >/dev/null 2>&1; then
    sudo -H -u "$SUDO_USER" git -C "$REPO_ROOT" "$@"
  else
    git -C "$REPO_ROOT" "$@"
  fi
}

is_git_repo() {
  command -v git >/dev/null 2>&1 || return 1
  git_cmd rev-parse --is-inside-work-tree >/dev/null 2>&1
}

git_current_branch() {
  git_cmd rev-parse --abbrev-ref HEAD 2>/dev/null || true
}

git_is_clean() {
  local out
  out="$(git_cmd status --porcelain=v1 2>/dev/null || true)"
  [[ -z "$out" ]]
}

git_fetch_origin_main() {
  git_cmd fetch -q origin main >/dev/null 2>&1
}

maybe_git_fetch_origin_main() {
  local now last delta
  now="$(date +%s 2>/dev/null || echo 0)"
  last="${LAST_GIT_FETCH_AT:-0}"
  if [[ "$now" =~ ^[0-9]+$ && "$last" =~ ^[0-9]+$ ]]; then
    delta=$(( now - last ))
    if [[ "$delta" -lt 300 ]]; then
      return 0
    fi
  fi
  if git_fetch_origin_main; then
    LAST_GIT_FETCH_AT="$now"
    return 0
  fi
  return 1
}

git_ahead_behind_origin_main() {
  git_cmd rev-list --left-right --count HEAD...origin/main 2>/dev/null || true
}

git_remote_commit() {
  local ref="$1"
  git_cmd rev-parse --short "$ref" 2>/dev/null || true
}

auto_update_repo_or_reexec() {
  # Best-effort: keep operators on latest `origin/main` without requiring a manual `update` command.
  #
  # Safety:
  # - Skips when the repo is dirty (including untracked files).
  # - Skips when in detached HEAD (pinned tag).
  # - Auto-switches to `main` when on a different branch and the worktree is clean.
  # - Fast-forward only (no merges).
  if [[ "${EMBODY_CLI_NO_AUTO_UPDATE:-0}" == "1" || "${EMBODY_CLI_NO_AUTO_UPDATE:-}" == "true" ]]; then
    return 0
  fi
  if [[ "${EMBODY_CLI_AUTO_UPDATE_DONE:-0}" == "1" ]]; then
    return 0
  fi

  is_git_repo || return 0
  git_is_clean || return 0

  local branch
  branch="$(trim_whitespace "$(git_current_branch)")"
  [[ -n "$branch" ]] || return 0
  if [[ "$branch" == "HEAD" ]]; then
    return 0
  fi

  if [[ "$branch" != "main" ]]; then
    if ! git_cmd switch main >/dev/null 2>&1; then
      if ! git_cmd switch -c main origin/main >/dev/null 2>&1; then
        return 0
      fi
    fi
  fi

  git_fetch_origin_main || return 0
  LAST_GIT_FETCH_AT="$(date +%s 2>/dev/null || echo 0)"

  local ab ahead behind
  ab="$(git_ahead_behind_origin_main)"
  ahead="$(printf '%s' "$ab" | awk '{print $1}')"
  behind="$(printf '%s' "$ab" | awk '{print $2}')"

  if [[ -n "$behind" && "$behind" != "0" ]]; then
    local before after
    before="$(git_remote_commit HEAD)"
    if git_cmd pull -q --ff-only origin main >/dev/null 2>&1; then
      after="$(git_remote_commit HEAD)"
      if [[ -n "$before" && -n "$after" && "$before" != "$after" ]]; then
        echo "cli: auto-updated repo ${before} -> ${after}" >&2
        export EMBODY_CLI_AUTO_UPDATE_DONE=1
        exec "$SCRIPT_DIR/embody_cli.sh" "$@"
      fi
    fi
  fi
}

setup_complete() {
  has_setup_state || return 1
  has_license_token || return 1
  [[ -s "$TURN_ENV_FILE" ]] || return 1
  return 0
}

run_setup() {
  if [[ ! -x "$ONBOARD_SCRIPT" ]]; then
    echo "Onboarding script not found: $ONBOARD_SCRIPT" >&2
    echo "If you're on an older checkout, run: ./scripts/onboard_orchestrator.sh" >&2
    exit 1
  fi
  exec "$ONBOARD_SCRIPT" "$@"
}

run_stack() {
  if [[ ! -x "$START_SCRIPT" ]]; then
    echo "Stack script not found: $START_SCRIPT" >&2
    exit 1
  fi
  exec "$START_SCRIPT" "$@"
}

is_valid_eth_address() {
  local addr="$1"
  [[ "$addr" =~ ^0x[0-9a-fA-F]{40}$ ]]
}

is_valid_orchestrator_id() {
  local id="$1"
  [[ "$id" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]]
}

write_token_file() {
  local path="$1"
  local token="$2"
  local dir
  dir="$(dirname "$path")"

  umask 077
  mkdir -p "$dir"
  chmod 700 "$dir" 2>/dev/null || true
  printf '%s' "$token" >"$path"
  chmod 600 "$path" 2>/dev/null || true

  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$dir" "$path" 2>/dev/null || true
  fi
}

cmd_license() {
  local sub="${1:-}"
  shift || true

  case "$sub" in
    -h|--help|help)
      cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh license
  ./scripts/embody_cli.sh license redeem [options]

Commands:
  license           Show token status (path + present/missing)
  license redeem    Redeem an invite code and store the token locally
EOF
      ;;
    ""|status)
      local payments_url token_state
      payments_url="$(get_payments_api_url)"
      [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"
      if [[ -s "$TOKEN_FILE_DEFAULT" ]]; then
        token_state="present (${TOKEN_FILE_DEFAULT})"
      else
        token_state="missing (${TOKEN_FILE_DEFAULT})"
      fi
      echo "Payments API:  ${payments_url}"
      echo "License token: ${token_state}"
      ;;
    redeem)
      local payments_url orch_id orch_addr invite_code invite_code_file invite_code_env token_file
      local response http_code body payload url token

      payments_url=""
      orch_id=""
      orch_addr=""
      invite_code=""
      invite_code_file=""
      invite_code_env=""
      token_file="$TOKEN_FILE_DEFAULT"

      while [[ $# -gt 0 ]]; do
        case "$1" in
          --payments-api-url)
            payments_url="${2:-}"
            shift 2
            ;;
          --orchestrator-id|--orch-id)
            orch_id="${2:-}"
            shift 2
            ;;
          --orchestrator-address|--orch-address)
            orch_addr="${2:-}"
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
          --token-file)
            token_file="${2:-}"
            shift 2
            ;;
          -h|--help)
            cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh license redeem [options]

Options:
  --payments-api-url <url>         Payments backend base URL (default: PAYMENTS_API_URL from .env)
  --orchestrator-id <id>           Orchestrator ID (defaults from .env)
  --orchestrator-address <0x...>   Payout wallet address (defaults from .env)
  --invite-code <code>             One-time invite code (not recommended; may leak via shell history)
  --invite-code-file <path>        Read invite code from a file
  --invite-code-env <ENV>          Read invite code from an env var name
  --token-file <path>              Where to store the license token (default: ~/.embody/orch-license-token.txt)
EOF
            return 0
            ;;
          *)
            echo "Unknown arg for license redeem: $1" >&2
            return 1
            ;;
        esac
      done

      payments_url="$(trim_whitespace "${payments_url:-}")"
      orch_id="$(trim_whitespace "${orch_id:-}")"
      orch_addr="$(trim_whitespace "${orch_addr:-}")"
      invite_code="$(trim_whitespace "${invite_code:-}")"
      token_file="$(trim_whitespace "${token_file:-}")"

      if [[ -z "$payments_url" ]]; then
        payments_url="$(get_payments_api_url)"
      fi
      [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

      if [[ -z "$orch_id" ]]; then
        orch_id="$(get_orchestrator_id)"
      fi
      if [[ -z "$orch_addr" ]]; then
        orch_addr="$(get_orchestrator_address)"
      fi

      if [[ -n "$invite_code_env" ]]; then
        invite_code="${!invite_code_env:-}"
        invite_code="$(trim_whitespace "${invite_code:-}")"
      elif [[ -n "$invite_code_file" ]]; then
        [[ -f "$invite_code_file" ]] || { echo "Invite code file not found: $invite_code_file" >&2; return 1; }
        invite_code="$(tr -d '\n' < "$invite_code_file")"
        invite_code="$(trim_whitespace "${invite_code:-}")"
      fi

      if is_tty; then
        if [[ -z "$payments_url" ]]; then
          payments_url="$(prompt_default "Payments API URL" "$DEFAULT_PAYMENTS_API_URL")"
        fi
        if [[ -z "$orch_id" ]]; then
          orch_id="$(prompt_default "Orchestrator ID" "")"
        fi
        if [[ -z "$orch_addr" ]]; then
          orch_addr="$(prompt_default "Payout wallet (0x...)" "")"
        fi
        if [[ -z "$invite_code" ]]; then
          invite_code="$(prompt_secret "Invite code")"
        fi
      fi

      [[ -n "$payments_url" ]] || { echo "Missing payments API URL" >&2; return 1; }
      [[ -n "$orch_id" ]] || { echo "Missing orchestrator ID (set ORCHESTRATOR_ID in .env or pass --orchestrator-id)" >&2; return 1; }
      [[ -n "$orch_addr" ]] || { echo "Missing orchestrator address (set ORCHESTRATOR_ADDRESS in .env or pass --orchestrator-address)" >&2; return 1; }
      [[ -n "$invite_code" ]] || { echo "Missing invite code" >&2; return 1; }
      [[ -n "$token_file" ]] || { echo "Missing token file path" >&2; return 1; }

      if ! is_valid_orchestrator_id "$orch_id"; then
        echo "Invalid orchestrator ID: must be 1-64 chars (letters/numbers/dot/underscore/dash), starting with letter/number." >&2
        return 1
      fi
      if ! is_valid_eth_address "$orch_addr"; then
        echo "Invalid payout wallet: expected 0x + 40 hex chars." >&2
        return 1
      fi

      command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; return 1; }
      command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }

      url="${payments_url%/}/api/licenses/invites/redeem"
      payload="$(INVITE_CODE="$invite_code" ORCH_ID="$orch_id" ORCH_ADDRESS="$orch_addr" python3 - <<'PY'
import json
import os

payload = {
    "code": os.environ.get("INVITE_CODE", ""),
    "orchestrator_id": os.environ.get("ORCH_ID", ""),
    "address": os.environ.get("ORCH_ADDRESS", ""),
}
print(json.dumps(payload))
PY
      )"

      response="$(curl -sS -X POST -H "Content-Type: application/json" -d "$payload" \
        -w $'\n%{http_code}' "$url")" || true
      http_code="${response##*$'\n'}"
      body="${response%$'\n'*}"

      if [[ "$http_code" != "200" ]]; then
        case "$http_code" in
          404) echo "Invite code not found (or already redeemed). Ask your admin for a fresh code." >&2 ;;
          403) echo "Invite code rejected (wallet mismatch or revoked). Double-check your payout wallet and ask your admin for a new code." >&2 ;;
          409) echo "Invite code already redeemed (or redemption in progress). If you already redeemed earlier, reuse your token file at ${TOKEN_FILE_DEFAULT}." >&2 ;;
          410) echo "Invite code expired. Ask your admin for a fresh code." >&2 ;;
          *) echo "Invite redeem failed (HTTP $http_code)" >&2 ;;
        esac
        if [[ -n "$body" ]]; then
          echo "$body" >&2
        fi
        return 1
      fi

      token="$(BODY="$body" python3 - <<'PY'
import json
import os

raw = os.environ.get("BODY", "") or ""
try:
    data = json.loads(raw) if raw else {}
except Exception:
    data = {}
print(data.get("token", "") or "")
PY
      )"
      [[ -n "$token" ]] || { echo "Invite redeem succeeded but token was missing in response" >&2; return 1; }

      write_token_file "$token_file" "$token"
      echo "Invite redeemed; token stored at ${token_file}"
      ;;
    *)
      echo "Unknown license command: $sub" >&2
      echo "Run: ./scripts/embody_cli.sh license --help" >&2
      return 1
      ;;
  esac
}

cmd_rollout() {
  local payments_url image_ref token_file mode min_free_gb
  local passthrough=()

  payments_url=""
  image_ref="$DEFAULT_LICENSE_IMAGE_REF"
  token_file="$TOKEN_FILE_DEFAULT"
  mode="rollout"
  min_free_gb="15"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --stage|--stage-only)
        mode="stage"
        shift 1
        ;;
      --apply-staged|--apply)
        mode="apply_staged"
        shift 1
        ;;
      --min-free-gb)
        min_free_gb="${2:-}"
        shift 2
        ;;
      --payments-api-url)
        payments_url="${2:-}"
        shift 2
        ;;
      --image-ref)
        image_ref="${2:-}"
        shift 2
        ;;
      --artifact-url|--compose-file|--game-image)
        passthrough+=("$1" "${2:-}")
        shift 2
        ;;
      --no-verify|--no-color)
        passthrough+=("$1")
        shift 1
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh rollout [options]

Modes:
  --stage            Stage the encrypted image (download+decrypt+docker load) without restarting containers.
  --apply-staged      Apply the staged image while sleeping (force-recreate stopped game containers; next wake uses it).

Default behavior (no mode flags) runs a full rollout (stops stack, reloads image, restarts) via `tools/encrypted-game-image/rollout.sh`.

Options:
  --payments-api-url <url>   Payments backend (default: PAYMENTS_API_URL from .env)
  --image-ref <ref>          Image ref registered in Payments (default: ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1)
  --min-free-gb <n>          Require at least N GiB free disk before downloading/loading (default: 15)
  --no-verify                Skip health checks after restart
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for rollout: $1" >&2
        return 1
        ;;
    esac
  done

  if [[ -z "$payments_url" ]]; then
    payments_url="$(get_payments_api_url)"
  fi
  [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

  if [[ ! -s "$token_file" ]]; then
    echo "Missing license token at ${token_file}." >&2
    if is_tty && prompt_yes_no "Redeem an invite code now?" "y"; then
      cmd_license redeem --payments-api-url "$payments_url" --token-file "$token_file" || return 1
    else
      echo "Run: ./scripts/embody_cli.sh license redeem" >&2
      return 1
    fi
  fi

  case "$mode" in
    stage)
      require_min_free_gb "$min_free_gb" "rollout stage" || return 1
      [[ -x "$REPO_ROOT/tools/encrypted-game-image/consume.sh" ]] || { echo "Missing consume script: $REPO_ROOT/tools/encrypted-game-image/consume.sh" >&2; return 1; }

      "$REPO_ROOT/tools/encrypted-game-image/consume.sh" \
        --payments-api-url "$payments_url" \
        --orch-token-file "$token_file" \
        --image-ref "$image_ref"

      local game_image image_id json out_path
      game_image="$(detect_game_image_from_compose "$COMPOSE_FILE" 2>/dev/null || true)"
      image_id=""
      if [[ -n "$game_image" ]] && command -v docker >/dev/null 2>&1; then
        image_id="$(docker image inspect -f '{{.Id}}' "$game_image" 2>/dev/null || true)"
        image_id="$(trim_whitespace "${image_id:-}")"
      fi

      json="$(STATUS="staged" IMAGE_REF="$image_ref" PAYMENTS_URL="$payments_url" GAME_IMAGE="$game_image" IMAGE_ID="$image_id" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

def clean(s: str) -> str:
    return (s or "").strip()

data = {
    "status": clean(os.environ.get("STATUS")),
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "image_ref": clean(os.environ.get("IMAGE_REF")),
    "payments_api_url": clean(os.environ.get("PAYMENTS_URL")),
    "game_image": clean(os.environ.get("GAME_IMAGE")),
    "loaded_image_id": clean(os.environ.get("IMAGE_ID")) or None,
}
print(json.dumps(data, sort_keys=True))
PY
      )"

      out_path="$(write_state_json_best_effort "$ROLLOUT_STATE_FILE_DEFAULT" "$ROLLOUT_STATE_FILE_FALLBACK" "$json" || true)"
      if [[ -n "$out_path" ]]; then
        echo "rollout: staged (state: ${out_path})" >&2
      fi
      ;;
    apply_staged)
      command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; return 1; }
      command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }

      local payload out http_code body
      payload="$(PAYMENTS_URL="$payments_url" IMAGE_REF="$image_ref" python3 - <<'PY'
import json
import os

print(json.dumps({
  "payments_api_url": os.environ.get("PAYMENTS_URL") or "",
  "image_ref": os.environ.get("IMAGE_REF") or "",
  "skip_download": True,
  "recreate_stopped": True,
  "min_free_gb": 0,
}))
PY
      )"
      out="$(curl -sS --max-time 60 -X POST -H "Content-Type: application/json" -d "$payload" -w $'\n%{http_code}' http://127.0.0.1:9090/ops/rollout 2>/dev/null || true)"
      http_code="${out##*$'\n'}"
      body="${out%$'\n'*}"
      if [[ "$http_code" != "200" ]]; then
        echo "rollout: apply-staged failed (HTTP ${http_code})" >&2
        if [[ -n "$body" ]]; then
          echo "$body" >&2
        fi
        echo "Hint: ensure the stack is sleeping (power sleep) and POWER_ALLOWED_IPS allowlisting includes 127.0.0.1 (remote /ops is strict)." >&2
        echo "If you opted out of remote ops (EXPERIMENTAL_REMOTE_OPS=0), set it back to 1 and recreate orchestrator-health." >&2
        return 1
      fi
      echo "$body"
      ;;
    rollout)
      require_min_free_gb "$min_free_gb" "rollout" || return 1
      if [[ ! -x "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" ]]; then
        echo "Missing rollout script: $REPO_ROOT/tools/encrypted-game-image/rollout.sh" >&2
        return 1
      fi
      "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" \
        --payments-api-url "$payments_url" \
        --orch-token-file "$token_file" \
        --image-ref "$image_ref" \
        "${passthrough[@]}"
      ;;
    *)
      echo "Unknown rollout mode: $mode" >&2
      return 1
      ;;
  esac
}

cmd_config() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing .env at $ENV_FILE" >&2
    return 1
  fi
  local orch_id orch_addr payments_url allowlist turn_external gpu_devices
  orch_id="$(get_orchestrator_id)"
  orch_addr="$(get_orchestrator_address)"
  payments_url="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "PAYMENTS_API_URL" 2>/dev/null || true)")"
  allowlist="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
  turn_external="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "TURN_EXTERNAL_IP" 2>/dev/null || true)")"
  gpu_devices="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "NVIDIA_VISIBLE_DEVICES" 2>/dev/null || true)")"

  echo "Orchestrator ID:        ${orch_id:-<unset>}"
  echo "Payout wallet:          ${orch_addr:-<unset>}"
  echo "Payments API:           ${payments_url:-<unset>}"
  echo "Allowed caller IPs:     ${allowlist:-<unset>}"
  echo "TURN external IP:       ${turn_external:-<unset>}"
  echo "GPU devices:            ${gpu_devices:-all}"
  if [[ -s "$TOKEN_FILE_DEFAULT" ]]; then
    echo "License token:          present (${TOKEN_FILE_DEFAULT})"
  else
    echo "License token:          missing (${TOKEN_FILE_DEFAULT})"
  fi
  if [[ -s "$TURN_ENV_FILE" ]]; then
    echo "TURN env:               present (${TURN_ENV_FILE})"
  else
    echo "TURN env:               missing (${TURN_ENV_FILE})"
  fi
}

cmd_health() {
  command -v curl >/dev/null 2>&1 || { ui_check "curl" "FAIL" "(missing dependency)"; return 1; }

  curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 && ui_check "signaling" "OK" || ui_check "signaling" "FAIL"
  curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 && ui_check "runner" "OK" || ui_check "runner" "FAIL"
  curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 && ui_check "orch health" "OK" || ui_check "orch health" "FAIL"

  if [[ -f "$ENV_FILE" ]]; then
    local edge_config_url allowlist nonlocal turn_external
    edge_config_url="$(get_edge_config_url)"
    if [[ -n "$edge_config_url" ]]; then
      allowlist="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
      nonlocal="$(extract_first_nonlocal_allowlist_token "$allowlist" || true)"
      turn_external="$(strip_inline_comment "$(read_env_value "$TURN_ENV_FILE" "TURN_EXTERNAL_IP" 2>/dev/null || true)")"
      if [[ -n "$nonlocal" ]]; then
        ui_check "edge plane" "OK" "(allowlisted: ${nonlocal})"
      else
        ui_check "edge plane" "WARN" "(no edge IP allowlisted yet; check vtuber-orchestrator-edge-rotator logs)"
      fi
      if [[ -n "$turn_external" && -n "$nonlocal" ]] && [[ "$turn_external" != "$nonlocal" ]]; then
        ui_check "turn" "WARN" "(TURN_EXTERNAL_IP=${turn_external}; expected ${nonlocal} for DNAT setups)"
      fi
    fi
  fi
}

ensure_registered_best_effort() {
  has_setup_state || return 0

  local payments_url orch_id orch_addr
  payments_url="$(get_payments_api_url)"
  payments_url="$(trim_whitespace "${payments_url:-}")"
  [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

  orch_id="$(get_orchestrator_id)"
  orch_addr="$(get_orchestrator_address)"

  if [[ -z "$orch_id" || -z "$orch_addr" ]]; then
    return 0
  fi

  command -v python3 >/dev/null 2>&1 || return 0

  python3 "$REPO_ROOT/scripts/register_orchestrator.py" \
    --api-url "$payments_url" \
    --orchestrator-id "$orch_id" \
    --orchestrator-address "$orch_addr" \
    --timeout 3 \
    --once \
    --state-file "$REGISTRATION_STATE_FILE_DEFAULT" \
    --skip-if-state-matches \
    --best-effort >/dev/null 2>&1 || true

  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" && -f "$REGISTRATION_STATE_FILE_DEFAULT" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$REGISTRATION_STATE_FILE_DEFAULT" 2>/dev/null || true
  fi
}

payments_self_me() {
  local payments_url="$1" timeout_s="${2:-4}" token
  token="$(read_orchestrator_token)"
  if [[ -z "$token" ]]; then
    echo ""
    return 2
  fi

  local url response http_code body
  url="${payments_url%/}/api/orchestrators/me"
  response="$(curl -sS --max-time "$timeout_s" -H "Authorization: Bearer $token" -w $'\n%{http_code}' "$url" 2>/dev/null || true)"
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  printf '%s\n%s' "$http_code" "$body"
}

payments_self_bootstrap() {
  local payments_url="$1" timeout_s="${2:-4}" token
  token="$(read_orchestrator_token)"
  if [[ -z "$token" ]]; then
    echo ""
    return 2
  fi

  local url response http_code body
  url="${payments_url%/}/api/orchestrators/bootstrap"
  response="$(curl -sS --max-time "$timeout_s" -H "Authorization: Bearer $token" -w $'\n%{http_code}' "$url" 2>/dev/null || true)"
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  printf '%s\n%s' "$http_code" "$body"
}

payments_self_stats() {
  local payments_url="$1" timeout_s="${2:-6}" days="${3:-30}" token
  token="$(read_orchestrator_token)"
  if [[ -z "$token" ]]; then
    echo ""
    return 2
  fi

  local url response http_code body
  url="${payments_url%/}/api/orchestrators/me/stats?days=${days}"
  response="$(curl -sS --max-time "$timeout_s" -H "Authorization: Bearer $token" -w $'\n%{http_code}' "$url" 2>/dev/null || true)"
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  printf '%s\n%s' "$http_code" "$body"
}

cmd_upgrade() {
  init_ui
  local yes="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --yes|-y)
        yes="1"
        shift 1
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh upgrade [--yes]

Options:
  --yes   Do not prompt before recreating containers
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for upgrade: $1" >&2
        return 1
        ;;
    esac
  done

  if ! command -v docker >/dev/null 2>&1; then
    ui_check "docker" "FAIL" "(missing dependency)"
    return 1
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    ui_check ".env" "FAIL" "(missing; run: ./scripts/embody_cli.sh setup)"
    return 1
  fi
  command -v python3 >/dev/null 2>&1 || { ui_check "python3" "FAIL" "(missing dependency)"; return 1; }

  if is_tty && [[ "$yes" != "1" ]]; then
    if ! prompt_yes_no "Pull latest service images and recreate containers now? This may disconnect active sessions." "y"; then
      ui_check "apply" "SKIP"
      return 0
    fi
  fi

  ui_section "Upgrade"
  ui_check "pull" "WARN" "(pulling service images...)"
  if ! "$START_SCRIPT" pull; then
    ui_check "pull" "FAIL"
    return 1
  fi
  ui_check "pull" "OK"

  local game_image
  game_image="$(detect_game_image_from_compose "$COMPOSE_FILE" || true)"
  if [[ -n "$game_image" ]] && ! docker_image_present "$game_image"; then
    ui_check "game image" "FAIL" "(${game_image}; run: ./scripts/embody_cli.sh rollout)"
    echo "Docs: docs/admin-encrypted-game-image.md" >&2
    return 1
  fi

  local awake="0"
  if docker inspect -f '{{.State.Status}}' vtuber-unreal-game >/dev/null 2>&1; then
    if [[ "$(docker inspect -f '{{.State.Status}}' vtuber-unreal-game 2>/dev/null || true)" == "running" ]]; then
      awake="1"
    fi
  fi

  local recreate_common=(orchestrator-edge-rotator orchestrator-health vtuber-watchdog vtuber-auto-updater)
  ui_check "recreate" "WARN" "(recreating always-on services...)"
  docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
    up -d --force-recreate "${recreate_common[@]}"

  if [[ "$awake" == "1" ]]; then
    ui_check "recreate" "WARN" "(stack awake; recreating signaling/turn/runner/recorder...)"
    docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
      up -d --force-recreate turn-server unreal-signaling vtuber-script-runner recorder-control orchestrator-registration
  else
    ui_check "recreate" "WARN" "(stack sleeping; updating runtime containers without starting)"
    docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
      up --no-start --force-recreate turn-server unreal-signaling vtuber-script-runner recorder-control orchestrator-registration
  fi

  ui_check "apply" "OK"
}

cmd_overview() {
  init_ui

  ui_title "Embody Orchestrator — Status"

  ui_section "Repo"
  if is_git_repo; then
    local branch sha remote_sha ab ahead behind
    branch="$(git_current_branch)"
    sha="$(git_remote_commit HEAD)"
    ui_kv "Branch" "${branch:-<unknown>}"
    ui_kv "Commit" "${sha:-<unknown>}"

    if maybe_git_fetch_origin_main; then
      remote_sha="$(git_remote_commit origin/main)"
      ab="$(git_ahead_behind_origin_main)"
      ahead="$(printf '%s' "$ab" | awk '{print $1}')"
      behind="$(printf '%s' "$ab" | awk '{print $2}')"
      if [[ "${behind:-0}" != "0" ]]; then
        ui_check "repo" "WARN" "(behind origin/main by ${behind} commit(s); CLI auto-updates on launch when checkout is clean)"
      elif [[ "${ahead:-0}" != "0" ]]; then
        ui_check "repo" "WARN" "(ahead of origin/main by ${ahead} commit(s); local changes not pushed)"
      else
        ui_check "repo" "OK" "(origin/main=${remote_sha})"
      fi
    else
      ui_check "repo" "WARN" "(git fetch origin main failed)"
    fi
  else
    ui_check "git" "SKIP" "(not a git checkout)"
  fi

  ui_section "Setup"
  [[ -f "$ENV_FILE" ]] && ui_check ".env" "OK" "(${ENV_FILE})" || ui_check ".env" "FAIL" "(missing; run: ./scripts/embody_cli.sh setup)"
  [[ -s "$TURN_ENV_FILE" ]] && ui_check ".env.turn" "OK" "(${TURN_ENV_FILE})" || ui_check ".env.turn" "WARN" "(missing; will be generated on start/rollout)"
  if has_license_token; then
    ui_check "license token" "OK" "(${TOKEN_FILE_DEFAULT})"
  else
    ui_check "license token" "WARN" "(missing; run: ./scripts/embody_cli.sh license redeem)"
  fi

  if [[ -f "$COMPOSE_FILE" ]]; then
    local game_image
    game_image="$(detect_game_image_from_compose "$COMPOSE_FILE" || true)"
    if [[ -n "$game_image" ]]; then
      if docker_image_present "$game_image"; then
        ui_check "game image" "OK" "(${game_image})"
      else
        ui_check "game image" "WARN" "(${game_image}; run: ./scripts/embody_cli.sh rollout)"
      fi
    else
      ui_check "game image" "WARN" "(could not detect from compose)"
    fi
  else
    ui_check "compose" "FAIL" "(missing: ${COMPOSE_FILE})"
  fi

  if has_setup_state; then
    local orch_id orch_addr payments_url
    orch_id="$(get_orchestrator_id)"
    orch_addr="$(get_orchestrator_address)"
    payments_url="$(get_payments_api_url)"
    payments_url="$(trim_whitespace "${payments_url:-}")"
    [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

    ui_kv "Orchestrator ID" "${orch_id:-<unset>}"
    ui_kv "Payout wallet" "${orch_addr:-<unset>}"
    ui_kv "Payments API" "${payments_url:-<unset>}"
    local edge_url
    edge_url="$(get_edge_config_url)"
    if [[ -n "$edge_url" ]]; then
      ui_kv "Edge config URL" "$edge_url"
    else
      ui_kv "Edge config URL" "<manual edge mode>"
    fi
  fi

  ui_section "Runtime (local)"
  if ! command -v docker >/dev/null 2>&1; then
    ui_check "docker" "FAIL" "(missing dependency)"
  elif ! docker info >/dev/null 2>&1; then
    ui_check "docker" "FAIL" "(daemon not reachable; try sudo or add user to docker group)"
  else
    ui_check "docker" "OK"
    cmd_health || true
  fi

  ui_section "Registration"
  if has_setup_state; then
    local payments_url orch_id token http_code body me_out
    payments_url="$(get_payments_api_url)"
    payments_url="$(trim_whitespace "${payments_url:-}")"
    [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"
    orch_id="$(get_orchestrator_id)"
    token="$(read_orchestrator_token)"

    if [[ -z "$token" ]]; then
      ui_check "registration" "WARN" "(missing license token; run: ./scripts/embody_cli.sh license redeem)"
    else
      me_out="$(payments_self_me "$payments_url" 3 || true)"
      http_code="$(printf '%s\n' "$me_out" | head -n 1 || true)"
      body="$(printf '%s\n' "$me_out" | tail -n +2 || true)"
      case "$http_code" in
        200)
          ui_check "registration" "OK" "(registered in Payments)"
          if command -v python3 >/dev/null 2>&1 && [[ -n "$body" ]]; then
            local summary
            summary="$(BODY="$body" python3 - <<'PY' || true
import json
import os

raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
orch_id = (data.get("orchestrator_id") or "").strip()
balance = data.get("balance_eth")
eligible = data.get("eligible_for_payments")
last_seen = (data.get("last_seen") or "").strip()
active = data.get("active")
active_sessions = data.get("active_sessions")
parts = []
if orch_id:
    parts.append(f"id={orch_id}")
if balance is not None:
    parts.append(f"balance={balance}")
if eligible is not None:
    parts.append(f"eligible={eligible}")
if active is not None:
    parts.append(f"active={active}")
if active_sessions is not None:
    parts.append(f"sessions={active_sessions}")
if last_seen:
    parts.append(f"last_seen={last_seen}")
print(", ".join(parts))
PY
            )"
            if [[ -n "$summary" ]]; then
              ui_check "payments" "OK" "(${summary})"
            fi
          fi
          ;;
        404)
          ui_check "registration" "WARN" "(not registered yet; attempting auto-register...)"
          ensure_registered_best_effort
          me_out="$(payments_self_me "$payments_url" 3 || true)"
          http_code="$(printf '%s\n' "$me_out" | head -n 1 || true)"
          if [[ "$http_code" == "200" ]]; then
            ui_check "registration" "OK" "(registered in Payments)"
          else
            ui_check "registration" "WARN" "(still unregistered; run: ./scripts/embody_cli.sh register)"
          fi
          ;;
        401)
          ui_check "registration" "FAIL" "(invalid orchestrator token; re-run: ./scripts/embody_cli.sh license redeem)"
          ;;
        *)
          if [[ -f "$REGISTRATION_STATE_FILE_DEFAULT" ]]; then
            ui_check "registration" "OK" "(cached: ${REGISTRATION_STATE_FILE_DEFAULT}; Payments unreachable)"
          else
            ui_check "registration" "WARN" "(Payments unreachable; cannot confirm)"
          fi
          ;;
      esac

      if [[ -f "$REGISTRATION_STATE_FILE_DEFAULT" ]]; then
        ui_kv "Registration cache" "$REGISTRATION_STATE_FILE_DEFAULT"
      else
        ui_kv "Registration cache" "<none>"
      fi

      if [[ -n "$orch_id" ]]; then
        local boot_code boot_body boot_id boot_out
        boot_out="$(payments_self_bootstrap "$payments_url" 3 || true)"
        boot_code="$(printf '%s\n' "$boot_out" | head -n 1 || true)"
        boot_body="$(printf '%s\n' "$boot_out" | tail -n +2 || true)"
        if [[ "$boot_code" == "200" ]] && command -v python3 >/dev/null 2>&1; then
          boot_id="$(BODY="$boot_body" python3 - <<'PY' || true
import json
import os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
print((data.get("orchestrator_id") or "").strip())
PY
          )"
          if [[ -n "$boot_id" && "$boot_id" != "$orch_id" ]]; then
            ui_check "token/env" "WARN" "(token orchestrator_id=${boot_id} != .env ORCHESTRATOR_ID=${orch_id})"
          fi
        fi
      fi
    fi
  else
    ui_check "registration" "SKIP" "(setup not complete)"
  fi

  ui_section "Rollout"
  local rollout_path
  rollout_path="$(first_existing_path "$ROLLOUT_STATE_FILE_DEFAULT" "$ROLLOUT_STATE_FILE_FALLBACK")"
  if [[ -f "$rollout_path" ]] && command -v python3 >/dev/null 2>&1; then
    local rollout_summary
    rollout_summary="$(PATH="$rollout_path" python3 - <<'PY' || true
import json
import os

path = os.environ.get("PATH") or ""
try:
    data = json.load(open(path, "r"))
except Exception:
    data = {}

status = (data.get("status") or "").strip() or "unknown"
image_ref = (data.get("image_ref") or "").strip() or ""
updated_at = (data.get("updated_at") or "").strip() or ""
loaded_id = (data.get("loaded_image_id") or "").strip() or ""
if loaded_id.startswith("sha256:"):
    loaded_id = loaded_id.split(":", 1)[1]
loaded_id_short = loaded_id[:12] if loaded_id else ""

parts = [f"status={status}"]
if image_ref:
    parts.append(f"image_ref={image_ref}")
if loaded_id_short:
    parts.append(f"image_id={loaded_id_short}")
if updated_at:
    parts.append(f"updated_at={updated_at}")
print(", ".join(parts))
PY
    )"
    if [[ -n "$rollout_summary" ]]; then
      ui_check "pending rollout" "OK" "(${rollout_summary}; state=${rollout_path})"
    else
      ui_check "pending rollout" "WARN" "(${rollout_path} unreadable)"
    fi
  elif [[ -f "$rollout_path" ]]; then
    ui_check "pending rollout" "OK" "(${rollout_path})"
  else
    ui_check "pending rollout" "OK" "(none)"
  fi

  ui_section "Verify (last)"
  local verify_path
  verify_path="$(first_existing_path "$VERIFY_LAST_FILE_DEFAULT" "$VERIFY_LAST_FILE_FALLBACK")"
  if [[ -f "$verify_path" ]] && command -v python3 >/dev/null 2>&1; then
    local verify_summary
    verify_summary="$(PATH="$verify_path" python3 - <<'PY' || true
import json
import os

path = os.environ.get("PATH") or ""
try:
    data = json.load(open(path, "r"))
except Exception:
    data = {}

ran_at = (data.get("ran_at") or "").strip() or ""
ok = data.get("ok")
git_sha = ((data.get("git") or {}).get("sha") or "").strip()

parts = []
if ran_at:
    parts.append(f"ran_at={ran_at}")
if ok is True:
    parts.append("ok=true")
elif ok is False:
    parts.append("ok=false")
if git_sha:
    parts.append(f"sha={git_sha}")
print(", ".join(parts))
PY
    )"
    if [[ -n "$verify_summary" ]]; then
      ui_check "last verify" "OK" "(${verify_summary}; state=${verify_path})"
    else
      ui_check "last verify" "WARN" "(${verify_path} unreadable)"
    fi
  elif [[ -f "$verify_path" ]]; then
    ui_check "last verify" "OK" "(${verify_path})"
  else
    ui_check "last verify" "WARN" "(no verify history; run: ./scripts/embody_cli.sh verify --fix)"
  fi
}

cmd_capacity() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi not found; cannot estimate GPU capacity." >&2
    return 1
  fi
  local raw
  raw="$(nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    echo "nvidia-smi returned no GPU info." >&2
    return 1
  fi
  local per per_gib devices util_max
  per="$(get_vram_per_instance_mib)"
  per_gib=$(( per / 1024 ))
  devices="$(normalize_gpu_devices_csv "$(get_gpu_devices 2>/dev/null || true)")"
  util_max="$(get_auto_gpu_util_max_percent)"
  if [[ "$devices" == "none" ]]; then
    echo "NVIDIA_VISIBLE_DEVICES=none; no GPUs selected." >&2
    return 1
  fi
  echo "Estimated capacity (based on FREE VRAM; ~${per_gib}GiB per UE instance; auto uses <=${util_max}% util):"
  local total="0" seen="0"
  local auto_total="0" auto_seen="0"
  local idx name mem_total mem_used util
  while IFS=',' read -r idx name mem_total mem_used util; do
    idx="$(trim_whitespace "$idx")"
    name="$(trim_whitespace "$name")"
    mem_total="$(trim_whitespace "$mem_total")"
    mem_used="$(trim_whitespace "${mem_used:-0}")"
    util="$(trim_whitespace "${util:-0}")"
    [[ -n "$idx" ]] || continue
    if [[ "$devices" != "all" ]]; then
      if [[ "$(csv_has_token "$devices" "$idx")" != "1" ]]; then
        continue
      fi
    fi
    if [[ "$mem_total" =~ ^[0-9]+$ && "$mem_used" =~ ^[0-9]+$ && "$util" =~ ^[0-9]+$ ]]; then
      local free=$(( mem_total - mem_used ))
      if [[ "$free" -lt 0 ]]; then
        free="0"
      fi
      local instances=$(( free / per ))
      total=$(( total + instances ))
      seen=$(( seen + 1 ))
      local busy=""
      if [[ "$util" -gt "$util_max" ]]; then
        busy=" (busy)"
      else
        auto_total=$(( auto_total + instances ))
        auto_seen=$(( auto_seen + 1 ))
      fi
      echo "  GPU ${idx} (${name}): util=${util}%${busy} total=${mem_total} used=${mem_used} free=${free} MiB -> ~${instances} instance(s)"
    else
      seen=$(( seen + 1 ))
      echo "  GPU ${idx} (${name}): total=${mem_total} used=${mem_used} util=${util}"
    fi
  done <<<"$raw"
  if [[ "$seen" -eq 0 ]]; then
    echo "No GPUs matched NVIDIA_VISIBLE_DEVICES=${devices}." >&2
    return 1
  fi
  echo "Total: ~${total} instance(s) across ${seen} GPU(s) (NVIDIA_VISIBLE_DEVICES=${devices})"
  echo "Auto-available: ~${auto_total} instance(s) across ${auto_seen} GPU(s) (util<=${util_max}%)"
}

cluster_config_path() {
  printf '%s' "${EMBODY_CLUSTER_FILE:-$CLUSTER_CONFIG_FILE_DEFAULT}"
}

cluster_print_example() {
  cat <<'EOF'
{
  "slot_count": 20,
  "default_gpu": "0",
  "instances": [
    { "avatar_id": "ghost", "slot": 0, "gpu": "0" },
    { "avatar_id": "pon",   "slot": 1, "gpu": "0" }
  ]
}
EOF
}

cluster_nvidia_smi_raw() {
  command -v nvidia-smi >/dev/null 2>&1 || return 1
  nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || true
}

cluster_auto_estimate_instance_count() {
  local raw="$1" devices="$2" per="$3" max_instances="${4:-}"
  local total="0"
  local idx mem_total mem_used util
  local util_max
  util_max="$(get_auto_gpu_util_max_percent)"

  devices="$(normalize_gpu_devices_csv "$devices")"
  if [[ "$devices" == "none" ]]; then
    printf '%s' "0"
    return 0
  fi
  if [[ ! "$per" =~ ^[0-9]+$ || "$per" -lt 1024 ]]; then
    per="8192"
  fi

  while IFS=',' read -r idx _name mem_total mem_used util; do
    idx="$(trim_whitespace "$idx")"
    mem_total="$(trim_whitespace "$mem_total")"
    mem_used="$(trim_whitespace "${mem_used:-0}")"
    util="$(trim_whitespace "${util:-0}")"
    [[ -n "$idx" ]] || continue
    if [[ "$devices" != "all" ]]; then
      if [[ "$(csv_has_token "$devices" "$idx")" != "1" ]]; then
        continue
      fi
    fi
    if [[ "$idx" =~ ^[0-9]+$ && "$mem_total" =~ ^[0-9]+$ && "$mem_used" =~ ^[0-9]+$ && "$util" =~ ^[0-9]+$ ]]; then
      if [[ "$util" -gt "$util_max" ]]; then
        continue
      fi
      local free=$(( mem_total - mem_used ))
      if [[ "$free" -lt 0 ]]; then
        free="0"
      fi
      total=$(( total + (free / per) ))
    fi
  done <<<"$raw"

  if [[ -n "$max_instances" && "$max_instances" =~ ^[0-9]+$ && "$max_instances" -gt 0 ]]; then
    if [[ "$total" -gt "$max_instances" ]]; then
      total="$max_instances"
    fi
  fi
  if [[ "$total" -gt "$CLUSTER_MAX_SLOTS" ]]; then
    total="$CLUSTER_MAX_SLOTS"
  fi
  printf '%s' "$total"
}

cluster_count_available_gpus() {
  local raw="$1" devices="$2" per="$3"
  local count="0"
  local idx mem_total mem_used util
  local util_max
  util_max="$(get_auto_gpu_util_max_percent)"

  devices="$(normalize_gpu_devices_csv "$devices")"
  if [[ "$devices" == "none" ]]; then
    printf '%s' "0"
    return 0
  fi
  if [[ ! "$per" =~ ^[0-9]+$ || "$per" -lt 1024 ]]; then
    per="8192"
  fi

  while IFS=',' read -r idx _name mem_total mem_used util; do
    idx="$(trim_whitespace "$idx")"
    mem_total="$(trim_whitespace "$mem_total")"
    mem_used="$(trim_whitespace "${mem_used:-0}")"
    util="$(trim_whitespace "${util:-0}")"
    [[ -n "$idx" ]] || continue
    if [[ "$devices" != "all" ]]; then
      if [[ "$(csv_has_token "$devices" "$idx")" != "1" ]]; then
        continue
      fi
    fi
    if [[ "$idx" =~ ^[0-9]+$ && "$mem_total" =~ ^[0-9]+$ && "$mem_used" =~ ^[0-9]+$ && "$util" =~ ^[0-9]+$ ]]; then
      if [[ "$util" -gt "$util_max" ]]; then
        continue
      fi
      local free=$(( mem_total - mem_used ))
      if [[ "$free" -ge "$per" ]]; then
        count=$(( count + 1 ))
      fi
    fi
  done <<<"$raw"

  printf '%s' "$count"
}

cluster_write_auto_config() {
  local out_path="$1" avatar_prefix="$2" max_instances="${3:-}" gpu_devices="${4:-all}" force="${5:-0}"

  out_path="$(trim_whitespace "$out_path")"
  [[ -n "$out_path" ]] || out_path="$(cluster_config_path)"

  if [[ -f "$out_path" && "$force" != "1" ]]; then
    echo "cluster init: config already exists: $out_path" >&2
    echo "cluster init: re-run with --force to overwrite" >&2
    return 1
  fi

  command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }
  local raw
  raw="$(cluster_nvidia_smi_raw)"
  if [[ -z "$raw" ]]; then
    echo "cluster init: nvidia-smi returned no GPU info" >&2
    return 1
  fi

  local per per_gib
  per="$(get_vram_per_instance_mib)"
  per_gib=$(( per / 1024 ))
  local util_max
  util_max="$(get_auto_gpu_util_max_percent)"

  gpu_devices="$(normalize_gpu_devices_csv "$gpu_devices")"
  if [[ "$gpu_devices" == "none" ]]; then
    echo "cluster init: NVIDIA_VISIBLE_DEVICES=none; no GPUs selected" >&2
    return 1
  fi

  local orch_id
  orch_id="$(get_orchestrator_id 2>/dev/null || true)"
  orch_id="$(trim_whitespace "${orch_id:-}")"
  avatar_prefix="$(trim_whitespace "${avatar_prefix:-}")"
  if [[ -z "$avatar_prefix" ]]; then
    avatar_prefix="$orch_id"
  fi
  [[ -n "$avatar_prefix" ]] || avatar_prefix="avatar"

  if [[ -z "${max_instances:-}" ]]; then
    max_instances="$(cluster_count_available_gpus "$raw" "$gpu_devices" "$per")"
  fi

  local estimate
  estimate="$(cluster_auto_estimate_instance_count "$raw" "$gpu_devices" "$per" "$max_instances")"
  if [[ ! "$estimate" =~ ^[0-9]+$ || "$estimate" -lt 1 ]]; then
    echo "cluster init: could not estimate capacity (per_instance=${per}MiB); please create $(cluster_config_path) manually" >&2
    return 1
  fi

  local dir
  dir="$(dirname "$out_path")"
  umask 077
  mkdir -p "$dir"
  chmod 700 "$dir" 2>/dev/null || true

  OUT_PATH="$out_path" GPU_RAW="$raw" GPU_DEVICES="$gpu_devices" PREFIX="$avatar_prefix" \
    MAX_SLOTS="$CLUSTER_MAX_SLOTS" MAX_INSTANCES="$estimate" VRAM_PER_INSTANCE_MIB="$per" GPU_UTIL_MAX_PERCENT="$(get_auto_gpu_util_max_percent)" python3 - <<'PY'
import json
import os
import re
from pathlib import Path

def slugify(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9_.-]+", "-", s)
    s = s.strip("-_.")
    return s or "avatar"

out_path = os.environ.get("OUT_PATH") or ""
gpu_raw = os.environ.get("GPU_RAW") or ""
gpu_devices = (os.environ.get("GPU_DEVICES") or "all").strip()
prefix = slugify(os.environ.get("PREFIX") or "")
max_slots = int(os.environ.get("MAX_SLOTS") or "20")
max_instances = int(os.environ.get("MAX_INSTANCES") or "0")
per_mib = int(os.environ.get("VRAM_PER_INSTANCE_MIB") or "8192")
util_max = int(os.environ.get("GPU_UTIL_MAX_PERCENT") or "20")

want = max_instances
if want < 1:
    raise SystemExit(1)
want = min(want, max_slots)

allowed = None
if gpu_devices and gpu_devices not in ("all", "none"):
    allowed = {part.strip() for part in gpu_devices.split(",") if part.strip()}

gpus = []
for line in gpu_raw.splitlines():
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        continue
    idx, name = parts[0], parts[1]
    total = parts[2] if len(parts) >= 3 else ""
    used = parts[3] if len(parts) >= 4 else "0"
    util = parts[4] if len(parts) >= 5 else "0"
    if allowed is not None and idx not in allowed:
        continue
    try:
        i = int(idx)
        total_m = int(total)
        used_m = int(used)
        util_p = int(util)
    except Exception:
        continue
    if util_p > util_max:
        continue
    free_m = max(0, total_m - used_m)
    cap = max(0, free_m // max(per_mib, 1))
    gpus.append((i, name, cap))

gpus.sort(key=lambda t: t[0])

instances = []
slot = 0
round_idx = 0
while slot < want:
    progressed = False
    for i, _name, cap in gpus:
        if cap > round_idx:
            instances.append({"avatar_id": f"{prefix}-{slot}", "slot": slot, "gpu": str(i)})
            slot += 1
            progressed = True
            if slot >= want:
                break
    if not progressed:
        break
    round_idx += 1

if not instances:
    raise SystemExit(1)

data = {"slot_count": max_slots, "default_gpu": "all", "instances": instances}

path = Path(out_path)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Wrote cluster config: {out_path}")
print(f"Instances: {len(instances)} (vram_per_instance_mib={per_mib})")
print(f"GPU devices: {gpu_devices or 'all'}")
PY

  chmod 600 "$out_path" 2>/dev/null || true
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$out_path" 2>/dev/null || true
    chown "$SUDO_USER":"$SUDO_USER" "$dir" 2>/dev/null || true
  fi

  echo "Tip: ./scripts/embody_cli.sh cluster plan"
  echo "Tip: ./scripts/embody_cli.sh cluster deploy --auto"
  echo "Note: estimate assumes ~${per_gib}GiB VRAM per UE instance (override: EMBODY_VRAM_PER_INSTANCE_MIB=<MiB>)"
  echo "Note: auto excludes GPUs over ${util_max}% utilization (override: EMBODY_AUTO_GPU_UTIL_MAX=100)"
}

cluster_load_config_lines() {
  local path
  path="$(cluster_config_path)"
  [[ -n "$path" ]] || { echo "Missing cluster config path" >&2; return 1; }
  [[ -f "$path" ]] || { echo "Cluster config not found: $path" >&2; return 1; }
  command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }

  CLUSTER_PATH="$path" CLUSTER_MAX_SLOTS="$CLUSTER_MAX_SLOTS" python3 - <<'PY'
import json
import os
import re
import sys

path = os.environ.get("CLUSTER_PATH") or ""
max_slots_raw = os.environ.get("CLUSTER_MAX_SLOTS") or "20"
try:
    max_slots = int(max_slots_raw)
except Exception:
    max_slots = 20

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"cluster: FAIL (config not found: {path})", file=sys.stderr)
    raise SystemExit(1)
except Exception as exc:
    print(f"cluster: FAIL (invalid JSON in {path}: {exc})", file=sys.stderr)
    raise SystemExit(1)

if not isinstance(data, dict):
    print("cluster: FAIL (config must be a JSON object)", file=sys.stderr)
    raise SystemExit(1)

slot_count = data.get("slot_count") or data.get("slots") or data.get("slotCount") or max_slots
try:
    slot_count = int(slot_count)
except Exception:
    print("cluster: FAIL (slot_count must be an integer)", file=sys.stderr)
    raise SystemExit(1)
if slot_count < 1 or slot_count > max_slots:
    print(f"cluster: FAIL (slot_count must be 1..{max_slots})", file=sys.stderr)
    raise SystemExit(1)

instances = data.get("instances") or data.get("avatars") or data.get("vtubers") or []
if not isinstance(instances, list):
    print("cluster: FAIL (instances must be a JSON list)", file=sys.stderr)
    raise SystemExit(1)
if not instances:
    print("cluster: FAIL (instances is empty)", file=sys.stderr)
    raise SystemExit(1)

default_gpu = (data.get("default_gpu") or data.get("defaultGpu") or data.get("gpu") or "all")
default_gpu = str(default_gpu).strip() or "all"

used_ids: set[str] = set()
used_slugs: set[str] = set()
used_slots: set[int] = set()
next_slot = 0

out: list[tuple[str, str, int, str]] = []

def slugify(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9_.-]+", "-", s)
    s = s.strip("-_.")
    return s

def alloc_slot() -> int:
    global next_slot
    while next_slot in used_slots:
        next_slot += 1
    return next_slot

for item in instances:
    avatar_id = ""
    slot = None
    gpu = None

    if isinstance(item, str):
        avatar_id = item.strip()
    elif isinstance(item, dict):
        avatar_id = str(
            item.get("avatar_id")
            or item.get("avatar")
            or item.get("streamer_id")
            or item.get("streamerId")
            or item.get("id")
            or ""
        ).strip()
        slot = item.get("slot")
        gpu = (
            item.get("gpu")
            or item.get("gpu_id")
            or item.get("gpuId")
            or item.get("nvidia_visible_devices")
            or item.get("nvidiaVisibleDevices")
        )
    else:
        print("cluster: FAIL (each instance must be an object or string)", file=sys.stderr)
        raise SystemExit(1)

    if not avatar_id:
        print("cluster: FAIL (instance missing avatar_id)", file=sys.stderr)
        raise SystemExit(1)
    if avatar_id in used_ids:
        print(f"cluster: FAIL (duplicate avatar_id: {avatar_id})", file=sys.stderr)
        raise SystemExit(1)

    slug = slugify(avatar_id)
    if not slug:
        print(f"cluster: FAIL (avatar_id produces empty slug: {avatar_id})", file=sys.stderr)
        raise SystemExit(1)
    if slug in used_slugs:
        print(f"cluster: FAIL (duplicate avatar slug after normalization: {slug})", file=sys.stderr)
        raise SystemExit(1)

    if slot is None or (isinstance(slot, str) and not slot.strip()):
        slot = alloc_slot()
    try:
        slot_int = int(slot)
    except Exception:
        print(f"cluster: FAIL (slot must be an integer for {avatar_id})", file=sys.stderr)
        raise SystemExit(1)

    if slot_int < 0 or slot_int >= slot_count:
        print(f"cluster: FAIL (slot out of range for {avatar_id}: {slot_int} (slot_count={slot_count}))", file=sys.stderr)
        raise SystemExit(1)
    if slot_int in used_slots:
        print(f"cluster: FAIL (duplicate slot {slot_int})", file=sys.stderr)
        raise SystemExit(1)

    gpu_value = str(gpu if gpu is not None else default_gpu).strip() or default_gpu

    used_ids.add(avatar_id)
    used_slugs.add(slug)
    used_slots.add(slot_int)
    out.append((avatar_id, slug, slot_int, gpu_value))

out.sort(key=lambda t: t[2])

print(f"SLOT_COUNT\t{slot_count}")
for avatar_id, slug, slot_int, gpu_value in out:
    print(f"INSTANCE\t{avatar_id}\t{slug}\t{slot_int}\t{gpu_value}")
PY
}

get_vtuber_session_dir_base() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "VTUBER_SESSION_DIR" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  raw="$(trim_whitespace "$raw")"
  [[ -n "$raw" ]] || raw="/home/ubuntu/vtuber_sessions"
  printf '%s' "$raw"
}

get_vtuber_recordings_dir_base() {
  local raw
  raw="$(read_env_value "$ENV_FILE" "VTUBER_RECORDINGS_DIR" 2>/dev/null || true)"
  raw="$(strip_inline_comment "$raw")"
  raw="$(trim_whitespace "$raw")"
  [[ -n "$raw" ]] || raw="/home/ubuntu/recordings"
  printf '%s' "$raw"
}

ensure_turn_env() {
  if [[ ! -s "$TURN_ENV_FILE" ]]; then
    echo "TURN credentials missing; generating .env.turn..." >&2
    "${REPO_ROOT}/scripts/generate_turn_credentials.sh"
  fi
}

cluster_read_config() {
  CLUSTER_SLOT_COUNT=""
  CLUSTER_AVATAR_IDS=()
  CLUSTER_AVATAR_SLUGS=()
  CLUSTER_SLOTS=()
  CLUSTER_GPUS=()

  local kind a b c d
  while IFS=$'\t' read -r kind a b c d; do
    case "$kind" in
      SLOT_COUNT)
        CLUSTER_SLOT_COUNT="$a"
        ;;
      INSTANCE)
        CLUSTER_AVATAR_IDS+=("$a")
        CLUSTER_AVATAR_SLUGS+=("$b")
        CLUSTER_SLOTS+=("$c")
        CLUSTER_GPUS+=("$d")
        ;;
    esac
  done < <(cluster_load_config_lines)

  [[ -n "${CLUSTER_SLOT_COUNT:-}" ]] || CLUSTER_SLOT_COUNT="$CLUSTER_MAX_SLOTS"
  if [[ "${#CLUSTER_AVATAR_IDS[@]}" -lt 1 ]]; then
    echo "cluster: no instances configured" >&2
    return 1
  fi
}

cluster_instance_ports() {
  local slot="$1"
  local signaling runner recorder game
  signaling=$(( CLUSTER_SIGNALING_PORT_BASE + slot ))
  runner=$(( CLUSTER_RUNNER_PORT_BASE + slot ))
  recorder=$(( CLUSTER_RECORDER_PORT_BASE + slot ))
  game=$(( CLUSTER_GAME_TCP_PORT_BASE + slot ))
  printf '%s\t%s\t%s\t%s\n' "$signaling" "$runner" "$recorder" "$game"
}

cluster_instance_subnet() {
  local slot="$1"
  printf '172.30.%s.0/24' "$slot"
}

cluster_instance_gateway() {
  local slot="$1"
  printf '172.30.%s.1' "$slot"
}

cluster_instance_allowlist() {
  local gateway="$1"
  local allow_csv local_allow edge_local token
  local -a tokens

  allow_csv="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
  edge_local="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" 2>/dev/null || true)")"

  local_allow="127.0.0.1,::1,172.17.0.1,172.18.0.1"
  if [[ -z "$allow_csv" ]]; then
    allow_csv="$local_allow"
  fi

  IFS=',' read -r -a tokens <<<"$local_allow"
  for token in "${tokens[@]}"; do
    token="$(trim_whitespace "$token")"
    [[ -n "$token" ]] || continue
    allow_csv="$(csv_add_token "$allow_csv" "$token")"
  done

  if [[ -n "$edge_local" ]]; then
    IFS=',' read -r -a tokens <<<"$edge_local"
    for token in "${tokens[@]}"; do
      token="$(trim_whitespace "$token")"
      token="$(strip_inline_comment "$token")"
      [[ -n "$token" ]] || continue
      allow_csv="$(csv_add_token "$allow_csv" "$token")"
    done
  fi

  gateway="$(trim_whitespace "${gateway:-}")"
  if [[ -n "$gateway" ]]; then
    allow_csv="$(csv_add_token "$allow_csv" "$gateway")"
  fi

  printf '%s' "$allow_csv"
}

cluster_find_instance_index() {
  local query="$1"
  local i
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    if [[ "${CLUSTER_AVATAR_IDS[$i]}" == "$query" || "${CLUSTER_AVATAR_SLUGS[$i]}" == "$query" ]]; then
      printf '%s' "$i"
      return 0
    fi
  done
  return 1
}

cluster_ensure_docker() {
  command -v docker >/dev/null 2>&1 || { echo "Missing dependency: docker" >&2; return 1; }
  docker compose version >/dev/null 2>&1 || { echo "docker compose plugin not available (docker compose)" >&2; return 1; }
  return 0
}

cluster_max_slot() {
  local max="-1" slot
  for slot in "${CLUSTER_SLOTS[@]}"; do
    if [[ "$slot" =~ ^[0-9]+$ && "$slot" -gt "$max" ]]; then
      max="$slot"
    fi
  done
  printf '%s' "$max"
}

cluster_host_project_name() {
  local container label
  for container in vtuber-orchestrator-health vtuber-orchestrator-edge-rotator vtuber-turn-server vtuber-auto-updater; do
    label="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$container" 2>/dev/null || true)"
    label="$(trim_whitespace "${label:-}")"
    if [[ -n "$label" ]]; then
      printf '%s' "$label"
      return 0
    fi
  done
  printf '%s' "$CLUSTER_HOST_PROJECT_NAME"
}

cluster_detect_running_single_stack_containers() {
  local container status
  for container in vtuber-unreal-game vtuber-unreal-signaling vtuber-recorder-control vtuber-script-runner; do
    status="$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || true)"
    if [[ "$status" == "running" ]]; then
      echo "$container"
    fi
  done
}

cluster_edge_allow_ports() {
  local max_slot="$1"
  local sig_end run_end rec_end
  sig_end=$(( CLUSTER_SIGNALING_PORT_BASE + max_slot ))
  run_end=$(( CLUSTER_RUNNER_PORT_BASE + max_slot ))
  rec_end=$(( CLUSTER_RECORDER_PORT_BASE + max_slot ))
  printf '%s' "80/tcp,${CLUSTER_SIGNALING_PORT_BASE}-${sig_end}/tcp,${CLUSTER_RUNNER_PORT_BASE}-${run_end}/tcp,${CLUSTER_RECORDER_PORT_BASE}-${rec_end}/tcp,9090/tcp,3478/tcp,3478/udp,49160-49200/udp"
}

cluster_monitored_services() {
  local out="vtuber-turn-server"
  local slug
  for slug in "${CLUSTER_AVATAR_SLUGS[@]}"; do
    out+=",vtuber-${slug}-unreal-game,vtuber-${slug}-unreal-signaling"
  done
  printf '%s' "$out"
}

cluster_enforce_capacity() {
  command -v nvidia-smi >/dev/null 2>&1 || return 0

  local per per_gib
  per="$(get_vram_per_instance_mib)"
  per_gib=$(( per / 1024 ))

  local raw
  raw="$(nvidia-smi --query-gpu=index,memory.total,memory.used --format=csv,noheader,nounits 2>/dev/null || true)"
  [[ -n "$raw" ]] || return 0

  declare -A cap
  local idx mem_total mem_used
  while IFS=',' read -r idx mem_total mem_used; do
    idx="$(trim_whitespace "$idx")"
    mem_total="$(trim_whitespace "$mem_total")"
    mem_used="$(trim_whitespace "${mem_used:-0}")"
    if [[ "$idx" =~ ^[0-9]+$ && "$mem_total" =~ ^[0-9]+$ && "$mem_used" =~ ^[0-9]+$ ]]; then
      local free=$(( mem_total - mem_used ))
      if [[ "$free" -lt 0 ]]; then
        free="0"
      fi
      cap["$idx"]=$(( free / per ))
    fi
  done <<<"$raw"

  declare -A need
  local i gpu
  for i in "${!CLUSTER_GPUS[@]}"; do
    gpu="$(trim_whitespace "${CLUSTER_GPUS[$i]}")"
    [[ -n "$gpu" ]] || gpu="all"
    if [[ "$gpu" =~ ^[0-9]+$ ]]; then
      need["$gpu"]=$(( ${need["$gpu"]:-0} + 1 ))
    fi
  done

  local violated="0"
  for idx in "${!need[@]}"; do
    local want="${need[$idx]}"
    local have="${cap[$idx]:-0}"
    if [[ "$have" -gt 0 && "$want" -gt "$have" ]]; then
      echo "cluster: capacity exceeded on GPU ${idx}: want=${want} estimated=${have} (~${per_gib}GiB/instance)" >&2
      violated="1"
    fi
  done

  [[ "$violated" == "0" ]]
}

cluster_plan() {
  cluster_read_config || return 1
  local cfg
  cfg="$(cluster_config_path)"
  echo "Cluster config: $cfg"
  echo "Instance compose: ${INSTANCE_COMPOSE_FILE}"
  echo ""

  local max_slot
  max_slot="$(cluster_max_slot)"
  if [[ ! "$max_slot" =~ ^[0-9]+$ || "$max_slot" -lt 0 ]]; then
    echo "cluster: invalid slot set" >&2
    return 1
  fi

  local session_base recordings_base
  session_base="$(get_vtuber_session_dir_base)"
  recordings_base="$(get_vtuber_recordings_dir_base)"

  local i avatar slug slot gpu ports signaling runner recorder game project
  echo "Instances:"
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    avatar="${CLUSTER_AVATAR_IDS[$i]}"
    slug="${CLUSTER_AVATAR_SLUGS[$i]}"
    slot="${CLUSTER_SLOTS[$i]}"
    gpu="${CLUSTER_GPUS[$i]}"
    IFS=$'\t' read -r signaling runner recorder game < <(cluster_instance_ports "$slot")
    project="vtuber-${slug}"
    echo "  - avatar=${avatar} (slot=${slot}, gpu=${gpu}, project=${project})"
    echo "    signaling=${signaling} runner=${runner} recorder=${recorder} game_tcp=${game}"
    echo "    sessions=${session_base%/}/${slug}"
    echo "    recordings=${recordings_base%/}/${slug}"
  done

  echo ""
  echo "Host-level:"
  echo "  EDGE_ALLOW_PORTS=$(cluster_edge_allow_ports "$max_slot")"
  echo "  MONITORED_SERVICES=$(cluster_monitored_services)"
}

cluster_list() {
  cluster_read_config || return 1
  local i avatar slug slot gpu
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    avatar="${CLUSTER_AVATAR_IDS[$i]}"
    slug="${CLUSTER_AVATAR_SLUGS[$i]}"
    slot="${CLUSTER_SLOTS[$i]}"
    gpu="${CLUSTER_GPUS[$i]}"
    local game_container="vtuber-${slug}-unreal-game"
    local status
    status="$(docker inspect -f '{{.State.Status}}' "$game_container" 2>/dev/null || true)"
    [[ -n "$status" ]] || status="missing"
    echo "${avatar}\t${slug}\tslot=${slot}\tgpu=${gpu}\tgame=${status}"
  done
}

cluster_up() {
  cd "$REPO_ROOT"
  [[ -f "$ENV_FILE" ]] || { echo "Missing .env (run: ./scripts/embody_cli.sh setup)" >&2; return 1; }
  [[ -f "$COMPOSE_FILE" ]] || { echo "Missing compose file: $COMPOSE_FILE" >&2; return 1; }
  [[ -f "$INSTANCE_COMPOSE_FILE" ]] || { echo "Missing instance compose file: $INSTANCE_COMPOSE_FILE" >&2; return 1; }
  cluster_ensure_docker || return 1
  ensure_turn_env || return 1

  local force="0"
  local recreate="0"
  local pull_mode=""
  local auto="0"
  local auto_yes="0"
  local auto_prefix=""
  local auto_max_instances=""
  local only=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        force="1"
        shift 1
        ;;
      --recreate|--force-recreate)
        recreate="1"
        shift 1
        ;;
      --pull)
        pull_mode="${2:-}"
        shift 2
        ;;
      --auto)
        auto="1"
        shift 1
        ;;
      --yes|--auto-yes)
        auto_yes="1"
        shift 1
        ;;
      --avatar-prefix|--prefix)
        auto_prefix="${2:-}"
        shift 2
        ;;
      --max-instances)
        auto_max_instances="${2:-}"
        shift 2
        ;;
      *)
        only+=("$1")
        shift 1
        ;;
    esac
  done
  pull_mode="$(trim_whitespace "${pull_mode:-}")"
  if [[ -n "$pull_mode" ]] && [[ "$pull_mode" != "always" && "$pull_mode" != "missing" && "$pull_mode" != "never" ]]; then
    echo "cluster: invalid --pull value (expected: always|missing|never)" >&2
    return 1
  fi

  local cfg_path
  cfg_path="$(cluster_config_path)"
  if [[ ! -f "$cfg_path" ]]; then
    if [[ "$auto" != "1" ]]; then
      echo "Cluster config not found: $cfg_path" >&2
      echo "Next: ./scripts/embody_cli.sh cluster init (or set EMBODY_CLUSTER_FILE=/path/to/cluster.json)" >&2
      return 1
    fi

    local raw devices per per_gib estimate effective_max
    raw="$(cluster_nvidia_smi_raw || true)"
    devices="$(normalize_gpu_devices_csv "$(get_gpu_devices 2>/dev/null || true)")"
    per="$(get_vram_per_instance_mib)"
    per_gib=$(( per / 1024 ))
    effective_max="$auto_max_instances"
    if [[ -z "${effective_max:-}" ]]; then
      effective_max="$(cluster_count_available_gpus "$raw" "$devices" "$per")"
    fi
    estimate="$(cluster_auto_estimate_instance_count "$raw" "$devices" "$per" "$effective_max")"
    if [[ ! "$estimate" =~ ^[0-9]+$ || "$estimate" -lt 1 ]]; then
      local estimate_ignore_util effective_max_ignore_util
      effective_max_ignore_util="$auto_max_instances"
      if [[ -z "${effective_max_ignore_util:-}" ]]; then
        effective_max_ignore_util="$(EMBODY_AUTO_GPU_UTIL_MAX=100 cluster_count_available_gpus "$raw" "$devices" "$per")"
      fi
      estimate_ignore_util="$(EMBODY_AUTO_GPU_UTIL_MAX=100 cluster_auto_estimate_instance_count "$raw" "$devices" "$per" "$effective_max_ignore_util" || true)"

      if [[ "$estimate_ignore_util" =~ ^[0-9]+$ ]] && [[ "$estimate_ignore_util" -ge 1 ]]; then
        echo "cluster: auto found VRAM capacity, but excluded GPUs due to utilization >$(get_auto_gpu_util_max_percent)%." >&2
        echo "cluster: to ignore utilization gating (EXPERIMENTAL), set EMBODY_AUTO_GPU_UTIL_MAX=100." >&2
        if is_tty && [[ "$auto_yes" != "1" ]]; then
          if prompt_yes_no "Proceed anyway and auto-generate ${estimate_ignore_util} instance(s)? (experimental)" "n"; then
            effective_max="$effective_max_ignore_util"
            estimate="$estimate_ignore_util"
          else
            echo "cluster: canceled" >&2
            return 1
          fi
        else
          echo "cluster: auto failed (GPU busy); re-run with EMBODY_AUTO_GPU_UTIL_MAX=100 or create cluster config manually." >&2
          return 1
        fi
      else
        echo "cluster: auto failed (nvidia-smi missing/unreadable, or insufficient VRAM for estimate)" >&2
        echo "Next: ./scripts/embody_cli.sh cluster init" >&2
        return 1
      fi
    fi

    if is_tty && [[ "$auto_yes" != "1" ]]; then
      if ! prompt_yes_no "Cluster config missing. Auto-generate ${estimate} instance(s) and start now? (~${per_gib}GiB/instance)" "n"; then
        echo "cluster: canceled" >&2
        return 1
      fi
    fi

    cluster_write_auto_config "$cfg_path" "$auto_prefix" "$effective_max" "$devices" "0" || return 1
  fi

  local game_image
  game_image="$(detect_game_image_from_compose "$COMPOSE_FILE" || true)"
  if [[ -n "$game_image" ]] && ! docker_image_present "$game_image"; then
    echo "Missing local game image: ${game_image}" >&2
    echo "Next: ./scripts/embody_cli.sh rollout (Payments lease → download/decrypt/load)" >&2
    echo "Docs: docs/admin-encrypted-game-image.md" >&2
    return 1
  fi

  cluster_read_config || return 1

  if [[ "$force" != "1" ]] && ! cluster_enforce_capacity; then
    echo "cluster: refusing to start (capacity exceeded). Reconfigure instances/GPU assignment." >&2
    echo "cluster: re-run with --force to bypass the estimate." >&2
    return 1
  fi

  local single_running
  single_running="$(cluster_detect_running_single_stack_containers || true)"
  if [[ -n "$single_running" ]]; then
    echo "cluster: detected a running single-instance stack (will conflict with cluster slot 0 ports + matchmaker IDs):" >&2
    printf '%s\n' "$single_running" | sed 's/^/  - /' >&2
    echo "cluster: recommended: ./scripts/embody_cli.sh stop (or ./scripts/embody_cli.sh down) then retry cluster deploy." >&2
    if ! is_tty; then
      echo "cluster: refusing to proceed in non-interactive mode." >&2
      return 1
    fi
    if ! prompt_yes_no "Stop the single-instance stack now and continue with cluster deploy?" "n"; then
      echo "cluster: canceled" >&2
      return 1
    fi
    "$START_SCRIPT" stop || return 1
  fi

  local max_slot
  max_slot="$(cluster_max_slot)"
  [[ "$max_slot" =~ ^[0-9]+$ ]] || { echo "cluster: invalid max slot" >&2; return 1; }

  local session_base recordings_base
  session_base="$(get_vtuber_session_dir_base)"
  recordings_base="$(get_vtuber_recordings_dir_base)"

  mkdir -p "$session_base" "$recordings_base" || true

  docker network create vtuber_network 2>/dev/null || true

  local edge_ports monitored
  edge_ports="$(cluster_edge_allow_ports "$max_slot")"
  monitored="$(cluster_monitored_services)"

  local host_up_flags=(-d --no-deps)
  local instance_up_flags=(-d)
  if [[ -n "$pull_mode" ]]; then
    host_up_flags+=(--pull "$pull_mode")
    instance_up_flags+=(--pull "$pull_mode")
  fi
  if [[ "$recreate" == "1" ]]; then
    host_up_flags+=(--force-recreate)
    instance_up_flags+=(--force-recreate)
  fi

  local host_project
  host_project="$(cluster_host_project_name)"

  EDGE_ALLOW_PORTS="$edge_ports" MONITORED_SERVICES="$monitored" EDGE_SKIP_COMPOSE_RECREATE="1" docker compose \
    -p "$host_project" -f "$COMPOSE_FILE" \
    up "${host_up_flags[@]}" \
    turn-server orchestrator-health orchestrator-edge-rotator vtuber-auto-updater orchestrator-registration

  local i avatar slug slot gpu project signaling runner recorder game instance_args session_dir recordings_dir
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    avatar="${CLUSTER_AVATAR_IDS[$i]}"
    slug="${CLUSTER_AVATAR_SLUGS[$i]}"
    slot="${CLUSTER_SLOTS[$i]}"
    gpu="$(trim_whitespace "${CLUSTER_GPUS[$i]}")"
    project="vtuber-${slug}"
    local subnet gateway allow_csv
    subnet="$(cluster_instance_subnet "$slot")"
    gateway="$(cluster_instance_gateway "$slot")"
    allow_csv="$(cluster_instance_allowlist "$gateway")"

    if [[ "${#only[@]}" -gt 0 ]]; then
      local match="0" q
      for q in "${only[@]}"; do
        if [[ "$q" == "$avatar" || "$q" == "$slug" ]]; then
          match="1"
          break
        fi
      done
      [[ "$match" == "1" ]] || continue
    fi

    IFS=$'\t' read -r signaling runner recorder game < <(cluster_instance_ports "$slot")
    session_dir="${session_base%/}/${slug}"
    recordings_dir="${recordings_base%/}/${slug}"
    mkdir -p "$session_dir" "$recordings_dir" || true

    instance_args="--public_port ${signaling} --matchmaker_streamer_id ${avatar}"

    VTUBER_AVATAR_ID="$avatar" \
      VTUBER_AVATAR_SLUG="$slug" \
      VTUBER_INSTANCE_PROJECT_NAME="$project" \
      VTUBER_SIGNALING_PUBLIC_PORT="$signaling" \
      VTUBER_RUNNER_PORT="$runner" \
      VTUBER_RECORDER_PORT="$recorder" \
      VTUBER_GAME_TCP_PORT="$game" \
      VTUBER_SESSION_DIR="$session_dir" \
    VTUBER_RECORDINGS_DIR="$recordings_dir" \
    VTUBER_SIGNALING_INSTANCE_ARGS="$instance_args" \
    VTUBER_DOCKER_SUBNET="$subnet" \
    VTUBER_ALLOWED_ADDRESSES="$allow_csv" \
    NVIDIA_VISIBLE_DEVICES="${gpu:-all}" \
      docker compose -p "$project" -f "$INSTANCE_COMPOSE_FILE" up "${instance_up_flags[@]}"
  done
}

cluster_compose_instance() {
  local project="$1"
  local slug="$2"
  shift 2
  VTUBER_AVATAR_SLUG="$slug" \
    VTUBER_INSTANCE_PROJECT_NAME="$project" \
    docker compose -p "$project" -f "$INSTANCE_COMPOSE_FILE" "$@"
}

cluster_deploy() {
  cd "$REPO_ROOT"
  [[ -f "$ENV_FILE" ]] || { echo "Missing .env (run: ./scripts/embody_cli.sh setup)" >&2; return 1; }
  [[ -f "$COMPOSE_FILE" ]] || { echo "Missing compose file: $COMPOSE_FILE" >&2; return 1; }
  [[ -f "$INSTANCE_COMPOSE_FILE" ]] || { echo "Missing instance compose file: $INSTANCE_COMPOSE_FILE" >&2; return 1; }
  cluster_ensure_docker || return 1

  local do_pull="1"
  local do_recreate="1"
  local up_args=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-pull)
        do_pull="0"
        shift 1
        ;;
      --no-recreate)
        do_recreate="0"
        shift 1
        ;;
      *)
        up_args+=("$1")
        shift 1
        ;;
    esac
  done

  local remote_cluster
  remote_cluster="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EXPERIMENTAL_REMOTE_CLUSTER_CONTROL" 2>/dev/null || true)")"
  remote_cluster="$(trim_whitespace "${remote_cluster:-}")"
  if [[ "$remote_cluster" != "1" ]] && is_tty; then
    echo "cluster: experimental remote cluster spawn/delete endpoints (:9090/cluster/*) are disabled by default." >&2
    if prompt_yes_no "Enable remote cluster control for this deploy? (experimental)" "n"; then
      export EXPERIMENTAL_REMOTE_CLUSTER_CONTROL="1"
      echo "cluster: enabled for this run (tip: add EXPERIMENTAL_REMOTE_CLUSTER_CONTROL=1 to .env to persist)." >&2
    fi
  fi

  if [[ "$do_pull" == "1" ]]; then
    "$START_SCRIPT" pull || return 1
  fi
  if [[ "$do_recreate" == "1" ]]; then
    cluster_up --recreate "${up_args[@]}"
  else
    cluster_up "${up_args[@]}"
  fi
}

cluster_down() {
  cd "$REPO_ROOT"
  cluster_read_config || return 1
  cluster_ensure_docker || return 1

  local only=()
  if [[ $# -gt 0 ]]; then
    only=("$@")
  fi

  local i avatar slug project match q
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    avatar="${CLUSTER_AVATAR_IDS[$i]}"
    slug="${CLUSTER_AVATAR_SLUGS[$i]}"
    project="vtuber-${slug}"

    if [[ "${#only[@]}" -gt 0 ]]; then
      match="0"
      for q in "${only[@]}"; do
        if [[ "$q" == "$avatar" || "$q" == "$slug" ]]; then
          match="1"
          break
        fi
      done
      [[ "$match" == "1" ]] || continue
    fi

    cluster_compose_instance "$project" "$slug" down
  done

  if [[ "${#only[@]}" -eq 0 ]]; then
    docker compose -p "$(cluster_host_project_name)" -f "$COMPOSE_FILE" down || true
  fi
}

cluster_gc() {
  cd "$REPO_ROOT"
  cluster_ensure_docker || return 1

  local yes="0"
  local dry_run="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --yes|-y)
        yes="1"
        shift 1
        ;;
      --dry-run)
        dry_run="1"
        shift 1
        ;;
      -h|--help|help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh cluster gc [--dry-run] [--yes]

Removes stopped cluster compose projects (prefix: vtuber-*) that have no running containers.
This does not touch the host-level project.
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for cluster gc: $1" >&2
        return 1
        ;;
    esac
  done

  local host_project ids inspect_out
  host_project="$(cluster_host_project_name)"
  ids="$(docker ps -aq 2>/dev/null || true)"
  [[ -n "$ids" ]] || { echo "cluster gc: no containers found." >&2; return 0; }

  inspect_out="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}\t{{.State.Status}}' $ids 2>/dev/null || true)"
  declare -A seen running
  local project status
  while IFS=$'\t' read -r project status; do
    project="$(trim_whitespace "${project:-}")"
    status="$(trim_whitespace "${status:-}")"
    [[ -n "$project" ]] || continue
    [[ "$project" == vtuber-* ]] || continue
    [[ "$project" != "$host_project" ]] || continue
    seen["$project"]="1"
    if [[ "$status" == "running" ]]; then
      running["$project"]="1"
    fi
  done <<<"$inspect_out"

  local candidates=() slug
  for project in "${!seen[@]}"; do
    [[ -z "${running[$project]:-}" ]] || continue
    slug="${project#vtuber-}"
    [[ -n "$slug" ]] || continue
    candidates+=("${project}:${slug}")
  done

  if [[ "${#candidates[@]}" -eq 0 ]]; then
    echo "cluster gc: nothing to clean." >&2
    return 0
  fi

  echo "cluster gc: stopped projects:"
  local entry
  for entry in "${candidates[@]}"; do
    echo "  - ${entry%%:*}"
  done

  if [[ "$dry_run" == "1" ]]; then
    return 0
  fi

  if is_tty && [[ "$yes" != "1" ]]; then
    if ! prompt_yes_no "Remove these stopped projects (docker compose down)?" "n"; then
      echo "cluster gc: skipped." >&2
      return 0
    fi
  elif [[ "$yes" != "1" ]]; then
    echo "cluster gc: refusing to run non-interactively without --yes" >&2
    return 1
  fi

  for entry in "${candidates[@]}"; do
    project="${entry%%:*}"
    slug="${entry#*:}"
    cluster_compose_instance "$project" "$slug" down || true
  done
}

cluster_status() {
  cd "$REPO_ROOT"
  cluster_read_config || return 1
  cluster_ensure_docker || return 1

  echo "Host:"
  docker compose -p "$(cluster_host_project_name)" -f "$COMPOSE_FILE" ps || true
  echo ""

  local only=()
  if [[ $# -gt 0 ]]; then
    only=("$@")
  fi

  local i avatar slug project match q
  for i in "${!CLUSTER_AVATAR_IDS[@]}"; do
    avatar="${CLUSTER_AVATAR_IDS[$i]}"
    slug="${CLUSTER_AVATAR_SLUGS[$i]}"
    project="vtuber-${slug}"

    if [[ "${#only[@]}" -gt 0 ]]; then
      match="0"
      for q in "${only[@]}"; do
        if [[ "$q" == "$avatar" || "$q" == "$slug" ]]; then
          match="1"
          break
        fi
      done
      [[ "$match" == "1" ]] || continue
    fi

    echo "Instance: ${avatar} (project=${project})"
    cluster_compose_instance "$project" "$slug" ps || true
    echo ""
  done
}

cluster_logs() {
  cd "$REPO_ROOT"
  cluster_read_config || return 1
  cluster_ensure_docker || return 1
  local which="${1:-}"
  local service="${2:-}"
  [[ -n "$which" ]] || { echo "Usage: ./scripts/embody_cli.sh cluster logs <avatar|slug> [service]" >&2; return 1; }
  local idx
  idx="$(cluster_find_instance_index "$which" 2>/dev/null || true)"
  [[ -n "$idx" ]] || { echo "Unknown instance: $which" >&2; return 1; }
  local slug="${CLUSTER_AVATAR_SLUGS[$idx]}"
  local project="vtuber-${slug}"
  if [[ -n "$service" ]]; then
    cluster_compose_instance "$project" "$slug" logs --tail=200 "$service"
  else
    cluster_compose_instance "$project" "$slug" logs --tail=200
  fi
}

cmd_cluster() {
  local sub="${1:-}"
  shift || true
  case "$sub" in
    init)
      local out="" prefix="" max_instances="" force="0"
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --output|--out)
            out="${2:-}"
            shift 2
            ;;
          --avatar-prefix|--prefix)
            prefix="${2:-}"
            shift 2
            ;;
          --max-instances)
            max_instances="${2:-}"
            shift 2
            ;;
          --force)
            force="1"
            shift 1
            ;;
          -h|--help|help)
            cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh cluster init [options]

Generates a default cluster config by inspecting local GPUs (via nvidia-smi).
Writes: ~/.embody/cluster.json (or --output).

Options:
  --output <path>         Write config to a custom path
  --avatar-prefix <text>  Prefix for generated avatar_id values (defaults to ORCHESTRATOR_ID)
  --max-instances <n>     Cap total instances (also capped to 20 slots)
  --force                Overwrite existing config file

Notes:
  - The estimate assumes ~8GiB VRAM per UE instance (override: EMBODY_VRAM_PER_INSTANCE_MIB=<MiB>)
  - cluster deploy can also auto-generate when config is missing: cluster deploy --auto
EOF
            return 0
            ;;
          *)
            echo "Unknown arg for cluster init: $1" >&2
            return 1
            ;;
        esac
      done
      cluster_write_auto_config "${out:-$(cluster_config_path)}" "$prefix" "$max_instances" "$(normalize_gpu_devices_csv "$(get_gpu_devices 2>/dev/null || true)")" "$force"
      ;;
    plan)
      cluster_plan "$@"
      ;;
    list)
      cluster_list "$@"
      ;;
    up|start)
      cluster_up "$@"
      ;;
    down|stop)
      cluster_down "$@"
      ;;
    gc)
      cluster_gc "$@"
      ;;
    deploy)
      cluster_deploy "$@"
      ;;
    auto)
      cluster_deploy --auto "$@"
      ;;
    status|ps)
      cluster_status "$@"
      ;;
    logs)
      cluster_logs "$@"
      ;;
    ""|-h|--help|help)
      cat <<EOF
Usage:
  ./scripts/embody_cli.sh cluster plan
  ./scripts/embody_cli.sh cluster init
  ./scripts/embody_cli.sh cluster list
  ./scripts/embody_cli.sh cluster up [--auto] [--yes] [--avatar-prefix <text>] [--max-instances <n>] [--force] [--recreate] [--pull always|missing|never] [avatar|slug...]
  ./scripts/embody_cli.sh cluster deploy [--no-pull] [--no-recreate] [--auto] [--yes] [--avatar-prefix <text>] [--max-instances <n>] [--force] [--pull always|missing|never] [avatar|slug...]
  ./scripts/embody_cli.sh cluster down [avatar|slug...]
  ./scripts/embody_cli.sh cluster gc [--dry-run] [--yes]
  ./scripts/embody_cli.sh cluster status [avatar|slug...]
  ./scripts/embody_cli.sh cluster logs <avatar|slug> [service]

Config:
  Path: $(cluster_config_path)
  Override: set EMBODY_CLUSTER_FILE=/path/to/cluster.json

Auto config:
  - Use --auto to generate the cluster config if missing (GPU detection + VRAM heuristic)
  - Confirm prompts: add --yes

Example:
$(cluster_print_example)
EOF
      ;;
    *)
      echo "Unknown cluster command: $sub" >&2
      return 1
      ;;
  esac
}

cmd_register() {
  local force="0"
  local payments_url orch_id orch_addr
  payments_url=""
  orch_id=""
  orch_addr=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        force="1"
        shift 1
        ;;
      --payments-api-url)
        payments_url="${2:-}"
        shift 2
        ;;
      --orchestrator-id|--orch-id)
        orch_id="${2:-}"
        shift 2
        ;;
      --orchestrator-address|--orch-address)
        orch_addr="${2:-}"
        shift 2
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh register [options]

Options:
  --payments-api-url <url>         Payments backend base URL (default: PAYMENTS_API_URL from .env)
  --orchestrator-id <id>           Orchestrator ID (defaults from .env)
  --orchestrator-address <0x...>   Payout wallet address (defaults from .env)
  --force                          Force registration even if cached state exists
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for register: $1" >&2
        return 1
        ;;
    esac
  done

  if [[ -z "$payments_url" ]]; then
    payments_url="$(get_payments_api_url)"
  fi
  [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

  if [[ -z "$orch_id" ]]; then
    orch_id="$(get_orchestrator_id)"
  fi
  if [[ -z "$orch_addr" ]]; then
    orch_addr="$(get_orchestrator_address)"
  fi

  [[ -n "$payments_url" ]] || { echo "Missing payments API URL" >&2; return 1; }
  [[ -n "$orch_id" ]] || { echo "Missing orchestrator ID (set ORCHESTRATOR_ID in .env or pass --orchestrator-id)" >&2; return 1; }
  [[ -n "$orch_addr" ]] || { echo "Missing orchestrator address (set ORCHESTRATOR_ADDRESS in .env or pass --orchestrator-address)" >&2; return 1; }

  command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }

  local args=(
    --api-url "$payments_url"
    --orchestrator-id "$orch_id"
    --orchestrator-address "$orch_addr"
    --max-retry-seconds 120
    --state-file "$REGISTRATION_STATE_FILE_DEFAULT"
    --skip-if-state-matches
  )
  if [[ "$force" == "1" ]]; then
    args+=(--force)
  fi

  python3 "$REPO_ROOT/scripts/register_orchestrator.py" "${args[@]}"
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" && -f "$REGISTRATION_STATE_FILE_DEFAULT" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$REGISTRATION_STATE_FILE_DEFAULT" 2>/dev/null || true
  fi
}

cmd_power() {
  local sub="${1:-status}"
  shift || true

  command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; return 1; }

  case "$sub" in
    -h|--help|help)
      cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh power
  ./scripts/embody_cli.sh power status
  ./scripts/embody_cli.sh power status [--project <compose_project>]
  ./scripts/embody_cli.sh power sleep [--project <compose_project>]
  ./scripts/embody_cli.sh power wake [--ttl <seconds>] [--project <compose_project>]
EOF
      return 0
      ;;
    ""|status)
      local project=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --project)
            project="${2:-}"
            shift 2
            ;;
          -h|--help)
            exec "$0" power --help
            ;;
          *)
            echo "Unknown arg for power status: $1" >&2
            return 1
            ;;
        esac
      done
      local endpoint="http://127.0.0.1:9090/power"
      if [[ -n "$project" ]]; then
        endpoint="http://127.0.0.1:9090/power/projects/${project}"
      fi
      curl -fsS --max-time 2 "$endpoint"
      echo ""
      ;;
    sleep)
      local project=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --project)
            project="${2:-}"
            shift 2
            ;;
          -h|--help)
            exec "$0" power --help
            ;;
          *)
            echo "Unknown arg for power sleep: $1" >&2
            return 1
            ;;
        esac
      done
      local endpoint="http://127.0.0.1:9090/power"
      if [[ -n "$project" ]]; then
        endpoint="http://127.0.0.1:9090/power/projects/${project}"
      fi
      curl -fsS --max-time 5 -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d '{"action":"sleep","reason":"cli"}'
      echo ""
      ;;
    wake)
      local ttl=""
      local project=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --ttl)
            ttl="${2:-}"
            shift 2
            ;;
          --project)
            project="${2:-}"
            shift 2
            ;;
          -h|--help)
            exec "$0" power --help
            ;;
          *)
            echo "Unknown arg for power wake: $1" >&2
            return 1
            ;;
        esac
      done
      local payload='{"action":"wake","reason":"cli"}'
      if [[ -n "$ttl" ]]; then
        payload="$(TTL="$ttl" python3 - <<'PY'
import json
import os
ttl = os.environ.get("TTL") or ""
try:
    sec = int(ttl)
except Exception:
    raise SystemExit(2)
print(json.dumps({"action": "wake", "reason": "cli", "awake_seconds": sec}))
PY
        )" || { echo "Invalid --ttl value (expected integer seconds)" >&2; return 1; }
      fi
      local endpoint="http://127.0.0.1:9090/power"
      if [[ -n "$project" ]]; then
        endpoint="http://127.0.0.1:9090/power/projects/${project}"
      fi
      curl -fsS --max-time 10 -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d "$payload"
      echo ""
      ;;
    *)
      echo "Unknown power command: $sub" >&2
      return 1
      ;;
  esac
}

container_env_value() {
  local container="$1" key="$2"
  docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | awk -v k="$key=" '
    index($0, k) == 1 {
      sub(k, "", $0)
      print
      exit
    }
  '
}

tcp_probe() {
  local host="$1" port="$2" timeout_s="${3:-2}"
  command -v python3 >/dev/null 2>&1 || return 1
  HOST="$host" PORT="$port" TIMEOUT="$timeout_s" python3 - <<'PY'
import os
import socket

host = os.environ.get("HOST") or ""
port_raw = os.environ.get("PORT") or ""
timeout_raw = os.environ.get("TIMEOUT") or "2"
try:
    port = int(port_raw)
except Exception:
    raise SystemExit(2)
try:
    timeout = float(timeout_raw)
except Exception:
    timeout = 2.0
try:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.close()
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
}

parse_matchmaker_from_args() {
  local args="$1"
  command -v python3 >/dev/null 2>&1 || return 1
  ARGS="$args" python3 - <<'PY'
import os
import shlex

raw = os.environ.get("ARGS") or ""
tokens = []
try:
    tokens = shlex.split(raw)
except Exception:
    tokens = raw.split()

host = ""
port = ""
use = False
for idx, tok in enumerate(tokens):
    if tok == "--use_matchmaker":
        use = True
    if tok.startswith("--matchmaker_address="):
        host = tok.split("=", 1)[1]
    if tok == "--matchmaker_address" and idx + 1 < len(tokens):
        host = tokens[idx + 1]
    if tok.startswith("--matchmaker_port="):
        port = tok.split("=", 1)[1]
    if tok == "--matchmaker_port" and idx + 1 < len(tokens):
        port = tokens[idx + 1]

if not use and not host:
    print("")
    print("")
    raise SystemExit(0)
print(host.strip())
print(port.strip())
PY
}

get_signaling_matchmaker() {
  local args extra matchmaker out host port
  extra="$(container_env_value vtuber-unreal-signaling SIGNALING_EXTRA_ARGS 2>/dev/null || true)"
  extra="$(strip_inline_comment "$(trim_whitespace "${extra:-}")")"
  if [[ -z "$extra" ]]; then
    extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "SIGNALING_EXTRA_ARGS" 2>/dev/null || true)")"
    extra="$(trim_whitespace "${extra:-}")"
  fi

  matchmaker="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "SIGNALING_MATCHMAKER_ARGS" 2>/dev/null || true)")"
  matchmaker="$(trim_whitespace "${matchmaker:-}")"

  args="$(trim_whitespace "${extra} ${matchmaker}")"
  out="$(parse_matchmaker_from_args "$args" || true)"
  host="$(printf '%s\n' "$out" | head -n 1 || true)"
  port="$(printf '%s\n' "$out" | tail -n 1 || true)"
  host="$(trim_whitespace "${host:-}")"
  port="$(trim_whitespace "${port:-}")"
  printf '%s\n%s' "$host" "$port"
}

cmd_verify() {
  init_ui
  local fix="0"
  local with_admin_payments="0"
  local no_record="0"
  local record_seconds="4"
  local edge_host="" edge_port=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fix)
        fix="1"
        shift 1
        ;;
      --payments|--payments-admin)
        with_admin_payments="1"
        shift 1
        ;;
      --no-record)
        no_record="1"
        shift 1
        ;;
      --record-seconds)
        record_seconds="${2:-}"
        shift 2
        ;;
      --edge-host)
        edge_host="${2:-}"
        shift 2
        ;;
      --edge-port)
        edge_port="${2:-}"
        shift 2
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh verify [options]

Options:
  --fix        Attempt to fix common drift (recreate runner+recorder; auto-fix Payments allowlists when possible)
  --payments   Also show Payments admin view (requires viewer/admin token)
  --no-record  Skip recorder start/download smoke test
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for verify: $1" >&2
        return 1
        ;;
    esac
  done

  local ok="1"
  local allowlist_ok="1"
  local awake=""

  if [[ ! "${record_seconds:-}" =~ ^[0-9]+$ ]]; then
    record_seconds="4"
  fi
  if [[ "$record_seconds" -lt 2 ]]; then
    record_seconds="2"
  elif [[ "$record_seconds" -gt 20 ]]; then
    record_seconds="20"
  fi

  if [[ -n "${edge_port:-}" ]] && [[ ! "${edge_port}" =~ ^[0-9]+$ ]]; then
    edge_port=""
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    ui_check ".env" "FAIL" "(missing; run: ./scripts/embody_cli.sh setup)"
    return 1
  fi

  command -v docker >/dev/null 2>&1 || { ui_check "docker" "FAIL" "(missing dependency)"; return 1; }
  if ! docker info >/dev/null 2>&1; then
    ui_check "docker" "FAIL" "(daemon not reachable; try sudo or add user to docker group)"
    return 1
  fi
  command -v curl >/dev/null 2>&1 || { ui_check "curl" "FAIL" "(missing dependency)"; return 1; }
  command -v python3 >/dev/null 2>&1 || { ui_check "python3" "FAIL" "(missing dependency)"; return 1; }

  ui_title "Embody Orchestrator — Verify"

  ui_section "Power"
  local power_out power_state
  power_state="unknown"
  power_out="$(curl -sS --max-time 3 http://127.0.0.1:9090/power 2>/dev/null || true)"
  if [[ -z "$power_out" ]]; then
    ui_check "power api" "FAIL" "(http://127.0.0.1:9090/power unreachable)"
    ok="0"
  else
    power_state="$(BODY="$power_out" python3 - <<'PY' || true
import json
import os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
print((data.get("state") or "").strip() or "unknown")
PY
    )"
    if [[ "$power_state" == "sleeping" ]]; then
      ui_check "power state" "WARN" "(sleeping)"
      awake="0"
      if [[ "$fix" == "1" ]] && is_tty && prompt_yes_no "Wake stack to run full checks?" "y"; then
        cmd_power wake || true
        sleep 5
        awake="1"
        ui_check "power wake" "OK"
      fi
    elif [[ "$power_state" == "awake" ]]; then
      ui_check "power state" "OK" "(awake)"
      awake="1"
    else
      ui_check "power state" "WARN" "(state=${power_state})"
      awake=""
    fi
  fi

  ui_section "Containers"
  local required=(vtuber-orchestrator-health)
  if [[ "${awake:-}" == "1" ]]; then
    required+=(vtuber-unreal-game vtuber-unreal-signaling vtuber-script-runner vtuber-recorder-control)
  fi

  local c status
  for c in "${required[@]}"; do
    if ! docker inspect "$c" >/dev/null 2>&1; then
      ui_check "$c" "FAIL" "(missing)"
      ok="0"
      continue
    fi
    status="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || true)"
    if [[ "$status" == "running" ]]; then
      ui_check "$c" "OK" "(running)"
    else
      ui_check "$c" "FAIL" "(${status:-unknown})"
      ok="0"
    fi
  done

  ui_section "Endpoints"
  curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 && ui_check "orch health" "OK" || { ui_check "orch health" "FAIL"; ok="0"; }
  if [[ "${awake:-}" == "1" ]]; then
    curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 && ui_check "signaling" "OK" || { ui_check "signaling" "FAIL"; ok="0"; }
    curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 && ui_check "runner" "OK" || { ui_check "runner" "FAIL"; ok="0"; }
    local rec_api_token
    rec_api_token="$(container_env_value vtuber-recorder-control RECORDINGS_API_TOKEN 2>/dev/null || true)"
    rec_api_token="$(trim_whitespace "${rec_api_token:-}")"
    if [[ -n "$rec_api_token" ]]; then
      curl -fsS --max-time 2 -H "Authorization: Bearer ${rec_api_token}" http://127.0.0.1:8889/recordings/status >/dev/null 2>&1 \
        && ui_check "recorder" "OK" \
        || { ui_check "recorder" "FAIL"; ok="0"; }
    else
      curl -fsS --max-time 2 http://127.0.0.1:8889/recordings/status >/dev/null 2>&1 \
        && ui_check "recorder" "OK" \
        || { ui_check "recorder" "FAIL"; ok="0"; }
    fi
  else
    ui_check "signaling" "SKIP" "(stack sleeping)"
    ui_check "runner" "SKIP" "(stack sleeping)"
    ui_check "recorder" "SKIP" "(stack sleeping)"
  fi

  ui_section "Allowlists"
  local allow_env allow_runner allow_recorder
  allow_env="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
  allow_runner="$(container_env_value vtuber-script-runner VTUBER_ALLOWED_ADDRESSES || true)"
  allow_recorder="$(container_env_value vtuber-recorder-control VTUBER_ALLOWED_ADDRESSES || true)"

  ui_kv "env" "${allow_env:-<unset>}"
  ui_kv "runner" "${allow_runner:-<unset>}"
  ui_kv "recorder" "${allow_recorder:-<unset>}"

  if [[ -n "$allow_env" ]] && { [[ "$allow_env" != "$allow_runner" ]] || [[ "$allow_env" != "$allow_recorder" ]]; }; then
    ui_check "allowlist" "WARN" "(DRIFT: containers not running with current VTUBER_ALLOWED_ADDRESSES)"
    allowlist_ok="0"
    if [[ "$fix" == "1" ]]; then
      ui_check "allowlist fix" "WARN" "(recreating runner+recorder to reload .env)"
      docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
        up -d --force-recreate vtuber-script-runner recorder-control
      allow_runner="$(container_env_value vtuber-script-runner VTUBER_ALLOWED_ADDRESSES || true)"
      allow_recorder="$(container_env_value vtuber-recorder-control VTUBER_ALLOWED_ADDRESSES || true)"
      if [[ "$allow_env" == "$allow_runner" && "$allow_env" == "$allow_recorder" ]]; then
        ui_check "allowlist" "OK" "(fixed)"
        allowlist_ok="1"
      else
        ui_check "allowlist" "FAIL" "(still drifted after recreate)"
      fi
    fi
  else
    ui_check "allowlist" "OK"
  fi

  ui_section "Networking"
  local payments_url payments_host payments_ip plane_url edge_ports
  payments_url="$(get_payments_api_url)"
  payments_host="$(extract_host_from_url "$payments_url")"
  payments_ip=""
  if [[ -n "$payments_host" ]] && is_ipv4 "$payments_host" >/dev/null 2>&1; then
    payments_ip="$payments_host"
    ui_kv "payments ip" "$payments_ip"
  else
    ui_check "payments ip" "WARN" "(cannot parse IPv4 from PAYMENTS_API_URL; skip allowlist checks)"
  fi

  if curl -sS --max-time 4 -I https://s3.amazonaws.com/ >/dev/null 2>&1; then
    ui_check "outbound https" "OK" "(s3.amazonaws.com)"
  else
    ui_check "outbound https" "WARN" "(cannot reach s3.amazonaws.com; presigned uploads may fail)"
  fi

  plane_url="$(get_edge_config_url)"
  edge_ports="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_ALLOW_PORTS" 2>/dev/null || true)")"
  if [[ -n "$plane_url" ]]; then
    ui_check "edge plane" "OK" "(EDGE_CONFIG_URL set)"
    if [[ -n "$payments_ip" ]]; then
      local fw_extra power_extra local_allow want_cidr
      want_cidr="${payments_ip}/32"
      fw_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_FIREWALL_EXTRA_CIDRS" 2>/dev/null || true)")"
      power_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_POWER_EXTRA_CIDRS" 2>/dev/null || true)")"
      local_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" 2>/dev/null || true)")"

      if [[ "$(csv_has_token "$fw_extra" "$want_cidr")" == "1" ]]; then
        ui_check "payments fw" "OK"
      else
        ui_check "payments fw" "WARN" "(missing ${want_cidr}; fix: ./scripts/embody_cli.sh allowlists fix)"
      fi

      if [[ "$(csv_has_token "$power_extra" "$want_cidr")" == "1" ]]; then
        ui_check "payments /power" "OK"
      else
        ui_check "payments /power" "WARN" "(missing ${want_cidr}; fix: ./scripts/embody_cli.sh allowlists fix)"
      fi

      if [[ "$(csv_has_token "$local_allow" "$payments_ip")" == "1" ]]; then
        ui_check "payments runner/rec" "OK"
      else
        ui_check "payments runner/rec" "WARN" "(missing ${payments_ip}; fix: ./scripts/embody_cli.sh allowlists fix)"
      fi

      if [[ "$fix" == "1" ]]; then
        local changed="0"
        if [[ "$(csv_has_token "$fw_extra" "$want_cidr")" != "1" ]]; then
          fw_extra="$(csv_add_token "$fw_extra" "$want_cidr")"
          if ! upsert_env_kv "$ENV_FILE" "EDGE_FIREWALL_EXTRA_CIDRS" "$fw_extra"; then
            ui_check "env" "FAIL" "(failed to update EDGE_FIREWALL_EXTRA_CIDRS)"
            return 1
          fi
          changed="1"
        fi
        if [[ "$(csv_has_token "$power_extra" "$want_cidr")" != "1" ]]; then
          power_extra="$(csv_add_token "$power_extra" "$want_cidr")"
          if ! upsert_env_kv "$ENV_FILE" "EDGE_POWER_EXTRA_CIDRS" "$power_extra"; then
            ui_check "env" "FAIL" "(failed to update EDGE_POWER_EXTRA_CIDRS)"
            return 1
          fi
          changed="1"
        fi
        if [[ -z "$local_allow" ]]; then
          local_allow="127.0.0.1,::1,172.17.0.1,172.18.0.1"
        fi
        if [[ "$(csv_has_token "$local_allow" "$payments_ip")" != "1" ]]; then
          local_allow="$(csv_add_token "$local_allow" "$payments_ip")"
          if ! upsert_env_kv "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" "$local_allow"; then
            ui_check "env" "FAIL" "(failed to update EDGE_LOCAL_ALLOWLIST)"
            return 1
          fi
          changed="1"
        fi

        if [[ "$changed" == "1" ]]; then
          ui_check "allowlists fix" "WARN" "(updated .env; restarting edge rotator)"
          if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
            up -d --force-recreate orchestrator-edge-rotator >/dev/null 2>&1; then
            ui_check "allowlists fix" "FAIL" "(docker compose failed)"
            return 1
          fi
          ui_check "allowlists fix" "OK"
        fi
      fi
    fi

    if [[ -n "$edge_ports" ]]; then
      local ports_rc="0"
      EDGE_PORTS="$edge_ports" python3 - <<'PY' >/dev/null 2>&1 || ports_rc="$?"
import os
raw = os.environ.get("EDGE_PORTS") or ""
needed = [("tcp", 8889), ("tcp", 9877), ("tcp", 9090)]
parsed = []
for token in raw.split(","):
    token = token.strip()
    if not token:
        continue
    if "/" in token:
        port_part, proto = token.split("/", 1)
        proto = proto.strip().lower()
    else:
        port_part, proto = token, "tcp"
    if proto not in ("tcp", "udp"):
        raise SystemExit(2)
    if "-" in port_part:
        a, b = port_part.split("-", 1)
        start, end = int(a), int(b)
    else:
        start = end = int(port_part)
    parsed.append((proto, start, end))
def covers(proto, port):
    for p, start, end in parsed:
        if p != proto:
            continue
        if start <= port <= end:
            return True
    return False
missing = [(proto, port) for proto, port in needed if not covers(proto, port)]
if missing:
    raise SystemExit(1)
PY
      if [[ "$ports_rc" == "0" ]]; then
        ui_check "edge ports" "OK" "(EDGE_ALLOW_PORTS includes 8889/9877/9090)"
      elif [[ "$ports_rc" == "2" ]]; then
        ui_check "edge ports" "WARN" "(invalid EDGE_ALLOW_PORTS)"
      else
        ui_check "edge ports" "WARN" "(EDGE_ALLOW_PORTS missing 8889/9877/9090; fix: clear it or include required ports)"
      fi
    else
      ui_check "edge ports" "OK" "(default ports)"
    fi
  else
    ui_check "edge plane" "SKIP" "(manual edge mode)"
    if [[ -n "$payments_ip" ]]; then
      local allow_csv
      allow_csv="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
      if [[ "$(csv_has_token "$allow_csv" "$payments_ip")" == "1" ]]; then
        ui_check "payments allowlist" "OK"
      else
        ui_check "payments allowlist" "WARN" "(missing ${payments_ip}; fix: ./scripts/embody_cli.sh setup --allowed-ip ${payments_ip})"
      fi

      if [[ "$fix" == "1" ]]; then
        local changed="0"
        if [[ -z "$allow_csv" ]]; then
          allow_csv="127.0.0.1,::1,172.17.0.1,172.18.0.1"
        fi
        if [[ "$(csv_has_token "$allow_csv" "$payments_ip")" != "1" ]]; then
          allow_csv="$(csv_add_token "$allow_csv" "$payments_ip")"
          if ! upsert_env_kv "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" "$allow_csv"; then
            ui_check "env" "FAIL" "(failed to update VTUBER_ALLOWED_ADDRESSES)"
            return 1
          fi
          changed="1"
        fi

        local power_allow want_cidr
        power_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "POWER_ALLOWED_IPS" 2>/dev/null || true)")"
        want_cidr="${payments_ip}/32"
        if [[ -z "$power_allow" ]]; then
          power_allow="127.0.0.1/32,::1/128"
        fi
        if [[ "$(csv_has_token "$power_allow" "$want_cidr")" != "1" && "$(csv_has_token "$power_allow" "$payments_ip")" != "1" ]]; then
          power_allow="$(csv_add_token "$power_allow" "$want_cidr")"
          if ! upsert_env_kv "$ENV_FILE" "POWER_ALLOWED_IPS" "$power_allow"; then
            ui_check "env" "FAIL" "(failed to update POWER_ALLOWED_IPS)"
            return 1
          fi
          changed="1"
        fi

        if [[ "$changed" == "1" ]]; then
          ui_check "allowlists fix" "WARN" "(updated .env; recreating containers)"
          if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
            up -d --force-recreate orchestrator-health >/dev/null 2>&1; then
            ui_check "allowlists fix" "FAIL" "(failed to recreate orchestrator-health)"
            return 1
          fi
          if docker inspect -f '{{.State.Status}}' vtuber-unreal-game >/dev/null 2>&1; then
            if [[ "$(docker inspect -f '{{.State.Status}}' vtuber-unreal-game 2>/dev/null || true)" == "running" ]]; then
              if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
                up -d --force-recreate vtuber-script-runner recorder-control >/dev/null 2>&1; then
                ui_check "allowlists fix" "FAIL" "(failed to recreate runner/recorder)"
                return 1
              fi
            else
              if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
                up --no-start --force-recreate vtuber-script-runner recorder-control >/dev/null 2>&1; then
                ui_check "allowlists fix" "FAIL" "(failed to update runner/recorder)"
                return 1
              fi
            fi
          fi
          ui_check "allowlists fix" "OK"
        fi
      fi
    fi
  fi

  ui_section "Edge"
  if [[ -z "$edge_host" ]]; then
    local mm_out mm_host mm_port
    mm_out="$(get_signaling_matchmaker || true)"
    mm_host="$(printf '%s\n' "$mm_out" | head -n 1 || true)"
    mm_port="$(printf '%s\n' "$mm_out" | tail -n 1 || true)"
    edge_host="$mm_host"
    edge_port="$mm_port"
  fi
  edge_host="$(trim_whitespace "${edge_host:-}")"
  edge_port="$(trim_whitespace "${edge_port:-}")"
  if [[ -n "$edge_host" && -n "$edge_port" ]]; then
    if tcp_probe "$edge_host" "$edge_port" 2 >/dev/null 2>&1; then
      ui_check "matchmaker" "OK" "(${edge_host}:${edge_port})"
    else
      ui_check "matchmaker" "FAIL" "(${edge_host}:${edge_port})"
      ok="0"
    fi
    if curl -fsS --max-time 3 "https://${edge_host}/api/status" >/dev/null 2>&1; then
      ui_check "edge status" "OK" "(https://${edge_host}/api/status)"
    elif curl -fsS --max-time 3 "http://${edge_host}/api/status" >/dev/null 2>&1; then
      ui_check "edge status" "OK" "(http://${edge_host}/api/status)"
    else
      ui_check "edge status" "WARN" "(cannot fetch /api/status; may be blocked)"
    fi
  else
    ui_check "matchmaker" "SKIP" "(not configured)"
    ui_check "edge status" "SKIP" "(not configured)"
  fi

  ui_section "E2E"
  if [[ "${awake:-}" != "1" ]]; then
    ui_check "runner tcp" "SKIP" "(stack sleeping)"
    ui_check "record/download" "SKIP" "(stack sleeping)"
  else
    # Runner TCP smoke test (sends a single BYOB command through the runner to the game TCP port).
    local session_id payload resp status_url status_body state
    session_id="verify_$(date +%s 2>/dev/null || echo 0)_$RANDOM"
    payload="$(SESSION_ID="$session_id" python3 - <<'PY'
import json
import os
sid = os.environ.get("SESSION_ID") or "verify"
print(json.dumps({
  "session_id": sid,
  "commands": [{"delay_ms": 0, "type": "tcp", "value": "TTS_BYOB_/opt/embody/sample-15s.mp3"}],
  "audio": [],
}))
PY
    )"
    resp="$(curl -sS --max-time 5 -H "Content-Type: application/json" -d "$payload" http://127.0.0.1:9877/scripts/execute 2>/dev/null || true)"
    status_url="http://127.0.0.1:9877/scripts/${session_id}"
    state=""
    for _ in {1..15}; do
      status_body="$(curl -sS --max-time 3 "$status_url" 2>/dev/null || true)"
      state="$(BODY="$status_body" python3 - <<'PY'
import json
import os
try:
    data = json.loads(os.environ.get("BODY") or "")
except Exception:
    data = {}
print((data.get("state") or "").strip())
PY
      )"
      [[ -n "$state" ]] || state=""
      if [[ "$state" == "completed" ]]; then
        break
      fi
      if [[ "$state" == "failed" ]]; then
        break
      fi
      sleep 1
    done
    if [[ "$state" == "completed" ]]; then
      ui_check "runner tcp" "OK"
    else
      ui_check "runner tcp" "FAIL" "(state=${state:-unknown})"
      ok="0"
    fi

    # Recorder smoke test (record a few seconds, download the file, then delete it).
    if [[ "$no_record" == "1" ]]; then
      ui_check "record/download" "SKIP" "(--no-record)"
    else
      local rec_status rec_active rec_label rec_dir rec_token rec_auth_headers rec_start_headers rec_resp rec_file tmpfile bytes start_out start_code start_body predicted prefix base_num found
      rec_token="$(container_env_value vtuber-recorder-control RECORDINGS_API_TOKEN 2>/dev/null || true)"
      rec_token="$(trim_whitespace "${rec_token:-}")"
      rec_auth_headers=()
      if [[ -n "$rec_token" ]]; then
        rec_auth_headers=(-H "Authorization: Bearer ${rec_token}")
      fi

      rec_status="$(curl -sS --max-time 3 "${rec_auth_headers[@]}" http://127.0.0.1:8889/recordings/status 2>/dev/null || true)"
      rec_active="$(BODY="$rec_status" python3 - <<'PY' || true
import json, os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
print("1" if data.get("active") else "0")
PY
      )"
      if [[ "$rec_active" == "1" ]]; then
        ui_check "record/download" "WARN" "(recorder already active; skipping)"
      else
        rec_label="verify_$(date +%s 2>/dev/null || echo 0)_$RANDOM"
        rec_dir="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_RECORDINGS_DIR" 2>/dev/null || true)")"
        rec_dir="$(trim_whitespace "${rec_dir:-}")"
        [[ -n "$rec_dir" ]] || rec_dir="/recordings"

        rec_start_headers=(-H "Content-Type: application/json" "${rec_auth_headers[@]}")

        rec_resp="$(LABEL="$rec_label" SECONDS="$record_seconds" python3 - <<'PY'
import json, os
label = os.environ.get("LABEL") or "verify"
sec_raw = os.environ.get("SECONDS") or "4"
try:
    sec = int(sec_raw)
except Exception:
    sec = 4
print(json.dumps({"label": label, "duration": max(2, min(sec, 20))}))
PY
        )"

        start_out="$(curl -sS --max-time 12 -X POST "${rec_start_headers[@]}" -d "$rec_resp" -w $'\n%{http_code}' http://127.0.0.1:8889/recordings/start 2>/dev/null || true)"
        start_code="${start_out##*$'\n'}"
        start_body="${start_out%$'\n'*}"
        if [[ "$start_code" != "200" && "$start_code" != "201" ]]; then
          ui_check "record/download" "FAIL" "(start failed)"
          ok="0"
        else
          predicted="$(BODY="$start_body" python3 - <<'PY' || true
import json
import os
import os.path
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
print(os.path.basename(str(data.get("output") or "")))
PY
          )"

          sleep $(( record_seconds + 3 ))

          rec_file=""
          if [[ -n "$rec_dir" && -d "$rec_dir" ]]; then
            rec_file="$(ls -t "${rec_dir}/${rec_label}"_*.mkv 2>/dev/null | head -n 1 || true)"
            rec_file="$(basename "${rec_file:-}" 2>/dev/null || true)"
          fi

          if [[ -z "$rec_file" && -n "$predicted" ]]; then
            if curl -fsS --max-time 2 -I "${rec_auth_headers[@]}" "http://127.0.0.1:8889/recordings/${predicted}" >/dev/null 2>&1; then
              rec_file="$predicted"
            fi
          fi

          if [[ -z "$rec_file" && -n "$predicted" && "$predicted" =~ ^(.*)_([0-9]+)[.]mkv$ ]]; then
            prefix="${BASH_REMATCH[1]}"
            base_num="${BASH_REMATCH[2]}"
            found=""
            for ((delta=-10; delta<=120; delta++)); do
              cand="${prefix}_$((base_num + delta)).mkv"
              if curl -fsS --max-time 2 -I "${rec_auth_headers[@]}" "http://127.0.0.1:8889/recordings/${cand}" >/dev/null 2>&1; then
                found="$cand"
                break
              fi
            done
            if [[ -n "$found" ]]; then
              rec_file="$found"
            fi
          fi

          if [[ -z "$rec_file" ]]; then
            ui_check "record/download" "FAIL" "(no output file found)"
            ok="0"
          else
            tmpfile="/tmp/${rec_file}"
            rm -f "$tmpfile" >/dev/null 2>&1 || true
            if curl -fsS --max-time 15 "${rec_auth_headers[@]}" "http://127.0.0.1:8889/recordings/${rec_file}" -o "$tmpfile" >/dev/null 2>&1; then
              bytes="$(wc -c < "$tmpfile" 2>/dev/null || echo 0)"
              if [[ "$bytes" =~ ^[0-9]+$ && "$bytes" -gt 0 ]]; then
                ui_check "record/download" "OK" "(${bytes} bytes)"
              else
                ui_check "record/download" "FAIL" "(download empty)"
                ok="0"
              fi
            else
              ui_check "record/download" "FAIL" "(download failed)"
              ok="0"
            fi
            curl -fsS --max-time 5 -X DELETE "${rec_auth_headers[@]}" "http://127.0.0.1:8889/recordings/${rec_file}" >/dev/null 2>&1 || true
            rm -f "$tmpfile" >/dev/null 2>&1 || true
          fi
        fi
      fi
    fi
  fi

  ui_section "Payments"
  local payments_url token me_out me_code payments_ok
  payments_ok="0"
  payments_url="$(get_payments_api_url)"
  payments_url="$(trim_whitespace "${payments_url:-}")"
  [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"
  token="$(read_orchestrator_token)"
  if [[ -z "$token" ]]; then
    ui_check "payments" "WARN" "(missing orchestrator token; run: ./scripts/embody_cli.sh license redeem)"
    ok="0"
  else
    me_out="$(payments_self_me "$payments_url" 4 || true)"
    me_code="$(printf '%s\n' "$me_out" | head -n 1 || true)"
    cmd_payments self || true
    if [[ "$me_code" == "200" ]]; then
      payments_ok="1"
    fi
    if [[ "$me_code" == "404" ]]; then
      ok="0"
    elif [[ "$me_code" == "401" ]]; then
      ok="0"
    fi
  fi
  if [[ "$with_admin_payments" == "1" ]]; then
    echo ""
    ui_section "Payments (Admin)"
    cmd_payments admin || true
  fi

  local container_lines="" c status image_ref image_id
  local containers_to_capture=(
    vtuber-orchestrator-health
    vtuber-orchestrator-edge-rotator
    vtuber-turn-server
    vtuber-auto-updater
    vtuber-watchdog
    vtuber-orchestrator-registration
    vtuber-unreal-signaling
    vtuber-unreal-game
    vtuber-script-runner
    vtuber-recorder-control
  )
  for c in "${containers_to_capture[@]}"; do
    if ! docker inspect "$c" >/dev/null 2>&1; then
      container_lines+="${c}\tmissing\t\t\n"
      continue
    fi
    status="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || true)"
    image_ref="$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null || true)"
    image_id="$(docker inspect -f '{{.Image}}' "$c" 2>/dev/null || true)"
    container_lines+="${c}\t${status}\t${image_ref}\t${image_id}\n"
  done

  local branch sha ran_at verify_json verify_out_path
  branch=""
  sha=""
  if is_git_repo; then
    branch="$(trim_whitespace "$(git_current_branch)")"
    sha="$(trim_whitespace "$(git_remote_commit HEAD)")"
  fi
  ran_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u)"

  verify_json="$(RAN_AT="$ran_at" OK="$ok" ALLOWLIST_OK="$allowlist_ok" POWER_STATE="$power_state" AWAKE="$awake" \
    PAYMENTS_OK="$payments_ok" PAYMENTS_URL="$payments_url" PAYMENTS_HTTP_CODE="$me_code" \
    GIT_BRANCH="$branch" GIT_SHA="$sha" CONTAINERS="$container_lines" python3 - <<'PY' || true
import json
import os

def clean(s: str) -> str:
    return (s or "").strip()

def as_bool01(s: str) -> bool:
    return clean(s) == "1"

def as_int(s: str):
    s = clean(s)
    try:
        return int(s)
    except Exception:
        return None

containers_raw = os.environ.get("CONTAINERS") or ""
containers = []
for line in containers_raw.splitlines():
    parts = line.split("\\t")
    name = parts[0] if len(parts) > 0 else ""
    status = parts[1] if len(parts) > 1 else ""
    image = parts[2] if len(parts) > 2 else ""
    image_id = parts[3] if len(parts) > 3 else ""
    containers.append(
        {
            "name": clean(name),
            "status": clean(status),
            "image": clean(image) or None,
            "image_id": clean(image_id) or None,
        }
    )

data = {
    "ran_at": clean(os.environ.get("RAN_AT")),
    "ok": as_bool01(os.environ.get("OK")),
    "allowlist_ok": as_bool01(os.environ.get("ALLOWLIST_OK")),
    "power_state": clean(os.environ.get("POWER_STATE")) or None,
    "awake": True if clean(os.environ.get("AWAKE")) == "1" else (False if clean(os.environ.get("AWAKE")) == "0" else None),
    "payments": {
        "ok": as_bool01(os.environ.get("PAYMENTS_OK")),
        "url": clean(os.environ.get("PAYMENTS_URL")) or None,
        "http_code": as_int(os.environ.get("PAYMENTS_HTTP_CODE")),
    },
    "git": {
        "branch": clean(os.environ.get("GIT_BRANCH")) or None,
        "sha": clean(os.environ.get("GIT_SHA")) or None,
    },
    "containers": containers,
}

print(json.dumps(data, sort_keys=True))
PY
  )"

  if [[ -n "$verify_json" ]]; then
    verify_out_path="$(write_state_json_best_effort "$VERIFY_LAST_FILE_DEFAULT" "$VERIFY_LAST_FILE_FALLBACK" "$verify_json" || true)"
    [[ -n "$verify_out_path" ]] && ui_check "verify state" "OK" "(${verify_out_path})"
  fi

  [[ "$ok" == "1" && "$allowlist_ok" == "1" ]]
}

cmd_payments() {
  init_ui
  local sub="${1:-}"
  shift || true

  case "$sub" in
    -h|--help|help)
      cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh payments              # Show your own orchestrator stats (token-based)
  ./scripts/embody_cli.sh payments self         # Same as above
  ./scripts/embody_cli.sh payments admin        # List orchestrators (viewer/admin token)
  ./scripts/embody_cli.sh payments token        # Show viewer/admin token status
  ./scripts/embody_cli.sh payments token set    # Store viewer/admin token

Notes:
  - Self status uses your **orchestrator token** (from `~/.embody/orch-license-token.txt`).
  - Admin status uses `X-Admin-Token` (viewer/admin token): PAYMENTS_VIEWER_TOKEN env, PAYMENTS_ADMIN_TOKEN env, then ~/.embody/payments-viewer-token.txt
EOF
      return 0
      ;;
    token)
      local action="${1:-status}"
      shift || true
      case "$action" in
        ""|status)
          if [[ -s "$PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT" ]]; then
            echo "Payments token: present (${PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT})"
          else
            echo "Payments token: missing (${PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT})"
          fi
          ;;
        set)
          if ! is_tty; then
            echo "Refusing to prompt for a token on non-interactive stdin." >&2
            return 1
          fi
          local token
          token="$(prompt_secret "Payments viewer/admin token (X-Admin-Token)")"
          [[ -n "$token" ]] || { echo "Missing token" >&2; return 1; }
          write_token_file "$PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT" "$token"
          echo "Payments token: stored (${PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT})"
          ;;
        *)
          echo "Unknown payments token command: $action" >&2
          return 1
          ;;
      esac
      ;;
    self|me|status|verify|"")
      local payments_url token out code body stats_out stats_code stats_body
      payments_url="$(get_payments_api_url)"
      payments_url="$(trim_whitespace "${payments_url:-}")"
      [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

      command -v curl >/dev/null 2>&1 || { ui_check "payments" "FAIL" "(missing dependency: curl)"; return 1; }
      command -v python3 >/dev/null 2>&1 || { ui_check "payments" "FAIL" "(missing dependency: python3)"; return 1; }

      token="$(read_orchestrator_token)"
      if [[ -z "$token" ]]; then
        ui_check "payments" "WARN" "(missing orchestrator token; run: ./scripts/embody_cli.sh license redeem)"
        return 1
      fi

      out="$(payments_self_me "$payments_url" 6 || true)"
      code="$(printf '%s\n' "$out" | head -n 1 || true)"
      body="$(printf '%s\n' "$out" | tail -n +2 || true)"

      case "$code" in
        200)
          ui_check "payments" "OK"
          local summary
          summary="$(BODY="$body" python3 - <<'PY' || true
import json
import os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
orch_id = (data.get("orchestrator_id") or "").strip()
balance = data.get("balance_eth")
eligible = data.get("eligible_for_payments")
deny = data.get("denylisted")
cooldown = data.get("cooldown_active")
active = data.get("active")
active_sessions = data.get("active_sessions")
last_seen = (data.get("last_seen") or "").strip()
parts = []
if orch_id:
    parts.append(f"id={orch_id}")
if balance is not None:
    parts.append(f"balance={balance}")
if eligible is not None:
    parts.append(f"eligible={eligible}")
if deny is not None:
    parts.append(f"denylisted={deny}")
if cooldown is not None:
    parts.append(f"cooldown={cooldown}")
if active is not None:
    parts.append(f"active={active}")
if active_sessions is not None:
    parts.append(f"sessions={active_sessions}")
if last_seen:
    parts.append(f"last_seen={last_seen}")
print(", ".join(parts))
PY
          )"
          if [[ -n "$summary" ]]; then
            ui_kv "Self" "$summary"
          fi

          stats_out="$(payments_self_stats "$payments_url" 8 30 || true)"
          stats_code="$(printf '%s\n' "$stats_out" | head -n 1 || true)"
          stats_body="$(printf '%s\n' "$stats_out" | tail -n +2 || true)"
          if [[ "$stats_code" == "200" ]]; then
            local stats_line
            stats_line="$(BODY="$stats_body" python3 - <<'PY' || true
import json
import os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
days = data.get("days")
credits = data.get("total_credits_eth")
payouts = data.get("total_payouts_eth")
session = data.get("total_session_eth")
workload = data.get("total_workload_eth")
adj = data.get("total_adjustments_eth")
parts = []
if days is not None:
    parts.append(f"days={days}")
if credits is not None:
    parts.append(f"credits={credits}")
if payouts is not None:
    parts.append(f"payouts={payouts}")
if session is not None:
    parts.append(f"session={session}")
if workload is not None:
    parts.append(f"workload={workload}")
if adj is not None:
    parts.append(f"adjustments={adj}")
print(", ".join(parts))
PY
            )"
            if [[ -n "$stats_line" ]]; then
              ui_kv "Stats" "$stats_line"
            fi
          fi
          ;;
        404)
          ui_check "payments" "WARN" "(not registered; run: ./scripts/embody_cli.sh register)"
          return 1
          ;;
        401)
          ui_check "payments" "FAIL" "(invalid orchestrator token; re-run: ./scripts/embody_cli.sh license redeem)"
          return 1
          ;;
        *)
          ui_check "payments" "WARN" "(request failed; HTTP ${code:-?})"
          return 1
          ;;
      esac
      ;;
    admin|list)
      local payments_url orch_id orch_addr token url json
      payments_url="$(get_payments_api_url)"
      [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"
      orch_id="$(get_orchestrator_id)"
      orch_addr="$(get_orchestrator_address)"

      token="$(read_payments_viewer_token)"
      if [[ -z "$token" ]]; then
        if is_tty && prompt_yes_no "Payments token missing. Store one now?" "y"; then
          cmd_payments token set || return 1
          token="$(read_payments_viewer_token)"
        fi
      fi
      [[ -n "$token" ]] || { echo "Missing Payments token (set PAYMENTS_VIEWER_TOKEN or run: ./scripts/embody_cli.sh payments token set)" >&2; return 1; }
      [[ -n "$orch_id" ]] || { echo "Missing ORCHESTRATOR_ID in .env" >&2; return 1; }

      command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; return 1; }
      command -v python3 >/dev/null 2>&1 || { echo "Missing dependency: python3" >&2; return 1; }

      url="${payments_url%/}/api/orchestrators"
      json="$(curl -fsS --max-time 5 -H "X-Admin-Token: $token" "$url" 2>/dev/null || true)"
      [[ -n "$json" ]] || { echo "Payments request failed: $url" >&2; return 1; }

      BODY="$json" ORCH_ID="$orch_id" ORCH_ADDR="$orch_addr" python3 - <<'PY'
import json
import os
import sys

body = os.environ.get("BODY") or ""
orch_id = (os.environ.get("ORCH_ID") or "").strip()
orch_addr = (os.environ.get("ORCH_ADDR") or "").strip().lower()

try:
    data = json.loads(body)
except Exception as exc:
    print(f"payments: FAIL (invalid JSON: {exc})", file=sys.stderr)
    raise SystemExit(1)

def _items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("orchestrators"), list):
        return payload["orchestrators"]
    return []

items = _items(data)
match = None
for item in items:
    if not isinstance(item, dict):
        continue
    item_id = (item.get("orchestrator_id") or item.get("orchestratorId") or item.get("id") or "").strip()
    if item_id and item_id == orch_id:
        match = item
        break

if match is None:
    print(f"payments: NOT FOUND (orchestrator_id={orch_id})", file=sys.stderr)
    raise SystemExit(1)

addr = (match.get("address") or match.get("orchestrator_address") or match.get("orchestratorAddress") or "").strip()
balance = match.get("balance_eth") or match.get("balanceEth") or match.get("balance") or ""
elig = match.get("eligible") if "eligible" in match else ""
last_seen = match.get("last_seen") or match.get("lastSeen") or match.get("updated_at") or match.get("updatedAt") or ""

parts = [f"payments: OK (orchestrator_id={orch_id}"]
if addr:
    parts.append(f"address={addr}")
if balance != "":
    parts.append(f"balance={balance}")
if elig != "":
    parts.append(f"eligible={elig}")
if last_seen:
    parts.append(f"last_seen={last_seen}")
print(", ".join(parts) + ")")
PY
      ;;
    *)
      echo "Unknown payments command: $sub" >&2
      return 1
      ;;
  esac
}

cmd_allowlists() {
  init_ui
  local sub="${1:-status}"
  shift || true

  local override_payments_ip=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --payments-ip)
        override_payments_ip="${2:-}"
        shift 2
        ;;
      -h|--help|help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh allowlists [status|fix] [options]

Options:
  --payments-ip <ip>   Override PAYMENTS_API_URL host parsing (IPv4 only).
EOF
        return 0
        ;;
      *)
        echo "Unknown arg for allowlists: $1" >&2
        return 1
        ;;
    esac
  done

  if [[ ! -f "$ENV_FILE" ]]; then
    ui_check ".env" "FAIL" "(missing; run: ./scripts/embody_cli.sh setup)"
    return 1
  fi

  local payments_url payments_host payments_ip plane_url mode
  payments_url="$(get_payments_api_url)"
  payments_url="$(trim_whitespace "${payments_url:-}")"
  [[ -n "$payments_url" ]] || payments_url="${PAYMENTS_API_URL:-$DEFAULT_PAYMENTS_API_URL}"

  payments_host="$(extract_host_from_url "$payments_url")"
  payments_ip=""
  if [[ -n "$override_payments_ip" ]]; then
    payments_ip="$(trim_whitespace "$override_payments_ip")"
  elif [[ -n "$payments_host" ]] && is_ipv4 "$payments_host" >/dev/null 2>&1; then
    payments_ip="$payments_host"
  fi

  plane_url="$(get_edge_config_url)"
  mode="manual"
  if [[ -n "$plane_url" ]]; then
    mode="edge-plane"
  fi

  ui_title "Embody Orchestrator — Allowlists"
  ui_section "Config"
  ui_kv "mode" "$mode"
  ui_kv "payments url" "$payments_url"
  ui_kv "payments ip" "${payments_ip:-<unresolved>}"

  if [[ -z "$payments_ip" ]]; then
    ui_check "payments ip" "WARN" "(set PAYMENTS_API_URL to an IPv4 host or pass --payments-ip)"
    [[ "$sub" == "fix" ]] && return 1
  fi

  case "$sub" in
    ""|status)
      ui_section "Status"
      if [[ "$mode" == "edge-plane" ]]; then
        local want_cidr fw_extra power_extra local_allow
        want_cidr="${payments_ip}/32"
        fw_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_FIREWALL_EXTRA_CIDRS" 2>/dev/null || true)")"
        power_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_POWER_EXTRA_CIDRS" 2>/dev/null || true)")"
        local_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" 2>/dev/null || true)")"
        ui_kv "EDGE_FIREWALL_EXTRA_CIDRS" "${fw_extra:-<unset>}"
        ui_kv "EDGE_POWER_EXTRA_CIDRS" "${power_extra:-<unset>}"
        ui_kv "EDGE_LOCAL_ALLOWLIST" "${local_allow:-<unset>}"
        if [[ -n "$payments_ip" ]]; then
          [[ "$(csv_has_token "$fw_extra" "$want_cidr")" == "1" ]] && ui_check "payments fw" "OK" || ui_check "payments fw" "WARN" "(missing ${want_cidr})"
          [[ "$(csv_has_token "$power_extra" "$want_cidr")" == "1" ]] && ui_check "payments /power" "OK" || ui_check "payments /power" "WARN" "(missing ${want_cidr})"
          [[ "$(csv_has_token "$local_allow" "$payments_ip")" == "1" ]] && ui_check "payments runner/rec" "OK" || ui_check "payments runner/rec" "WARN" "(missing ${payments_ip})"
        fi
      else
        local allow_csv power_allow want_cidr
        allow_csv="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
        power_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "POWER_ALLOWED_IPS" 2>/dev/null || true)")"
        ui_kv "VTUBER_ALLOWED_ADDRESSES" "${allow_csv:-<unset>}"
        ui_kv "POWER_ALLOWED_IPS" "${power_allow:-<unset>}"
        if [[ -n "$payments_ip" ]]; then
          want_cidr="${payments_ip}/32"
          [[ "$(csv_has_token "$allow_csv" "$payments_ip")" == "1" ]] && ui_check "payments runner/rec" "OK" || ui_check "payments runner/rec" "WARN" "(missing ${payments_ip})"
          if [[ "$(csv_has_token "$power_allow" "$want_cidr")" == "1" || "$(csv_has_token "$power_allow" "$payments_ip")" == "1" ]]; then
            ui_check "payments /power" "OK"
          else
            ui_check "payments /power" "WARN" "(missing ${want_cidr})"
          fi
        fi
      fi
      return 0
      ;;
    fix)
      ui_section "Fix"
      [[ -n "$payments_ip" ]] || { ui_check "fix" "FAIL" "(payments IP unresolved)"; return 1; }

      local changed="0"
      if [[ "$mode" == "edge-plane" ]]; then
        local want_cidr fw_extra power_extra local_allow
        want_cidr="${payments_ip}/32"
        fw_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_FIREWALL_EXTRA_CIDRS" 2>/dev/null || true)")"
        power_extra="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_POWER_EXTRA_CIDRS" 2>/dev/null || true)")"
        local_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" 2>/dev/null || true)")"

        if [[ "$(csv_has_token "$fw_extra" "$want_cidr")" != "1" ]]; then
          fw_extra="$(csv_add_token "$fw_extra" "$want_cidr")"
          upsert_env_kv "$ENV_FILE" "EDGE_FIREWALL_EXTRA_CIDRS" "$fw_extra" || true
          changed="1"
        fi
        if [[ "$(csv_has_token "$power_extra" "$want_cidr")" != "1" ]]; then
          power_extra="$(csv_add_token "$power_extra" "$want_cidr")"
          upsert_env_kv "$ENV_FILE" "EDGE_POWER_EXTRA_CIDRS" "$power_extra" || true
          changed="1"
        fi
        if [[ -z "$local_allow" ]]; then
          local_allow="127.0.0.1,::1,172.17.0.1,172.18.0.1"
        fi
        if [[ "$(csv_has_token "$local_allow" "$payments_ip")" != "1" ]]; then
          local_allow="$(csv_add_token "$local_allow" "$payments_ip")"
          if ! upsert_env_kv "$ENV_FILE" "EDGE_LOCAL_ALLOWLIST" "$local_allow"; then
            ui_check "env" "FAIL" "(failed to update EDGE_LOCAL_ALLOWLIST)"
            return 1
          fi
          changed="1"
        fi

        if [[ "$changed" == "1" ]]; then
          ui_check "env" "OK" "(updated $ENV_FILE)"
          if command -v docker >/dev/null 2>&1; then
            ui_check "edge rotator" "WARN" "(restarting)"
            if docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
              up -d --force-recreate orchestrator-edge-rotator >/dev/null 2>&1; then
              ui_check "edge rotator" "OK"
            else
              ui_check "edge rotator" "FAIL" "(docker compose failed)"
              return 1
            fi
          else
            ui_check "docker" "WARN" "(docker missing; restart orchestrator-edge-rotator to apply)"
          fi
        else
          ui_check "fix" "OK" "(already configured)"
        fi
        return 0
      fi

      # manual mode
      local allow_csv power_allow want_cidr
      allow_csv="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
      power_allow="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "POWER_ALLOWED_IPS" 2>/dev/null || true)")"
      want_cidr="${payments_ip}/32"
      if [[ -z "$allow_csv" ]]; then
        allow_csv="127.0.0.1,::1,172.17.0.1,172.18.0.1"
      fi
      if [[ "$(csv_has_token "$allow_csv" "$payments_ip")" != "1" ]]; then
        allow_csv="$(csv_add_token "$allow_csv" "$payments_ip")"
        if ! upsert_env_kv "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" "$allow_csv"; then
          ui_check "env" "FAIL" "(failed to update VTUBER_ALLOWED_ADDRESSES)"
          return 1
        fi
        changed="1"
      fi
      if [[ -z "$power_allow" ]]; then
        power_allow="127.0.0.1/32,::1/128"
      fi
      if [[ "$(csv_has_token "$power_allow" "$want_cidr")" != "1" && "$(csv_has_token "$power_allow" "$payments_ip")" != "1" ]]; then
        power_allow="$(csv_add_token "$power_allow" "$want_cidr")"
        if ! upsert_env_kv "$ENV_FILE" "POWER_ALLOWED_IPS" "$power_allow"; then
          ui_check "env" "FAIL" "(failed to update POWER_ALLOWED_IPS)"
          return 1
        fi
        changed="1"
      fi

      if [[ "$changed" == "1" ]]; then
        ui_check "env" "OK" "(updated $ENV_FILE)"
        if command -v docker >/dev/null 2>&1; then
          ui_check "containers" "WARN" "(recreating orchestrator-health + runner/recorder)"
          if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
            up -d --force-recreate orchestrator-health >/dev/null 2>&1; then
            ui_check "containers" "FAIL" "(failed to recreate orchestrator-health)"
            return 1
          fi
          if docker inspect -f '{{.State.Status}}' vtuber-unreal-game >/dev/null 2>&1; then
            if [[ "$(docker inspect -f '{{.State.Status}}' vtuber-unreal-game 2>/dev/null || true)" == "running" ]]; then
              if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
                up -d --force-recreate vtuber-script-runner recorder-control >/dev/null 2>&1; then
                ui_check "containers" "FAIL" "(failed to recreate runner/recorder)"
                return 1
              fi
            else
              if ! docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
                up --no-start --force-recreate vtuber-script-runner recorder-control >/dev/null 2>&1; then
                ui_check "containers" "FAIL" "(failed to update runner/recorder)"
                return 1
              fi
            fi
          fi
          ui_check "containers" "OK"
        else
          ui_check "docker" "WARN" "(docker missing; restart containers to apply)"
        fi
      else
        ui_check "fix" "OK" "(already configured)"
      fi
      ;;
    *)
      echo "Unknown allowlists command: $sub" >&2
      return 1
      ;;
  esac
}

menu_start_stack() {
  local gpu_arg=()

  if command -v nvidia-smi >/dev/null 2>&1; then
    local gpu_list gpu_count
    gpu_list="$(nvidia-smi -L 2>/dev/null || true)"
    gpu_count="0"
    if [[ -n "$gpu_list" ]]; then
      gpu_count="$(printf '%s\n' "$gpu_list" | grep -c '^GPU ' || true)"
    fi
    if [[ "$gpu_count" -gt 1 ]]; then
      echo ""
      echo "Detected NVIDIA GPUs:"
      echo "$gpu_list"
      local current sel
      current="$(get_gpu_devices)"
      [[ -n "$current" ]] || current="all"
      echo -n "GPU selection (blank = use .env / ${current}): "
      read -r sel || true
      sel="$(trim_whitespace "${sel:-}")"
      if [[ -n "$sel" ]]; then
        gpu_arg=(--gpu "$sel")
      fi
    fi
  fi

  "$START_SCRIPT" start "${gpu_arg[@]}"
}

menu() {
  if ! has_setup_state; then
    run_setup
  fi

  ensure_registered_best_effort

  while true; do
    cmd_overview || true
    echo ""
    ui_menu_item "1" "Start stack"
    ui_menu_item "2" "Stop stack"
    ui_menu_item "3" "Restart stack"
    ui_menu_item "4" "Status"
    ui_menu_item "5" "Logs"
    ui_menu_item "6" "Health (quick)"
    ui_menu_item "7" "TCP test (runner → game)"
    ui_menu_item "8" "Config summary"
    ui_menu_item "9" "GPU capacity"
    ui_menu_item "c" "Cluster deploy (auto)"
    ui_menu_item "C" "Cluster status"
    ui_menu_item "x" "Cluster down"
    ui_menu_item "r" "Rollout game image"
    ui_menu_item "u" "Upgrade (pull/recreate containers)"
    ui_menu_item "v" "Verify (end-to-end)"
    ui_menu_item "m" "Payments status"
    ui_menu_item "p" "Power (sleep/wake)"
    ui_menu_item "s" "Setup / reconfigure"
    ui_menu_item "q" "Quit"
    printf '> '

    local choice
    read -r choice || exit 0
    case "$choice" in
      1) menu_start_stack ;;
      2) "$START_SCRIPT" stop ;;
      3) "$START_SCRIPT" restart ;;
      4) "$START_SCRIPT" status ;;
      5)
        echo -n "Service (blank for all): "
        local svc
        read -r svc || true
        "$START_SCRIPT" logs "$svc"
        ;;
      6) cmd_health || true ;;
      7) "$START_SCRIPT" test || true ;;
      8) cmd_config ;;
      9) cmd_capacity ;;
      c) cmd_cluster deploy --auto || true ;;
      C) cmd_cluster status || true ;;
      x) cmd_cluster down || true ;;
      r|R) cmd_rollout || true ;;
      u|U) cmd_upgrade || true ;;
      v|V) cmd_verify || true ;;
      m|M) cmd_payments status || true ;;
      p|P)
        echo -n "Power action (status|sleep|wake): "
        local act
        read -r act || true
        act="$(trim_whitespace "${act:-}")"
        [[ -n "$act" ]] || act="status"
        cmd_power "$act" || true
        ;;
      s|S) "$ONBOARD_SCRIPT" ;;
      q|Q) exit 0 ;;
      *) echo "Unknown option." ;;
    esac
  done
}

local_power_state() {
  command -v curl >/dev/null 2>&1 || return 1
  local body state
  body="$(curl -sS --max-time 2 http://127.0.0.1:9090/power 2>/dev/null || true)"
  [[ -n "$body" ]] || return 1
  state=""
  if command -v python3 >/dev/null 2>&1; then
    state="$(BODY="$body" python3 - <<'PY' || true
import json
import os
raw = os.environ.get("BODY") or ""
try:
    data = json.loads(raw)
except Exception:
    data = {}
print((data.get("state") or "").strip())
PY
    )"
  else
    case "$body" in
      *\"state\":\"sleeping\"*) state="sleeping" ;;
      *\"state\":\"awake\"*) state="awake" ;;
      *) state="" ;;
    esac
  fi
  state="$(trim_whitespace "${state:-}")"
  [[ -n "$state" ]] || return 1
  printf '%s' "$state"
}

maybe_auto_upgrade_when_sleeping() {
  local cmd="$1"
  if [[ -n "$cmd" ]]; then
    return 0
  fi
  if [[ "${EMBODY_CLI_AUTO_UPGRADE_WHEN_SLEEPING:-1}" == "0" || "${EMBODY_CLI_AUTO_UPGRADE_WHEN_SLEEPING:-}" == "false" ]]; then
    return 0
  fi
  if [[ "${EMBODY_CLI_AUTO_UPGRADE_DONE:-0}" == "1" ]]; then
    return 0
  fi
  if [[ "${EMBODY_CLI_AUTO_UPDATE_DONE:-0}" != "1" ]]; then
    return 0
  fi
  [[ -f "$ENV_FILE" ]] || return 0
  command -v docker >/dev/null 2>&1 || return 0
  docker info >/dev/null 2>&1 || return 0

  local pstate
  pstate="$(local_power_state 2>/dev/null || true)"
  if [[ "$pstate" != "sleeping" ]]; then
    return 0
  fi

  echo "cli: repo auto-updated and stack is sleeping; auto-upgrading containers (non-disruptive)..." >&2
  export EMBODY_CLI_AUTO_UPGRADE_DONE=1
  cmd_upgrade --yes || true
}

main() {
  init_ui

  auto_update_repo_or_reexec "$@"

  local cmd="${1:-}"

  maybe_auto_upgrade_when_sleeping "$cmd"

  case "$cmd" in
    -h|--help|help)
      usage
      exit 0
      ;;
  esac

  case "$cmd" in
    setup|onboard)
      shift
      run_setup "$@"
      ;;
    overview|dashboard)
      shift || true
      cmd_overview "$@"
      ;;
    update)
      echo "update: deprecated (CLI auto-updates on launch)" >&2
      ;;
    upgrade)
      shift || true
      cmd_upgrade "$@"
      ;;
    license|token)
      shift || true
      cmd_license "$@"
      ;;
    rollout|update-image)
      shift || true
      cmd_rollout "$@"
      ;;
    register)
      shift || true
      cmd_register "$@"
      ;;
    verify|doctor)
      shift || true
      cmd_verify "$@"
      ;;
    power)
      shift || true
      cmd_power "$@"
      ;;
    sleep|wake)
      shift || true
      cmd_power "$cmd" "$@"
      ;;
    start|up|stop|down|restart|logs|ps|status|pull|build|test)
      shift
      run_stack "$cmd" "$@"
      ;;
    health)
      cmd_health
      ;;
    config)
      cmd_config
      ;;
    cluster)
      shift || true
      cmd_cluster "$@"
      ;;
    capacity)
      cmd_capacity
      ;;
    payments)
      shift || true
      cmd_payments "$@"
      ;;
    allowlists|allowlist)
      shift || true
      cmd_allowlists "$@"
      ;;
    "")
      if setup_complete && is_tty; then
        menu
        return
      fi
      if ! has_setup_state; then
        run_setup
      fi
      if is_tty; then
        menu
        return
      fi
      usage
      exit 1
      ;;
    --*)
      # Treat unknown flags as onboarding args for convenience.
      run_setup "$@"
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
