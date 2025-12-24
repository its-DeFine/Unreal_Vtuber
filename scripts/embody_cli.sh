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
  ./scripts/embody_cli.sh verify           # Verify services + edge routing + firewall
  ./scripts/embody_cli.sh register         # Re-register with Payments
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

docker_container_status() {
  local name="$1"
  docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null
}

docker_container_health() {
  local name="$1"
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$name" 2>/dev/null
}

iptables_cmd() {
  if [[ "$(id -u)" == "0" ]]; then
    iptables "$@"
    return $?
  fi
  if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo -n iptables "$@"
    return $?
  fi
  return 126
}

cmd_register() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing .env at $ENV_FILE" >&2
    return 1
  fi
  docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
    -e ORCHESTRATOR_REGISTRATION_DELAY=0 \
    orchestrator-registration
}

cmd_verify() {
  local failures=0
  local power_state="unknown"

  vok() { echo "[OK] $*"; }
  vwarn() { echo "[WARN] $*" >&2; }
  vfail() { echo "[FAIL] $*" >&2; failures=$((failures + 1)); }
  vinfo() { echo "[INFO] $*"; }

  vinfo "Verifying orchestrator host"

  if [[ ! -f "$COMPOSE_FILE" ]]; then
    vfail "Missing compose file: $COMPOSE_FILE"
  else
    vok "Compose file present"
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    vfail "Missing .env: $ENV_FILE"
  else
    vok ".env present"
  fi

  local orch_id orch_addr
  orch_id="$(get_orchestrator_id)"
  orch_addr="$(get_orchestrator_address)"
  if [[ -n "$orch_id" ]]; then
    vok "ORCHESTRATOR_ID=$orch_id"
  else
    vfail "ORCHESTRATOR_ID is unset in .env"
  fi
  if [[ -n "$orch_addr" ]]; then
    vok "ORCHESTRATOR_ADDRESS set"
  else
    vwarn "ORCHESTRATOR_ADDRESS is unset in .env (payouts/registration may fail)"
  fi

  local token_path="${TOKEN_FILE_DEFAULT}"
  if [[ -s "$token_path" ]]; then
    vok "License token present (${token_path})"
  else
    vwarn "License token missing (${token_path})"
  fi

  if [[ -s "$TURN_ENV_FILE" ]]; then
    vok "TURN env present (${TURN_ENV_FILE})"
  else
    vwarn "TURN env missing (${TURN_ENV_FILE})"
  fi

  local power_json power_state_raw
  power_json="$(curl -fsS --max-time 2 http://127.0.0.1:9090/power 2>/dev/null || true)"
  power_state_raw=""
  if [[ -n "$power_json" ]]; then
    if command -v python3 >/dev/null 2>&1; then
      power_state_raw="$(printf '%s' "$power_json" | python3 - <<'PY'
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
state = data.get("state")
if isinstance(state, str):
    print(state)
PY
      )"
    else
      power_state_raw="$(printf '%s' "$power_json" | sed -n 's/.*"state"[[:space:]]*:[[:space:]]*"\\([^"]\\+\\)".*/\\1/p' | head -n1)"
    fi
  fi
  if [[ -n "${power_state_raw:-}" ]]; then
    power_state="$power_state_raw"
    vok "Power state: $power_state"
  else
    vwarn "Power state: unknown (power API not reachable or unparsable)"
  fi

  vinfo "Container status"

  if ! command -v docker >/dev/null 2>&1; then
    vfail "docker not found"
  else
    local required_running=()
    local optional_running=()

    required_running+=(vtuber-orchestrator-health)

    local edge_config_url
    edge_config_url="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_CONFIG_URL" 2>/dev/null || true)")"
    if [[ -n "$edge_config_url" ]]; then
      optional_running+=(vtuber-orchestrator-edge-rotator)
    fi

    if [[ "$power_state" != "sleeping" ]]; then
      required_running+=(
        vtuber-turn-server
        vtuber-unreal-signaling
        vtuber-unreal-game
        vtuber-script-runner
        vtuber-recorder-control
        vtuber-watchdog
        vtuber-auto-updater
      )
    fi

    local c status health
    for c in "${required_running[@]}"; do
      status="$(docker_container_status "$c" || true)"
      if [[ -z "$status" ]]; then
        vfail "Missing container: $c"
        continue
      fi
      if [[ "$status" != "running" ]]; then
        vfail "Container not running: $c ($status)"
        continue
      fi
      health="$(docker_container_health "$c" || true)"
      if [[ -n "$health" && "$health" != "healthy" ]]; then
        vwarn "Container health: $c ($health)"
      else
        vok "Container running: $c"
      fi
    done

    for c in "${optional_running[@]}"; do
      status="$(docker_container_status "$c" || true)"
      if [[ -z "$status" ]]; then
        vwarn "Optional container missing: $c"
        continue
      fi
      if [[ "$status" != "running" ]]; then
        vwarn "Optional container not running: $c ($status)"
        continue
      fi
      vok "Optional container running: $c"
    done

    local reg_status
    reg_status="$(docker_container_status "vtuber-orchestrator-registration" || true)"
    if [[ -n "$reg_status" ]]; then
      if [[ "$reg_status" == "exited" || "$reg_status" == "created" ]]; then
        vok "Registration container state: vtuber-orchestrator-registration ($reg_status)"
      else
        vwarn "Registration container state: vtuber-orchestrator-registration ($reg_status)"
      fi
    fi
  fi

  vinfo "Local health endpoints"
  if [[ "$power_state" == "sleeping" ]]; then
    vwarn "Skipping signaling/game health checks while sleeping"
  else
    curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 && vok "signaling OK (127.0.0.1:8080/healthz)" || vfail "signaling FAIL (127.0.0.1:8080/healthz)"
    curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 && vok "runner OK (127.0.0.1:9877/health)" || vfail "runner FAIL (127.0.0.1:9877/health)"
  fi
  curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 && vok "orchestrator-health OK (127.0.0.1:9090/health)" || vfail "orchestrator-health FAIL (127.0.0.1:9090/health)"

  local edge_config_token assignment edge_id mm_host mm_port edge_cidrs
  edge_id=""
  mm_host=""
  mm_port=""
  edge_cidrs=""

  edge_config_token="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_CONFIG_TOKEN" 2>/dev/null || true)")"

  if [[ -n "${edge_config_url:-}" ]]; then
    vinfo "Edge config control plane"
    if ! command -v python3 >/dev/null 2>&1; then
      vfail "python3 required to verify EDGE_CONFIG_URL connectivity (install python3)"
    else
      assignment="$(
        EDGE_CONFIG_URL="$edge_config_url" EDGE_CONFIG_TOKEN="$edge_config_token" ORCHESTRATOR_ID="$orch_id" \
          python3 - <<'PY' 2>/dev/null || true
