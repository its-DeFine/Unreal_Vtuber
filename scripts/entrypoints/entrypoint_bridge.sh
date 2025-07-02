#!/usr/bin/env bash
# entrypoint_bridge.sh – launches NeuroSync Local API, Player HTTP Server, and BYOC Worker inside a single container
# Logs stdout/stderr so that Docker captures everything.
set -euo pipefail

# Launch Local API (Flask) in the background
python /app/NeuroBridge/NeuroSync_Local_API/neurosync_local_api.py &
API_PID=$!
echo "[ENTRYPOINT] NeuroSync Local API started with PID: $API_PID"

# Launch NeuroSync Player HTTP Server in the background
python /app/NeuroBridge/NeuroSync_Player/llm_to_face.py &
PLAYER_PID=$!
echo "[ENTRYPOINT] NeuroSync Player HTTP Server started with PID: $PLAYER_PID"

# Legacy BYOC Worker removed - not needed for current game control implementation
# All functionality is now handled by the NeuroSync Player HTTP Server
echo "[ENTRYPOINT] NeuroSync system ready with Game Control enabled"

# Forward signals to all child processes
trap 'echo "[ENTRYPOINT] Received termination signal, propagating to children..."; kill -TERM $API_PID $PLAYER_PID 2>/dev/null' TERM INT

# Wait for any of the background jobs to exit
# If one exits, the script will exit, and Docker will handle container restart based on policy.
wait -n $API_PID $PLAYER_PID

echo "[ENTRYPOINT] One of the main processes exited. Exiting entrypoint." 