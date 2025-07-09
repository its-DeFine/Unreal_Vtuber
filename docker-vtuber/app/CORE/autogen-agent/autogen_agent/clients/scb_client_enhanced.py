"""
Enhanced SCB Client with TTL and Categories
Example implementation of suggested improvements
"""

import json
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EnhancedSCBClient:
    """Enhanced SCB client with TTL, categories, and versioning"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize enhanced SCB client"""
        self.url = redis_url
        self._redis = None
        self.enabled = False
        self.version = 2  # SCB protocol version
        
        # State categories for different consumers
        self.CATEGORIES = {
            "s1_display": "scb:s1:display",      # S1 avatar display
            "s2_analysis": "scb:s2:analysis",    # S2 analysis data
            "system_health": "scb:system:health", # System monitoring
            "agent_comm": "scb:agent:comm",      # Agent coordination
            "stimuli": "scb:stimuli:active",     # Active stimuli
        }
        
        # TTL settings (seconds)
        self.TTL_SETTINGS = {
            "s1_display": 60,        # 1 minute for display
            "s2_analysis": 300,      # 5 minutes for analysis
            "system_health": 3600,   # 1 hour for health
            "agent_comm": 120,       # 2 minutes for messages
            "stimuli": 1800,         # 30 minutes for stimuli
        }
        
        self._connect()
    
    def _connect(self):
        """Connect to Redis with enhanced error handling"""
        if not self.url:
            logger.info("🔗 [SCB_ENHANCED] No Redis URL - running in standalone mode")
            return
            
        try:
            import redis
            self._redis = redis.from_url(self.url, decode_responses=True)
            # Test connection
            self._redis.ping()
            self.enabled = True
            logger.info("✅ [SCB_ENHANCED] Connected to Redis with enhancements")
        except Exception as e:
            logger.warning(f"⚠️ [SCB_ENHANCED] Redis connection failed: {e}")
            self.enabled = False
    
    def publish_categorized(self, category: str, data: Dict[str, Any], ttl_override: Optional[int] = None):
        """
        Publish state to specific category with TTL
        
        Args:
            category: One of the defined categories
            data: State data to publish
            ttl_override: Override default TTL in seconds
        """
        if category not in self.CATEGORIES:
            logger.error(f"❌ [SCB_ENHANCED] Unknown category: {category}")
            return
        
        # Add metadata
        enhanced_data = {
            "version": self.version,
            "category": category,
            "timestamp": time.time(),
            "data": data
        }
        
        if not self.enabled or not self._redis:
            logger.info(f"🔗 [SCB_ENHANCED] {category}: {json.dumps(enhanced_data, indent=2)}")
            return
        
        try:
            channel = self.CATEGORIES[category]
            ttl = ttl_override or self.TTL_SETTINGS.get(category, 300)
            
            # Store with TTL
            key = f"{channel}:{int(time.time() * 1000)}"
            self._redis.setex(key, ttl, json.dumps(enhanced_data))
            
            # Also publish for real-time subscribers
            self._redis.publish(channel, json.dumps(enhanced_data))
            
            # Update "latest" pointer
            self._redis.setex(f"{channel}:latest", ttl, json.dumps(enhanced_data))
            
            logger.debug(f"✅ [SCB_ENHANCED] Published to {category} with {ttl}s TTL")
            
        except Exception as e:
            logger.error(f"❌ [SCB_ENHANCED] Publish failed: {e}")
    
    def get_latest(self, category: str) -> Optional[Dict[str, Any]]:
        """Get latest state for a category"""
        if category not in self.CATEGORIES:
            return None
            
        if not self.enabled or not self._redis:
            return None
        
        try:
            channel = self.CATEGORIES[category]
            data = self._redis.get(f"{channel}:latest")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"❌ [SCB_ENHANCED] Get failed: {e}")
        
        return None
    
    def get_recent_states(self, category: str, minutes: int = 5) -> list[Dict[str, Any]]:
        """Get recent states within time window"""
        if category not in self.CATEGORIES or not self._redis:
            return []
        
        try:
            channel = self.CATEGORIES[category]
            cutoff = time.time() - (minutes * 60)
            
            # Get all keys matching pattern
            keys = self._redis.keys(f"{channel}:*")
            states = []
            
            for key in keys:
                if key.endswith(":latest"):
                    continue
                    
                # Extract timestamp from key
                try:
                    timestamp = int(key.split(":")[-1]) / 1000
                    if timestamp > cutoff:
                        data = self._redis.get(key)
                        if data:
                            states.append(json.loads(data))
                except:
                    continue
            
            # Sort by timestamp
            states.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return states
            
        except Exception as e:
            logger.error(f"❌ [SCB_ENHANCED] Get recent failed: {e}")
            return []
    
    def publish_s1_safe(self, display_data: Dict[str, Any]):
        """Publish S1-safe display data (no sensitive info)"""
        # Filter out sensitive data
        safe_data = {
            k: v for k, v in display_data.items()
            if k not in ["api_keys", "internal_state", "passwords"]
        }
        
        self.publish_categorized("s1_display", safe_data)
    
    def publish_s2_analysis(self, analysis_data: Dict[str, Any]):
        """Publish S2 analysis data with full context"""
        self.publish_categorized("s2_analysis", analysis_data)
    
    def publish_stimuli(self, stimuli_id: str, stimuli_data: Dict[str, Any]):
        """Publish active stimuli with extended TTL"""
        enhanced_stimuli = {
            "stimuli_id": stimuli_id,
            "start_time": time.time(),
            **stimuli_data
        }
        self.publish_categorized("stimuli", enhanced_stimuli)
    
    def cleanup_old_states(self, category: str, keep_minutes: int = 60):
        """Clean up old states beyond retention period"""
        if not self._redis:
            return
            
        try:
            channel = self.CATEGORIES.get(category)
            if not channel:
                return
            
            cutoff = time.time() - (keep_minutes * 60)
            keys = self._redis.keys(f"{channel}:*")
            
            deleted = 0
            for key in keys:
                if key.endswith(":latest"):
                    continue
                    
                try:
                    timestamp = int(key.split(":")[-1]) / 1000
                    if timestamp < cutoff:
                        self._redis.delete(key)
                        deleted += 1
                except:
                    continue
            
            if deleted > 0:
                logger.info(f"🧹 [SCB_ENHANCED] Cleaned up {deleted} old states from {category}")
                
        except Exception as e:
            logger.error(f"❌ [SCB_ENHANCED] Cleanup failed: {e}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get Redis memory usage statistics"""
        if not self._redis:
            return {"enabled": False}
        
        try:
            info = self._redis.info("memory")
            return {
                "enabled": True,
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio"),
            }
        except Exception as e:
            logger.error(f"❌ [SCB_ENHANCED] Memory info failed: {e}")
            return {"enabled": False, "error": str(e)}


# Example usage patterns for different agents
class SCBUsageExamples:
    """Examples of how different agents should use enhanced SCB"""
    
    @staticmethod
    def s1_agent_example(scb: EnhancedSCBClient):
        """S1 agents only read safe display data"""
        # S1 can only read from Redis, not write to graph
        display_state = scb.get_latest("s1_display")
        if display_state:
            # Use for avatar display
            return display_state["data"]
        return None
    
    @staticmethod
    def s2_agent_example(scb: EnhancedSCBClient):
        """S2 agents publish analysis and read all categories"""
        # S2 publishes analysis results
        analysis = {
            "market_trend": "bullish",
            "confidence": 0.85,
            "recommendations": ["buy", "hold"]
        }
        scb.publish_s2_analysis(analysis)
        
        # S2 can read from any category
        recent_stimuli = scb.get_recent_states("stimuli", minutes=10)
        return recent_stimuli
    
    @staticmethod
    def system_monitor_example(scb: EnhancedSCBClient):
        """System monitoring and cleanup"""
        # Publish health metrics
        health = {
            "cpu_usage": 45.2,
            "memory_usage": 72.1,
            "active_agents": 5
        }
        scb.publish_categorized("system_health", health)
        
        # Cleanup old states
        for category in scb.CATEGORIES.keys():
            scb.cleanup_old_states(category, keep_minutes=120)
        
        # Check memory usage
        return scb.get_memory_usage()