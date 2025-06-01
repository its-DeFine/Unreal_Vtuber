#!/bin/bash

# 🧪 Simple Monitor Test - Verify No Duplication
# Tests the fixed monitoring system with a short run

set -e

echo "🧪 Testing Fixed Monitoring System"
echo "=================================="

# Test duration (1 minute)
TEST_DURATION=1

echo "📊 Starting $TEST_DURATION minute test..."
echo "⏰ Start time: $(date)"

# Run the fixed monitoring system
./monitor_autonomous_system_fixed.sh $TEST_DURATION

echo ""
echo "✅ Test completed at: $(date)"

# Find the latest session
LATEST_SESSION=$(ls -t logs/autonomous_monitoring/session_* | head -1)
echo "📁 Latest session: $LATEST_SESSION"

echo ""
echo "📊 Results Summary:"
echo "=================="

if [ -d "$LATEST_SESSION/structured" ]; then
    echo "📋 Event counts:"
    for file in "$LATEST_SESSION/structured"/*.jsonl; do
        if [ -f "$file" ]; then
            event_type=$(basename "$file" .jsonl)
            count=$(wc -l < "$file" 2>/dev/null || echo "0")
            echo "   $event_type: $count events"
        fi
    done
    
    echo ""
    echo "🔍 Checking for duplicates in autonomous_iteration.jsonl:"
    if [ -f "$LATEST_SESSION/structured/autonomous_iteration.jsonl" ]; then
        # Check for duplicate timestamps (a sign of duplication)
        duplicate_count=$(grep '"timestamp"' "$LATEST_SESSION/structured/autonomous_iteration.jsonl" | sort | uniq -d | wc -l)
        if [ "$duplicate_count" -eq 0 ]; then
            echo "   ✅ No duplicate timestamps found!"
        else
            echo "   ❌ Found $duplicate_count duplicate timestamps"
        fi
        
        # Show first few entries
        echo ""
        echo "📝 First 3 autonomous iterations:"
        head -30 "$LATEST_SESSION/structured/autonomous_iteration.jsonl" | grep -A 10 '"event_type": "autonomous_iteration"' | head -15
    fi
else
    echo "❌ No structured logs found - containers may not be generating logs"
fi

echo ""
echo "�� Test completed!" 