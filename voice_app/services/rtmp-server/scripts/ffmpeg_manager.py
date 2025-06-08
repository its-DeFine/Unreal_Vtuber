#!/usr/bin/env python3
"""
FFmpeg Integration Manager for RTMP Server
Handles multi-quality transcoding, process orchestration, and stream management
within the single container architecture
"""

import sys
import os
import signal
import logging
import asyncio
import json
import time
import subprocess
import psutil
from typing import Dict, Any, List, Optional, Tuple
from threading import Thread, Event, Lock
from pathlib import Path
import argparse

# Configure logging with comprehensive details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ffmpeg_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FFmpegManager:
    """
    Advanced FFmpeg process manager for real-time transcoding
    Features:
    - Multi-quality stream generation (240p-1080p)
    - Hardware acceleration detection and usage
    - Process monitoring and automatic restart
    - Resource usage monitoring
    - Adaptive quality based on system resources
    - Stream health checking
    """
    
    def __init__(self, config_path: str = "/etc/nginx/nginx.conf"):
        """
        Initialize FFmpeg manager
        
        Args:
            config_path: Path to nginx configuration for stream detection
        """
        self.config_path = config_path
        self.shutdown_event = Event()
        self.processes_lock = Lock()
        
        # Active FFmpeg processes
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.process_stats: Dict[str, Dict] = {}
        
        # Quality profiles for adaptive streaming
        self.quality_profiles = {
            '240p': {
                'resolution': '426x240',
                'bitrate': '400k',
                'fps': 30,
                'preset': 'ultrafast',
                'profile': 'baseline'
            },
            '480p': {
                'resolution': '854x480', 
                'bitrate': '1000k',
                'fps': 30,
                'preset': 'fast',
                'profile': 'main'
            },
            '720p': {
                'resolution': '1280x720',
                'bitrate': '2500k',
                'fps': 30,
                'preset': 'medium',
                'profile': 'high'
            },
            '1080p': {
                'resolution': '1920x1080',
                'bitrate': '5000k',
                'fps': 30,
                'preset': 'medium',
                'profile': 'high'
            }
        }
        
        # Hardware acceleration detection
        self.hw_accel = self.detect_hardware_acceleration()
        
        # System resources
        self.system_stats = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'available_memory_gb': 0.0,
            'active_processes': 0,
            'total_bitrate_mbps': 0.0
        }
        
        logger.info(f"🎬 [FFmpeg] Manager initialized with hardware acceleration: {self.hw_accel}")

    def detect_hardware_acceleration(self) -> Dict[str, bool]:
        """
        Detect available hardware acceleration options
        
        Returns:
            dict: Available hardware acceleration capabilities
        """
        capabilities = {
            'nvenc': False,
            'vaapi': False,
            'qsv': False,
            'videotoolbox': False,
            'amf': False
        }
        
        try:
            # Check FFmpeg encoders
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=10)
            output = result.stdout.lower()
            
            capabilities['nvenc'] = 'h264_nvenc' in output
            capabilities['vaapi'] = 'h264_vaapi' in output
            capabilities['qsv'] = 'h264_qsv' in output
            capabilities['videotoolbox'] = 'h264_videotoolbox' in output
            capabilities['amf'] = 'h264_amf' in output
            
            logger.info(f"🔧 [FFmpeg] Hardware acceleration capabilities: {capabilities}")
            
        except Exception as e:
            logger.warning(f"⚠️ [FFmpeg] Error detecting hardware acceleration: {str(e)}")
        
        return capabilities

    def get_optimal_encoder(self) -> Tuple[str, str]:
        """
        Get the optimal video encoder and parameters based on available hardware
        
        Returns:
            tuple: (encoder_name, encoder_params)
        """
        if self.hw_accel['nvenc']:
            return 'h264_nvenc', '-preset p1 -tune ll -rc vbr -cq 23 -b:v {bitrate} -maxrate {maxrate} -bufsize {bufsize}'
        elif self.hw_accel['vaapi']:
            return 'h264_vaapi', '-vaapi_device /dev/dri/renderD128 -vf "format=nv12,hwupload" -c:v h264_vaapi -b:v {bitrate} -maxrate {maxrate}'
        elif self.hw_accel['qsv']:
            return 'h264_qsv', '-preset fast -b:v {bitrate} -maxrate {maxrate} -bufsize {bufsize}'
        elif self.hw_accel['videotoolbox']:
            return 'h264_videotoolbox', '-b:v {bitrate} -maxrate {maxrate} -bufsize {bufsize}'
        elif self.hw_accel['amf']:
            return 'h264_amf', '-usage transcoding -rc vbr_peak -b:v {bitrate} -maxrate {maxrate}'
        else:
            return 'libx264', '-preset ultrafast -tune zerolatency -b:v {bitrate} -maxrate {maxrate} -bufsize {bufsize}'

    def build_ffmpeg_command(self, input_stream: str, output_stream: str, 
                           quality: str, stream_key: str) -> List[str]:
        """
        Build FFmpeg command for specific quality transcoding
        
        Args:
            input_stream: Input RTMP stream URL
            output_stream: Output RTMP stream URL  
            quality: Quality profile (240p, 480p, 720p, 1080p)
            stream_key: Unique identifier for this stream
            
        Returns:
            list: FFmpeg command arguments
        """
        profile = self.quality_profiles[quality]
        encoder, encoder_params = self.get_optimal_encoder()
        
        # Calculate buffer sizes
        bitrate_num = int(profile['bitrate'].replace('k', ''))
        maxrate = f"{int(bitrate_num * 1.2)}k"
        bufsize = f"{int(bitrate_num * 2)}k"
        
        # Format encoder parameters
        encoder_params = encoder_params.format(
            bitrate=profile['bitrate'],
            maxrate=maxrate,
            bufsize=bufsize
        )
        
        # Build command with optimizations
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-i', input_stream,  # Input stream
            
            # Input optimization
            '-fflags', '+genpts+igndts',
            '-avoid_negative_ts', 'make_zero',
            '-max_delay', '0',
            '-use_wallclock_as_timestamps', '1',
            
            # Video encoding
            '-c:v', encoder,
            '-s', profile['resolution'],
            '-r', str(profile['fps']),
            '-g', str(profile['fps'] * 2),  # GOP size = 2 seconds
            '-keyint_min', str(profile['fps']),
            '-sc_threshold', '0',
            
            # Audio encoding
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '48000',
            '-ac', '2',
            
            # Output optimization
            '-f', 'flv',
            '-rtmp_live', 'live',
            '-rtmp_buffer', '100',
            '-rtmp_flush_interval', '10',
            
            output_stream
        ]
        
        # Add encoder-specific parameters
        if encoder_params:
            cmd.extend(encoder_params.split())
        
        # Add low-latency optimizations
        if 'nvenc' in encoder:
            cmd.extend(['-zerolatency', '1', '-delay', '0'])
        elif 'x264' in encoder:
            cmd.extend(['-x264-params', 'nal-hrd=cbr'])
        
        logger.info(f"🎬 [FFmpeg] Built command for {quality} transcoding: {' '.join(cmd[:10])}...")
        return cmd

    def start_transcoding(self, input_stream: str, stream_name: str, 
                         qualities: List[str] = None) -> bool:
        """
        Start multi-quality transcoding for a stream
        
        Args:
            input_stream: Source RTMP stream
            stream_name: Name identifier for the stream
            qualities: List of quality profiles to generate
            
        Returns:
            bool: True if transcoding started successfully
        """
        if qualities is None:
            # Auto-select qualities based on system resources
            qualities = self.select_optimal_qualities()
        
        success_count = 0
        
        with self.processes_lock:
            for quality in qualities:
                try:
                    # Build output stream URL
                    output_stream = f"rtmp://localhost:1935/live/{stream_name}_{quality}"
                    
                    # Build FFmpeg command
                    cmd = self.build_ffmpeg_command(input_stream, output_stream, quality, stream_name)
                    
                    # Start FFmpeg process
                    logger.info(f"🚀 [FFmpeg] Starting {quality} transcoding for stream '{stream_name}'")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=os.setsid  # Create new process group
                    )
                    
                    # Store process reference
                    process_key = f"{stream_name}_{quality}"
                    self.active_processes[process_key] = process
                    self.process_stats[process_key] = {
                        'stream_name': stream_name,
                        'quality': quality,
                        'start_time': time.time(),
                        'input_stream': input_stream,
                        'output_stream': output_stream,
                        'restarts': 0,
                        'status': 'starting'
                    }
                    
                    success_count += 1
                    logger.info(f"✅ [FFmpeg] Started {quality} transcoding process (PID: {process.pid})")
                    
                except Exception as e:
                    logger.error(f"❌ [FFmpeg] Failed to start {quality} transcoding: {str(e)}")
        
        if success_count > 0:
            logger.info(f"🎬 [FFmpeg] Started {success_count}/{len(qualities)} transcoding processes for '{stream_name}'")
            return True
        else:
            logger.error(f"❌ [FFmpeg] Failed to start any transcoding processes for '{stream_name}'")
            return False

    def select_optimal_qualities(self) -> List[str]:
        """
        Select optimal quality profiles based on system resources
        
        Returns:
            list: Recommended quality profiles
        """
        self.update_system_stats()
        
        cpu_percent = self.system_stats['cpu_percent']
        memory_gb = self.system_stats['available_memory_gb']
        
        # Quality selection logic based on resources
        if cpu_percent < 50 and memory_gb > 4:
            return ['240p', '480p', '720p', '1080p']  # Full quality range
        elif cpu_percent < 70 and memory_gb > 2:
            return ['240p', '480p', '720p']  # Medium quality range
        elif cpu_percent < 85 and memory_gb > 1:
            return ['240p', '480p']  # Basic quality range
        else:
            return ['240p']  # Minimal quality only
    
    def update_system_stats(self):
        """Update current system resource statistics"""
        try:
            self.system_stats['cpu_percent'] = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            self.system_stats['memory_percent'] = memory.percent
            self.system_stats['available_memory_gb'] = memory.available / (1024**3)
            
            with self.processes_lock:
                self.system_stats['active_processes'] = len(self.active_processes)
                
                # Calculate total bitrate
                total_bitrate = 0
                for stats in self.process_stats.values():
                    quality = stats['quality']
                    if quality in self.quality_profiles:
                        bitrate_str = self.quality_profiles[quality]['bitrate']
                        bitrate_kbps = int(bitrate_str.replace('k', ''))
                        total_bitrate += bitrate_kbps
                
                self.system_stats['total_bitrate_mbps'] = total_bitrate / 1000.0
                
        except Exception as e:
            logger.warning(f"⚠️ [FFmpeg] Error updating system stats: {str(e)}")

    def monitor_processes(self):
        """Monitor FFmpeg processes and restart if needed"""
        while not self.shutdown_event.is_set():
            try:
                self.update_system_stats()
                
                with self.processes_lock:
                    processes_to_restart = []
                    
                    for process_key, process in list(self.active_processes.items()):
                        try:
                            # Check if process is still running
                            if process.poll() is not None:
                                # Process has terminated
                                stats = self.process_stats.get(process_key, {})
                                logger.warning(f"⚠️ [FFmpeg] Process {process_key} terminated unexpectedly")
                                
                                # Schedule for restart if not too many failures
                                if stats.get('restarts', 0) < 5:
                                    processes_to_restart.append(process_key)
                                else:
                                    logger.error(f"❌ [FFmpeg] Process {process_key} failed too many times, not restarting")
                                    
                                # Remove from active processes
                                del self.active_processes[process_key]
                                if process_key in self.process_stats:
                                    self.process_stats[process_key]['status'] = 'failed'
                            else:
                                # Process is running, update status
                                if process_key in self.process_stats:
                                    self.process_stats[process_key]['status'] = 'running'
                                    
                        except Exception as e:
                            logger.error(f"❌ [FFmpeg] Error checking process {process_key}: {str(e)}")
                
                # Restart failed processes
                for process_key in processes_to_restart:
                    self.restart_process(process_key)
                
                # Log statistics periodically
                if len(self.active_processes) > 0:
                    logger.info(f"📊 [FFmpeg] Active processes: {len(self.active_processes)}, "
                              f"CPU: {self.system_stats['cpu_percent']:.1f}%, "
                              f"Memory: {self.system_stats['memory_percent']:.1f}%, "
                              f"Total bitrate: {self.system_stats['total_bitrate_mbps']:.1f} Mbps")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ [FFmpeg] Error in process monitoring: {str(e)}")
                time.sleep(5)

    def restart_process(self, process_key: str):
        """Restart a specific FFmpeg process"""
        try:
            if process_key not in self.process_stats:
                logger.error(f"❌ [FFmpeg] No stats found for process {process_key}")
                return
                
            stats = self.process_stats[process_key]
            stats['restarts'] += 1
            
            logger.info(f"🔄 [FFmpeg] Restarting process {process_key} (attempt {stats['restarts']})")
            
            # Start new transcoding process
            self.start_transcoding(
                stats['input_stream'], 
                stats['stream_name'], 
                [stats['quality']]
            )
            
        except Exception as e:
            logger.error(f"❌ [FFmpeg] Failed to restart process {process_key}: {str(e)}")

    def stop_transcoding(self, stream_name: str = None):
        """
        Stop transcoding processes
        
        Args:
            stream_name: Stop processes for specific stream, or all if None
        """
        try:
            with self.processes_lock:
                processes_to_stop = []
                
                if stream_name:
                    # Stop processes for specific stream
                    processes_to_stop = [key for key in self.active_processes.keys() 
                                       if key.startswith(f"{stream_name}_")]
                else:
                    # Stop all processes
                    processes_to_stop = list(self.active_processes.keys())
                
                for process_key in processes_to_stop:
                    try:
                        process = self.active_processes[process_key]
                        
                        logger.info(f"🛑 [FFmpeg] Stopping process {process_key} (PID: {process.pid})")
                        
                        # Send SIGTERM first
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        
                        # Wait for graceful shutdown
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            # Force kill if not responding
                            logger.warning(f"⚠️ [FFmpeg] Force killing process {process_key}")
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                        
                        # Remove from active processes
                        del self.active_processes[process_key]
                        if process_key in self.process_stats:
                            self.process_stats[process_key]['status'] = 'stopped'
                        
                        logger.info(f"✅ [FFmpeg] Stopped process {process_key}")
                        
                    except Exception as e:
                        logger.error(f"❌ [FFmpeg] Error stopping process {process_key}: {str(e)}")
                
        except Exception as e:
            logger.error(f"❌ [FFmpeg] Error in stop_transcoding: {str(e)}")

    def get_process_stats(self) -> Dict[str, Any]:
        """Get current process statistics"""
        with self.processes_lock:
            return {
                'system_stats': self.system_stats.copy(),
                'active_processes': len(self.active_processes),
                'process_details': self.process_stats.copy(),
                'hardware_acceleration': self.hw_accel
            }

    def start_monitoring(self):
        """Start the process monitoring thread"""
        monitor_thread = Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        logger.info("🔄 [FFmpeg] Process monitoring started")

