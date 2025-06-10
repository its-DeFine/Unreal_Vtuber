import logging
from typing import Dict

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class VTuberClient:
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint.rstrip("/") if endpoint else None
        self.enabled = bool(endpoint)
        
        if self.enabled:
            logging.info("🎭 [VTUBER] VTuber client using %s", endpoint)
        else:
            logging.info("🎭 [VTUBER] VTuber client disabled - standalone mode")

    def post_message(self, message: str) -> None:
        if not message:
            return
            
        if not self.enabled:
            logging.info("🎭 [VTUBER] Message (standalone): %s", message[:100] + "..." if len(message) > 100 else message)
            return
            
        url = f"{self.endpoint}/message"
        if requests:
            try:
                requests.post(url, json={"message": message}, timeout=5)
                logging.info("🎭 [VTUBER] Message sent to external service")
            except Exception as exc:  # pragma: no cover
                logging.warning("⚠️ [VTUBER] Failed to post message to external service: %s", exc)
                logging.info("🎭 [VTUBER] Message (fallback): %s", message[:100] + "..." if len(message) > 100 else message)
