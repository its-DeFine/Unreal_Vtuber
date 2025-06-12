from typing import List, Dict
import logging


class MemoryManager:
    """Simple in-memory context store. Replace with database-backed store."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._mem: List[Dict] = []
        logging.info("memory manager connected to %s", db_url)

    def get_recent_context(self) -> Dict:
        return self._mem[-1] if self._mem else {}

    def store_memory(self, item: Dict) -> None:
        self._mem.append(item)
