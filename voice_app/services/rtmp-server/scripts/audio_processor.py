#!/usr/bin/env python3
"""
Advanced Audio Processor for Voice Streams
Handles real-time voice enhancement, noise reduction, and audio analysis
Optimized for low-latency voice streaming applications
"""

import sys
import os
import signal
import logging
import asyncio
import json
import time
import argparse
import threading
from typing import Dict, Any, Optional, Tuple
from threading import Thread, Event, Lock
import numpy as np

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GstApp, GLib, GstAudio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/audio_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VoiceEnhancer:
    """Advanced voice enhancement and noise reduction"""
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize voice enhancer
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * 0.02)  # 20ms frames
        
        # Noise reduction parameters
        self.noise_profile = None
        self.noise_learn_frames = 50  # Frames to learn noise profile
        self.noise_frames_count = 0
        self.alpha = 0.95  # Noise reduction factor
        
        # Voice activity detection
        self.vad_threshold = 0.02
        self.silence_frames = 0
        self.max_silence_frames = 100  # 2 seconds at 20ms frames
        
        # Audio enhancement parameters
        self.gain = 1.0
        self.compression_ratio = 3.0
        self.compression_threshold = 0.7
        
        logger.info(f"🎤 [Voice Enhancer] Initialized with sample rate {sample_rate}Hz")

    def detect_voice_activity(self, audio_data: np.ndarray) -> bool:
        """
        Detect if the audio contains voice activity
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            bool: True if voice activity detected
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms > self.vad_threshold:
            self.silence_frames = 0
            return True
        else:
            self.silence_frames += 1
            return False

    def learn_noise_profile(self, audio_data: np.ndarray):
        """
        Learn the noise profile from silent periods
        
        Args:
            audio_data: Audio samples during silence
        """
        if self.noise_profile is None:
            self.noise_profile = np.abs(np.fft.fft(audio_data))
        else:
            current_spectrum = np.abs(np.fft.fft(audio_data))
            self.noise_profile = 0.9 * self.noise_profile + 0.1 * current_spectrum
        
        self.noise_frames_count += 1
        
        if self.noise_frames_count % 10 == 0:
            logger.debug(f"🔍 [Voice Enhancer] Learned noise profile from {self.noise_frames_count} frames")

    def reduce_noise(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Apply spectral noise reduction
        
        Args:
            audio_data: Input audio samples
            
        Returns:
            np.ndarray: Noise-reduced audio samples
        """
        if self.noise_profile is None:
            return audio_data
        
        # FFT of input signal
        audio_fft = np.fft.fft(audio_data)
        audio_magnitude = np.abs(audio_fft)
        audio_phase = np.angle(audio_fft)
        
        # Calculate noise reduction gain
        snr_estimate = audio_magnitude / (self.noise_profile + 1e-10)
        gain = np.maximum(1 - self.alpha / snr_estimate, 0.1)
        
        # Apply gain to magnitude spectrum
        enhanced_magnitude = audio_magnitude * gain
        
        # Reconstruct signal
        enhanced_fft = enhanced_magnitude * np.exp(1j * audio_phase)
        enhanced_audio = np.real(np.fft.ifft(enhanced_fft))
        
        return enhanced_audio.astype(np.float32)

    def apply_compression(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Apply dynamic range compression
        
        Args:
            audio_data: Input audio samples
            
        Returns:
            np.ndarray: Compressed audio samples
        """
        # Calculate envelope
        envelope = np.abs(audio_data)
        
        # Apply compression above threshold
        compressed = np.where(
            envelope > self.compression_threshold,
            np.sign(audio_data) * (
                self.compression_threshold + 
                (envelope - self.compression_threshold) / self.compression_ratio
            ),
            audio_data
        )
        
        return compressed * self.gain

    def enhance_audio(self, audio_data: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Apply complete audio enhancement pipeline
        
        Args:
            audio_data: Input audio samples
            
        Returns:
            tuple: (Enhanced audio, Statistics)
        """
        stats = {
            'voice_activity': False,
            'noise_reduction_applied': False,
            'compression_applied': False,
            'input_level': 0.0,
            'output_level': 0.0,
            'enhancement_gain': 0.0
        }
        
        # Calculate input level
        input_rms = np.sqrt(np.mean(audio_data ** 2))
        stats['input_level'] = float(input_rms)
        
        # Voice activity detection
        has_voice = self.detect_voice_activity(audio_data)
        stats['voice_activity'] = has_voice
        
        enhanced = audio_data.copy()
        
        # Learn noise profile during silence
        if not has_voice and self.noise_frames_count < self.noise_learn_frames:
            self.learn_noise_profile(audio_data)
        
        # Apply noise reduction
        if self.noise_profile is not None:
            enhanced = self.reduce_noise(enhanced)
            stats['noise_reduction_applied'] = True
        
        # Apply dynamic compression
        enhanced = self.apply_compression(enhanced)
        stats['compression_applied'] = True
        
        # Calculate output level and gain
        output_rms = np.sqrt(np.mean(enhanced ** 2))
        stats['output_level'] = float(output_rms)
        stats['enhancement_gain'] = float(output_rms / (input_rms + 1e-10))
        
        return enhanced, stats

class AudioProcessor:
    """
    Main audio processor class integrating GStreamer with voice enhancement
    """
    
    def __init__(self, stream_name: str, client_addr: str, daemon_mode: bool = False):
        """
        Initialize audio processor
        
        Args:
            stream_name: Name of the audio stream
            client_addr: Publishing client address
            daemon_mode: Whether to run as daemon
        """
        self.stream_name = stream_name
        self.client_addr = client_addr
        self.daemon_mode = daemon_mode
        self.shutdown_event = Event()
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Voice enhancer
        self.enhancer = VoiceEnhancer()
        
        # Pipeline components
        self.pipeline = None
        self.bus = None
        self.loop = None
        
        # Statistics
        self.stats_lock = Lock()
        self.stats = {
            'stream_name': stream_name,
            'client_addr': client_addr,
            'start_time': time.time(),
            'frames_processed': 0,
            'voice_frames': 0,
            'silence_frames': 0,
            'average_input_level': 0.0,
            'average_output_level': 0.0,
            'enhancement_ratio': 1.0,
            'errors': 0,
            'status': 'initializing'
        }
        
        logger.info(f"🎤 [Audio Processor] Initialized for stream '{stream_name}' from {client_addr}")

    def create_pipeline(self) -> bool:
        """
        Create GStreamer pipeline for audio processing
        
        Returns:
            bool: True if pipeline created successfully
        """
        try:
            # Audio-optimized pipeline for voice processing
            pipeline_str = f"""
                rtmpsrc location=rtmp://localhost:1935/voice/{self.stream_name} ! 
                flvdemux name=demux
                
                demux.audio ! 
                decodebin ! 
                audioconvert ! 
                audioresample ! 
                audio/x-raw,format=F32LE,channels=1,rate=16000 !
                
                tee name=audio_tee
                
                audio_tee. ! queue max-size-time=100000000 ! 
                appsink name=enhancement_sink emit-signals=true sync=false max-buffers=10
                
                audio_tee. ! queue ! 
                audioconvert ! 
                audio/x-raw,format=S16LE,channels=1,rate=16000 !
                appsrc name=enhanced_src ! 
                audioconvert ! 
                voaacenc bitrate=64000 ! 
                aacparse ! 
                flvmux ! 
                rtmpsink location=rtmp://localhost:1935/enhanced/{self.stream_name}
            """
            
            logger.info("🔧 [Audio Processor] Creating audio processing pipeline")
            self.pipeline = Gst.parse_launch(pipeline_str)
            
            if not self.pipeline:
                logger.error("❌ [Audio Processor] Failed to create pipeline")
                return False
            
            # Set up bus for message handling
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_message)
            
            # Connect audio processing callbacks
            enhancement_sink = self.pipeline.get_by_name("enhancement_sink")
            if enhancement_sink:
                enhancement_sink.connect("new-sample", self.on_audio_sample)
            
            # Set up enhanced audio source
            self.enhanced_src = self.pipeline.get_by_name("enhanced_src")
            if self.enhanced_src:
                self.enhanced_src.set_property("format", Gst.Format.TIME)
                self.enhanced_src.set_property("caps", 
                    Gst.Caps.from_string("audio/x-raw,format=S16LE,channels=1,rate=16000"))
            
            logger.info("✅ [Audio Processor] Pipeline created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ [Audio Processor] Pipeline creation failed: {str(e)}")
            return False

    def on_audio_sample(self, sink) -> Gst.FlowReturn:
        """
        Process audio samples with enhancement
        
        Args:
            sink: The appsink element
            
        Returns:
            Gst.FlowReturn: Flow return status
        """
        try:
            sample = sink.emit("pull-sample")
            if sample is None:
                return Gst.FlowReturn.OK
            
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            
            # Extract audio data
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR
            
            # Convert to numpy array
            audio_data = np.frombuffer(map_info.data, dtype=np.float32)
            
            # Apply voice enhancement
            enhanced_audio, enhancement_stats = self.enhancer.enhance_audio(audio_data)
            
            # Update statistics
            with self.stats_lock:
                self.stats['frames_processed'] += 1
                
                if enhancement_stats['voice_activity']:
                    self.stats['voice_frames'] += 1
                else:
                    self.stats['silence_frames'] += 1
                
                # Running averages
                alpha = 0.95
                self.stats['average_input_level'] = (
                    alpha * self.stats['average_input_level'] + 
                    (1 - alpha) * enhancement_stats['input_level']
                )
                self.stats['average_output_level'] = (
                    alpha * self.stats['average_output_level'] + 
                    (1 - alpha) * enhancement_stats['output_level']
                )
                self.stats['enhancement_ratio'] = (
                    alpha * self.stats['enhancement_ratio'] + 
                    (1 - alpha) * enhancement_stats['enhancement_gain']
                )
            
            # Convert back to GStreamer buffer
            enhanced_bytes = (enhanced_audio * 32767).astype(np.int16).tobytes()
            
            # Push enhanced audio to output
            if self.enhanced_src:
                out_buffer = Gst.Buffer.new_allocate(None, len(enhanced_bytes), None)
                out_buffer.fill(0, enhanced_bytes)
                out_buffer.pts = buffer.pts
                out_buffer.duration = buffer.duration
                
                ret = self.enhanced_src.emit("push-buffer", out_buffer)
                if ret != Gst.FlowReturn.OK:
                    logger.warning(f"⚠️ [Audio Processor] Push buffer failed: {ret}")
            
            buffer.unmap(map_info)
            
            # Log stats periodically
            if self.stats['frames_processed'] % 200 == 0:  # Every ~4 seconds at 20ms frames
                self.log_processing_stats()
            
            return Gst.FlowReturn.OK
            
        except Exception as e:
            logger.error(f"❌ [Audio Processor] Sample processing error: {str(e)}")
            with self.stats_lock:
                self.stats['errors'] += 1
            return Gst.FlowReturn.ERROR

    def on_message(self, bus, message) -> bool:
        """Handle GStreamer bus messages"""
        msg_type = message.type
        
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"❌ [Audio Processor] Pipeline error: {err.message}")
            with self.stats_lock:
                self.stats['status'] = 'error'
                self.stats['errors'] += 1
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"⚠️ [Audio Processor] Pipeline warning: {warn.message}")
            
        elif msg_type == Gst.MessageType.EOS:
            logger.info("🏁 [Audio Processor] End of stream")
            with self.stats_lock:
                self.stats['status'] = 'completed'
            self.shutdown_event.set()
            
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(f"🔄 [Audio Processor] State: {old_state.value_nick} -> {new_state.value_nick}")
                
                with self.stats_lock:
                    if new_state == Gst.State.PLAYING:
                        self.stats['status'] = 'processing'
                    elif new_state == Gst.State.PAUSED:
                        self.stats['status'] = 'paused'
        
        return True

    def log_processing_stats(self):
        """Log current processing statistics"""
        with self.stats_lock:
            uptime = time.time() - self.stats['start_time']
            total_frames = self.stats['frames_processed']
            voice_ratio = self.stats['voice_frames'] / max(total_frames, 1)
            
            logger.info(
                f"📊 [Audio Processor] Stream: {self.stream_name}, "
                f"Uptime: {uptime:.1f}s, Frames: {total_frames}, "
                f"Voice: {voice_ratio:.1%}, "
                f"Input Level: {self.stats['average_input_level']:.3f}, "
                f"Output Level: {self.stats['average_output_level']:.3f}, "
                f"Enhancement: {self.stats['enhancement_ratio']:.2f}x, "
                f"Errors: {self.stats['errors']}"
            )

    def start_processing(self) -> bool:
        """Start audio processing"""
        try:
            if not self.create_pipeline():
                return False
            
            logger.info(f"🚀 [Audio Processor] Starting processing for '{self.stream_name}'")
            
            # Start pipeline
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("❌ [Audio Processor] Failed to start pipeline")
                return False
            
            # Create main loop
            self.loop = GLib.MainLoop()
            
            if self.daemon_mode:
                loop_thread = Thread(target=self.loop.run, daemon=True)
                loop_thread.start()
                logger.info("🔄 [Audio Processor] Running in daemon mode")
            else:
                self.loop.run()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [Audio Processor] Failed to start: {str(e)}")
            return False

    def stop_processing(self):
        """Stop audio processing"""
        try:
            logger.info(f"🛑 [Audio Processor] Stopping processing for '{self.stream_name}'")
            
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
            
            if self.loop and self.loop.is_running():
                self.loop.quit()
            
            with self.stats_lock:
                self.stats['status'] = 'stopped'
            
            self.log_processing_stats()
            logger.info("✅ [Audio Processor] Processing stopped")
            
        except Exception as e:
            logger.error(f"❌ [Audio Processor] Error stopping: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        with self.stats_lock:
            stats = self.stats.copy()
            stats['uptime'] = time.time() - stats['start_time']
            return stats

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"🛑 [Audio Processor] Received signal {signum}")
    if hasattr(signal_handler, 'processor'):
        signal_handler.processor.stop_processing()
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Advanced Audio Processor for Voice Streams')
    parser.add_argument('stream_name', nargs='?', help='Name of the audio stream')
    parser.add_argument('client_addr', nargs='?', help='Address of publishing client')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Handle daemon mode without specific stream
    if not args.stream_name and args.daemon:
        logger.info("🎤 [Audio Processor] Starting in daemon mode")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 [Audio Processor] Daemon stopped")
        return
    
    if not args.stream_name or not args.client_addr:
        logger.error("❌ [Audio Processor] Stream name and client address required")
        parser.print_help()
        sys.exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Create and start processor
        processor = AudioProcessor(args.stream_name, args.client_addr, args.daemon)
        signal_handler.processor = processor
        
        if processor.start_processing():
            logger.info(f"✅ [Audio Processor] Started successfully for '{args.stream_name}'")
            
            # Wait for completion
            if not args.daemon:
                processor.shutdown_event.wait()
            else:
                try:
                    while not processor.shutdown_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        else:
            logger.error("❌ [Audio Processor] Failed to start")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ [Audio Processor] Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        if 'processor' in locals():
            processor.stop_processing()

if __name__ == "__main__":
    main() 