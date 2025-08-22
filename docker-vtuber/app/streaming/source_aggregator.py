"""
Data Source Aggregator for S2 Thinking System
Connects to various data sources and feeds processed data to S2 via SCB
"""

import asyncio
import aiohttp
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import websockets
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of data sources"""
    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    DATABASE = "database"
    FILE_STREAM = "file_stream"
    MESSAGE_QUEUE = "message_queue"
    SOCIAL_MEDIA = "social_media"
    MARKET_DATA = "market_data"
    SENSOR = "sensor"


@dataclass
class DataSource:
    """Configuration for a data source"""
    name: str
    source_type: DataSourceType
    endpoint: str  # URL, file path, or connection string
    auth: Optional[Dict[str, str]] = None
    polling_interval: float = 10.0  # seconds
    filters: Dict[str, Any] = field(default_factory=dict)
    transformers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class DataConnector(ABC):
    """Abstract base class for data source connectors"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to data source"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> Any:
        """Fetch data from source"""
        pass
    
    @abstractmethod
    async def subscribe(self, callback: Callable):
        """Subscribe to real-time updates"""
        pass


class RestApiConnector(DataConnector):
    """Connector for REST API data sources"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Create HTTP session"""
        try:
            self.session = aiohttp.ClientSession()
            # Test connection
            async with self.session.get(self.source.endpoint) as response:
                return response.status < 400
        except Exception as e:
            logger.error(f"Failed to connect to {self.source.endpoint}: {e}")
            return False
    
    async def disconnect(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def fetch_data(self) -> Any:
        """Fetch data from REST API"""
        if not self.session:
            await self.connect()
        
        headers = {}
        if self.source.auth:
            if 'bearer_token' in self.source.auth:
                headers['Authorization'] = f"Bearer {self.source.auth['bearer_token']}"
            elif 'api_key' in self.source.auth:
                headers['X-API-Key'] = self.source.auth['api_key']
        
        try:
            async with self.session.get(
                self.source.endpoint,
                headers=headers,
                params=self.source.filters
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API error {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch from {self.source.endpoint}: {e}")
            return None
    
    async def subscribe(self, callback: Callable):
        """Poll API at regular intervals"""
        while self.source.enabled:
            try:
                data = await self.fetch_data()
                if data:
                    await callback(self.source.name, data)
                await asyncio.sleep(self.source.polling_interval)
            except Exception as e:
                logger.error(f"Subscription error for {self.source.name}: {e}")
                await asyncio.sleep(self.source.polling_interval)


class WebSocketConnector(DataConnector):
    """Connector for WebSocket data sources"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.websocket = None
    
    async def connect(self) -> bool:
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(self.source.endpoint)
            
            # Send authentication if needed
            if self.source.auth:
                await self.websocket.send(json.dumps(self.source.auth))
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket {self.source.endpoint}: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
    
    async def fetch_data(self) -> Any:
        """Receive data from WebSocket"""
        if not self.websocket:
            await self.connect()
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except Exception as e:
            logger.error(f"Failed to receive from WebSocket: {e}")
            return None
    
    async def subscribe(self, callback: Callable):
        """Listen for WebSocket messages"""
        if not self.websocket:
            await self.connect()
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await callback(self.source.name, data)
                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    await callback(self.source.name, message)
        except Exception as e:
            logger.error(f"WebSocket subscription error: {e}")


class DataAggregator:
    """
    Aggregates data from multiple sources and routes to S2 via SCB
    """
    
    def __init__(self, scb_gateway_url: str = "http://scb_gateway:5002"):
        self.sources: Dict[str, DataSource] = {}
        self.connectors: Dict[str, DataConnector] = {}
        self.scb_gateway_url = scb_gateway_url
        self.active_subscriptions: Dict[str, asyncio.Task] = {}
        self.data_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 1000
        
        # Data transformers
        self.transformers = {
            'extract_sentiment': self._transform_sentiment,
            'normalize_numbers': self._transform_normalize,
            'filter_keywords': self._transform_filter,
            'summarize': self._transform_summarize,
        }
    
    def add_source(self, source: DataSource):
        """Add a new data source"""
        self.sources[source.name] = source
        
        # Create appropriate connector
        if source.source_type == DataSourceType.REST_API:
            self.connectors[source.name] = RestApiConnector(source)
        elif source.source_type == DataSourceType.WEBSOCKET:
            self.connectors[source.name] = WebSocketConnector(source)
        # Add other connector types as needed
        
        logger.info(f"Added data source: {source.name} ({source.source_type.value})")
    
    def remove_source(self, name: str):
        """Remove a data source"""
        if name in self.sources:
            # Stop subscription if active
            if name in self.active_subscriptions:
                self.active_subscriptions[name].cancel()
                del self.active_subscriptions[name]
            
            # Disconnect connector
            if name in self.connectors:
                asyncio.create_task(self.connectors[name].disconnect())
                del self.connectors[name]
            
            del self.sources[name]
            logger.info(f"Removed data source: {name}")
    
    async def start_aggregation(self, source_names: Optional[List[str]] = None):
        """
        Start aggregating data from specified sources
        
        Args:
            source_names: List of source names to aggregate from.
                         If None, uses all enabled sources.
        """
        if source_names is None:
            source_names = [
                name for name, source in self.sources.items()
                if source.enabled
            ]
        
        for name in source_names:
            if name in self.sources and name not in self.active_subscriptions:
                source = self.sources[name]
                connector = self.connectors.get(name)
                
                if connector:
                    # Start subscription
                    task = asyncio.create_task(
                        connector.subscribe(self._handle_data)
                    )
                    self.active_subscriptions[name] = task
                    logger.info(f"Started aggregation from: {name}")
    
    async def stop_aggregation(self, source_names: Optional[List[str]] = None):
        """Stop aggregating from specified sources"""
        if source_names is None:
            source_names = list(self.active_subscriptions.keys())
        
        for name in source_names:
            if name in self.active_subscriptions:
                self.active_subscriptions[name].cancel()
                del self.active_subscriptions[name]
                logger.info(f"Stopped aggregation from: {name}")
    
    async def _handle_data(self, source_name: str, raw_data: Any):
        """
        Handle incoming data from a source
        
        Args:
            source_name: Name of the data source
            raw_data: Raw data from the source
        """
        try:
            source = self.sources[source_name]
            
            # Apply transformations
            processed_data = raw_data
            for transformer_name in source.transformers:
                if transformer_name in self.transformers:
                    transformer = self.transformers[transformer_name]
                    processed_data = await transformer(processed_data, source.filters)
            
            # Create data package
            data_package = {
                'source': source_name,
                'timestamp': datetime.utcnow().isoformat(),
                'data': processed_data,
                'metadata': source.metadata
            }
            
            # Buffer data
            self.data_buffer.append(data_package)
            if len(self.data_buffer) > self.max_buffer_size:
                self.data_buffer = self.data_buffer[-self.max_buffer_size:]
            
            # Send to S2 via SCB
            await self._send_to_s2(data_package)
            
        except Exception as e:
            logger.error(f"Error handling data from {source_name}: {e}")
    
    async def _send_to_s2(self, data_package: Dict[str, Any]):
        """Send processed data to S2 thinking system via SCB"""
        try:
            # Create SCB event
            event = {
                'type': 'data_aggregation',
                'source': data_package['source'],
                'text': json.dumps(data_package['data']),
                'metadata': {
                    'timestamp': data_package['timestamp'],
                    **data_package['metadata']
                }
            }
            
            # Send to SCB gateway for S2 team
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.scb_gateway_url}/scb/team/s2_thinking/event",
                    json=event,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Sent data to S2: {data_package['source']}")
                    else:
                        logger.error(f"Failed to send to S2: {response.status}")
        
        except Exception as e:
            logger.error(f"Error sending to S2: {e}")
    
    # Data transformers
    
    async def _transform_sentiment(self, data: Any, filters: Dict) -> Any:
        """Extract sentiment from text data"""
        # TODO: Implement sentiment analysis
        return data
    
    async def _transform_normalize(self, data: Any, filters: Dict) -> Any:
        """Normalize numerical data"""
        # TODO: Implement normalization
        return data
    
    async def _transform_filter(self, data: Any, filters: Dict) -> Any:
        """Filter data based on keywords"""
        if isinstance(data, dict) and 'keywords' in filters:
            keywords = filters['keywords']
            # Simple keyword filtering
            filtered = {}
            for key, value in data.items():
                if any(kw in str(value).lower() for kw in keywords):
                    filtered[key] = value
            return filtered
        return data
    
    async def _transform_summarize(self, data: Any, filters: Dict) -> Any:
        """Summarize long text data"""
        # TODO: Implement text summarization
        return data
    
    def get_buffer(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get buffered data"""
        if limit:
            return self.data_buffer[-limit:]
        return self.data_buffer
    
    def clear_buffer(self):
        """Clear data buffer"""
        self.data_buffer.clear()
        logger.info("Cleared data buffer")


# Global instance
_data_aggregator = None


def get_data_aggregator(scb_gateway_url: Optional[str] = None) -> DataAggregator:
    """Get or create the global data aggregator instance"""
    global _data_aggregator
    if _data_aggregator is None:
        url = scb_gateway_url or "http://scb_gateway:5002"
        _data_aggregator = DataAggregator(url)
    return _data_aggregator