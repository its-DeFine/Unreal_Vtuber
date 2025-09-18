#!/bin/bash
set -euo pipefail

PUBLIC_IP="${PUBLIC_IP:-auto}"
HTTP_PORT="${HTTP_PORT:-8080}"
STREAMER_PORT="${STREAMER_PORT:-8888}"
SFU_PORT="${SFU_PORT:-8889}"
STUN_SERVER="${STUN_SERVER:-}"
TURN_SERVER="${TURN_SERVER:-}"
TURN_USER="${TURN_USER:-}"
TURN_PASS="${TURN_PASS:-}"
EXTRA_ARGS="${SIGNALING_EXTRA_ARGS:-}"

# Build ICE server JSON if STUN/TURN provided
ICE_JSON=""
PS_NODE_DIR=/opt/pixel-streaming/SignallingWebServer/platform_scripts/node/bin
if [[ -x "${PS_NODE_DIR}/npm" ]]; then
  export PATH="${PS_NODE_DIR}:$PATH"
fi

pushd /opt/pixel-streaming/Signalling > /dev/null
npm link ../Common >/dev/null
npm run build >/dev/null
popd > /dev/null

pushd /opt/pixel-streaming/SignallingWebServer > /dev/null
npm link ../Signalling >/dev/null
npm run build >/dev/null
popd > /dev/null

declare -a ICE_URLS=()
if [[ -n "${STUN_SERVER}" ]]; then
  ICE_URLS+=("stun:${STUN_SERVER}")
fi
if [[ -n "${TURN_SERVER}" ]]; then
  ICE_URLS+=("turn:${TURN_SERVER}")
fi

if (( ${#ICE_URLS[@]} > 0 )); then
  urls="$(printf '"%s",' "${ICE_URLS[@]}")"
  urls="[${urls%,}]"
  if [[ -n "${TURN_SERVER}" && -n "${TURN_USER}" ]]; then
    ICE_JSON="{\"iceServers\":[{\"urls\":${urls},\"username\":\"${TURN_USER}\",\"credential\":\"${TURN_PASS}\"}]}"
  else
    ICE_JSON="{\"iceServers\":[{\"urls\":${urls}}]}"
  fi
fi

cmd=(
  node /opt/pixel-streaming/SignallingWebServer/build/index.js
  --serve
  --public_ip="${PUBLIC_IP}"
  --player_port="${HTTP_PORT}"
  --streamer_port="${STREAMER_PORT}"
  --sfu_port="${SFU_PORT}"
  --http_root="/opt/pixel-streaming/SignallingWebServer/www"
  --homepage="player.html"
)

if [[ -n "${ICE_JSON}" ]]; then
  cmd+=("--peer_options=${ICE_JSON}")
fi

if [[ "${ENABLE_REST_API:-0}" == "1" ]]; then
  cmd+=("--rest_api")
fi

if [[ -n "${EXTRA_ARGS}" ]]; then
  # shellcheck disable=SC2206
  extra_array=(${EXTRA_ARGS})
  cmd+=("${extra_array[@]}")
fi

echo "[signaling] starting with public_ip=${PUBLIC_IP} player_port=${HTTP_PORT} streamer_port=${STREAMER_PORT} sfu_port=${SFU_PORT}" >&2
exec "${cmd[@]}"
