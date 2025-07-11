#!/usr/bin/env python3
"""
S2 Teams System Integration Test
================================

Simple integration test to verify the system processes stimuli correctly.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append('/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

from autogen_agent.core.character_team_registry import get_character_team_registry
from autogen_agent.core.queue_consumer_service import QueueConsumerService
from autogen_agent.core.tool_registry import ToolRegistry


async def main():
    print("🧪 S2 Teams Integration Test")
    print("=" * 40)
    
    # Step 1: Create test stimuli
    print("\n1️⃣ Creating test stimuli...")
    
    test_stimuli = [
        {
            "stimuli_id": "test_trader_001",
            "content": "Analyze current market conditions and provide trading recommendations",
            "character_id": "dr._house_doctor_template",  # Maps to TRADER
            "priority": "high",
            "source": "integration_test"
        },
        {
            "stimuli_id": "test_streamer_001", 
            "content": "Create a content strategy for increasing engagement",
            "character_id": "weatherman_template",  # Maps to STREAMER
            "priority": "medium",
            "source": "integration_test"
        },
        {
            "stimuli_id": "test_teacher_001",
            "content": "Design a learning module for advanced mathematics",
            "character_id": "emma_teacher_template",  # Maps to TEACHER
            "priority": "high",
            "source": "integration_test"
        },
        {
            "stimuli_id": "test_default_001",
            "content": "Optimize system performance and identify improvement areas",
            "character_id": "secretary_template",  # Maps to DEFAULT
            "priority": "low",
            "source": "integration_test"
        }
    ]
    
    # Create batch
    batch = {
        "batch_id": "integration_test_batch_001",
        "timestamp": datetime.now().isoformat(),
        "stimuli_count": len(test_stimuli),
        "stimuli": test_stimuli
    }
    
    # Write to queue
    queue_file = "/tmp/s2_processing_queue.json"
    with open(queue_file, 'w') as f:
        json.dump([batch], f, indent=2)
    
    print(f"✅ Created {len(test_stimuli)} test stimuli")
    
    # Step 2: Verify character mappings
    print("\n2️⃣ Verifying character mappings...")
    
    registry = get_character_team_registry()
    for stimuli in test_stimuli:
        char_id = stimuli["character_id"]
        config = registry.get_team_config_by_character_id(char_id)
        if config:
            print(f"✅ {char_id} → {config.character_type.value} team")
        else:
            print(f"❌ {char_id} → No mapping found")
    
    # Step 3: Initialize queue consumer
    print("\n3️⃣ Initializing queue consumer...")
    
    tool_registry = ToolRegistry()
    tool_registry.load_tools()
    print(f"📦 Loaded {len(tool_registry.tools)} tools")
    
    consumer = QueueConsumerService(
        queue_file=queue_file,
        poll_interval=1
    )
    
    # Initialize consumer (without clients for testing)
    await consumer.initialize(
        tool_registry=tool_registry,
        scb_client=None,
        vtuber_client=None
    )
    
    print("✅ Queue consumer initialized")
    
    # Step 4: Process one batch
    print("\n4️⃣ Processing stimuli batch...")
    
    # Check if queue has items
    has_items = await consumer._check_queue()
    print(f"📬 Queue has items: {has_items}")
    
    if has_items:
        # Get and process batch
        batch = await consumer._get_next_batch()
        if batch:
            print(f"📦 Retrieved batch: {batch['batch_id']} with {batch['stimuli_count']} stimuli")
            
            # Process each stimulus
            results = []
            for stimuli in batch['stimuli']:
                print(f"\n  Processing: {stimuli['stimuli_id']} ({stimuli['character_id']})")
                try:
                    result = await consumer._process_stimulus(stimuli)
                    results.append({
                        "stimuli_id": stimuli['stimuli_id'],
                        "success": result.get("success", False),
                        "team": result.get("team_name", "unknown")
                    })
                    print(f"  ✅ Processed by: {result.get('team_name', 'unknown')}")
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:50]}...")
                    results.append({
                        "stimuli_id": stimuli['stimuli_id'],
                        "success": False,
                        "error": str(e)[:50]
                    })
    
    # Step 5: Summary
    print("\n" + "=" * 40)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 40)
    
    if 'results' in locals():
        successful = sum(1 for r in results if r.get('success', False))
        print(f"\nProcessed: {len(results)} stimuli")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {len(results) - successful}")
        
        print("\nDetails:")
        for result in results:
            status = "✅" if result.get('success') else "❌"
            team = result.get('team', result.get('error', 'unknown'))
            print(f"{status} {result['stimuli_id']}: {team}")
    else:
        print("❌ No results - batch processing failed")
    
    print("\n✨ Integration test completed")


if __name__ == "__main__":
    asyncio.run(main())