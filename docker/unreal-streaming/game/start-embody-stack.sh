#!/bin/bash
set -euo pipefail

SIGNALING_HTTP_PORT="${SIGNALING_HTTP_PORT:-8080}"
SIGNALING_STREAMER_PORT="${SIGNALING_STREAMER_PORT:-8888}"
SIGNALING_SFU_PORT="${SIGNALING_SFU_PORT:-8889}"
AUTO_PUBLIC_IP="${AUTO_PUBLIC_IP:-1}"
SIGNALING_PUBLIC_IP="${SIGNALING_PUBLIC_IP:-${PUBLIC_IP:-}}"

if [[ -z "${SIGNALING_PUBLIC_IP}" && "${AUTO_PUBLIC_IP}" != "0" ]]; then
  SIGNALING_PUBLIC_IP="$(curl -s --max-time 2 https://api.ipify.org || true)"
fi
if [[ -z "${SIGNALING_PUBLIC_IP}" ]]; then
  SIGNALING_PUBLIC_IP="127.0.0.1"
fi

STUN_SERVER="${SIGNALING_STUN_SERVER:-${STUN_SERVER:-stun.l.google.com:19302}}"
TURN_SERVER="${SIGNALING_TURN_SERVER:-${TURN_SERVER:-}}"
TURN_USER="${SIGNALING_TURN_USER:-${TURN_USER:-}}"
TURN_PASS="${SIGNALING_TURN_PASS:-${TURN_PASS:-}}"

ICE_JSON=""
declare -a ice_urls=()
if [[ -n "${STUN_SERVER}" ]]; then
  ice_urls+=("stun:${STUN_SERVER}")
fi
if [[ -n "${TURN_SERVER}" ]]; then
  ice_urls+=("turn:${TURN_SERVER}")
fi
if ((${#ice_urls[@]} > 0)); then
  json_urls=$(printf '"%s",' "${ice_urls[@]}")
  json_urls="[${json_urls%,}]"
  if [[ -n "${TURN_SERVER}" && -n "${TURN_USER}" ]]; then
    ICE_JSON="{\"iceServers\":[{\"urls\":${json_urls},\"username\":\"${TURN_USER}\",\"credential\":\"${TURN_PASS}\"}]}"
  else
    ICE_JSON="{\"iceServers\":[{\"urls\":${json_urls}}]}"
  fi
fi

node_cmd=(
  node /opt/pixel-streaming/SignallingWebServer/build/index.js
  --serve
  --public_ip="${SIGNALING_PUBLIC_IP}"
  --player_port="${SIGNALING_HTTP_PORT}"
  --streamer_port="${SIGNALING_STREAMER_PORT}"
  --sfu_port="${SIGNALING_SFU_PORT}"
  --http_root="/opt/pixel-streaming/SignallingWebServer/www"
  --homepage="player.html"
)

if [[ -n "${ICE_JSON}" ]]; then
  node_cmd+=("--peer_options=${ICE_JSON}")
fi
if [[ "${ENABLE_PS_REST_API:-0}" == "1" ]]; then
  node_cmd+=("--rest_api")
fi
if [[ -n "${SIGNALING_LOG_LEVEL:-}" ]]; then
  node_cmd+=("--log_level_console=${SIGNALING_LOG_LEVEL}")
fi
if [[ -n "${SIGNALING_LOG_FOLDER:-}" ]]; then
  node_cmd+=("--log_folder=${SIGNALING_LOG_FOLDER}")
fi
if [[ -n "${SIGNALING_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=(${SIGNALING_EXTRA_ARGS})
  node_cmd+=("${extra_args[@]}")
fi

echo "[pixel-streaming] starting signalling server on ports ${SIGNALING_HTTP_PORT}/${SIGNALING_STREAMER_PORT}/${SIGNALING_SFU_PORT}"

cleanup() {
  if [[ -n "${signaling_pid:-}" ]] && kill -0 "${signaling_pid}" 2>/dev/null; then
    kill "${signaling_pid}" 2>/dev/null || true
    wait "${signaling_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

"${node_cmd[@]}" &
signaling_pid=$!

for attempt in {1..60}; do
  if curl -fs "http://127.0.0.1:${SIGNALING_HTTP_PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! kill -0 "${signaling_pid}" 2>/dev/null; then
  echo "[pixel-streaming] signalling server exited prematurely" >&2
  wait "${signaling_pid}"
fi

export PIXEL_STREAMING_URL="${PIXEL_STREAMING_URL:-ws://127.0.0.1:${SIGNALING_STREAMER_PORT}}"

exec /usr/local/bin/start-embody.sh "$@"
