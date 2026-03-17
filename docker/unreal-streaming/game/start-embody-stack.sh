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

# Cloudflare TURN: generate short-lived credentials at startup
if [[ -n "${CF_TURN_TOKEN_ID:-}" && -n "${CF_TURN_API_TOKEN:-}" ]]; then
  CF_TTL="${CF_TURN_TTL:-86400}"
  cf_response=$(curl -fsS --max-time 5 \
    -H "Authorization: Bearer ${CF_TURN_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"ttl\": ${CF_TTL}}" \
    "https://rtc.live.cloudflare.com/v1/turn/keys/${CF_TURN_TOKEN_ID}/credentials/generate" 2>/dev/null || true)

  if [[ -n "${cf_response}" ]]; then
    ICE_JSON=$(echo "${cf_response}" | node -e "
      const chunks = [];
      process.stdin.on('data', c => chunks.push(c));
      process.stdin.on('end', () => {
        try {
          const data = JSON.parse(Buffer.concat(chunks).toString());
          const ice = data.iceServers;
          const config = {iceServers: Array.isArray(ice) ? ice : [ice]};
          if (process.env.CF_TURN_RELAY_ONLY !== '0') config.iceTransportPolicy = 'relay';
          process.stdout.write(JSON.stringify(config));
        } catch(e) { process.exit(1); }
      });" 2>/dev/null || true)

    if [[ -n "${ICE_JSON}" ]]; then
      echo "[pixel-streaming] Using Cloudflare TURN (TTL=${CF_TTL}s)" >&2
    else
      echo "[pixel-streaming] Warning: failed to parse Cloudflare TURN response" >&2
    fi
  else
    echo "[pixel-streaming] Warning: Cloudflare TURN API unreachable, falling back to static TURN config" >&2
  fi
fi

# Static ICE config (skipped if Cloudflare TURN already set ICE_JSON above)
if [[ -z "${ICE_JSON}" ]]; then
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
