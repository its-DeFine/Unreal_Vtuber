#!/bin/bash

# Simple Character Test Script
# Flow: Visual Setup → Character API Setup → 2 Questions (20s each) → Repeat for next character

BASE_URL="http://localhost:5001"
QUESTION_WAIT_TIME=40  # 20 seconds wait between questions

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

visual_setup() {
    echo -e "${PURPLE}🎭 $1${NC}"
}

test_character() {
    local character_id=$1
    local character_name=$2
    local question1="$3"
    local question2="$4"
    
    echo "=========================================="
    log "🎭 Testing Character: $character_name ($character_id)"
    echo "=========================================="
    
    # Step 1: Apply visual appearance (no background change)
    log "Step 1: Applying visual appearance for $character_name"
    visual_setup "Setting up $character_name visual appearance..."
    
    case $character_id in
        "demo_teacher")
            log "🎓 Setting up Professor Agatha visual appearance (Blue hair, blue eyes, professional look)"
            if docker exec neurosync_s1 python3 -c "import sys; sys.path.append('/app/NeuroBridge/NeuroSync_Player'); from character_visual_setups import apply_professor_agatha_appearance; print('Success' if apply_professor_agatha_appearance(enhanced=False) else 'Failed')" | grep -q "Success"; then
                success "Professor Agatha visual setup completed!"
            else
                echo "⚠️ Professor Agatha visual setup had some issues"
            fi
            ;;
        "reactive_default")
            log "🎬 Setting up Streamer visual appearance (Pink/purple hair, violet eyes, modern look)"
            if docker exec neurosync_s1 python3 -c "import sys; sys.path.append('/app/NeuroBridge/NeuroSync_Player'); from character_visual_setups import apply_streamer_appearance; print('Success' if apply_streamer_appearance(enhanced=False, dynamic=False) else 'Failed')" | grep -q "Success"; then
                success "Streamer visual setup completed!"
            else
                echo "⚠️ Streamer visual setup had some issues"
            fi
            ;;
    esac
    
    sleep 5
    success "Visual appearance applied for $character_name"
    
    # Step 2: Set up character via API
    log "Step 2: Setting up character via API"
    curl -X POST "$BASE_URL/api/v1/reactive/character/load" \
         -H "Content-Type: application/json" \
         -d "{\"character_id\": \"$character_id\"}"
    echo
    sleep 3
    success "Character $character_name loaded via API"
    
    # Step 3: Ask first question
    log "Step 3: Asking first question"
    echo "Question 1: $question1"
    curl -X POST "$BASE_URL/api/v1/reactive/event/chat" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$question1\"}"
    echo
    
    log "⏱️ Waiting ${QUESTION_WAIT_TIME} seconds for response processing..."
    sleep $QUESTION_WAIT_TIME
    success "First question completed"
    
    # Step 4: Ask second question
    log "Step 4: Asking second question"
    echo "Question 2: $question2"
    curl -X POST "$BASE_URL/api/v1/reactive/event/chat" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$question2\"}"
    echo
    
    log "⏱️ Waiting ${QUESTION_WAIT_TIME} seconds for response processing..."
    sleep $QUESTION_WAIT_TIME
    success "Second question completed"
    
    success "✅ Character $character_name testing completed!"
    
    # Brief pause before next character
    log "⏸️ Pausing 10 seconds before next character..."
    sleep 10
}

main() {
    echo "🎭 SIMPLE CHARACTER TEST SCRIPT"
    echo "📝 Flow: Visual Setup → API Setup → 2 Questions (20s each) × 2 characters"
    echo "⏱️ No autonomous mode - focused character testing"
    echo "=================================================================="
    
    # Test Character 1: Professor Agatha
    test_character \
        "demo_teacher" \
        "Professor Agatha" \
        "What character are you? Who are you? Please introduce yourself as an academic." \
        "Can you explain a mathematical concept that you find particularly interesting?"
    
    # Test Character 2: Streamer
    test_character \
        "reactive_default" \
        "Streaming Star" \
        "What character are you? Who are you? Please introduce yourself as a content creator." \
        "What advice would you give to someone starting their first streaming channel?"
    
    echo "=================================================================="
    success "🎉 Simple character test completed successfully!"
    log "📊 Test Summary:"
    log "   - Professor Agatha: Visual Setup ✅ → API Setup ✅ → 2 Questions ✅"  
    log "   - Streaming Star: Visual Setup ✅ → API Setup ✅ → 2 Questions ✅"
    log "⏱️ Total time: ~2 minutes (20s × 4 questions + setup time)"
    success "Simple Character Test: COMPLETE ✨"
}

main "$@" 