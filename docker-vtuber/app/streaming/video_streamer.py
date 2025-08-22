"""
Unreal Engine Video Streaming Module
Captures and streams Unreal Engine viewport to multiple destinations
"""

import asyncio
import logging
import subprocess
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UnrealStreamConfig:
    """Configuration for Unreal Engine streaming"""
    capture_method: str = "pixel_streaming"  # or "ndi", "spout", "render_target"
    resolution: str = "1920x1080"
    framerate: int = 30
    bitrate: str = "4000k"
    codec: str = "h264"  # or "h265", "vp9"
    pixel_format: str = "yuv420p"
    preset: str = "fast"  # ultrafast, superfast, veryfast, faster, fast, medium, slow
    
    # Unreal-specific settings
    viewport_name: str = "main"
    capture_alpha: bool = False
    capture_hdr: bool = False
    
    # Network settings
    buffer_size: int = 1024 * 1024  # 1MB
    low_latency: bool = True
    
    def to_ffmpeg_args(self) -> List[str]:
        """Convert config to FFmpeg arguments"""
        args = []
        
        # Video codec settings
        if self.codec == "h264":
            args.extend(["-c:v", "libx264"])
            args.extend(["-preset", self.preset])
            args.extend(["-tune", "zerolatency" if self.low_latency else "film"])
        elif self.codec == "h265":
            args.extend(["-c:v", "libx265"])
            args.extend(["-preset", self.preset])
        elif self.codec == "vp9":
            args.extend(["-c:v", "libvpx-vp9"])
            args.extend(["-deadline", "realtime" if self.low_latency else "good"])
        
        # Common video settings
        args.extend(["-pix_fmt", self.pixel_format])
        args.extend(["-b:v", self.bitrate])
        args.extend(["-r", str(self.framerate)])
        
        # Resolution
        if "x" in self.resolution:
            args.extend(["-s", self.resolution])
        
        # Low latency optimizations
        if self.low_latency:
            args.extend(["-flags", "+low_delay"])
            args.extend(["-fflags", "+nobuffer+flush_packets"])
            args.extend(["-max_delay", "0"])
        
        return args


