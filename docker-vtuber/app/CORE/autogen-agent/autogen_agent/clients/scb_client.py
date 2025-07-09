import logging
import json
import os
from typing import Dict, List

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class SCBClient:
    def __init__(self, url: str = None):
        self.url = url
        self.enabled = bool(url)
        
        # 🔗 NEW: AgentNet activation state (default false)
        self.agentnet_enabled = os.getenv("AGENTNET_ENABLED", "false").lower() == "true"
        
        if self.enabled and redis and self.agentnet_enabled:
            try:
                self._redis = redis.from_url(url)
                logging.info("🔗 [SCB] SCB client connected to %s (AgentNet enabled)", url)
            except Exception as e:
                logging.warning(f"⚠️ [SCB] Failed to connect to Redis: {e}")
                self._redis = None
                self.enabled = False
        else:
            self._redis = None
            if not self.agentnet_enabled:
                logging.info("🔗 [SCB] SCB client disabled - AgentNet not enabled")
            else:
                logging.info("🔗 [SCB] SCB client disabled - standalone mode")

    def enable_agentnet(self) -> None:
        """🔗 Enable AgentNet for SCB communication"""
        self.agentnet_enabled = True
        logging.info("🔗 [SCB] AgentNet enabled - SCB state will now be published")
        
        # Try to reconnect to Redis if URL available
        if self.url and redis and not self._redis:
            try:
                self._redis = redis.from_url(self.url)
                self.enabled = True
                logging.info("🔗 [SCB] Reconnected to Redis at %s", self.url)
            except Exception as e:
                logging.warning(f"⚠️ [SCB] Failed to reconnect to Redis: {e}")

    def disable_agentnet(self) -> None:
        """🔗 Disable AgentNet to stop SCB communication"""
        self.agentnet_enabled = False
        logging.info("🔗 [SCB] AgentNet disabled - SCB state will be logged only")

    def is_agentnet_enabled(self) -> bool:
        """🔗 Check if AgentNet is currently enabled"""
        return self.agentnet_enabled

    def is_enabled(self) -> bool:
        """Check if SCB client is enabled and connected"""
        return self.enabled and self._redis is not None

    def publish_state(self, data: Dict, force_publish: bool = False) -> None:
        """
        Publish state to SCB only if AgentNet is enabled or forced
        
        Args:
            data: State data to publish
            force_publish: If True, bypass AgentNet check (for critical states)
        """
        # 🚫 Check AgentNet activation first
        if not force_publish and not self.agentnet_enabled:
            logging.debug("🚫 [SCB] State blocked - AgentNet not enabled")
            return
            
        if not self.enabled or not self._redis:
            agentnet_status = "enabled" if self.agentnet_enabled or force_publish else "disabled"
            logging.info("🔗 [SCB] State (standalone, AgentNet %s): %s", 
                        agentnet_status, json.dumps(data, indent=2))
            return
            
        try:
            self._redis.publish("state", json.dumps(data))
            logging.debug("🔗 [SCB] State published to Redis")
        except Exception as e:
            logging.warning(f"⚠️ [SCB] Failed to publish state: {e}")
            logging.info("🔗 [SCB] State (fallback): %s", json.dumps(data, indent=2))

    def get_status(self) -> Dict[str, any]:
        """🔗 Get SCB client status"""
        return {
            "enabled": self.enabled,
            "agentnet_enabled": self.agentnet_enabled,
            "redis_connected": bool(self._redis),
            "url": self.url
        }

    def get_state(self, key: str) -> any:
        """Get state value from SCB"""
        if not self.enabled or not self._redis:
            return None
        
        try:
            value = self._redis.get(key)
            if value and isinstance(value, bytes):
                try:
                    return json.loads(value.decode('utf-8'))
                except:
                    return value.decode('utf-8')
            return value
        except Exception as e:
            logging.error(f"❌ [SCB] Failed to get state for {key}: {e}")
            return None

    def set_state(self, key: str, value: any, ttl: int = 3600) -> bool:
        """Set state value in SCB with TTL"""
        if not self.enabled or not self._redis:
            return False
        
        try:
            if isinstance(value, dict):
                value = json.dumps(value)
            
            self._redis.setex(key, ttl, value)
            return True
        except Exception as e:
            logging.error(f"❌ [SCB] Failed to set state for {key}: {e}")
            return False

    def get_keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern"""
        if not self.enabled or not self._redis:
            return []
        
        try:
            keys = self._redis.keys(pattern)
            return [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logging.error(f"❌ [SCB] Failed to get keys for pattern {pattern}: {e}")
            return []