def main():
    """Main entry point for FFmpeg manager"""
    parser = argparse.ArgumentParser(description='FFmpeg Integration Manager')
    parser.add_argument('--input-stream', required=True, help='Input RTMP stream URL')
    parser.add_argument('--stream-name', required=True, help='Stream name identifier')
    parser.add_argument('--qualities', nargs='+', 
                       choices=['240p', '480p', '720p', '1080p'],
                       help='Quality profiles to generate')
    parser.add_argument('--monitor-only', action='store_true', 
                       help='Only run monitoring without starting transcoding')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create FFmpeg manager
    manager = FFmpegManager()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"🛑 [FFmpeg] Received signal {signum}, shutting down...")
        manager.shutdown_event.set()
        manager.stop_transcoding()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start process monitoring
        manager.start_monitoring()
        
        if not args.monitor_only:
            # Start transcoding
            if manager.start_transcoding(args.input_stream, args.stream_name, args.qualities):
                logger.info(f"✅ [FFmpeg] Transcoding started successfully for '{args.stream_name}'")
            else:
                logger.error("❌ [FFmpeg] Failed to start transcoding")
                sys.exit(1)
        
        # Keep running until shutdown
        while not manager.shutdown_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 [FFmpeg] Interrupted by user")
    except Exception as e:
        logger.error(f"❌ [FFmpeg] Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        manager.stop_transcoding()

if __name__ == "__main__":
    main() 