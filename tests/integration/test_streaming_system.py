"""
Comprehensive tests for the multi-stream and data aggregation system
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "docker-vtuber" / "app"))

from streaming.stream_manager import (
    StreamManager, StreamDestination, StreamSource, 
    StreamType, StreamProtocol
)
from streaming.video_streamer import UnrealVideoStreamer, UnrealStreamConfig
from streaming.source_aggregator import (
    DataAggregator, DataSource, DataSourceType
)
from CORE.autogen_agent.autogen_agent.source_selector import (
    AgentSourceSelector, SelectionStrategy
)


class TestStreamManager:
    """Test StreamManager functionality"""
    
    @pytest.fixture
    def stream_manager(self):
        """Create a StreamManager instance"""
        return StreamManager()
    
    def test_add_destination(self, stream_manager):
        """Test adding streaming destinations"""
        dest = StreamDestination(
            name="twitch_main",
            url="rtmp://live.twitch.tv/app/test_key",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.AUDIO_RTMP,
            priority=10
        )
        
        stream_manager.add_destination(dest)
        assert "twitch_main" in stream_manager.destinations
        assert stream_manager.destinations["twitch_main"].priority == 10
    
    def test_add_source(self, stream_manager):
        """Test adding stream sources"""
        source = StreamSource(
            name="test_audio",
            source_type="file",
            location="/tmp/test.wav",
            format="wav"
        )
        
        stream_manager.add_source(source)
        assert "test_audio" in stream_manager.sources
        assert stream_manager.sources["test_audio"].format == "wav"
    
    def test_get_destinations_by_type(self, stream_manager):
        """Test filtering destinations by type"""
        # Add multiple destinations
        audio_dest = StreamDestination(
            name="audio_dest",
            url="rtmp://audio.example.com/live",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.AUDIO_RTMP
        )
        
        video_dest = StreamDestination(
            name="video_dest",
            url="rtmp://video.example.com/live",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.VIDEO_UNREAL
        )
        
        stream_manager.add_destination(audio_dest)
        stream_manager.add_destination(video_dest)
        
        # Test filtering
        audio_dests = stream_manager.get_destinations_by_type(StreamType.AUDIO_RTMP)
        assert len(audio_dests) == 1
        assert audio_dests[0].name == "audio_dest"
        
        video_dests = stream_manager.get_destinations_by_type(StreamType.VIDEO_UNREAL)
        assert len(video_dests) == 1
        assert video_dests[0].name == "video_dest"
    
    def test_get_enabled_destinations(self, stream_manager):
        """Test getting enabled destinations sorted by priority"""
        # Add destinations with different priorities
        high_priority = StreamDestination(
            name="high",
            url="rtmp://high.example.com/live",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.AUDIO_RTMP,
            priority=10
        )
        
        low_priority = StreamDestination(
            name="low",
            url="rtmp://low.example.com/live",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.AUDIO_RTMP,
            priority=1
        )
        
        disabled = StreamDestination(
            name="disabled",
            url="rtmp://disabled.example.com/live",
            protocol=StreamProtocol.RTMP,
            stream_type=StreamType.AUDIO_RTMP,
            enabled=False,
            priority=20
        )
        
        stream_manager.add_destination(high_priority)
        stream_manager.add_destination(low_priority)
        stream_manager.add_destination(disabled)
        
        enabled = stream_manager.get_enabled_destinations()
        assert len(enabled) == 2  # Disabled destination excluded
        assert enabled[0].name == "high"  # Higher priority first
        assert enabled[1].name == "low"
    
    @pytest.mark.asyncio
    async def test_start_stream_invalid_source(self, stream_manager):
        """Test starting stream with invalid source"""
        with pytest.raises(ValueError, match="Source 'nonexistent' not found"):
            await stream_manager.start_stream("nonexistent")
    
    def test_config_loading(self, tmp_path):
        """Test loading configuration from JSON"""
        # Create config file
        config = {
            "destinations": [
                {
                    "name": "youtube",
                    "url": "rtmp://a.rtmp.youtube.com/live2/test",
                    "protocol": "rtmp",
                    "stream_type": "audio_rtmp",
                    "enabled": True,
                    "priority": 5
                }
            ],
            "sources": [
                {
                    "name": "mic",
                    "source_type": "capture",
                    "location": "default",
                    "format": "raw"
                }
            ]
        }
        
        config_file = tmp_path / "stream_config.json"
        config_file.write_text(json.dumps(config))
        
        # Load config
        manager = StreamManager(str(config_file))
        
        assert "youtube" in manager.destinations
        assert "mic" in manager.sources


class TestVideoStreamer:
    """Test UnrealVideoStreamer functionality"""
    
    @pytest.fixture
    def video_config(self):
        """Create video streaming configuration"""
        return UnrealStreamConfig(
            resolution="1920x1080",
            framerate=30,
            bitrate="4000k",
            codec="h264",
            low_latency=True
        )
    
    @pytest.fixture
    def video_streamer(self, video_config):
        """Create video streamer instance"""
        return UnrealVideoStreamer(video_config)
    
    def test_config_to_ffmpeg_args(self, video_config):
        """Test converting config to FFmpeg arguments"""
        args = video_config.to_ffmpeg_args()
        
        assert "-c:v" in args
        assert "libx264" in args
        assert "-preset" in args
        assert "fast" in args
        assert "-b:v" in args
        assert "4000k" in args
        assert "-r" in args
        assert "30" in args
    
    @patch('subprocess.Popen')
    def test_start_window_capture(self, mock_popen, video_streamer):
        """Test starting window capture"""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        result = video_streamer.start_window_capture("UnrealEditor")
        
        assert result is not None
        mock_popen.assert_called_once()
        
        # Check FFmpeg command
        call_args = mock_popen.call_args[0][0]
        assert "ffmpeg" in call_args
        assert "rawvideo" in call_args


class TestDataAggregator:
    """Test DataAggregator functionality"""
    
    @pytest.fixture
    def data_aggregator(self):
        """Create data aggregator instance"""
        return DataAggregator()
    
    def test_add_data_source(self, data_aggregator):
        """Test adding data sources"""
        source = DataSource(
            name="api_source",
            source_type=DataSourceType.REST_API,
            endpoint="https://api.example.com/data",
            polling_interval=5.0
        )
        
        data_aggregator.add_source(source)
        
        assert "api_source" in data_aggregator.sources
        assert "api_source" in data_aggregator.connectors
    
    @pytest.mark.asyncio
    async def test_transform_filter(self, data_aggregator):
        """Test keyword filtering transformer"""
        data = {
            "message1": "This contains important keyword",
            "message2": "This does not",
            "message3": "Another important message"
        }
        
        filters = {"keywords": ["important"]}
        
        filtered = await data_aggregator._transform_filter(data, filters)
        
        assert "message1" in filtered
        assert "message2" not in filtered
        assert "message3" in filtered
    
    def test_buffer_management(self, data_aggregator):
        """Test data buffer management"""
        # Set small buffer size
        data_aggregator.max_buffer_size = 3
        
        # Add data to buffer
        for i in range(5):
            data_aggregator.data_buffer.append({
                "source": f"test_{i}",
                "data": f"data_{i}"
            })
        
        # Check buffer is trimmed
        assert len(data_aggregator.data_buffer) == 3
        
        # Check we have the latest data
        assert data_aggregator.data_buffer[-1]["source"] == "test_4"
        
        # Test clearing buffer
        data_aggregator.clear_buffer()
        assert len(data_aggregator.data_buffer) == 0


class TestAgentSourceSelector:
    """Test AgentSourceSelector functionality"""
    
    @pytest.fixture
    def selector(self):
        """Create agent source selector"""
        return AgentSourceSelector(
            agent_id="test_agent_001",
            stream_manager=StreamManager(),
            data_aggregator=DataAggregator()
        )
    
    @pytest.mark.asyncio
    async def test_select_stream_source_manual(self, selector):
        """Test manual stream source selection"""
        # Add source to manager
        source = StreamSource(
            name="test_source",
            source_type="file",
            location="/tmp/test.wav",
            format="wav"
        )
        selector.stream_manager.add_source(source)
        
        # Select source
        success, message = await selector.select_stream_source("test_source")
        
        assert success is True
        assert selector.current_stream_source == "test_source"
        assert "Selected stream source: test_source" in message
    
    @pytest.mark.asyncio
    async def test_select_stream_source_invalid(self, selector):
        """Test selecting invalid stream source"""
        success, message = await selector.select_stream_source("nonexistent")
        
        assert success is False
        assert "Source not found" in message
    
    @pytest.mark.asyncio
    async def test_select_data_sources(self, selector):
        """Test selecting data aggregation sources"""
        # Add sources
        source1 = DataSource(
            name="source1",
            source_type=DataSourceType.REST_API,
            endpoint="https://api1.example.com"
        )
        source2 = DataSource(
            name="source2",
            source_type=DataSourceType.WEBSOCKET,
            endpoint="ws://api2.example.com"
        )
        
        selector.data_aggregator.add_source(source1)
        selector.data_aggregator.add_source(source2)
        
        # Select sources
        success, message = await selector.select_data_sources(["source1", "source2"])
        
        assert success is True
        assert "source1" in selector.current_data_sources
        assert "source2" in selector.current_data_sources
        assert "Selected 2 data sources" in message
    
    @pytest.mark.asyncio
    async def test_strategy_round_robin(self, selector):
        """Test round-robin selection strategy"""
        # Add multiple sources
        for i in range(3):
            source = StreamSource(
                name=f"source_{i}",
                source_type="file",
                location=f"/tmp/test_{i}.wav",
                format="wav"
            )
            selector.stream_manager.add_source(source)
        
        selector.strategy = SelectionStrategy.ROUND_ROBIN
        
        # First selection
        success1, _ = await selector.select_stream_source(strategy=SelectionStrategy.ROUND_ROBIN)
        first_source = selector.current_stream_source
        
        # Second selection should be different
        success2, _ = await selector.select_stream_source(strategy=SelectionStrategy.ROUND_ROBIN)
        second_source = selector.current_stream_source
        
        assert success1 and success2
        assert first_source != second_source
    
    def test_get_status(self, selector):
        """Test getting selector status"""
        selector.current_stream_source = "test_source"
        selector.current_data_sources = ["data1", "data2"]
        
        status = selector.get_status()
        
        assert status["agent_id"] == "test_agent_001"
        assert status["current_stream_source"] == "test_source"
        assert len(status["current_data_sources"]) == 2
        assert status["strategy"] == "priority"  # Default


@pytest.mark.asyncio
async def test_integration_flow():
    """Test complete integration flow"""
    # Create components
    stream_manager = StreamManager()
    data_aggregator = DataAggregator()
    selector = AgentSourceSelector(
        agent_id="integration_test",
        stream_manager=stream_manager,
        data_aggregator=data_aggregator
    )
    
    # Add stream source and destination
    source = StreamSource(
        name="audio_input",
        source_type="file",
        location="/tmp/test_audio.wav",
        format="wav"
    )
    
    destination = StreamDestination(
        name="output_stream",
        url="rtmp://localhost/live/test",
        protocol=StreamProtocol.RTMP,
        stream_type=StreamType.AUDIO_RTMP
    )
    
    stream_manager.add_source(source)
    stream_manager.add_destination(destination)
    
    # Add data source
    data_source = DataSource(
        name="metrics_api",
        source_type=DataSourceType.REST_API,
        endpoint="https://api.example.com/metrics"
    )
    
    data_aggregator.add_source(data_source)
    
    # Agent selects sources
    stream_success, _ = await selector.select_stream_source("audio_input")
    data_success, _ = await selector.select_data_sources(["metrics_api"])
    
    assert stream_success
    assert data_success
    assert selector.current_stream_source == "audio_input"
    assert "metrics_api" in selector.current_data_sources
    
    # Get status
    status = selector.get_status()
    assert status["agent_id"] == "integration_test"
    assert status["current_stream_source"] == "audio_input"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])