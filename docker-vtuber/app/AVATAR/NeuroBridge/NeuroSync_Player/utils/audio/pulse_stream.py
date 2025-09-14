#!/usr/bin/env python3
"""
PulseAudio streaming for ultra-low latency (10-30ms)
Works with WSL2/Docker setup where game runs on Windows host
"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

def setup_pulseaudio_bridge():
    """
    Setup PulseAudio server connection for WSL2/Docker to Windows host
    """
    try:
        # Check if PulseAudio is available
        result = subprocess.run(['pactl', 'info'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            logger.info("[PulseAudio] Connected to PulseAudio server")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try to connect to Windows host PulseAudio
    windows_host = os.getenv('PULSE_SERVER', 'tcp:host.docker.internal:4713')
    os.environ['PULSE_SERVER'] = windows_host
    
    try:
        result = subprocess.run(['pactl', 'info'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            logger.info(f"[PulseAudio] Connected to Windows host at {windows_host}")
            return True
    except:
        logger.warning("[PulseAudio] Could not connect to PulseAudio server")
        return False

def stream_wav_to_pulseaudio(wav_path, blocking=True):
    """
    Stream WAV file directly to PulseAudio for ultra-low latency
    
    Args:
        wav_path: Path to WAV file
        blocking: If True, wait for playback to complete
    """
    if not setup_pulseaudio_bridge():
        raise RuntimeError("PulseAudio not available")
    
    try:
        # Use paplay for direct PulseAudio playback with minimal buffering
        cmd = [
            'paplay',
            '--latency-msec=10',  # Ultra-low latency buffer
            '--process-time-msec=5',  # Minimal processing time
            wav_path
        ]
        
        logger.info(f"[PulseAudio] Streaming {wav_path} with 10ms latency buffer")
        
        if blocking:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"[PulseAudio] Playback failed: {result.stderr}")
                raise RuntimeError(f"PulseAudio playback failed: {result.stderr}")
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        logger.info("[PulseAudio] Streaming completed successfully")
        
    except Exception as e:
        logger.error(f"[PulseAudio] Error streaming: {e}")
        raise

def create_pulseaudio_sink(sink_name="vtuber_output", description="VTuber Audio Output"):
    """
    Create a virtual PulseAudio sink that OBS can monitor
    """
    try:
        # Create null sink
        cmd = [
            'pactl', 'load-module', 'module-null-sink',
            f'sink_name={sink_name}',
            f'sink_properties=device.description="{description}"'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"[PulseAudio] Created virtual sink: {sink_name}")
            return sink_name
        else:
            # Sink might already exist
            logger.info(f"[PulseAudio] Virtual sink may already exist: {result.stderr}")
            return sink_name
            
    except Exception as e:
        logger.error(f"[PulseAudio] Failed to create sink: {e}")
        return None

def stream_to_virtual_sink(wav_path, sink_name="vtuber_output"):
    """
    Stream audio to a virtual PulseAudio sink for OBS capture
    """
    try:
        cmd = [
            'paplay',
            '--latency-msec=10',
            '--device', sink_name,
            wav_path
        ]
        
        logger.info(f"[PulseAudio] Streaming to virtual sink {sink_name}")
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"[PulseAudio] Failed to stream to sink: {e}")
        raise