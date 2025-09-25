"""Simple JSON-backed ledger for orchestrator balances."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Dict
import threading


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.balances: Dict[str, Decimal] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.balances = {}
            return
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self.balances = {key: Decimal(str(value)) for key, value in raw.items()}

    def _persist(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        data = {key: str(value) for key, value in self.balances.items()}
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        tmp_path.replace(self.path)

    def credit(self, orchestrator_id: str, amount: Decimal) -> Decimal:
        with self._lock:
            current = self.balances.get(orchestrator_id, Decimal("0"))
            new_balance = current + amount
            self.balances[orchestrator_id] = new_balance
            self._persist()
            return new_balance

    def set_balance(self, orchestrator_id: str, amount: Decimal) -> None:
        with self._lock:
            self.balances[orchestrator_id] = amount
            self._persist()

    def get_balance(self, orchestrator_id: str) -> Decimal:
        with self._lock:
            return self.balances.get(orchestrator_id, Decimal("0"))

    def as_dict(self) -> Dict[str, str]:
        with self._lock:
            return {key: str(value) for key, value in self.balances.items()}
