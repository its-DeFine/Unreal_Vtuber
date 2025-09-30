import tempfile
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from payments.ledger import Ledger
from payments.registry import Registry, RegistryError


@pytest.fixture()
def temp_paths():
    tmp = tempfile.TemporaryDirectory()
    balances_path = Path(tmp.name) / "balances.json"
    registry_path = Path(tmp.name) / "registry.json"
    yield balances_path, registry_path
    tmp.cleanup()


@pytest.fixture()
def settings():
    return SimpleNamespace(
        top_contract_address="0x0000000000000000000000000000000000000000",
        top_contract_function="getTop",
        top_contract_abi_json=None,
        top_contract_abi_path=None,
        registration_rate_limit_per_minute=5,
        registration_rate_limit_burst=5,
        address_denylist=[],
    )


def create_registry(registry_path, balances_path, settings):
    ledger = Ledger(balances_path)
    return Registry(
        path=registry_path,
        settings=settings,
        ledger=ledger,
        web3=None,
    )


def test_registration_enforces_top_membership(temp_paths, settings):
    balances_path, registry_path = temp_paths
    registry = create_registry(registry_path, balances_path, settings)

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        result = registry.register(
            orchestrator_id="orch-1",
            address="0xAAAA",
        )

    assert result.first_registration is True
    assert result.is_top_100 is True
    assert registry.is_eligible("orch-1") is True

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        result_second = registry.register(
            orchestrator_id="orch-1",
            address="0xAAAA",
        )

    assert result_second.first_registration is False
    assert result_second.registration_count == 2


def test_registration_rejects_out_of_top(temp_paths, settings):
    balances_path, registry_path = temp_paths
    registry = create_registry(registry_path, balances_path, settings)

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        with pytest.raises(RegistryError) as exc:
            registry.register(
                orchestrator_id="orch-2",
                address="0xBBBB",
            )
    assert exc.value.status_code == 403


def test_skip_rank_validation_allows_local_registration(temp_paths, settings):
    balances_path, registry_path = temp_paths
    registry = create_registry(registry_path, balances_path, settings)

    result = registry.register(
        orchestrator_id="orch-local",
        address="0xCCCC",
        skip_rank_validation=True,
    )

    assert result.is_top_100 is True
    assert registry.is_eligible("orch-local") is True


def test_cooldown_controls_eligibility(temp_paths, settings):
    balances_path, registry_path = temp_paths
    ledger = Ledger(balances_path)
    registry = Registry(
        path=registry_path,
        settings=settings,
        ledger=ledger,
        web3=None,
    )

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        registry.register(
            orchestrator_id="orch-penalty",
            address="0xAAAA",
        )

    assert registry.is_eligible("orch-penalty") is True
    registry.set_cooldown("orch-penalty", seconds=10)
    assert registry.is_in_cooldown("orch-penalty") is True
    assert registry.is_eligible("orch-penalty") is False
    registry.clear_cooldown("orch-penalty")
    assert registry.is_eligible("orch-penalty") is True


def test_address_uniqueness(temp_paths, settings):
    balances_path, registry_path = temp_paths
    registry = create_registry(registry_path, balances_path, settings)

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        registry.register(
            orchestrator_id="orch-1",
            address="0xAAAA",
        )

    with patch.object(Registry, "_resolve_top_set", return_value={"0xaaaa"}):
        with pytest.raises(RegistryError) as exc:
            registry.register(
                orchestrator_id="orch-2",
                address="0xAAAA",
            )
    assert exc.value.status_code == 409


def test_registration_rejects_denylisted_address(temp_paths, settings):
    balances_path, registry_path = temp_paths
    settings.address_denylist = ["0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF"]
    registry = create_registry(registry_path, balances_path, settings)

    with pytest.raises(RegistryError) as exc:
        registry.register(
            orchestrator_id="blocked",
            address="0xDeadBeefDeadBeefDeadBeefDeadBeefDeadBeeF",
            skip_rank_validation=True,
        )

    assert exc.value.status_code == 403
    assert "denylisted" in str(exc.value)
    assert registry.get_record("blocked") is None


def test_existing_record_becomes_denylisted(temp_paths, settings):
    balances_path, registry_path = temp_paths
    settings.address_denylist = []
    registry = create_registry(registry_path, balances_path, settings)

    registry.register(
        orchestrator_id="orch-keep",
        address="0xAAAA",
        skip_rank_validation=True,
    )

    settings.address_denylist = ["0xaaaa"]
    reloaded = create_registry(registry_path, balances_path, settings)

    record = reloaded.get_record("orch-keep")
    assert record is not None
    assert record["denylisted"] is True
    assert reloaded.is_eligible("orch-keep") is False
