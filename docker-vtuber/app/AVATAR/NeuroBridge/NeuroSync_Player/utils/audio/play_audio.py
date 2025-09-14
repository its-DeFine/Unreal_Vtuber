"""
play_audio.py
-----------------
This module provides functions to play audio using Pygame. It includes
helper functions for initializing the mixer and unified playback loops.
It also supports audio conversion on the fly (e.g. raw PCM to WAV) where needed.
"""

import io
import time
import os
import logging
import pygame
from utils.audio.convert_audio import convert_to_wav
from utils.audio.gst_stream import stream_wav_to_rtmp
try:
    from utils.audio.gst_webrtc_stream import stream_wav_to_rtp, stream_wav_to_srt, stream_wav_to_webrtc_whip
except ImportError:
    stream_wav_to_rtp = None
    stream_wav_to_srt = None
    stream_wav_to_webrtc_whip = None

try:
    from utils.audio.pulse_stream import stream_wav_to_pulseaudio
except ImportError:
    stream_wav_to_pulseaudio = None

try:
    from utils.audio.webrtc_stream import stream_audio_webrtc_sync
except ImportError:
    stream_audio_webrtc_sync = None

try:
    import sys
    sys.path.append('/app/NeuroBridge/NeuroSync_Player')
    from http_audio_server import stream_audio_to_http
except ImportError:
    stream_audio_to_http = None

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# --- Helper Functions ---

def init_pygame_mixer():
    """
    Initialize the Pygame mixer only once.
    """
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def sync_playback_loop():
    """
    A playback loop that synchronizes elapsed time with the music position.
    """
    start_time = time.perf_counter()
    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        elapsed_time = time.perf_counter() - start_time
        current_pos = pygame.mixer.music.get_pos() / 1000.0  # convert ms to sec

        # If behind, sleep briefly; if ahead, let it catch up.
        if elapsed_time > current_pos:
            time.sleep(0.01)
        elif elapsed_time < current_pos:
            continue
        clock.tick(10)


def simple_playback_loop():
    """
    A simple playback loop that just ticks the clock until playback finishes.
    """
    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        clock.tick(10)


# --- Configuration Helpers -------------------------------------------------

def _audio_mode() -> str:
    """Return the requested audio mode.

    • "pulse"  → stream via PulseAudio for ultra-low latency (10-30ms)
    • "rtp"    → stream via RTP for low latency (100-300ms)
    • "srt"    → stream via SRT for low latency (500ms-1s)
    • "webrtc" → stream via WebRTC/HTTP fallback
    • "rtmp"   → stream with GStreamer RTMP (1-3s latency)
    • "pygame" → local playback via SDL/ALSA
    """
    return os.getenv("AUDIO_MODE", "rtp").lower()


def _rtmp_url() -> str:
    """Return the RTMP url to push to.

    Prioritizes Twitch if TWITCH_STREAM_KEY is set, otherwise defaults to local RTMP server.
    """
    twitch_stream_key = os.getenv("TWITCH_STREAM_KEY")
    obs_host_ip = os.getenv("OBS_HOST_IP", "nginx_rtmp") # Docker container hostname for internal networking

    if twitch_stream_key:
        twitch_broadcast_mode = os.getenv("TWITCH_BROADCAST_MODE", "test").lower()
        logger.info("Twitch stream key found. Target: Twitch.")
        # NOTE: Do NOT log the stream_key itself for security!
        if twitch_broadcast_mode == "live":
            logger.info("TWITCH_BROADCAST_MODE=live. Streaming to Twitch for public broadcast.")
            return f"rtmp://live.twitch.tv/app/{twitch_stream_key}"
        else:
            logger.info("TWITCH_BROADCAST_MODE=test (or not set). Streaming to Twitch in bandwidth test mode.")
            return f"rtmp://live.twitch.tv/app/{twitch_stream_key}?bandwidthtest=true"
    else:
        logger.info(f"No Twitch key found. Target: Local RTMP server at {obs_host_ip}:1935/live/mystream")
        return f"rtmp://{obs_host_ip}:1935/live/mystream"


# --- Playback Functions ---

def play_audio_bytes(audio_bytes, start_event, sync=True):
    """
    Play audio from raw bytes.
    
    Parameters:
      - audio_bytes: audio data as bytes.
      - start_event: threading.Event to wait for before starting playback.
      - sync: if True, uses time-syncing playback loop.
    """
    try:
        init_pygame_mixer()
        audio_file = io.BytesIO(audio_bytes)
        pygame.mixer.music.load(audio_file)
        start_event.wait()  # Wait for the signal to start
        pygame.mixer.music.play()
        if sync:
            sync_playback_loop()
        else:
            simple_playback_loop()
    except pygame.error as e:
        print(f"Error in play_audio_bytes: {e}")


def play_audio_from_memory(audio_data, start_event, sync=False):
    """
    Play audio from memory (assumes valid WAV bytes).
    Uses a simple playback loop.
    """
    try:
        init_pygame_mixer()
        audio_file = io.BytesIO(audio_data)
        pygame.mixer.music.load(audio_file)
        start_event.wait()
        pygame.mixer.music.play()
        simple_playback_loop()
    except pygame.error as e:
        if "Unknown WAVE format" in str(e):
            print("Unknown WAVE format encountered. Skipping to the next item in the queue.")
        else:
            print(f"Error in play_audio_from_memory: {e}")
    except Exception as e:
        print(f"Error in play_audio_from_memory: {e}")


