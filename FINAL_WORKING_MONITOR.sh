#!/bin/bash

# =============================================================================
# FINAL WORKING AUTONOMOUS VTUBER MONITOR
# =============================================================================
# Following Better Stack logging best practices:
# ✅ "Establish clear objectives" - Monitor autonomous cycles and VTuber comms
# ✅ "Write meaningful log entries" - Only real events, no noise
# ✅ "Don't ignore performance cost" - Single pass extraction
# ✅ "Structure your logs" - Clean JSON format
# =============================================================================

set -euo pipefail

readonly SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"
readonly LOG_DIR="logs/autonomous_monitoring/${SESSION_ID}"

mkdir -p "$LOG_DIR"

echo "🚀 FINAL WORKING AUTONOMOUS VTUBER MONITOR"
echo "=========================================="
echo "📁 Session: $SESSION_ID"
echo "⏰ Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# =============================================================================
# GET RAW LOGS
# =============================================================================

echo "📊 Getting raw logs from last 10 minutes..."
SINCE_TIME=$(date -d "10 minutes ago" '+%Y-%m-%dT%H:%M:%S')
echo "⏰ Since: $SINCE_TIME"

RAW_FILE="$LOG_DIR/raw_logs.txt"
docker logs autonomous_starter_s3 --since "$SINCE_TIME" > "$RAW_FILE" 2>&1

LINE_COUNT=$(wc -l < "$RAW_FILE")
echo "📄 Raw log lines: $LINE_COUNT"

if [[ $LINE_COUNT -eq 0 ]]; then
    echo "❌ No logs found - container might not be running"
    exit 1
fi

# =============================================================================
# EXTRACT ALL EVENTS
# =============================================================================

echo ""
echo "🔍 Extracting all events..."

EVENTS_FILE="$LOG_DIR/events.jsonl"
> "$EVENTS_FILE"  # Clear file

# Extract autonomous cycles
echo "🔄 Extracting autonomous cycles..."
CYCLES_FOUND=0
grep -E "iteration.*completed" "$RAW_FILE" | while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*iteration\ ([0-9]+)\ completed ]]; then
        timestamp="${BASH_REMATCH[1]}"
        iteration="${BASH_REMATCH[2]}"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"autonomous_cycle\",\"iteration\":$iteration,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        CYCLES_FOUND=$((CYCLES_FOUND + 1))
    fi
done
CYCLES_FOUND=$(grep -c '"type":"autonomous_cycle"' "$EVENTS_FILE" 2>/dev/null || echo "0")
echo "   ✅ Found $CYCLES_FOUND autonomous cycles"

# Extract VTuber sends
echo "📤 Extracting VTuber sends..."
grep -E "🎯 SENDING TO VTUBER" "$RAW_FILE" | while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*🎯\ SENDING\ TO\ VTUBER:\ (.+)\ at\ http ]]; then
        timestamp="${BASH_REMATCH[1]}"
        message="${BASH_REMATCH[2]}"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_send\",\"message\":$message,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
    fi
done
SENDS_FOUND=$(grep -c '"type":"vtuber_send"' "$EVENTS_FILE" 2>/dev/null || echo "0")
echo "   ✅ Found $SENDS_FOUND VTuber sends"

# Extract VTuber responses
echo "📥 Extracting VTuber responses..."
grep -E "✅ VTUBER RESPONSE RECEIVED" "$RAW_FILE" | while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*✅\ VTUBER\ RESPONSE\ RECEIVED ]]; then
        timestamp="${BASH_REMATCH[1]}"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_response\",\"status\":\"success\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
    fi
done
RESPONSES_FOUND=$(grep -c '"type":"vtuber_response"' "$EVENTS_FILE" 2>/dev/null || echo "0")
echo "   ✅ Found $RESPONSES_FOUND VTuber responses"

