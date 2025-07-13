import os
import time

import pytest

from docker_vtuber.app.CORE.autogen_agent.autogen_agent.clients.scb_v2_client import SCBv2Client


@pytest.fixture(scope="module")
def scb_client():
    # Use a dedicated Redis DB (1) for tests to avoid clobbering prod data
    url = os.getenv("REDIS_SCB_URL", "redis://localhost:6379/1")
    client = SCBv2Client(redis_url=url, default_max_chars=100)
    # flush before & after
    client._redis.flushdb()
    yield client
    client._redis.flushdb()


def _slice_size(client, key):
    raw = client._redis.get(key)
    return len(raw.encode("utf-8")) if raw else 0


def test_char_budget_enforced(scb_client):
    key = "scb:team:test"

    # Append events until over budget (default_max_chars=100)
    for i in range(20):
        scb_client.append_event(key, {"type": "note", "actor": "tester", "text": f"event {i} - " + "x" * 20})

    size = _slice_size(scb_client, key)
    assert size <= 100, f"slice size {size} exceeds budget"


def test_team_isolation(scb_client):
    trader_key = "scb:team:trader"
    educator_key = "scb:team:educator"

    scb_client.append_event(trader_key, {"type": "note", "actor": "trader", "text": "trader event"})
    scb_client.append_event(educator_key, {"type": "note", "actor": "educator", "text": "educator event"})

    trader_slice = scb_client.get_slice(trader_key)
    educator_slice = scb_client.get_slice(educator_key)

    assert trader_slice != educator_slice
    assert trader_slice["window"][0]["actor"] == "trader"
    assert educator_slice["window"][0]["actor"] == "educator" 