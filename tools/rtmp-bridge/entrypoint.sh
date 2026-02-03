#!/usr/bin/env bash
set -euo pipefail

SIGNALING_URL="${RTMP_SIGNALING_URL:-ws://unreal-signaling:80}"
OUTS="${RTMP_OUTS:-}"
STREAMER_ID="${RTMP_STREAMER_ID:-}"

# docker compose .env parsing can leave quotes in-place; strip one layer.
OUTS="${OUTS%\"}"; OUTS="${OUTS#\"}"
OUTS="${OUTS%\'}"; OUTS="${OUTS#\'}"

if [ -z "${OUTS}" ]; then
  echo "ERROR: RTMP_OUTS is required (space-separated list of RTMP URLs)" >&2
  exit 2
fi

args=( "--signaling" "${SIGNALING_URL}" )
if [ -n "${STREAMER_ID}" ]; then
  args+=( "--streamer-id" "${STREAMER_ID}" )
fi

if [ "${RTMP_TRANSCODE_VIDEO:-1}" = "1" ]; then
  args+=( "--transcode-video" )
  args+=( "--video-bitrate-kbps" "${RTMP_VIDEO_BITRATE_KBPS:-6000}" )
  args+=( "--fps" "${RTMP_FPS:-30}" )
fi

if [ "${RTMP_FORCE_H264:-0}" = "1" ]; then
  args+=( "--force-h264" )
fi

args+=( "--audio-bitrate-kbps" "${RTMP_AUDIO_BITRATE_KBPS:-160}" )

for url in ${OUTS}; do
  args+=( "--rtmp-out" "${url}" )
done

# PYTHONPATH is set in the Dockerfile so apt-installed GI bindings (python3-gi)
# are importable from the Python.org runtime (/usr/local/bin/python3).
exec python3 /opt/embody/rtmp-bridge/gs_webrtc_rtmp.py "${args[@]}"
