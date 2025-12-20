#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  rollout.sh --payments-api-url <url> --image-ref <ref> --artifact-url <url> (--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>)

This is an orchestrator helper that:
  1) Stops the compose stack
  2) Removes the local game image tag (forces a clean reload)
  3) Downloads + decrypts + docker loads the encrypted artifact via a Payments lease
  4) Restarts the compose stack

Options:
  --payments-api-url     Payments backend base URL (example: http://3.141.111.200:8081)
  --image-ref            Image ref registered in Payments licenses (example: ghcr.io/...:enc-v1)
  --artifact-url         Public or presigned URL to the encrypted artifact (.tar.zst.age)
  --orch-token           Orchestrator license token (NOT recommended; may leak via shell history)
  --orch-token-file      Read orchestrator license token from file (recommended)
  --orch-token-env       Read orchestrator license token from env var name (recommended)

  --compose-file         Compose file path (default: ./docker-compose.unreal.yml)
  --game-image           Game image ref to remove before reload (default: auto-detected from compose)
  --no-verify            Skip local health checks after restart
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

payments_api_url=""
image_ref=""
artifact_url=""
orch_token=""
orch_token_file=""
orch_token_env=""

compose_file="$REPO_ROOT/docker-compose.unreal.yml"
game_image=""
verify="1"

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
    --compose-file)
      compose_file="${2:-}"
      shift 2
      ;;
    --game-image)
      game_image="${2:-}"
      shift 2
      ;;
    --no-verify)
      verify="0"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown arg: $1"
      ;;
  esac
done

[[ -n "$payments_api_url" ]] || die "--payments-api-url is required"
[[ -n "$image_ref" ]] || die "--image-ref is required"
[[ -n "$artifact_url" ]] || die "--artifact-url is required"

command -v docker >/dev/null 2>&1 || die "missing dependency: docker"
command -v curl >/dev/null 2>&1 || die "missing dependency: curl"
command -v jq >/dev/null 2>&1 || die "missing dependency: jq"
command -v zstd >/dev/null 2>&1 || die "missing dependency: zstd"
command -v age >/dev/null 2>&1 || die "missing dependency: age"

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  die "missing dependency: docker compose (or docker-compose)"
fi

compose_file="$(cd "$REPO_ROOT" && realpath "$compose_file" 2>/dev/null || echo "$compose_file")"
[[ -f "$compose_file" ]] || die "compose file not found: $compose_file"

token_args=()
if [[ -n "$orch_token_env" ]]; then
  token_args=(--orch-token-env "$orch_token_env")
elif [[ -n "$orch_token_file" ]]; then
  [[ -f "$orch_token_file" ]] || die "--orch-token-file not found: $orch_token_file"
  token_args=(--orch-token-file "$orch_token_file")
elif [[ -n "$orch_token" ]]; then
  token_args=(--orch-token "$orch_token")
else
  die "orchestrator token required (use --orch-token-file or --orch-token-env)"
fi

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

if [[ -z "$game_image" ]]; then
  game_image="$(detect_game_image_from_compose "$compose_file" || true)"
fi
[[ -n "$game_image" ]] || die "could not detect game image from compose; pass --game-image"

cd "$REPO_ROOT"

echo "[rollout] ensuring vtuber_network exists"
docker network create vtuber_network 2>/dev/null || true

echo "[rollout] stopping stack"
"${compose_cmd[@]}" -f "$compose_file" down

echo "[rollout] removing local game image tag: $game_image"
docker image rm -f "$game_image" >/dev/null 2>&1 || true

echo "[rollout] loading encrypted game image via Payments lease"
"$SCRIPT_DIR/consume.sh" \
  --payments-api-url "$payments_api_url" \
  --image-ref "$image_ref" \
  --artifact-url "$artifact_url" \
  "${token_args[@]}"

echo "[rollout] starting stack"
"${compose_cmd[@]}" -f "$compose_file" up -d

if [[ "$verify" == "1" ]]; then
  echo "[rollout] verifying local health (best-effort)"
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 || die "runner health check failed on 127.0.0.1:9877"
fi

echo "[rollout] done"
