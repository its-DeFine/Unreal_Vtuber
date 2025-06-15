#!/bin/bash

echo "🎥 Real-Time OBS RTMP Stream Test"
echo "================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔧 Starting RTMP server...${NC}"
docker-compose -f docker-compose.bridge.yml up nginx-rtmp -d
sleep 2

echo -e "${BLUE}📡 Starting neurosync...${NC}"
docker-compose -f docker-compose.bridge.yml up neurosync -d
sleep 3

echo ""
echo -e "${GREEN}🎯 CONFIGURE OBS NOW:${NC}"
echo ""
echo "1. In OBS, add a Media Source:"
echo "   ✅ Source Type: Media Source"
echo "   ✅ Name: VTuber_Audio"
echo "   ✅ Input: rtmp://localhost:1935/live/mystream"
echo "   ✅ Input Format: (leave blank)"
echo "   ✅ ☑ Restart when source becomes active"
echo "   ✅ ☑ Close file when inactive"
echo ""
echo "2. Audio Settings:"
echo "   ✅ Right-click source → Advanced Audio Properties"
echo "   ✅ Audio Monitoring: Monitor and Output"
echo ""
echo -e "${YELLOW}📢 IMPORTANT: OBS must be configured BEFORE the stream starts!${NC}"
echo ""

read -p "✋ Press ENTER when OBS is configured and ready..."

echo ""
echo -e "${BLUE}🎵 Sending continuous test stream for 30 seconds...${NC}"
echo "👀 WATCH OBS NOW for audio activity!"
echo ""

# Generate and stream continuous audio
if command -v ffmpeg &> /dev/null; then
    echo "🎶 Streaming 440Hz tone for 30 seconds..."
    timeout 30 ffmpeg -f lavfi -i "sine=frequency=440:duration=30" -ar 44100 -c:a aac -b:a 128k -f flv rtmp://localhost:1935/live/mystream -loglevel quiet 2>/dev/null &
    
    # Show progress
    for i in {1..30}; do
        echo -ne "⏱️  Streaming... ${i}/30 seconds\r"
        sleep 1
    done
    echo ""
    
    wait
    echo "✅ Test stream completed!"
else
    echo -e "${RED}❌ FFmpeg not found - cannot stream test audio${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🧪 Now testing with VTuber LLM...${NC}"
echo "🗣️ Sending text to VTuber for processing..."

curl -X POST http://localhost:5001/process_text \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello! This is a test of the VTuber audio streaming system. You should hear this in OBS."}' \
     2>/dev/null

echo ""
echo "👂 Listen for VTuber response in OBS!"
echo ""
echo "🔍 Check logs if needed:"
echo "   docker logs neurosync_s1 --tail 20"
echo "   docker logs nginx_rtmp --tail 10" 