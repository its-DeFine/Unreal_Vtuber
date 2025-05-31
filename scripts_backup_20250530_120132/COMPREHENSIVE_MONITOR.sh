#!/bin/bash

# =============================================================================
# COMPREHENSIVE AUTONOMOUS VTUBER MONITORING SYSTEM
# =============================================================================
# Enhanced monitoring that captures:
# 1. Paired autonomous input ↔ VTuber response
# 2. VTuber LLM response text
# 3. Tool usage tracking per iteration
# =============================================================================

set -euo pipefail

readonly SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"
readonly LOG_DIR="logs/comprehensive_monitoring/${SESSION_ID}"
readonly STRUCTURED_DIR="${LOG_DIR}/structured"
readonly RAW_DIR="${LOG_DIR}/raw"

mkdir -p "${STRUCTURED_DIR}" "${RAW_DIR}"

echo "🚀 COMPREHENSIVE AUTONOMOUS VTUBER MONITOR"
echo "=========================================="
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

# =============================================================================
# 1. EXTRACT AUTONOMOUS CYCLES WITH TOOL USAGE
# =============================================================================

echo "🔄 Extracting autonomous cycles with tool usage..."
CYCLES_FOUND=0

# Create temporary file for cycle analysis
CYCLE_TEMP="${RAW_DIR}/cycle_analysis.tmp"
> "$CYCLE_TEMP"

# Extract cycle information with context
while IFS= read -r line; do
    # Capture iteration starts
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*Starting\ autonomous\ loop\ iteration\ ([0-9]+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        iteration="${BASH_REMATCH[2]}"
        echo "CYCLE_START|$timestamp|$iteration" >> "$CYCLE_TEMP"
    fi
    
    # Capture iteration completions
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*iteration\ ([0-9]+)\ completed ]]; then
        timestamp="${BASH_REMATCH[1]}"
        iteration="${BASH_REMATCH[2]}"
        echo "CYCLE_END|$timestamp|$iteration" >> "$CYCLE_TEMP"
        
        # Add to events
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"autonomous_cycle_completed\",\"iteration\":$iteration,\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        ((CYCLES_FOUND++))
    fi
    
    # Capture tool executions
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*Executing\ action:\ ([A-Z_]+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        tool="${BASH_REMATCH[2]}"
        echo "TOOL_EXEC|$timestamp|$tool" >> "$CYCLE_TEMP"
    fi
    
    # Capture action selections
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*Selected\ action:\ ([A-Z_]+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        action="${BASH_REMATCH[2]}"
        echo "ACTION_SELECT|$timestamp|$action" >> "$CYCLE_TEMP"
    fi
    
    # Capture decision reasoning
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*Decision\ reasoning:\ (.+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        reasoning="${BASH_REMATCH[2]}"
        echo "REASONING|$timestamp|$reasoning" >> "$CYCLE_TEMP"
    fi
    
done < "$AUTONOMOUS_RAW"

echo "   ✅ Found $CYCLES_FOUND autonomous cycles"

# =============================================================================
# 2. EXTRACT VTUBER SENDS WITH CONTEXT
# =============================================================================

echo "📤 Extracting VTuber sends with context..."
SENDS_FOUND=0

while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*🎯\ SENDING\ TO\ VTUBER:\ \"(.+)\"\ at\ http ]]; then
        timestamp="${BASH_REMATCH[1]}"
        message="${BASH_REMATCH[2]}"
        
        # Extract the message without quotes
        clean_message=$(echo "$message" | sed 's/^"//;s/"$//')
        
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_send\",\"message\":\"$clean_message\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        echo "VTUBER_SEND|$timestamp|$clean_message" >> "$CYCLE_TEMP"
        ((SENDS_FOUND++))
    fi
done < "$AUTONOMOUS_RAW"

echo "   ✅ Found $SENDS_FOUND VTuber sends"

# =============================================================================
# 3. EXTRACT VTUBER RESPONSES (FROM AUTONOMOUS LOGS)
# =============================================================================

echo "📥 Extracting VTuber responses..."
RESPONSES_FOUND=0

while IFS= read -r line; do
    if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*✅\ VTUBER\ RESPONSE\ RECEIVED:\ (.+) ]]; then
        timestamp="${BASH_REMATCH[1]}"
        response_data="${BASH_REMATCH[2]}"
        
        echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_response_received\",\"response_data\":\"$response_data\",\"session\":\"$SESSION_ID\"}" >> "$EVENTS_FILE"
        echo "VTUBER_RESPONSE|$timestamp|$response_data" >> "$CYCLE_TEMP"
        ((RESPONSES_FOUND++))
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
        # Look for enhanced VTuber processing logs
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ 🧠\ LLM\ RESPONSE:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            llm_response="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_llm_response\",\"llm_text\":\"$llm_response\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            echo "LLM_RESPONSE|$timestamp|$llm_response" >> "$CYCLE_TEMP"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Look for processed text patterns
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ 📝\ PROCESSED\ TEXT:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            processed_text="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_processed_text\",\"processed_text\":\"$processed_text\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Look for speech generation
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ 🎤\ SPEECH\ GENERATION\ QUEUED:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            speech_text="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_speech_generated\",\"speech_text\":\"$speech_text\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Look for emotion detection
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ 😊\ EMOTION\ DETECTED:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            emotion="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_emotion_detected\",\"emotion\":\"$emotion\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Look for processing completion
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ ✅\ PROCESSING\ COMPLETED\ in\ ([0-9.]+)s ]]; then
            timestamp="${BASH_REMATCH[1]}"
            duration="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_processing_completed\",\"duration_seconds\":\"$duration\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Look for input received
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*\[VTuberProcessing\]\ 📥\ RECEIVED\ INPUT:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            input_text="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_input_received\",\"input_text\":\"$input_text\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            echo "VTUBER_INPUT|$timestamp|$input_text" >> "$CYCLE_TEMP"
            ((LLM_RESPONSES_FOUND++))
        fi
        
        # Legacy patterns for backward compatibility
        if [[ $line =~ \[([0-9-]+\ [0-9:]+)\].*LLM\ response:\ (.+) ]]; then
            timestamp="${BASH_REMATCH[1]}"
            llm_response="${BASH_REMATCH[2]}"
            
            echo "{\"timestamp\":\"$timestamp\",\"type\":\"vtuber_llm_response_legacy\",\"llm_text\":\"$llm_response\",\"session\":\"$SESSION_ID\"}" >> "$VTUBER_RESPONSES_FILE"
            echo "LLM_RESPONSE|$timestamp|$llm_response" >> "$CYCLE_TEMP"
            ((LLM_RESPONSES_FOUND++))
        fi
    done < "$VTUBER_RAW"
