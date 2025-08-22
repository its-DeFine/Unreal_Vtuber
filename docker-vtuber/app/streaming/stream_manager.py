"""
Unified Stream Manager for Multi-Destination Audio/Video Streaming
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Types of streams supported"""
    AUDIO_RTMP = "audio_rtmp"
    VIDEO_UNREAL = "video_unreal"
    DATA_AGGREGATION = "data_aggregation"
    HYBRID = "hybrid"  # Combined audio+video


class StreamProtocol(Enum):
    """Streaming protocols"""
    RTMP = "rtmp"
    RTMPS = "rtmps"
    HLS = "hls"
    WEBRTC = "webrtc"
    WEBSOCKET = "websocket"
    SRT = "srt"  # Secure Reliable Transport


@dataclass
class StreamDestination:
    """Configuration for a streaming destination"""
    name: str
    url: str
    protocol: StreamProtocol
    stream_type: StreamType
    enabled: bool = True
    priority: int = 0  # Higher = more important
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StreamSource:
    """Configuration for a stream source"""
    name: str
    source_type: str  # 'file', 'capture', 'pipeline', 'aggregator'
    location: str  # File path, device ID, or URL
    format: str  # 'wav', 'mp4', 'raw', etc.
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamManager:
    """
    Manages multiple streaming destinations and sources
    Coordinates audio, video, and data streaming
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.destinations: Dict[str, StreamDestination] = {}
        self.sources: Dict[str, StreamSource] = {}
        self.active_streams: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.config_path = config_path
        
        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
        
        # Initialize stream handlers
        self._init_handlers()
    
    def _init_handlers(self):
        """Initialize protocol-specific handlers"""
        self.handlers = {
            StreamProtocol.RTMP: self._handle_rtmp_stream,
            StreamProtocol.RTMPS: self._handle_rtmps_stream,
            StreamProtocol.HLS: self._handle_hls_stream,
            StreamProtocol.WEBRTC: self._handle_webrtc_stream,
            StreamProtocol.WEBSOCKET: self._handle_websocket_stream,
            StreamProtocol.SRT: self._handle_srt_stream,
        }
    
    def load_config(self, config_path: str):
        """Load streaming configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Load destinations
            for dest_config in config.get('destinations', []):
                dest = StreamDestination(
                    name=dest_config['name'],
                    url=dest_config['url'],
                    protocol=StreamProtocol(dest_config['protocol']),
                    stream_type=StreamType(dest_config['stream_type']),
                    enabled=dest_config.get('enabled', True),
                    priority=dest_config.get('priority', 0),
                    metadata=dest_config.get('metadata', {})
                )
                self.add_destination(dest)
            
            # Load sources
            for src_config in config.get('sources', []):
                src = StreamSource(
                    name=src_config['name'],
                    source_type=src_config['source_type'],
                    location=src_config['location'],
                    format=src_config['format'],
                    metadata=src_config.get('metadata', {})
                )
                self.add_source(src)
            
            logger.info(f"Loaded config: {len(self.destinations)} destinations, {len(self.sources)} sources")
        
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
    
    def add_destination(self, destination: StreamDestination):
        """Add a streaming destination"""
        with self._lock:
            self.destinations[destination.name] = destination
            logger.info(f"Added destination: {destination.name} ({destination.protocol.value})")
    
    def remove_destination(self, name: str):
        """Remove a streaming destination"""
        with self._lock:
            if name in self.destinations:
                # Stop any active streams to this destination
                self.stop_stream(name)
                del self.destinations[name]
                logger.info(f"Removed destination: {name}")
    
    def add_source(self, source: StreamSource):
        """Add a stream source"""
        with self._lock:
            self.sources[source.name] = source
            logger.info(f"Added source: {source.name} ({source.source_type})")
    
    def remove_source(self, name: str):
        """Remove a stream source"""
        with self._lock:
            if name in self.sources:
                del self.sources[name]
                logger.info(f"Removed source: {name}")
    
    def get_destinations_by_type(self, stream_type: StreamType) -> List[StreamDestination]:
        """Get all destinations of a specific type"""
        with self._lock:
            return [
                dest for dest in self.destinations.values()
                if dest.stream_type == stream_type and dest.enabled
            ]
    
    def get_enabled_destinations(self) -> List[StreamDestination]:
        """Get all enabled destinations sorted by priority"""
        with self._lock:
            enabled = [dest for dest in self.destinations.values() if dest.enabled]
            return sorted(enabled, key=lambda x: x.priority, reverse=True)
    
    async def start_stream(
        self,
        source_name: str,
        destination_names: Optional[List[str]] = None,
        stream_type: Optional[StreamType] = None
    ):
        """
        Start streaming from a source to one or more destinations
        
        Args:
            source_name: Name of the source to stream from
            destination_names: List of destination names. If None, use all enabled destinations
            stream_type: Type of stream. If None, auto-detect from source
        """
        with self._lock:
            if source_name not in self.sources:
                raise ValueError(f"Source '{source_name}' not found")
            
            source = self.sources[source_name]
            
            # Determine destinations
            if destination_names:
                destinations = [
                    self.destinations[name] 
                    for name in destination_names 
                    if name in self.destinations
                ]
            else:
                destinations = self.get_enabled_destinations()
            
            if not destinations:
                logger.warning("No destinations available for streaming")
                return
            
            # Start streaming to each destination
            tasks = []
            for dest in destinations:
                if dest.enabled:
                    task = asyncio.create_task(
                        self._stream_to_destination(source, dest)
                    )
                    tasks.append(task)
                    
                    # Track active stream
                    stream_id = f"{source_name}->{dest.name}"
                    self.active_streams[stream_id] = {
                        'source': source_name,
                        'destination': dest.name,
                        'task': task,
                        'started_at': asyncio.get_event_loop().time()
                    }
            
            # Wait for all streams to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _stream_to_destination(self, source: StreamSource, destination: StreamDestination):
        """Stream from source to destination using appropriate handler"""
        try:
            logger.info(f"Starting stream: {source.name} -> {destination.name}")
            
            # Get appropriate handler
            handler = self.handlers.get(destination.protocol)
            if not handler:
                raise ValueError(f"Unsupported protocol: {destination.protocol}")
            
            # Execute streaming
            await handler(source, destination)
            
            logger.info(f"Stream completed: {source.name} -> {destination.name}")
        
        except Exception as e:
            logger.error(f"Stream failed {source.name} -> {destination.name}: {e}")
            raise
    
    def stop_stream(self, stream_id: str):
        """Stop a specific active stream"""
        with self._lock:
            if stream_id in self.active_streams:
                stream_info = self.active_streams[stream_id]
                if 'task' in stream_info and not stream_info['task'].done():
                    stream_info['task'].cancel()
                del self.active_streams[stream_id]
                logger.info(f"Stopped stream: {stream_id}")
    
    def stop_all_streams(self):
        """Stop all active streams"""
        with self._lock:
            for stream_id in list(self.active_streams.keys()):
                self.stop_stream(stream_id)
            logger.info("Stopped all streams")
    
    def get_active_streams(self) -> Dict[str, Any]:
        """Get information about active streams"""
        with self._lock:
            return dict(self.active_streams)
    
    # Protocol-specific handlers
    
    async def _handle_rtmp_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle RTMP streaming"""
        # Import here to avoid circular dependency
        from ..AVATAR.NeuroBridge.NeuroSync_Player.utils.audio.gst_stream import stream_wav_to_rtmp
        
        if source.format == 'wav' and source.source_type == 'file':
            # Use existing GStreamer implementation
            await asyncio.get_event_loop().run_in_executor(
                None,
                stream_wav_to_rtmp,
                source.location,
                destination.url,
                True  # blocking
            )
        else:
            # TODO: Implement other source types
            raise NotImplementedError(f"RTMP streaming for {source.source_type} not yet implemented")
    
    async def _handle_rtmps_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle RTMPS (secure RTMP) streaming"""
        # Similar to RTMP but with TLS
        destination.url = destination.url.replace('rtmps://', 'rtmp://')
        destination.metadata['tls'] = True
        await self._handle_rtmp_stream(source, destination)
    
    async def _handle_hls_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle HLS streaming"""
        # TODO: Implement HLS streaming
        raise NotImplementedError("HLS streaming not yet implemented")
    
    async def _handle_webrtc_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle WebRTC streaming"""
        # TODO: Implement WebRTC streaming
        raise NotImplementedError("WebRTC streaming not yet implemented")
    
    async def _handle_websocket_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle WebSocket streaming"""
        # TODO: Implement WebSocket streaming
        raise NotImplementedError("WebSocket streaming not yet implemented")
    
    async def _handle_srt_stream(self, source: StreamSource, destination: StreamDestination):
        """Handle SRT streaming"""
        # TODO: Implement SRT streaming
        raise NotImplementedError("SRT streaming not yet implemented")


# Singleton instance
_stream_manager = None


def get_stream_manager(config_path: Optional[str] = None) -> StreamManager:
    """Get or create the global stream manager instance"""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager(config_path)
    return _stream_manager