import json
import os
import socket
import sys
import urllib.parse
import urllib.request

url = (os.environ.get("EDGE_CONFIG_URL") or "").strip()
token = (os.environ.get("EDGE_CONFIG_TOKEN") or "").strip()
orch = (os.environ.get("ORCHESTRATOR_ID") or "").strip()
if not url or not orch:
    sys.exit(1)

q = urllib.parse.urlencode({"orchestrator_id": orch})
full = f"{url}{'&' if '?' in url else '?'}{q}"
headers = {"Accept": "application/json"}
if token:
    headers["Authorization"] = f"Bearer {token}"
req = urllib.request.Request(full, headers=headers, method="GET")
with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
    data = resp.read().decode("utf-8")
payload = json.loads(data)
if not isinstance(payload, dict):
    sys.exit(1)

def _get_str(key: str) -> str:
    v = payload.get(key)
    return v.strip() if isinstance(v, str) else ""

edge_id = _get_str("edge_id")
mm_host = _get_str("matchmaker_host") or _get_str("matchmaker_address")
mm_port = payload.get("matchmaker_port")
mm_port_out = str(mm_port) if isinstance(mm_port, int) else ""

cidrs: list[str] = []
raw = payload.get("edge_cidrs")
if isinstance(raw, list):
    for item in raw:
        if isinstance(item, str) and item.strip():
            cidrs.append(item.strip())
