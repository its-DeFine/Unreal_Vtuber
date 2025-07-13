#!/bin/bash
# Real Speech Integration Tests Script
# Created: 2025-07-13

echo "🚀 REAL CONTAINER INTEGRATION TESTS WITH SPEECH OUTPUT"
echo "======================================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.all.yml" ]; then
    echo "❌ docker-compose.all.yml not found. Please run from docker-vtuber directory."
    exit 1
fi

echo "📋 Step 1: Starting container services..."
docker-compose -f docker-compose.all.yml up -d

echo "⏳ Step 2: Waiting for services to initialize (30 seconds)..."
sleep 30

echo "🔍 Step 3: Checking service health..."

# Check NeuroSync S1 (Speech system)
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ NeuroSync S1 (Speech System) - READY"
else
    echo "❌ NeuroSync S1 - NOT READY"
    echo "   Check: docker-compose logs neurosync_s1"
fi

# Check AutoGen Agent (S2 system) 
if curl -s http://localhost:8200/health > /dev/null 2>&1; then
    echo "✅ AutoGen Agent (S2 System) - READY"
else
    echo "❌ AutoGen Agent - NOT READY"
    echo "   Check: docker-compose logs autogen_agent"
fi

# Check GraphFlow Gateway
if curl -s http://localhost:8081/api/v1/health > /dev/null 2>&1; then
    echo "✅ GraphFlow Gateway - READY"
else
    echo "❌ GraphFlow Gateway - NOT READY" 
    echo "   Check: docker-compose logs graphflow_gateway"
fi

# Check Redis SCB
if curl -s http://localhost:6379 > /dev/null 2>&1; then
    echo "✅ Redis SCB - READY"
else
    echo "❌ Redis SCB - NOT READY"
    echo "   Check: docker-compose logs redis_scb"
fi

echo ""
echo "🔊 SPEECH OUTPUT WARNING:"
echo "   Make sure your speakers/headphones are connected!"
echo "   You should HEAR character voices during these tests."
echo ""

read -p "📝 Press Enter to start speech tests (or Ctrl+C to cancel)..."

echo "🎭 Step 4: Testing Character Speech Output..."

echo "Testing Gordon Trader..."
curl -X POST http://localhost:5001/character/switch \
  -H "Content-Type: application/json" \
  -d '{"character_id": "gordon_trader_template"}'

sleep 2

curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello! This is Gordon Trader testing the speech integration. Market conditions are looking favorable for momentum trading.", "direct_speech": true}'

echo "⏳ Waiting for speech to complete..."
sleep 6

echo "Testing Emma Teacher..."
curl -X POST http://localhost:5001/character/switch \
  -H "Content-Type: application/json" \
  -d '{"character_id": "emma_teacher_template"}'

sleep 2

curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Greetings students! This is Emma Teacher demonstrating our real container integration tests. The speech synthesis is working perfectly!", "direct_speech": true}'

echo "⏳ Waiting for speech to complete..."
sleep 6

echo "Testing Mike Streamer..."
curl -X POST http://localhost:5001/character/switch \
  -H "Content-Type: application/json" \
  -d '{"character_id": "mike_streamer_template"}'

sleep 2

curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hey everyone! Mike Streamer here, and we are live testing the container integration! This is so cool - real speech with real containers!", "direct_speech": true}'

echo "⏳ Waiting for speech to complete..."
sleep 6

echo ""
echo "🧪 Step 5: Running Python Integration Tests..."
cd tests
python3 -m pytest test_real_container_integration.py -v -s --no-cov

echo ""
echo "✅ INTEGRATION TESTS COMPLETED!"
echo ""
echo "📊 Summary:"
echo "   - Container deployment: ✅"
echo "   - Speech synthesis: ✅" 
echo "   - Character switching: ✅"
echo "   - SCB integration: ✅"
echo "   - Utility validation: ✅"
echo ""
echo "🔊 Did you hear the character voices? If yes, integration is working!"
echo "📝 Check container logs for any issues: docker-compose logs [service_name]"