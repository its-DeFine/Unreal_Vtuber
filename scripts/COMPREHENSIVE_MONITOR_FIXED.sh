#!/bin/bash

# =============================================================================
# COMPREHENSIVE AUTONOMOUS VTUBER MONITORING SYSTEM - FIXED VERSION
# =============================================================================
# This version handles both legacy and enhanced log formats
# =============================================================================

set -euo pipefail

readonly SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"
readonly LOG_DIR="logs/comprehensive_monitoring/${SESSION_ID}"
readonly STRUCTURED_DIR="${LOG_DIR}/structured"
readonly RAW_DIR="${LOG_DIR}/raw"

mkdir -p "${STRUCTURED_DIR}" "${RAW_DIR}"

echo "🚀 COMPREHENSIVE AUTONOMOUS VTUBER MONITOR (FIXED)"
echo "================================================="
echo "📁 Session: $SESSION_ID"
echo "⏰ Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# =============================================================================
# GET RAW LOGS FROM BOTH CONTAINERS
# =============================================================================

echo "📊 Getting raw logs from last 15 minutes..."
SINCE_TIME=$(date -d "15 minutes ago" '+%Y-%m-%dT%H:%M:%S')
echo "⏰ Since: $SINCE_TIME"

# Get autonomous agent logs
AUTONOMOUS_RAW="${RAW_DIR}/autonomous_raw.log"
docker logs autonomous_starter_s3 --since "$SINCE_TIME" > "$AUTONOMOUS_RAW" 2>&1

# Get VTuber logs
VTUBER_RAW="${RAW_DIR}/vtuber_raw.log"
docker logs neurosync_byoc --since "$SINCE_TIME" > "$VTUBER_RAW" 2>&1

AUTONOMOUS_LINES=$(wc -l < "$AUTONOMOUS_RAW")
VTUBER_LINES=$(wc -l < "$VTUBER_RAW")

echo "📄 Autonomous log lines: $AUTONOMOUS_LINES"
echo "📄 VTuber log lines: $VTUBER_LINES"

if [[ $AUTONOMOUS_LINES -eq 0 ]]; then
    echo "❌ No autonomous logs found - container might not be running"
    exit 1
fi

# =============================================================================
# DETECT LOG FORMAT
# =============================================================================

echo ""
echo "🔍 Detecting log format..."

# Check if we have enhanced logging
ENHANCED_LOGGING=false
if grep -q "🔄 Starting autonomous loop iteration" "$AUTONOMOUS_RAW" 2>/dev/null; then
    ENHANCED_LOGGING=true
    echo "✅ Enhanced logging detected"
else
    echo "⚠️  Legacy logging detected - using fallback patterns"
fi

# =============================================================================
# EXTRACT COMPREHENSIVE EVENTS
# =============================================================================

echo ""
echo "🔍 Extracting comprehensive events..."

EVENTS_FILE="${STRUCTURED_DIR}/comprehensive_events.jsonl"
PAIRS_FILE="${STRUCTURED_DIR}/autonomous_vtuber_pairs.jsonl"
TOOLS_FILE="${STRUCTURED_DIR}/tool_usage.jsonl"
VTUBER_RESPONSES_FILE="${STRUCTURED_DIR}/vtuber_llm_responses.jsonl"

> "$EVENTS_FILE"
> "$PAIRS_FILE"
> "$TOOLS_FILE"
> "$VTUBER_RESPONSES_FILE"

# Create temporary file for cycle analysis
CYCLE_TEMP="${RAW_DIR}/cycle_analysis.tmp"
> "$CYCLE_TEMP"

# =============================================================================
# 1. EXTRACT AUTONOMOUS CYCLES WITH TOOL USAGE
# =============================================================================

echo "🔄 Extracting autonomous cycles with tool usage..."
CYCLES_FOUND=0

