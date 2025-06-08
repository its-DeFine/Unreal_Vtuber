#!/bin/bash

# Stream Processor Script for Multi-Quality RTMP Outputs
# Processes incoming streams and creates multiple quality variants
# Usage: ./stream_processor.sh <stream_name> <quality>

set -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Stream Processor] $1"
}

# Configuration
STREAM_NAME="$1"
QUALITY="$2"
INPUT_URL="rtmp://localhost:1935/live/$STREAM_NAME"
BASE_OUTPUT_URL="rtmp://localhost:1935/processed"

# Validate arguments
if [ -z "$STREAM_NAME" ] || [ -z "$QUALITY" ]; then
    log "❌ Usage: $0 <stream_name> <quality>"
    log "   Quality options: 240p, 480p, 720p, 1080p"
    exit 1
fi

# Quality configuration
case "$QUALITY" in
    240p)
        VIDEO_BITRATE="400k"
        AUDIO_BITRATE="64k"
        RESOLUTION="426x240"
        FRAMERATE="15"
        PRESET="ultrafast"
        ;;
    480p)
        VIDEO_BITRATE="1000k"
        AUDIO_BITRATE="96k"
        RESOLUTION="854x480"
        FRAMERATE="25"
        PRESET="veryfast"
        ;;
    720p)
        VIDEO_BITRATE="2500k"
        AUDIO_BITRATE="128k"
        RESOLUTION="1280x720"
        FRAMERATE="30"
        PRESET="fast"
        ;;
    1080p)
        VIDEO_BITRATE="5000k"
        AUDIO_BITRATE="192k"
        RESOLUTION="1920x1080"
        FRAMERATE="30"
        PRESET="medium"
        ;;
    *)
        log "❌ Invalid quality: $QUALITY"
        log "   Supported qualities: 240p, 480p, 720p, 1080p"
        exit 1
        ;;
esac

OUTPUT_URL="$BASE_OUTPUT_URL/${STREAM_NAME}_$QUALITY"

log "🎬 Starting stream processing:"
log "   Stream: $STREAM_NAME"
log "   Quality: $QUALITY"
log "   Resolution: $RESOLUTION"
log "   Video Bitrate: $VIDEO_BITRATE"
log "   Audio Bitrate: $AUDIO_BITRATE"
log "   Input: $INPUT_URL"
log "   Output: $OUTPUT_URL"

# Check if FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    log "❌ FFmpeg not found"
    exit 1
fi

