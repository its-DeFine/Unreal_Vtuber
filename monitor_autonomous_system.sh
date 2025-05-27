#!/bin/bash

# 🔍 Autonomous VTuber System Monitor
# Comprehensive logging and monitoring for autonomous agent interactions
# Usage: ./monitor_autonomous_system.sh [duration_in_minutes]

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
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"
mkdir -p "$SESSION_LOG"

echo -e "${GREEN}🚀 Starting Autonomous VTuber System Monitoring${NC}"
echo -e "${BLUE}📊 Session: ${TIMESTAMP}${NC}"
echo -e "${BLUE}⏱️  Duration: ${DURATION} minutes${NC}"
echo -e "${BLUE}📁 Logs: ${SESSION_LOG}${NC}"
echo ""

# Function to log with timestamp
log_with_timestamp() {
    local service=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    mkdir -p "$SESSION_LOG"  # Ensure directory exists
    echo "[$timestamp] [$service] $message" | tee -a "$SESSION_LOG/master.log"
}

# Function to monitor container logs
monitor_container() {
    local container_name=$1
    local log_file="$SESSION_LOG/${container_name}.log"
    local filter_pattern=$2
    
    echo -e "${CYAN}📡 Monitoring $container_name...${NC}"
    
    if [ -n "$filter_pattern" ]; then
        docker logs -f "$container_name" 2>&1 | grep -E "$filter_pattern" | while read line; do
            echo "$(date '+%Y-%m-%d %H:%M:%S') $line" >> "$log_file"
            log_with_timestamp "$container_name" "$line"
        done &
    else
        docker logs -f "$container_name" 2>&1 | while read line; do
            echo "$(date '+%Y-%m-%d %H:%M:%S') $line" >> "$log_file"
        done &
    fi
}

