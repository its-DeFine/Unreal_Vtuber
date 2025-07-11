"""
Context Analyzer Node for GraphFlow Pipeline.

This node performs comprehensive context analysis on categorized stimuli
to provide rich context for decision making.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import psutil
import random

from ...models.stimuli import CategorizedStimuli, AnalyzedStimuli
from ...models.context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis
)
from ...config.settings import AnalyzerConfig
from ...utils.logging import get_structured_logger
from ...services.context_service import ContextService


class ContextAnalyzerNode:
    """
    GraphFlow node for context analysis.
    
    Analyzes multiple dimensions of context including:
    - System state (speaking, idle, busy, errors)
    - User interaction patterns and history
    - Environmental factors (streaming, autonomous mode)
    - Resource availability (CPU, memory, agents)
    """
    
    def __init__(self, config: AnalyzerConfig, context_service: Optional[ContextService] = None):
        """
        Initialize the analyzer node.
        
        Args:
            config: Analyzer configuration
            context_service: Optional context service for centralized state management
        """
        self.config = config
        self.logger = get_structured_logger("analyzer_node")
        self.context_service = context_service
        
        # Context storage (fallback if no context service)
        self._user_history: Dict[str, Any] = {}
        self._system_state_cache: Optional[SystemStateAnalysis] = None
        self._cache_timestamp: Optional[datetime] = None
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the analyzer node."""
        try:
            self.logger.info("Initializing analyzer node")
            
            # Initialize any required connections or services
            
            self.is_initialized = True
            self.logger.info("Analyzer node initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analyzer node: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the analyzer node."""
        self.logger.info("Shutting down analyzer node")
        
        # Clear caches
        self._user_history.clear()
        self._system_state_cache = None
        
        self.is_initialized = False
    
    async def process(self, categorized_stimuli: CategorizedStimuli) -> AnalyzedStimuli:
        """
        Analyze context for categorized stimuli.
        
        Performs comprehensive analysis across multiple dimensions
        to provide rich context for decision making.
        
        Args:
            categorized_stimuli: Categorized stimuli to analyze
            
        Returns:
            AnalyzedStimuli with full context analysis
        """
        start_time = datetime.now()
        
        try:
            # Use context service if available for better state management
            if self.context_service and self.context_service.is_initialized:
                # Perform analyses based on configuration depth
                if self.config.analysis_depth.value == "minimal":
                    # Quick analysis using cached data
                    system_state = await self.context_service.get_system_state(force_refresh=False)
                    user_context = await self.context_service.analyze_user_context(
                        categorized_stimuli, include_history=False
                    )
                    environmental = await self.context_service.get_environmental_context(force_refresh=False)
                    resources = await self.context_service.get_resource_availability(include_predictions=False)
                    
                elif self.config.analysis_depth.value == "deep":
                    # Deep analysis with full refresh and predictions
                    system_state = await self.context_service.get_system_state(force_refresh=True)
                    user_context = await self.context_service.analyze_user_context(
                        categorized_stimuli, include_history=True
                    )
                    environmental = await self.context_service.get_environmental_context(force_refresh=True)
                    resources = await self.context_service.get_resource_availability(include_predictions=True)
                    
                else:  # standard
                    # Standard analysis - balanced approach
                    system_state = await self.context_service.get_system_state()
                    user_context = await self.context_service.analyze_user_context(categorized_stimuli)
                    environmental = await self.context_service.get_environmental_context()
                    resources = await self.context_service.get_resource_availability()
            else:
                # Fallback to local analysis methods
                if self.config.analysis_depth.value == "minimal":
                    # Quick analysis - only essential checks
                    system_state = await self._quick_system_state_check()
                    user_context = self._minimal_user_context(categorized_stimuli)
                    environmental = self._minimal_environmental_check()
                    resources = await self._quick_resource_check()
                    
                elif self.config.analysis_depth.value == "deep":
                    # Deep analysis - comprehensive checks
                    system_state = await self._analyze_system_state()
                    user_context = await self._analyze_user_context(categorized_stimuli)
                    environmental = await self._analyze_environmental_context()
                    resources = await self._analyze_resource_availability()
                    
                else:  # standard
                    # Standard analysis - balanced approach
                    system_state = await self._analyze_system_state()
                    user_context = await self._analyze_user_context(categorized_stimuli)
                    environmental = await self._analyze_environmental_context()
                    resources = await self._analyze_resource_availability()
            
            # Create analyzed stimuli
            analyzed = AnalyzedStimuli(
                **categorized_stimuli.__dict__,
                system_state_analysis=system_state,
                user_context_analysis=user_context,
                environmental_analysis=environmental,
                resource_analysis=resources,
                analysis_timestamp=datetime.now()
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate context score
            context_score = analyzed.get_context_score()
            if self.context_service:
                # Get more accurate score from context service
                context_score = await self.context_service.get_context_score(
                    system_state, user_context, environmental, resources
                )
            
            self.logger.info(
                "Context analysis completed",
                stimuli_id=categorized_stimuli.id,
                analysis_depth=self.config.analysis_depth.value,
                context_score=context_score,
                processing_time=processing_time,
                using_context_service=self.context_service is not None
            )
            
            return analyzed
            
        except Exception as e:
            self.logger.error(
                f"Context analysis failed for stimuli {categorized_stimuli.id}: {e}"
            )
            # Return with minimal context
            return AnalyzedStimuli(
                **categorized_stimuli.__dict__,
                analysis_timestamp=datetime.now()
            )
    
    async def _analyze_system_state(self) -> SystemStateAnalysis:
        """Analyze current system state."""
        # Check cache first
        if self.config.cache_enabled and self._system_state_cache:
            cache_age = (datetime.now() - self._cache_timestamp).seconds
            if cache_age < self.config.cache_ttl:
                return self._system_state_cache
        
        # In a real implementation, this would query actual system state
        # For now, simulate with realistic values
        try:
            # Get actual system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Simulate other states (would be real queries in production)
            is_speaking = random.random() < 0.2  # 20% chance
            is_idle = not is_speaking and random.random() < 0.7  # 70% chance when not speaking
            is_busy = not is_speaking and not is_idle
            has_errors = random.random() < 0.05  # 5% chance
            queue_size = random.randint(0, 20)
            
            analysis = SystemStateAnalysis(
                is_speaking=is_speaking,
                is_idle=is_idle,
                is_busy=is_busy,
                has_errors=has_errors,
                queue_size=queue_size,
                resource_utilization={
                    'cpu': cpu_percent / 100.0,
                    'memory': memory.percent / 100.0
                },
                availability_score=self._calculate_availability_score(
                    is_speaking, is_idle, has_errors, queue_size
                ),
                active_processes=['gateway', 'analyzer'] if not is_idle else [],
                last_activity_timestamp=datetime.now() if not is_idle else None
            )
            
            # Cache the result
            if self.config.cache_enabled:
                self._system_state_cache = analysis
                self._cache_timestamp = datetime.now()
            
            return analysis
            
        except Exception as e:
            self.logger.warning(f"System state analysis failed: {e}")
            # Return default state
            return SystemStateAnalysis(
                is_speaking=False,
                is_idle=True,
                is_busy=False,
                has_errors=False,
                queue_size=0,
                resource_utilization={},
                availability_score=0.5
            )
    
    async def _analyze_user_context(self, stimuli: CategorizedStimuli) -> UserContextAnalysis:
        """Analyze user interaction context."""
        # Update user history if configured
        if self.config.include_user_history:
            user_id = stimuli.metadata.get('user_id', 'anonymous')
            if user_id not in self._user_history:
                self._user_history[user_id] = {
                    'interactions': [],
                    'topics': [],
                    'last_seen': None
                }
            
            # Add to history
            self._user_history[user_id]['interactions'].append({
                'timestamp': datetime.now(),
                'category': stimuli.category.value,
                'content_preview': stimuli.content[:50]
            })
            self._user_history[user_id]['last_seen'] = datetime.now()
            
            # Keep history window limited
            if len(self._user_history[user_id]['interactions']) > self.config.history_window_size:
                self._user_history[user_id]['interactions'] = (
                    self._user_history[user_id]['interactions'][-self.config.history_window_size:]
                )
        
        # Calculate interaction metrics
        interaction_frequency = self._calculate_interaction_frequency(stimuli)
        engagement_level = self._determine_engagement_level(interaction_frequency)
        recent_topics = self._extract_recent_topics(stimuli)
        preference_match = self._calculate_preference_match(stimuli)
        
        return UserContextAnalysis(
            interaction_frequency=interaction_frequency,
            engagement_level=engagement_level,
            recent_topics=recent_topics,
            user_preference_match=preference_match,
            historical_response_patterns={
                'average_response_time': 2.5,  # Simulated
                'preferred_interaction_type': stimuli.category.value
            },
            user_id=stimuli.metadata.get('user_id'),
            session_duration=300.0,  # Simulated 5 minutes
            sentiment_score=0.7  # Simulated positive sentiment
        )
    
    async def _analyze_environmental_context(self) -> EnvironmentalAnalysis:
        """Analyze environmental context."""
        # In production, would query actual environmental state
        current_hour = datetime.now().hour
        time_of_day_factor = self._calculate_time_factor(current_hour)
        
        # Get temporal factors
        temporal_factors = await self._analyze_temporal_factors()
        
        return EnvironmentalAnalysis(
            autonomous_mode_active=random.random() < 0.3,  # 30% chance
            streaming_status=random.choice(['live', 'offline', 'offline']),  # More likely offline
            time_of_day_factor=time_of_day_factor,
            recent_activity_level=random.choice(['low', 'moderate', 'high']),
            external_event_context={
                'special_event': False,
                'scheduled_stream': False,
                **temporal_factors  # Include temporal analysis
            },
            platform_context='standalone',
            audience_size=random.randint(0, 1000) if random.random() < 0.3 else None
        )
    
    async def _analyze_resource_availability(self) -> ResourceAnalysis:
        """Analyze system resource availability."""
        try:
            # Get real system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Calculate availability (inverse of usage)
            cpu_availability = 1.0 - (cpu_percent / 100.0)
            memory_availability = 1.0 - (memory.percent / 100.0)
            
            # Simulate agent availability (in production would query actual agents)
            agent_availability = {
                'router_agent': True,
                'executor_agent': True,
                'analyzer_agent': True
            }
            
            # Estimate processing capacity based on resources
            estimated_capacity = int(
                min(cpu_availability, memory_availability) * 50
            )
            
            # Check actual system availability using health checks
            system1_availability = await self._check_system1_health()
            system2_availability = await self._check_system2_health()
            
            return ResourceAnalysis(
                cpu_availability=cpu_availability,
                memory_availability=memory_availability,
                agent_availability=agent_availability,
                system1_availability=system1_availability,
                system2_availability=system2_availability,
                estimated_processing_capacity=estimated_capacity,
                network_bandwidth_available=100.0,  # Simulated 100 Mbps
                resource_pressure_level=self._determine_pressure_level(
                    cpu_availability, memory_availability
                )
            )
            
        except Exception as e:
            self.logger.warning(f"Resource analysis failed: {e}")
            # Return default availability
            return ResourceAnalysis(
                cpu_availability=0.5,
                memory_availability=0.5,
                agent_availability={},
                system1_availability=True,
                system2_availability=True,
                estimated_processing_capacity=10
            )
    
    # Helper methods for quick/minimal analysis
    async def _quick_system_state_check(self) -> SystemStateAnalysis:
        """Quick system state check for minimal analysis."""
        return SystemStateAnalysis(
            is_speaking=False,
            is_idle=True,
            is_busy=False,
            has_errors=False,
            queue_size=0,
            resource_utilization={},
            availability_score=0.8
        )
    
    def _minimal_user_context(self, stimuli: CategorizedStimuli) -> UserContextAnalysis:
        """Minimal user context for quick analysis."""
        return UserContextAnalysis(
            interaction_frequency=1.0,
            engagement_level="medium",
            recent_topics=[],
            user_preference_match=0.5,
            historical_response_patterns={}
        )
    
    def _minimal_environmental_check(self) -> EnvironmentalAnalysis:
        """Minimal environmental check."""
        return EnvironmentalAnalysis(
            autonomous_mode_active=False,
            streaming_status="offline",
            time_of_day_factor=0.5,
            recent_activity_level="moderate",
            external_event_context={}
        )
    
    async def _quick_resource_check(self) -> ResourceAnalysis:
        """Quick resource availability check."""
        # For quick checks, still do basic health checks but with shorter timeout
        system1_availability = await self._check_system1_health()
        system2_availability = await self._check_system2_health()
        
        return ResourceAnalysis(
            cpu_availability=0.7,
            memory_availability=0.7,
            agent_availability={},
            system1_availability=system1_availability,
            system2_availability=system2_availability,
            estimated_processing_capacity=20
        )
    
    # Utility methods
    def _calculate_availability_score(
        self, is_speaking: bool, is_idle: bool, has_errors: bool, queue_size: int
    ) -> float:
        """Calculate overall system availability score."""
        score = 1.0
        
        if is_speaking:
            score -= 0.3
        if not is_idle:
            score -= 0.2
        if has_errors:
            score -= 0.5
        if queue_size > 10:
            score -= 0.2
        elif queue_size > 5:
            score -= 0.1
            
        return max(0.0, score)
    
    def _calculate_interaction_frequency(self, stimuli: CategorizedStimuli) -> float:
        """Calculate user interaction frequency."""
        user_id = stimuli.metadata.get('user_id', 'anonymous')
        if user_id in self._user_history:
            interactions = self._user_history[user_id]['interactions']
            if len(interactions) > 1:
                # Calculate average time between interactions
                time_diffs = []
                for i in range(1, len(interactions)):
                    diff = (interactions[i]['timestamp'] - interactions[i-1]['timestamp']).seconds
                    time_diffs.append(diff)
                
                avg_seconds = sum(time_diffs) / len(time_diffs)
                # Convert to interactions per minute
                return 60.0 / avg_seconds if avg_seconds > 0 else 0.0
        
        return 1.0  # Default frequency
    
    def _determine_engagement_level(self, frequency: float) -> str:
        """Determine user engagement level based on interaction frequency."""
        if frequency > 10:
            return "high"
        elif frequency > 2:
            return "medium"
        else:
            return "low"
    
    def _extract_recent_topics(self, stimuli: CategorizedStimuli) -> List[str]:
        """Extract recent conversation topics."""
        # Simple topic extraction based on category
        topics = [stimuli.category.value]
        
        # Add more specific topics based on content keywords
        content_lower = stimuli.content.lower()
        if 'weather' in content_lower:
            topics.append('weather')
        if 'music' in content_lower:
            topics.append('music')
        if 'game' in content_lower or 'play' in content_lower:
            topics.append('gaming')
            
        return topics[:5]  # Limit to 5 topics
    
    def _calculate_preference_match(self, stimuli: CategorizedStimuli) -> float:
        """Calculate how well stimuli matches user preferences."""
        # Simplified preference matching
        base_score = 0.5
        
        # Boost score for certain categories
        if stimuli.category.value in ['USER_INTERACTION', 'DIRECT_ADMIN']:
            base_score += 0.3
            
        # Boost for high confidence categorization
        base_score += stimuli.confidence * 0.2
        
        return min(1.0, base_score)
    
    def _calculate_time_factor(self, hour: int) -> float:
        """Calculate time of day activity factor."""
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
    
    def _determine_pressure_level(self, cpu_avail: float, mem_avail: float) -> str:
        """Determine resource pressure level."""
        min_avail = min(cpu_avail, mem_avail)
        
        if min_avail < 0.2:
            return "critical"
        elif min_avail < 0.4:
            return "high"
        elif min_avail < 0.7:
            return "normal"
        else:
            return "low"
    
    async def _analyze_temporal_factors(self) -> Dict[str, Any]:
        """
        Analyze temporal factors affecting system behavior.
        
        Returns:
            Dictionary with temporal analysis including:
            - Day of week patterns
            - Time since last interaction
            - Recent activity patterns
            - Scheduled events
        """
        now = datetime.now()
        temporal_data = {}
        
        # Day of week analysis
        day_of_week = now.strftime('%A')
        is_weekend = now.weekday() >= 5
        temporal_data['day_of_week'] = day_of_week
        temporal_data['is_weekend'] = is_weekend
        
        # Time since last interaction
        if self._user_history:
            # Find most recent interaction
            last_interaction = None
            for user_data in self._user_history.values():
                if 'interactions' in user_data and user_data['interactions']:
                    latest = user_data['interactions'][-1]
                    if last_interaction is None or latest['timestamp'] > last_interaction:
                        last_interaction = latest['timestamp']
            
            if last_interaction:
                time_since_last = (now - last_interaction).seconds
                temporal_data['seconds_since_last_interaction'] = time_since_last
                temporal_data['interaction_gap_category'] = self._categorize_time_gap(time_since_last)
        
        # Activity patterns over last hour
        hour_activity = []
        for i in range(4):  # Check last 4 15-minute intervals
            interval_start = now - timedelta(minutes=(i+1)*15)
            interval_end = now - timedelta(minutes=i*15)
            
            # Count interactions in this interval
            interval_count = 0
            for user_data in self._user_history.values():
                if 'interactions' in user_data:
                    interval_count += sum(
                        1 for interaction in user_data['interactions']
                        if interval_start <= interaction['timestamp'] <= interval_end
                    )
            
            hour_activity.append({
                'interval': f'{i*15}-{(i+1)*15}min_ago',
                'count': interval_count
            })
        
        temporal_data['recent_activity_pattern'] = hour_activity
        
        # Peak hours analysis
        current_hour = now.hour
        temporal_data['is_peak_hours'] = 18 <= current_hour <= 23
        temporal_data['is_off_hours'] = 0 <= current_hour < 6
        
        # Seasonal factors (simplified)
        month = now.month
        temporal_data['season'] = self._get_season(month)
        
        # Business hours check
        temporal_data['is_business_hours'] = (
            9 <= current_hour <= 17 and not is_weekend
        )
        
        return temporal_data
    
    def _categorize_time_gap(self, seconds: int) -> str:
        """Categorize time gap between interactions."""
        if seconds < 60:
            return "immediate"
        elif seconds < 300:  # 5 minutes
            return "recent"
        elif seconds < 1800:  # 30 minutes
            return "moderate"
        elif seconds < 7200:  # 2 hours
            return "extended"
        else:
            return "long"
    
    def _get_season(self, month: int) -> str:
        """Get season based on month."""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"
    
    async def _check_system1_health(self) -> bool:
        """Check System1 (VTuber/Avatar) health via direct HTTP call."""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("http://localhost:5001/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy"
                    return False
        except Exception as e:
            self.logger.warning(f"System1 health check failed: {e}")
            return False
    
    async def _check_system2_health(self) -> bool:
        """Check System2 (AutoGen) health via direct HTTP call."""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("http://localhost:8200/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy"
                    return False
        except Exception as e:
            self.logger.warning(f"System2 health check failed: {e}")
            return False