#!/bin/bash

# Test script to verify Direct VTuber Integration
# This script monitors the autonomous system to ensure DIRECT_VTUBER_SPEECH is being called

echo "🧪 Testing Direct VTuber Integration"
echo "===================================="

# Configuration
DURATION=${1:-5}  # Default 5 minutes
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "📊 Test Duration: ${DURATION} minutes"
echo "🕐 Start Time: $(date)"
echo ""

# Check if containers are running
echo "🔍 Checking container status..."
if ! docker ps | grep -q "autonomous_starter"; then
    echo "❌ Autonomous starter container not running"
    exit 1
fi

if ! docker ps | grep -q "neurosync"; then
    echo "❌ NeuroSync container not running"
    exit 1
fi

echo "✅ All required containers are running"
echo ""

# Monitor for DIRECT_VTUBER_SPEECH actions
echo "🎯 Monitoring for DIRECT_VTUBER_SPEECH actions..."
echo "Expected: At least 1 DIRECT_VTUBER_SPEECH action every 2-3 iterations"
echo ""

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION * 60))
DIRECT_SPEECH_COUNT=0
TOTAL_ITERATIONS=0
LAST_ITERATION=0

while [ $(date +%s) -lt $END_TIME ]; do
    # Check for new iterations
    CURRENT_ITERATION=$(docker logs autonomous_starter_s3 --since="1m" 2>&1 | grep -c "Starting autonomous loop iteration" || echo "0")
    
    if [ $CURRENT_ITERATION -gt $LAST_ITERATION ]; then
        TOTAL_ITERATIONS=$((TOTAL_ITERATIONS + CURRENT_ITERATION - LAST_ITERATION))
        LAST_ITERATION=$CURRENT_ITERATION
        echo "📈 Total iterations so far: $TOTAL_ITERATIONS"
    fi
    
    # Check for DIRECT_VTUBER_SPEECH actions
    RECENT_DIRECT_SPEECH=$(docker logs autonomous_starter_s3 --since="1m" 2>&1 | grep -c "DIRECT_VTUBER_SPEECH" || echo "0")
    
    if [ $RECENT_DIRECT_SPEECH -gt 0 ]; then
        DIRECT_SPEECH_COUNT=$((DIRECT_SPEECH_COUNT + RECENT_DIRECT_SPEECH))
        echo "🎯 DIRECT_VTUBER_SPEECH detected! Total count: $DIRECT_SPEECH_COUNT"
        
        # Show the actual speech content
        docker logs autonomous_starter_s3 --since="1m" 2>&1 | grep "SENDING DIRECT SPEECH TO VTUBER" | tail -1 | sed 's/^/   /'
    fi
    
    # Check for VTuber responses
    VTUBER_RESPONSES=$(docker logs neurosync_byoc --since="1m" 2>&1 | grep -c "process_text" || echo "0")
    if [ $VTUBER_RESPONSES -gt 0 ]; then
        echo "📥 VTuber processing detected: $VTUBER_RESPONSES requests"
    fi
    
    sleep 30
done

echo ""
echo "📊 Test Results Summary"
echo "======================"
echo "🕐 Test Duration: ${DURATION} minutes"
echo "🔄 Total Iterations: $TOTAL_ITERATIONS"
echo "🎯 DIRECT_VTUBER_SPEECH Actions: $DIRECT_SPEECH_COUNT"

if [ $TOTAL_ITERATIONS -gt 0 ]; then
    SPEECH_RATIO=$((DIRECT_SPEECH_COUNT * 100 / TOTAL_ITERATIONS))
    echo "📈 Speech-to-Iteration Ratio: ${SPEECH_RATIO}%"
    
    if [ $SPEECH_RATIO -ge 30 ]; then
        echo "✅ EXCELLENT: High frequency of VTuber speech generation"
    elif [ $SPEECH_RATIO -ge 15 ]; then
        echo "👍 GOOD: Moderate VTuber speech generation"
    elif [ $SPEECH_RATIO -gt 0 ]; then
        echo "⚠️  NEEDS IMPROVEMENT: Low VTuber speech generation"
    else
        echo "❌ FAILED: No DIRECT_VTUBER_SPEECH actions detected"
    fi
else
    echo "❌ FAILED: No autonomous iterations detected"
fi

echo ""
echo "💡 Recommendations:"
if [ $DIRECT_SPEECH_COUNT -eq 0 ]; then
    echo "1. Check if DIRECT_VTUBER_SPEECH action is properly registered"
    echo "2. Verify autonomous loop is including DIRECT_VTUBER_SPEECH in available actions"
    echo "3. Check LLM decision-making logs for action selection reasoning"
elif [ $SPEECH_RATIO -lt 30 ]; then
    echo "1. Consider adjusting action diversity guidance to favor VTuber interactions"
    echo "2. Review prompt suggestions to encourage more VTuber content"
    echo "3. Check if other actions are being prioritized over VTuber speech"
else
    echo "1. System is working well! Monitor for content variety"
    echo "2. Check VTuber response quality and engagement"
    echo "3. Consider fine-tuning prompt generation for better content"
fi

echo ""
echo "🔍 For detailed logs, check:"
echo "   docker logs autonomous_starter_s3 | grep DIRECT_VTUBER_SPEECH"
echo "   docker logs neurosync_byoc | grep process_text" 