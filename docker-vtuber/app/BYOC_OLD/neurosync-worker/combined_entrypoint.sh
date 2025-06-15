#!/usr/bin/env bash
# Combined entry-point that starts BOTH the original NeuroSync API (Flask)
# *and* the BYOC worker FastAPI adapter inside **one single container**.
#
# – NeuroSync Flask server: runs on port 5000 (unchanged)
# – BYOC adapter:          runs on port 9876 (configurable via $SERVER_PORT)
#
# Logs from both processes will be interleaved in stdout/stderr, which makes
# container-level log shipping simple.

set -euo pipefail

# Colours for readability when tails-ing logs.
GREEN="\033[32m"; CYAN="\033[36m"; NC="\033[0m"

echo -e "${GREEN}>>> Launching NeuroSync Core API (Flask) on :5000${NC}"
python -m neurosync.server.app &
CORE_PID=$!

echo -e "${CYAN}>>> Launching BYOC adapter on :${SERVER_PORT:-9876}${NC}"
python /app/server_adapter.py &
BYOC_PID=$!

# Wait on both – if either exits, we exit (container restarts if policy says so)
wait -n $CORE_PID $BYOC_PID 