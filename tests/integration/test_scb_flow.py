import os
import pytest

from docker_vtuber.app.CORE.autogen_agent.autogen_agent.clients.scb_v2_client import SCBv2Client

@pytest.fixture(scope="module")
def scb_client():
    url = os.getenv("REDIS_SCB_URL", "redis://localhost:6379/2")
    client = SCBv2Client(redis_url=url, default_max_chars=200)
    client._redis.flushdb()
    yield client
    client._redis.flushdb()

def test_s1_and_s2_flow(scb_client):
    """End-to-end slice flow: S2 writes reasoning, S1 writes summary."""
    trader_key = "scb:team:trader"
    global_key = "scb:global"

    # Simulate S2 tool writing reasoning
    s2_event = {"type": "reasoning", "actor": "s2_agent", "text": "Trader thinking about TSLA"}
    scb_client.append_event(trader_key, s2_event)

    # Simulate S1 summary write
    s1_summary = {"type": "speech_summary", "actor": "s1", "text": "Hello traders, TSLA update"}
    scb_client.append_event(global_key, s1_summary)

    # Verify team slice contains event
    trader_slice = scb_client.get_slice(trader_key)
    assert trader_slice["window"][-1]["text"] == s2_event["text"]

    # Verify global slice contains summary
    global_slice = scb_client.get_slice(global_key)
    assert global_slice["window"][-1]["text"] == s1_summary["text"]

    # Ensure slices are distinct
    assert trader_slice != global_slice 