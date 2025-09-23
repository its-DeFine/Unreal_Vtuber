import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from payments.ledger import Ledger
from payments.registry import Registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        balances_path = Path(self.temp_dir.name) / "balances.json"
        registry_path = Path(self.temp_dir.name) / "registry.json"
        self.ledger = Ledger(balances_path)
        self.registry_path = registry_path

        self.settings = SimpleNamespace(
            top_contract_address="0x0000000000000000000000000000000000000000",
            top_contract_function="getTop",
            top_contract_abi_json=None,
            top_contract_abi_path=None,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_registration_without_top_contract_defaults_to_eligible(self):
        self.settings.top_contract_address = None
        with patch("payments.registry.fetch_orchestrator_addresses", return_value=[
            "0x1111111111111111111111111111111111111111"
        ]):
            registry = Registry(
                path=self.registry_path,
                settings=self.settings,
                ledger=self.ledger,
                web3=None,
            )

            result = registry.register(
                orchestrator_id="orch-1",
                address="0x1111111111111111111111111111111111111111",
            )

        self.assertTrue(result.first_registration)
        self.assertTrue(result.is_top_100)
        self.assertTrue(registry.is_eligible("orch-1"))

    def test_registration_marks_top_membership(self):
        registry = Registry(
            path=self.registry_path,
            settings=self.settings,
            ledger=self.ledger,
            web3=None,
        )

        with patch.object(Registry, "_fetch_top_addresses", return_value=[
            "0xaaaa", "0xbbbb",
        ]), patch("payments.registry.fetch_orchestrator_addresses", return_value=[
            "0xaaaa", "0xbbbb"
        ]):
            result = registry.register(
                orchestrator_id="orch-2",
                address="0xAAAA",
            )

        self.assertTrue(result.is_top_100)
        self.assertTrue(registry.is_eligible("orch-2"))

        with patch.object(Registry, "_fetch_top_addresses", return_value=[
            "0xcccc",
        ]), patch("payments.registry.fetch_orchestrator_addresses", return_value=[
            "0xcccc"
        ]):
            result_second = registry.register(
                orchestrator_id="orch-2",
                address="0xaaaa",
            )

        self.assertFalse(result_second.first_registration)
        self.assertFalse(result_second.is_top_100)
        self.assertFalse(registry.is_eligible("orch-2"))


if __name__ == "__main__":
    unittest.main()
