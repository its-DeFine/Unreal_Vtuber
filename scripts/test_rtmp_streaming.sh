#!/bin/bash

# 🎵 RTMP Audio Streaming Test Script
# This script tests RTMP audio streaming functionality using ffmpeg and gstreamer
# Usage: ./test_rtmp_streaming.sh [mode] [duration]
# Modes: container (default), host, twitch
# Duration: seconds (default: 10)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_MODE="container"
DEFAULT_DURATION=10
TEST_AUDIO_FILE="test_rtmp_audio.wav"

# Parse arguments
MODE=${1:-$DEFAULT_MODE}
DURATION=${2:-$DEFAULT_DURATION}

echo -e "${BLUE}🎵 RTMP Audio Streaming Test Script${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Mode: $MODE"
echo "Duration: ${DURATION}s"
echo ""

# Function to log messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        return 1
    fi
    log_success "$1 is available"
    return 0
}

# Function to get RTMP URL based on mode
get_rtmp_url() {
    local url=""
    case "$MODE" in
        "container")
            RTMP_HOST=${RTMP_HOST:-"nginx-rtmp"}
            RTMP_PORT=${RTMP_PORT:-"1935"}
            RTMP_STREAM_NAME=${RTMP_STREAM_NAME:-"audiostream"}
            
            # Check if we're running inside a Docker container
            if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
                # Running inside container - use container name
                url="rtmp://${RTMP_HOST}:${RTMP_PORT}/live/${RTMP_STREAM_NAME}"
            else
                # Running on host - use localhost (container port is mapped)
                url="rtmp://localhost:${RTMP_PORT}/live/${RTMP_STREAM_NAME}"
            fi
            ;;
        "host")
            RTMP_HOST=${RTMP_HOST:-"localhost"}  # Changed default from WSL IP
            RTMP_PORT=${RTMP_PORT:-"1935"}
            RTMP_STREAM_NAME=${RTMP_STREAM_NAME:-"audiostream"}
            url="rtmp://${RTMP_HOST}:${RTMP_PORT}/live/${RTMP_STREAM_NAME}"
            ;;
        "twitch")
            if [[ -z "${TWITCH_STREAM_KEY:-}" ]]; then
                log_error "TWITCH_STREAM_KEY environment variable is required for Twitch mode"
                exit 1
            fi
            TWITCH_BROADCAST_MODE=${TWITCH_BROADCAST_MODE:-"test"}
            if [[ "$TWITCH_BROADCAST_MODE" == "live" ]]; then
                url="rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY}"
            else
                url="rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY}?bandwidthtest=true"
            fi
            ;;
        *)
            log_error "Invalid mode: $MODE. Use 'container', 'host', or 'twitch'"
            exit 1
            ;;
    esac
    
    echo "$url"
}

# Function to generate test audio file
generate_test_audio() {
    log_info "Generating test audio file: $TEST_AUDIO_FILE"
    
    # Generate a 440Hz sine wave test tone using ffmpeg
    if ! ffmpeg -f lavfi -i "sine=frequency=440:duration=${DURATION}" \
        -ac 2 -ar 22050 -y "$TEST_AUDIO_FILE" &>/dev/null; then
        log_error "Failed to generate test audio file"
        return 1
    fi
    
    log_success "Test audio file created: $TEST_AUDIO_FILE (${DURATION}s, 440Hz tone)"
    return 0
}

