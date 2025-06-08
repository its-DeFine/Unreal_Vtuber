#!/usr/bin/env python3
"""
GStreamer RTMP Stream Processor
Handles real-time stream processing with advanced audio enhancement
Integrates with nginx-rtmp for enhanced voice streaming capabilities
"""

import sys
import os
import signal
import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional
from threading import Thread, Event
import subprocess
import argparse

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GstApp, GLib, GstAudio

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/gstreamer_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GStreamerProcessor:
    """
    Advanced GStreamer processor for RTMP streams
    Provides real-time audio enhancement, analysis, and forwarding
    """
    
    def __init__(self, stream_name: str, client_addr: str, daemon_mode: bool = False):
        """
        Initialize the GStreamer processor
        
        Args:
            stream_name: Name of the RTMP stream
            client_addr: Address of the publishing client
            daemon_mode: Whether to run as a background daemon
        """
        self.stream_name = stream_name
        self.client_addr = client_addr
        self.daemon_mode = daemon_mode
        self.shutdown_event = Event()
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Pipeline components
        self.pipeline = None
        self.bus = None
        self.loop = None
        
        # Processing state
        self.start_time = time.time()
        self.frame_count = 0
        self.last_stats_time = time.time()
        
        # Statistics
        self.stats = {
            'stream_name': stream_name,
            'client_addr': client_addr,
            'start_time': self.start_time,
            'frames_processed': 0,
            'audio_level': 0.0,
            'processing_latency_ms': 0.0,
            'errors': 0,
            'status': 'initializing'
        }
        
        logger.info(f"🎛️ [GStreamer] Initialized processor for stream '{stream_name}' from {client_addr}")

    def create_pipeline(self) -> bool:
        """
        Create the GStreamer pipeline for audio processing
        
        Returns:
            bool: True if pipeline created successfully
        """
        try:
            # Build pipeline string for audio enhancement
            pipeline_str = f"""
                rtmpsrc location=rtmp://localhost:1935/live/{self.stream_name} ! 
                flvdemux name=demux
                
                demux.audio ! 
                decodebin ! 
                audioconvert ! 
                audioresample ! 
                audio/x-raw,format=F32LE,channels=1,rate=16000 !
                
                tee name=audio_tee
                
                audio_tee. ! queue ! 
                audioresample ! 
                audioconvert ! 
                audio/x-raw,format=S16LE,channels=1,rate=16000 !
                appsink name=analysis_sink emit-signals=true sync=false
                
                audio_tee. ! queue ! 
                volume volume=1.2 ! 
                audiofirfilter kernel="{{ 0.1, 0.8, 0.1 }}" ! 
                audioconvert ! 
                voaacenc bitrate=128000 ! 
                aacparse ! 
                flvmux name=mux ! 
                rtmpsink location=rtmp://localhost:1935/processed/{self.stream_name}
                
                demux.video ! 
                decodebin ! 
                videoconvert ! 
                x264enc tune=zerolatency bitrate=1000 speed-preset=ultrafast ! 
                h264parse ! 
                mux.
            """
            
            logger.info(f"🔧 [GStreamer] Creating pipeline for stream processing")
            self.pipeline = Gst.parse_launch(pipeline_str)
            
            if not self.pipeline:
                logger.error("❌ [GStreamer] Failed to create pipeline")
                return False
            
            # Get the bus for message handling
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_message)
            
            # Set up audio analysis sink
            analysis_sink = self.pipeline.get_by_name("analysis_sink")
            if analysis_sink:
                analysis_sink.connect("new-sample", self.on_audio_sample)
            
            logger.info("✅ [GStreamer] Pipeline created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ [GStreamer] Pipeline creation failed: {str(e)}")
            return False

    def on_audio_sample(self, sink) -> Gst.FlowReturn:
        """
        Handle new audio samples for real-time analysis
        
        Args:
            sink: The appsink element
            
        Returns:
            Gst.FlowReturn: Flow return status
        """
        try:
            sample = sink.emit("pull-sample")
            if sample:
                buffer = sample.get_buffer()
                caps = sample.get_caps()
                
                # Extract audio data for analysis
                success, map_info = buffer.map(Gst.MapFlags.READ)
                if success:
                    # Calculate audio level (simplified RMS)
                    import struct
                    import math
                    
                    audio_data = map_info.data
                    samples = struct.unpack(f"{len(audio_data)//2}h", audio_data)
                    
                    # Calculate RMS level
                    if samples:
                        rms = math.sqrt(sum(s*s for s in samples) / len(samples))
                        self.stats['audio_level'] = min(100.0, (rms / 32767.0) * 100.0)
                    
                    buffer.unmap(map_info)
                    
                    # Update frame count and stats
                    self.frame_count += 1
                    self.stats['frames_processed'] = self.frame_count
                    
                    # Log stats periodically
                    current_time = time.time()
                    if current_time - self.last_stats_time >= 5.0:  # Every 5 seconds
                        self.log_stats()
                        self.last_stats_time = current_time
            
            return Gst.FlowReturn.OK
            
        except Exception as e:
            logger.error(f"❌ [GStreamer] Audio sample processing error: {str(e)}")
            self.stats['errors'] += 1
            return Gst.FlowReturn.ERROR

    def on_message(self, bus, message) -> bool:
        """
        Handle GStreamer bus messages
        
        Args:
            bus: The message bus
            message: The message
            
        Returns:
            bool: True to continue handling messages
        """
        msg_type = message.type
        
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"❌ [GStreamer] Pipeline error: {err.message}")
            logger.debug(f"🔍 [GStreamer] Debug info: {debug}")
            self.stats['status'] = 'error'
            self.stats['errors'] += 1
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"⚠️ [GStreamer] Pipeline warning: {warn.message}")
            
        elif msg_type == Gst.MessageType.EOS:
            logger.info("🏁 [GStreamer] End of stream reached")
            self.stats['status'] = 'completed'
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(f"🔄 [GStreamer] Pipeline state changed: {old_state.value_nick} -> {new_state.value_nick}")
                
                if new_state == Gst.State.PLAYING:
                    self.stats['status'] = 'playing'
                elif new_state == Gst.State.PAUSED:
                    self.stats['status'] = 'paused'
        
        return True

    def log_stats(self):
        """Log current processing statistics"""
        uptime = time.time() - self.start_time
        fps = self.frame_count / uptime if uptime > 0 else 0
        
        logger.info(f"📊 [GStreamer] Stats - Stream: {self.stream_name}, "
                   f"Uptime: {uptime:.1f}s, Frames: {self.frame_count}, "
                   f"FPS: {fps:.1f}, Audio Level: {self.stats['audio_level']:.1f}%, "
                   f"Errors: {self.stats['errors']}")

    def start_processing(self) -> bool:
        """
        Start the GStreamer pipeline processing
        
        Returns:
            bool: True if started successfully
        """
        try:
            if not self.create_pipeline():
                return False
            
            logger.info(f"🚀 [GStreamer] Starting pipeline for stream '{self.stream_name}'")
            
            # Start the pipeline
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("❌ [GStreamer] Failed to start pipeline")
                return False
            
            # Create GLib main loop for message handling
            self.loop = GLib.MainLoop()
            
            # Start the main loop in a separate thread if in daemon mode
            if self.daemon_mode:
                loop_thread = Thread(target=self.loop.run, daemon=True)
                loop_thread.start()
                logger.info("🔄 [GStreamer] Running in daemon mode")
            else:
                # Run synchronously
                self.loop.run()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [GStreamer] Failed to start processing: {str(e)}")
            return False

    def stop_processing(self):
        """Stop the GStreamer pipeline processing"""
        try:
            logger.info(f"🛑 [GStreamer] Stopping processing for stream '{self.stream_name}'")
            
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
                
            if self.loop and self.loop.is_running():
                self.loop.quit()
            
            self.stats['status'] = 'stopped'
            self.log_stats()
            
            logger.info("✅ [GStreamer] Processing stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ [GStreamer] Error stopping processing: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current processing statistics
        
        Returns:
            dict: Current statistics
        """
        uptime = time.time() - self.start_time
        self.stats['uptime'] = uptime
        self.stats['fps'] = self.frame_count / uptime if uptime > 0 else 0
        return self.stats.copy()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"🛑 [GStreamer] Received signal {signum}, shutting down...")
    if hasattr(signal_handler, 'processor'):
        signal_handler.processor.stop_processing()
    sys.exit(0)

def main():
    """Main entry point for the GStreamer processor"""
    parser = argparse.ArgumentParser(description='GStreamer RTMP Stream Processor')
    parser.add_argument('stream_name', nargs='?', help='Name of the RTMP stream')
    parser.add_argument('client_addr', nargs='?', help='Address of the publishing client')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Handle case where script is called without arguments (daemon mode)
    if not args.stream_name and args.daemon:
        logger.info("🎛️ [GStreamer] Starting in daemon mode without specific stream")
        # In daemon mode, we could listen for new streams or handle multiple streams
        # For now, just keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 [GStreamer] Daemon stopped by user")
        return
    
    if not args.stream_name or not args.client_addr:
        logger.error("❌ [GStreamer] Stream name and client address required")
        parser.print_help()
        sys.exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Create and start the processor
        processor = GStreamerProcessor(args.stream_name, args.client_addr, args.daemon)
        signal_handler.processor = processor  # Store for signal handler
        
        if processor.start_processing():
            logger.info(f"✅ [GStreamer] Processing started successfully for '{args.stream_name}'")
            
            # Wait for completion or shutdown
            if not args.daemon:
                processor.shutdown_event.wait()
            else:
                # In daemon mode, run until interrupted
                try:
                    while not processor.shutdown_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        else:
            logger.error("❌ [GStreamer] Failed to start processing")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [GStreamer] Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        if 'processor' in locals():
            processor.stop_processing()

if __name__ == "__main__":
    main() 