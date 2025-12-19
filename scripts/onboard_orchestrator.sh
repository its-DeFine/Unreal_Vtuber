#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
One-command orchestrator onboarding (encrypted game image flow).

Usage:
  ./scripts/onboard_orchestrator.sh \
    --orchestrator-id <id> \
    --orchestrator-address <0x...> \
    --artifact-url <https://...tar.zst.age> \
    (--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>)

Common options:
  --payments-api-url <url>    (default: http://3.141.111.200:8081)
  --image-ref <ref>           (default: ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1)
  --forwarder-ip <ip>         (default: 3.150.172.153)
  --public-ip <ip|auto>       (default: auto; tries EC2 IMDSv2 then ipify)

Host paths (written into .env):
  --session-dir <path>        (default: <target-home>/vtuber_sessions)
  --recordings-dir <path>     (default: <target-home>/recordings)

Behavior flags:
  --install-deps              Attempt apt-get install of curl/jq/zstd/age (Ubuntu/Debian only)
  --rotate-turn               Regenerate .env.turn even if present
  --no-pull                   Skip docker compose pull
  --skip-rollout              Skip encrypted image rollout; just docker compose up -d
  --skip-registration         Skip running orchestrator-registration
  --no-verify                 Skip rollout health checks
  --force-env                 Overwrite .env (otherwise upsert keys)

Examples:
  # Recommended: store the license token in a file (admin provides it)
  mkdir -p ~/.embody && chmod 700 ~/.embody
  printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt && chmod 600 ~/.embody/orch-license-token.txt

  git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && \
    ./scripts/onboard_orchestrator.sh \
      --orchestrator-id orch-123 \
      --orchestrator-address 0x0000000000000000000000000000000000000000 \
      --artifact-url "https://example.com/embody-ue-ps.tar.zst.age" \
      --orch-token-file ~/.embody/orch-license-token.txt
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

note() {
  echo "[onboard] $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="$REPO_ROOT/.env"
TURN_ENV_FILE="$REPO_ROOT/.env.turn"
COMPOSE_FILE="$REPO_ROOT/docker-compose.unreal.yml"

PAYMENTS_API_URL="http://3.141.111.200:8081"
IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"
FORWARDER_IP="3.150.172.153"
PUBLIC_IP="auto"

ORCH_ID=""
ORCH_ADDRESS=""
ARTIFACT_URL=""
ORCH_TOKEN=""
ORCH_TOKEN_FILE=""
ORCH_TOKEN_ENV=""

SESSION_DIR=""
RECORDINGS_DIR=""

INSTALL_DEPS="0"
ROTATE_TURN="0"
NO_PULL="0"
SKIP_ROLLOUT="0"
SKIP_REGISTRATION="0"
NO_VERIFY="0"
FORCE_ENV="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --payments-api-url)
      PAYMENTS_API_URL="${2:-}"
      shift 2
      ;;
    --image-ref)
      IMAGE_REF="${2:-}"
      shift 2
      ;;
    --forwarder-ip)
      FORWARDER_IP="${2:-}"
      shift 2
      ;;
    --public-ip)
      PUBLIC_IP="${2:-}"
      shift 2
      ;;
    --orchestrator-id)
      ORCH_ID="${2:-}"
      shift 2
      ;;
    --orchestrator-address)
      ORCH_ADDRESS="${2:-}"
      shift 2
      ;;
    --artifact-url)
      ARTIFACT_URL="${2:-}"
      shift 2
      ;;
    --orch-token)
      ORCH_TOKEN="${2:-}"
      shift 2
      ;;
    --orch-token-file)
      ORCH_TOKEN_FILE="${2:-}"
      shift 2
      ;;
    --orch-token-env)
      ORCH_TOKEN_ENV="${2:-}"
      shift 2
      ;;
    --session-dir)
      SESSION_DIR="${2:-}"
      shift 2
      ;;
    --recordings-dir)
      RECORDINGS_DIR="${2:-}"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS="1"
      shift 1
      ;;
    --rotate-turn)
      ROTATE_TURN="1"
      shift 1
      ;;
    --no-pull)
      NO_PULL="1"
      shift 1
      ;;
    --skip-rollout)
      SKIP_ROLLOUT="1"
      shift 1
      ;;
    --skip-registration)
      SKIP_REGISTRATION="1"
      shift 1
      ;;
    --no-verify)
      NO_VERIFY="1"
      shift 1
      ;;
    --force-env)
      FORCE_ENV="1"
      shift 1
      ;;
    *)
      die "unknown arg: $1 (run with --help)"
      ;;
  esac
