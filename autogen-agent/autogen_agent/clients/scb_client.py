import logging
import json
from typing import Dict

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class SCBClient:
    def __init__(self, url: str):
        self.url = url
        if redis:
            self._redis = redis.from_url(url)
        else:  # pragma: no cover
            self._redis = None
        logging.info("SCB client connected to %s", url)

    def publish_state(self, data: Dict) -> None:
        if self._redis:
            self._redis.publish("state", json.dumps(data))