# Function to monitor SCB interactions
monitor_scb() {
    local scb_log="$SESSION_LOG/scb_interactions.log"
    echo -e "${PURPLE}🔗 Monitoring SCB interactions...${NC}"
    
    while true; do
        # Check Redis for SCB updates
        docker exec redis_scb redis-cli --scan --pattern "*scb*" 2>/dev/null | while read key; do
            if [ -n "$key" ]; then
                value=$(docker exec redis_scb redis-cli get "$key" 2>/dev/null || echo "")
                if [ -n "$value" ]; then
                    log_with_timestamp "SCB" "Key: $key | Value: $value"
                    echo "$(date '+%Y-%m-%d %H:%M:%S') SCB_UPDATE: $key = $value" >> "$scb_log"
                fi
            fi
        done
        
        # Check NeuroSync SCB endpoint
        scb_status=$(curl -s http://localhost:5000/scb/status 2>/dev/null || echo "SCB endpoint unavailable")
        if [ "$scb_status" != "SCB endpoint unavailable" ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') SCB_STATUS: $scb_status" >> "$scb_log"
        fi
        
        sleep 5
    done &
}

# Function to monitor VTuber interactions
monitor_vtuber() {
    local vtuber_log="$SESSION_LOG/vtuber_interactions.log"
    echo -e "${YELLOW}🎭 Monitoring VTuber interactions...${NC}"
    
    while true; do
        # Monitor VTuber endpoint
        vtuber_status=$(curl -s http://localhost:5001/health 2>/dev/null || echo "VTuber endpoint unavailable")
        if [ "$vtuber_status" != "VTuber endpoint unavailable" ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') VTUBER_HEALTH: $vtuber_status" >> "$vtuber_log"
        fi
        
        sleep 10
    done &
}

# Function to analyze autonomous patterns
analyze_patterns() {
    local analysis_log="$SESSION_LOG/pattern_analysis.log"
    echo -e "${GREEN}🧠 Starting pattern analysis...${NC}"
    
    while true; do
        sleep 60  # Analyze every minute
        
        # Count autonomous loop iterations
        loop_count=$(grep -c "Loop iteration" "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null || echo "0")
        
        # Count VTuber interactions
        vtuber_count=$(grep -c "VTuber" "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null || echo "0")
        
        # Count SCB updates
        scb_count=$(grep -c "SCB" "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null || echo "0")
        
        # Count database operations
        db_count=$(grep -c "Database\|SQL\|postgres" "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null || echo "0")
        
        analysis_entry="ANALYSIS: Loops=$loop_count, VTuber=$vtuber_count, SCB=$scb_count, DB=$db_count"
        log_with_timestamp "ANALYZER" "$analysis_entry"
        echo "$(date '+%Y-%m-%d %H:%M:%S') $analysis_entry" >> "$analysis_log"
    done &
}

# Function to create summary report
create_summary() {
    local summary_file="$SESSION_LOG/SUMMARY_REPORT.md"
    
    echo "# Autonomous VTuber System Monitoring Report" > "$summary_file"
    echo "**Session:** $TIMESTAMP" >> "$summary_file"
    echo "**Duration:** $DURATION minutes" >> "$summary_file"
    echo "**Generated:** $(date)" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## 📊 System Status" >> "$summary_file"
    echo "### Container Status" >> "$summary_file"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(autonomous|neurosync|postgres|redis)" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## 🔄 Autonomous Agent Activity" >> "$summary_file"
    if [ -f "$SESSION_LOG/autonomous_starter_s3.log" ]; then
        echo "### Loop Iterations" >> "$summary_file"
        grep -c "Loop iteration" "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null >> "$summary_file" || echo "0" >> "$summary_file"
        
        echo "### Recent Actions" >> "$summary_file"
        echo '```' >> "$summary_file"
        tail -20 "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null >> "$summary_file" || echo "No logs available" >> "$summary_file"
        echo '```' >> "$summary_file"
    fi
    echo "" >> "$summary_file"
    
    echo "## 🎭 VTuber Interactions" >> "$summary_file"
    if [ -f "$SESSION_LOG/vtuber_interactions.log" ]; then
        echo "### Interaction Count" >> "$summary_file"
        wc -l < "$SESSION_LOG/vtuber_interactions.log" 2>/dev/null >> "$summary_file" || echo "0" >> "$summary_file"
    fi
    echo "" >> "$summary_file"
    
    echo "## 🔗 SCB Bridge Activity" >> "$summary_file"
    if [ -f "$SESSION_LOG/scb_interactions.log" ]; then
        echo "### SCB Updates" >> "$summary_file"
        wc -l < "$SESSION_LOG/scb_interactions.log" 2>/dev/null >> "$summary_file" || echo "0" >> "$summary_file"
    fi
    echo "" >> "$summary_file"
    
    echo "## 📁 Log Files Generated" >> "$summary_file"
    ls -la "$SESSION_LOG/" >> "$summary_file"
    
    echo -e "${GREEN}📋 Summary report created: $summary_file${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping monitoring...${NC}"
    jobs -p | xargs -r kill
    create_summary
    echo -e "${GREEN}✅ Monitoring session completed${NC}"
    echo -e "${BLUE}📁 All logs saved to: $SESSION_LOG${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start monitoring services
echo -e "${CYAN}🔧 Starting monitoring services...${NC}"

# Monitor key containers with specific filters
monitor_container "autonomous_starter_s3" "(Loop iteration|VTuber|SCB|Database|Starting autonomous|ERROR|WARN)"
monitor_container "neurosync_s1" "(SCB|VTuber|process_text|blendshapes|ERROR|WARN)"
monitor_container "autonomous_postgres_bridge" "(ERROR|WARN|ready)"
monitor_container "redis_scb" "(ERROR|WARN)"

# Start specialized monitoring
monitor_scb
monitor_vtuber
analyze_patterns

echo -e "${GREEN}✅ All monitoring services started${NC}"
echo -e "${YELLOW}⏱️  Monitoring for $DURATION minutes...${NC}"
echo -e "${CYAN}💡 Press Ctrl+C to stop monitoring early${NC}"
echo ""

# Show real-time status
while true; do
    echo -e "${BLUE}📊 Live Status ($(date '+%H:%M:%S')):${NC}"
    echo -e "   🤖 Autonomous Agent: $(docker ps --filter name=autonomous_starter_s3 --format '{{.Status}}' | head -1)"
    echo -e "   🧠 NeuroSync: $(docker ps --filter name=neurosync_s1 --format '{{.Status}}' | head -1)"
    echo -e "   🗄️  Database: $(docker ps --filter name=autonomous_postgres_bridge --format '{{.Status}}' | head -1)"
    echo -e "   📦 Redis: $(docker ps --filter name=redis_scb --format '{{.Status}}' | head -1)"
    
    # Show recent autonomous activity
    if [ -f "$SESSION_LOG/autonomous_starter_s3.log" ]; then
        recent_activity=$(tail -1 "$SESSION_LOG/autonomous_starter_s3.log" 2>/dev/null | cut -c1-80)
        if [ -n "$recent_activity" ]; then
            echo -e "   🔄 Latest: $recent_activity..."
        fi
    fi
    
    echo ""
    sleep 30
done &

# Wait for specified duration
sleep $((DURATION * 60))

# Cleanup and exit
cleanup 