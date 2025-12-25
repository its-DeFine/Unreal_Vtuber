#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${REPO_ROOT}/.env"
TURN_ENV_FILE="${REPO_ROOT}/.env.turn"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.unreal.yml"
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
DEFAULT_PAYMENTS_API_URL="http://3.141.111.200:8081"
DEFAULT_LICENSE_IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"

usage() {
  cat <<'EOF'
Embody Orchestrator CLI

Usage:
  ./scripts/embody_cli.sh                  # Auto: setup wizard or day-to-day menu
  ./scripts/embody_cli.sh setup [args...]  # Run onboarding wizard
  ./scripts/embody_cli.sh license          # Show license token status
  ./scripts/embody_cli.sh license redeem   # Redeem invite code → store token
  ./scripts/embody_cli.sh rollout          # Rollout encrypted game image (wraps tools/encrypted-game-image/rollout.sh)

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
  ./scripts/embody_cli.sh payments   # (placeholder)

Notes:
  - Onboarding is stored in `scripts/embody_onboard.sh` (called by `setup`).
  - License token default path: `~/.embody/orch-license-token.txt`
EOF
}

is_tty() {
  [[ -t 0 && -t 1 ]]
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
  local payments_url image_ref token_file
  local passthrough=()

  payments_url=""
  image_ref="$DEFAULT_LICENSE_IMAGE_REF"
  token_file="$TOKEN_FILE_DEFAULT"

  while [[ $# -gt 0 ]]; do
    case "$1" in
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

This wraps `tools/encrypted-game-image/rollout.sh` and uses your stored license token.

Options:
  --payments-api-url <url>   Payments backend (default: PAYMENTS_API_URL from .env)
  --image-ref <ref>          Image ref registered in Payments (default: ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1)
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

  if [[ ! -x "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" ]]; then
    echo "Missing rollout script: $REPO_ROOT/tools/encrypted-game-image/rollout.sh" >&2
    return 1
  fi

  "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" \
    --payments-api-url "$payments_url" \
    --orch-token-file "$token_file" \
    --image-ref "$image_ref" \
    "${passthrough[@]}"
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
  curl -fsS --max-time 2 http://127.0.0.1:8080/healthz 2>/dev/null && echo "signaling: OK" || echo "signaling: FAIL"
  curl -fsS --max-time 2 http://127.0.0.1:9877/health 2>/dev/null && echo "runner:    OK" || echo "runner:    FAIL"
  curl -fsS --max-time 2 http://127.0.0.1:9090/health 2>/dev/null && echo "orch:      OK" || echo "orch:      FAIL"

  if [[ -f "$ENV_FILE" ]]; then
    local edge_config_url allowlist nonlocal turn_external
    edge_config_url="$(get_edge_config_url)"
    if [[ -n "$edge_config_url" ]]; then
      allowlist="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
      nonlocal="$(extract_first_nonlocal_allowlist_token "$allowlist" || true)"
      turn_external="$(strip_inline_comment "$(read_env_value "$TURN_ENV_FILE" "TURN_EXTERNAL_IP" 2>/dev/null || true)")"
      if [[ -n "$nonlocal" ]]; then
        echo "edge-plane: OK (edge allowlisted: ${nonlocal})"
      else
        echo "edge-plane: WAITING (no edge IP allowlisted yet; check vtuber-orchestrator-edge-rotator logs)"
      fi
      if [[ -n "$turn_external" && -n "$nonlocal" ]] && [[ "$turn_external" != "$nonlocal" ]]; then
        echo "turn:      WARN (TURN_EXTERNAL_IP=${turn_external}; expected edge IP ${nonlocal} for DNAT setups)"
      fi
    fi
  fi
}

cmd_capacity() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi not found; cannot estimate GPU capacity." >&2
    return 1
  fi
  local raw
  raw="$(nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    echo "nvidia-smi returned no GPU info." >&2
    return 1
  fi
  echo "Estimated capacity (assuming ~8GB VRAM per UE instance):"
  echo "$raw" | while IFS=',' read -r idx name mem; do
    idx="$(trim_whitespace "$idx")"
    name="$(trim_whitespace "$name")"
    mem="$(trim_whitespace "$mem")"
    if [[ "$mem" =~ ^[0-9]+$ ]]; then
      local instances=$(( mem / 8192 ))
      echo "  GPU ${idx} (${name}): ${mem} MiB -> ~${instances} instance(s)"
    else
      echo "  GPU ${idx} (${name}): ${mem}"
    fi
  done
}

cmd_payments() {
  echo "Payments view is not wired into the orchestrator CLI yet."
  echo "Planned: show balance/eligibility once the Payments revamp exposes safe per-orchestrator endpoints."
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

  while true; do
    echo ""
    echo "Embody Orchestrator — day-to-day"
    echo "  1) Start stack"
    echo "  2) Stop stack"
    echo "  3) Restart stack"
    echo "  4) Status"
    echo "  5) Logs"
    echo "  6) Health checks"
    echo "  7) Sample test"
    echo "  8) Config summary"
    echo "  9) GPU capacity"
    echo "  s) Setup / reconfigure"
    echo "  q) Quit"
    echo -n "> "

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
      6) cmd_health ;;
      7) "$START_SCRIPT" test ;;
      8) cmd_config ;;
      9) cmd_capacity ;;
      s|S) "$ONBOARD_SCRIPT" ;;
      q|Q) exit 0 ;;
      *) echo "Unknown option." ;;
    esac
  done
}

main() {
  local cmd="${1:-}"

  case "$cmd" in
    -h|--help|help)
      usage
      exit 0
      ;;
    setup|onboard)
      shift
      run_setup "$@"
      ;;
    license|token)
      shift || true
      cmd_license "$@"
      ;;
    rollout|update-image)
      shift || true
      cmd_rollout "$@"
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
    capacity)
      cmd_capacity
      ;;
    payments)
      cmd_payments
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
