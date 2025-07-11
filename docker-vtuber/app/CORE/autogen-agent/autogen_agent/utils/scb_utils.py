"""
SCB (Shared Context Blackboard) Utilities
=========================================

Provides utilities for teams to communicate and share insights through SCB channels.
Enables cross-team coordination and knowledge sharing.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class SCBChannel(Enum):
    """Predefined SCB channels for team communication"""
    # General channels
    SYSTEM_BROADCAST = "system_broadcast"
    TEAM_COORDINATION = "team_coordination"
    INSIGHTS_SHARING = "insights_sharing"
    
    # Team-specific channels
    TRADER_INSIGHTS = "trader_insights"
    TRADER_SIGNALS = "trader_signals"
    STREAMER_ANALYTICS = "streamer_analytics"
    STREAMER_CONTENT = "streamer_content"
    TEACHER_KNOWLEDGE = "teacher_knowledge"
    TEACHER_PROGRESS = "teacher_progress"
    DEFAULT_EVOLUTION = "default_evolution"
    
    # Cross-team channels
    PERFORMANCE_METRICS = "performance_metrics"
    GOAL_UPDATES = "goal_updates"
    LEARNING_PATTERNS = "learning_patterns"
    COLLABORATION_REQUESTS = "collaboration_requests"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SCBWriter:
    """
    Utility class for writing to SCB channels.
    Used by teams to publish insights and communicate.
    """
    
    def __init__(self, scb_client=None):
        self.scb_client = scb_client
        self.enabled = scb_client is not None and scb_client.is_enabled()
        
        if self.enabled:
            logger.info("✅ [SCB_UTILS] SCB writer initialized with active client")
        else:
            logger.warning("⚠️ [SCB_UTILS] SCB writer in standalone mode")
    
    async def publish_insight(
        self, 
        channel: str, 
        insight_type: str,
        content: str,
        data: Dict[str, Any] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        tags: List[str] = None
    ) -> bool:
        """
        Publish an insight to an SCB channel
        
        Args:
            channel: Channel to publish to
            insight_type: Type of insight (discovery, pattern, recommendation, etc.)
            content: Human-readable insight description
            data: Structured data associated with the insight
            priority: Message priority
            tags: Optional tags for categorization
        
        Returns:
            Success status
        """
        if not self.enabled:
            logger.debug(f"[SCB_UTILS] Skipping publish - SCB not enabled")
            return False
        
        try:
            message = {
                "type": "insight",
                "insight_type": insight_type,
                "content": content,
                "data": data or {},
                "priority": priority.value,
                "tags": tags or [],
                "timestamp": datetime.now().isoformat(),
                "source": "autonomous_team"
            }
            
            self.scb_client.publish_state(message, channel)
            
            logger.info(f"📤 [SCB_UTILS] Published {insight_type} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to publish insight: {e}")
            return False
    
    async def publish_event(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish an event to an SCB channel
        
        Args:
            channel: Channel to publish to
            event_type: Type of event
            data: Event data
            correlation_id: Optional ID for event correlation
        
        Returns:
            Success status
        """
        if not self.enabled:
            return False
        
        try:
            event = {
                "type": "event",
                "event_type": event_type,
                "data": data,
                "correlation_id": correlation_id,
                "timestamp": datetime.now().isoformat(),
                "source": "autonomous_team"
            }
            
            self.scb_client.publish_state(event, channel)
            
            logger.debug(f"📤 [SCB_UTILS] Published {event_type} event to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to publish event: {e}")
            return False
    
    async def request_collaboration(
        self,
        target_team: str,
        request_type: str,
        context: Dict[str, Any],
        callback_channel: Optional[str] = None
    ) -> str:
        """
        Request collaboration from another team
        
        Args:
            target_team: Team to collaborate with
            request_type: Type of collaboration needed
            context: Request context and data
            callback_channel: Channel for response
        
        Returns:
            Request ID
        """
        if not self.enabled:
            return ""
        
        try:
            request_id = f"collab_{datetime.now().timestamp()}"
            
            request = {
                "type": "collaboration_request",
                "request_id": request_id,
                "target_team": target_team,
                "request_type": request_type,
                "context": context,
                "callback_channel": callback_channel or SCBChannel.COLLABORATION_REQUESTS.value,
                "timestamp": datetime.now().isoformat(),
                "source": "autonomous_team"
            }
            
            self.scb_client.publish_state(
                request, 
                SCBChannel.COLLABORATION_REQUESTS.value
            )
            
            logger.info(f"🤝 [SCB_UTILS] Requested {request_type} collaboration from {target_team}")
            return request_id
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to request collaboration: {e}")
            return ""
    
    async def broadcast_metrics(
        self,
        metrics: Dict[str, Any],
        metric_type: str = "performance"
    ) -> bool:
        """
        Broadcast team metrics to the performance channel
        
        Args:
            metrics: Performance metrics to broadcast
            metric_type: Type of metrics
        
        Returns:
            Success status
        """
        return await self.publish_event(
            SCBChannel.PERFORMANCE_METRICS.value,
            f"{metric_type}_metrics",
            metrics
        )


