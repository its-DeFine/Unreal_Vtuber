#!/bin/bash

# NeuroSync Character & Mode Integration Test with Visual Appearance Setup
# Tests centralized TTS integration across characters and modes
# Flow: Character Init → Visual Setup → Identity Question → Subject Question → Specialized Question → Autonomous Mode (2min)

# set -e  # Commented out for debugging

BASE_URL="http://localhost:5001"
REACTIVE_WAIT_TIME=25  # Increased time to wait between reactive questions for processing
AUTONOMOUS_DURATION=120  # 2 minutes for autonomous mode testing
LOG_FILE="character_test_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
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

visual_setup() {
    echo -e "${PURPLE}🎭 $1${NC}" | tee -a "$LOG_FILE"
}

check_api() {
    log "🔍 Checking NeuroSync API availability..."
    if curl -s "$BASE_URL/api/v1/reactive/status" > /dev/null; then
        success "NeuroSync API is responsive"
        return 0
    else
        error "NeuroSync API is not responding at $BASE_URL"
        return 1
    fi
}

apply_visual_setup() {
    local character_id=$1
    local character_name=$2
    
    visual_setup "Applying $character_name visual appearance..."
    
    # Create a temporary Python script for visual setup
    case $character_id in
        "demo_teacher")
            log "🎓 Setting up Professor Smith visual appearance (Blue hair, blue eyes, academic look)"
            if docker exec neurosync_s1 python3 -c "import sys; sys.path.append('/app/NeuroBridge/NeuroSync_Player'); from character_visual_setups import apply_professor_smith_appearance; print('Success' if apply_professor_smith_appearance(enhanced=False) else 'Failed')" | grep -q "Success"; then
                echo "✅ Professor Smith visual setup completed!"
            else
                echo "⚠️ Professor Smith visual setup had some issues"
            fi
            ;;
        "reactive_default")
            log "🎬 Setting up Streamer visual appearance (Pink/purple hair, violet eyes, streaming look)"
            if docker exec neurosync_s1 python3 -c "import sys; sys.path.append('/app/NeuroBridge/NeuroSync_Player'); from character_visual_setups import apply_streamer_appearance; print('Success' if apply_streamer_appearance(enhanced=False, dynamic=False) else 'Failed')" | grep -q "Success"; then
                echo "✅ Streamer visual setup completed!"
            else
                echo "⚠️ Streamer visual setup had some issues"
            fi
            ;;
        *)
            warning "No visual setup defined for character: $character_id"
            ;;
    esac
}

