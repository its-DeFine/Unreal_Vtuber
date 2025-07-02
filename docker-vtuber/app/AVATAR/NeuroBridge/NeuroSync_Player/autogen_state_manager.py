"""
AutoGen State Management System
==============================

This module provides comprehensive state management for the multi-agent orchestrator.
It tracks conversation context, system state, content history, and performance metrics.

Key Components:
- OrchestratorState: Central state object
- StateManager: State management logic and utilities
- ConversationContext: Tracks conversation flow and topics
- EnvironmentState: Tracks game/avatar state
- ContentHistory: Manages content generation history
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import hashlib
import json


class ActivityLevel(Enum):
    """Stream activity levels"""
    IDLE = "idle"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    PEAK = "peak"


class StreamPhase(Enum):
    """Stream lifecycle phases"""
    STARTING = "starting"
    WARMING_UP = "warming_up"
    ACTIVE = "active"
    WINDING_DOWN = "winding_down"
    ENDING = "ending"


@dataclass
class ViewerMetrics:
    """Tracks viewer engagement metrics"""
    current_count: int = 0
    peak_count: int = 0
    average_count: float = 0.0
    join_rate: float = 0.0  # Viewers per minute
    chat_rate: float = 0.0  # Messages per minute
    engagement_score: float = 0.0  # 0-1 score
    active_chatters: Set[str] = field(default_factory=set)
    viewer_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_count(self, count: int):
        """Update viewer count and metrics"""
        self.current_count = count
        self.peak_count = max(self.peak_count, count)
        self.viewer_history.append((time.time(), count))
        
        # Calculate average
        if self.viewer_history:
            self.average_count = sum(v[1] for v in self.viewer_history) / len(self.viewer_history)
    
    def calculate_join_rate(self) -> float:
        """Calculate viewer join rate over last 5 minutes"""
        if len(self.viewer_history) < 2:
            return 0.0
            
        five_min_ago = time.time() - 300
        recent_history = [(t, c) for t, c in self.viewer_history if t > five_min_ago]
        
        if len(recent_history) < 2:
            return 0.0
            
        time_diff = recent_history[-1][0] - recent_history[0][0]
        count_diff = recent_history[-1][1] - recent_history[0][1]
        
        if time_diff > 0:
            self.join_rate = (count_diff / time_diff) * 60  # Per minute
        
        return self.join_rate


@dataclass
class ConversationContext:
    """Tracks conversation state and context"""
    recent_topics: deque = field(default_factory=lambda: deque(maxlen=10))
    user_interests: List[str] = field(default_factory=list)
    current_activity: str = "chatting"
    conversation_energy: float = 0.5  # 0-1 scale
    last_topic_change: float = field(default_factory=time.time)
    topic_durations: Dict[str, float] = field(default_factory=dict)
    message_sentiments: deque = field(default_factory=lambda: deque(maxlen=20))
    keywords_frequency: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def add_topic(self, topic: str):
        """Add a new conversation topic"""
        if self.recent_topics and self.recent_topics[-1] != topic:
            # Track duration of previous topic
            duration = time.time() - self.last_topic_change
            if self.recent_topics:
                prev_topic = self.recent_topics[-1]
                self.topic_durations[prev_topic] = self.topic_durations.get(prev_topic, 0) + duration
        
        self.recent_topics.append(topic)
        self.last_topic_change = time.time()
    
    def add_keywords(self, keywords: List[str]):
        """Track keyword frequency"""
        for keyword in keywords:
            self.keywords_frequency[keyword] += 1
    
    def get_trending_topics(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """Get most frequent recent keywords"""
        sorted_keywords = sorted(
            self.keywords_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        return sorted_keywords[:top_n]
    
    def calculate_energy(self) -> float:
        """Calculate conversation energy based on activity"""
        # Factors: message rate, sentiment, topic changes
        base_energy = 0.5
        
        # Recent topic changes increase energy
        recent_changes = sum(1 for _ in self.recent_topics)
        energy_from_changes = min(recent_changes * 0.1, 0.3)
        
        # Positive sentiments increase energy
        if self.message_sentiments:
            positive_ratio = sum(1 for s in self.message_sentiments if s > 0) / len(self.message_sentiments)
            energy_from_sentiment = positive_ratio * 0.2
        else:
            energy_from_sentiment = 0
        
        self.conversation_energy = min(base_energy + energy_from_changes + energy_from_sentiment, 1.0)
        return self.conversation_energy


@dataclass
class EnvironmentState:
    """Tracks game/avatar environment state"""
    current_scene: str = "default"
    avatar_state: Dict[str, Any] = field(default_factory=lambda: {
        "hair_color": "default",
        "outfit": "casual",
        "expression": "neutral",
        "pose": "idle"
    })
    active_effects: List[str] = field(default_factory=list)
    last_change_time: float = field(default_factory=time.time)
    change_history: deque = field(default_factory=lambda: deque(maxlen=50))
    scene_duration: Dict[str, float] = field(default_factory=dict)
    
    def update_scene(self, scene: str):
        """Update current scene and track duration"""
        if self.current_scene != scene:
            # Track duration of previous scene
            duration = time.time() - self.last_change_time
            self.scene_duration[self.current_scene] = self.scene_duration.get(self.current_scene, 0) + duration
            
            self.current_scene = scene
            self.last_change_time = time.time()
            self.change_history.append({
                "time": time.time(),
                "type": "scene",
                "from": self.current_scene,
                "to": scene
            })
    
    def update_avatar(self, attribute: str, value: str):
        """Update avatar state"""
        old_value = self.avatar_state.get(attribute)
        self.avatar_state[attribute] = value
        self.last_change_time = time.time()
        
        self.change_history.append({
            "time": time.time(),
            "type": "avatar",
            "attribute": attribute,
            "from": old_value,
            "to": value
        })
    
    def get_recent_changes(self, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get environment changes in the last N seconds"""
        cutoff_time = time.time() - seconds
        return [
            change for change in self.change_history 
            if change["time"] > cutoff_time
        ]