done

[[ -n "$ORCH_ID" ]] || die "--orchestrator-id is required"
[[ -n "$ORCH_ADDRESS" ]] || die "--orchestrator-address is required"

if [[ "$SKIP_ROLLOUT" != "1" ]]; then
  [[ -n "$ARTIFACT_URL" ]] || die "--artifact-url is required unless --skip-rollout is set"
  if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
    die "orchestrator token required (use --orch-token-file or --orch-token-env)"
  fi
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  die "compose file not found: $COMPOSE_FILE (are you in the repo?)"
fi

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  die "missing dependency: docker compose (or docker-compose)"
fi

target_user="${SUDO_USER:-$USER}"
target_home=""
if command -v getent >/dev/null 2>&1; then
  target_home="$(getent passwd "$target_user" | cut -d: -f6 || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$(eval echo "~${target_user}" 2>/dev/null || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$HOME"
fi

if [[ -z "$SESSION_DIR" ]]; then
  SESSION_DIR="$target_home/vtuber_sessions"
fi
if [[ -z "$RECORDINGS_DIR" ]]; then
  RECORDINGS_DIR="$target_home/recordings"
fi

install_deps_if_requested() {
  if [[ "$INSTALL_DEPS" != "1" ]]; then
    return
  fi
  if [[ "$(id -u)" != "0" ]]; then
    die "--install-deps requires root (re-run with sudo)"
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    die "--install-deps only supports apt-get (Ubuntu/Debian)"
  fi
  note "Installing host deps (curl jq zstd age)…"
  apt-get update -y
  apt-get install -y curl jq zstd age
}

detect_public_ip() {
  local token ip
  token="$(curl -fsS --max-time 2 -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    ip="$(curl -fsS --max-time 2 -H "X-aws-ec2-metadata-token: $token" \
      "http://169.254.169.254/latest/meta-data/public-ipv4" 2>/dev/null || true)"
  else
    ip="$(curl -fsS --max-time 2 "http://169.254.169.254/latest/meta-data/public-ipv4" 2>/dev/null || true)"
  fi
  if [[ -n "${ip:-}" ]]; then
    echo "$ip"
    return 0
  fi
  curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null || true
}

