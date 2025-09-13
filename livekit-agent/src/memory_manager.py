"""
Session Memory Manager for LiveKit VTuber Agent
Handles temporary session memory and consolidation to Central Manager
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import httpx
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class SessionMemoryManager:
    """
    Manages session memory with automatic consolidation
    """
    
    def __init__(
        self,
        agent_name: str,
        redis_url: str = "redis://redis_scb:6379",
        central_manager_url: str = "http://central-manager:8000",
        consolidation_interval: int = 3600  # 1 hour
    ):
        self.agent_name = agent_name
        self.redis_url = redis_url
        self.central_manager_url = central_manager_url
        self.consolidation_interval = consolidation_interval
        
        self.redis_client: Optional[redis.Redis] = None
        self.session_id: Optional[str] = None
        self.session_start: Optional[datetime] = None
        self.interaction_count = 0
        self.consolidation_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for session memory")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fall back to in-memory storage
            self.redis_client = None
    
    async def start_session(self, room_name: str) -> None:
        """Start a new session"""
        
        self.session_id = f"{self.agent_name}_{room_name}_{datetime.now().isoformat()}"
        self.session_start = datetime.now()
        self.interaction_count = 0
        
        logger.info(f"Started session: {self.session_id}")
        
        # Store session metadata
        if self.redis_client:
            await self.redis_client.hset(
                f"session:{self.session_id}",
                mapping={
                    "agent": self.agent_name,
                    "room": room_name,
                    "start_time": self.session_start.isoformat(),
                    "status": "active"
                }
            )
            
            # Set expiry (2 hours to be safe)
            await self.redis_client.expire(f"session:{self.session_id}", 7200)
        
        # Start consolidation timer
        self.consolidation_task = asyncio.create_task(
            self._consolidation_timer()
        )
    
    async def add_interaction(
        self,
        user_text: Optional[str] = None,
        agent_text: Optional[str] = None,
        platform: str = "voice",
        user: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> None:
        """Add an interaction to session memory"""
        
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "user": user,
            "user_text": user_text,
            "agent_text": agent_text,
            "emotion": emotion
        }
        
        self.interaction_count += 1
        
        # Store in Redis
        if self.redis_client and self.session_id:
            await self.redis_client.lpush(
                f"session:{self.session_id}:interactions",
                json.dumps(interaction)
            )
            
            # Update interaction count
            await self.redis_client.hincrby(
                f"session:{self.session_id}",
                "interaction_count",
                1
            )
            
            # Check if we should consolidate
            if self.interaction_count >= 50:
                await self.consolidate()
    
    async def get_recent_context(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions for context"""
        
        if not self.redis_client or not self.session_id:
            return []
        
        try:
            interactions = await self.redis_client.lrange(
                f"session:{self.session_id}:interactions",
                0,
                limit - 1
            )
            
            return [json.loads(i) for i in interactions]
            
        except Exception as e:
            logger.error(f"Failed to get recent context: {e}")
            return []
    
    async def consolidate(self) -> Dict[str, Any]:
        """Consolidate session memory and send to Central Manager"""
        
        logger.info(f"Consolidating session {self.session_id}")
        
        if not self.redis_client or not self.session_id:
            return {}
        
        try:
            # Get all interactions
            interactions = await self.redis_client.lrange(
                f"session:{self.session_id}:interactions",
                0,
                -1
            )
            
            interactions = [json.loads(i) for i in interactions]
            
            # Analyze session
            summary = self._analyze_session(interactions)
            
            # Send to Central Manager
            await self._send_to_manager(summary)
            
            # Clear session memory
            await self.redis_client.delete(f"session:{self.session_id}:interactions")
            self.interaction_count = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to consolidate session: {e}")
            return {}
    
    def _analyze_session(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Analyze session interactions"""
        
        if not interactions:
            return {}
        
        # Count platforms
        platform_counts = {}
        emotion_counts = {}
        user_messages = []
        agent_messages = []
        unique_users = set()
        
        for interaction in interactions:
            platform = interaction.get("platform", "unknown")
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            if interaction.get("emotion"):
                emotion = interaction["emotion"]
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            if interaction.get("user"):
                unique_users.add(interaction["user"])
            
            if interaction.get("user_text"):
                user_messages.append(interaction["user_text"])
            
            if interaction.get("agent_text"):
                agent_messages.append(interaction["agent_text"])
        
        # Calculate metrics
        duration = (datetime.now() - self.session_start).total_seconds() if self.session_start else 0
        
        summary = {
            "session_id": self.session_id,
            "agent": self.agent_name,
            "duration_seconds": duration,
            "interaction_count": len(interactions),
            "unique_users": len(unique_users),
            "platform_distribution": platform_counts,
            "emotion_distribution": emotion_counts,
            "sample_user_messages": user_messages[:10],
            "sample_agent_messages": agent_messages[:10],
            "timestamp": datetime.now().isoformat()
        }
        
        # Add key moments (high engagement, emotional peaks, etc.)
        key_moments = self._extract_key_moments(interactions)
        if key_moments:
            summary["key_moments"] = key_moments
        
        return summary
    
    def _extract_key_moments(self, interactions: List[Dict]) -> List[Dict]:
        """Extract key moments from the session"""
        
        key_moments = []
        
        # Find emotional peaks
        excited_moments = [
            i for i in interactions
            if i.get("emotion") in ["excited", "love", "surprised"]
        ]
        
        if excited_moments:
            key_moments.append({
                "type": "emotional_peak",
                "count": len(excited_moments),
                "samples": excited_moments[:3]
            })
        
        # Find questions
        questions = [
            i for i in interactions
            if i.get("user_text") and "?" in i["user_text"]
        ]
        
        if questions:
            key_moments.append({
                "type": "questions_asked",
                "count": len(questions),
                "samples": questions[:3]
            })
        
        return key_moments
    
    async def _send_to_manager(self, summary: Dict[str, Any]) -> None:
        """Send consolidated summary to Central Manager"""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.central_manager_url}/api/v1/memory/consolidate",
                    json={
                        "agent_id": self.agent_name,
                        "session_summary": summary
                    }
                )
                
                if response.status_code == 200:
                    logger.info("Successfully sent session summary to Central Manager")
                else:
                    logger.warning(f"Central Manager returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to send summary to Central Manager: {e}")
    
    async def _consolidation_timer(self) -> None:
        """Timer for automatic consolidation"""
        
        try:
            await asyncio.sleep(self.consolidation_interval)
            await self.consolidate()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in consolidation timer: {e}")
    
    async def end_session(self) -> Dict[str, Any]:
        """End the session and return final summary"""
        
        # Cancel consolidation timer
        if self.consolidation_task:
            self.consolidation_task.cancel()
        
        # Final consolidation
        summary = await self.consolidate()
        
        # Mark session as ended
        if self.redis_client and self.session_id:
            await self.redis_client.hset(
                f"session:{self.session_id}",
                "status",
                "ended"
            )
        
        logger.info(f"Ended session: {self.session_id}")
        
        return summary