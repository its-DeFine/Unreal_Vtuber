"""
Agent Source Selector
Allows agents to dynamically select and switch between streaming sources
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

# Import streaming components
from ....streaming.stream_manager import StreamManager, StreamDestination, StreamSource, StreamType
from ....streaming.source_aggregator import DataAggregator, DataSource, DataSourceType

logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Strategies for source selection"""
    MANUAL = "manual"  # Agent explicitly selects
    PRIORITY = "priority"  # Based on source priority
    ROUND_ROBIN = "round_robin"  # Cycle through sources
    QUALITY = "quality"  # Based on quality metrics
    LATENCY = "latency"  # Lowest latency first
    HYBRID = "hybrid"  # Combination of factors


@dataclass
class SourceMetrics:
    """Metrics for a source"""
    latency_ms: float = 0.0
    quality_score: float = 1.0
    reliability: float = 1.0
    bandwidth_kbps: float = 0.0
    error_rate: float = 0.0
    last_updated: Optional[datetime] = None


class AgentSourceSelector:
    """
    Manages source selection for agents
    Coordinates between streaming sources and data aggregation
    """
    
    def __init__(
        self,
        agent_id: str,
        stream_manager: Optional[StreamManager] = None,
        data_aggregator: Optional[DataAggregator] = None
    ):
        self.agent_id = agent_id
        self.stream_manager = stream_manager or StreamManager()
        self.data_aggregator = data_aggregator or DataAggregator()
        
        # Current selections
        self.current_stream_source: Optional[str] = None
        self.current_data_sources: List[str] = []
        
        # Selection strategy
        self.strategy = SelectionStrategy.PRIORITY
        
        # Source metrics
        self.source_metrics: Dict[str, SourceMetrics] = {}
        
        # Selection history
        self.selection_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    async def select_stream_source(
        self,
        source_name: Optional[str] = None,
        strategy: Optional[SelectionStrategy] = None
    ) -> Tuple[bool, str]:
        """
        Select a streaming source for the agent
        
        Args:
            source_name: Specific source to select. If None, uses strategy
            strategy: Selection strategy to use. If None, uses default
        
        Returns:
            Tuple of (success, message)
        """
        try:
            strategy = strategy or self.strategy
            
            if source_name:
                # Manual selection
                if source_name in self.stream_manager.sources:
                    self.current_stream_source = source_name
                    self._record_selection('stream', source_name, 'manual')
                    logger.info(f"Agent {self.agent_id} selected stream source: {source_name}")
                    return True, f"Selected stream source: {source_name}"
                else:
                    return False, f"Source not found: {source_name}"
            
            # Automatic selection based on strategy
            available_sources = list(self.stream_manager.sources.keys())
            
            if not available_sources:
                return False, "No stream sources available"
            
            selected = await self._select_by_strategy(available_sources, strategy)
            
            if selected:
                self.current_stream_source = selected
                self._record_selection('stream', selected, strategy.value)
                logger.info(f"Agent {self.agent_id} auto-selected stream source: {selected}")
                return True, f"Auto-selected stream source: {selected}"
            
            return False, "Failed to select stream source"
        
        except Exception as e:
            logger.error(f"Error selecting stream source: {e}")
            return False, str(e)
    
    async def select_data_sources(
        self,
        source_names: Optional[List[str]] = None,
        add: bool = False
    ) -> Tuple[bool, str]:
        """
        Select data aggregation sources
        
        Args:
            source_names: List of sources to select. If None, uses all available
            add: If True, add to existing sources. If False, replace
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if source_names is None:
                # Select all available sources
                source_names = [
                    name for name, source in self.data_aggregator.sources.items()
                    if source.enabled
                ]
            
            # Validate sources exist
            invalid = [s for s in source_names if s not in self.data_aggregator.sources]
            if invalid:
                return False, f"Invalid sources: {invalid}"
            
            # Update selection
            if add:
                self.current_data_sources.extend(source_names)
                self.current_data_sources = list(set(self.current_data_sources))  # Remove duplicates
            else:
                self.current_data_sources = source_names
            
            # Start aggregation from selected sources
            await self.data_aggregator.start_aggregation(self.current_data_sources)
            
            self._record_selection('data', source_names, 'manual')
            logger.info(f"Agent {self.agent_id} selected data sources: {source_names}")
            
            return True, f"Selected {len(source_names)} data sources"
        
        except Exception as e:
            logger.error(f"Error selecting data sources: {e}")
            return False, str(e)
    
    async def switch_stream_source(self, new_source: str) -> Tuple[bool, str]:
        """
        Switch to a different streaming source
        
        Args:
            new_source: Name of the new source
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop current stream if active
            if self.current_stream_source:
                active_streams = self.stream_manager.get_active_streams()
                for stream_id in active_streams:
                    if self.current_stream_source in stream_id:
                        self.stream_manager.stop_stream(stream_id)
            
            # Select new source
            success, message = await self.select_stream_source(new_source)
            
            if success:
                # Start streaming with new source
                await self.start_streaming()
            
            return success, message
        
        except Exception as e:
            logger.error(f"Error switching stream source: {e}")
            return False, str(e)
    
    async def start_streaming(
        self,
        destinations: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Start streaming from current source to destinations
        
        Args:
            destinations: List of destination names. If None, uses all enabled
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.current_stream_source:
                return False, "No stream source selected"
            
            # Start streaming
            await self.stream_manager.start_stream(
                self.current_stream_source,
                destinations
            )
            
            logger.info(f"Agent {self.agent_id} started streaming from {self.current_stream_source}")
            return True, f"Started streaming from {self.current_stream_source}"
        
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return False, str(e)
    
    def stop_streaming(self):
        """Stop all streaming for this agent"""
        try:
            active_streams = self.stream_manager.get_active_streams()
            stopped = 0
            
            for stream_id, info in active_streams.items():
                if info['source'] == self.current_stream_source:
                    self.stream_manager.stop_stream(stream_id)
                    stopped += 1
            
            logger.info(f"Agent {self.agent_id} stopped {stopped} streams")
            return True, f"Stopped {stopped} streams"
        
        except Exception as e:
            logger.error(f"Error stopping streams: {e}")
            return False, str(e)
    
    async def update_source_metrics(self, source_name: str, metrics: SourceMetrics):
        """Update metrics for a source"""
        metrics.last_updated = datetime.utcnow()
        self.source_metrics[source_name] = metrics
        logger.debug(f"Updated metrics for {source_name}: {metrics}")
    
    async def _select_by_strategy(
        self,
        sources: List[str],
        strategy: SelectionStrategy
    ) -> Optional[str]:
        """Select source based on strategy"""
        if not sources:
            return None
        
        if strategy == SelectionStrategy.MANUAL:
            # Should not reach here for manual
            return sources[0]
        
        elif strategy == SelectionStrategy.PRIORITY:
            # Select highest priority source
            # For streaming sources
            if hasattr(self.stream_manager, 'sources'):
                prioritized = sorted(
                    sources,
                    key=lambda x: self.stream_manager.sources.get(x).metadata.get('priority', 0),
                    reverse=True
                )
                return prioritized[0] if prioritized else sources[0]
            return sources[0]
        
        elif strategy == SelectionStrategy.ROUND_ROBIN:
            # Cycle through sources
            if self.current_stream_source in sources:
                current_idx = sources.index(self.current_stream_source)
                next_idx = (current_idx + 1) % len(sources)
                return sources[next_idx]
            return sources[0]
        
        elif strategy == SelectionStrategy.QUALITY:
            # Select based on quality score
            if self.source_metrics:
                scored = sorted(
                    sources,
                    key=lambda x: self.source_metrics.get(x, SourceMetrics()).quality_score,
                    reverse=True
                )
                return scored[0]
            return sources[0]
        
        elif strategy == SelectionStrategy.LATENCY:
            # Select lowest latency
            if self.source_metrics:
                sorted_by_latency = sorted(
                    sources,
                    key=lambda x: self.source_metrics.get(x, SourceMetrics()).latency_ms
                )
                return sorted_by_latency[0]
            return sources[0]
        
        elif strategy == SelectionStrategy.HYBRID:
            # Combine multiple factors
            scores = {}
            for source in sources:
                metrics = self.source_metrics.get(source, SourceMetrics())
                # Calculate hybrid score (customize weights as needed)
                score = (
                    metrics.quality_score * 0.4 +
                    (1.0 - min(metrics.latency_ms / 1000, 1.0)) * 0.3 +
                    metrics.reliability * 0.3
                )
                scores[source] = score
            
            # Select highest scored
            if scores:
                best = max(scores, key=scores.get)
                return best
            return sources[0]
        
        return sources[0]  # Default fallback
    
    def _record_selection(self, selection_type: str, sources: Any, method: str):
        """Record selection in history"""
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_id': self.agent_id,
            'type': selection_type,
            'sources': sources,
            'method': method
        }
        
        self.selection_history.append(record)
        
        # Trim history
        if len(self.selection_history) > self.max_history:
            self.selection_history = self.selection_history[-self.max_history:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current selector status"""
        return {
            'agent_id': self.agent_id,
            'current_stream_source': self.current_stream_source,
            'current_data_sources': self.current_data_sources,
            'strategy': self.strategy.value,
            'active_streams': len(self.stream_manager.get_active_streams()),
            'metrics': {
                name: {
                    'latency_ms': m.latency_ms,
                    'quality_score': m.quality_score,
                    'reliability': m.reliability
                }
                for name, m in self.source_metrics.items()
            }
        }
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get selection history"""
        if limit:
            return self.selection_history[-limit:]
        return self.selection_history