import sys
import types
import unittest
from pathlib import Path

# Stub redis to avoid dependency
if 'redis' not in sys.modules:
    redis = types.ModuleType('redis')
    class ConnectionError(Exception):
        pass
    class DummyClient:
        def ping(self):
            pass
        def pipeline(self):
            class P:
                def lpush(self, *a):
                    pass
                def ltrim(self, *a):
                    pass
                def execute(self):
                    pass
            return P()
        def lrange(self, *a):
            return []
        def get(self, *a):
            return None
        def set(self, *a):
            pass
    def from_url(*a, **k):
        return DummyClient()
    redis.exceptions = types.SimpleNamespace(ConnectionError=ConnectionError)
    redis.from_url = from_url
    sys.modules['redis'] = redis

MODULE_BASE = Path(__file__).resolve().parents[1] / 'NeuroBridge/NeuroSync_Player'
sys.path.append(str(MODULE_BASE))
from utils.scb.scb_store import scb_store

class SCBStoreTests(unittest.TestCase):
    def setUp(self):
        scb_store.use_redis = False
        scb_store._memory_log.clear()
        scb_store._memory_summary = ""

    def test_append_and_retrieve(self):
        scb_store.append({'type': 'event', 'actor': 'user', 'text': 'hello'})
        entries = scb_store.get_log_entries(10)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['text'], 'hello')

    def test_summary_roundtrip(self):
        scb_store.set_summary('summary')
        self.assertEqual(scb_store.get_summary(), 'summary')
        full = scb_store.get_full()
        self.assertEqual(full['summary'], 'summary')

if __name__ == '__main__':
    unittest.main()