def play_audio_from_path(audio_path, start_event, sync=True):
    """
    Play audio from a file path. If the format is unsupported,
    automatically convert it to WAV.
    """
    mode = _audio_mode()

    # -------------------------------------------------------------
    # Primary path: Ultra-low latency via PulseAudio (10-30ms)
    # -------------------------------------------------------------
    if mode == "pulse":
        # PulseAudio streaming - ultra-low latency (10-30ms)
        if stream_wav_to_pulseaudio:
            logger.info(f"[Audio] Using PulseAudio for ultra-low latency (10-30ms)")
            start_event.wait()
            try:
                stream_wav_to_pulseaudio(audio_path, blocking=True)
                return
            except Exception as pulse_error:
                logger.error(f"[Audio] PulseAudio streaming failed: {pulse_error}")
                mode = "rtp"  # Fall back to RTP
        else:
            logger.warning("[Audio] PulseAudio not available, falling back to RTP")
            mode = "rtp"
    
    # -------------------------------------------------------------
    # Secondary path: Low-latency streaming via GStreamer
    # -------------------------------------------------------------
    if mode == "rtp":
        # RTP streaming - lowest latency (100-300ms)
        if stream_wav_to_rtp:
            logger.info(f"[Audio] Using RTP streaming for ultra-low latency (100-300ms)")
            start_event.wait()
            
            # Note: Synchronization is now handled by delaying blendshapes
            # since they arrive BEFORE audio in RTP mode
            
            try:
                stream_wav_to_rtp(audio_path, blocking=True)
                return
            except Exception as rtp_error:
                logger.error(f"[Audio] RTP streaming failed: {rtp_error}")
                mode = "srt"  # Fall back to SRT
        else:
            logger.warning("[Audio] RTP streaming not available, falling back to SRT")
            mode = "srt"
    
    if mode == "srt":
        # SRT streaming - low latency (500ms-1s) with better reliability
        if stream_wav_to_srt:
            logger.info(f"[Audio] Using SRT streaming for low latency (500ms-1s)")
            start_event.wait()
            try:
                stream_wav_to_srt(audio_path, blocking=True)
                return
            except Exception as srt_error:
                logger.error(f"[Audio] SRT streaming failed: {srt_error}")
                mode = "rtmp"  # Fall back to RTMP
        else:
            logger.warning("[Audio] SRT streaming not available, falling back to RTMP")
            mode = "rtmp"
    
    if mode == "webrtc":
        # WebRTC via WHIP protocol
        if stream_wav_to_webrtc_whip:
            logger.info(f"[Audio] Using WebRTC WHIP streaming")
            start_event.wait()
            try:
                stream_wav_to_webrtc_whip(audio_path, blocking=True)
                return
            except Exception as whip_error:
                logger.error(f"[Audio] WebRTC WHIP failed: {whip_error}")
        
        # Try HTTP audio server as fallback
        if stream_audio_to_http:
            logger.info(f"[Audio] Falling back to HTTP server (port 8765)")
            start_event.wait()
            try:
                success = stream_audio_to_http(audio_path)
                if success:
                    logger.info(f"[Audio] ✅ Audio available at: http://localhost:8765/audio/current.wav")
                    return
            except Exception as http_error:
                logger.error(f"[Audio] HTTP streaming failed: {http_error}")
        
        # Final fallback to RTMP
        logger.warning("[Audio] WebRTC methods not available, falling back to RTMP")
        mode = "rtmp"
    
    if mode == "rtmp":
        rtmp_url = _rtmp_url()
        logger.info(f"[Audio] Streaming {audio_path} to {rtmp_url} (mode={mode})")
        start_event.wait()
        try:
            stream_wav_to_rtmp(audio_path, rtmp_url, blocking=True)
        except Exception as stream_error:
            logger.error(f"[Audio] GStreamer RTMP streaming failed: {stream_error}")
        return
    
    if mode != "pygame":
        return

    # -------------------------------------------------------------
    # Secondary path: local playback via pygame
    # -------------------------------------------------------------
    try:
        logger.info(f"[Audio] Attempting pygame playback: {audio_path}")
        init_pygame_mixer()
        try:
            pygame.mixer.music.load(audio_path)
        except pygame.error:
            logger.info(f"Unsupported format for {audio_path}. Converting to WAV.")
            audio_path = convert_to_wav(audio_path)
            pygame.mixer.music.load(audio_path)

        start_event.wait()
        pygame.mixer.music.play()
        logger.info("Playback via pygame started successfully.")
        if sync:
            sync_playback_loop()
        else:
            simple_playback_loop()
    except pygame.error as e:
        logger.error("Pygame playback failed (%s) and AUDIO_MODE=pygame. No fallback executed.", e)


def read_audio_file_as_bytes(file_path):
    """
    Read a WAV audio file from disk as bytes.
    Only WAV files are supported.
    """
    if not file_path.lower().endswith('.wav'):
        print(f"Unsupported file format: {file_path}. Only WAV files are supported.")
        return None
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error reading audio file: {e}")
        return None
