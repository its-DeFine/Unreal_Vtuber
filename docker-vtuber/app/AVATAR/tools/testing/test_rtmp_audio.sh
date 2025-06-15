#!/bin/bash

echo "🎵 RTMP Audio Streaming Test & Debug Script"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Step 1: Checking Docker containers${NC}"
echo "Current running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo -e "${BLUE}📋 Step 2: Starting RTMP server${NC}"
docker-compose -f docker-compose.bridge.yml up nginx-rtmp -d
sleep 2

echo ""
echo -e "${BLUE}📋 Step 3: Checking RTMP server status${NC}"
docker logs nginx_rtmp --tail 5

echo ""
echo -e "${BLUE}📋 Step 4: Testing RTMP server connectivity${NC}"
echo "Testing if RTMP server is accessible..."
timeout 5 telnet localhost 1935 2>/dev/null || echo -e "${RED}❌ RTMP server not accessible on localhost:1935${NC}"

echo ""
echo -e "${BLUE}📋 Step 5: Testing with FFmpeg (if available)${NC}"
if command -v ffmpeg &> /dev/null; then
    echo "Creating test audio file..."
    ffmpeg -f lavfi -i "sine=frequency=440:duration=3" -ar 44100 test_audio.wav -y 2>/dev/null
    
    if [ -f "test_audio.wav" ]; then
        echo -e "${GREEN}✅ Test audio file created${NC}"
        echo "Testing RTMP streaming with FFmpeg..."
        timeout 10 ffmpeg -re -i test_audio.wav -c:a aac -b:a 128k -f flv rtmp://localhost:1935/live/mystream 2>/dev/null &
        sleep 3
        echo -e "${YELLOW}⚠️  Check OBS for audio now!${NC}"
        wait
        rm -f test_audio.wav
    else
        echo -e "${RED}❌ Failed to create test audio${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  FFmpeg not found - skipping direct test${NC}"
fi

echo ""
echo -e "${BLUE}📋 Step 6: OBS Configuration Instructions${NC}"
echo -e "${GREEN}🎯 OBS Setup Instructions:${NC}"
echo "1. In OBS, add a new source:"
echo "   - Click '+' in Sources"
echo "   - Choose 'Media Source'"
echo "   - Name it 'VTuber Audio'"
echo ""
echo "2. Configure the Media Source:"
echo "   - Input: rtmp://localhost:1935/live/mystream"
echo "   - Input Format: (leave blank)"
echo "   - Restart when source becomes active: ✓"
echo "   - Advanced: Hardware Decoding: ✓"
echo ""
echo "3. Alternative - Browser Source:"
echo "   - URL: http://localhost:8080/live/mystream.m3u8"
echo ""
echo -e "${YELLOW}📝 Notes:${NC}"
echo "- Use 'localhost' (not nginx-rtmp) in OBS since OBS runs on the host"
echo "- The stream name is 'mystream' (configurable in .env)"
echo "- Port 1935 is for RTMP input, port 8080 is for HLS output"

echo ""
echo -e "${BLUE}📋 Step 7: Starting neurosync for full test${NC}"
echo "Starting neurosync container..."
docker-compose -f docker-compose.bridge.yml up neurosync -d
sleep 3

echo ""
echo "🎯 Ready to test! Run this command to test the full pipeline:"
echo -e "${GREEN}curl -X POST http://localhost:5001/process_text -H 'Content-Type: application/json' -d '{\"text\": \"Testing audio streaming\"}'\n${NC}"

echo "🔍 To debug further, check these logs:"
echo -e "${YELLOW}docker logs neurosync_s1 --tail 50${NC}"
echo -e "${YELLOW}docker logs nginx_rtmp --tail 20${NC}" 