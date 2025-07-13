"""
gst_stream.py
-----------------
GStreamer-based audio streaming to RTMP servers.
"""

import os
import logging
import threading
from gi import require_version
require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global pipeline tracking for speech control
_active_pipelines = []
_pipeline_lock = threading.Lock()

def stop_all_audio_streams():
    """Stop all active GStreamer audio pipelines"""
    global _active_pipelines
    with _pipeline_lock:
        stopped_count = 0
        for pipeline in _active_pipelines[:]:  # Copy list to avoid modification during iteration
            try:
                if not pipeline:
                    continue

                # 1️⃣  Send EOS first so any thread blocking on bus.timed_pop exits cleanly
                try:
                    eos_sent = pipeline.send_event(Gst.Event.new_eos())
                    if not eos_sent:
                        logger.debug("🚦 Failed to send EOS event (pipeline may already be NULL)")
                except Exception as eos_err:
                    logger.debug(f"🚦 Error while sending EOS: {eos_err}")

                # 2️⃣  Do NOT immediately set the pipeline to NULL here.
                #     Setting NULL right after EOS can swallow the EOS message, leaving
                #     the thread in stream_wav_to_rtmp blocked on bus.timed_pop.
                #     We let the audio thread receive EOS, complete gracefully, and
                #     then call set_state(NULL) inside that thread.

                stopped_count += 1
                logger.info("🛑 Sent EOS to GStreamer pipeline (will transition to NULL in audio thread)")
            except Exception as e:
                logger.warning(f"⚠️ Error stopping pipeline: {e}")
        _active_pipelines.clear()
        if stopped_count > 0:
            logger.info(f"🛑 Stopped {stopped_count} active audio streams")
        return stopped_count

def get_active_stream_count():
    """Get number of active audio streams"""
    with _pipeline_lock:
        return len(_active_pipelines)

def get_rtmp_url():
    """
    Get the RTMP URL from environment variables or use Docker container default.
    Prioritizes Twitch if TWITCH_STREAM_KEY is set.
    """
    twitch_stream_key = os.getenv("TWITCH_STREAM_KEY")
    
    if twitch_stream_key:
        twitch_broadcast_mode = os.getenv("TWITCH_BROADCAST_MODE", "test").lower()
        if twitch_broadcast_mode == "live":
            return f"rtmp://live.twitch.tv/app/{twitch_stream_key}"
        else:
            return f"rtmp://live.twitch.tv/app/{twitch_stream_key}?bandwidthtest=true"
    else:
        # For Docker container-to-container communication, use nginx_rtmp service name
        rtmp_host = os.getenv("RTMP_HOST", "nginx_rtmp")
        rtmp_port = os.getenv("RTMP_PORT", "1935")
        stream_name = os.getenv("RTMP_STREAM_NAME", "mystream")
        return f"rtmp://{rtmp_host}:{rtmp_port}/live/{stream_name}"

def stream_wav_to_rtmp(wav_file_path, rtmp_url=None, blocking=True):
    """
    Stream a WAV file to an RTMP server using GStreamer.
    
    Args:
        wav_file_path (str): Path to the WAV file
        rtmp_url (str, optional): RTMP URL. If None, uses get_rtmp_url()
        blocking (bool): Whether to block until streaming is complete
    """
    global _active_pipelines
    
    if rtmp_url is None:
        rtmp_url = get_rtmp_url()
    
    logger.info(f"🎵 [GStreamer] Streaming {wav_file_path} to {rtmp_url}")
    
    # Create GStreamer pipeline
    pipeline_str = (
        f"filesrc location=\"{wav_file_path}\" ! "
        "wavparse ! "
        "audioconvert ! "
        "audioresample ! "
        "voaacenc bitrate=128000 ! "
        "flvmux ! "
        f"rtmpsink location=\"{rtmp_url} live=1\""
    )
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        
        # Register pipeline for tracking
        with _pipeline_lock:
            _active_pipelines.append(pipeline)
        
        pipeline.set_state(Gst.State.PLAYING)
        
        if blocking:
            # Wait for EOS or error
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)
            
            # Check if we were stopped externally vs completed naturally
            if msg and msg.type == Gst.MessageType.ERROR:
                logger.warning("🚨 [GStreamer] Pipeline stopped due to error")
            elif msg and msg.type == Gst.MessageType.EOS:
                logger.info("✅ [GStreamer] Pipeline completed normally")
        
        pipeline.set_state(Gst.State.NULL)
        
        # Unregister pipeline
        with _pipeline_lock:
            if pipeline in _active_pipelines:
                _active_pipelines.remove(pipeline)
        
        logger.info("✅ [GStreamer] Audio streaming completed")
        
    except Exception as e:
        # Ensure pipeline is removed from tracking on error
        with _pipeline_lock:
            if 'pipeline' in locals() and pipeline in _active_pipelines:
                _active_pipelines.remove(pipeline)
        logger.error(f"❌ [GStreamer] Streaming failed: {e}")
        raise

