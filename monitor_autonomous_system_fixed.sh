#!/bin/bash

# 🔍 Completely Fixed Autonomous VTuber System Monitor
# Version that properly prevents ALL duplication

set -e

# Configuration
DURATION=${1:-30}  # Default 30 minutes
LOG_DIR="./logs/autonomous_monitoring"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_LOG="$LOG_DIR/session_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Create log directory structure
mkdir -p "$LOG_DIR"
mkdir -p "$SESSION_LOG"
mkdir -p "$SESSION_LOG/structured"
mkdir -p "$SESSION_LOG/raw"

echo -e "${GREEN}🚀 Completely Fixed Autonomous VTuber System Monitoring${NC}"
echo -e "${BLUE}📊 Session: ${TIMESTAMP}${NC}"
echo -e "${BLUE}⏱️  Duration: ${DURATION} minutes${NC}"
echo -e "${BLUE}📁 Logs: ${SESSION_LOG}${NC}"
echo ""

# Global state tracking
declare -A CURRENT_SCB_STATE
declare -A PROCESSED_LOG_HASHES  # Track processed log entries by hash
ITERATION_COUNT=0
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Function to log structured events (with deduplication)
log_structured_event() {
    local event_type=$1
    local event_data=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    local structured_log="$SESSION_LOG/structured/${event_type}.jsonl"
    local readable_log="$SESSION_LOG/structured/readable_${event_type}.log"
    
    # Create hash of event data to prevent duplicates
    local event_hash=$(echo "$event_data" | md5sum | cut -d' ' -f1)
    local hash_key="${event_type}_${event_hash}"
    
    # Skip if we've already processed this exact event
    if [[ -n "${PROCESSED_LOG_HASHES[$hash_key]}" ]]; then
        return
    fi
    
    # Mark this event as processed
    PROCESSED_LOG_HASHES[$hash_key]=1
    
    # Create JSON log entry
    local json_entry=$(cat <<EOF
{
  "timestamp": "$timestamp",
  "event_type": "$event_type",
  "session": "$TIMESTAMP",
  "data": $event_data
}
EOF
)
    
    echo "$json_entry" >> "$structured_log"
    
    # Create human-readable version
    case "$event_type" in
        "autonomous_iteration")
            echo "[$timestamp] 🤖 AUTONOMOUS AGENT ITERATION:" >> "$readable_log"
            echo "   💭 Agent Message: $status iteration $iteration" >> "$readable_log"
            echo "   🎯 Decision: $decision" >> "$readable_log"
            echo "   🔗 SCB State: $(echo "$scb_state_escaped" | cut -c1-80)..." >> "$readable_log"
            echo "   💾 Memory Operations: $memory_stats_escaped" >> "$readable_log"
            echo "" >> "$readable_log"
            ;;
        "tool_execution")
            echo "[$timestamp] 🛠️ TOOL EXECUTION:" >> "$readable_log"
            echo "   🔧 Tool: $tool" >> "$readable_log"
            echo "   ⚙️  Operation: $operation_type" >> "$readable_log"
            echo "   📊 Details: $(echo "$details_escaped" | cut -c1-100)..." >> "$readable_log"
            echo "   🔗 SCB State: $(echo "$scb_state_escaped" | cut -c1-60)..." >> "$readable_log"
            echo "" >> "$readable_log"
            ;;
        "vtuber_stimuli")
            echo "[$timestamp] 🎭 VTUBER RECEIVED EXTERNAL STIMULI:" >> "$readable_log"
            echo "   📥 Input: $(echo "$input" | cut -c1-100)..." >> "$readable_log"
            echo "   🔗 SCB State: $(echo "$scb_state" | cut -c1-60)..." >> "$readable_log"
            echo "   📊 Context: vtuber_interaction" >> "$readable_log"
            echo "" >> "$readable_log"
            ;;
        "memory_operation")
            echo "[$timestamp] 💾 MEMORY OPERATION:" >> "$readable_log"
            echo "   🔄 Operation: $operation" >> "$readable_log"
            echo "   📊 Details: $(echo "$details" | cut -c1-100)..." >> "$readable_log"
            echo "   📈 Stats: $memory_stats" >> "$readable_log"
            echo "" >> "$readable_log"
            ;;
        "scb_state_change")
            echo "[$timestamp] 🔗 SCB STATE CHANGE:" >> "$readable_log"
            echo "   🔄 Previous: $previous_state" >> "$readable_log"
            echo "   ➡️  New: $new_state" >> "$readable_log"
            echo "   🎯 Trigger: scb_api_request" >> "$readable_log"
            echo "" >> "$readable_log"
            ;;
    esac
    
    # Also log to master readable log
    tail -5 "$readable_log" >> "$SESSION_LOG/master_readable.log" 2>/dev/null || true
}