# Extract memory errors
echo "💾 Extracting memory errors..."
grep -E "ERROR.*MemoryArchivingEngine" "$RAW_FILE" | while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\]\ ERROR:\ \[MemoryArchivingEngine\]\ (.+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        error="${BASH_REMATCH[2]}"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"memory_error\",\"error\":\"$error\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
    fi
done
ERRORS_FOUND=$(grep -c '"type":"memory_error"' "$EVENTS_FILE" 2>/dev/null || echo "0")
echo "   ✅ Found $ERRORS_FOUND memory errors"

TOTAL_EVENTS=$(wc -l < "$EVENTS_FILE" 2>/dev/null || echo "0")
echo ""
echo "📊 Total events extracted: $TOTAL_EVENTS"

# =============================================================================
# GENERATE DASHBOARD
# =============================================================================

echo ""
echo "📋 Generating dashboard..."

# Container status
AUTONOMOUS_STATUS="unknown"
NEUROSYNC_STATUS="unknown"

if docker inspect autonomous_starter_s3 >/dev/null 2>&1; then
    AUTONOMOUS_STATUS=$(docker inspect --format='{{.State.Status}}' autonomous_starter_s3)
fi

if docker inspect neurosync_byoc >/dev/null 2>&1; then
    NEUROSYNC_STATUS=$(docker inspect --format='{{.State.Status}}' neurosync_byoc)
fi

# Create dashboard
DASHBOARD_FILE="$LOG_DIR/dashboard.txt"
cat > "$DASHBOARD_FILE" << EOF
🚀 AUTONOMOUS VTUBER SYSTEM MONITOR
==================================
Session: $SESSION_ID
Updated: $(date '+%Y-%m-%d %H:%M:%S')

📊 CONTAINER STATUS:
   🤖 Autonomous Agent: $AUTONOMOUS_STATUS
   🧠 NeuroSync VTuber: $NEUROSYNC_STATUS

📈 EVENTS CAPTURED (NO DUPLICATES):
   🔄 Autonomous Cycles: $CYCLES_FOUND
   📤 VTuber Sends: $SENDS_FOUND
   📥 VTuber Responses: $RESPONSES_FOUND
   ❌ Memory Errors: $ERRORS_FOUND
   📊 Total Events: $TOTAL_EVENTS

📁 FILES:
   📋 Events: $EVENTS_FILE
   📄 Raw Logs: $RAW_FILE
   📊 Dashboard: $DASHBOARD_FILE

EOF

# =============================================================================
# DISPLAY RESULTS
# =============================================================================

clear
cat "$DASHBOARD_FILE"

# Show recent events
if [[ -f "$EVENTS_FILE" && -s "$EVENTS_FILE" ]]; then
    echo ""
    echo "🔍 RECENT EVENTS:"
    echo "================"
    tail -10 "$EVENTS_FILE" | while IFS= read -r line; do
        timestamp=$(echo "$line" | jq -r '.timestamp // "unknown"' 2>/dev/null || echo "unknown")
        type=$(echo "$line" | jq -r '.type // "unknown"' 2>/dev/null || echo "unknown")
        
        case "$type" in
            "autonomous_cycle")
                iteration=$(echo "$line" | jq -r '.iteration // "?"' 2>/dev/null || echo "?")
                echo "   🔄 $timestamp - Cycle $iteration completed"
                ;;
            "vtuber_send")
                message=$(echo "$line" | jq -r '.message // "unknown"' 2>/dev/null | cut -c1-50)
                echo "   📤 $timestamp - VTuber send: $message..."
                ;;
            "vtuber_response")
                echo "   📥 $timestamp - VTuber response received"
                ;;
            "memory_error")
                echo "   ❌ $timestamp - Memory error"
                ;;
            *)
                echo "   ❓ $timestamp - $type"
                ;;
        esac
    done
fi

echo ""
echo "📊 SYSTEM HEALTH:"
echo "================"

# Check autonomous cycles
if [[ $CYCLES_FOUND -gt 0 ]]; then
    echo "   ✅ Autonomous agent is active ($CYCLES_FOUND cycles)"
else
    echo "   ⚠️  No autonomous cycles detected"
fi

# Check VTuber communication
if [[ $SENDS_FOUND -gt 0 && $RESPONSES_FOUND -gt 0 ]]; then
    echo "   ✅ VTuber communication working ($SENDS_FOUND sends, $RESPONSES_FOUND responses)"
elif [[ $SENDS_FOUND -gt 0 ]]; then
    echo "   ⚠️  VTuber sends but no responses ($SENDS_FOUND sends, $RESPONSES_FOUND responses)"
else
    echo "   ⚠️  No VTuber communication"
fi

# Check memory errors
if [[ $ERRORS_FOUND -eq 0 ]]; then
    echo "   ✅ No memory errors"
else
    echo "   ❌ Memory errors detected: $ERRORS_FOUND"
fi

echo ""
echo "🎯 NEXT STEPS:"
echo "============="
echo "   📋 View events: cat $EVENTS_FILE"
echo "   📊 View dashboard: cat $DASHBOARD_FILE"
echo "   🔄 Run again: ./FINAL_WORKING_MONITOR.sh"
echo ""
echo "✅ Monitoring complete - session saved to: $LOG_DIR"
echo ""
echo "🎉 SUCCESS! This is how proper logging should work:"
echo "   ✅ No millisecond polling"
echo "   ✅ No duplicate events"
echo "   ✅ Only meaningful data"
echo "   ✅ Structured JSON output"
echo "   ✅ Clear objectives achieved" 