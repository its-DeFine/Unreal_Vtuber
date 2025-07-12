import os
import sys
import types
import tempfile
import shutil
from pathlib import Path
import unittest

# Provide minimal stubs for optional dependencies so server_adapter can be imported
if 'requests' not in sys.modules:
    sys.modules['requests'] = types.ModuleType('requests')

if 'jsonschema' not in sys.modules:
    jsonschema = types.ModuleType('jsonschema')
    jsonschema.validate = lambda *a, **k: None
    class ValidationError(Exception):
        pass
    jsonschema.ValidationError = ValidationError
    sys.modules['jsonschema'] = jsonschema

if 'httpx' not in sys.modules:
    sys.modules['httpx'] = types.ModuleType('httpx')

# Import the module under test
MODULE_PATH = Path(__file__).resolve().parents[1] / 'neurosync-worker'
sys.path.append(str(MODULE_PATH))
import server_adapter

class FakeMonotonic:
    def __init__(self, start=0.0):
        self.value = start
    def __call__(self):
        return self.value
    def advance(self, delta):
        self.value += delta

class JobWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.flag_path = self.tmpdir / 'flag'
        self.fake_time = FakeMonotonic(100.0)

        server_adapter.WINDOW_ACTIVE_FLAG_PATH = str(self.flag_path)
        server_adapter.WINDOW_DURATION_SEC = 1
        server_adapter._window_expiry = None
        self.original_monotonic = server_adapter.time.monotonic
        server_adapter.time.monotonic = self.fake_time

    def tearDown(self):
        server_adapter.time.monotonic = self.original_monotonic
        if self.flag_path.exists():
            os.remove(self.flag_path)
        shutil.rmtree(self.tmpdir)
        server_adapter._window_expiry = None

    def test_open_job_window_creates_flag_and_active(self):
        server_adapter.open_job_window()
        self.assertTrue(server_adapter.is_job_window_active())
        self.assertTrue(self.flag_path.exists())
        self.assertEqual(server_adapter._window_expiry, self.fake_time() + 1)

    def test_extend_job_window_resets_expiry(self):
        server_adapter.open_job_window()
        initial_expiry = server_adapter._window_expiry
        self.fake_time.advance(0.5)
        server_adapter.extend_job_window()
        self.assertGreater(server_adapter._window_expiry, initial_expiry)
        self.assertEqual(server_adapter._window_expiry, self.fake_time() + 1)

    def test_close_job_window_if_expired(self):
        server_adapter.open_job_window()
        self.fake_time.advance(2)
        closed = server_adapter.close_job_window_if_expired()
        self.assertTrue(closed)
        self.assertFalse(server_adapter.is_job_window_active())
        self.assertFalse(self.flag_path.exists())

if __name__ == '__main__':
    unittest.main()
