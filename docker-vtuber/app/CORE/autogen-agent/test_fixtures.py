"""
Test Fixtures
Common test data and mock objects
"""

from typing import Dict, Any
from datetime import datetime
import json


class MockRedis:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self.published = []
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value):
        self.data[key] = value
    
    def setex(self, key, ttl, value):
        self.data[key] = value
    
    def publish(self, channel, message):
        self.published.append({
            "channel": channel,
            "message": message,
            "timestamp": datetime.now()
        })
    
    def ping(self):
        return True


class MockNeo4j:
    """Mock Neo4j driver for testing"""
    def __init__(self):
        self.nodes = []
        self.relationships = []
    
    async def run(self, query, **params):
        # Simple mock implementation
        return MockResult([])


class MockResult:
    """Mock query result"""
    def __init__(self, records):
        self.records = records
    
    async def single(self):
        return self.records[0] if self.records else None
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.records:
            return self.records.pop(0)
        raise StopAsyncIteration


# Test data generators

def generate_test_stimuli(num: int = 1) -> list:
    """Generate test stimuli"""
    stimuli = []
    for i in range(num):
        stimuli.append({
            "stimuli_id": f"test_stim_{i}",
            "content": f"Test stimuli content {i}",
            "priority": "normal",
            "timestamp": datetime.now().timestamp()
        })
    return stimuli


def generate_test_scb_state() -> Dict[str, Any]:
    """Generate test SCB state"""
    return {
        "agent": "test_agent",
        "content": "Test state content",
        "timestamp": datetime.now().timestamp(),
        "metadata": {
            "test": True,
            "source": "test_fixtures"
        }
    }


def generate_test_nodes(num: int = 1, context: str = "test") -> list:
    """Generate test graph nodes"""
    nodes = []
    for i in range(num):
        nodes.append({
            "id": f"test_node_{i}",
            "content": f"Test node content {i}",
            "context": context,
            "node_type": "test",
            "timestamp": datetime.now().timestamp(),
            "metadata": {"index": i}
        })
    return nodes
