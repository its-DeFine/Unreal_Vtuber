from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, Iterable, List

from .base import AnalyticsBase


class MetabaseAnalytics(AnalyticsBase):
    """Analytics provider that communicates with a Metabase server via its REST API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self._session_id: str | None = None
        self._login()

    # ------------------------------------------------------------------
    # Internal helpers
    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data: bytes | None = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if self._session_id:
            headers['X-Metabase-Session'] = self._session_id
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            if body:
                return json.loads(body)
            return None

    def _login(self) -> None:
        resp = self._request(
            'POST',
            '/api/session',
            {'username': self.username, 'password': self.password},
        )
        self._session_id = resp['id']

    # ------------------------------------------------------------------
    # Public API
    def create_board(self, name: str) -> str:
        resp = self._request('POST', '/api/collection', {'name': name})
        return str(resp['id'])

    def import_data(self, board_id: str, data: Iterable[Dict[str, Any]]) -> None:
        self._request('POST', '/api/dataset', {'board_id': board_id, 'rows': list(data)})

    def get_board(self, board_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/api/collection/{board_id}')

    def list_boards(self) -> Iterable[Dict[str, Any]]:
        return self._request('GET', '/api/collection')

    # Convenience accessor similar to InMemoryAnalytics
    def get_board_data(self, board_id: str) -> List[Dict[str, Any]]:
        board = self.get_board(board_id)
        return board.get('rows', [])
