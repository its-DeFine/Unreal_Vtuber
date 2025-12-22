#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Note: scripts/onboard_orchestrator.sh is deprecated; use ./scripts/embody_cli.sh (or ./scripts/embody_cli.sh setup)." >&2
exec "${SCRIPT_DIR}/embody_cli.sh" setup "$@"

