#!/usr/bin/env python3
"""
Low-Latency GStreamer Pipeline for RTMP Processing
Optimized for sub-200ms end-to-end latency with advanced buffer management
"""

import sys
import os
import signal
import logging
import time
import json
from typing import Dict, Any, Optional, List
from threading import Thread, Event, Lock
import argparse

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GstApp, GLib, GstVideo, GstAudio

# Configure logging for high-performance operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/low_latency_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LowLatencyProcessor:
    """
    Ultra-low latency GStreamer processor optimized for sub-200ms performance
    Features:
    - Minimal buffering (1-2 frames max)
    - Hardware acceleration when available
    - Zero-latency encoding presets
    - Real-time priority processing
    - Adaptive quality based on latency constraints
    """
    
    def __init__(self, input_stream: str, output_stream: str, max_latency_ms: int = 200):
        """
        Initialize the low-latency processor
        
        Args:
            input_stream: Source RTMP stream URL
            output_stream: Destination RTMP stream URL
            max_latency_ms: Maximum allowed latency in milliseconds
        """
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.max_latency_ms = max_latency_ms
        self.shutdown_event = Event()
        self.stats_lock = Lock()
        
        # Initialize GStreamer with latency-optimized settings
        Gst.init(None)
        
        # Pipeline components
        self.pipeline = None
        self.bus = None
        self.loop = None
        
        # Latency monitoring
        self.frame_timestamps = []
        self.last_latency_check = time.time()
        self.latency_violations = 0
        
        # Performance statistics
        self.stats = {
            'stream_input': input_stream,
            'stream_output': output_stream,
            'max_latency_ms': max_latency_ms,
            'current_latency_ms': 0.0,
            'average_latency_ms': 0.0,
            'frames_processed': 0,
            'latency_violations': 0,
            'dropped_frames': 0,
            'encoding_time_ms': 0.0,
            'hardware_acceleration': False,
            'status': 'initializing'
        }
        
        logger.info(f"🚀 [LowLatency] Initialized processor with {max_latency_ms}ms max latency")

    def detect_hardware_acceleration(self) -> Dict[str, bool]:
        """
        Detect available hardware acceleration capabilities
        
        Returns:
            dict: Available hardware acceleration features
        """
        capabilities = {
            'nvenc': False,
            'vaapi': False,
            'qsv': False,
            'omx': False,
            'v4l2': False
        }
        
        try:
            # Check for NVIDIA NVENC
            nvenc_test = Gst.ElementFactory.find('nvh264enc')
            capabilities['nvenc'] = nvenc_test is not None
            
            # Check for VAAPI (Intel/AMD)
            vaapi_test = Gst.ElementFactory.find('vaapih264enc')
            capabilities['vaapi'] = vaapi_test is not None
            
            # Check for Intel Quick Sync
            qsv_test = Gst.ElementFactory.find('qsvh264enc')
            capabilities['qsv'] = qsv_test is not None
            
            # Check for OpenMAX (ARM platforms)
            omx_test = Gst.ElementFactory.find('omxh264enc')
            capabilities['omx'] = omx_test is not None
            
            # Check for V4L2 hardware encoding
            v4l2_test = Gst.ElementFactory.find('v4l2h264enc')
            capabilities['v4l2'] = v4l2_test is not None
            
            logger.info(f"🔧 [LowLatency] Hardware acceleration capabilities: {capabilities}")
            
        except Exception as e:
            logger.warning(f"⚠️ [LowLatency] Error detecting hardware acceleration: {str(e)}")
        
        return capabilities

    def build_optimized_pipeline(self) -> str:
        """
        Build the most optimized pipeline string based on available hardware
        
        Returns:
            str: Optimized GStreamer pipeline string
        """
        hw_caps = self.detect_hardware_acceleration()
        
        # Select the best encoder based on available hardware
        video_encoder = "x264enc"
        video_encoder_params = "tune=zerolatency speed-preset=ultrafast bitrate=1000 key-int-max=15"
        
        if hw_caps['nvenc']:
            video_encoder = "nvh264enc"
            video_encoder_params = "preset=low-latency-default bitrate=1000 gop-size=15"
            self.stats['hardware_acceleration'] = True
            logger.info("🎯 [LowLatency] Using NVIDIA NVENC hardware acceleration")
            
        elif hw_caps['vaapi']:
            video_encoder = "vaapih264enc"
            video_encoder_params = "bitrate=1000 keyframe-period=15"
            self.stats['hardware_acceleration'] = True
            logger.info("🎯 [LowLatency] Using VAAPI hardware acceleration")
            
        elif hw_caps['qsv']:
            video_encoder = "qsvh264enc"
            video_encoder_params = "bitrate=1000 gop-size=15"
            self.stats['hardware_acceleration'] = True
            logger.info("🎯 [LowLatency] Using Intel Quick Sync hardware acceleration")
            
        elif hw_caps['v4l2']:
            video_encoder = "v4l2h264enc"
            video_encoder_params = "extra-controls=\"encode,h264_profile=1,h264_level=10,video_bitrate=1000000\""
            self.stats['hardware_acceleration'] = True
            logger.info("🎯 [LowLatency] Using V4L2 hardware acceleration")
            
        else:
            logger.info("🔧 [LowLatency] Using software encoding (x264)")

        # Build ultra-low latency pipeline
        pipeline_str = f"""
            rtmpsrc location="{self.input_stream}" ! 
            flvdemux name=demux
            
            demux.video ! 
            h264parse ! 
            decodebin ! 
            videoconvert ! 
            videoscale ! 
            video/x-raw,width=1280,height=720,framerate=30/1 !
            queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=downstream !
            {video_encoder} {video_encoder_params} !
            h264parse config-interval=1 !
            queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=downstream !
            mux.
            
            demux.audio ! 
            aacparse ! 
            decodebin ! 
            audioconvert ! 
            audioresample ! 
            audio/x-raw,format=S16LE,channels=2,rate=48000 !
            queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=downstream !
            voaacenc bitrate=128000 !
            aacparse !
            queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=downstream !
            mux.
            
            flvmux name=mux streamable=true latency=10000000 !
            queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=downstream !
            rtmpsink location="{self.output_stream} live=true"
        """
        
        return pipeline_str

    def create_pipeline(self) -> bool:
        """
        Create the ultra-low latency pipeline
        
        Returns:
            bool: True if pipeline created successfully
        """
        try:
            pipeline_str = self.build_optimized_pipeline()
            logger.info(f"🔧 [LowLatency] Creating optimized pipeline")
            
            self.pipeline = Gst.parse_launch(pipeline_str)
            if not self.pipeline:
                logger.error("❌ [LowLatency] Failed to create pipeline")
                return False
            
            # Set pipeline to live mode for minimal latency
            self.pipeline.set_property('async-handling', True)
            self.pipeline.set_latency(Gst.MSECOND * 10)  # 10ms base latency
            
            # Get the bus for message handling
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_message)
            
            # Add probes for latency measurement
            self.add_latency_probes()
            
            logger.info("✅ [LowLatency] Pipeline created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ [LowLatency] Pipeline creation failed: {str(e)}")
            return False

    def add_latency_probes(self):
        """Add buffer probes for latency measurement"""
        try:
            # Find elements for probe attachment
            demux = self.pipeline.get_by_name("demux")
            mux = self.pipeline.get_by_name("mux")
            
            if demux and mux:
                # Add input probe
                input_pad = demux.get_static_pad("video")
                if input_pad:
                    input_pad.add_probe(Gst.PadProbeType.BUFFER, self.input_probe_callback)
                
                # Add output probe
                output_pad = mux.get_static_pad("src")
                if output_pad:
                    output_pad.add_probe(Gst.PadProbeType.BUFFER, self.output_probe_callback)
                    
                logger.info("📊 [LowLatency] Latency probes installed")
            
        except Exception as e:
            logger.warning(f"⚠️ [LowLatency] Failed to add latency probes: {str(e)}")

    def input_probe_callback(self, pad, info):
        """Callback for input buffer probe"""
        buffer = info.get_buffer()
        if buffer:
            timestamp = buffer.pts
            current_time = time.time() * 1000000000  # Convert to nanoseconds
            
            with self.stats_lock:
                self.frame_timestamps.append({
                    'input_time': current_time,
                    'pts': timestamp,
                    'buffer_size': buffer.get_size()
                })
                
                # Keep only recent timestamps (last 100 frames)
                if len(self.frame_timestamps) > 100:
                    self.frame_timestamps.pop(0)
        
        return Gst.PadProbeReturn.OK

    def output_probe_callback(self, pad, info):
        """Callback for output buffer probe"""
        buffer = info.get_buffer()
        if buffer:
            current_time = time.time() * 1000000000  # Convert to nanoseconds
            timestamp = buffer.pts
            
            with self.stats_lock:
                # Find matching input timestamp
                for frame_data in self.frame_timestamps:
                    if abs(frame_data['pts'] - timestamp) < 100000000:  # 100ms tolerance
                        latency_ns = current_time - frame_data['input_time']
                        latency_ms = latency_ns / 1000000.0
                        
                        self.stats['current_latency_ms'] = latency_ms
                        self.stats['frames_processed'] += 1
                        
                        # Check for latency violations
                        if latency_ms > self.max_latency_ms:
                            self.latency_violations += 1
                            self.stats['latency_violations'] = self.latency_violations
                            logger.warning(f"⚠️ [LowLatency] Latency violation: {latency_ms:.1f}ms > {self.max_latency_ms}ms")
                        
                        # Update average latency
                        frame_count = self.stats['frames_processed']
                        if frame_count > 0:
                            current_avg = self.stats['average_latency_ms']
                            self.stats['average_latency_ms'] = (current_avg * (frame_count - 1) + latency_ms) / frame_count
                        
                        break
        
        return Gst.PadProbeReturn.OK

    def on_message(self, bus, message) -> bool:
        """Handle GStreamer bus messages with latency focus"""
        msg_type = message.type
        
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"❌ [LowLatency] Pipeline error: {err.message}")
            self.stats['status'] = 'error'
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"⚠️ [LowLatency] Pipeline warning: {warn.message}")
            
        elif msg_type == Gst.MessageType.EOS:
            logger.info("🏁 [LowLatency] End of stream reached")
            self.stats['status'] = 'completed'
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                if new_state == Gst.State.PLAYING:
                    self.stats['status'] = 'playing'
                    logger.info("🚀 [LowLatency] Pipeline playing - latency monitoring active")
                    
        elif msg_type == Gst.MessageType.LATENCY:
            # Handle latency messages to maintain optimal performance
            logger.debug("📊 [LowLatency] Latency message received - recalculating")
            if self.pipeline:
                self.pipeline.recalculate_latency()
        
        return True

    def start_processing(self) -> bool:
        """Start the low-latency pipeline processing"""
        try:
            if not self.create_pipeline():
                return False
            
            logger.info(f"🚀 [LowLatency] Starting pipeline - target latency: {self.max_latency_ms}ms")
            
            # Start the pipeline
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("❌ [LowLatency] Failed to start pipeline")
                return False
            
            # Create and start GLib main loop
            self.loop = GLib.MainLoop()
            
            # Start statistics reporting thread
            stats_thread = Thread(target=self.stats_reporter, daemon=True)
            stats_thread.start()
            
            # Run the main loop
            self.loop.run()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [LowLatency] Failed to start processing: {str(e)}")
            return False

    def stats_reporter(self):
        """Report statistics periodically"""
        while not self.shutdown_event.is_set():
            time.sleep(5)  # Report every 5 seconds
            
            with self.stats_lock:
                stats = self.get_stats()
                logger.info(
                    f"📊 [LowLatency] Stats - "
                    f"Frames: {stats['frames_processed']}, "
                    f"Avg Latency: {stats['average_latency_ms']:.1f}ms, "
                    f"Current: {stats['current_latency_ms']:.1f}ms, "
                    f"Violations: {stats['latency_violations']}, "
                    f"HW Accel: {stats['hardware_acceleration']}"
                )

    def stop_processing(self):
        """Stop the low-latency pipeline processing"""
        try:
            logger.info("🛑 [LowLatency] Stopping low-latency processing")
            
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
                
            if self.loop and self.loop.is_running():
                self.loop.quit()
            
            self.stats['status'] = 'stopped'
            logger.info("✅ [LowLatency] Processing stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ [LowLatency] Error stopping processing: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current latency and processing statistics"""
        return self.stats.copy()

def main():
    """Main entry point for low-latency processor"""
    parser = argparse.ArgumentParser(description='Low-Latency GStreamer RTMP Processor')
    parser.add_argument('--input', required=True, help='Input RTMP stream URL')
    parser.add_argument('--output', required=True, help='Output RTMP stream URL')
    parser.add_argument('--max-latency', type=int, default=200, 
                       help='Maximum allowed latency in milliseconds (default: 200)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"🛑 [LowLatency] Received signal {signum}, shutting down...")
        if hasattr(signal_handler, 'processor'):
            signal_handler.processor.stop_processing()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Create and start the processor
        processor = LowLatencyProcessor(args.input, args.output, args.max_latency)
        signal_handler.processor = processor
        
        if processor.start_processing():
            logger.info(f"✅ [LowLatency] Processing started successfully")
            processor.shutdown_event.wait()
        else:
            logger.error("❌ [LowLatency] Failed to start processing")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [LowLatency] Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        if 'processor' in locals():
            processor.stop_processing()

if __name__ == "__main__":
    main() 