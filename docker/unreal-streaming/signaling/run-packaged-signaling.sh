#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="/opt/embody/Embody/Samples/PixelStreaming/WebServers/SignallingWebServer/platform_scripts/bash"
export PATH="${SCRIPT_DIR}/node/bin:${PATH}"
START_SCRIPT="${SCRIPT_DIR}/start.sh"

if [[ ! -x "${START_SCRIPT}" ]]; then
  echo "Error: ${START_SCRIPT} not found or not executable" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"

args=("${START_SCRIPT}" "--nosudo")

if [[ -n "${PUBLIC_IP:-}" && "${PUBLIC_IP}" != "auto" ]]; then
  args+=("--publicip" "${PUBLIC_IP}")
fi

if [[ -n "${TURN_SERVER:-}" ]]; then
  args+=("--turn" "${TURN_SERVER}")
fi

if [[ -n "${TURN_USER:-}" ]]; then
  args+=("--turn-user" "${TURN_USER}")
fi

if [[ -n "${TURN_PASS:-}" ]]; then
  args+=("--turn-pass" "${TURN_PASS}")
fi

args+=("--stun" "${STUN_SERVER:-stun.l.google.com:19302}")

HTTP_PORT_VALUE="${HTTP_PORT:-8080}"
STREAMER_PORT_VALUE="${STREAMER_PORT:-8888}"
SFU_PORT_VALUE="${SFU_PORT:-8889}"

args+=("--player_port" "${HTTP_PORT_VALUE}")
args+=("--streamer_port" "${STREAMER_PORT_VALUE}")
args+=("--sfu_port" "${SFU_PORT_VALUE}")

if [[ -z "${TURN_SERVER:-}" ]]; then
  args+=("--turn" "turn-server:3478")
fi

if [[ -n "${SIGNALING_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra=( ${SIGNALING_EXTRA_ARGS} )
  args+=("${extra[@]}")
fi

exec "${args[@]}"