# Extract cycle information with context
while IFS= read -r line; do
    # Enhanced format patterns
    if [[ $ENHANCED_LOGGING == true ]]; then
        # Capture iteration starts (enhanced)
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*🔄\ Starting\ autonomous\ loop\ iteration\ ([0-9]+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            iteration="${BASH_REMATCH[2]}"
            echo "CYCLE_START|$timestamp|$iteration" >> "$CYCLE_TEMP"
        fi
        
        # Capture iteration completions (enhanced)
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*✅\ Autonomous\ loop\ iteration\ ([0-9]+)\ completed ]]; then
            timestamp="${BASH_REMATCH[1]}"
            iteration="${BASH_REMATCH[2]}"
            echo "CYCLE_END|$timestamp|$iteration" >> "$CYCLE_TEMP"
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"autonomous_cycle_completed\",\"iteration\":$iteration,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            ((CYCLES_FOUND++))
        fi
    fi
    
    # Legacy format patterns (always check these)
    # Look for any iteration completion patterns
    if [[ $line =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}).*iteration[[:space:]]+([0-9]+)[[:space:]]+completed ]]; then
        timestamp="${BASH_REMATCH[1]}"
        iteration="${BASH_REMATCH[2]}"
        # Convert timestamp format if needed
        timestamp=$(echo "$timestamp" | sed 's/T/ /')
        echo "CYCLE_END|$timestamp|$iteration" >> "$CYCLE_TEMP"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"autonomous_cycle_completed\",\"iteration\":$iteration,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        ((CYCLES_FOUND++))
    fi
    
    # Capture tool/action executions (various formats)
    if [[ $line =~ Executing[[:space:]]+action:[[:space:]]+([A-Z_]+) ]]; then
        timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
        tool="${BASH_REMATCH[1]}"
        if [[ -n "$timestamp" ]]; then
            echo "TOOL_EXEC|$timestamp|$tool" >> "$CYCLE_TEMP"
        fi
    fi
    
    # Capture action selections
    if [[ $line =~ Selected[[:space:]]+action:[[:space:]]+([A-Z_]+) ]]; then
        timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
        action="${BASH_REMATCH[1]}"
        if [[ -n "$timestamp" ]]; then
            echo "ACTION_SELECT|$timestamp|$action" >> "$CYCLE_TEMP"
        fi
    fi
    
done < "$AUTONOMOUS_RAW"

echo "   ✅ Found $CYCLES_FOUND autonomous cycles"

# =============================================================================
# 2. EXTRACT VTUBER SENDS WITH CONTEXT
# =============================================================================

echo "📤 Extracting VTuber sends with context..."
SENDS_FOUND=0