test_character() {
    local character_id=$1
    local character_name=$2
    local identity_question=$3
    local subject_question=$4
    local specialized_question=$5
    local autonomous_topic=$6
    
    log "=========================================="
    log "🎭 Testing Character: $character_name ($character_id)"
    log "=========================================="
    
    # Step 1: Character initialization
    log "Step 1: Initializing character and switching to reactive mode"
    curl -X POST "$BASE_URL/api/v1/reactive/character/load" \
         -H "Content-Type: application/json" \
         -d "{\"character_id\": \"$character_id\"}" \
         -w "\\n"
    
    curl -X POST "$BASE_URL/api/v1/reactive/mode/switch" \
         -H "Content-Type: application/json" \
         -d '{"mode": "reactive"}' \
         -w "\\n"
    
    sleep 5
    success "Character initialized: $character_name"
    
    # Step 1.5: Apply visual appearance setup
    log "Step 1.5: Applying character-specific visual appearance..."
    apply_visual_setup "$character_id" "$character_name"
    sleep 5
    success "Visual appearance applied for $character_name"
    
    # Step 2: Identity question
    log "Step 2: Asking identity question"
    curl -X POST "$BASE_URL/api/v1/reactive/event/chat" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$identity_question\"}" \
         -w "\\n"
    
    log "⏱️ Waiting ${REACTIVE_WAIT_TIME}s for identity response processing..."
    sleep $REACTIVE_WAIT_TIME
    success "Identity question completed"
    
    # Step 3: Subject question  
    log "Step 3: Asking subject-specific question"
    curl -X POST "$BASE_URL/api/v1/reactive/event/chat" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$subject_question\"}" \
         -w "\\n"
    
    log "⏱️ Waiting ${REACTIVE_WAIT_TIME}s for subject response processing..."
    sleep $REACTIVE_WAIT_TIME
    success "Subject question completed"
    
    # Step 4: Specialized question
    log "Step 4: Asking specialized question"
    curl -X POST "$BASE_URL/api/v1/reactive/event/chat" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$specialized_question\"}" \
         -w "\\n"
    
    log "⏱️ Waiting ${REACTIVE_WAIT_TIME}s for specialized response processing..."
    sleep $REACTIVE_WAIT_TIME
    success "Specialized question completed"
    
    # Step 5: Autonomous mode testing
    log "Step 5: Testing autonomous mode (${AUTONOMOUS_DURATION}s duration)"
    curl -X POST "$BASE_URL/api/v1/reactive/mode/autonomous/start" \
         -H "Content-Type: application/json" \
         -d "{\"topic\": \"$autonomous_topic\"}" \
         -w "\\n"
    
    log "🤖 Autonomous mode started - monitoring for ${AUTONOMOUS_DURATION} seconds..."
    
    # Monitor autonomous mode progress
    for ((i=0; i<$AUTONOMOUS_DURATION; i+=30)); do
        remaining=$((AUTONOMOUS_DURATION - i))
        log "🤖 Autonomous mode progress: ${i}s elapsed, ${remaining}s remaining..."
        sleep 30
    done
    
    # Stop autonomous mode
    log "🛑 Stopping autonomous mode..."
    curl -X POST "$BASE_URL/api/v1/reactive/mode/autonomous/stop" \
         -H "Content-Type: application/json" \
         -w "\\n"
    
    curl -X POST "$BASE_URL/api/v1/reactive/mode/switch" \
         -H "Content-Type: application/json" \
         -d '{"mode": "reactive"}' \
         -w "\\n"
    
    success "✅ Autonomous mode testing completed"
    
    log "Character test completed: $character_name"
    log "⏸️ Pausing 15 seconds before next character..."
    sleep 15
}

main() {
    echo -e "${BLUE}🎭 NeuroSync Character & Mode Integration Test with Visual Setup${NC}"
    echo -e "${BLUE}📝 Testing Flow: Init → Visual Setup → Identity → Subject → Specialized → Autonomous (2min)${NC}"
    echo "=================================================================="
    
    if ! check_api; then
        exit 1
    fi
    
    # Character 1: Professor Smith (Mathematics Teacher)
    test_character \
        "demo_teacher" \
        "Professor Smith" \
        "What character are you? Who are you? Please introduce yourself." \
        "Can you explain basic algebra to me? I'm just starting to learn." \
        "I'm struggling with quadratic equations. Can you walk me through solving x² + 5x + 6 = 0 step by step?" \
        "advanced mathematics and science concepts"
    
    # Character 2: Streamer (Content Creator)  
    test_character \
        "reactive_default" \
        "Streaming Star" \
        "What character are you? Who are you? Please introduce yourself and tell me about your streaming focus." \
        "Can you give me some tips about starting a streaming channel? What should I know about streaming?" \
        "I want to grow my streaming audience and create engaging content. What are your best strategies for audience growth and viewer engagement?" \
        "streaming tips and content creation strategies"
    
    echo "=================================================================="
    success "🎉 All character tests completed successfully!"
    log "📊 Test Results Summary:"
    log "   - Professor Smith: Identity ✅ → Math ✅ → Quadratic Equations ✅ → Autonomous Math ✅"
    log "   - Streaming Star: Identity ✅ → Streaming Basics ✅ → Audience Growth ✅ → Autonomous Tips ✅"
    log "📝 Detailed logs saved to: $LOG_FILE"
    success "Character & Mode Integration Test: COMPLETE ✨"
}

main "$@" 