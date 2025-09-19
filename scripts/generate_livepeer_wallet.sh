#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/../config"
KEYSTORE_DIR="${CONFIG_DIR}/keystore"

mkdir -p "${KEYSTORE_DIR}"

if ! python3 -c 'import eth_account' &>/dev/null; then
  echo "eth-account Python package not installed. Installing to user site..."
  python3 -m pip install --user eth-account >/dev/null
fi

read -rsp "Enter new wallet passphrase: " PASSPHRASE
echo
read -rsp "Confirm passphrase: " CONFIRM
echo
if [[ "${PASSPHRASE}" != "${CONFIRM}" ]]; then
  echo "Error: passphrases do not match" >&2
  exit 1
fi

ADDRESS=$(CONFIG_DIR="$CONFIG_DIR" KEYSTORE_DIR="$KEYSTORE_DIR" PASSPHRASE="$PASSPHRASE" python3 - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path
from eth_account import Account

config_dir = Path(os.environ['CONFIG_DIR'])
keystore_dir = Path(os.environ['KEYSTORE_DIR'])
passphrase = os.environ['PASSPHRASE']

acct = Account.create()
keystore = Account.encrypt(acct.key, passphrase)
filename = f"UTC--{datetime.utcnow().isoformat().replace(':','-')}--{acct.address.lower().replace('0x','')}"
outfile = keystore_dir / filename
with outfile.open('w') as f:
    json.dump(keystore, f)
print(acct.address)
PY
)

if [[ -z "${ADDRESS}" ]]; then
  echo "Failed to generate wallet" >&2
  exit 1
fi

ETH_PASS_FILE="${CONFIG_DIR}/ethpass"
echo -n "${PASSPHRASE}" > "${ETH_PASS_FILE}"
chmod 600 "${ETH_PASS_FILE}"

echo "Generated keystore for ${ADDRESS}."
echo "Keystore saved to ${KEYSTORE_DIR}."
echo "Passphrase written to ${ETH_PASS_FILE} (not committed)."