@dataclass
class ContentHistory:
    """Manages content generation history and patterns"""
    generated_content: deque = field(default_factory=lambda: deque(maxlen=100))
    content_hashes: Set[str] = field(default_factory=set)
    content_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    generation_times: deque = field(default_factory=lambda: deque(maxlen=100))
    repetition_tracker: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def add_content(self, content: str, content_type: str):
        """Add generated content to history"""
        timestamp = time.time()
        content_hash = hashlib.md5(content.lower().encode()).hexdigest()[:16]
        
        # Check for repetition
        if content_hash in self.content_hashes:
            self.repetition_tracker[content_hash] += 1
        
        self.generated_content.append({
            "content": content,
            "type": content_type,
            "hash": content_hash,
            "timestamp": timestamp
        })
        
        self.content_hashes.add(content_hash)
        self.content_types[content_type] += 1
        self.generation_times.append(timestamp)
    
    def get_recent_content(self, seconds: int = 300) -> List[Dict[str, Any]]:
        """Get content generated in the last N seconds"""
        cutoff_time = time.time() - seconds
        return [
            item for item in self.generated_content
            if item["timestamp"] > cutoff_time
        ]
    
    def calculate_generation_rate(self) -> float:
        """Calculate content generation rate per minute"""
        if len(self.generation_times) < 2:
            return 0.0
            
        time_span = self.generation_times[-1] - self.generation_times[0]
        if time_span > 0:
            return (len(self.generation_times) / time_span) * 60
        return 0.0
    
    def get_variety_score(self) -> float:
        """Calculate content variety score (0-1)"""
        if not self.generated_content:
            return 1.0
            
        # Check uniqueness in recent content
        recent = self.get_recent_content(300)
        if not recent:
            return 1.0
            
        unique_hashes = len(set(item["hash"] for item in recent))
        total_content = len(recent)
        
        return unique_hashes / total_content if total_content > 0 else 1.0


@dataclass
class SystemPerformance:
    """Tracks system performance metrics"""
    decision_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    api_response_times: Dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=50)))
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    success_rates: Dict[str, float] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    def record_latency(self, operation: str, latency: float):
        """Record operation latency"""
        self.decision_latencies.append((operation, latency, time.time()))
        self.api_response_times[operation].append(latency)
    
    def record_error(self, error_type: str):
        """Record error occurrence"""
        self.error_counts[error_type] += 1
    
    def calculate_success_rate(self, operation: str, successes: int, total: int) -> float:
        """Calculate and store success rate"""
        if total > 0:
            rate = successes / total
            self.success_rates[operation] = rate
            return rate
        return 0.0
    
    def get_average_latency(self, operation: str = None) -> float:
        """Get average latency for operation or overall"""
        if operation and operation in self.api_response_times:
            latencies = self.api_response_times[operation]
            return sum(latencies) / len(latencies) if latencies else 0.0
        
        # Overall average
        all_latencies = [l[1] for l in self.decision_latencies]
        return sum(all_latencies) / len(all_latencies) if all_latencies else 0.0


