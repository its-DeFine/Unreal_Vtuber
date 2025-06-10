#!/bin/bash

# 🧹 Clean Duplicate Logs Script
# Removes existing duplicated monitoring logs to start fresh

set -e

LOG_DIR="./logs/autonomous_monitoring"

echo "🧹 Cleaning up duplicate monitoring logs..."

if [ -d "$LOG_DIR" ]; then
    echo "📁 Found monitoring logs directory: $LOG_DIR"
    
    # List existing sessions
    echo "📊 Existing sessions:"
    ls -la "$LOG_DIR" | grep "session_" || echo "   No sessions found"
    
    echo ""
    read -p "🗑️  Do you want to remove ALL existing monitoring sessions? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing all monitoring sessions..."
        rm -rf "$LOG_DIR"/session_*
        echo "✅ All monitoring sessions removed"
    else
        echo "⏭️  Keeping existing sessions"
    fi
else
    echo "📁 No monitoring logs directory found - nothing to clean"
fi

echo ""
echo "🚀 Ready to start fresh monitoring with the fixed script!"
echo "💡 Run: ./monitor_autonomous_system_working.sh 1"
echo "   (for a 1-minute test to verify no duplication)" 