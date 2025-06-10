import logging
import json
from typing import Dict

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class SCBClient:
    def __init__(self, url: str = None):
        self.url = url
        self.enabled = bool(url)
        
        if self.enabled and redis:
            try:
                self._redis = redis.from_url(url)
                logging.info("🔗 [SCB] SCB client connected to %s", url)
            except Exception as e:
                logging.warning(f"⚠️ [SCB] Failed to connect to Redis: {e}")
                self._redis = None
                self.enabled = False
        else:
            self._redis = None
            logging.info("🔗 [SCB] SCB client disabled - standalone mode")

    def publish_state(self, data: Dict) -> None:
        if not self.enabled or not self._redis:
            logging.info("🔗 [SCB] State (standalone): %s", json.dumps(data, indent=2))
            return
            
        try:
            self._redis.publish("state", json.dumps(data))
            logging.debug("🔗 [SCB] State published to Redis")
        except Exception as e:
            logging.warning(f"⚠️ [SCB] Failed to publish state: {e}")
            logging.info("🔗 [SCB] State (fallback): %s", json.dumps(data, indent=2))