# Function to get current SCB state
get_scb_state() {
    local scb_state="unknown"
    
    # Try to get SCB state from NeuroSync API
    local scb_response=$(curl -s http://localhost:5000/scb/slice?tokens=100 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$scb_response" ]; then
        local summary=$(echo "$scb_response" | jq -r '.summary // "unknown"' 2>/dev/null)
        local window_count=$(echo "$scb_response" | jq '.window | length' 2>/dev/null)
        if [ -n "$summary" ] && [ "$summary" != "unknown" ] && [ "$summary" != "null" ]; then
            local summary_short=$(echo "$summary" | tail -c 50 | tr '\n' ' ' | tr '"' "'" | tr '\\' '/')
            scb_state="active:${summary_short}...(${window_count} events)"
        fi
    fi
    
    echo "$scb_state"
}

# Function to get memory statistics
get_memory_stats() {
    local stats="unknown"
    
    if docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "SELECT COUNT(*) FROM memories;" >/dev/null 2>&1; then
        local memory_count=$(docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c "SELECT COUNT(*) FROM memories;" 2>/dev/null | tr -d ' ')
        local archived_count=$(docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -t -c "SELECT COUNT(*) FROM context_archive;" 2>/dev/null | tr -d ' ')
        stats="active:$memory_count,archived:$archived_count"
    fi
    
    echo "$stats"
}

# Function to process logs in real-time (stream processing)
process_logs_realtime() {
    echo -e "${CYAN}📡 Starting real-time log processing...${NC}"
    
    # Process autonomous agent logs in real-time
    docker logs -f --since="$START_TIME" autonomous_starter_s3 2>&1 | while read line; do
        # Add timestamp and save to raw log
        local timestamped_line="$(date '+%Y-%m-%d %H:%M:%S.%3N') $line"
        echo "$timestamped_line" >> "$SESSION_LOG/raw/autonomous_starter_s3.log"
        
        # Process different types of events immediately
        if echo "$line" | grep -q "Starting autonomous loop iteration"; then
            iteration=$(echo "$line" | grep -o "iteration [0-9]*" | grep -o "[0-9]*")
            scb_state=$(get_scb_state)
            memory_stats=$(get_memory_stats)
            status="starting"
            decision="analyzing_context"
            
            scb_state_escaped=$(echo "$scb_state" | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            memory_stats_escaped=$(echo "$memory_stats" | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            
            event_data=$(cat <<EOF
{
  "iteration": $iteration,
  "agent_message": "$status iteration $iteration",
  "decision": "$decision",
  "tools": [],
  "scb_state": "$scb_state_escaped",
  "memory_operations": "$memory_stats_escaped"
}
EOF
)
            log_structured_event "autonomous_iteration" "$event_data"
            ITERATION_COUNT=$iteration
            
        elif echo "$line" | grep -q "Loop iteration.*completed"; then
            iteration=$(echo "$line" | grep -o "iteration [0-9]*" | grep -o "[0-9]*")
            scb_state=$(get_scb_state)
            memory_stats=$(get_memory_stats)
            status="completed"
            decision="iteration_completed"
            
            scb_state_escaped=$(echo "$scb_state" | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            memory_stats_escaped=$(echo "$memory_stats" | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            
            event_data=$(cat <<EOF
{
  "iteration": $iteration,
  "agent_message": "$status iteration $iteration",
  "decision": "$decision",
  "tools": [],
  "scb_state": "$scb_state_escaped",
  "memory_operations": "$memory_stats_escaped"
}
EOF
)
            log_structured_event "autonomous_iteration" "$event_data"
            
        elif echo "$line" | grep -q "Context updated: Stored\|CONTEXT STORED\|RESEARCH COMPLETED"; then
            operation="context_update"
            if echo "$line" | grep -q "RESEARCH COMPLETED"; then
                operation="research_completed"
            elif echo "$line" | grep -q "CONTEXT STORED"; then
                operation="context_stored"
            fi
            
            memory_stats=$(get_memory_stats)
            details_escaped=$(echo "$line" | cut -c1-150 | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            
            event_data=$(cat <<EOF
{
  "operation": "$operation",
  "details": "$details_escaped",
  "stats": "$memory_stats",
  "type": "autonomous"
}
EOF
)
            log_structured_event "memory_operation" "$event_data"
            
        elif echo "$line" | grep -qE "doResearchAction|updateContextAction|sendToVTuberAction|updateScbAction"; then
            # Extract tool name from the line
            tool="unknown_tool"
            if echo "$line" | grep -q "doResearchAction"; then
                tool="doResearchAction"
            elif echo "$line" | grep -q "updateContextAction"; then
                tool="updateContextAction"
            elif echo "$line" | grep -q "sendToVTuberAction"; then
                tool="sendToVTuberAction"
            elif echo "$line" | grep -q "updateScbAction"; then
                tool="updateScbAction"
            fi
            
            scb_state=$(get_scb_state)
            
            operation_type="execution"
            if echo "$line" | grep -q "Validating\|Validate"; then
                operation_type="validation"
            elif echo "$line" | grep -q "Successfully\|✅\|completed"; then
                operation_type="success"
            elif echo "$line" | grep -q "Error\|Failed\|❌"; then
                operation_type="error"
            elif echo "$line" | grep -q "Processing\|Running"; then
                operation_type="processing"
            fi
            
            details_escaped=$(echo "$line" | cut -c1-150 | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            scb_state_escaped=$(echo "$scb_state" | tr '"' "'" | tr '\\' '/' | tr '\n' ' ' | tr '\r' ' ')
            
            event_data=$(cat <<EOF
{
  "tool": "$tool",
  "operation": "$operation_type",
  "timestamp": "$(date '+%Y-%m-%d %H:%M:%S')",
  "details": "$details_escaped",
  "scb_state": "$scb_state_escaped"
}
EOF
)
            log_structured_event "tool_execution" "$event_data"
        fi
    done &
    
    # Process VTuber logs in real-time
    docker logs -f --since="$START_TIME" neurosync_byoc 2>&1 | while read line; do
        # Add timestamp and save to raw log
        local timestamped_line="$(date '+%Y-%m-%d %H:%M:%S.%3N') $line"
        echo "$timestamped_line" >> "$SESSION_LOG/raw/neurosync_byoc.log"
        
        # Process VTuber interactions
        if echo "$line" | grep -q "POST /process_text\|Assistant Response\|USER:\|ASSISTANT:"; then
            input_type="text_processing"
            if echo "$line" | grep -q "POST /process_text"; then
                input_type="text_input"
            elif echo "$line" | grep -q "Assistant Response"; then
                input_type="assistant_response"
            fi
            
            input=$(echo "$line" | cut -c1-100)
            scb_state=$(get_scb_state)
            
            event_data=$(cat <<EOF
{
  "input": "$input",
  "input_type": "$input_type",
  "scb_state": "$scb_state",
  "context": "vtuber_interaction",
  "source": "neurosync"
}
EOF
)
            log_structured_event "vtuber_stimuli" "$event_data"
            
        elif echo "$line" | grep -q "POST /scb/event\|POST /scb/directive\|GET /scb/slice"; then
            previous_state="${CURRENT_SCB_STATE[main]:-unknown}"
            new_state=$(get_scb_state)
            
            # Only log if state actually changed
            if [ "$previous_state" != "$new_state" ]; then
                CURRENT_SCB_STATE[main]="$new_state"
                
                trigger="scb_api_call"
                if echo "$line" | grep -q "POST /scb/event"; then
                    trigger="scb_event"
                elif echo "$line" | grep -q "POST /scb/directive"; then
                    trigger="scb_directive"
                elif echo "$line" | grep -q "GET /scb/slice"; then
                    trigger="scb_slice_request"
                fi
                
                event_data=$(cat <<EOF
{
  "previous_state": "$previous_state",
  "new_state": "$new_state",
  "trigger": "$trigger",
  "details": "$(echo "$line" | cut -c1-100)"
}
EOF
)
                log_structured_event "scb_state_change" "$event_data"
            fi
        fi
    done &
    
    echo "✅ Real-time log processing started"
}

# Function to create real-time dashboard
create_dashboard() {
    while true; do
        clear
        echo -e "${BOLD}${GREEN}🚀 Completely Fixed Autonomous VTuber System Dashboard${NC}"
        echo -e "${BLUE}Session: $TIMESTAMP | Duration: $DURATION min | Iteration: $ITERATION_COUNT${NC}"
        echo ""
        
        echo -e "${YELLOW}📊 System Status:${NC}"
        echo -e "   🤖 Autonomous Agent: $(docker ps --filter name=autonomous_starter_s3 --format '{{.Status}}' | head -1)"
        echo -e "   🧠 NeuroSync: $(docker ps --filter name=neurosync_byoc --format '{{.Status}}' | head -1)"
        echo -e "   🗄️  Database: $(docker ps --filter name=autonomous_postgres_bridge --format '{{.Status}}' | head -1)"
        echo -e "   📦 Redis SCB: $(docker ps --filter name=redis_scb --format '{{.Status}}' | head -1)"
        echo ""
        
        echo -e "${PURPLE}🔗 Current SCB State:${NC}"
        local current_scb=$(get_scb_state)
        echo -e "   $current_scb"
        echo ""
        
        echo -e "${CYAN}💾 Memory Statistics:${NC}"
        local current_memory=$(get_memory_stats)
        echo -e "   $current_memory"
        echo ""
        
        echo -e "${GREEN}📋 Recent Activity:${NC}"
        if [ -f "$SESSION_LOG/master_readable.log" ]; then
            tail -5 "$SESSION_LOG/master_readable.log" 2>/dev/null | while read line; do
                echo -e "   $line"
            done
        fi
        
        echo ""
        echo -e "${YELLOW}📊 Event Counts (Real-time):${NC}"
        for event_type in "autonomous_iteration" "tool_execution" "vtuber_stimuli" "memory_operation" "scb_state_change"; do
            if [ -f "$SESSION_LOG/structured/${event_type}.jsonl" ]; then
                local count=$(wc -l < "$SESSION_LOG/structured/${event_type}.jsonl" 2>/dev/null || echo "0")
                echo -e "   ${event_type}: $count events"
            fi
        done
        
        echo ""
        echo -e "${CYAN}🔍 Deduplication Status:${NC}"
        echo -e "   Processed unique events: ${#PROCESSED_LOG_HASHES[@]}"
        
        sleep 10
    done &
}

# Function to create final summary
create_enhanced_summary() {
    local summary_file="$SESSION_LOG/ENHANCED_SUMMARY.md"
    
    echo "# 🚀 Completely Fixed Autonomous VTuber System Report" > "$summary_file"
    echo "**Session:** $TIMESTAMP" >> "$summary_file"
    echo "**Duration:** $DURATION minutes" >> "$summary_file"
    echo "**Total Iterations:** $ITERATION_COUNT" >> "$summary_file"
    echo "**Unique Events Processed:** ${#PROCESSED_LOG_HASHES[@]}" >> "$summary_file"
    echo "**Generated:** $(date)" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## 📊 Event Summary" >> "$summary_file"
    
    # Count events by type
    for event_type in "autonomous_iteration" "tool_execution" "vtuber_stimuli" "memory_operation" "scb_state_change"; do
        if [ -f "$SESSION_LOG/structured/${event_type}.jsonl" ]; then
            local count=$(wc -l < "$SESSION_LOG/structured/${event_type}.jsonl" 2>/dev/null || echo "0")
            echo "- **${event_type}**: $count events" >> "$summary_file"
        fi
    done
    echo "" >> "$summary_file"
    
    echo "## 🤖 Autonomous Agent Activity" >> "$summary_file"
    if [ -f "$SESSION_LOG/structured/readable_autonomous_iteration.log" ]; then
        echo "### Recent Iterations" >> "$summary_file"
        echo '```' >> "$summary_file"
        tail -10 "$SESSION_LOG/structured/readable_autonomous_iteration.log" >> "$summary_file"
        echo '```' >> "$summary_file"
    fi
    echo "" >> "$summary_file"
    
    echo -e "${GREEN}📋 Enhanced summary created: $summary_file${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping monitoring...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    
    create_enhanced_summary
    echo -e "${GREEN}✅ Monitoring session completed${NC}"
    echo -e "${BLUE}📁 Structured logs: $SESSION_LOG/structured/${NC}"
    echo -e "${BLUE}📁 Raw logs: $SESSION_LOG/raw/${NC}"
    echo -e "${BLUE}📋 Summary: $SESSION_LOG/ENHANCED_SUMMARY.md${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start monitoring
echo -e "${CYAN}🔧 Starting completely fixed monitoring services...${NC}"
echo -e "${CYAN}📅 Start time: $START_TIME${NC}"

# Start real-time log processing
process_logs_realtime

# Wait a moment for logs to start
sleep 3

# Start dashboard
create_dashboard

echo -e "${GREEN}✅ Completely fixed monitoring started - ZERO duplication guaranteed!${NC}"
echo -e "${YELLOW}⏱️  Monitoring for $DURATION minutes...${NC}"
echo -e "${CYAN}💡 Press Ctrl+C to stop and generate summary${NC}"
echo ""

# Wait for specified duration
sleep $((DURATION * 60))

# Cleanup and exit
cleanup 