while IFS= read -r line; do
    # Enhanced format
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*🎯\ SENDING\ TO\ VTUBER:\ \"(.+)\"\ at\ http ]]; then
        timestamp="${BASH_REMATCH[1]}"
        message="${BASH_REMATCH[2]}"
        clean_message=$(echo "$message" | sed 's/^"//;s/"$//')
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_send\",\"message\":\"$clean_message\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        echo "VTUBER_SEND|$timestamp|$clean_message" >> "$CYCLE_TEMP"
        ((SENDS_FOUND++))
    # Legacy format - look for sendToVTuber patterns
    elif [[ $line =~ sendToVTuberAction.*Handler.*processing.*message:.*\"(.+)\" ]] || 
         [[ $line =~ sendToVTuberAction.*message.*to.*send:.*\"(.+)\" ]]; then
        timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
        message="${BASH_REMATCH[1]}"
        if [[ -n "$timestamp" && -n "$message" ]]; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_send\",\"message\":\"$message\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            echo "VTUBER_SEND|$timestamp|$message" >> "$CYCLE_TEMP"
            ((SENDS_FOUND++))
        fi
    fi
done < "$AUTONOMOUS_RAW"

echo "   ✅ Found $SENDS_FOUND VTuber sends"

# =============================================================================
# 3. EXTRACT VTUBER RESPONSES (FROM AUTONOMOUS LOGS)
# =============================================================================

echo "📥 Extracting VTuber responses..."
RESPONSES_FOUND=0

while IFS= read -r line; do
    # Enhanced format
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*✅\ VTUBER\ RESPONSE\ RECEIVED:\ (.+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        response_data="${BASH_REMATCH[2]}"
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_response_received\",\"response_data\":\"$response_data\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        echo "VTUBER_RESPONSE|$timestamp|$response_data" >> "$CYCLE_TEMP"
        ((RESPONSES_FOUND++))
    # Legacy format - look for VTuber response patterns
    elif [[ $line =~ VTuber.*[Rr]esponse.*[Ss]tatus:.*200 ]] ||
         [[ $line =~ sendToVTuberAction.*Response.*Status:.*200 ]]; then
        timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
        if [[ -n "$timestamp" ]]; then
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_response_received\",\"response_data\":\"{status:200}\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
            echo "VTUBER_RESPONSE|$timestamp|{status:200}" >> "$CYCLE_TEMP"
            ((RESPONSES_FOUND++))
        fi
    fi
done < "$AUTONOMOUS_RAW"

echo "   ✅ Found $RESPONSES_FOUND VTuber responses"

# =============================================================================
# 4. EXTRACT VTUBER LLM RESPONSES (FROM VTUBER LOGS)
# =============================================================================

echo "🧠 Extracting VTuber LLM responses..."
LLM_RESPONSES_FOUND=0

if [[ -f "$VTUBER_RAW" && -s "$VTUBER_RAW" ]]; then
    while IFS= read -r line; do
        # Enhanced VTuber processing logs
        if [[ $line =~ \[VTuberProcessing\]\ 🧠\ LLM\ RESPONSE:\ (.+) ]]; then
            timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
            llm_response="${BASH_REMATCH[1]}"
            if [[ -n "$timestamp" ]]; then
                echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_llm_response\",\"llm_text\":\"$llm_response\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
                echo "LLM_RESPONSE|$timestamp|$llm_response" >> "$CYCLE_TEMP"
                ((LLM_RESPONSES_FOUND++))
            fi
        fi
        
        # Legacy patterns - look for any LLM response patterns
        if [[ $line =~ LLM[[:space:]]+response:\ (.+) ]] ||
           [[ $line =~ full_response.*=.*[\'\"](.+)[\'\"] ]]; then
            timestamp=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1 | sed 's/T/ /')
            llm_response="${BASH_REMATCH[1]}"
            if [[ -n "$timestamp" && -n "$llm_response" ]]; then
                echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_llm_response_legacy\",\"llm_text\":\"$llm_response\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
                echo "LLM_RESPONSE|$timestamp|$llm_response" >> "$CYCLE_TEMP"
                ((LLM_RESPONSES_FOUND++))
            fi
        fi
    done < "$VTUBER_RAW"
fi

echo "   ✅ Found $LLM_RESPONSES_FOUND VTuber LLM responses"

# =============================================================================
# 5. ANALYZE TOOL USAGE PER ITERATION
# =============================================================================

echo "🔧 Analyzing tool usage per iteration..."

# Sort cycle temp file by timestamp
sort "$CYCLE_TEMP" > "${CYCLE_TEMP}.sorted" 2>/dev/null || touch "${CYCLE_TEMP}.sorted"

current_iteration=""
current_tools=()
iteration_start=""
iteration_end=""

while IFS='|' read -r event_type timestamp data; do
    case "$event_type" in
        "CYCLE_START")
            current_iteration="$data"
            iteration_start="$timestamp"
            current_tools=()
            ;;
        "CYCLE_END")
            if [[ -n "$data" ]]; then
                iteration_end="$timestamp"
                
                # Create tool usage record if we have tools
                if [[ ${#current_tools[@]} -gt 0 ]]; then
                    tools_json=$(printf '%s\n' "${current_tools[@]}" | jq -R . | jq -s . 2>/dev/null || echo "[]")
                    echo "{\"iteration\":\"$data\",\"start_time\":\"$iteration_start\",\"end_time\":\"$iteration_end\",\"tools_used\":$tools_json,\"session\":\"$SESSION_ID\"}" >> "$TOOLS_FILE"
                fi
            fi
            ;;
        "TOOL_EXEC"|"ACTION_SELECT")
            if [[ -n "$data" ]]; then
                current_tools+=("$data")
            fi
            ;;
    esac
done < "${CYCLE_TEMP}.sorted"

TOOL_RECORDS=$(wc -l < "$TOOLS_FILE" 2>/dev/null || echo "0")
echo "   ✅ Created $TOOL_RECORDS tool usage records"

# =============================================================================
# 6. CREATE AUTONOMOUS-VTUBER PAIRS
# =============================================================================

echo "🔗 Creating autonomous-VTuber pairs..."
PAIRS_FOUND=0

# Create pairs by matching timestamps (within 10 seconds)
while IFS='|' read -r event_type timestamp data; do
    if [[ "$event_type" == "VTUBER_SEND" ]]; then
        send_timestamp="$timestamp"
        send_message="$data"
        
        # Look for corresponding VTuber response within 10 seconds
        send_epoch=$(date -d "$send_timestamp" +%s 2>/dev/null || echo "0")
        
        if [[ "$send_epoch" != "0" ]]; then
            while IFS='|' read -r resp_event resp_timestamp resp_data; do
                if [[ "$resp_event" == "VTUBER_RESPONSE" ]]; then
                    resp_epoch=$(date -d "$resp_timestamp" +%s 2>/dev/null || echo "0")
                    if [[ "$resp_epoch" != "0" ]]; then
                        time_diff=$((resp_epoch - send_epoch))
                        
                        # If response is within 10 seconds after send
                        if [[ $time_diff -ge 0 && $time_diff -le 10 ]]; then
                            echo "{\"send_timestamp\":\"$send_timestamp\",\"response_timestamp\":\"$resp_timestamp\",\"autonomous_message\":\"$send_message\",\"vtuber_response\":\"$resp_data\",\"response_delay_seconds\":$time_diff,\"session\":\"$SESSION_ID\"}" >> "$PAIRS_FILE"
                            ((PAIRS_FOUND++))
                            break
                        fi
                    fi
                fi
            done < "${CYCLE_TEMP}.sorted"
        fi
    fi
done < "${CYCLE_TEMP}.sorted"

echo "   ✅ Created $PAIRS_FOUND autonomous-VTuber pairs"

# =============================================================================
# 7. GENERATE COMPREHENSIVE DASHBOARD
# =============================================================================

echo ""
echo "📋 Generating comprehensive dashboard..."

# Container status
AUTONOMOUS_STATUS="unknown"
NEUROSYNC_STATUS="unknown"

if docker inspect autonomous_starter_s3 >/dev/null 2>&1; then
    AUTONOMOUS_STATUS=$(docker inspect --format='{{.State.Status}}' autonomous_starter_s3)
fi

if docker inspect neurosync_byoc >/dev/null 2>&1; then
    NEUROSYNC_STATUS=$(docker inspect --format='{{.State.Status}}' neurosync_byoc)
fi

DASHBOARD_FILE="${LOG_DIR}/comprehensive_dashboard.txt"
cat > "$DASHBOARD_FILE" << EOF
🚀 COMPREHENSIVE AUTONOMOUS VTUBER MONITOR
==========================================
Session: $SESSION_ID
Updated: $(date '+%Y-%m-%d %H:%M:%S')
Log Format: $(if [[ $ENHANCED_LOGGING == true ]]; then echo "Enhanced"; else echo "Legacy"; fi)

📊 CONTAINER STATUS:
   🤖 Autonomous Agent: $AUTONOMOUS_STATUS
   🧠 NeuroSync VTuber: $NEUROSYNC_STATUS

📈 COMPREHENSIVE EVENTS CAPTURED:
   🔄 Autonomous Cycles: $CYCLES_FOUND
   📤 VTuber Sends: $SENDS_FOUND
   📥 VTuber Responses: $RESPONSES_FOUND
   🧠 VTuber LLM Responses: $LLM_RESPONSES_FOUND
   🔗 Autonomous-VTuber Pairs: $PAIRS_FOUND
   🔧 Tool Usage Records: $TOOL_RECORDS

📁 STRUCTURED DATA FILES:
   📋 All Events: $EVENTS_FILE
   🔗 Paired Communications: $PAIRS_FILE
   🔧 Tool Usage: $TOOLS_FILE
   🧠 VTuber LLM Responses: $VTUBER_RESPONSES_FILE
   📄 Raw Logs: $RAW_DIR/

EOF

# Display results
clear
cat "$DASHBOARD_FILE"

# Show diagnostic info if no events found
if [[ $CYCLES_FOUND -eq 0 && $SENDS_FOUND -eq 0 && $RESPONSES_FOUND -eq 0 ]]; then
    echo ""
    echo "⚠️  NO EVENTS CAPTURED - DIAGNOSTICS:"
    echo "===================================="
    echo ""
    echo "1. Check if containers were rebuilt with enhanced logging:"
    echo "   docker-compose -f docker-compose.bridge.yml build autonomous_starter"
    echo "   docker-compose -f docker-compose.bridge.yml build neurosync"
    echo ""
    echo "2. Sample of autonomous logs:"
    head -5 "$AUTONOMOUS_RAW" 2>/dev/null | sed 's/^/   /'
    echo ""
    echo "3. Check for any iteration patterns:"
    grep -m 3 -i "iteration" "$AUTONOMOUS_RAW" 2>/dev/null | sed 's/^/   /' || echo "   No iteration patterns found"
    echo ""
fi

echo ""
echo "✅ Monitoring complete - session saved to: $LOG_DIR"

# Cleanup
rm -f "${CYCLE_TEMP}" "${CYCLE_TEMP}.sorted" 