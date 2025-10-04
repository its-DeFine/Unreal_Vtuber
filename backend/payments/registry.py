"""Orchestrator registry to track registrations and eligibility."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from web3 import Web3

from .config import PaymentSettings
from .ledger import Ledger
from .orchestrators import fetch_orchestrator_addresses, fetch_top_orchestrators_onchain

logger = logging.getLogger(__name__)


class RegistryError(Exception):
    """Raised when a registration request cannot be completed."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class RegistrationResult:
    orchestrator_id: str
    address: str
    first_registration: bool
    registration_count: int
    is_top_100: bool
    eligible_for_payments: bool
    denylisted: bool
    has_active_payments: bool
    cooldown_expires_at: Optional[str]
    message: str


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
        self.audit_log_path: Path = getattr(
            settings,
            "audit_log_path",
            Path("/app/data/audit/registry.log"),
        )
        self._lock = threading.RLock()
        self._records: Dict[str, Dict[str, Any]] = {}
        self._address_index: Dict[str, str] = {}
        denylist_raw = getattr(settings, "address_denylist", []) or []
        self._denylist_addresses: set[str] = {
            address.lower() for address in denylist_raw if isinstance(address, str)
        }
        self._load()
        self._top_cache_addresses: set[str] = set()
        self._top_cache_timestamp: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._records = {}
            self._address_index = {}
            return

        with self.path.open("r", encoding="utf-8") as handle:
            raw_records = json.load(handle)

        now_iso = datetime.now(timezone.utc).isoformat()
        records: Dict[str, Dict[str, Any]] = {}
        address_index: Dict[str, str] = {}

        for orchestrator_id, raw in raw_records.items():
            if not isinstance(raw, dict):
                continue
            record = self._normalize_record(orchestrator_id, raw, now_iso)
            address = record.get("address")
            denylisted = bool(record.get("denylisted", False))
            if isinstance(address, str):
                address_lower = address.lower()
                if address_lower in self._denylist_addresses:
                    denylisted = True
                address_index[address_lower] = orchestrator_id
            if denylisted:
                record["denylisted"] = True
                record["eligible_for_payments"] = False
            records[orchestrator_id] = record

        self._records = records
        self._address_index = address_index
        self._persist()

    def _persist(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(self._records, handle, indent=2)
        tmp_path.replace(self.path)

    def _write_audit_event(
        self,
        event: str,
        orchestrator_id: str,
        payload: Dict[str, Any],
    ) -> None:
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "orchestrator_id": orchestrator_id,
                **payload,
            }
            with self.audit_log_path.open("a", encoding="utf-8") as handle:
                json.dump(entry, handle, separators=(",", ":"))
                handle.write("\n")
        except Exception as exc:  # pragma: no cover - audit logging best effort
            logger.error("Failed to append audit log for %s: %s", event, exc)

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_record(
        orchestrator_id: str,
        record: Dict[str, Any],
        now_iso: str,
    ) -> Dict[str, Any]:
        normalized = dict(record)
        normalized.setdefault("orchestrator_id", orchestrator_id)
        normalized.setdefault("address", record.get("address"))
        normalized.setdefault("capability", record.get("capability"))
        normalized.setdefault("contact_email", record.get("contact_email"))
        normalized.setdefault("host_public_ip", record.get("host_public_ip"))
        normalized.setdefault("host_name", record.get("host_name"))
        normalized.setdefault("last_seen_ip", record.get("last_seen_ip"))
        normalized.setdefault("health_url", record.get("health_url"))
        normalized.setdefault("health_timeout", record.get("health_timeout"))
        normalized.setdefault("monitored_services", record.get("monitored_services"))
        normalized.setdefault("min_service_uptime", record.get("min_service_uptime"))
        normalized.setdefault("first_seen", record.get("first_seen") or now_iso)
        normalized.setdefault("last_seen", record.get("last_seen") or now_iso)
        normalized.setdefault("registration_count", int(record.get("registration_count", 0)))
        normalized.setdefault("is_top_100", bool(record.get("is_top_100", False)))
        normalized.setdefault("eligible_for_payments", bool(record.get("eligible_for_payments", False)))
        normalized.setdefault("denylisted", bool(record.get("denylisted", False)))
        normalized.setdefault("cooldown_expires_at", record.get("cooldown_expires_at"))
        normalized.setdefault("last_missed_all_services", record.get("last_missed_all_services"))
        normalized.setdefault("last_cooldown_started_at", record.get("last_cooldown_started_at"))
        normalized.setdefault("last_cooldown_cleared_at", record.get("last_cooldown_cleared_at"))
        normalized.setdefault("last_healthy_at", record.get("last_healthy_at"))
        return normalized

    # ------------------------------------------------------------------
    # Top-100 utilities
    # ------------------------------------------------------------------
    def _fetch_top_addresses(self) -> Sequence[str]:
        if not self.settings.top_contract_address:
            return []
        if not self.web3:
            logger.warning("Top-100 check skipped: Web3 provider unavailable")
            return []

        return fetch_top_orchestrators_onchain(
            self.web3,
            self.settings.top_contract_address,
            limit=100,
        )

    def _resolve_top_set(self) -> set[str]:
        now = datetime.now(timezone.utc)
        if (
            self._top_cache_addresses
            and self._top_cache_timestamp
            and (now - self._top_cache_timestamp).total_seconds()
            < self.settings.top_cache_ttl_seconds
        ):
            return set(self._top_cache_addresses)

        addresses = self._fetch_top_addresses()
        if addresses:
            normalized = {addr.lower() for addr in addresses if isinstance(addr, str)}
            if normalized:
                self._top_cache_addresses = normalized
                self._top_cache_timestamp = now
                return normalized

        fallback = fetch_orchestrator_addresses(limit=100)
        if fallback:
            normalized = {addr.lower() for addr in fallback if isinstance(addr, str)}
            if normalized:
                self._top_cache_addresses = normalized
                self._top_cache_timestamp = now
                return normalized

        if self._top_cache_addresses:
            logger.warning(
                "Using stale top orchestrator cache after fetch failure"
            )
            return set(self._top_cache_addresses)

        raise RegistryError("Unable to validate orchestrator rank at this time", status_code=503)

    # ------------------------------------------------------------------
    # Registry logic
    # ------------------------------------------------------------------
    def register(
        self,
        orchestrator_id: str,
        address: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        skip_rank_validation: bool = False,
    ) -> RegistrationResult:
        metadata = metadata or {}
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        address_lower = address.lower()

        with self._lock:
            record = self._records.get(orchestrator_id)
            first_registration = record is None

            if address_lower in self._denylist_addresses:
                if record is not None:
                    record["denylisted"] = True
                    record["eligible_for_payments"] = False
                    record["last_seen"] = now_iso
                    self._records[orchestrator_id] = record
                    self._persist()
                self._write_audit_event(
                    "register_denied",
                    orchestrator_id,
                    {
                        "address": address,
                        "reason": "denylisted",
                    },
                )
                raise RegistryError(
                    "Address is denylisted and cannot register",
                    status_code=403,
                )

            if not skip_rank_validation:
                top_set = self._resolve_top_set()
                if address_lower not in top_set:
                    raise RegistryError(
                        "Address is not part of the current top orchestrators",
                        status_code=403,
                    )
                is_top_member = True
            else:
                if record is not None:
                    is_top_member = bool(record.get("is_top_100", True))
                else:
                    is_top_member = bool(metadata.get("is_top_100", True))

            existing_id = self._address_index.get(address_lower)
            if existing_id and existing_id != orchestrator_id:
                raise RegistryError(
                    "Address already registered to a different orchestrator",
                    status_code=409,
                )

            if record is None:
                record = {
                    "orchestrator_id": orchestrator_id,
                    "address": address,
                    "first_seen": now_iso,
                    "registration_count": 0,
                    "eligible_for_payments": True,
                    "denylisted": False,
                }

            previous_address = record.get("address")
            if previous_address and previous_address.lower() != address_lower:
                raise RegistryError(
                    "Existing orchestrator attempted to change address; this is not allowed",
                    status_code=409,
                )

            registration_count = int(record.get("registration_count", 0)) + 1
            balance = self.ledger.get_balance(orchestrator_id)
            has_active_payments = balance > Decimal("0")

            monitored_services = metadata.get("monitored_services")
            if monitored_services:
                monitored_services = list(monitored_services)
            health_timeout = metadata.get("health_timeout")
            if health_timeout is not None:
                try:
                    health_timeout = float(health_timeout)
                except (TypeError, ValueError):
                    health_timeout = record.get("health_timeout")
            min_service_uptime = metadata.get("min_service_uptime")
            if min_service_uptime is not None:
                try:
                    min_service_uptime = float(min_service_uptime)
                except (TypeError, ValueError):
                    min_service_uptime = record.get("min_service_uptime")

            record.update(
                {
                    "address": address,
                    "capability": metadata.get("capability") or record.get("capability"),
                    "contact_email": metadata.get("contact_email") or record.get("contact_email"),
                    "host_public_ip": metadata.get("host_public_ip") or record.get("host_public_ip"),
                    "host_name": metadata.get("host_name") or record.get("host_name"),
                    "last_seen_ip": metadata.get("request_ip")
                    or metadata.get("host_public_ip")
                    or record.get("last_seen_ip"),
                    "last_seen": now_iso,
                    "registration_count": registration_count,
                    "is_top_100": is_top_member,
                    "health_url": metadata.get("health_url")
                    or record.get("health_url"),
                    "health_timeout": health_timeout
                    if health_timeout is not None
                    else record.get("health_timeout"),
                    "monitored_services": monitored_services
                    or record.get("monitored_services"),
                    "min_service_uptime": min_service_uptime
                    if min_service_uptime is not None
                    else record.get("min_service_uptime"),
                }
            )

            cooldown_active = self._refresh_cooldown_state(record, now_dt)
            denylisted_flag = bool(record.get("denylisted", False))
            if denylisted_flag:
                record["eligible_for_payments"] = False
            else:
                record["eligible_for_payments"] = (
                    False if cooldown_active else bool(record.get("is_top_100", False))
                )

            if metadata.get("services_healthy"):
                record["last_healthy_at"] = now_iso

            self._records[orchestrator_id] = record
            self._address_index[address_lower] = orchestrator_id
            self._persist()

        self._write_audit_event(
            "register",
            orchestrator_id,
            {
                "address": address,
                "first_registration": first_registration,
                "registration_count": registration_count,
                "is_top_100": is_top_member,
                "eligible_for_payments": not denylisted_flag and not cooldown_active and is_top_member,
                "denylisted": denylisted_flag,
            },
        )

        message = "Registered orchestrator" if first_registration else "Registration refreshed"
        if denylisted_flag:
            message = "Registration blocked (address denylisted)"
        elif cooldown_active:
            message = f"{message} (cooldown active)"

        is_top_flag = bool(record.get("is_top_100", False))
        eligible_flag = not denylisted_flag and not cooldown_active and is_top_flag

        return RegistrationResult(
            orchestrator_id=orchestrator_id,
            address=address,
            first_registration=first_registration,
            registration_count=registration_count,
            is_top_100=is_top_flag,
            eligible_for_payments=eligible_flag,
            denylisted=denylisted_flag,
            has_active_payments=has_active_payments,
            cooldown_expires_at=record.get("cooldown_expires_at"),
            message=message,
        )

    def is_eligible(self, orchestrator_id: str) -> bool:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return False
            now_dt = datetime.now(timezone.utc)
            cooldown_active = self._refresh_cooldown_state(record, now_dt)
            denylisted_flag = bool(record.get("denylisted", False))
            changed = False
            if denylisted_flag:
                if record.get("eligible_for_payments"):
                    record["eligible_for_payments"] = False
                    changed = True
            elif cooldown_active:
                if record.get("eligible_for_payments"):
                    record["eligible_for_payments"] = False
                    changed = True
            else:
                desired = bool(record.get("is_top_100", False))
                if record.get("eligible_for_payments") != desired:
                    record["eligible_for_payments"] = desired
                    changed = True
            if changed:
                self._persist()
            return bool(record.get("eligible_for_payments", False)) and not denylisted_flag

    def is_in_cooldown(self, orchestrator_id: str) -> bool:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return False
            return self._refresh_cooldown_state(record, datetime.now(timezone.utc))

    def set_cooldown(self, orchestrator_id: str, seconds: int) -> None:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return
            now_dt = datetime.now(timezone.utc)
            expires = now_dt + timedelta(seconds=seconds)
            record["cooldown_expires_at"] = expires.isoformat()
            record["eligible_for_payments"] = False
            record["last_cooldown_started_at"] = now_dt.isoformat()
            self._persist()
        self._write_audit_event(
            "cooldown_started",
            orchestrator_id,
            {"cooldown_expires_at": expires.isoformat()},
        )

    def clear_cooldown(self, orchestrator_id: str) -> None:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return
            if not record.get("cooldown_expires_at"):
                return
            record["cooldown_expires_at"] = None
            record["eligible_for_payments"] = bool(record.get("is_top_100", False))
            record["last_cooldown_cleared_at"] = datetime.now(timezone.utc).isoformat()
            self._persist()
        self._write_audit_event("cooldown_cleared", orchestrator_id, {})

    def record_missed_all_services(self, orchestrator_id: str) -> None:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return
            record["last_missed_all_services"] = datetime.now(timezone.utc).isoformat()
            self._persist()

    def record_healthy_cycle(self, orchestrator_id: str) -> None:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if not record:
                return
            record["last_healthy_at"] = datetime.now(timezone.utc).isoformat()
            self._persist()

    def get_record(self, orchestrator_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._records.get(orchestrator_id)
            if record:
                return json.loads(json.dumps(record))
            return None

    def all_records(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return json.loads(json.dumps(self._records))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _refresh_cooldown_state(record: Dict[str, Any], now_dt: datetime) -> bool:
        expiry = record.get("cooldown_expires_at")
        if not expiry:
            return False
        try:
            expiry_dt = datetime.fromisoformat(expiry)
        except ValueError:
            record["cooldown_expires_at"] = None
            return False
        if expiry_dt <= now_dt:
            record["cooldown_expires_at"] = None
            return False
        return True


__all__ = [
    "Registry",
    "RegistryError",
    "RegistrationResult",
]
