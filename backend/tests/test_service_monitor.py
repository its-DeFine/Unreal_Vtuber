import unittest
from unittest.mock import MagicMock, patch

from payments.service_monitor import ServiceMonitor


class ServiceMonitorTests(unittest.TestCase):
    def setUp(self):
        self.fake_containers = []

        class FakeContainer:
            def __init__(self, name, status, health="healthy"):
                self.name = name
                self.status = status
                self.attrs = {"State": {"Health": {"Status": health}}}

        self.FakeContainer = FakeContainer

    def _mock_client(self, containers):
        client = MagicMock()
        client.containers.list.return_value = containers
        return client

    @patch("payments.service_monitor.docker.from_env")
    def test_all_services_running_sets_eligible(self, mock_from_env):
        containers = [
            self.FakeContainer("vtuber-unreal-game", "running"),
            self.FakeContainer("vtuber-unreal-signaling", "running"),
            self.FakeContainer("vtuber-turn-server", "running"),
        ]
        client = self._mock_client(containers)
        mock_from_env.return_value = client

        monitor = ServiceMonitor()
        result = monitor.check_services()
        summary = result["summary"]
        self.assertTrue(summary["eligible_for_payment"])
        self.assertEqual(summary["services_up"], 3)

    @patch("payments.service_monitor.docker.from_env")
    def test_missing_service_marks_ineligible(self, mock_from_env):
        containers = [self.FakeContainer("vtuber-unreal-game", "running")]
        client = self._mock_client(containers)
        mock_from_env.return_value = client

        monitor = ServiceMonitor()
        result = monitor.check_services()
        summary = result["summary"]
        self.assertFalse(summary["eligible_for_payment"])
        self.assertEqual(summary["services_down"], 2)


if __name__ == "__main__":
    unittest.main()