raw_ip = _get_str("edge_ip")
if raw_ip:
    cidrs.append(f"{raw_ip}/32")
raw_ips = payload.get("edge_ips")
if isinstance(raw_ips, list):
    for item in raw_ips:
        if isinstance(item, str) and item.strip():
            cidrs.append(f"{item.strip()}/32")
edge_host = _get_str("edge_host")
if edge_host:
    try:
        infos = socket.getaddrinfo(edge_host, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
        for info in infos:
            addr = info[4][0]
            if addr:
                cidrs.append(f"{addr}/32")
    except Exception:
        pass

seen: set[str] = set()
deduped: list[str] = []
for c in cidrs:
    if c in seen:
        continue
    seen.add(c)
    deduped.append(c)

print(f"edge_id={edge_id}")
print(f"matchmaker_host={mm_host}")
print(f"matchmaker_port={mm_port_out}")
print("edge_cidrs=" + ",".join(deduped))
PY
      )"

      if [[ -z "$assignment" ]]; then
        vfail "Failed to fetch edge assignment from EDGE_CONFIG_URL"
      else
        while IFS='=' read -r k v; do
          case "$k" in
            edge_id) edge_id="$v" ;;
            matchmaker_host) mm_host="$v" ;;
            matchmaker_port) mm_port="$v" ;;
            edge_cidrs) edge_cidrs="$v" ;;
          esac
        done <<<"$assignment"

        vok "Edge assignment fetched (edge_id=${edge_id:-<unset>}, matchmaker=${mm_host:-<unset>}:${mm_port:-<unset>})"
        if [[ -n "$edge_cidrs" ]]; then
          vok "Edge CIDRs: $edge_cidrs"
        else
          vwarn "Edge CIDRs not returned by control plane (edge gating may be incorrect)"
        fi
      fi
    fi
  else
    vwarn "EDGE_CONFIG_URL is unset; skipping edge-rotation checks"
  fi

  vinfo "Signaling matchmaker configuration"
  local signaling_args mm_env_host mm_env_port
  signaling_args="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "SIGNALING_EXTRA_ARGS" 2>/dev/null || true)")"
  signaling_args="$signaling_args $(strip_inline_comment "$(read_env_value "$ENV_FILE" "SIGNALING_MATCHMAKER_ARGS" 2>/dev/null || true)")"
  mm_env_host="$(printf '%s' "$signaling_args" | sed -n 's/.*--matchmaker_address[[:space:]]\\([^[:space:]]\\+\\).*/\\1/p' | tail -n1)"
  mm_env_port="$(printf '%s' "$signaling_args" | sed -n 's/.*--matchmaker_port[[:space:]]\\([0-9]\\+\\).*/\\1/p' | tail -n1)"

  if [[ -n "$mm_env_host" ]]; then
    vok "Matchmaker configured in .env: ${mm_env_host}:${mm_env_port:-<default>}"
    if [[ -n "$mm_host" && "$mm_host" != "$mm_env_host" ]]; then
      vwarn "Control plane matchmaker_host differs from .env (plane=$mm_host env=$mm_env_host)"
    fi
    if [[ -n "$mm_port" && -n "$mm_env_port" && "$mm_port" != "$mm_env_port" ]]; then
      vwarn "Control plane matchmaker_port differs from .env (plane=$mm_port env=$mm_env_port)"
    fi
  else
    if [[ -n "${edge_config_url:-}" ]]; then
      vfail "Matchmaker is not configured in .env (expected --use_matchmaker ... --matchmaker_address ...)"
    else
      vwarn "Matchmaker not configured (single-edge setups may be OK)"
    fi
  fi

  if [[ -n "$mm_env_host" ]]; then
    vinfo "Edge matchmaker status"
    local status_url status_json
    status_url="https://${mm_env_host}/api/status"
    status_json="$(curl -fsS --max-time 5 "$status_url" 2>/dev/null || true)"
    if [[ -z "$status_json" ]]; then
      status_url="http://${mm_env_host}/api/status"
      status_json="$(curl -fsS --max-time 5 "$status_url" 2>/dev/null || true)"
    fi
    if [[ -z "$status_json" ]]; then
      vfail "Unable to fetch edge /api/status from ${mm_env_host}"
    else
      if command -v python3 >/dev/null 2>&1; then
        printf '%s' "$status_json" | python3 - <<'PY' || true
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("[WARN] edge /api/status returned non-JSON")
    sys.exit(0)
