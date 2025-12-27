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
PAYMENTS_VIEWER_TOKEN_FILE_DEFAULT="${TARGET_HOME}/.embody/payments-viewer-token.txt"
REGISTRATION_STATE_FILE_DEFAULT="${TARGET_HOME}/.embody/orchestrator-registration.json"
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
  ./scripts/embody_cli.sh register         # Register orchestrator in Payments (cached; skip when already registered)
  ./scripts/embody_cli.sh verify           # Full health/consistency checks (optionally auto-fix)
  ./scripts/embody_cli.sh power            # Sleep/wake via orchestrator-health /power

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

read_file_trim() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  local value
  value="$(tr -d '\n' < "$path" 2>/dev/null || true)"
  value="$(trim_whitespace "${value:-}")"
  printf '%s' "$value"
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
  ./scripts/embody_cli.sh power sleep
  ./scripts/embody_cli.sh power wake [--ttl <seconds>]
EOF
      return 0
      ;;
    ""|status)
      curl -fsS --max-time 2 http://127.0.0.1:9090/power
      echo ""
      ;;
    sleep)
      curl -fsS --max-time 5 -X POST http://127.0.0.1:9090/power \
        -H "Content-Type: application/json" \
        -d '{"action":"sleep","reason":"cli"}'
      echo ""
      ;;
    wake)
      local ttl=""
      while [[ $# -gt 0 ]]; do
        case "$1" in
          --ttl)
            ttl="${2:-}"
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
      curl -fsS --max-time 10 -X POST http://127.0.0.1:9090/power \
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

cmd_verify() {
  local fix="0"
  local with_payments="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fix)
        fix="1"
        shift 1
        ;;
      --payments)
        with_payments="1"
        shift 1
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh verify [options]

Options:
  --fix        Attempt to fix common drift (recreate runner+recorder if allowlist env is stale)
  --payments   Also verify Payments registration/balance (requires viewer/admin token)
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

  if [[ ! -f "$ENV_FILE" ]]; then
    echo ".env missing at $ENV_FILE (run ./scripts/embody_cli.sh setup)" >&2
    return 1
  fi

  command -v docker >/dev/null 2>&1 || { echo "docker not found" >&2; return 1; }
  if ! docker info >/dev/null 2>&1; then
    echo "docker daemon not reachable (try sudo or add user to docker group)" >&2
    return 1
  fi

  echo "== Containers =="
  local required=(
    vtuber-unreal-game
    vtuber-unreal-signaling
    vtuber-script-runner
    vtuber-recorder-control
    vtuber-orchestrator-health
  )
  local c status
  for c in "${required[@]}"; do
    if ! docker inspect "$c" >/dev/null 2>&1; then
      echo "${c}: MISSING"
      ok="0"
      continue
    fi
    status="$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || true)"
    if [[ "$status" == "running" ]]; then
      echo "${c}: running"
    else
      echo "${c}: ${status:-unknown}"
      ok="0"
    fi
  done

  echo ""
  echo "== Endpoints =="
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 && echo "signaling: OK" || { echo "signaling: FAIL"; ok="0"; }
    curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 && echo "runner:    OK" || { echo "runner:    FAIL"; ok="0"; }
    curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 && echo "orch:      OK" || { echo "orch:      FAIL"; ok="0"; }
  else
    echo "curl missing; cannot run HTTP health checks"
    ok="0"
  fi

  echo ""
  echo "== Allowlist Consistency =="
  local allow_env allow_runner allow_recorder
  allow_env="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null || true)")"
  allow_runner="$(container_env_value vtuber-script-runner VTUBER_ALLOWED_ADDRESSES || true)"
  allow_recorder="$(container_env_value vtuber-recorder-control VTUBER_ALLOWED_ADDRESSES || true)"

  echo "env:     ${allow_env:-<unset>}"
  echo "runner:  ${allow_runner:-<unset>}"
  echo "recorder:${allow_recorder:-<unset>}"

  if [[ -n "$allow_env" ]] && { [[ "$allow_env" != "$allow_runner" ]] || [[ "$allow_env" != "$allow_recorder" ]]; }; then
    echo "allowlist: DRIFT (containers not running with current VTUBER_ALLOWED_ADDRESSES)"
    allowlist_ok="0"
    if [[ "$fix" == "1" ]]; then
      echo "fix: recreating runner+recorder to reload .env"
      docker compose --project-directory "$REPO_ROOT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
        up -d --force-recreate vtuber-script-runner recorder-control
      allow_runner="$(container_env_value vtuber-script-runner VTUBER_ALLOWED_ADDRESSES || true)"
      allow_recorder="$(container_env_value vtuber-recorder-control VTUBER_ALLOWED_ADDRESSES || true)"
      if [[ "$allow_env" == "$allow_runner" && "$allow_env" == "$allow_recorder" ]]; then
        echo "allowlist: OK (fixed)"
        allowlist_ok="1"
      else
        echo "allowlist: still drifted after recreate"
      fi
    fi
  else
    echo "allowlist: OK"
  fi

  if [[ "$with_payments" == "1" ]]; then
    echo ""
    echo "== Payments =="
    if ! cmd_payments status; then
      ok="0"
    fi
  fi

  [[ "$ok" == "1" && "$allowlist_ok" == "1" ]]
}

cmd_payments() {
  local sub="${1:-}"
  shift || true

  case "$sub" in
    -h|--help|help)
      cat <<'EOF'
Usage:
  ./scripts/embody_cli.sh payments token
  ./scripts/embody_cli.sh payments token set
  ./scripts/embody_cli.sh payments status

Notes:
  - Token precedence: PAYMENTS_VIEWER_TOKEN env, PAYMENTS_ADMIN_TOKEN env, then ~/.embody/payments-viewer-token.txt
  - Payments status uses `X-Admin-Token` (viewer/admin token) to call `/api/orchestrators`.
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
    ""|status|verify)
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
    echo "  v) Verify (full)"
    echo "  m) Payments status"
    echo "  p) Power (sleep/wake)"
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
      v|V) cmd_verify ;;
      m|M) cmd_payments status ;;
      p|P)
        echo -n "Power action (status|sleep|wake): "
        local act
        read -r act || true
        act="$(trim_whitespace "${act:-}")"
        [[ -n "$act" ]] || act="status"
        cmd_power "$act"
        ;;
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
    capacity)
      cmd_capacity
      ;;
    payments)
      shift || true
      cmd_payments "$@"
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