fi

echo "   ✅ Found $LLM_RESPONSES_FOUND VTuber LLM responses"

# =============================================================================
# 5. ANALYZE TOOL USAGE PER ITERATION
# =============================================================================

echo "🔧 Analyzing tool usage per iteration..."

# Sort cycle temp file by timestamp
sort "$CYCLE_TEMP" > "${CYCLE_TEMP}.sorted"

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
            if [[ "$data" == "$current_iteration" ]]; then
                iteration_end="$timestamp"
                
                # Create tool usage record
                tools_json=$(printf '%s\n' "${current_tools[@]}" | jq -R . | jq -s .)
                echo "{\"iteration\":$current_iteration,\"start_time\":\"$iteration_start\",\"end_time\":\"$iteration_end\",\"tools_used\":$tools_json,\"session\":\"$SESSION_ID\"}" >> "$TOOLS_FILE"
            fi
            ;;
        "TOOL_EXEC"|"ACTION_SELECT")
            if [[ -n "$current_iteration" ]]; then
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

# Create pairs by matching timestamps (within 5 seconds)
PAIRS_FOUND=0

while IFS='|' read -r event_type timestamp data; do
    if [[ "$event_type" == "VTUBER_SEND" ]]; then
        send_timestamp="$timestamp"
        send_message="$data"
        
        # Look for corresponding VTuber response within 10 seconds
        send_epoch=$(date -d "$send_timestamp" +%s)
        
        while IFS='|' read -r resp_event resp_timestamp resp_data; do
            if [[ "$resp_event" == "VTUBER_RESPONSE" ]]; then
                resp_epoch=$(date -d "$resp_timestamp" +%s)
                time_diff=$((resp_epoch - send_epoch))
                
                # If response is within 10 seconds after send
                if [[ $time_diff -ge 0 && $time_diff -le 10 ]]; then
                    echo "{\"send_timestamp\":\"$send_timestamp\",\"response_timestamp\":\"$resp_timestamp\",\"autonomous_message\":\"$send_message\",\"vtuber_response\":\"$resp_data\",\"response_delay_seconds\":$time_diff,\"session\":\"$SESSION_ID\"}" >> "$PAIRS_FILE"
                    ((PAIRS_FOUND++))
                    break
                fi
            fi
        done < "${CYCLE_TEMP}.sorted"
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

