"""
Context Service for managing system state and context analysis.

This service provides centralized state management, pattern analysis,
and integration with System1/System2 for comprehensive context tracking.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import psutil
import statistics
from collections import deque, defaultdict
from dataclasses import dataclass, field
import json

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from ..models.stimuli import CategorizedStimuli, StimuliCategory
from ..models.context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis
)
from ..integrations.system1_interface import System1Interface
from ..integrations.system2_interface import System2Interface
from ..config.settings import GraphFlowConfig, Priority
from ..utils.logging import get_structured_logger
from ..utils.metrics import MetricsCollector


@dataclass
class UserSession:
    """Tracks user session information."""
    user_id: str
    started_at: datetime
    last_interaction: datetime
    interaction_count: int = 0
    topics: List[str] = field(default_factory=list)
    sentiment_scores: List[float] = field(default_factory=list)
    engagement_scores: List[float] = field(default_factory=list)
    
    def get_average_sentiment(self) -> float:
        """Calculate average sentiment score."""
        return statistics.mean(self.sentiment_scores) if self.sentiment_scores else 0.0
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds."""
        return (self.last_interaction - self.started_at).total_seconds()


@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_io_read: float
    disk_io_write: float
    network_sent: float
    network_recv: float
    active_connections: int
    thread_count: int


