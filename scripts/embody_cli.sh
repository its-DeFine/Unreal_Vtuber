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

usage() {
  cat <<'EOF'
Embody Orchestrator CLI

Usage:
  ./scripts/embody_cli.sh                  # Auto: setup wizard or day-to-day menu
  ./scripts/embody_cli.sh setup [args...]  # Run onboarding wizard

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
