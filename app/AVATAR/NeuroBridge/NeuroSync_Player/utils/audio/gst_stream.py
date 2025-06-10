"""
gst_stream.py
-----------------
GStreamer-based audio streaming to RTMP servers.
"""

import os
import logging
from gi import require_version
require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # For Docker container-to-container communication, use nginx-rtmp service name
        rtmp_host = os.getenv("RTMP_HOST", "nginx-rtmp")
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
        pipeline.set_state(Gst.State.PLAYING)
        
        if blocking:
            # Wait for EOS or error
            bus = pipeline.get_bus()
            bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        
        pipeline.set_state(Gst.State.NULL)
        logger.info("✅ [GStreamer] Audio streaming completed successfully")
        
    except Exception as e:
        logger.error(f"❌ [GStreamer] Streaming failed: {e}")
        raise