# Function to handle cleanup
cleanup() {
    log "🛑 Cleaning up stream processor for $STREAM_NAME ($QUALITY)"
    # Kill any remaining FFmpeg processes for this stream
    pkill -f "ffmpeg.*$STREAM_NAME.*$QUALITY" 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for input stream to be available
log "⏳ Waiting for input stream to become available..."
WAIT_COUNT=0
MAX_WAIT=30  # 30 seconds timeout

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$INPUT_URL" 2>/dev/null; then
        log "✅ Input stream detected"
        break
    fi
    
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    
    if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
        log "⏳ Still waiting for input stream... (${WAIT_COUNT}s)"
    fi
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    log "❌ Timeout waiting for input stream"
    exit 1
fi

# Get input stream information
log "🔍 Analyzing input stream..."
INPUT_INFO=$(ffprobe -v quiet -print_format json -show_streams "$INPUT_URL" 2>/dev/null || echo "{}")

if [ "$INPUT_INFO" = "{}" ]; then
    log "❌ Failed to get input stream information"
    exit 1
fi

log "✅ Input stream analysis complete"

# Start FFmpeg processing
log "🚀 Starting FFmpeg processing for $QUALITY quality"

# Build FFmpeg command based on quality requirements
FFMPEG_CMD="ffmpeg"
FFMPEG_CMD="$FFMPEG_CMD -fflags +genpts"
FFMPEG_CMD="$FFMPEG_CMD -re"  # Read input at native frame rate
FFMPEG_CMD="$FFMPEG_CMD -i '$INPUT_URL'"
FFMPEG_CMD="$FFMPEG_CMD -c:v libx264"
FFMPEG_CMD="$FFMPEG_CMD -preset $PRESET"
FFMPEG_CMD="$FFMPEG_CMD -tune zerolatency"
FFMPEG_CMD="$FFMPEG_CMD -profile:v baseline"
FFMPEG_CMD="$FFMPEG_CMD -level 3.0"
FFMPEG_CMD="$FFMPEG_CMD -pix_fmt yuv420p"
FFMPEG_CMD="$FFMPEG_CMD -s $RESOLUTION"
FFMPEG_CMD="$FFMPEG_CMD -r $FRAMERATE"
FFMPEG_CMD="$FFMPEG_CMD -b:v $VIDEO_BITRATE"
FFMPEG_CMD="$FFMPEG_CMD -maxrate $VIDEO_BITRATE"
FFMPEG_CMD="$FFMPEG_CMD -bufsize $((${VIDEO_BITRATE%k} * 2))k"
FFMPEG_CMD="$FFMPEG_CMD -g $((FRAMERATE * 2))"  # Keyframe interval: 2 seconds
FFMPEG_CMD="$FFMPEG_CMD -keyint_min $FRAMERATE"  # Minimum keyframe interval: 1 second

# Audio processing
FFMPEG_CMD="$FFMPEG_CMD -c:a aac"
FFMPEG_CMD="$FFMPEG_CMD -b:a $AUDIO_BITRATE"
FFMPEG_CMD="$FFMPEG_CMD -ar 44100"
FFMPEG_CMD="$FFMPEG_CMD -ac 2"

# Low latency optimizations
FFMPEG_CMD="$FFMPEG_CMD -flags +global_header"
FFMPEG_CMD="$FFMPEG_CMD -avoid_negative_ts make_zero"
FFMPEG_CMD="$FFMPEG_CMD -fflags +nobuffer"
FFMPEG_CMD="$FFMPEG_CMD -strict experimental"

# Output format
FFMPEG_CMD="$FFMPEG_CMD -f flv"
FFMPEG_CMD="$FFMPEG_CMD '$OUTPUT_URL'"

# Add logging and error handling
FFMPEG_CMD="$FFMPEG_CMD -loglevel warning"
FFMPEG_CMD="$FFMPEG_CMD -stats_period 5"

log "🔧 Executing: $FFMPEG_CMD"

# Execute FFmpeg with error handling
eval "$FFMPEG_CMD" &
FFMPEG_PID=$!

log "✅ FFmpeg started with PID: $FFMPEG_PID"

# Monitor FFmpeg process
monitor_ffmpeg() {
    local last_check=$(date +%s)
    local restart_count=0
    local max_restarts=3
    
    while true do
        sleep 5
        
        # Check if FFmpeg is still running
        if ! kill -0 $FFMPEG_PID 2>/dev/null; then
            log "⚠️ FFmpeg process stopped unexpectedly"
            
            # Check exit code
            wait $FFMPEG_PID 2>/dev/null
            exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log "✅ FFmpeg completed normally"
                break
            else
                log "❌ FFmpeg exited with code: $exit_code"
                
                # Attempt restart if under limit
                if [ $restart_count -lt $max_restarts ]; then
                    restart_count=$((restart_count + 1))
                    log "🔄 Attempting restart $restart_count/$max_restarts"
                    
                    # Wait a bit before restart
                    sleep 2
                    
                    # Restart FFmpeg
                    eval "$FFMPEG_CMD" &
                    FFMPEG_PID=$!
                    log "🚀 FFmpeg restarted with PID: $FFMPEG_PID"
                else
                    log "❌ Maximum restart attempts reached"
                    exit 1
                fi
            fi
        fi
        
        # Log status every 30 seconds
        current_time=$(date +%s)
        if [ $((current_time - last_check)) -ge 30 ]; then
            log "📊 Stream processor running for $QUALITY - PID: $FFMPEG_PID"
            last_check=$current_time
        fi
    done
}

# Start monitoring in background
monitor_ffmpeg &
MONITOR_PID=$!

# Wait for FFmpeg to complete or be terminated
wait $FFMPEG_PID 2>/dev/null
FFMPEG_EXIT_CODE=$?

# Clean up monitor
kill $MONITOR_PID 2>/dev/null || true

# Report final status
if [ $FFMPEG_EXIT_CODE -eq 0 ]; then
    log "✅ Stream processing completed successfully for $QUALITY"
else
    log "❌ Stream processing failed with exit code: $FFMPEG_EXIT_CODE"
fi

log "🏁 Stream processor finished for $STREAM_NAME ($QUALITY)"
exit $FFMPEG_EXIT_CODE 