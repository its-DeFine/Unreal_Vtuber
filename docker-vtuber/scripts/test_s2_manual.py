#!/usr/bin/env python3
"""
Manual test of S2 Teams System
==============================

Simple test to verify basic functionality.
"""

import json
from datetime import datetime

# Create test stimuli
test_stimuli = {
    "stimuli_id": "manual_test_001",
    "content": "Analyze market trends and provide investment recommendations",
    "character_id": "dr._house_doctor_template",  # Should map to TRADER
    "priority": "high",
    "source": "manual_test"
}

# Create batch
batch = {
    "batch_id": "manual_batch_001",
    "timestamp": datetime.now().isoformat(),
    "stimuli_count": 1,
    "stimuli": [test_stimuli]
}

# Write to queue
queue_file = "/tmp/s2_processing_queue.json"
with open(queue_file, 'w') as f:
    json.dump([batch], f, indent=2)

print("✅ Test stimuli created and written to queue")
print(f"📁 Queue file: {queue_file}")
print("\nTo process this stimuli:")
print("1. Ensure S2 AutoGen is running")
print("2. The queue consumer should pick it up automatically")
print("3. Check logs for processing results")
print("\nStimuli details:")
print(f"- ID: {test_stimuli['stimuli_id']}")
print(f"- Character: {test_stimuli['character_id']} (TRADER team)")
print(f"- Content: {test_stimuli['content']}")