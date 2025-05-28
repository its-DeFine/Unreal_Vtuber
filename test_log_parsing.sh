#!/bin/bash

# Test script to verify log parsing logic

echo "🔍 Testing Log Parsing Logic"
echo "============================"

# Test data
TEST_LOG="/tmp/test_autonomous.log"

# Create test log entries
cat > "$TEST_LOG" <<EOF
2025-05-28 12:09:14.367 [2025-05-28 08:50:17] INFO: [AutonomousService] Starting autonomous loop iteration 26
2025-05-28 12:09:15.367 [2025-05-28 08:50:18] INFO: [doResearchAction] ✅ RESEARCH COMPLETED
2025-05-28 12:09:16.367 [2025-05-28 08:50:19] INFO: [updateContextAction] ✅ CONTEXT STORED: "VR technology insights"
2025-05-28 12:09:17.367 [2025-05-28 08:50:20] INFO: [AutonomousService] Loop iteration 26 completed
EOF

echo "📋 Test log created with sample entries"
echo ""

# Test parsing patterns
echo "🔍 Testing iteration start pattern:"
if grep -q "Starting autonomous loop iteration" "$TEST_LOG"; then
    echo "✅ Found iteration start pattern"
    iteration=$(grep "Starting autonomous loop iteration" "$TEST_LOG" | grep -o "iteration [0-9]*" | grep -o "[0-9]*")
    echo "   Extracted iteration: $iteration"
else
    echo "❌ Iteration start pattern not found"
fi

echo ""
echo "🔍 Testing iteration completion pattern:"
if grep -q "Loop iteration.*completed" "$TEST_LOG"; then
    echo "✅ Found iteration completion pattern"
    iteration=$(grep "Loop iteration.*completed" "$TEST_LOG" | grep -o "iteration [0-9]*" | grep -o "[0-9]*")
    echo "   Extracted iteration: $iteration"
else
    echo "❌ Iteration completion pattern not found"
fi

echo ""
echo "🔍 Testing action patterns:"
if grep -q "\[doResearchAction\]\|\[updateContextAction\]" "$TEST_LOG"; then
    echo "✅ Found action patterns"
    actions=$(grep -o "\[doResearchAction\]\|\[updateContextAction\]" "$TEST_LOG" | tr -d '[]')
    echo "   Found actions: $actions"
else
    echo "❌ Action patterns not found"
fi

echo ""
echo "🔍 Testing memory operation patterns:"
if grep -q "CONTEXT STORED\|RESEARCH COMPLETED" "$TEST_LOG"; then
    echo "✅ Found memory operation patterns"
    operations=$(grep -o "CONTEXT STORED\|RESEARCH COMPLETED" "$TEST_LOG")
    echo "   Found operations: $operations"
else
    echo "❌ Memory operation patterns not found"
fi

# Test with actual log file
echo ""
echo "🔍 Testing with actual autonomous agent logs:"
ACTUAL_LOG="logs/autonomous_monitoring/session_20250528_120914/raw/autonomous_starter_s3.log"

if [ -f "$ACTUAL_LOG" ]; then
    echo "📁 Found actual log file: $ACTUAL_LOG"
    
    echo "   Iteration starts found: $(grep -c "Starting autonomous loop iteration" "$ACTUAL_LOG")"
    echo "   Iteration completions found: $(grep -c "Loop iteration.*completed" "$ACTUAL_LOG")"
    echo "   Action executions found: $(grep -c "\[doResearchAction\]\|\[updateContextAction\]\|\[sendToVTuberAction\]\|\[updateScbAction\]" "$ACTUAL_LOG")"
    echo "   Memory operations found: $(grep -c "CONTEXT STORED\|RESEARCH COMPLETED\|SCB UPDATE STORED" "$ACTUAL_LOG")"
    
    echo ""
    echo "📋 Sample entries from actual log:"
    grep "Starting autonomous loop iteration\|Loop iteration.*completed" "$ACTUAL_LOG" | tail -3
else
    echo "❌ Actual log file not found"
fi

# Cleanup
rm -f "$TEST_LOG"

echo ""
echo "�� Test completed!" 