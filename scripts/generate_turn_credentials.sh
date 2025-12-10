#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.turn"

# Allow overriding defaults
TURN_REALM=${TURN_REALM:-pixel-streaming}
MIN_PORT=${TURN_MIN_PORT:-49160}
MAX_PORT=${TURN_MAX_PORT:-49200}
PORT=${TURN_PORT:-3478}
SECRET_LEN=${TURN_SECRET_LEN:-64}

random_string() {
  python3 - <<'PY'
import secrets
import string
alphabet = string.ascii_letters + string.digits
user = 'turn_' + ''.join(secrets.choice(alphabet) for _ in range(10))
password = ''.join(secrets.choice(alphabet) for _ in range(24))
print(user)
print(password)
PY
}

readarray -t creds < <(random_string)

turn_secret() {
  python3 - "$SECRET_LEN" <<'PY'
import secrets
import sys
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
length = int(sys.argv[1])
print(''.join(secrets.choice(alphabet) for _ in range(length)))
PY
}

TURN_USER=${TURN_USER:-${creds[0]}}
TURN_PASS=${TURN_PASS:-${creds[1]}}
TURN_SECRET=${TURN_SECRET:-$(turn_secret)}

if [[ -z "${PUBLIC_IP:-}" ]]; then
  PUBLIC_IP=$(curl -fsS --max-time 3 https://api.ipify.org || true)
else
  PUBLIC_IP=${PUBLIC_IP}
fi

if [[ -z "$PUBLIC_IP" ]]; then
  echo "Warning: Could not automatically determine public IP; TURN will advertise container IP." >&2
  PUBLIC_IP="0.0.0.0"
fi

cat >"${ENV_FILE}" <<EOF_ENV
TURN_USER=${TURN_USER}
TURN_PASS=${TURN_PASS}
TURN_REALM=${TURN_REALM}
TURN_EXTERNAL_IP=${TURN_EXTERNAL_IP:-${PUBLIC_IP}}
TURN_MIN_PORT=${MIN_PORT}
TURN_MAX_PORT=${MAX_PORT}
TURN_PORT=${PORT}
TURN_SERVER=${TURN_EXTERNAL_IP:-${PUBLIC_IP}}:${PORT}
TURN_PORT=${PORT}
TURN_SECRET=${TURN_SECRET}
EOF_ENV

chmod 600 "${ENV_FILE}"
echo "Wrote TURN credentials to ${ENV_FILE}" >&2
