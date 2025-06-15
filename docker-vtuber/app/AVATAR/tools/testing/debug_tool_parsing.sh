#!/bin/bash

# Debug script to isolate tool parsing issues

echo "🔍 Debug Tool Parsing"
echo "===================="

# Test data
TEST_LINE='2025-05-28 12:32:22.245 [2025-05-28 08:50:17] DEBUG: [sendToVTuberAction] Validate: true (based on message.content.text: "## Agent Context (Iteration 1)'

echo "📋 Test line:"
echo "$TEST_LINE"
echo ""

# Test tool extraction
echo "🔧 Testing tool extraction:"
tool=$(echo "$TEST_LINE" | grep -o "\[doResearchAction\]\|\[updateContextAction\]\|\[sendToVTuberAction\]\|\[updateScbAction\]" | tr -d '[]' | head -1)
echo "Extracted tool: '$tool'"
echo ""

# Test operation extraction
echo "⚙️ Testing operation extraction:"
operation_type="unknown"
if echo "$TEST_LINE" | grep -q "Validate\|Validating"; then
    operation_type="validation"
elif echo "$TEST_LINE" | grep -q "Successfully\|✅"; then
    operation_type="success"
elif echo "$TEST_LINE" | grep -q "Error\|Failed\|❌"; then
    operation_type="error"
elif echo "$TEST_LINE" | grep -q "Executing\|Running"; then
    operation_type="execution"
fi
echo "Extracted operation: '$operation_type'"
echo ""

# Test SCB state
echo "🔗 Testing SCB state:"
scb_response=$(curl -s http://localhost:5000/scb/slice?tokens=50 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$scb_response" ]; then
    summary=$(echo "$scb_response" | jq -r '.summary // "unknown"' 2>/dev/null)
    window_count=$(echo "$scb_response" | jq '.window | length' 2>/dev/null)
    if [ -n "$summary" ] && [ "$summary" != "unknown" ] && [ "$summary" != "null" ]; then
        scb_state="active:$(echo "$summary" | tail -c 30 | tr '\n' ' ' | tr '"' "'" | tr '\\' '/')...(${window_count} events)"
    else
        scb_state="unknown"
    fi
else
    scb_state="api_unavailable"
fi
echo "SCB state: '$scb_state'"
echo ""

# Test JSON generation
echo "📄 Testing JSON generation:"
details=$(echo "$TEST_LINE" | cut -c1-100 | tr '"' "'" | tr '\\' '/')
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

echo "Details: '$details'"
echo "Timestamp: '$timestamp'"
echo ""

# Generate JSON
event_data=$(cat <<EOF
{
  "tool": "$tool",
  "operation": "$operation_type",
  "timestamp": "$timestamp",
  "details": "$details",
  "scb_state": "$scb_state"
}
EOF
)

echo "Generated JSON:"
echo "$event_data"
echo ""

# Test JSON validity
echo "🧪 Testing JSON validity:"
echo "$event_data" | jq '.' >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ JSON is valid"
    echo ""
    echo "📊 Parsed values:"
    echo "  Tool: $(echo "$event_data" | jq -r '.tool')"
    echo "  Operation: $(echo "$event_data" | jq -r '.operation')"
    echo "  Details: $(echo "$event_data" | jq -r '.details')"
    echo "  SCB State: $(echo "$event_data" | jq -r '.scb_state')"
else
    echo "❌ JSON is invalid"
    echo "Error details:"
    echo "$event_data" | jq '.' 2>&1
fi

echo ""
echo "🎯 Debug completed!" 