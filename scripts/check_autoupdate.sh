#!/bin/bash
# Auto-update system health check script

echo "=== Auto-Update System Check ==="
echo ""

# Check if update_orchestrator is running
if docker ps | grep -q update_orchestrator; then
    echo "✅ Update orchestrator is running"
    
    # Check last update check
    echo ""
    echo "📋 Recent update checks:"
    docker logs update_orchestrator --tail 10 2>&1 | grep -E "Update Check|UPDATE|Local:|Remote:" | tail -5
    
    # Check current version
    echo ""
    echo "📦 Current version info:"
    docker logs vtuber_orchestrator 2>&1 | grep -E "version|Version" | tail -1
    
    # Show update interval
    echo ""
    echo "⏱️  Check interval:"
    docker exec update_orchestrator sh -c 'echo "Every $CHECK_INTERVAL seconds (or 60 if not set)"'
    
else
    echo "❌ Update orchestrator is NOT running!"
    echo ""
    echo "To start it, run:"
    echo "  docker-compose up -d update_orchestrator"
fi

echo ""
echo "=== Git Status ==="
git log --oneline -1
echo "Remote: $(git ls-remote origin main | head -1 | cut -c1-7)"

echo ""
echo "💡 The auto-updater checks for updates every 60 seconds and automatically rebuilds when changes are detected."