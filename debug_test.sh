#!/bin/bash
set -e

echo "🎭 Debug Test: Professor Smith Identity Question"
echo "================================================"

# Step 1: Check API
echo "Step 1: Testing API availability..."
curl -s "http://localhost:5001/api/v1/reactive/status" > /dev/null && echo "✅ API responsive"

# Step 2: Load character
echo "Step 2: Loading Professor Smith..."
curl -X POST "http://localhost:5001/api/v1/reactive/character/load" \
     -H "Content-Type: application/json" \
     -d '{"character_id": "demo_teacher"}' && echo

# Step 3: Identity question
echo "Step 3: Asking identity question..."
curl -X POST "http://localhost:5001/api/v1/reactive/event/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "What character are you? Who are you? Please introduce yourself."}' && echo

echo "✅ Debug test completed successfully!"
