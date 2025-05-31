import gi, sys, time, logging
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
Gst.init(None)

# Configure logging for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def stream_wav_to_rtmp(wav_path: str,
                       rtmp_url: str,
                       blocking: bool = True) -> None:
    """
    Streams a local WAV file to an RTMP server (e.g. OBS).  Non-blocking
    mode returns immediately after starting the pipeline.
    """
    logger.info(f"[GStreamer] Starting audio stream from {wav_path} to {rtmp_url}")
    
    # Validate inputs
    if not wav_path or not rtmp_url:
        logger.error(f"[GStreamer] Invalid inputs - wav_path: {wav_path}, rtmp_url: {rtmp_url}")
        return
    
    # Check if WAV file exists
    import os
    if not os.path.exists(wav_path):
        logger.error(f"[GStreamer] WAV file not found: {wav_path}")
        return
    
    pipeline_desc = (
        # ---------- Audio ----------
        f"filesrc location={wav_path} ! wavparse ! audioconvert ! "
        f"voaacenc bitrate=128000 ! queue ! mux. "
        # ---------- Dummy Video ----------
        # "videotestsrc is-live=true pattern=black ! "
        # "video/x-raw,width=640,height=360,framerate=30/1 ! "
        # "x264enc tune=zerolatency bitrate=1500 speed-preset=ultrafast key-int-max=30 ! "
        # "queue ! mux. "
        # ---------- Mux & Push ----------
        "flvmux name=mux streamable=true ! "
        f"rtmpsink location=\"{rtmp_url}\""
    )
    
    logger.info(f"[GStreamer] Launching pipeline: {pipeline_desc}")
    
    try:
        pipeline = Gst.parse_launch(pipeline_desc)
        logger.info("[GStreamer] Pipeline created successfully")
        
        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("[GStreamer] Failed to start pipeline")
            return
            
        logger.info("[GStreamer] Pipeline started successfully")
        
        if not blocking:
            logger.info("[GStreamer] Non-blocking mode - returning immediately")
            return

        # —––– Wait until EOS or ERROR ––––
        bus = pipeline.get_bus()
        logger.info("[GStreamer] Waiting for pipeline completion...")
        
        while True:
            msg = bus.timed_pop_filtered(
                Gst.SECOND,
                Gst.MessageType.EOS | Gst.MessageType.ERROR | Gst.MessageType.WARNING
            )
            if msg:
                if msg.type == Gst.MessageType.ERROR:
                    err, dbg = msg.parse_error()
                    logger.error(f"[GStreamer] Pipeline error: {err}")
                    if dbg:
                        logger.error(f"[GStreamer] Debug info: {dbg}")
                    break
                elif msg.type == Gst.MessageType.WARNING:
                    warn, dbg = msg.parse_warning()
                    logger.warning(f"[GStreamer] Pipeline warning: {warn}")
                    if dbg:
                        logger.warning(f"[GStreamer] Debug info: {dbg}")
                elif msg.type == Gst.MessageType.EOS:
                    logger.info("[GStreamer] End of stream reached")
                    break
            time.sleep(0.1)

        pipeline.set_state(Gst.State.NULL)
        logger.info("[GStreamer] Pipeline stopped and cleaned up")
        
    except Exception as e:
        logger.error(f"[GStreamer] Exception during streaming: {e}")
        try:
            pipeline.set_state(Gst.State.NULL)
        except:
            pass

