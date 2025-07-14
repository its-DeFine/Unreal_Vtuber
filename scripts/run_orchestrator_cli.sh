#!/bin/bash
# Run Orchestrator CLI
# Created: 2025-07-14

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🤖 Starting VTuber Orchestrator CLI..."
echo

# Check if orchestrator is running
if docker ps | grep -q orchestrator; then
    echo "✅ Orchestrator is running"
else
    echo "⚠️  Orchestrator not detected. Start it with:"
    echo "   docker-compose -f docker-compose.all.yml up orchestrator"
    echo
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run the CLI
python3 "$SCRIPT_DIR/orchestrator_cli.py" "$@"