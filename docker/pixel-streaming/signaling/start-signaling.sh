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

# Resolve auto public IP if requested
if [[ "${PUBLIC_IP}" == "auto" ]]; then
  detected_ip=$(curl -fsS --max-time 3 https://api.ipify.org || true)
  if [[ -n "${detected_ip}" ]]; then
    PUBLIC_IP="${detected_ip}"
  else
    PUBLIC_IP="127.0.0.1"
    echo "[signaling] Warning: unable to autodetect public IP, defaulting to ${PUBLIC_IP}" >&2
  fi
fi

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

# Cloudflare TURN: generate short-lived credentials at startup
if [[ -z "${ICE_JSON}" && -n "${CF_TURN_TOKEN_ID:-}" && -n "${CF_TURN_API_TOKEN:-}" ]]; then
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
      echo "[signaling] Using Cloudflare TURN (TTL=${CF_TTL}s)" >&2
    else
      echo "[signaling] Warning: failed to parse Cloudflare TURN response" >&2
    fi
  else
    echo "[signaling] Warning: Cloudflare TURN API unreachable, falling back to static TURN config" >&2
  fi
fi

# Static ICE config (skipped if Cloudflare TURN already set ICE_JSON above)
if [[ -z "${ICE_JSON}" ]]; then
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
