"""Main payment loop that ties monitoring + ledger + Web3 payouts."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, Optional

import requests

from .config import PaymentSettings
from .ledger import Ledger
from .payment_client import PaymentClient
from .registry import Registry
from .service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)


class PaymentProcessor:
    def __init__(
        self,
        settings: PaymentSettings,
        monitor: ServiceMonitor,
        ledger: Ledger,
        payment_client: PaymentClient,
        registry: Registry,
    ) -> None:
        self.settings = settings
        self.monitor = monitor
        self.ledger = ledger
        self.payment_client = payment_client
        self.registry = registry

        self._missing_cycles: Dict[str, int] = defaultdict(int)
        self._monitors: Dict[str, ServiceMonitor] = {}
        self._http = requests.Session()

    def evaluate_once(self) -> None:
        """Run a single monitoring + payment evaluation cycle over all orchestrators."""
        records = self.registry.all_records()
        if not records:
            logger.debug("No orchestrators registered; skipping payment evaluation")
            return

        for orchestrator_id, record in records.items():
            try:
                self._evaluate_orchestrator(orchestrator_id, record)
            except Exception as exc:  # pragma: no cover - defensive guard per orchestrator
                logger.exception("Cycle evaluation failed for %s: %s", orchestrator_id, exc)

    def _evaluate_orchestrator(self, orchestrator_id: str, record: Dict[str, Any]) -> None:
        summary = self._collect_health_summary(orchestrator_id, record)
        if summary is None:
            logger.debug("Health summary unavailable for %s; skipping", orchestrator_id)
            return

        services_up = summary.get("services_up", 0)
        total_services = summary.get("total_services", 0)
        eligible = summary.get("eligible_for_payment", False)
        status_message = summary.get("status_message", "unknown")

        missing_all = total_services > 0 and services_up == 0
        if missing_all:
            self._handle_missing_services(orchestrator_id, record)
            return

        if services_up > 0:
            self.registry.record_healthy_cycle(orchestrator_id)
        self._missing_cycles.pop(orchestrator_id, None)

        if self.registry.is_in_cooldown(orchestrator_id):
            cooldown = self.registry.get_record(orchestrator_id) or {}
            logger.info(
                "Payments paused for %s during cooldown (expires %s)",
                orchestrator_id,
                cooldown.get("cooldown_expires_at"),
            )
            return

        if not self.registry.is_eligible(orchestrator_id):
            logger.debug("Orchestrator %s not eligible for payments", orchestrator_id)
            return

        logger.debug(
            "Service summary for %s: up=%s total=%s eligible=%s",
            orchestrator_id,
            services_up,
            total_services,
            eligible,
        )

        if eligible and services_up == total_services and total_services > 0:
            proof_ttl = max(1, self.settings.capture_proof_ttl_seconds)
            if not self.registry.has_fresh_proof(
                orchestrator_id,
                ttl_seconds=proof_ttl,
                require_trusted=self.settings.require_trusted_capture,
            ):
                logger.info(
                    "[%s] Skipping credit: fresh capture proof missing",
                    orchestrator_id,
                )
                return

            increment = self.settings.payment_increment_eth
            new_balance = self.ledger.credit(orchestrator_id, increment)
            logger.info(
                "[%s] Eligible cycle → credited %s ETH. Balance=%s",
                orchestrator_id,
                increment,
                new_balance,
            )
            payout_address = record.get("address") or record.get("payout_address")
            if not payout_address:
                logger.error("[%s] Missing payout address; skipping transfer", orchestrator_id)
                return
            self._maybe_payout(orchestrator_id, payout_address, new_balance)
        else:
            logger.info("[%s] Cycle not eligible for payout credit: %s", orchestrator_id, status_message)

    def _handle_missing_services(self, orchestrator_id: str, record: Dict[str, Any]) -> None:
        self._missing_cycles[orchestrator_id] += 1
        self.registry.record_missed_all_services(orchestrator_id)
        logger.warning(
            "[%s] All monitored services offline (cycle %s of %s)",
            orchestrator_id,
            self._missing_cycles[orchestrator_id],
            self.settings.payment_miss_threshold,
        )
        if self._missing_cycles[orchestrator_id] >= self.settings.payment_miss_threshold:
            self.registry.set_cooldown(orchestrator_id, self.settings.payment_cooldown_seconds)
            cooldown = self.registry.get_record(orchestrator_id) or {}
            logger.error(
                "[%s] Cooldown triggered until %s",
                orchestrator_id,
                cooldown.get("cooldown_expires_at"),
            )
            self._missing_cycles[orchestrator_id] = 0

    def _collect_health_summary(
        self, orchestrator_id: str, record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        health_url = record.get("health_url")
        monitor_services = record.get("monitored_services")

        if health_url:
            timeout = record.get("health_timeout")
            if timeout is None:
                timeout = self.settings.default_health_timeout
            try:
                response = self._http.get(
                    health_url,
                    headers={"Accept": "application/json"},
                    timeout=timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as exc:
                logger.warning("[%s] Remote health check failed (%s): %s", orchestrator_id, health_url, exc)
                return None
            if not isinstance(payload, dict) or "summary" not in payload:
                logger.warning("[%s] Remote health payload malformed: %s", orchestrator_id, payload)
                return None
            summary = payload.get("summary") or {}
            if monitor_services and isinstance(payload.get("services"), dict):
                missing = [svc for svc in monitor_services if svc not in payload["services"]]
                if missing:
                    summary = dict(summary)
                    summary.setdefault("status_message", "")
                    summary["status_message"] = (
                        summary.get("status_message") or ""
                    ) + f"; missing metrics for: {', '.join(sorted(missing))}"
            if record.get("min_service_uptime") is not None:
                desired = float(record["min_service_uptime"])
            else:
                desired = self.settings.default_min_service_uptime
            summary = dict(summary)
            summary.setdefault("min_service_uptime", desired)
            return summary

        # Fallback to local monitoring (used when backend shares the host)
        monitor = self._monitors.get(orchestrator_id)
        if monitor is None:
            monitor = ServiceMonitor(services=monitor_services)
            self._monitors[orchestrator_id] = monitor
        status = monitor.check_services()
        summary = status.get("summary") or {}
        if record.get("min_service_uptime") is not None:
            summary = dict(summary)
            summary["min_service_uptime"] = float(record["min_service_uptime"])
        return summary

    def _maybe_payout(
        self, orchestrator_id: str, payout_address: str, balance: Decimal
    ) -> None:
        threshold = self.settings.payout_threshold_eth
        if balance < threshold:
            logger.debug(
                "[%s] Balance %s below threshold %s; deferring payout",
                orchestrator_id,
                balance,
                threshold,
            )
            return

        amount = balance
        logger.info("[%s] Triggering payout of %s ETH to %s", orchestrator_id, amount, payout_address)
        tx_hash = self.payment_client.send_payment(payout_address, amount)
        if tx_hash is not None or self.payment_client.dry_run:
            self.ledger.set_balance(orchestrator_id, Decimal("0"))
            logger.info("[%s] Ledger reset after payout (tx=%s)", orchestrator_id, tx_hash)

    def run_forever(self) -> None:
        """Blocking loop that runs the evaluation every configured interval."""
        interval = self.settings.payment_interval_seconds
        logger.info("Starting payment loop with interval %s seconds", interval)
        try:
            while True:
                start = time.time()
                try:
                    self.evaluate_once()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Unexpected error in payment cycle: %s", exc)
                elapsed = time.time() - start
                sleep_for = max(interval - elapsed, 0)
                time.sleep(sleep_for)
        except KeyboardInterrupt:
            logger.info("Payment loop stopped via keyboard interrupt")
