#!/usr/bin/env bash
# =============================================================================
# agent-setup-wizard.sh — Interactive setup for an openclaw-brain agent.
#
# Generates ~/.embody/agent.json with agent name, persona, voice, skills, and
# network configuration.
# =============================================================================
set -euo pipefail

TARGET_HOME="${TARGET_HOME:-$HOME}"
CONFIG_DIR="${TARGET_HOME}/.embody"
CONFIG_FILE="${CONFIG_DIR}/agent.json"

# ---------------------------------------------------------------------------
# Parse flags for non-interactive use
# ---------------------------------------------------------------------------
AGENT_NAME="" AGENT_PERSONA="" VOICE="" NETWORK_URL="" FORCE="0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)       AGENT_NAME="${2:-}"; shift 2 ;;
    --persona)    AGENT_PERSONA="${2:-}"; shift 2 ;;
    --voice)      VOICE="${2:-}"; shift 2 ;;
    --network)    NETWORK_URL="${2:-}"; shift 2 ;;
    --force)      FORCE="1"; shift ;;
    -h|--help)
      cat <<'EOF'
Usage: agent-setup-wizard.sh [options]

Options:
  --name <name>         Agent name (default: avatar slug)
  --persona <text>      Persona description
  --voice <voice>       TTS voice (alloy|echo|fable|onyx|nova|shimmer)
  --network <url>       Agent network URL
  --force               Overwrite existing config

Without options, runs an interactive wizard.
EOF
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Interactive prompts (only if values not provided via flags)
# ---------------------------------------------------------------------------
if [ -f "$CONFIG_FILE" ] && [ "$FORCE" != "1" ]; then
  echo "Agent config already exists at ${CONFIG_FILE}"
  echo "Use --force to overwrite."
  exit 0
fi

DEFAULT_SLUG="${VTUBER_AVATAR_SLUG:-agent}"

if [ -z "$AGENT_NAME" ]; then
  printf "Agent name [%s]: " "$DEFAULT_SLUG"
  read -r AGENT_NAME
  AGENT_NAME="${AGENT_NAME:-$DEFAULT_SLUG}"
fi

if [ -z "$AGENT_PERSONA" ]; then
  printf "Persona description: "
  read -r AGENT_PERSONA
  AGENT_PERSONA="${AGENT_PERSONA:-A friendly VTuber streamer}"
fi

if [ -z "$VOICE" ]; then
  echo "Available voices: alloy, echo, fable, onyx, nova, shimmer"
  printf "Voice [nova]: "
  read -r VOICE
  VOICE="${VOICE:-nova}"
fi

# Skills selection
echo ""
echo "Available skills:"
echo "  1) streamer        — VTuber chat engagement"
echo "  2) avatar-control  — Unreal Engine avatar commands"
echo "  3) scheduler       — Appointment management"
echo "  4) network-agent   — Peer network participation"
echo "  5) infra-ops       — Infrastructure management"
echo "  6) evolution       — Self-improvement loop"
printf "Enable skills (comma-separated numbers, or 'all') [all]: "
read -r SKILLS_INPUT
SKILLS_INPUT="${SKILLS_INPUT:-all}"

SKILLS=()
if [ "$SKILLS_INPUT" = "all" ]; then
  SKILLS=("streamer" "avatar-control" "scheduler" "network-agent" "infra-ops" "evolution")
else
  IFS=',' read -ra NUMS <<< "$SKILLS_INPUT"
  for n in "${NUMS[@]}"; do
    n=$(echo "$n" | tr -d ' ')
    case "$n" in
      1) SKILLS+=("streamer") ;;
      2) SKILLS+=("avatar-control") ;;
      3) SKILLS+=("scheduler") ;;
      4) SKILLS+=("network-agent") ;;
      5) SKILLS+=("infra-ops") ;;
      6) SKILLS+=("evolution") ;;
    esac
  done
fi

if [ -z "$NETWORK_URL" ]; then
  printf "Agent network URL (leave empty to skip): "
  read -r NETWORK_URL
fi

NETWORK_TOKEN=""
if [ -n "$NETWORK_URL" ]; then
  printf "Agent network token (leave empty to auto-generate on register): "
  read -r NETWORK_TOKEN
fi

# ---------------------------------------------------------------------------
# Write config
# ---------------------------------------------------------------------------
mkdir -p "$CONFIG_DIR"

SKILLS_JSON=$(printf '%s\n' "${SKILLS[@]}" | python3 -c '
import json, sys
skills = [line.strip() for line in sys.stdin if line.strip()]
print(json.dumps(skills))
')

python3 -c "
import json
config = {
    'agent_name': $(printf '%s' "$AGENT_NAME" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    'persona': $(printf '%s' "$AGENT_PERSONA" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    'avatar_slug': '${DEFAULT_SLUG}',
    'voice': '${VOICE}',
    'skills': ${SKILLS_JSON},
    'network_url': '${NETWORK_URL}',
    'network_token': '${NETWORK_TOKEN}',
    'auto_governance': False,
    'infra_auto_restart': True,
}
with open('${CONFIG_FILE}', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
print(json.dumps(config, indent=2))
"

echo ""
echo "Agent config written to ${CONFIG_FILE}"
echo ""
echo "Next steps:"
echo "  1. Start the agent:  ./scripts/embody_cli.sh agent start"
echo "  2. Check status:     ./scripts/embody_cli.sh agent status"
if [ -n "$NETWORK_URL" ]; then
  echo "  3. Register:         ./scripts/embody_cli.sh agent network register"
fi
