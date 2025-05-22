from __future__ import annotations

from typing import Any, Dict, Iterable, List
import itertools

from .base import AnalyticsBase


class InMemoryAnalytics(AnalyticsBase):
    """Simple in-memory analytics provider used for testing."""

    def __init__(self) -> None:
        self._boards: Dict[str, Dict[str, Any]] = {}
        self._data: Dict[str, List[Dict[str, Any]]] = {}
        self._id_counter = itertools.count(1)

    def create_board(self, name: str) -> str:
        board_id = f"board-{next(self._id_counter)}"
        self._boards[board_id] = {"id": board_id, "name": name}
        self._data[board_id] = []
        return board_id

    def import_data(self, board_id: str, data: Iterable[Dict[str, Any]]) -> None:
        if board_id not in self._boards:
            raise KeyError(f"Unknown board_id {board_id}")
        self._data[board_id].extend(list(data))

    def get_board(self, board_id: str) -> Dict[str, Any]:
        return self._boards[board_id]

    def list_boards(self) -> Iterable[Dict[str, Any]]:
        return list(self._boards.values())

    def get_board_data(self, board_id: str) -> List[Dict[str, Any]]:
        return list(self._data.get(board_id, []))