upsert_env_kv() {
  local file="$1" key="$2" value="$3"
  local tmp
  tmp="$(mktemp)"

  if [[ ! -f "$file" ]]; then
    cat >"$file" <<EOF_ENV
# Generated by scripts/onboard_orchestrator.sh
# Safe to edit; rerun with --force-env to regenerate.
EOF_ENV
  fi

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

write_token_file_if_needed() {
  if [[ -n "$ORCH_TOKEN_FILE" || -n "$ORCH_TOKEN_ENV" ]]; then
    return
  fi
  if [[ -z "$ORCH_TOKEN" ]]; then
    return
  fi

  local token_dir token_file
  token_dir="$target_home/.embody"
  token_file="$token_dir/orch-license-token.txt"

  note "Writing orchestrator token to $token_file"
  mkdir -p "$token_dir"
  chmod 700 "$token_dir" || true
  printf '%s' "$ORCH_TOKEN" >"$token_file"
  chmod 600 "$token_file" || true
  if [[ "$(id -u)" == "0" && -n "$SUDO_USER" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$token_dir" "$token_file" || true
  fi
  ORCH_TOKEN_FILE="$token_file"
  ORCH_TOKEN=""
}

install_deps_if_requested

require_cmd docker
require_cmd curl

if ! docker info >/dev/null 2>&1; then
  die "docker daemon not reachable (try running with sudo, or add your user to the docker group)"
fi

if [[ "$PUBLIC_IP" == "auto" ]]; then
  note "Detecting public IP…"
  PUBLIC_IP="$(detect_public_ip || true)"
  [[ -n "$PUBLIC_IP" ]] || die "could not detect public IP; pass --public-ip <ip>"
fi

note "Using PUBLIC_IP=$PUBLIC_IP"
note "Using PAYMENTS_API_URL=$PAYMENTS_API_URL"

write_token_file_if_needed

if [[ "$FORCE_ENV" == "1" ]]; then
  note "Regenerating $ENV_FILE"
  rm -f "$ENV_FILE"
fi

upsert_env_kv "$ENV_FILE" "PAYMENTS_API_URL" "$PAYMENTS_API_URL"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_ID" "$ORCH_ID"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_ADDRESS" "$ORCH_ADDRESS"
upsert_env_kv "$ENV_FILE" "PUBLIC_IP" "$PUBLIC_IP"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_HOST_PUBLIC_IP" "$PUBLIC_IP"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_HEALTH_URL" "http://$PUBLIC_IP:9090/health"
upsert_env_kv "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" "127.0.0.1,::1,$FORWARDER_IP"
upsert_env_kv "$ENV_FILE" "VTUBER_SESSION_DIR" "$SESSION_DIR"
upsert_env_kv "$ENV_FILE" "VTUBER_RECORDINGS_DIR" "$RECORDINGS_DIR"

chmod 600 "$ENV_FILE" >/dev/null 2>&1 || true

note "Ensuring host directories exist"
mkdir -p "$SESSION_DIR" "$RECORDINGS_DIR"
if [[ "$(id -u)" == "0" && -n "$SUDO_USER" ]]; then
  chown "$SUDO_USER":"$SUDO_USER" "$SESSION_DIR" "$RECORDINGS_DIR" || true
fi

note "Ensuring vtuber_network exists"
docker network create vtuber_network 2>/dev/null || true

if [[ "$ROTATE_TURN" == "1" || ! -s "$TURN_ENV_FILE" ]]; then
  note "Generating TURN credentials (.env.turn)"
  (cd "$REPO_ROOT" && PUBLIC_IP="$PUBLIC_IP" ./scripts/generate_turn_credentials.sh)
else
  note "Keeping existing $TURN_ENV_FILE (use --rotate-turn to regenerate)"
fi

if [[ "$NO_PULL" != "1" ]]; then
  note "Pulling service images"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" pull \
    turn-server unreal-signaling \
    vtuber-script-runner vtuber-watchdog \
    orchestrator-registration orchestrator-health \
    vtuber-auto-updater recorder-control
fi

if [[ "$SKIP_ROLLOUT" == "1" ]]; then
  note "Starting compose stack (skipping encrypted rollout)"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" up -d
else
  require_cmd jq
  require_cmd zstd
  require_cmd age

  rollout_args=()
  if [[ "$NO_VERIFY" == "1" ]]; then
    rollout_args+=(--no-verify)
  fi

  note "Rolling out encrypted game image + starting compose stack"
  token_args=()
  if [[ -n "$ORCH_TOKEN_ENV" ]]; then
    token_args+=(--orch-token-env "$ORCH_TOKEN_ENV")
  elif [[ -n "$ORCH_TOKEN_FILE" ]]; then
    token_args+=(--orch-token-file "$ORCH_TOKEN_FILE")
  elif [[ -n "$ORCH_TOKEN" ]]; then
    token_args+=(--orch-token "$ORCH_TOKEN")
  fi
  "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" \
    --payments-api-url "$PAYMENTS_API_URL" \
    --image-ref "$IMAGE_REF" \
    --artifact-url "$ARTIFACT_URL" \
    "${token_args[@]}" \
    "${rollout_args[@]}"
fi

if [[ "$SKIP_REGISTRATION" != "1" ]]; then
  note "Registering orchestrator with Payments (best-effort)"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" run --rm orchestrator-registration >/dev/null 2>&1 || true
fi

note "Health checks (best-effort)"
curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 || true

cat >&2 <<EOF

[onboard] Done.

Next:
  1) Ensure inbound allowlists / firewall rules are set:
     - Forwarder ${FORWARDER_IP} -> TCP 8080,8888,8889,9877 and UDP 3478,49160-49200
     - Payments backend -> TCP 9090 (health monitoring)

  2) Verify locally:
     - Signaling health:    curl http://127.0.0.1:8080/healthz
     - Runner health:       curl http://127.0.0.1:9877/health
     - Orchestrator health: curl http://127.0.0.1:9090/health

  3) If registration didn’t show up yet, rerun:
     ${compose_cmd[*]} -f docker-compose.unreal.yml run --rm orchestrator-registration
EOF