@dataclass
class OrchestratorState:
    """Central state object for the orchestrator"""
    # Core state from V2 compatibility
    is_speaking: bool = False
    current_speech_id: Optional[str] = None
    speech_start_time: Optional[float] = None
    speech_end_time: Optional[float] = None
    last_speech_completed: float = 0.0
    
    # Blendshape state
    blendshape_active: bool = False
    blendshape_start_time: Optional[float] = None
    blendshape_frame_count: int = 0
    blendshape_total_frames: int = 0
    
    # Timing
    last_user_input_time: float = field(default_factory=time.time)
    last_autonomous_speech_time: float = 0.0
    true_idle_duration: float = 0.0
    
    # Queue state
    speech_queue_size: int = 0
    pending_interrupts: int = 0
    
    # Enhanced state components
    viewer_metrics: ViewerMetrics = field(default_factory=ViewerMetrics)
    conversation_context: ConversationContext = field(default_factory=ConversationContext)
    environment_state: EnvironmentState = field(default_factory=EnvironmentState)
    content_history: ContentHistory = field(default_factory=ContentHistory)
    system_performance: SystemPerformance = field(default_factory=SystemPerformance)
    
    # Stream metadata
    stream_start_time: float = field(default_factory=time.time)
    stream_phase: StreamPhase = StreamPhase.STARTING
    activity_level: ActivityLevel = ActivityLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "is_speaking": self.is_speaking,
            "idle_duration": self.true_idle_duration,
            "viewer_count": self.viewer_metrics.current_count,
            "activity_level": self.activity_level.value,
            "stream_phase": self.stream_phase.value,
            "conversation_energy": self.conversation_context.conversation_energy,
            "current_scene": self.environment_state.current_scene,
            "content_variety": self.content_history.get_variety_score(),
            "timestamp": time.time()
        }


