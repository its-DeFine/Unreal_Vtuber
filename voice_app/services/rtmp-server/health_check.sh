#!/bin/bash

# Health check script for nginx-rtmp server
# Verifies server status and core functionality

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Health Check] $1"
}

# Exit codes
EXIT_OK=0
EXIT_WARNING=1
EXIT_CRITICAL=2
EXIT_UNKNOWN=3

# Check if nginx is running
if ! pgrep nginx > /dev/null; then
    log "❌ nginx process not running"
    exit $EXIT_CRITICAL
fi

# Check if nginx is responding on port 8080
if ! curl -s -f http://localhost:8080/health > /dev/null; then
    log "❌ HTTP health endpoint not responding"
    exit $EXIT_CRITICAL
fi

# Check RTMP port 1935
if ! nc -z localhost 1935 2>/dev/null; then
    log "❌ RTMP port 1935 not accessible"
    exit $EXIT_CRITICAL
fi

# Check required directories exist and are writable
REQUIRED_DIRS=(
    "/var/recordings"
    "/tmp/hls"
    "/tmp/dash"
    "/var/log/nginx"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        log "❌ Required directory missing: $dir"
        exit $EXIT_CRITICAL
    fi
    
    if [ ! -w "$dir" ]; then
        log "❌ Directory not writable: $dir"
        exit $EXIT_CRITICAL
    fi
done

# Check GStreamer availability
if ! command -v gst-launch-1.0 &> /dev/null; then
    log "❌ GStreamer not available"
    exit $EXIT_CRITICAL
fi

# Check FFmpeg availability
if ! command -v ffmpeg &> /dev/null; then
    log "❌ FFmpeg not available"
    exit $EXIT_CRITICAL
fi

# Check Python availability
if ! command -v python3 &> /dev/null; then
    log "❌ Python3 not available"
    exit $EXIT_CRITICAL
fi

# Check disk space for recordings (warn if < 1GB free)
RECORDINGS_SPACE=$(df /var/recordings | awk 'NR==2 {print $4}')
if [ "$RECORDINGS_SPACE" -lt 1048576 ]; then  # 1GB in KB
    log "⚠️  Low disk space for recordings: $(($RECORDINGS_SPACE / 1024))MB remaining"
    # Don't exit critical, just warn
fi

# Check memory usage (warn if > 80%)
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    log "⚠️  High memory usage: ${MEMORY_USAGE}%"
    # Don't exit critical, just warn
fi

# Check nginx error log for recent errors
ERROR_COUNT=$(tail -100 /var/log/nginx/error.log 2>/dev/null | grep -c "$(date '+%Y/%m/%d')" || echo "0")
if [ "$ERROR_COUNT" -gt 10 ]; then
    log "⚠️  High error count in nginx log: $ERROR_COUNT errors today"
    # Don't exit critical, just warn
fi

# Check if stats endpoint is working
STATS_RESPONSE=$(curl -s http://localhost:8080/stats 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$STATS_RESPONSE" ]; then
    log "⚠️  Statistics endpoint not responding properly"
    # Don't exit critical, just warn
fi

# Optional: Check if HLS directory is being used (streams active)
HLS_FILES=$(find /tmp/hls -name "*.m3u8" -mmin -5 2>/dev/null | wc -l)
if [ "$HLS_FILES" -gt 0 ]; then
    log "✅ Active HLS streams detected: $HLS_FILES"
else
    log "ℹ️  No recent HLS activity"
fi

log "✅ All critical health checks passed"
exit $EXIT_OK 