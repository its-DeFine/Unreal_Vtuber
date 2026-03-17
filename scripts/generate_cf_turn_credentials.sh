#!/bin/bash
# Generate Cloudflare TURN credentials and write peer_options.json for the signaling server.
# Usage: ./generate_cf_turn_credentials.sh [output_file]
#
# Reads CF_TURN_TOKEN_ID and CF_TURN_API_TOKEN from environment or .env/.env.cloudflare-turn files.
# Writes a JSON file compatible with Wilbur's --peer_options_file flag.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_FILE="${1:-${REPO_ROOT}/peer_options.json}"

# Source credentials from env files if not already set
for envfile in "${REPO_ROOT}/.env" "${REPO_ROOT}/.env.cloudflare-turn"; do
  if [[ -f "${envfile}" ]]; then
    # shellcheck disable=SC1090
    set -a; source "${envfile}"; set +a
  fi
done

if [[ -z "${CF_TURN_TOKEN_ID:-}" || -z "${CF_TURN_API_TOKEN:-}" ]]; then
  echo "Error: CF_TURN_TOKEN_ID and CF_TURN_API_TOKEN must be set" >&2
  echo "Set them in .env or .env.cloudflare-turn" >&2
  exit 1
fi

CF_TTL="${CF_TURN_TTL:-86400}"
CF_RELAY_ONLY="${CF_TURN_RELAY_ONLY:-1}"

echo "[cf-turn] Generating credentials (TTL=${CF_TTL}s)..." >&2

response=$(curl -fsS --max-time 10 \
  -H "Authorization: Bearer ${CF_TURN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"ttl\": ${CF_TTL}}" \
  "https://rtc.live.cloudflare.com/v1/turn/keys/${CF_TURN_TOKEN_ID}/credentials/generate")

if [[ -z "${response}" ]]; then
  echo "Error: Empty response from Cloudflare TURN API" >&2
  exit 1
fi

# Transform API response into peer_options format
# API returns: {"iceServers": {"urls": [...], "username": "...", "credential": "..."}}
# Wilbur expects: {"iceServers": [{...}], "iceTransportPolicy": "relay"}
python3 -c "
import json, sys
data = json.loads('''${response}''')
ice = data.get('iceServers', data)
config = {'iceServers': [ice] if isinstance(ice, dict) else ice}
if '${CF_RELAY_ONLY}' != '0':
    config['iceTransportPolicy'] = 'relay'
json.dump(config, sys.stdout, indent=2)
print()
" > "${OUTPUT_FILE}"

echo "[cf-turn] Written to ${OUTPUT_FILE}" >&2
echo "[cf-turn] Relay-only: $([ "${CF_RELAY_ONLY}" != "0" ] && echo "yes" || echo "no")" >&2
echo "[cf-turn] Expires in ${CF_TTL}s" >&2