class StateManager:
    """Manages orchestrator state and provides utilities"""
    
    def __init__(self):
        self.state = OrchestratorState()
        self.logger = logging.getLogger(__name__)
        self._state_snapshots: deque = deque(maxlen=100)
        self._snapshot_interval = 30.0  # Seconds between snapshots
        self._last_snapshot_time = 0.0
    
    def update_idle_state(self):
        """Update idle duration calculation"""
        current_time = time.time()
        self.state.true_idle_duration = current_time - self.state.last_user_input_time
        
        # Update activity level based on idle time
        if self.state.true_idle_duration < 5:
            self.state.activity_level = ActivityLevel.HIGH
        elif self.state.true_idle_duration < 15:
            self.state.activity_level = ActivityLevel.MODERATE
        elif self.state.true_idle_duration < 30:
            self.state.activity_level = ActivityLevel.LOW
        else:
            self.state.activity_level = ActivityLevel.IDLE
    
    def update_stream_phase(self):
        """Update stream lifecycle phase"""
        stream_duration = time.time() - self.state.stream_start_time
        
        if stream_duration < 300:  # First 5 minutes
            self.state.stream_phase = StreamPhase.STARTING
        elif stream_duration < 900:  # 5-15 minutes
            self.state.stream_phase = StreamPhase.WARMING_UP
        elif self.state.viewer_metrics.current_count < self.state.viewer_metrics.average_count * 0.7:
            # Viewer count dropping
            self.state.stream_phase = StreamPhase.WINDING_DOWN
        else:
            self.state.stream_phase = StreamPhase.ACTIVE
    
    def update_interaction_time(self):
        """Update last interaction timestamp"""
        self.state.last_user_input_time = time.time()
        self.update_idle_state()
    
    def update_autonomous_generation_time(self):
        """Update last autonomous content generation time"""
        self.state.last_autonomous_speech_time = time.time()
    
    def update_activity(self, activity: str):
        """Update current activity"""
        self.state.conversation_context.current_activity = activity
        self.logger.debug(f"Activity updated to: {activity}")
    
    def add_viewer_interaction(self, viewer_name: str, message: str):
        """Add a viewer interaction to metrics and conversation context"""
        # Add viewer to active chatters
        self.state.viewer_metrics.active_chatters.add(viewer_name)
        
        # Update conversation context with message keywords
        keywords = [word for word in message.lower().split() if len(word) > 3]
        self.state.conversation_context.add_keywords(keywords)
        
        # Update interaction time
        self.update_interaction_time()
        
        self.logger.debug(f"Viewer interaction recorded: {viewer_name} - {message[:30]}...")
    
    def add_viewers(self, viewer_names: List[str]):
        """Add new viewers to metrics"""
        for name in viewer_names:
            self.state.viewer_metrics.active_chatters.add(name)
        
        # Update viewer count
        new_count = self.state.viewer_metrics.current_count + len(viewer_names)
        self.state.viewer_metrics.update_count(new_count)
    
    def update_conversation_topic(self, topic: str):
        """Update current conversation topic"""
        self.state.conversation_context.add_topic(topic)
        
        # Extract keywords (simple implementation)
        keywords = [word for word in topic.lower().split() if len(word) > 3]
        self.state.conversation_context.add_keywords(keywords)
    
    def get_idle_duration(self) -> float:
        """Get current idle duration in seconds"""
        self.update_idle_state()
        return self.state.true_idle_duration
    
    def get_viewer_count(self) -> int:
        """Get current viewer count"""
        return self.state.viewer_metrics.current_count
    
    def get_recent_topics(self, count: int = 5) -> List[str]:
        """Get recent conversation topics"""
        return list(self.state.conversation_context.recent_topics)[-count:]
    
    def get_engagement_score(self) -> float:
        """Calculate overall engagement score"""
        viewer_score = min(self.state.viewer_metrics.current_count / 100, 1.0) * 0.3
        chat_score = self.state.conversation_context.conversation_energy * 0.3
        variety_score = self.state.content_history.get_variety_score() * 0.2
        activity_score = (5 - self.state.activity_level.value) / 5 * 0.2
        
        return viewer_score + chat_score + variety_score + activity_score
    
    def should_take_snapshot(self) -> bool:
        """Check if it's time to take a state snapshot"""
        current_time = time.time()
        if current_time - self._last_snapshot_time >= self._snapshot_interval:
            self._last_snapshot_time = current_time
            return True
        return False
    
    def take_snapshot(self):
        """Take a snapshot of current state"""
        snapshot = {
            "timestamp": time.time(),
            "state": self.state.to_dict(),
            "metrics": {
                "viewer_metrics": {
                    "current": self.state.viewer_metrics.current_count,
                    "peak": self.state.viewer_metrics.peak_count,
                    "average": self.state.viewer_metrics.average_count,
                    "engagement": self.state.viewer_metrics.engagement_score
                },
                "content_metrics": {
                    "generation_rate": self.state.content_history.calculate_generation_rate(),
                    "variety_score": self.state.content_history.get_variety_score(),
                    "total_generated": len(self.state.content_history.generated_content)
                },
                "performance_metrics": {
                    "avg_latency": self.state.system_performance.get_average_latency(),
                    "error_count": sum(self.state.system_performance.error_counts.values())
                }
            }
        }
        
        self._state_snapshots.append(snapshot)
        return snapshot
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state"""
        return {
            "activity": {
                "level": self.state.activity_level.value,
                "idle_time": self.state.true_idle_duration,
                "is_speaking": self.state.is_speaking
            },
            "stream": {
                "phase": self.state.stream_phase.value,
                "duration": time.time() - self.state.stream_start_time,
                "viewer_count": self.state.viewer_metrics.current_count
            },
            "conversation": {
                "energy": self.state.conversation_context.conversation_energy,
                "recent_topics": list(self.state.conversation_context.recent_topics)[-3:],
                "trending_keywords": self.state.conversation_context.get_trending_topics(3)
            },
            "environment": {
                "scene": self.state.environment_state.current_scene,
                "avatar": self.state.environment_state.avatar_state,
                "recent_changes": len(self.state.environment_state.get_recent_changes(300))
            },
            "content": {
                "variety_score": self.state.content_history.get_variety_score(),
                "generation_rate": self.state.content_history.calculate_generation_rate(),
                "recent_types": dict(self.state.content_history.content_types)
            },
            "engagement_score": self.get_engagement_score()
        }
    
    def export_analytics(self) -> Dict[str, Any]:
        """Export analytics data for external analysis"""
        return {
            "session_info": {
                "start_time": self.state.stream_start_time,
                "duration": time.time() - self.state.stream_start_time,
                "current_phase": self.state.stream_phase.value
            },
            "viewer_analytics": {
                "peak_viewers": self.state.viewer_metrics.peak_count,
                "average_viewers": self.state.viewer_metrics.average_count,
                "unique_chatters": len(self.state.viewer_metrics.active_chatters),
                "join_rate": self.state.viewer_metrics.join_rate,
                "chat_rate": self.state.viewer_metrics.chat_rate
            },
            "content_analytics": {
                "total_generated": len(self.state.content_history.generated_content),
                "content_types": dict(self.state.content_history.content_types),
                "average_variety": self.state.content_history.get_variety_score(),
                "generation_rate": self.state.content_history.calculate_generation_rate()
            },
            "conversation_analytics": {
                "topics_discussed": len(set(self.state.conversation_context.recent_topics)),
                "top_keywords": self.state.conversation_context.get_trending_topics(10),
                "average_energy": self.state.conversation_context.conversation_energy,
                "topic_durations": dict(self.state.conversation_context.topic_durations)
            },
            "environment_analytics": {
                "scenes_used": list(self.state.environment_state.scene_duration.keys()),
                "scene_durations": dict(self.state.environment_state.scene_duration),
                "total_changes": len(self.state.environment_state.change_history)
            },
            "performance_analytics": {
                "average_latency": self.state.system_performance.get_average_latency(),
                "error_counts": dict(self.state.system_performance.error_counts),
                "success_rates": dict(self.state.system_performance.success_rates)
            },
            "snapshots": list(self._state_snapshots)
        }


# Utility functions

def calculate_time_of_day_factor() -> float:
    """Calculate activity factor based on time of day"""
    hour = datetime.now().hour
    
    # Peak hours: 7-10 PM
    if 19 <= hour <= 22:
        return 1.2
    # Good hours: 2-7 PM, 10-11 PM
    elif 14 <= hour <= 19 or 22 <= hour <= 23:
        return 1.0
    # Morning/late night: lower activity
    elif hour < 6 or hour > 23:
        return 0.6
    # Default
    else:
        return 0.8


def estimate_speech_duration(text: str, wpm: int = 150) -> float:
    """Estimate speech duration based on text length"""
    words = len(text.split())
    minutes = words / wpm
    return max(1.0, minutes * 60)  # Convert to seconds, minimum 1 second


def extract_keywords(text: str, min_length: int = 4) -> List[str]:
    """Extract meaningful keywords from text"""
    # Simple keyword extraction
    words = text.lower().split()
    
    # Filter out common words
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
        "was", "one", "our", "out", "his", "has", "had", "were", "been", "have",
        "with", "what", "this", "that", "from", "they", "will", "would", "could"
    }
    
    keywords = [
        word.strip(".,!?;:'\"") 
        for word in words 
        if len(word) >= min_length and word not in stop_words and word.isalpha()
    ]
    
    return keywords


def calculate_content_relevance(content: str, context: ConversationContext) -> float:
    """Calculate how relevant content is to current conversation"""
    if not context.recent_topics:
        return 0.5
    
    content_keywords = set(extract_keywords(content))
    context_keywords = set()
    
    # Get keywords from recent topics
    for topic in context.recent_topics:
        context_keywords.update(extract_keywords(str(topic)))
    
    # Calculate overlap
    if not context_keywords:
        return 0.5
        
    overlap = len(content_keywords & context_keywords)
    total = len(context_keywords)
    
    return min(overlap / total if total > 0 else 0.0, 1.0)


# Export all main components
__all__ = [
    'OrchestratorState',
    'StateManager',
    'ConversationContext',
    'EnvironmentState',
    'ContentHistory',
    'ViewerMetrics',
    'SystemPerformance',
    'ActivityLevel',
    'StreamPhase',
    'calculate_time_of_day_factor',
    'estimate_speech_duration',
    'extract_keywords',
    'calculate_content_relevance'
]