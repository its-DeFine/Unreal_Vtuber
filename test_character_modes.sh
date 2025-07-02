#!/bin/bash

# NeuroSync Character & Mode Integration Test
# Tests centralized TTS integration across characters and modes
# Flow: Character Init → Identity Question → Subject Question → Specialized Question

set -e

BASE_URL="http://localhost:5001"
WAIT_TIME=15  # Time to wait between questions for processing
LOG_FILE="character_test_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}" | tee -a "$LOG_FILE"
}

# Test configuration - Two characters with specific flow
declare -A TEST_CHARACTERS=(
    ["demo_teacher"]="Professor Smith"
    ["reactive_default"]="Reactive Assistant (Streamer)"
)

# Character-specific question flows
declare -A CHARACTER_FLOWS=(
    ["demo_teacher"]="mathematics"
    ["reactive_default"]="streaming"
)

# Identity questions for each character
declare -A IDENTITY_QUESTIONS=(
    ["demo_teacher"]="What character are you? Who are you? Please introduce yourself."
    ["reactive_default"]="What character are you? Who are you? Please introduce yourself as a streamer."
)

# First subject questions  
declare -A FIRST_QUESTIONS=(
    ["demo_teacher"]="Can you explain basic algebra to me? I'm just starting to learn."
    ["reactive_default"]="I'm new to streaming. What are the essential things I need to start streaming?"
)

# Specialized questions for each character
declare -A SPECIALIZED_QUESTIONS=(
    ["demo_teacher"]="I'm struggling with quadratic equations. Can you walk me through solving x² + 5x + 6 = 0 step by step?"
    ["reactive_default"]="I want to grow my Twitch audience and increase engagement. What specific strategies work best for small streamers?"
)

# API Helper Functions
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    log "API: $method $endpoint - $description"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -X GET "$BASE_URL$endpoint" | jq -r '.')
    else
        response=$(curl -s -X POST "$BASE_URL$endpoint" \
                   -H "Content-Type: application/json" \
                   -d "$data" | jq -r '.')
    fi
    
    if [[ $response == *"success"* ]] || [[ $response == *"character"* ]] || [[ $response == *"mode"* ]]; then
        success "$description completed"
        echo "$response" >> "$LOG_FILE"
        return 0
    else
        error "$description failed: $response"
        return 1
    fi
}

send_chat() {
    local message=$1
    local description=$2
    
    log "CHAT: $description"
    log "Message: $message"
    api_call "POST" "/api/v1/reactive/event/chat" "{\"message\": \"$message\"}" "$description"
}

load_character() {
    local char_id=$1
    local char_name=$2
    
    log "Loading character: $char_name ($char_id)"
    api_call "POST" "/api/v1/reactive/character/load" "{\"character_id\": \"$char_id\"}" "Load $char_name"
}

switch_to_reactive() {
    log "Switching to reactive mode"
    api_call "POST" "/api/v1/reactive/mode/switch" "{\"mode\": \"reactive\"}" "Switch to reactive mode"
}

get_status() {
    log "Getting system status"
    api_call "GET" "/api/v1/reactive/status" "" "Get system status"
}

wait_for_processing() {
    local seconds=$1
    local description=$2
    
    log "Waiting ${seconds}s for $description"
    sleep $seconds
    success "$description wait completed"
}

# Check container status
check_container() {
    log "Checking NeuroSync container status..."
    
    if ! docker ps | grep -q "neurosync_s1"; then
        error "NeuroSync container not running!"
        exit 1
    fi
    
    # Wait for API to be ready
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -s "$BASE_URL/api/v1/reactive/status" >/dev/null 2>&1; then
            success "NeuroSync API is ready"
            break
        fi
        
        warning "Waiting for NeuroSync API... (attempt $((retries+1))/10)"
        sleep 3
        ((retries++))
    done
    
    if [ $retries -eq 10 ]; then
        error "NeuroSync API not responding after 30 seconds"
        exit 1
    fi
}

# Test a single character with specific flow
test_character_flow() {
    local char_id=$1
    local char_name="${TEST_CHARACTERS[$char_id]}"
    local subject="${CHARACTER_FLOWS[$char_id]}"
    
    echo ""
    log "🎭 TESTING CHARACTER FLOW: $char_name ($char_id) - Subject: $subject"
    log "================================================================="
    
    # Step 1: Load character
    log "📋 STEP 1: Character Initialization"
    load_character "$char_id" "$char_name"
    switch_to_reactive
    wait_for_processing 3 "character initialization"
    
    # Step 2: Identity question
    log "🆔 STEP 2: Identity Question - 'Who are you?'"
    local identity_q="${IDENTITY_QUESTIONS[$char_id]}"
    send_chat "$identity_q" "Character identity question"
    wait_for_processing $WAIT_TIME "identity response and TTS"
    
    # Step 3: First subject question
    log "📚 STEP 3: First Subject Question ($subject)"
    local first_q="${FIRST_QUESTIONS[$char_id]}"
    send_chat "$first_q" "First subject question"
    wait_for_processing $WAIT_TIME "first subject response and TTS"
    
    # Step 4: Specialized question on the subject
    log "🎯 STEP 4: Specialized Question ($subject)"
    local specialized_q="${SPECIALIZED_QUESTIONS[$char_id]}"
    send_chat "$specialized_q" "Specialized subject question"
    wait_for_processing $WAIT_TIME "specialized response and TTS"
    
    success "Character flow completed: $char_name ($subject)"
    log "================================================================="
}

# Main test execution
main() {
    log "🚀 Starting NeuroSync Character Flow Test"
    log "Flow: Init → Identity → Subject → Specialized"
    log "Characters: Professor Smith (math) → Streamer (streaming)"
    log "Log file: $LOG_FILE"
    echo ""
    
    # Pre-test checks
    check_container
    get_status
    
    # Test each character in order
    for char_id in "demo_teacher" "reactive_default"; do
        test_character_flow "$char_id"
        
        # Brief pause between characters
        if [ "$char_id" = "demo_teacher" ]; then
            log "Pausing 10 seconds before next character..."
            sleep 10
        fi
    done
    
    # Final status check
    log "🏁 All character flows completed!"
    get_status
    
    # Summary
    echo ""
    log "📊 TEST SUMMARY"
    log "==============="
    log "Characters tested: ${#TEST_CHARACTERS[@]}"
    log "Flow per character: Init → Identity → Subject → Specialized"
    log "Total test time: ~$(( ($(date +%s) - start_time) / 60 )) minutes"
    log "Log file: $LOG_FILE"
    
    success "Character flow test completed successfully!"
    
    # Check TTS integration
    log "🔊 Checking TTS integration..."
    if docker logs neurosync_s1 2>/dev/null | grep -q "Audio generated successfully"; then
        success "TTS integration working - audio generated for responses!"
        log "TTS generations: $(docker logs neurosync_s1 2>/dev/null | grep -c 'Audio generated successfully')"
    else
        warning "No TTS audio generation found - check integration"
    fi
    
    echo ""
    log "To review full container logs: docker logs neurosync_s1"
    log "To review test logs: cat $LOG_FILE"
}

# Trap for cleanup
cleanup() {
    log "Cleaning up test environment..."
    switch_to_reactive 2>/dev/null || true
}

trap cleanup EXIT

# Record start time
start_time=$(date +%s)

# Run the main test
main "$@" 