class UnrealVideoStreamer:
    """
    Manages video capture and streaming from Unreal Engine
    """
    
    def __init__(self, config: Optional[UnrealStreamConfig] = None):
        self.config = config or UnrealStreamConfig()
        self.capture_process: Optional[subprocess.Popen] = None
        self.stream_processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()
        self._running = False
        
        # Pixel Streaming WebRTC signaling
        self.signaling_server: Optional[str] = os.getenv(
            "UNREAL_SIGNALING_SERVER", 
            "ws://localhost:8888"
        )
        
        # NDI settings (if using NDI)
        self.ndi_source_name = os.getenv("UNREAL_NDI_SOURCE", "Unreal Engine")
    
    def start_pixel_streaming_capture(self) -> Optional[subprocess.Popen]:
        """
        Start capturing from Unreal Engine's Pixel Streaming
        Returns a process that outputs raw video frames
        """
        try:
            # Build FFmpeg command to capture from Pixel Streaming
            cmd = [
                "ffmpeg",
                "-f", "lavfi",  # Use lavfi for now, replace with actual capture
                "-i", f"testsrc=size={self.config.resolution}:rate={self.config.framerate}",
                "-f", "rawvideo",
                "-pix_fmt", self.config.pixel_format,
                "-"
            ]
            
            # TODO: Replace with actual Pixel Streaming capture
            # This would involve WebRTC connection to Unreal's Pixel Streaming plugin
            
            logger.info(f"Starting Pixel Streaming capture: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.config.buffer_size
            )
            
            return process
        
        except Exception as e:
            logger.error(f"Failed to start Pixel Streaming capture: {e}")
            return None
    
    def start_ndi_capture(self) -> Optional[subprocess.Popen]:
        """
        Start capturing from Unreal Engine via NDI
        NDI (Network Device Interface) allows low-latency video over network
        """
        try:
            # Use FFmpeg with NDI input (requires FFmpeg built with NDI support)
            cmd = [
                "ffmpeg",
                "-f", "libndi_newtek",
                "-i", self.ndi_source_name,
                "-f", "rawvideo",
                "-pix_fmt", self.config.pixel_format,
                "-"
            ]
            
            logger.info(f"Starting NDI capture from: {self.ndi_source_name}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.config.buffer_size
            )
            
            return process
        
        except Exception as e:
            logger.error(f"Failed to start NDI capture: {e}")
            return None
    
    def start_window_capture(self, window_name: str = "UnrealEditor") -> Optional[subprocess.Popen]:
        """
        Capture directly from Unreal Engine window (Linux/Windows)
        """
        try:
            # Platform-specific capture
            if os.name == 'posix':  # Linux
                # Use x11grab to capture window
                cmd = [
                    "ffmpeg",
                    "-f", "x11grab",
                    "-framerate", str(self.config.framerate),
                    "-video_size", self.config.resolution,
                    "-i", f":0.0+0,0",  # Display :0.0 at position 0,0
                    "-f", "rawvideo",
                    "-pix_fmt", self.config.pixel_format,
                    "-"
                ]
            else:  # Windows
                # Use gdigrab for Windows
                cmd = [
                    "ffmpeg",
                    "-f", "gdigrab",
                    "-framerate", str(self.config.framerate),
                    "-i", f"title={window_name}",
                    "-f", "rawvideo",
                    "-pix_fmt", self.config.pixel_format,
                    "-"
                ]
            
            logger.info(f"Starting window capture: {window_name}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.config.buffer_size
            )
            
            return process
        
        except Exception as e:
            logger.error(f"Failed to start window capture: {e}")
            return None
    
    async def stream_to_rtmp(
        self,
        rtmp_url: str,
        capture_source: Optional[subprocess.Popen] = None
    ):
        """
        Stream video to RTMP server
        
        Args:
            rtmp_url: RTMP destination URL
            capture_source: Video capture process (if None, starts new capture)
        """
        with self._lock:
            try:
                # Start capture if not provided
                if capture_source is None:
                    if self.config.capture_method == "pixel_streaming":
                        capture_source = self.start_pixel_streaming_capture()
                    elif self.config.capture_method == "ndi":
                        capture_source = self.start_ndi_capture()
                    else:
                        capture_source = self.start_window_capture()
                
                if not capture_source:
                    raise RuntimeError("Failed to start video capture")
                
                # Build FFmpeg command for RTMP streaming
                cmd = [
                    "ffmpeg",
                    "-f", "rawvideo",
                    "-pix_fmt", self.config.pixel_format,
                    "-s", self.config.resolution,
                    "-r", str(self.config.framerate),
                    "-i", "-",  # Read from stdin
                ]
                
                # Add codec settings
                cmd.extend(self.config.to_ffmpeg_args())
                
                # Add audio (if available)
                # TODO: Sync with audio from NeuroSync
                
                # Output settings
                cmd.extend([
                    "-f", "flv",  # FLV format for RTMP
                    "-flvflags", "no_duration_filesize",
                    rtmp_url
                ])
                
                logger.info(f"Starting RTMP stream to: {rtmp_url}")
                
                # Start streaming process
                stream_process = subprocess.Popen(
                    cmd,
                    stdin=capture_source.stdout,
                    stderr=subprocess.PIPE
                )
                
                # Store process reference
                self.stream_processes[rtmp_url] = stream_process
                
                # Monitor streaming
                await self._monitor_stream(stream_process, rtmp_url)
            
            except Exception as e:
                logger.error(f"Failed to stream to {rtmp_url}: {e}")
                raise
    
    async def stream_to_multiple(
        self,
        destinations: List[Dict[str, Any]],
        capture_source: Optional[subprocess.Popen] = None
    ):
        """
        Stream to multiple destinations simultaneously
        
        Args:
            destinations: List of destination configs with 'url' and 'protocol'
            capture_source: Shared video capture source
        """
        # Start capture once
        if capture_source is None:
            if self.config.capture_method == "pixel_streaming":
                capture_source = self.start_pixel_streaming_capture()
            elif self.config.capture_method == "ndi":
                capture_source = self.start_ndi_capture()
            else:
                capture_source = self.start_window_capture()
        
        if not capture_source:
            raise RuntimeError("Failed to start video capture")
        
        # Use tee command to split output to multiple destinations
        tasks = []
        for dest in destinations:
            if dest['protocol'] == 'rtmp':
                task = asyncio.create_task(
                    self.stream_to_rtmp(dest['url'], capture_source)
                )
                tasks.append(task)
            # Add other protocols as needed
        
        # Wait for all streams
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _monitor_stream(self, process: subprocess.Popen, url: str):
        """Monitor streaming process for errors"""
        try:
            while process.poll() is None:
                # Read stderr for any errors/warnings
                if process.stderr:
                    line = process.stderr.readline()
                    if line:
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        if line_str:
                            if 'error' in line_str.lower():
                                logger.error(f"Stream error ({url}): {line_str}")
                            else:
                                logger.debug(f"Stream ({url}): {line_str}")
                
                await asyncio.sleep(1)
            
            # Process ended
            if process.returncode != 0:
                logger.error(f"Stream to {url} ended with code: {process.returncode}")
            else:
                logger.info(f"Stream to {url} ended normally")
        
        except Exception as e:
            logger.error(f"Error monitoring stream {url}: {e}")
    
    def stop_stream(self, url: str):
        """Stop streaming to a specific URL"""
        with self._lock:
            if url in self.stream_processes:
                process = self.stream_processes[url]
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                del self.stream_processes[url]
                logger.info(f"Stopped stream to: {url}")
    
    def stop_all_streams(self):
        """Stop all active streams"""
        with self._lock:
            urls = list(self.stream_processes.keys())
            for url in urls:
                self.stop_stream(url)
            
            # Stop capture if running
            if self.capture_process and self.capture_process.poll() is None:
                self.capture_process.terminate()
                try:
                    self.capture_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.capture_process.kill()
                self.capture_process = None
            
            logger.info("Stopped all video streams")


# Global instance
_video_streamer = None


def get_video_streamer(config: Optional[UnrealStreamConfig] = None) -> UnrealVideoStreamer:
    """Get or create the global video streamer instance"""
    global _video_streamer
    if _video_streamer is None:
        _video_streamer = UnrealVideoStreamer(config)
    return _video_streamer