#!/usr/bin/env python3
"""
Audio Quality Manager for LLM + TTS RTMP Streaming
Handles audio-only multi-quality stream generation for real-time voice production
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/audio_quality_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AudioQualityManager:
    """
    Audio-only quality manager for LLM + TTS streaming
    Features:
    - Multiple audio bitrates (64k, 128k, 256k)
    - Optimized for voice/speech content
    - Real-time transcoding from TTS output
    - RTMP audio streaming without video overhead
    """
    
    def __init__(self):
        self.shutdown_event = Event()
        self.processes_lock = Lock()
        
        # Active audio processes
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.process_stats: Dict[str, Dict] = {}
        
        # Audio quality profiles optimized for voice/TTS
        self.audio_profiles = {
            'low': {
                'bitrate': '64k',
                'sample_rate': 22050,
                'channels': 1,  # Mono for voice
                'format': 'aac',
                'description': 'Low bandwidth voice (mobile/poor connection)'
            },
            'medium': {
                'bitrate': '128k', 
                'sample_rate': 44100,
                'channels': 2,  # Stereo
                'format': 'aac',
                'description': 'Standard quality voice (default)'
            },
            'high': {
                'bitrate': '256k',
                'sample_rate': 48000,
                'channels': 2,  # Stereo
                'format': 'aac',
                'description': 'High quality voice (good connection)'
            }
        }
        
        logger.info(f"🎤 [AudioQuality] Manager initialized with {len(self.audio_profiles)} audio profiles")

    def build_audio_ffmpeg_command(self, input_stream: str, output_stream: str, 
                                 profile_name: str, stream_key: str) -> List[str]:
        """
        Build FFmpeg command for audio-only transcoding
        
        Args:
            input_stream: Input audio source (TTS output, microphone, etc.)
            output_stream: Output RTMP stream URL
            profile_name: Audio quality profile (low, medium, high)
            stream_key: Unique identifier for this stream
            
        Returns:
            list: FFmpeg command arguments optimized for audio
        """
        profile = self.audio_profiles[profile_name]
        
        # Build audio-focused FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-i', input_stream,  # Input audio stream
            
            # Input optimization for real-time audio
            '-fflags', '+genpts',
            '-avoid_negative_ts', 'make_zero',
            '-max_delay', '0',
            
            # Audio processing - optimized for voice/TTS
            '-c:a', 'aac',
            '-b:a', profile['bitrate'],
            '-ar', str(profile['sample_rate']),
            '-ac', str(profile['channels']),
            
            # Audio quality settings for voice
            '-profile:a', 'aac_low' if profile['bitrate'] == '64k' else 'aac_main',
            '-movflags', '+faststart',
            
            # Remove video completely (audio-only)
            '-vn',  # No video
            
            # Output optimization for RTMP
            '-f', 'flv',
            '-rtmp_live', 'live',
            '-rtmp_buffer', '100',
            '-rtmp_flush_interval', '10',
            
            output_stream
        ]
        
        # Add voice-specific optimizations
        if 'voice' in stream_key.lower() or 'tts' in stream_key.lower():
            # Optimize for speech content
            cmd.extend([
                '-af', 'highpass=f=80,lowpass=f=8000,volume=1.2',  # Voice frequency range
                '-compression_level', '1'  # Fast compression for real-time
            ])
        
        logger.info(f"🎤 [AudioQuality] Built {profile_name} audio command: {' '.join(cmd[:8])}...")
        return cmd

    def start_audio_transcoding(self, input_source: str, stream_name: str, 
                              profiles: List[str] = None) -> bool:
        """
        Start multi-quality audio transcoding for a stream
        
        Args:
            input_source: Audio input source (file, device, stream)
            stream_name: Name identifier for the stream
            profiles: List of audio quality profiles to generate
            
        Returns:
            bool: True if transcoding started successfully
        """
        if profiles is None:
            profiles = ['medium']  # Default to medium quality for TTS
        
        success_count = 0
        
        with self.processes_lock:
            for profile_name in profiles:
                try:
                    if profile_name not in self.audio_profiles:
                        logger.warning(f"⚠️ [AudioQuality] Unknown profile: {profile_name}")
                        continue
                    
                    # Build output stream URL for audio
                    output_stream = f"rtmp://localhost:1935/live/{stream_name}_{profile_name}"
                    
                    # Build FFmpeg command
                    cmd = self.build_audio_ffmpeg_command(
                        input_source, output_stream, profile_name, stream_name
                    )
                    
                    # Start FFmpeg process
                    profile_desc = self.audio_profiles[profile_name]['description']
                    logger.info(f"🚀 [AudioQuality] Starting {profile_name} audio transcoding: {profile_desc}")
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=os.setsid  # Create new process group
                    )
                    
                    # Store process reference
                    process_key = f"{stream_name}_{profile_name}"
                    self.active_processes[process_key] = process
                    self.process_stats[process_key] = {
                        'stream_name': stream_name,
                        'profile': profile_name,
                        'profile_desc': profile_desc,
                        'start_time': time.time(),
                        'input_source': input_source,
                        'output_stream': output_stream,
                        'restarts': 0,
                        'status': 'starting',
                        'bitrate': self.audio_profiles[profile_name]['bitrate'],
                        'sample_rate': self.audio_profiles[profile_name]['sample_rate'],
                        'channels': self.audio_profiles[profile_name]['channels']
                    }
                    
                    success_count += 1
                    logger.info(f"✅ [AudioQuality] Started {profile_name} audio process (PID: {process.pid})")
                    
                except Exception as e:
                    logger.error(f"❌ [AudioQuality] Failed to start {profile_name} transcoding: {str(e)}")
        
        if success_count > 0:
            logger.info(f"🎤 [AudioQuality] Started {success_count}/{len(profiles)} audio processes for '{stream_name}'")
            return True
        else:
            logger.error(f"❌ [AudioQuality] Failed to start any audio processes for '{stream_name}'")
            return False

    def create_tts_pipeline(self, tts_text: str, stream_name: str, 
                          voice_model: str = "tts_models/en/ljspeech/tacotron2-DDC") -> bool:
        """
        Create a TTS → RTMP pipeline for real-time text-to-speech streaming
        
        Args:
            tts_text: Text to convert to speech
            stream_name: Stream identifier
            voice_model: TTS model to use
            
        Returns:
            bool: True if pipeline created successfully
        """
        try:
            logger.info(f"🎙️ [AudioQuality] Creating TTS pipeline for: '{tts_text[:50]}...'")
            
            # Create named pipe for TTS output
            pipe_path = f"/tmp/tts_output_{stream_name}.wav"
            
            # Generate TTS audio to pipe
            tts_cmd = [
                'tts',
                '--text', tts_text,
                '--model_name', voice_model,
                '--out_path', pipe_path
            ]
            
            # Start TTS generation
            tts_process = subprocess.Popen(tts_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tts_process.wait()  # Wait for TTS completion
            
            if tts_process.returncode == 0:
                # Start audio transcoding from TTS output
                return self.start_audio_transcoding(pipe_path, f"tts_{stream_name}", ['medium', 'high'])
            else:
                logger.error("❌ [AudioQuality] TTS generation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ [AudioQuality] TTS pipeline creation failed: {str(e)}")
            return False

    def monitor_audio_processes(self):
        """Monitor audio transcoding processes and restart if needed"""
        while not self.shutdown_event.is_set():
            try:
                with self.processes_lock:
                    processes_to_restart = []
                    
                    for process_key, process in list(self.active_processes.items()):
                        try:
                            # Check if process is still running
                            if process.poll() is not None:
                                # Process has terminated
                                stats = self.process_stats.get(process_key, {})
                                logger.warning(f"⚠️ [AudioQuality] Audio process {process_key} terminated")
                                
                                # Schedule for restart if not too many failures
                                if stats.get('restarts', 0) < 3:  # Fewer retries for audio
                                    processes_to_restart.append(process_key)
                                else:
                                    logger.error(f"❌ [AudioQuality] Audio process {process_key} failed too many times")
                                    
                                # Remove from active processes
                                del self.active_processes[process_key]
                                if process_key in self.process_stats:
                                    self.process_stats[process_key]['status'] = 'failed'
                            else:
                                # Process is running, update status
                                if process_key in self.process_stats:
                                    self.process_stats[process_key]['status'] = 'running'
                                    
                        except Exception as e:
                            logger.error(f"❌ [AudioQuality] Error checking audio process {process_key}: {str(e)}")
                
                # Restart failed processes
                for process_key in processes_to_restart:
                    self.restart_audio_process(process_key)
                
                # Log audio statistics
                if len(self.active_processes) > 0:
                    total_bitrate = sum(
                        int(stats.get('bitrate', '0k').replace('k', '')) 
                        for stats in self.process_stats.values()
                    )
                    logger.info(f"🎤 [AudioQuality] Active audio streams: {len(self.active_processes)}, "
                              f"Total bitrate: {total_bitrate} kbps")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ [AudioQuality] Error in audio process monitoring: {str(e)}")
                time.sleep(5)

    def restart_audio_process(self, process_key: str):
        """Restart a specific audio transcoding process"""
        try:
            if process_key not in self.process_stats:
                logger.error(f"❌ [AudioQuality] No stats found for audio process {process_key}")
                return
                
            stats = self.process_stats[process_key]
            stats['restarts'] += 1
            
            logger.info(f"🔄 [AudioQuality] Restarting audio process {process_key} (attempt {stats['restarts']})")
            
            # Start new audio transcoding process
            self.start_audio_transcoding(
                stats['input_source'], 
                stats['stream_name'], 
                [stats['profile']]
            )
            
        except Exception as e:
            logger.error(f"❌ [AudioQuality] Failed to restart audio process {process_key}: {str(e)}")

    def stop_audio_transcoding(self, stream_name: str = None):
        """Stop audio transcoding processes"""
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
                        
                        logger.info(f"🛑 [AudioQuality] Stopping audio process {process_key} (PID: {process.pid})")
                        
                        # Send SIGTERM first
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        
                        # Wait for graceful shutdown
                        try:
                            process.wait(timeout=5)  # Shorter timeout for audio
                        except subprocess.TimeoutExpired:
                            # Force kill if not responding
                            logger.warning(f"⚠️ [AudioQuality] Force killing audio process {process_key}")
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                        
                        # Remove from active processes
                        del self.active_processes[process_key]
                        if process_key in self.process_stats:
                            self.process_stats[process_key]['status'] = 'stopped'
                        
                        logger.info(f"✅ [AudioQuality] Stopped audio process {process_key}")
                        
                    except Exception as e:
                        logger.error(f"❌ [AudioQuality] Error stopping audio process {process_key}: {str(e)}")
                
        except Exception as e:
            logger.error(f"❌ [AudioQuality] Error in stop_audio_transcoding: {str(e)}")

    def get_audio_stats(self) -> Dict[str, Any]:
        """Get current audio transcoding statistics"""
        with self.processes_lock:
            return {
                'active_audio_streams': len(self.active_processes),
                'audio_profiles': self.audio_profiles,
                'process_details': self.process_stats.copy(),
                'total_audio_bitrate_kbps': sum(
                    int(stats.get('bitrate', '0k').replace('k', '')) 
                    for stats in self.process_stats.values()
                )
            }

def main():
    """Main entry point for audio quality manager"""
    parser = argparse.ArgumentParser(description='Audio Quality Manager for LLM + TTS')
    parser.add_argument('--input-source', required=True, help='Audio input source')
    parser.add_argument('--stream-name', required=True, help='Stream name identifier')
    parser.add_argument('--profiles', nargs='+', 
                       choices=['low', 'medium', 'high'],
                       default=['medium'],
                       help='Audio quality profiles to generate')
    parser.add_argument('--tts-mode', action='store_true', 
                       help='Enable TTS pipeline mode')
    parser.add_argument('--tts-text', help='Text for TTS mode')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create audio quality manager
    manager = AudioQualityManager()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"🛑 [AudioQuality] Received signal {signum}, shutting down...")
        manager.shutdown_event.set()
        manager.stop_audio_transcoding()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start process monitoring
        monitor_thread = Thread(target=manager.monitor_audio_processes, daemon=True)
        monitor_thread.start()
        
        if args.tts_mode and args.tts_text:
            # TTS pipeline mode
            if manager.create_tts_pipeline(args.tts_text, args.stream_name):
                logger.info(f"✅ [AudioQuality] TTS pipeline started for '{args.stream_name}'")
            else:
                logger.error("❌ [AudioQuality] Failed to start TTS pipeline")
                sys.exit(1)
        else:
            # Standard audio transcoding mode
            if manager.start_audio_transcoding(args.input_source, args.stream_name, args.profiles):
                logger.info(f"✅ [AudioQuality] Audio transcoding started for '{args.stream_name}'")
            else:
                logger.error("❌ [AudioQuality] Failed to start audio transcoding")
                sys.exit(1)
        
        # Keep running until shutdown
        while not manager.shutdown_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 [AudioQuality] Interrupted by user")
    except Exception as e:
        logger.error(f"❌ [AudioQuality] Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        manager.stop_audio_transcoding()

if __name__ == "__main__":
    main() 