"""CLI entrypoint for the payments backend."""
from __future__ import annotations

import logging
import sys

from .config import settings
from .ledger import Ledger
from .payment_client import PaymentClient
from .processor import PaymentProcessor
from .registry import Registry
from .service_monitor import ServiceMonitor


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
        stream=sys.stdout,
    )


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting payments backend for orchestrator %s", settings.orchestrator_id)

    monitor = ServiceMonitor()
    ledger = Ledger(settings.ledger.balances)
    payment_client = PaymentClient(
        rpc_url=settings.eth_rpc_url,
        chain_id=settings.chain_id,
        private_key=settings.payment_private_key,
        keystore_path=settings.payment_keystore_path,
        keystore_password=settings.payment_keystore_password,
        dry_run=settings.payment_dry_run,
    )

    registry = Registry(
        path=settings.registry_paths.registry,
        settings=settings,
        ledger=ledger,
        web3=payment_client.web3,
    )

    registration = registry.register(
        orchestrator_id=settings.orchestrator_id,
        address=settings.orchestrator_address,
    )

    logger.info(
        "Registration: first=%s active_payments=%s top_100=%s count=%s",
        registration.first_registration,
        registration.has_active_payments,
        registration.is_top_100,
        registration.registration_count,
    )

    processor = PaymentProcessor(settings, monitor, ledger, payment_client, registry)
    processor.run_forever()


if __name__ == "__main__":
    main()