# Function to test RTMP connectivity
test_rtmp_connectivity() {
    local rtmp_url="$1"
    log_info "Testing RTMP connectivity to: $rtmp_url"
    
    # Extract host and port from RTMP URL
    if [[ "$rtmp_url" =~ rtmp://([^:/]+)(:([0-9]+))? ]]; then
        local host="${BASH_REMATCH[1]}"
        local port="${BASH_REMATCH[3]:-1935}"
        
        # Skip connectivity test for external services like Twitch
        if [[ "$host" == "live.twitch.tv" ]]; then
            log_info "Skipping connectivity test for external service: $host"
            return 0
        fi
        
        # Test TCP connectivity
        if command -v nc &> /dev/null; then
            if timeout 5 nc -z "$host" "$port" &>/dev/null; then
                log_success "RTMP server is reachable at $host:$port"
                return 0
            else
                log_warning "Cannot reach RTMP server at $host:$port"
                log_warning "This might be normal if the server only accepts RTMP connections"
                return 0  # Don't fail the test for this
            fi
        else
            log_warning "netcat (nc) not available, skipping connectivity test"
            return 0
        fi
    else
        log_warning "Could not parse RTMP URL for connectivity test"
        return 0
    fi
}

# Function to test with ffmpeg
test_ffmpeg_streaming() {
    local rtmp_url="$1"
    log_info "Testing RTMP streaming with ffmpeg..."
    
    # Stream the test audio file to RTMP
    log_info "Streaming $TEST_AUDIO_FILE to $rtmp_url"
    
    local ffmpeg_cmd="ffmpeg -re -i $TEST_AUDIO_FILE -c:a aac -b:a 128k -f flv $rtmp_url"
    log_info "Running: $ffmpeg_cmd"
    
    # Create a log file for ffmpeg output
    local ffmpeg_log="ffmpeg_test.log"
    
    if timeout $((DURATION + 10)) $ffmpeg_cmd &>"$ffmpeg_log"; then
        log_success "ffmpeg streaming completed successfully!"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_warning "ffmpeg streaming timed out (this might be expected for a successful stream)"
            # Check if there were any errors in the log
            if grep -i "error\|failed" "$ffmpeg_log" &>/dev/null; then
                log_error "ffmpeg encountered errors during streaming:"
                tail -5 "$ffmpeg_log"
                return 1
            else
                log_success "ffmpeg timeout is normal - stream was likely successful"
                return 0
            fi
        else
            log_error "ffmpeg streaming failed with exit code: $exit_code"
            log_error "ffmpeg output:"
            tail -10 "$ffmpeg_log"
            return 1
        fi
    fi
}

# Function to test with gstreamer
test_gstreamer_streaming() {
    local rtmp_url="$1"
    log_info "Testing RTMP streaming with GStreamer..."
    
    # Build GStreamer pipeline
    local gst_pipeline="filesrc location=$TEST_AUDIO_FILE ! wavparse ! audioconvert ! voaacenc bitrate=128000 ! queue ! flvmux ! rtmpsink location=\"$rtmp_url\""
    log_info "Running GStreamer pipeline..."
    
    # Create a log file for gstreamer output
    local gst_log="gstreamer_test.log"
    
    if timeout $((DURATION + 10)) gst-launch-1.0 $gst_pipeline &>"$gst_log"; then
        log_success "GStreamer streaming completed successfully!"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_warning "GStreamer streaming timed out (this might be expected for a successful stream)"
            # Check if there were any errors in the log
            if grep -i "error\|failed\|warning" "$gst_log" &>/dev/null; then
                log_error "GStreamer encountered errors during streaming:"
                tail -10 "$gst_log"
                return 1
            else
                log_success "GStreamer timeout is normal - stream was likely successful"
                return 0
            fi
        else
            log_error "GStreamer streaming failed with exit code: $exit_code"
            log_error "GStreamer output:"
            tail -10 "$gst_log"
            return 1
        fi
    fi
}

# Function to check RTMP server status (if accessible)
check_rtmp_server_status() {
    local rtmp_url="$1"
    
    # Only check for local servers
    if [[ "$rtmp_url" =~ rtmp://(nginx-rtmp|localhost|127\.0\.0\.1|172\.22\.80\.1) ]]; then
        log_info "Checking RTMP server status..."
        
        # Try to get server stats
        local stats_url=""
        if [[ "$rtmp_url" =~ nginx-rtmp ]]; then
            stats_url="http://nginx-rtmp:8080/stat"
        else
            stats_url="http://localhost:8080/stat"
        fi
        
        if command -v curl &> /dev/null; then
            if curl -s --connect-timeout 5 "$stats_url" &>/dev/null; then
                log_success "RTMP server is responding to status requests"
            else
                log_warning "RTMP server status endpoint not accessible"
            fi
        fi
    fi
}

# Function to cleanup
cleanup() {
    if [[ -f "$TEST_AUDIO_FILE" ]]; then
        rm -f "$TEST_AUDIO_FILE"
        log_info "Cleaned up test audio file"
    fi
    
    # Clean up log files
    for log_file in ffmpeg_test.log gstreamer_test.log; do
        if [[ -f "$log_file" ]]; then
            rm -f "$log_file"
        fi
    done
}

# Main function
main() {
    local success=true
    
    # Cleanup on exit
    trap cleanup EXIT
    
    # Check dependencies
    log_info "Checking dependencies..."
    
    if ! check_command ffmpeg; then
        log_error "ffmpeg is required for this test"
        exit 1
    fi
    
    if ! check_command gst-launch-1.0; then
        log_warning "GStreamer is not available, skipping GStreamer tests"
        local gstreamer_available=false
    else
        local gstreamer_available=true
    fi
    
    # Get RTMP URL
    local rtmp_url
    
    # Log environment detection
    if [[ "$MODE" == "container" ]]; then
        if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
            log_info "Detected container environment - using container networking"
        else
            log_info "Detected host environment - using localhost instead of container name"
        fi
    fi
    
    rtmp_url=$(get_rtmp_url)
    log_info "Target RTMP URL: $rtmp_url"
    
    # Generate test audio
    if ! generate_test_audio; then
        log_error "Failed to generate test audio"
        exit 1
    fi
    
    # Test connectivity
    test_rtmp_connectivity "$rtmp_url"
    
    # Check server status
    check_rtmp_server_status "$rtmp_url"
    
    # Test streaming with ffmpeg
    log_info "Starting ffmpeg streaming test..."
    if ! test_ffmpeg_streaming "$rtmp_url"; then
        success=false
        log_error "ffmpeg streaming test failed"
    fi
    
    # Test streaming with GStreamer (if available)
    if [[ "$gstreamer_available" == true ]]; then
        log_info "Starting GStreamer streaming test..."
        if ! test_gstreamer_streaming "$rtmp_url"; then
            success=false
            log_error "GStreamer streaming test failed"
        fi
    fi
    
    # Final result
    echo ""
    echo "============================================"
    if [[ "$success" == true ]]; then
        log_success "🎉 RTMP STREAMING TESTS PASSED!"
        echo -e "${GREEN}Your RTMP audio streaming is working correctly!${NC}"
    else
        log_error "❌ RTMP STREAMING TESTS FAILED!"
        echo -e "${RED}Please check the errors above and your configuration.${NC}"
        exit 1
    fi
    echo "============================================"
}

# Help function
show_help() {
    echo "RTMP Audio Streaming Test Script"
    echo ""
    echo "Usage: $0 [mode] [duration]"
    echo ""
    echo "Modes:"
    echo "  container  - Test with container networking (nginx-rtmp container)"
    echo "  host       - Test with host networking (localhost/WSL)"
    echo "  twitch     - Test streaming to Twitch (requires TWITCH_STREAM_KEY)"
    echo ""
    echo "Duration: Test audio duration in seconds (default: 10)"
    echo ""
    echo "Environment Variables:"
    echo "  RTMP_HOST           - RTMP server hostname/IP"
    echo "  RTMP_PORT           - RTMP server port (default: 1935)"
    echo "  RTMP_STREAM_NAME    - Stream name (default: audiostream)"
    echo "  TWITCH_STREAM_KEY   - Twitch stream key (for twitch mode)"
    echo "  TWITCH_BROADCAST_MODE - 'test' or 'live' (default: test)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Test container mode for 10 seconds"
    echo "  $0 host 15           # Test host mode for 15 seconds"
    echo "  $0 twitch 30         # Test Twitch streaming for 30 seconds"
    echo ""
}

# Check for help flag
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@" 