class SCBReader:
    """
    Utility class for reading from SCB channels.
    Used by teams to consume insights and messages.
    """
    
    def __init__(self, scb_client=None):
        self.scb_client = scb_client
        self.enabled = scb_client is not None and scb_client.is_enabled()
        self.subscriptions: Dict[str, Set[str]] = {}  # team -> channels
        
        if self.enabled:
            logger.info("✅ [SCB_UTILS] SCB reader initialized with active client")
        else:
            logger.warning("⚠️ [SCB_UTILS] SCB reader in standalone mode")
    
    async def get_latest_insights(
        self,
        channel: str,
        limit: int = 10,
        min_priority: MessagePriority = MessagePriority.NORMAL
    ) -> List[Dict[str, Any]]:
        """
        Get latest insights from a channel
        
        Args:
            channel: Channel to read from
            limit: Maximum number of insights
            min_priority: Minimum priority filter
        
        Returns:
            List of insights
        """
        if not self.enabled:
            return []
        
        try:
            # In a real implementation, this would fetch from Redis lists/streams
            # For now, return from current state
            state_key = f"{channel}_insights"
            insights = self.scb_client.get_state(state_key)
            
            if not insights:
                return []
            
            if isinstance(insights, str):
                insights = json.loads(insights)
            
            # Filter by priority
            filtered = [
                i for i in insights 
                if MessagePriority(i.get("priority", "normal")).value >= min_priority.value
            ]
            
            return filtered[:limit]
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to get insights: {e}")
            return []
    
    async def get_team_state(self, team_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current state of a specific team
        
        Args:
            team_name: Name of the team
        
        Returns:
            Team state or None
        """
        if not self.enabled:
            return None
        
        try:
            state = self.scb_client.get_state(f"{team_name}_state")
            
            if state and isinstance(state, str):
                state = json.loads(state)
            
            return state
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to get team state: {e}")
            return None
    
    async def get_collaboration_requests(
        self,
        target_team: Optional[str] = None,
        request_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending collaboration requests
        
        Args:
            target_team: Filter by target team
            request_type: Filter by request type
        
        Returns:
            List of collaboration requests
        """
        if not self.enabled:
            return []
        
        try:
            requests = self.scb_client.get_state("collaboration_requests")
            
            if not requests:
                return []
            
            if isinstance(requests, str):
                requests = json.loads(requests)
            
            # Apply filters
            filtered = requests
            if target_team:
                filtered = [r for r in filtered if r.get("target_team") == target_team]
            if request_type:
                filtered = [r for r in filtered if r.get("request_type") == request_type]
            
            return filtered
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to get collaboration requests: {e}")
            return []
    
    async def subscribe_to_channels(
        self,
        team_name: str,
        channels: List[str]
    ) -> bool:
        """
        Subscribe a team to specific channels
        
        Args:
            team_name: Name of the team
            channels: List of channels to subscribe to
        
        Returns:
            Success status
        """
        if not self.enabled:
            return False
        
        try:
            if team_name not in self.subscriptions:
                self.subscriptions[team_name] = set()
            
            self.subscriptions[team_name].update(channels)
            
            # In a real implementation, this would set up Redis pub/sub
            logger.info(f"✅ [SCB_UTILS] {team_name} subscribed to {len(channels)} channels")
            return True
            
        except Exception as e:
            logger.error(f"❌ [SCB_UTILS] Failed to subscribe: {e}")
            return False


class SCBCoordinator:
    """
    High-level coordinator for SCB-based team communication.
    Manages complex multi-team interactions.
    """
    
    def __init__(self, scb_client=None):
        self.writer = SCBWriter(scb_client)
        self.reader = SCBReader(scb_client)
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
    
    async def coordinate_team_action(
        self,
        initiator_team: str,
        action_type: str,
        participating_teams: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Coordinate a multi-team action
        
        Args:
            initiator_team: Team initiating the action
            action_type: Type of coordinated action
            participating_teams: Teams to participate
            context: Action context
        
        Returns:
            Coordination result
        """
        try:
            coordination_id = f"coord_{datetime.now().timestamp()}"
            
            # Broadcast coordination request
            for team in participating_teams:
                await self.writer.request_collaboration(
                    target_team=team,
                    request_type=f"coordinate_{action_type}",
                    context={
                        "coordination_id": coordination_id,
                        "initiator": initiator_team,
                        "action": action_type,
                        "context": context
                    }
                )
            
            # Track active coordination
            self.active_collaborations[coordination_id] = {
                "initiator": initiator_team,
                "action": action_type,
                "teams": participating_teams,
                "status": "pending",
                "started_at": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "coordination_id": coordination_id,
                "participating_teams": participating_teams
            }
            
        except Exception as e:
            logger.error(f"❌ [SCB_COORD] Failed to coordinate action: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def share_cross_team_insight(
        self,
        source_team: str,
        insight: str,
        relevant_teams: List[str],
        data: Dict[str, Any] = None
    ) -> bool:
        """
        Share an insight across multiple teams
        
        Args:
            source_team: Team generating the insight
            insight: Insight description
            relevant_teams: Teams that should receive the insight
            data: Associated data
        
        Returns:
            Success status
        """
        try:
            # Publish to general insights channel
            await self.writer.publish_insight(
                channel=SCBChannel.INSIGHTS_SHARING.value,
                insight_type="cross_team",
                content=insight,
                data={
                    "source_team": source_team,
                    "relevant_teams": relevant_teams,
                    **(data or {})
                },
                priority=MessagePriority.HIGH
            )
            
            # Also publish to team-specific channels
            for team in relevant_teams:
                channel = self._get_team_channel(team)
                if channel:
                    await self.writer.publish_insight(
                        channel=channel,
                        insight_type="shared_insight",
                        content=f"Insight from {source_team}: {insight}",
                        data=data
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [SCB_COORD] Failed to share insight: {e}")
            return False
    
    def _get_team_channel(self, team_name: str) -> Optional[str]:
        """Get primary channel for a team"""
        channel_map = {
            "trader": SCBChannel.TRADER_INSIGHTS.value,
            "streamer": SCBChannel.STREAMER_ANALYTICS.value,
            "teacher": SCBChannel.TEACHER_KNOWLEDGE.value,
            "default": SCBChannel.DEFAULT_EVOLUTION.value
        }
        return channel_map.get(team_name.lower())


# Convenience functions for common operations
async def publish_team_insight(
    scb_client,
    team_name: str,
    insight: str,
    data: Dict[str, Any] = None,
    priority: MessagePriority = MessagePriority.NORMAL
) -> bool:
    """Convenience function to publish a team insight"""
    writer = SCBWriter(scb_client)
    
    # Determine appropriate channel
    channel_map = {
        "trader": SCBChannel.TRADER_INSIGHTS,
        "streamer": SCBChannel.STREAMER_ANALYTICS,
        "teacher": SCBChannel.TEACHER_KNOWLEDGE,
        "default": SCBChannel.DEFAULT_EVOLUTION
    }
    
    channel = channel_map.get(team_name.lower(), SCBChannel.INSIGHTS_SHARING)
    
    return await writer.publish_insight(
        channel=channel.value,
        insight_type="team_insight",
        content=insight,
        data=data,
        priority=priority
    )


async def request_team_collaboration(
    scb_client,
    from_team: str,
    to_team: str,
    collaboration_type: str,
    context: Dict[str, Any]
) -> str:
    """Convenience function to request collaboration"""
    writer = SCBWriter(scb_client)
    
    return await writer.request_collaboration(
        target_team=to_team,
        request_type=collaboration_type,
        context={
            "requesting_team": from_team,
            **context
        }
    )


async def get_team_insights(
    scb_client,
    team_name: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Convenience function to get team insights"""
    reader = SCBReader(scb_client)
    
    # Get from team-specific channel
    channel_map = {
        "trader": SCBChannel.TRADER_INSIGHTS,
        "streamer": SCBChannel.STREAMER_ANALYTICS,
        "teacher": SCBChannel.TEACHER_KNOWLEDGE,
        "default": SCBChannel.DEFAULT_EVOLUTION
    }
    
    channel = channel_map.get(team_name.lower(), SCBChannel.INSIGHTS_SHARING)
    
    return await reader.get_latest_insights(channel.value, limit)