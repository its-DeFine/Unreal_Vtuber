"""Orchestrator registry to track registrations and top-100 eligibility."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

from web3 import Web3

from .config import PaymentSettings
from .onchain import fetch_top_entries
from .ledger import Ledger
from .orchestrators import fetch_orchestrator_addresses

logger = logging.getLogger(__name__)


@dataclass
class RegistrationResult:
    orchestrator_id: str
    first_registration: bool
    has_active_payments: bool
    is_top_100: bool
    registration_count: int
    address: str


class Registry:
    """Persists orchestrator registration metadata and eligibility flags."""

    def __init__(
        self,
        path: Path,
        settings: PaymentSettings,
        ledger: Ledger,
        web3: Optional[Web3] = None,
    ) -> None:
        self.path = path
        self.settings = settings
        self.ledger = ledger
        self.web3 = web3
        self._lock = threading.RLock()
        self._records: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._records = {}
            return
        with self.path.open("r", encoding="utf-8") as handle:
            self._records = json.load(handle)

    def _persist(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(self._records, handle, indent=2)
        tmp_path.replace(self.path)

    # ------------------------------------------------------------------
    # Top-100 utilities
    # ------------------------------------------------------------------
    def _fetch_top_addresses(self) -> Sequence[str]:
        address = self.settings.top_contract_address
        if not address:
            return []
        if not self.web3:
            logger.warning("Top-100 check skipped: Web3 provider unavailable")
            return []

        abi = self._load_contract_abi()
        if not abi:
            logger.warning("Top-100 check skipped: contract ABI missing")
            return []

        try:
            raw_entries = fetch_top_entries(
                self.web3,
                contract_address=address,
                abi=abi,
                function_name=self.settings.top_contract_function,
                limit=100,
            )
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to fetch top orchestrators: %s", exc)
            return []

        return self._normalize_top_entries(raw_entries)

    def _load_contract_abi(self) -> Optional[Iterable[dict[str, Any]]]:
        if self.settings.top_contract_abi_json:
            try:
                return json.loads(self.settings.top_contract_abi_json)
            except json.JSONDecodeError as exc:
                logger.error("Failed to decode TOP_CONTRACT_ABI_JSON: %s", exc)
                return None
        path = self.settings.top_contract_abi_path
        if not path:
            return None
        try:
            with Path(path).expanduser().open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            logger.error("Contract ABI file not found: %s", path)
        except json.JSONDecodeError as exc:
            logger.error("Contract ABI file invalid JSON (%s): %s", path, exc)
        return None

    @staticmethod
    def _normalize_top_entries(raw: Any) -> Sequence[str]:
        if isinstance(raw, (list, tuple)):
            # Flatten list of addresses or structs
            addresses: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    addresses.append(item.lower())
                elif isinstance(item, (list, tuple)) and item:
                    first = item[0]
                    if isinstance(first, str):
                        addresses.append(first.lower())
                elif isinstance(item, dict):
                    for key in ("address", "addr", "orchestrator"):  # common field names
                        value = item.get(key)
                        if isinstance(value, str):
                            addresses.append(value.lower())
                            break
            return addresses
        if isinstance(raw, dict):
            # Possibly mapping of ranks -> addresses
            return [str(value).lower() for value in raw.values()]
        if isinstance(raw, str):
            return [raw.lower()]
        return []

    # ------------------------------------------------------------------
    # Registry logic
    # ------------------------------------------------------------------
    def register(
        self,
        orchestrator_id: str,
        address: str,
    ) -> RegistrationResult:
        now = datetime.now(timezone.utc).isoformat()
        address_lower = address.lower()

        with self._lock:
            record = self._records.get(orchestrator_id)
            first_registration = record is None
            registration_count = 1
            if record:
                registration_count = record.get("registration_count", 0) + 1

            balance = self.ledger.get_balance(orchestrator_id)
            has_active_payments = balance > Decimal("0")

            top_addresses = self._fetch_top_addresses()
            if not top_addresses:
                top_addresses = fetch_orchestrator_addresses(limit=100)
            top_address_set = {
                addr.lower() for addr in top_addresses if isinstance(addr, str)
            }
            # If no contract source configured, fall back to allowing payments.
            is_top_100 = (
                address_lower in top_address_set if top_address_set else True
            )

            updated_record = {
                "orchestrator_id": orchestrator_id,
                "address": address,
                "first_seen": record.get("first_seen") if record else now,
                "last_seen": now,
                "registration_count": registration_count,
                "has_active_payments": has_active_payments,
                "is_top_100": is_top_100,
                "eligible_for_payments": is_top_100,
            }

            self._records[orchestrator_id] = updated_record
            self._persist()

        return RegistrationResult(
            orchestrator_id=orchestrator_id,
            first_registration=first_registration,
            has_active_payments=has_active_payments,
            is_top_100=is_top_100,
            registration_count=registration_count,
            address=address,
        )

    def is_eligible(self, orchestrator_id: str) -> bool:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return False
            return bool(record.get("eligible_for_payments", False))

    def get_record(self, orchestrator_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if record:
                return dict(record)
            return None

    def all_records(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return json.loads(json.dumps(self._records))
