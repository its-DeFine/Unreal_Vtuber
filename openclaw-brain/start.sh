#!/usr/bin/env bash
set -euo pipefail

AGENT_NAME="${AGENT_NAME:-agent}"
AGENT_PERSONA="${AGENT_PERSONA:-A friendly VTuber streamer}"
AVATAR_SLUG="${AVATAR_SLUG:-default}"

echo "[start] Initializing openclaw-brain for agent=${AGENT_NAME} avatar=${AVATAR_SLUG}"

# ---------------------------------------------------------------------------
# 1. Generate OpenClaw workspace from templates
# ---------------------------------------------------------------------------
WORKSPACE="/workspace"
mkdir -p "${WORKSPACE}/skills" "${WORKSPACE}/coaching"

if [ ! -f "${WORKSPACE}/SOUL.md" ]; then
  sed -e "s|{{AGENT_NAME}}|${AGENT_NAME}|g" \
      -e "s|{{AGENT_PERSONA}}|${AGENT_PERSONA}|g" \
      /app/templates/SOUL.md > "${WORKSPACE}/SOUL.md"
  echo "[start] Generated SOUL.md"
fi

if [ ! -f "${WORKSPACE}/IDENTITY.md" ]; then
  sed -e "s|{{AVATAR_SLUG}}|${AVATAR_SLUG}|g" \
      -e "s|{{AGENT_NAME}}|${AGENT_NAME}|g" \
      -e "s|{{AGENT_NETWORK_URL}}|${AGENT_NETWORK_URL:-}|g" \
      /app/templates/IDENTITY.md > "${WORKSPACE}/IDENTITY.md"
  echo "[start] Generated IDENTITY.md"
fi

# Copy skills into workspace (don't overwrite customised ones)
for skill in /app/skills/*.md; do
  base=$(basename "$skill")
  [ -f "${WORKSPACE}/skills/${base}" ] || cp "$skill" "${WORKSPACE}/skills/${base}"
done

# ---------------------------------------------------------------------------
# 2. Initialise long-term memory DB
# ---------------------------------------------------------------------------
mkdir -p /data/memory
echo "[start] Ensuring long-term memory database …"
node -e "import('./long-term-memory.mjs').then(m => { const db = new m.MemoryDB(); db.close(); console.log('[start] Memory DB ready'); })"

# ---------------------------------------------------------------------------
# 3. Start OpenClaw gateway (background)
# ---------------------------------------------------------------------------
if command -v openclaw &>/dev/null; then
  echo "[start] Starting OpenClaw gateway …"
  openclaw gateway --workspace "${WORKSPACE}" --port 18789 &
  OPENCLAW_PID=$!

  # Wait for gateway readiness (up to 30 s)
  for i in $(seq 1 30); do
    if curl -sf http://localhost:18789/health >/dev/null 2>&1; then
      echo "[start] OpenClaw gateway ready"
      break
    fi
    sleep 1
  done
else
  echo "[start] OpenClaw CLI not installed; chat-shim will run in stub mode"
fi

# ---------------------------------------------------------------------------
# 4. Start infra-manager (background)
# ---------------------------------------------------------------------------
echo "[start] Starting infra-manager …"
node /app/infra-manager.mjs &
INFRA_PID=$!

# ---------------------------------------------------------------------------
# 5. Start network-client (background, restarts on crash)
# ---------------------------------------------------------------------------
if [ -n "${AGENT_NETWORK_URL:-}" ]; then
  echo "[start] Starting network-client → ${AGENT_NETWORK_URL} …"
  (
    while true; do
      node /app/network-client.mjs || true
      echo "[start] network-client exited; restarting in 5 s …"
      sleep 5
    done
  ) &
  NETWORK_PID=$!
else
  echo "[start] AGENT_NETWORK_URL not set; network-client disabled"
fi

# ---------------------------------------------------------------------------
# 6. Start chat-shim (foreground — container stops if this exits)
# ---------------------------------------------------------------------------
echo "[start] Starting chat-shim on :18801 …"
exec node /app/chat-shim.mjs
