import sys
import types
import tempfile
import shutil
import asyncio
from pathlib import Path
import unittest

# Minimal stubs so server_adapter imports without optional deps
for name in ("requests", "httpx"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

if "jsonschema" not in sys.modules:
    jsonschema = types.ModuleType("jsonschema")
    jsonschema.validate = lambda *a, **k: None
    class ValidationError(Exception):
        pass
    jsonschema.ValidationError = ValidationError
    sys.modules["jsonschema"] = jsonschema

MODULE_PATH = Path(__file__).resolve().parents[1] / "neurosync-worker"
sys.path.append(str(MODULE_PATH))
import server_adapter

class FakeRequest:
    def __init__(self, path: str, data: dict):
        self._data = data
        self.url = types.SimpleNamespace(path=path)

    async def json(self):
        return self._data

class ServerAdapterEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.flag_path = self.tmpdir / "flag"
        server_adapter.WINDOW_ACTIVE_FLAG_PATH = str(self.flag_path)
        server_adapter.WINDOW_DURATION_SEC = 5
        server_adapter._window_expiry = None
        server_adapter.VTUBER_PAYMENT_ENABLED = True
        server_adapter.submit_job_to_neurosync = lambda payload: "hash123"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        server_adapter._window_expiry = None

    def test_text_echo_blocked_without_window(self):
        req = FakeRequest("/text-echo", {"text": "hi"})
        async def handler(r):
            return await server_adapter.text_echo_handler(r)
        resp = asyncio.run(server_adapter._window_guard(req, handler))
        self.assertEqual(resp.status_code, 403)

    def test_vtuber_start_opens_window_and_allows_text_echo(self):
        start_req = FakeRequest("/v1/vtuber/start", {"job_id": "1", "character": "c", "prompt": "p"})
        async def start_handler(r):
            return await server_adapter.vtuber_start(r)
        resp1 = asyncio.run(server_adapter._window_guard(start_req, start_handler))
        self.assertEqual(resp1.status_code, 200)
        self.assertTrue(server_adapter.is_job_window_active())

        echo_req = FakeRequest("/text-echo", {"text": "hello"})
        async def echo_handler(r):
            return await server_adapter.text_echo_handler(r)
        resp2 = asyncio.run(server_adapter._window_guard(echo_req, echo_handler))
        self.assertEqual(resp2.status_code, 200)
        body = resp2.body.decode()
        self.assertIn("helloa", body)

if __name__ == "__main__":
    unittest.main()
