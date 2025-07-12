#!/usr/bin/env python3
"""
Send Stimuli to S2 Container Queue
==================================

This script sends stimuli to the S2 processing queue that should be
consumed by the queue consumer service in the container.
"""

import json
import os
from datetime import datetime

def send_stimuli_to_queue(content, source="external", priority="high"):
    """Send stimuli to the S2 processing queue"""
    
    # Queue file path (this should be mounted in the container)
    queue_file = "/tmp/s2_processing_queue.json"
    
    # Create batch format
    batch = {
        "prompt": content,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "processing_mode": "s2_only"
    }
    
    # Read existing queue or create new
    try:
        with open(queue_file, 'r') as f:
            queue = json.load(f)
    except:
        queue = []
    
    # Add to queue
    queue.append(batch)
    
    # Write back
    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)
    
    print(f"✅ Added stimuli to queue: {queue_file}")
    print(f"📨 Content: {content}")
    print(f"⏰ Timestamp: {batch['timestamp']}")
    print(f"📍 Queue size: {len(queue)} items")

if __name__ == "__main__":
    # Send Bitcoin analysis request
    send_stimuli_to_queue(
        content="Analyze Bitcoin price trends and recommend trading strategy",
        source="container_test",
        priority="high"
    )
    
    print("\n🔄 To process in container:")
    print("1. The container needs to run the queue consumer service")
    print("2. Mount /tmp/s2_processing_queue.json as a volume")
    print("3. The queue consumer will pick up and process through S2 teams")
    
    print("\n📋 Current architecture:")
    print("- S2 files ARE in the container ✅")
    print("- But container runs old orchestrator, not S2 teams ❌")
    print("- Need to modify container startup to initialize queue consumer")