servers = data.get("servers") if isinstance(data, dict) else None
if not isinstance(servers, list):
    print("[WARN] edge /api/status missing servers[]")
    sys.exit(0)
print(f"[OK] edge reports {len(servers)} server(s)")
for s in servers[:5]:
    if not isinstance(s, dict):
        continue
    addr = s.get("address")
    port = s.get("port")
    ready = s.get("ready")
    clients = s.get("numConnectedClients")
    print(f"[INFO] - {addr}:{port} ready={ready} clients={clients}")
PY
      else
        vok "Fetched edge /api/status (${status_url})"
      fi
    fi
  fi

  if [[ -n "${edge_config_url:-}" && -n "$edge_cidrs" ]]; then
    vinfo "Firewall allowlist (iptables)"

    local chain
    chain="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_IPTABLES_CHAIN" 2>/dev/null || true)")"
    [[ -n "$chain" ]] || chain="EMBODY_EDGE_ALLOWLIST"

    if ! iptables_cmd -S "$chain" >/dev/null 2>&1; then
      if [[ $? -eq 126 ]]; then
        vwarn "iptables verify requires root; re-run as root or with passwordless sudo"
      else
        vfail "iptables chain missing: $chain"
      fi
    else
      vok "iptables chain present: $chain"

      if iptables_cmd -S INPUT 2>/dev/null | grep -q -- "-j ${chain}"; then
        vok "INPUT jumps to ${chain}"
      else
        vfail "INPUT missing jump to ${chain}"
      fi

      if iptables_cmd -S DOCKER-USER 2>/dev/null | grep -q -- "-j ${chain}"; then
        vok "DOCKER-USER jumps to ${chain}"
      else
        vfail "DOCKER-USER missing jump to ${chain}"
      fi

      local first_cidr
      first_cidr="$(printf '%s' "$edge_cidrs" | awk -F',' '{print $1}')"
      if [[ -n "$first_cidr" ]] && iptables_cmd -S "$chain" 2>/dev/null | grep -q -- "-s ${first_cidr}"; then
        vok "Allowlist contains ${first_cidr}"
      else
        vwarn "Allowlist does not contain expected edge CIDR (${first_cidr}); waiting for rotator?"
      fi
    fi

    local power_allowed_file
    power_allowed_file="$(strip_inline_comment "$(read_env_value "$ENV_FILE" "EDGE_POWER_ALLOWED_IPS_FILE" 2>/dev/null || true)")"
    [[ -n "$power_allowed_file" ]] || power_allowed_file="/var/lib/vtuber/power-state/power_allowed_ips.txt"
    if [[ -f "$power_allowed_file" ]]; then
      vok "Power allowlist file present (${power_allowed_file})"
    else
      vwarn "Power allowlist file missing (${power_allowed_file})"
    fi
  fi

  if [[ "$failures" -eq 0 ]]; then
    vok "Verify complete"
    return 0
  fi
  vfail "Verify failed (${failures} issue(s))"
  return 1
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
    echo "  7) Verify (services + edge routing)"
    echo "  8) Sample test"
    echo "  9) Config summary"
    echo "  10) GPU capacity"
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
      7) cmd_verify ;;
      8) "$START_SCRIPT" test ;;
      9) cmd_config ;;
      10) cmd_capacity ;;
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
    verify)
      cmd_verify
      ;;
    register)
      cmd_register
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
