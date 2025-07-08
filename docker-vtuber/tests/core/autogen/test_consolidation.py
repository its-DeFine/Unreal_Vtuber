#!/usr/bin/env python3
"""
Test script for the new Stimuli Consolidation System

This script tests the basic functionality of the capacity monitor and consolidator
to ensure they work correctly before integration with the main system.
"""

import asyncio
import logging
import json
from datetime import datetime
import sys
import os

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autogen_agent.capacity_monitor import CapacityMonitor, CapacityStatus
from autogen_agent.stimuli_consolidator import StimuliConsolidator, ConsolidationStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_capacity_monitor():
    """Test the capacity monitoring system"""
    logger.info("🧪 Testing Capacity Monitor")
    
    # Create capacity monitor
    monitor = CapacityMonitor(
        s1_endpoint="http://localhost:5001",  # Will fail, but that's expected in test
        monitoring_interval=1.0
    )
    
    # Start monitoring
    await monitor.start_monitoring()
    
    # Let it run for a few seconds
    await asyncio.sleep(3)
    
    # Check status
    status = monitor.get_combined_capacity()
    logger.info(f"Capacity Status: {json.dumps(status, indent=2)}")
    
    # Test S2 discussion tracking
    monitor.register_s2_discussion_start("test_discussion_1")
    await asyncio.sleep(1)
    
    status = monitor.get_combined_capacity()
    logger.info(f"Status with S2 discussion: {json.dumps(status, indent=2)}")
    
    monitor.register_s2_discussion_end("test_discussion_1")
    await asyncio.sleep(1)
    
    # Stop monitoring
    await monitor.stop_monitoring()
    
    logger.info("✅ Capacity Monitor test completed")
    return monitor


async def test_consolidator(capacity_monitor):
    """Test the consolidation system"""
    logger.info("🧪 Testing Consolidator")
    
    # Create consolidator
    consolidator = StimuliConsolidator(
        capacity_monitor=capacity_monitor,
        max_batch_size=3,
        batch_timeout=2.0
    )
    
    # Start processing
    await consolidator.start_processing()
    
    # Add some test stimuli
    test_stimuli = [
        {
            "content": "Test message 1 about system performance",
            "source": "test_system",
            "priority": "medium",
            "category": "system",
            "metadata": {"test": True}
        },
        {
            "content": "Test message 2 about system optimization", 
            "source": "test_system",
            "priority": "medium",
            "category": "system",
            "metadata": {"test": True}
        },
        {
            "content": "High priority alert message",
            "source": "alert_system",
            "priority": "high",
            "category": "alert",
            "metadata": {"test": True}
        }
    ]
    
    # Add stimuli
    stimuli_ids = []
    for stimuli in test_stimuli:
        stimuli_id = await consolidator.add_stimuli(stimuli)
        stimuli_ids.append(stimuli_id)
        logger.info(f"Added stimuli: {stimuli_id}")
        await asyncio.sleep(0.5)
    
    # Let consolidator process for a bit
    await asyncio.sleep(5)
    
    # Check status
    status = consolidator.get_status()
    logger.info(f"Consolidator Status: {json.dumps(status, indent=2, default=str)}")
    
    # Stop processing
    await consolidator.stop_processing()
    
    logger.info("✅ Consolidator test completed")
    return consolidator


async def test_integration():
    """Test integration between components"""
    logger.info("🧪 Testing Integration")
    
    # Create monitor
    monitor = CapacityMonitor(
        s1_endpoint="http://localhost:5001",
        monitoring_interval=0.5
    )
    await monitor.start_monitoring()
    
    # Create consolidator
    consolidator = StimuliConsolidator(
        capacity_monitor=monitor,
        max_batch_size=2,
        batch_timeout=1.5
    )
    await consolidator.start_processing()
    
    # Simulate rapid stimuli arrival
    rapid_stimuli = []
    for i in range(5):
        stimuli = {
            "content": f"Rapid stimuli {i+1} - urgent task",
            "source": "rapid_test",
            "priority": "high" if i % 2 == 0 else "medium",
            "category": "urgent",
            "metadata": {"batch": "rapid", "index": i}
        }
        rapid_stimuli.append(stimuli)
    
    # Add them quickly
    for stimuli in rapid_stimuli:
        await consolidator.add_stimuli(stimuli)
        await asyncio.sleep(0.2)  # Quick succession
    
    # Wait for processing
    await asyncio.sleep(4)
    
    # Check final status
    consolidator_status = consolidator.get_detailed_status()
    capacity_status = monitor.get_detailed_status()
    
    logger.info("📊 Final Integration Status:")
    logger.info(f"Consolidator: {json.dumps(consolidator_status, indent=2, default=str)}")
    logger.info(f"Capacity Monitor: {json.dumps(capacity_status, indent=2, default=str)}")
    
    # Cleanup
    await consolidator.stop_processing()
    await monitor.stop_monitoring()
    
    logger.info("✅ Integration test completed")


async def run_all_tests():
    """Run all consolidation tests"""
    logger.info("🚀 Starting Consolidation System Tests")
    
    try:
        # Test 1: Capacity Monitor
        monitor = await test_capacity_monitor()
        
        # Test 2: Consolidator
        consolidator = await test_consolidator(monitor)
        
        # Test 3: Integration
        await test_integration()
        
        logger.info("🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    logger.info("🧪 Consolidation System Test Suite")
    asyncio.run(run_all_tests())