class ContextService:
    """
    Centralized service for context management and state tracking.
    
    Provides:
    - System state monitoring and caching
    - User history and pattern tracking
    - Environmental context detection
    - Resource monitoring and prediction
    - Integration with System1/System2 for real-time state
    """
    
    def __init__(
        self,
        config: GraphFlowConfig,
        system1_interface: Optional[System1Interface] = None,
        system2_interface: Optional[System2Interface] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize context service.
        
        Args:
            config: GraphFlow configuration
            system1_interface: System1 interface instance
            system2_interface: System2 interface instance
            metrics_collector: Metrics collection instance
        """
        self.config = config
        self.system1_interface = system1_interface
        self.system2_interface = system2_interface
        self.metrics_collector = metrics_collector
        self.logger = get_structured_logger("context_service")
        
        # State caches
        self._system_state_cache: Optional[SystemStateAnalysis] = None
        self._environmental_cache: Optional[EnvironmentalAnalysis] = None
        self._resource_cache: Optional[ResourceAnalysis] = None
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # User tracking
        self._user_sessions: Dict[str, UserSession] = {}
        self._user_patterns: Dict[str, Dict[str, Any]] = {}
        self._interaction_history: deque = deque(maxlen=1000)
        
        # System metrics tracking
        self._metrics_history: deque = deque(maxlen=300)  # 5 minutes at 1 sample/sec
        self._performance_baselines: Dict[str, float] = {}
        
        # Environmental state
        self._autonomous_mode: bool = False
        self._streaming_active: bool = False
        self._streaming_platform: Optional[str] = None
        self._special_events: Dict[str, Any] = {}
        
        # Resource monitoring
        self._resource_monitor_task: Optional[asyncio.Task] = None
        self._redis_client: Optional[aioredis.Redis] = None
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the context service."""
        try:
            self.logger.info("Initializing context service")
            
            # Connect to Redis for distributed state if configured
            if self.config.redis_url and REDIS_AVAILABLE:
                try:
                    self._redis_client = await aioredis.create_redis_pool(
                        self.config.redis_url,
                        encoding='utf-8'
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to connect to Redis: {e}")
                    self._redis_client = None
            
            # Initialize performance baselines
            await self._establish_performance_baselines()
            
            # Start resource monitoring
            self._resource_monitor_task = asyncio.create_task(
                self._monitor_resources()
            )
            
            # Load any persisted state
            await self._load_persisted_state()
            
            self.is_initialized = True
            self.logger.info("Context service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize context service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the context service."""
        self.logger.info("Shutting down context service")
        
        # Cancel monitoring task
        if self._resource_monitor_task:
            self._resource_monitor_task.cancel()
            try:
                await self._resource_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Save state before shutdown
        await self._persist_state()
        
        # Close Redis connection
        if self._redis_client:
            self._redis_client.close()
            await self._redis_client.wait_closed()
        
        # Clear caches
        self._clear_all_caches()
        
        self.is_initialized = False
    
    async def get_system_state(self, force_refresh: bool = False) -> SystemStateAnalysis:
        """
        Get current system state analysis.
        
        Args:
            force_refresh: Force refresh bypassing cache
            
        Returns:
            SystemStateAnalysis with current state
        """
        cache_key = "system_state"
        
        # Check cache unless forced refresh
        if not force_refresh and self._is_cache_valid(cache_key, 30):
            return self._system_state_cache
        
        # Gather system state from multiple sources
        is_speaking = await self._check_avatar_speaking()
        system_status = await self._get_system_status()
        queue_info = await self._get_queue_status()
        resource_util = await self._get_resource_utilization()
        
        # Determine states
        is_idle = not is_speaking and queue_info['size'] == 0
        is_busy = queue_info['size'] > 5 or resource_util['cpu'] > 0.8
        has_errors = system_status.get('has_errors', False)
        
        # Calculate availability score
        availability_score = self._calculate_system_availability(
            is_speaking, is_idle, is_busy, has_errors, queue_info['size']
        )
        
        # Get active processes
        active_processes = await self._get_active_processes()
        
        analysis = SystemStateAnalysis(
            is_speaking=is_speaking,
            is_idle=is_idle,
            is_busy=is_busy,
            has_errors=has_errors,
            queue_size=queue_info['size'],
            resource_utilization=resource_util,
            availability_score=availability_score,
            active_processes=active_processes,
            last_activity_timestamp=system_status.get('last_activity'),
            error_details=system_status.get('error_details')
        )
        
        # Update cache
        self._system_state_cache = analysis
        self._cache_timestamps[cache_key] = datetime.now()
        
        # Store in Redis if available
        if self._redis_client:
            await self._redis_client.setex(
                f"context:system_state",
                30,
                json.dumps({
                    'is_speaking': is_speaking,
                    'is_idle': is_idle,
                    'queue_size': queue_info['size'],
                    'availability_score': availability_score
                })
            )
        
        return analysis
    
    async def analyze_user_context(
        self,
        stimuli: CategorizedStimuli,
        include_history: bool = True
    ) -> UserContextAnalysis:
        """
        Analyze user interaction context.
        
        Args:
            stimuli: Categorized stimuli to analyze
            include_history: Whether to include historical analysis
            
        Returns:
            UserContextAnalysis with comprehensive user context
        """
        user_id = stimuli.metadata.get('user_id', 'anonymous')
        
        # Update or create user session
        session = await self._update_user_session(user_id, stimuli)
        
        # Calculate metrics
        interaction_frequency = self._calculate_interaction_frequency(session)
        engagement_level = self._determine_engagement_level(session, stimuli)
        recent_topics = await self._extract_topics(stimuli, session)
        preference_match = await self._calculate_preference_match(user_id, stimuli)
        
        # Get historical patterns if enabled
        historical_patterns = {}
        if include_history:
            historical_patterns = await self._analyze_historical_patterns(user_id)
        
        # Estimate sentiment
        sentiment_score = await self._analyze_sentiment(stimuli.content)
        session.sentiment_scores.append(sentiment_score)
        
        # Create analysis
        analysis = UserContextAnalysis(
            interaction_frequency=interaction_frequency,
            engagement_level=engagement_level,
            recent_topics=recent_topics,
            user_preference_match=preference_match,
            historical_response_patterns=historical_patterns,
            user_id=user_id,
            session_duration=session.get_session_duration(),
            sentiment_score=sentiment_score,
            interaction_context={
                'session_interactions': session.interaction_count,
                'average_sentiment': session.get_average_sentiment(),
                'category_distribution': await self._get_category_distribution(user_id)
            }
        )
        
        # Track interaction
        self._interaction_history.append({
            'user_id': user_id,
            'timestamp': datetime.now(),
            'category': stimuli.category.value,
            'sentiment': sentiment_score,
            'engagement': engagement_level
        })
        
        return analysis
    
    async def get_environmental_context(
        self,
        force_refresh: bool = False
    ) -> EnvironmentalAnalysis:
        """
        Get current environmental context.
        
        Args:
            force_refresh: Force refresh bypassing cache
            
        Returns:
            EnvironmentalAnalysis with environmental factors
        """
        cache_key = "environmental"
        
        # Check cache unless forced refresh
        if not force_refresh and self._is_cache_valid(cache_key, 60):
            return self._environmental_cache
        
        # Get current states
        autonomous_mode = await self._check_autonomous_mode()
        streaming_info = await self._get_streaming_status()
        activity_level = await self._analyze_activity_level()
        
        # Calculate time factors
        current_time = datetime.now()
        time_factor = self._calculate_time_of_day_factor(current_time.hour)
        
        # Check for special events
        event_context = await self._check_special_events()
        
        # Determine platform context
        platform_context = streaming_info.get('platform', 'standalone')
        if not streaming_info.get('is_live'):
            platform_context = 'standalone'
        
        analysis = EnvironmentalAnalysis(
            autonomous_mode_active=autonomous_mode,
            streaming_status='live' if streaming_info.get('is_live') else 'offline',
            time_of_day_factor=time_factor,
            recent_activity_level=activity_level,
            external_event_context=event_context,
            platform_context=platform_context,
            audience_size=streaming_info.get('viewer_count'),
            environmental_triggers=await self._get_environmental_triggers(),
            mode_settings=await self._get_mode_settings()
        )
        
        # Update cache
        self._environmental_cache = analysis
        self._cache_timestamps[cache_key] = datetime.now()
        
        return analysis
    
    async def get_resource_availability(
        self,
        include_predictions: bool = True
    ) -> ResourceAnalysis:
        """
        Get current resource availability analysis.
        
        Args:
            include_predictions: Include predicted future availability
            
        Returns:
            ResourceAnalysis with resource metrics
        """
        cache_key = "resources"
        
        # Check cache for recent data
        if self._is_cache_valid(cache_key, 5):
            return self._resource_cache
        
        # Get current metrics
        current_metrics = await self._get_current_metrics()
        
        # Check agent availability
        agent_status = {}
        if self.system2_interface:
            agent_statuses = await self.system2_interface.get_agent_status()
            agent_status = {
                agent_id: status.is_active
                for agent_id, status in agent_statuses.items()
            }
        
        # Check system availability
        system1_available = True
        system2_available = True
        
        if self.system1_interface:
            s1_status = await self.system1_interface.check_system_availability()
            system1_available = s1_status.is_available
        
        if self.system2_interface:
            # Simple availability check based on agent status
            system2_available = len(agent_status) > 0
        
        # Calculate processing capacity
        cpu_avail = 1.0 - (current_metrics.cpu_percent / 100.0)
        mem_avail = 1.0 - (current_metrics.memory_percent / 100.0)
        capacity = int(min(cpu_avail, mem_avail) * self.config.max_concurrent_stimuli)
        
        # Determine resource pressure
        pressure_level = self._determine_resource_pressure(
            cpu_avail, mem_avail, current_metrics
        )
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(current_metrics, cpu_avail, mem_avail)
        
        analysis = ResourceAnalysis(
            cpu_availability=cpu_avail,
            memory_availability=mem_avail,
            agent_availability=agent_status,
            system1_availability=system1_available,
            system2_availability=system2_available,
            estimated_processing_capacity=max(1, capacity),
            gpu_availability=await self._get_gpu_availability(),
            network_bandwidth_available=await self._estimate_bandwidth(),
            storage_availability=await self._get_storage_availability(),
            resource_pressure_level=pressure_level,
            bottlenecks=bottlenecks
        )
        
        # Update cache
        self._resource_cache = analysis
        self._cache_timestamps[cache_key] = datetime.now()
        
        # Record metrics if collector available
        if self.metrics_collector:
            self.metrics_collector.record_resource_availability(
                cpu=cpu_avail,
                memory=mem_avail,
                capacity=capacity
            )
        
        return analysis
    
    async def update_system_state(self, state_update: Dict[str, Any]) -> None:
        """
        Update system state with new information.
        
        Args:
            state_update: Dictionary with state updates
        """
        # Update specific state components
        if 'autonomous_mode' in state_update:
            self._autonomous_mode = state_update['autonomous_mode']
            self.logger.info(f"Autonomous mode set to: {self._autonomous_mode}")
        
        if 'streaming_active' in state_update:
            self._streaming_active = state_update['streaming_active']
            self._streaming_platform = state_update.get('platform')
            self.logger.info(
                f"Streaming state updated: {self._streaming_active} on {self._streaming_platform}"
            )
        
        if 'special_event' in state_update:
            event_name = state_update['special_event']
            self._special_events[event_name] = {
                'started_at': datetime.now(),
                'metadata': state_update.get('event_metadata', {})
            }
        
        # Invalidate relevant caches
        if any(key in state_update for key in ['autonomous_mode', 'streaming_active']):
            self._invalidate_cache('environmental')
        
        # Persist state changes
        await self._persist_state_update(state_update)
    
    async def get_context_score(
        self,
        system_state: Optional[SystemStateAnalysis] = None,
        user_context: Optional[UserContextAnalysis] = None,
        environment: Optional[EnvironmentalAnalysis] = None,
        resources: Optional[ResourceAnalysis] = None
    ) -> float:
        """
        Calculate overall context quality score.
        
        Args:
            system_state: System state analysis
            user_context: User context analysis
            environment: Environmental analysis
            resources: Resource analysis
            
        Returns:
            Context quality score (0.0 to 1.0)
        """
        scores = []
        weights = []
        
        if system_state:
            scores.append(system_state.availability_score)
            weights.append(2.0)  # System state is important
        
        if user_context:
            engagement_score = {
                'low': 0.3,
                'medium': 0.6,
                'high': 0.9
            }.get(user_context.engagement_level, 0.5)
            scores.append(engagement_score * user_context.user_preference_match)
            weights.append(1.5)
        
        if environment:
            env_score = environment.time_of_day_factor
            if environment.autonomous_mode_active:
                env_score *= 1.2  # Boost for autonomous mode
            if environment.is_live_streaming():
                env_score *= 1.3  # Boost for live streaming
            scores.append(min(1.0, env_score))
            weights.append(1.0)
        
        if resources:
            resource_score = (
                resources.cpu_availability * 0.4 +
                resources.memory_availability * 0.4 +
                (1.0 if resources.system1_availability else 0.0) * 0.1 +
                (1.0 if resources.system2_availability else 0.0) * 0.1
            )
            scores.append(resource_score)
            weights.append(1.5)
        
        if not scores:
            return 0.5
        
        # Weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        
        return weighted_sum / total_weight
    
    # Private helper methods
    
    async def _monitor_resources(self) -> None:
        """Background task to monitor system resources."""
        while True:
            try:
                # Collect metrics
                metrics = await self._collect_system_metrics()
                self._metrics_history.append(metrics)
                
                # Update baselines periodically
                if len(self._metrics_history) >= 60:  # Every minute
                    await self._update_performance_baselines()
                
                # Check for anomalies
                anomalies = self._detect_anomalies(metrics)
                if anomalies:
                    self.logger.warning(
                        "Resource anomalies detected",
                        anomalies=anomalies
                    )
                
                await asyncio.sleep(1)  # Collect every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_io_read=disk_io.read_bytes if disk_io else 0,
            disk_io_write=disk_io.write_bytes if disk_io else 0,
            network_sent=net_io.bytes_sent if net_io else 0,
            network_recv=net_io.bytes_recv if net_io else 0,
            active_connections=len(psutil.net_connections()),
            thread_count=psutil.Process().num_threads()
        )
    
    async def _check_avatar_speaking(self) -> bool:
        """Check if avatar is currently speaking."""
        if not self.system1_interface:
            return False
        
        try:
            status = await self.system1_interface.get_current_status()
            return status.get('is_speaking', False)
        except Exception as e:
            self.logger.error(f"Failed to check avatar speaking status: {e}")
            return False
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        status = {
            'has_errors': False,
            'last_activity': datetime.now(),
            'error_details': None
        }
        
        # Check System1 status
        if self.system1_interface:
            try:
                s1_status = await self.system1_interface.get_current_status()
                if s1_status.get('error'):
                    status['has_errors'] = True
                    status['error_details'] = {'system1': s1_status['error']}
            except Exception as e:
                status['has_errors'] = True
                status['error_details'] = {'system1': str(e)}
        
        # Get last activity from Redis if available
        if self._redis_client:
            try:
                last_activity = await self._redis_client.get('context:last_activity')
                if last_activity:
                    status['last_activity'] = datetime.fromisoformat(last_activity)
            except Exception:
                pass
        
        return status
    
    async def _get_queue_status(self) -> Dict[str, int]:
        """Get processing queue status."""
        # In a real implementation, this would query actual queue
        # For now, simulate based on recent activity
        recent_count = sum(
            1 for interaction in self._interaction_history
            if (datetime.now() - interaction['timestamp']).seconds < 60
        )
        
        return {
            'size': min(recent_count, 20),  # Simulated queue size
            'processing': max(0, recent_count - 5)
        }
    
    async def _get_resource_utilization(self) -> Dict[str, float]:
        """Get current resource utilization."""
        if self._metrics_history:
            latest = self._metrics_history[-1]
            return {
                'cpu': latest.cpu_percent / 100.0,
                'memory': latest.memory_percent / 100.0,
                'threads': latest.thread_count / 100.0  # Normalized
            }
        
        # Fallback to direct measurement
        return {
            'cpu': psutil.cpu_percent() / 100.0,
            'memory': psutil.virtual_memory().percent / 100.0,
            'threads': psutil.Process().num_threads() / 100.0
        }
    
    async def _get_active_processes(self) -> List[str]:
        """Get list of active processes."""
        active = []
        
        # Check if gateway is processing
        if self._interaction_history:
            recent = [
                i for i in self._interaction_history
                if (datetime.now() - i['timestamp']).seconds < 10
            ]
            if recent:
                active.append('gateway')
        
        # Check if agents are active
        if self.system2_interface:
            agent_statuses = await self.system2_interface.get_agent_status()
            for agent_id, status in agent_statuses.items():
                if status.is_active:
                    active.append(f'agent:{agent_id}')
        
        return active
    
    def _calculate_system_availability(
        self,
        is_speaking: bool,
        is_idle: bool,
        is_busy: bool,
        has_errors: bool,
        queue_size: int
    ) -> float:
        """Calculate system availability score."""
        score = 1.0
        
        if has_errors:
            score *= 0.3
        if is_speaking:
            score *= 0.7
        if is_busy:
            score *= 0.6
        if queue_size > 10:
            score *= 0.5
        elif queue_size > 5:
            score *= 0.8
        
        if is_idle and not has_errors:
            score = min(1.0, score * 1.2)
        
        return max(0.0, min(1.0, score))
    
    async def _update_user_session(
        self,
        user_id: str,
        stimuli: CategorizedStimuli
    ) -> UserSession:
        """Update or create user session."""
        now = datetime.now()
        
        if user_id not in self._user_sessions:
            session = UserSession(
                user_id=user_id,
                started_at=now,
                last_interaction=now
            )
            self._user_sessions[user_id] = session
        else:
            session = self._user_sessions[user_id]
            # Check for session timeout (30 minutes)
            if (now - session.last_interaction).seconds > 1800:
                # Start new session
                session = UserSession(
                    user_id=user_id,
                    started_at=now,
                    last_interaction=now
                )
                self._user_sessions[user_id] = session
            else:
                session.last_interaction = now
        
        session.interaction_count += 1
        
        # Extract topic from category
        session.topics.append(stimuli.category.value)
        
        return session
    
    def _calculate_interaction_frequency(self, session: UserSession) -> float:
        """Calculate user interaction frequency."""
        duration = session.get_session_duration()
        if duration < 60:  # Less than a minute
            return session.interaction_count  # interactions per minute
        
        return (session.interaction_count / duration) * 60
    
    def _determine_engagement_level(
        self,
        session: UserSession,
        stimuli: CategorizedStimuli
    ) -> str:
        """Determine user engagement level."""
        frequency = self._calculate_interaction_frequency(session)
        
        # Check interaction patterns
        high_value_categories = {
            StimuliCategory.DIRECT_ADMIN,
            StimuliCategory.USER_INTERACTION,
            StimuliCategory.EMERGENCY
        }
        
        high_value_ratio = sum(
            1 for topic in session.topics
            if topic in [cat.value for cat in high_value_categories]
        ) / max(1, len(session.topics))
        
        # Calculate engagement score
        engagement_score = (
            frequency * 0.4 +
            high_value_ratio * 0.3 +
            stimuli.confidence * 0.3
        )
        
        if engagement_score > 0.7 or frequency > 10:
            return "high"
        elif engagement_score > 0.4 or frequency > 3:
            return "medium"
        else:
            return "low"
    
    async def _extract_topics(
        self,
        stimuli: CategorizedStimuli,
        session: UserSession
    ) -> List[str]:
        """Extract conversation topics."""
        topics = [stimuli.category.value]
        
        # Add specific topics based on content analysis
        content_lower = stimuli.content.lower()
        topic_keywords = {
            'weather': ['weather', 'temperature', 'rain', 'sunny'],
            'gaming': ['game', 'play', 'stream', 'match'],
            'music': ['music', 'song', 'sing', 'dance'],
            'tech': ['code', 'program', 'computer', 'software'],
            'chat': ['hello', 'hi', 'how are', 'bye']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        # Include recent session topics
        recent_topics = list(set(session.topics[-5:]))
        topics.extend(recent_topics)
        
        return list(set(topics))[:5]  # Deduplicate and limit
    
    async def _calculate_preference_match(
        self,
        user_id: str,
        stimuli: CategorizedStimuli
    ) -> float:
        """Calculate how well stimuli matches user preferences."""
        if user_id not in self._user_patterns:
            # No patterns yet, neutral match
            return 0.5
        
        patterns = self._user_patterns[user_id]
        
        # Check category preference
        category_prefs = patterns.get('category_preferences', {})
        category_score = category_prefs.get(stimuli.category.value, 0.5)
        
        # Check time preference
        hour = datetime.now().hour
        time_prefs = patterns.get('time_preferences', {})
        time_score = time_prefs.get(str(hour), 0.5)
        
        # Combine scores
        return (category_score * 0.7 + time_score * 0.3)
    
    async def _analyze_historical_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze historical user patterns."""
        # Filter interactions for this user
        user_interactions = [
            i for i in self._interaction_history
            if i['user_id'] == user_id
        ]
        
        if not user_interactions:
            return {}
        
        # Calculate patterns
        patterns = {
            'total_interactions': len(user_interactions),
            'average_sentiment': statistics.mean(
                [i['sentiment'] for i in user_interactions]
            ) if user_interactions else 0.0,
            'preferred_categories': self._get_preferred_categories(user_interactions),
            'peak_activity_hours': self._get_peak_hours(user_interactions),
            'average_session_duration': self._get_avg_session_duration(user_id)
        }
        
        # Update stored patterns
        self._user_patterns[user_id] = patterns
        
        return patterns
    
    async def _analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment of content."""
        # Simple keyword-based sentiment analysis
        positive_words = {
            'happy', 'great', 'good', 'love', 'awesome', 'wonderful',
            'fantastic', 'amazing', 'excellent', 'thanks', 'thank you'
        }
        negative_words = {
            'sad', 'bad', 'hate', 'terrible', 'awful', 'horrible',
            'stupid', 'angry', 'frustrated', 'disappointed'
        }
        
        content_lower = content.lower()
        words = content_lower.split()
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if positive_count + negative_count == 0:
            return 0.0  # Neutral
        
        # Calculate sentiment score (-1 to 1)
        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        
        return sentiment
    
    async def _get_category_distribution(self, user_id: str) -> Dict[str, float]:
        """Get distribution of interaction categories for user."""
        user_interactions = [
            i for i in self._interaction_history
            if i['user_id'] == user_id
        ]
        
        if not user_interactions:
            return {}
        
        category_counts = defaultdict(int)
        for interaction in user_interactions:
            category_counts[interaction['category']] += 1
        
        total = len(user_interactions)
        return {
            category: count / total
            for category, count in category_counts.items()
        }
    
    async def _check_autonomous_mode(self) -> bool:
        """Check if autonomous mode is active."""
        # Check internal state first
        if self._autonomous_mode is not None:
            return self._autonomous_mode
        
        # Query System1 if available
        if self.system1_interface:
            try:
                status = await self.system1_interface.get_current_status()
                return status.get('mode') == 'autonomous'
            except Exception:
                pass
        
        return False
    
    async def _get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming status."""
        status = {
            'is_live': self._streaming_active,
            'platform': self._streaming_platform,
            'viewer_count': None
        }
        
        # Get additional info from System1 if available
        if self.system1_interface and self._streaming_active:
            try:
                system_status = await self.system1_interface.get_current_status()
                status['viewer_count'] = system_status.get('viewer_count', 0)
            except Exception:
                pass
        
        return status
    
    async def _analyze_activity_level(self) -> str:
        """Analyze recent activity level."""
        # Count recent interactions
        recent_count = sum(
            1 for i in self._interaction_history
            if (datetime.now() - i['timestamp']).seconds < 300  # Last 5 minutes
        )
        
        if recent_count > 20:
            return "high"
        elif recent_count > 5:
            return "moderate"
        else:
            return "low"
    
    def _calculate_time_of_day_factor(self, hour: int) -> float:
        """Calculate activity factor based on time of day."""
        # Peak hours: 6 PM - 11 PM (18-23)
        if 18 <= hour <= 23:
            return 0.9
        # Active hours: 10 AM - 6 PM (10-18)
        elif 10 <= hour < 18:
            return 0.7
        # Morning: 6 AM - 10 AM (6-10)
        elif 6 <= hour < 10:
            return 0.5
        # Night: 11 PM - 6 AM
        else:
            return 0.3
    
    async def _check_special_events(self) -> Dict[str, Any]:
        """Check for any special events."""
        active_events = {}
        
        # Check current special events
        for event_name, event_data in self._special_events.items():
            # Events expire after 24 hours
            if (datetime.now() - event_data['started_at']).total_seconds() < 86400:
                active_events[event_name] = event_data['metadata']
        
        # Clean up expired events
        self._special_events = {
            k: v for k, v in self._special_events.items()
            if (datetime.now() - v['started_at']).total_seconds() < 86400
        }
        
        return active_events
    
    async def _get_environmental_triggers(self) -> List[str]:
        """Get list of active environmental triggers."""
        triggers = []
        
        if self._autonomous_mode:
            triggers.append('autonomous_mode')
        
        if self._streaming_active:
            triggers.append(f'streaming_{self._streaming_platform}')
        
        # Time-based triggers
        hour = datetime.now().hour
        if 18 <= hour <= 23:
            triggers.append('peak_hours')
        elif 0 <= hour < 6:
            triggers.append('late_night')
        
        # Activity-based triggers
        activity = await self._analyze_activity_level()
        if activity == "high":
            triggers.append('high_activity')
        
        return triggers
    
    async def _get_mode_settings(self) -> Dict[str, Any]:
        """Get current mode configuration."""
        settings = {
            'autonomous_mode': self._autonomous_mode,
            'streaming_mode': self._streaming_active,
            'interaction_mode': 'reactive'  # Default
        }
        
        if self._autonomous_mode:
            settings['interaction_mode'] = 'proactive'
        
        return settings
    
    async def _get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        if self._metrics_history:
            return self._metrics_history[-1]
        
        # Collect fresh metrics
        return await self._collect_system_metrics()
    
    def _determine_resource_pressure(
        self,
        cpu_avail: float,
        mem_avail: float,
        metrics: SystemMetrics
    ) -> str:
        """Determine overall resource pressure level."""
        # Consider multiple factors
        pressure_score = 0.0
        
        # CPU pressure
        if cpu_avail < 0.2:
            pressure_score += 0.4
        elif cpu_avail < 0.4:
            pressure_score += 0.2
        
        # Memory pressure
        if mem_avail < 0.2:
            pressure_score += 0.4
        elif mem_avail < 0.4:
            pressure_score += 0.2
        
        # Thread pressure
        if metrics.thread_count > 100:
            pressure_score += 0.2
        
        # Active connections pressure
        if metrics.active_connections > 1000:
            pressure_score += 0.2
        
        if pressure_score >= 0.8:
            return "critical"
        elif pressure_score >= 0.5:
            return "high"
        elif pressure_score >= 0.2:
            return "normal"
        else:
            return "low"
    
    def _identify_bottlenecks(
        self,
        metrics: SystemMetrics,
        cpu_avail: float,
        mem_avail: float
    ) -> List[str]:
        """Identify system bottlenecks."""
        bottlenecks = []
        
        if cpu_avail < 0.2:
            bottlenecks.append("cpu_exhausted")
        elif cpu_avail < 0.4:
            bottlenecks.append("cpu_constrained")
        
        if mem_avail < 0.2:
            bottlenecks.append("memory_exhausted")
        elif mem_avail < 0.4:
            bottlenecks.append("memory_constrained")
        
        if metrics.thread_count > 200:
            bottlenecks.append("thread_exhaustion")
        
        if metrics.active_connections > 2000:
            bottlenecks.append("connection_limit")
        
        # Check historical trends
        if len(self._metrics_history) > 60:
            recent_cpu = [m.cpu_percent for m in list(self._metrics_history)[-60:]]
            if statistics.mean(recent_cpu) > 80:
                bottlenecks.append("sustained_high_cpu")
        
        return bottlenecks
    
    async def _get_gpu_availability(self) -> Optional[float]:
        """Get GPU availability if applicable."""
        # This would integrate with GPU monitoring tools
        # For now, return None indicating no GPU monitoring
        return None
    
    async def _estimate_bandwidth(self) -> float:
        """Estimate available network bandwidth."""
        if len(self._metrics_history) < 2:
            return 100.0  # Default 100 Mbps
        
        # Calculate bandwidth usage from metrics
        latest = self._metrics_history[-1]
        previous = self._metrics_history[-2]
        
        time_delta = (latest.timestamp - previous.timestamp).total_seconds()
        if time_delta <= 0:
            return 100.0
        
        # Calculate bytes per second
        sent_rate = (latest.network_sent - previous.network_sent) / time_delta
        recv_rate = (latest.network_recv - previous.network_recv) / time_delta
        
        # Convert to Mbps and estimate available (assume 100 Mbps total)
        used_mbps = (sent_rate + recv_rate) * 8 / 1_000_000
        available = max(0, 100 - used_mbps)
        
        return available
    
    async def _get_storage_availability(self) -> float:
        """Get storage availability."""
        try:
            disk_usage = psutil.disk_usage('/')
            return 1.0 - (disk_usage.percent / 100.0)
        except Exception:
            return 0.5  # Default to 50% if unable to determine
    
    def _is_cache_valid(self, cache_key: str, ttl_seconds: int) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = (datetime.now() - self._cache_timestamps[cache_key]).total_seconds()
        return age < ttl_seconds
    
    def _invalidate_cache(self, cache_key: str) -> None:
        """Invalidate specific cache."""
        self._cache_timestamps.pop(cache_key, None)
        
        if cache_key == "system_state":
            self._system_state_cache = None
        elif cache_key == "environmental":
            self._environmental_cache = None
        elif cache_key == "resources":
            self._resource_cache = None
    
    def _clear_all_caches(self) -> None:
        """Clear all cached data."""
        self._system_state_cache = None
        self._environmental_cache = None
        self._resource_cache = None
        self._cache_timestamps.clear()
    
    async def _establish_performance_baselines(self) -> None:
        """Establish performance baselines on startup."""
        self.logger.info("Establishing performance baselines")
        
        # Collect samples
        samples = []
        for _ in range(10):
            metrics = await self._collect_system_metrics()
            samples.append(metrics)
            await asyncio.sleep(0.5)
        
        # Calculate baselines
        self._performance_baselines = {
            'cpu': statistics.mean([s.cpu_percent for s in samples]),
            'memory': statistics.mean([s.memory_percent for s in samples]),
            'threads': statistics.mean([s.thread_count for s in samples])
        }
        
        self.logger.info(
            "Performance baselines established",
            baselines=self._performance_baselines
        )
    
    async def _update_performance_baselines(self) -> None:
        """Update performance baselines with recent data."""
        if len(self._metrics_history) < 60:
            return
        
        recent = list(self._metrics_history)[-60:]
        
        # Use rolling average
        self._performance_baselines['cpu'] = (
            self._performance_baselines['cpu'] * 0.8 +
            statistics.mean([m.cpu_percent for m in recent]) * 0.2
        )
        self._performance_baselines['memory'] = (
            self._performance_baselines['memory'] * 0.8 +
            statistics.mean([m.memory_percent for m in recent]) * 0.2
        )
        self._performance_baselines['threads'] = (
            self._performance_baselines['threads'] * 0.8 +
            statistics.mean([m.thread_count for m in recent]) * 0.2
        )
    
    def _detect_anomalies(self, metrics: SystemMetrics) -> List[str]:
        """Detect anomalies in system metrics."""
        anomalies = []
        
        if not self._performance_baselines:
            return anomalies
        
        # Check for significant deviations
        cpu_deviation = abs(metrics.cpu_percent - self._performance_baselines['cpu'])
        if cpu_deviation > self._performance_baselines['cpu'] * 0.5:
            anomalies.append(f"cpu_anomaly:{metrics.cpu_percent:.1f}%")
        
        memory_deviation = abs(metrics.memory_percent - self._performance_baselines['memory'])
        if memory_deviation > self._performance_baselines['memory'] * 0.3:
            anomalies.append(f"memory_anomaly:{metrics.memory_percent:.1f}%")
        
        thread_deviation = abs(metrics.thread_count - self._performance_baselines['threads'])
        if thread_deviation > self._performance_baselines['threads'] * 0.5:
            anomalies.append(f"thread_anomaly:{metrics.thread_count}")
        
        return anomalies
    
    async def _load_persisted_state(self) -> None:
        """Load persisted state from storage."""
        if not self._redis_client:
            return
        
        try:
            # Load user patterns
            patterns_data = await self._redis_client.get('context:user_patterns')
            if patterns_data:
                self._user_patterns = json.loads(patterns_data)
            
            # Load special events
            events_data = await self._redis_client.get('context:special_events')
            if events_data:
                events = json.loads(events_data)
                # Reconstruct datetime objects
                for event_name, event_data in events.items():
                    event_data['started_at'] = datetime.fromisoformat(
                        event_data['started_at']
                    )
                self._special_events = events
            
            # Load mode states
            mode_data = await self._redis_client.get('context:mode_states')
            if mode_data:
                modes = json.loads(mode_data)
                self._autonomous_mode = modes.get('autonomous_mode', False)
                self._streaming_active = modes.get('streaming_active', False)
                self._streaming_platform = modes.get('streaming_platform')
            
            self.logger.info("Loaded persisted state from Redis")
            
        except Exception as e:
            self.logger.error(f"Failed to load persisted state: {e}")
    
    async def _persist_state(self) -> None:
        """Persist current state to storage."""
        if not self._redis_client:
            return
        
        try:
            # Save user patterns
            await self._redis_client.set(
                'context:user_patterns',
                json.dumps(self._user_patterns)
            )
            
            # Save special events (convert datetime to string)
            events_data = {}
            for event_name, event_data in self._special_events.items():
                events_data[event_name] = {
                    'started_at': event_data['started_at'].isoformat(),
                    'metadata': event_data['metadata']
                }
            await self._redis_client.set(
                'context:special_events',
                json.dumps(events_data)
            )
            
            # Save mode states
            await self._redis_client.set(
                'context:mode_states',
                json.dumps({
                    'autonomous_mode': self._autonomous_mode,
                    'streaming_active': self._streaming_active,
                    'streaming_platform': self._streaming_platform
                })
            )
            
            # Save last activity timestamp
            await self._redis_client.set(
                'context:last_activity',
                datetime.now().isoformat()
            )
            
            self.logger.info("Persisted state to Redis")
            
        except Exception as e:
            self.logger.error(f"Failed to persist state: {e}")
    
    async def _persist_state_update(self, update: Dict[str, Any]) -> None:
        """Persist specific state update."""
        if not self._redis_client:
            return
        
        try:
            # Update specific keys based on update content
            if 'autonomous_mode' in update or 'streaming_active' in update:
                await self._redis_client.set(
                    'context:mode_states',
                    json.dumps({
                        'autonomous_mode': self._autonomous_mode,
                        'streaming_active': self._streaming_active,
                        'streaming_platform': self._streaming_platform
                    })
                )
            
            if 'special_event' in update:
                events_data = {}
                for event_name, event_data in self._special_events.items():
                    events_data[event_name] = {
                        'started_at': event_data['started_at'].isoformat(),
                        'metadata': event_data['metadata']
                    }
                await self._redis_client.set(
                    'context:special_events',
                    json.dumps(events_data)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to persist state update: {e}")
    
    def _get_preferred_categories(
        self,
        interactions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Get user's preferred interaction categories."""
        if not interactions:
            return {}
        
        category_counts = defaultdict(int)
        for interaction in interactions:
            category_counts[interaction['category']] += 1
        
        total = len(interactions)
        preferences = {}
        
        for category, count in category_counts.items():
            # Calculate preference score based on frequency and engagement
            engaged_count = sum(
                1 for i in interactions
                if i['category'] == category and i['engagement'] == 'high'
            )
            
            preference_score = (count / total) * 0.7 + (engaged_count / count) * 0.3
            preferences[category] = preference_score
        
        return preferences
    
    def _get_peak_hours(self, interactions: List[Dict[str, Any]]) -> List[int]:
        """Get user's peak activity hours."""
        if not interactions:
            return []
        
        hour_counts = defaultdict(int)
        for interaction in interactions:
            hour = interaction['timestamp'].hour
            hour_counts[hour] += 1
        
        # Get top 3 hours
        sorted_hours = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [hour for hour, _ in sorted_hours[:3]]
    
    def _get_avg_session_duration(self, user_id: str) -> float:
        """Get average session duration for user."""
        if user_id not in self._user_sessions:
            return 0.0
        
        session = self._user_sessions[user_id]
        return session.get_session_duration()