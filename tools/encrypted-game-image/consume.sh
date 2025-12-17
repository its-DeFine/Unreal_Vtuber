#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  consume.sh --payments-api-url <url> --image-ref <ref> --artifact-url <url> (--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>)

Options:
  --payments-api-url     Payments backend base URL (example: http://3.141.111.200:8081)
  --image-ref            Image ref registered in Payments licenses (example: ghcr.io/...:enc-v1)
  --artifact-url         Public or presigned URL to the encrypted artifact (.age)
  --orch-token           Orchestrator license token (NOT recommended; may leak via shell history)
  --orch-token-file      Read orchestrator license token from file (recommended)
  --orch-token-env       Read orchestrator license token from env var name (recommended)
  --no-heartbeat         Do not heartbeat the lease while loading
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

payments_api_url=""
image_ref=""
artifact_url=""
orch_token=""
orch_token_file=""
orch_token_env=""
heartbeat="1"

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
command -v curl >/dev/null 2>&1 || die "missing dependency: curl"
command -v jq >/dev/null 2>&1 || die "missing dependency: jq"
command -v zstd >/dev/null 2>&1 || die "missing dependency: zstd"
command -v docker >/dev/null 2>&1 || die "missing dependency: docker"
command -v age >/dev/null 2>&1 || die "missing dependency: age"

if [[ -n "$orch_token_env" ]]; then
  orch_token="${!orch_token_env:-}"
fi
if [[ -n "$orch_token_file" ]]; then
  [[ -f "$orch_token_file" ]] || die "--orch-token-file not found: $orch_token_file"
  orch_token="$(tr -d '\n' < "$orch_token_file")"
fi
[[ -n "$orch_token" ]] || die "orchestrator token required (use --orch-token-file or --orch-token-env)"

payload="$(jq -nc --arg image_ref "$image_ref" '{image_ref:$image_ref}')"
lease_json="$(curl -sS -X POST \
  -H "Authorization: Bearer $orch_token" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  "$payments_api_url/api/licenses/lease")"

lease_id="$(echo "$lease_json" | jq -r '.lease_id // empty')"
secret_b64="$(echo "$lease_json" | jq -r '.secret_b64 // empty')"
lease_seconds="$(echo "$lease_json" | jq -r '.lease_seconds // 900')"

[[ -n "$lease_id" ]] || die "missing lease_id from payments response"
[[ -n "$secret_b64" ]] || die "missing secret_b64 from payments response"

hb_pid=""
identity_file=""
cleanup() {
  if [[ -n "$hb_pid" ]]; then
    kill "$hb_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$identity_file" ]]; then
    rm -f "$identity_file" >/dev/null 2>&1 || true
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
      curl -sS -X POST -H "Authorization: Bearer $orch_token" \
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

curl -fsSL "$artifact_url" \
  | age --decrypt -i "$identity_file" \
  | zstd -d -q -c \
  | docker load

echo "Loaded encrypted image via lease_id=$lease_id"
