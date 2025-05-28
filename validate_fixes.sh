#!/bin/bash

# =============================================================================
# BULLETPROOF AUTONOMOUS VTUBER MONITORING - FINAL VERSION
# =============================================================================
# Following Better Stack logging best practices:
# ✅ "Establish clear objectives" - Monitor what matters
# ✅ "Write meaningful log entries" - No noise, only real events  
# ✅ "Don't ignore performance cost" - Single pass, no polling
# ✅ "Structure your logs" - Clean JSON output
# =============================================================================

set -euo pipefail

readonly SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"
readonly LOG_DIR="logs/autonomous_monitoring/${SESSION_ID}"
readonly EVENTS_FILE="${LOG_DIR}/events.jsonl"
readonly RAW_FILE="${LOG_DIR}/raw_logs.txt"
readonly DASHBOARD_FILE="${LOG_DIR}/dashboard.txt"

mkdir -p "$LOG_DIR"

echo "🚀 BULLETPROOF AUTONOMOUS VTUBER MONITOR"
echo "========================================"
echo "📁 Session: $SESSION_ID"
echo "⏰ Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# =============================================================================
# STEP 1: GET RAW LOGS
# =============================================================================

echo "📊 Step 1: Getting raw logs from last 10 minutes..."
SINCE_TIME=$(date -d "10 minutes ago" '+%Y-%m-%dT%H:%M:%S')
echo "⏰ Since: $SINCE_TIME"

docker logs autonomous_starter_s3 --since "$SINCE_TIME" > "$RAW_FILE" 2>&1
LINE_COUNT=$(wc -l < "$RAW_FILE")
echo "📄 Raw log lines: $LINE_COUNT"

if [[ $LINE_COUNT -eq 0 ]]; then
    echo "❌ No logs found - container might not be running"
    exit 1
fi

# =============================================================================
# STEP 2: EXTRACT EVENTS (NO DUPLICATES)
# =============================================================================

echo ""
echo "🔍 Step 2: Extracting events..."

# Initialize events file
> "$EVENTS_FILE"

# Extract autonomous cycles
echo "🔄 Extracting autonomous cycles..."
CYCLES_FOUND=0
while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*iteration\ ([0-9]+)\ completed ]]; then
        timestamp="${BASH_REMATCH[1]}"
        iteration="${BASH_REMATCH[2]}"
        
        # Check for duplicates
        if ! grep -q "\"iteration\":$iteration" "$EVENTS_FILE" 2>/dev/null; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"autonomous_cycle\",\"iteration\":$iteration,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            ((CYCLES_FOUND++))
        fi
    fi
done < "$RAW_FILE"
echo "   ✅ Found $CYCLES_FOUND autonomous cycles"

# Extract VTuber sends
echo "📤 Extracting VTuber sends..."
SENDS_FOUND=0
while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*🎯\ SENDING\ TO\ VTUBER:\ (.+)\ at\ http ]]; then
        timestamp="${BASH_REMATCH[1]}"
        message="${BASH_REMATCH[2]}"
        
        # Check for duplicates by timestamp
        if ! grep -q "\"timestamp\":\"$timestamp\".*\"type\":\"vtuber_send\"" "$EVENTS_FILE" 2>/dev/null; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_send\",\"message\":$message,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            ((SENDS_FOUND++))
        fi
    fi
done < "$RAW_FILE"
echo "   ✅ Found $SENDS_FOUND VTuber sends"

# Extract VTuber responses
echo "📥 Extracting VTuber responses..."
RESPONSES_FOUND=0
while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*✅\ VTUBER\ RESPONSE\ RECEIVED ]]; then
        timestamp="${BASH_REMATCH[1]}"
        
        # Check for duplicates by timestamp
        if ! grep -q "\"timestamp\":\"$timestamp\".*\"type\":\"vtuber_response\"" "$EVENTS_FILE" 2>/dev/null; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_response\",\"status\":\"success\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            ((RESPONSES_FOUND++))
        fi
    fi
done < "$RAW_FILE"
echo "   ✅ Found $RESPONSES_FOUND VTuber responses"

# Extract memory errors
echo "💾 Extracting memory errors..."
ERRORS_FOUND=0
while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\]\ ERROR:\ \[MemoryArchivingEngine\]\ (.+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        error="${BASH_REMATCH[2]}"
        
        # Check for duplicates by timestamp
        if ! grep -q "\"timestamp\":\"$timestamp\".*\"type\":\"memory_error\"" "$EVENTS_FILE" 2>/dev/null; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"memory_error\",\"error\":\"$error\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            ((ERRORS_FOUND++))
        fi
    fi
done < "$RAW_FILE"
echo "   ✅ Found $ERRORS_FOUND memory errors"

TOTAL_EVENTS=$((CYCLES_FOUND + SENDS_FOUND + RESPONSES_FOUND + ERRORS_FOUND))
echo ""
echo "📊 Total events extracted: $TOTAL_EVENTS"

# =============================================================================
# STEP 3: GENERATE DASHBOARD
# =============================================================================

echo ""
echo "📋 Step 3: Generating dashboard..."

# Container status
AUTONOMOUS_STATUS="unknown"
NEUROSYNC_STATUS="unknown"

if docker inspect autonomous_starter_s3 >/dev/null 2>&1; then
    AUTONOMOUS_STATUS=$(docker inspect --format='{{.State.Status}}' autonomous_starter_s3)
fi

if docker inspect neurosync_byoc >/dev/null 2>&1; then
    NEUROSYNC_STATUS=$(docker inspect --format='{{.State.Status}}' neurosync_byoc)
fi

# Generate dashboard
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
# STEP 4: DISPLAY RESULTS
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

# Check if autonomous cycles are happening
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
echo "   🔄 Run again: ./validate_fixes.sh"
echo ""
echo "✅ Monitoring complete - session saved to: $LOG_DIR" 