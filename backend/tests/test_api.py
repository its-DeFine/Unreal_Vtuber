import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from payments.api import create_app
from payments.ledger import Ledger
from payments.registry import Registry


@pytest.fixture()
def temp_paths():
    tmp = tempfile.TemporaryDirectory()
    balances_path = Path(tmp.name) / "balances.json"
    registry_path = Path(tmp.name) / "registry.json"
    yield balances_path, registry_path
    tmp.cleanup()


@pytest.fixture()
def anyio_backend():
    return "asyncio"


def build_registry(temp_paths):
    balances_path, registry_path = temp_paths
    ledger = Ledger(balances_path)
    settings = SimpleNamespace(
        top_contract_address=None,
        top_contract_function="getTop",
        top_contract_abi_json=None,
        top_contract_abi_path=None,
        registration_rate_limit_per_minute=5,
        registration_rate_limit_burst=5,
        api_admin_token=None,
        audit_log_path=registry_path.with_name("registry-audit.log"),
        capture_proof_ttl_seconds=300,
        require_trusted_capture=False,
    )
    registry = Registry(
        path=registry_path,
        settings=settings,
        ledger=ledger,
        web3=None,
    )
    return registry, ledger


@pytest.mark.anyio("asyncio")
async def test_register_endpoint_success(temp_paths):
    registry, ledger = build_registry(temp_paths)
    app_settings = SimpleNamespace(
        registration_rate_limit_per_minute=5,
        registration_rate_limit_burst=5,
        api_admin_token=None,
        capture_proof_ttl_seconds=300,
        require_trusted_capture=False,
    )
    app = create_app(registry, ledger, app_settings)

    payload = {
        "orchestrator_id": "orch-test",
        "address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(Registry, "_resolve_top_set", return_value={payload["address"].lower()}):
            response = await client.post("/api/orchestrators/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["orchestrator_id"] == "orch-test"
    assert body["eligible_for_payments"] is True
    assert body["capture_trust_level"] == "untrusted"


@pytest.mark.anyio("asyncio")
async def test_register_endpoint_rate_limited(temp_paths):
    registry, ledger = build_registry(temp_paths)
    app_settings = SimpleNamespace(
        registration_rate_limit_per_minute=1,
        registration_rate_limit_burst=1,
        api_admin_token=None,
        capture_proof_ttl_seconds=300,
        require_trusted_capture=False,
    )
    app = create_app(registry, ledger, app_settings)

    payload = {
        "orchestrator_id": "orch-rate",
        "address": "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(Registry, "_resolve_top_set", return_value={payload["address"].lower()}):
            first = await client.post("/api/orchestrators/register", json=payload)
            second = await client.post("/api/orchestrators/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.anyio("asyncio")
async def test_admin_listing_requires_token(temp_paths):
    registry, ledger = build_registry(temp_paths)

    address = "0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    with patch.object(Registry, "_resolve_top_set", return_value={address.lower()}):
        registry.register(
            orchestrator_id="orch-admin",
            address=address,
        )

    app_settings = SimpleNamespace(
        registration_rate_limit_per_minute=5,
        registration_rate_limit_burst=5,
        api_admin_token="secret",
        capture_proof_ttl_seconds=300,
        require_trusted_capture=False,
    )
    app = create_app(registry, ledger, app_settings)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/orchestrators")
        assert unauthorized.status_code == 401

        authorized = await client.get(
            "/api/orchestrators",
            headers={"X-Admin-Token": "secret"},
        )

    assert authorized.status_code == 200
    data = authorized.json()
    assert data["orchestrators"][0]["orchestrator_id"] == "orch-admin"


@pytest.mark.anyio("asyncio")
async def test_submit_proof_success(temp_paths):
    registry, ledger = build_registry(temp_paths)
    app_settings = SimpleNamespace(
        registration_rate_limit_per_minute=5,
        registration_rate_limit_burst=5,
        api_admin_token=None,
        capture_proof_ttl_seconds=300,
        require_trusted_capture=False,
    )
    app = create_app(registry, ledger, app_settings)

    address = "0xDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
    with patch.object(Registry, "_resolve_top_set", return_value={address.lower()}):
        registry.register(
            orchestrator_id="orch-proof",
            address=address,
        )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        proof_payload = {
            "orchestrator_id": "orch-proof",
            "nonce": "nonce-123",
            "attestation": {
                "nonce": "nonce-123",
                "measurement": "hash",
                "gpu_uuid": "GPU-123",
            },
            "frame_hash_root": "frame-root",
            "command_root": "command-root",
            "script_root": "script-root",
            "asset_root": "asset-root",
            "proof": {
                "status": "valid",
                "public_inputs": {
                    "script_root": "script-root",
                    "asset_root": "asset-root",
                    "frame_root": "frame-root",
                    "command_root": "command-root",
                    "nonce": "nonce-123",
                },
            },
        }

        response = await client.post(
            "/api/orchestrators/submit-proof",
            json=proof_payload,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["orchestrator_id"] == "orch-proof"
    assert body["capture_trust_level"] == "trusted"
