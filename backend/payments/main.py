"""CLI entrypoint for the payments backend."""
from __future__ import annotations

import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List

from pydantic import ValidationError

from .api import create_app, run_api
from .config import BootstrapOrchestrator, settings
from .ledger import Ledger
from .payment_client import PaymentClient
from .processor import PaymentProcessor
from .registry import Registry, RegistryError
from .service_monitor import ServiceMonitor


def _normalize_bootstrap_payload(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield dict(item)
    elif isinstance(payload, dict):
        if "orchestrator_id" in payload and "address" in payload:
            yield dict(payload)
        else:
            for orchestrator_id, value in payload.items():
                if isinstance(value, dict):
                    candidate = dict(value)
                    candidate.setdefault("orchestrator_id", orchestrator_id)
                    yield candidate


def _load_bootstrap_orchestrators(logger: logging.Logger) -> List[BootstrapOrchestrator]:
    entries: List[BootstrapOrchestrator] = []
    sources: list[tuple[str, Any]] = []

    inline = settings.bootstrap_orchestrators_inline
    if inline:
        try:
            sources.append(("env:PAYMENTS_BOOTSTRAP_ORCHESTRATORS", json.loads(inline)))
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse PAYMENTS_BOOTSTRAP_ORCHESTRATORS JSON: %s", exc)

    path = settings.bootstrap_orchestrators_path
    if path:
        resolved = Path(path).expanduser()
        if resolved.exists():
            try:
                with resolved.open("r", encoding="utf-8") as handle:
                    sources.append((f"file:{resolved}", json.load(handle)))
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse orchestrator bootstrap file %s: %s", resolved, exc)
            except OSError as exc:
                logger.error("Unable to read orchestrator bootstrap file %s: %s", resolved, exc)

    seen_ids: set[str] = set()
    seen_addresses: set[str] = set()

    for source, payload in sources:
        for candidate in _normalize_bootstrap_payload(payload):
            try:
                entry = BootstrapOrchestrator.model_validate(candidate)
            except ValidationError as exc:
                logger.error("Invalid orchestrator entry from %s: %s", source, exc)
                continue

            lower_id = entry.orchestrator_id.lower()
            lower_address = entry.address.lower()
            if lower_id in seen_ids or lower_address in seen_addresses:
                logger.debug(
                    "Skipping duplicate orchestrator bootstrap entry %s (%s)",
                    entry.orchestrator_id,
                    source,
                )
                continue

            seen_ids.add(lower_id)
            seen_addresses.add(lower_address)
            entries.append(entry)

    return entries


def _register_bootstrap_orchestrators(
    logger: logging.Logger,
    registry: Registry,
    orchestrators: List[BootstrapOrchestrator],
) -> None:
    if not orchestrators:
        return

    skip_rank = settings.bootstrap_skip_rank_validation
    for entry in orchestrators:
        metadata: Dict[str, Any] = {}
        if entry.capability:
            metadata["capability"] = entry.capability
        if entry.contact_email:
            metadata["contact_email"] = entry.contact_email
        if entry.host_public_ip:
            metadata["host_public_ip"] = entry.host_public_ip
            metadata.setdefault("request_ip", entry.host_public_ip)
        if entry.host_name:
            metadata["host_name"] = entry.host_name
        if entry.services_healthy is not None:
            metadata["services_healthy"] = entry.services_healthy
        if entry.health_url:
            metadata["health_url"] = entry.health_url
        if entry.health_timeout is not None:
            metadata["health_timeout"] = entry.health_timeout
        if entry.monitored_services:
            metadata["monitored_services"] = entry.monitored_services
        if entry.min_service_uptime is not None:
            metadata["min_service_uptime"] = entry.min_service_uptime

        try:
            result = registry.register(
                orchestrator_id=entry.orchestrator_id,
                address=entry.address,
                metadata=metadata or None,
                skip_rank_validation=skip_rank,
            )
        except RegistryError as exc:
            logger.error(
                "Failed to bootstrap orchestrator %s (%s): %s",
                entry.orchestrator_id,
                entry.address,
                exc,
            )
            continue

        logger.info(
            "Bootstrapped orchestrator %s (first=%s eligible=%s count=%s)",
            result.orchestrator_id,
            result.first_registration,
            result.eligible_for_payments,
            result.registration_count,
        )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
        stream=sys.stdout,
    )


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting payments backend")

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

    app = create_app(registry, ledger, settings)
    api_thread = threading.Thread(
        target=run_api,
        name="payments-api",
        args=(app, settings),
        daemon=True,
    )
    api_thread.start()
    logger.info(
        "HTTP API available at http://%s:%s", settings.api_host, settings.api_port
    )

    if settings.single_orchestrator_mode:
        try:
            metadata: Dict[str, Any] = {}
            if settings.orchestrator_health_url:
                metadata["health_url"] = settings.orchestrator_health_url
            if settings.orchestrator_health_timeout is not None:
                metadata["health_timeout"] = settings.orchestrator_health_timeout
            metadata["monitored_services"] = monitor.monitored_services
            metadata["min_service_uptime"] = settings.default_min_service_uptime
            registration = registry.register(
                orchestrator_id=settings.orchestrator_id,
                address=settings.orchestrator_address,
                metadata=metadata,
                skip_rank_validation=True,
            )
            logger.info(
                "Autoregistration (single mode): first=%s active_payments=%s top_100=%s count=%s",
                registration.first_registration,
                registration.has_active_payments,
                registration.is_top_100,
                registration.registration_count,
            )
        except RegistryError as exc:
            logger.error("Failed to register orchestrator from settings: %s", exc)

    bootstrap_orchestrators = _load_bootstrap_orchestrators(logger)
    if bootstrap_orchestrators:
        logger.info(
            "Bootstrapping %s orchestrators from configuration", len(bootstrap_orchestrators)
        )
        _register_bootstrap_orchestrators(logger, registry, bootstrap_orchestrators)
    else:
        logger.debug("No bootstrap orchestrators configured")

    processor = PaymentProcessor(settings, monitor, ledger, payment_client, registry)
    processor.run_forever()


if __name__ == "__main__":
    main()
