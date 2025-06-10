import logging
from typing import Dict

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class VTuberClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        logging.info("VTuber client using %s", endpoint)

    def post_message(self, message: str) -> None:
        if not message:
            return
        url = f"{self.endpoint}/message"
        if requests:
            try:
                requests.post(url, json={"message": message}, timeout=5)
            except Exception as exc:  # pragma: no cover
                logging.error("failed to post message: %s", exc)
