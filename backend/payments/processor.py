"""Main payment loop that ties monitoring + ledger + Web3 payouts."""
from __future__ import annotations

import logging
import time
from decimal import Decimal

from .config import PaymentSettings
from .ledger import Ledger
from .payment_client import PaymentClient
from .service_monitor import ServiceMonitor
from .registry import Registry

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

    def evaluate_once(self) -> None:
        """Run a single monitoring + payment evaluation cycle."""
        if not self.registry.is_eligible(self.settings.orchestrator_id):
            logger.debug(
                "Orchestrator %s not eligible for payments",
                self.settings.orchestrator_id,
            )
            return

        status = self.monitor.check_services()
        summary = status.get("summary", {})

        services_up = summary.get("services_up", 0)
        total_services = summary.get("total_services", 0)
        eligible = summary.get("eligible_for_payment", False)

        logger.debug(
            "Service summary: up=%s total=%s eligible=%s", services_up, total_services, eligible
        )

        if eligible and services_up == total_services and total_services > 0:
            new_balance = self.ledger.credit(
                self.settings.orchestrator_id,
                self.settings.payment_increment_eth,
            )
            logger.info(
                "Eligible cycle → credited %s ETH. Balance=%s", 
                self.settings.payment_increment_eth,
                new_balance,
            )
            self._maybe_payout(new_balance)
        else:
            logger.info("Cycle not eligible for payout credit: %s", summary.get("status_message"))

    def _maybe_payout(self, balance: Decimal) -> None:
        threshold = self.settings.payout_threshold_eth
        if balance < threshold:
            logger.debug(
                "Balance %s below threshold %s; deferring payout", balance, threshold
            )
            return

        amount = balance
        logger.info(
            "Triggering payout of %s ETH to %s", amount, self.settings.orchestrator_address
        )
        tx_hash = self.payment_client.send_payment(self.settings.orchestrator_address, amount)
        if tx_hash is not None or self.payment_client.dry_run:
            self.ledger.set_balance(self.settings.orchestrator_id, Decimal("0"))
            logger.info("Ledger reset after payout (tx=%s)", tx_hash)

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
