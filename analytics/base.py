from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable


class AnalyticsBase(ABC):
    """Abstract interface for analytics providers."""

    @abstractmethod
    def create_board(self, name: str) -> str:
        """Create a new analytics board and return its identifier."""
        raise NotImplementedError

    @abstractmethod
    def import_data(self, board_id: str, data: Iterable[Dict[str, Any]]) -> None:
        """Import a collection of records into the given board."""
        raise NotImplementedError

    @abstractmethod
    def get_board(self, board_id: str) -> Dict[str, Any]:
        """Return metadata for the specified board."""
        raise NotImplementedError

    @abstractmethod
    def list_boards(self) -> Iterable[Dict[str, Any]]:
        """Return iterable of available boards."""
        raise NotImplementedError