# =============================================================================
# 8. DISPLAY RESULTS
# =============================================================================

clear
cat "$DASHBOARD_FILE"

# Show recent autonomous-VTuber pairs
if [[ -f "$PAIRS_FILE" && -s "$PAIRS_FILE" ]]; then
    echo ""
    echo "🔗 RECENT AUTONOMOUS-VTUBER PAIRS:"
    echo "=================================="
    tail -5 "$PAIRS_FILE" | while IFS= read -r line; do
        send_time=$(echo "$line" | jq -r '.send_timestamp // "unknown"')
        resp_time=$(echo "$line" | jq -r '.response_timestamp // "unknown"')
        message=$(echo "$line" | jq -r '.autonomous_message // "unknown"' | cut -c1-40)
        delay=$(echo "$line" | jq -r '.response_delay_seconds // "?"')
        echo "   📤➡️📥 $send_time → $resp_time (${delay}s delay)"
        echo "        Message: $message..."
    done
fi

# Show recent tool usage
if [[ -f "$TOOLS_FILE" && -s "$TOOLS_FILE" ]]; then
    echo ""
    echo "🔧 RECENT TOOL USAGE:"
    echo "===================="
    tail -5 "$TOOLS_FILE" | while IFS= read -r line; do
        iteration=$(echo "$line" | jq -r '.iteration // "?"')
        tools=$(echo "$line" | jq -r '.tools_used[] // "none"' | tr '\n' ', ' | sed 's/,$//')
        start_time=$(echo "$line" | jq -r '.start_time // "unknown"')
        echo "   🔄 Iteration $iteration ($start_time): $tools"
    done
fi

# Show recent VTuber LLM responses
if [[ -f "$VTUBER_RESPONSES_FILE" && -s "$VTUBER_RESPONSES_FILE" ]]; then
    echo ""
    echo "🧠 RECENT VTUBER LLM RESPONSES:"
    echo "=============================="
    tail -3 "$VTUBER_RESPONSES_FILE" | while IFS= read -r line; do
        timestamp=$(echo "$line" | jq -r '.timestamp // "unknown"')
        type=$(echo "$line" | jq -r '.type // "unknown"')
        text=$(echo "$line" | jq -r '.llm_text // .processed_text // .speech_text // "unknown"' | cut -c1-60)
        echo "   🧠 $timestamp ($type): $text..."
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

# Check VTuber communication pairing
if [[ $PAIRS_FOUND -gt 0 ]]; then
    echo "   ✅ Autonomous-VTuber communication paired ($PAIRS_FOUND pairs)"
elif [[ $SENDS_FOUND -gt 0 ]]; then
    echo "   ⚠️  VTuber sends but no paired responses ($SENDS_FOUND sends, $RESPONSES_FOUND responses)"
else
    echo "   ⚠️  No VTuber communication"
fi

# Check tool usage tracking
if [[ $TOOL_RECORDS -gt 0 ]]; then
    echo "   ✅ Tool usage tracked ($TOOL_RECORDS iterations)"
else
    echo "   ⚠️  No tool usage data"
fi

# Check VTuber LLM responses
if [[ $LLM_RESPONSES_FOUND -gt 0 ]]; then
    echo "   ✅ VTuber LLM responses captured ($LLM_RESPONSES_FOUND responses)"
else
    echo "   ⚠️  No VTuber LLM responses detected"
fi

echo ""
echo "🎯 ANALYSIS COMMANDS:"
echo "===================="
echo "   🔗 View pairs: cat $PAIRS_FILE | jq ."
echo "   🔧 View tools: cat $TOOLS_FILE | jq ."
echo "   🧠 View LLM responses: cat $VTUBER_RESPONSES_FILE | jq ."
echo "   📋 View all events: cat $EVENTS_FILE | jq ."
echo ""
echo "✅ Comprehensive monitoring complete - session saved to: $LOG_DIR"
echo ""
echo "🎉 ENHANCED FEATURES:"
echo "   ✅ Autonomous-VTuber pairs tracked"
echo "   ✅ VTuber LLM responses captured"
echo "   ✅ Tool usage per iteration recorded"
echo "   ✅ Complete communication pipeline monitored"

# Cleanup
rm -f "${CYCLE_TEMP}" "${CYCLE_TEMP}.sorted" 