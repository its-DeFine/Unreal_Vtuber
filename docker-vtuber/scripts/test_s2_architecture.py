#!/usr/bin/env python3
"""
S2 Architecture Verification Test
=================================

This script verifies the S2 specialized teams architecture is properly implemented
without requiring actual LLM connections.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the autogen agent path
sys.path.append('/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_architecture():
    """Test the S2 specialized teams architecture"""
    
    print("\n" + "="*80)
    print("🏗️ S2 SPECIALIZED TEAMS ARCHITECTURE VERIFICATION")
    print("="*80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Test 1: Character Team Registry
    print("\n1️⃣ Testing Character Team Registry...")
    try:
        from autogen_agent.core.character_team_registry import (
            get_character_team_registry, CharacterType
        )
        
        registry = get_character_team_registry()
        
        # Verify all team types are configured
        team_configs = {}
        for char_type in CharacterType:
            config = registry.get_team_config(char_type)
            if config:
                team_configs[char_type.value] = {
                    "name": config.team_name,
                    "agents": len(config.agents),
                    "tools": len(config.shared_tools),
                    "scb_channels": len(config.scb_channels)
                }
        
        # Verify character mappings
        test_characters = [
            ("dr._house_doctor_template", CharacterType.TRADER),
            ("emma_teacher_template", CharacterType.TEACHER),
            ("weatherman_template", CharacterType.STREAMER),
            ("secretary_template", CharacterType.DEFAULT)
        ]
        
        mapping_results = []
        for char_id, expected_type in test_characters:
            config = registry.get_team_config_by_character_id(char_id)
            mapping_results.append({
                "character": char_id,
                "expected": expected_type.value,
                "actual": config.character_type.value if config else None,
                "success": config and config.character_type == expected_type
            })
        
        results["tests"].append({
            "name": "Character Team Registry",
            "success": all(r["success"] for r in mapping_results),
            "team_configs": team_configs,
            "character_mappings": mapping_results
        })
        
        print(f"✅ Registry configured with {len(team_configs)} team types")
        
    except Exception as e:
        results["tests"].append({
            "name": "Character Team Registry",
            "success": False,
            "error": str(e)
        })
        print(f"❌ Registry test failed: {e}")
    
    # Test 2: Tool Catalog
    print("\n2️⃣ Testing Tool Catalog...")
    try:
        from autogen_agent.tools.tool_catalog import ToolCatalog
        from autogen_agent.core.character_team_registry import CharacterType
        
        catalog = ToolCatalog()
        
        # Verify tools for each team
        tool_results = {}
        for char_type in CharacterType:
            tools = catalog.get_tools_for_team(char_type)
            tool_results[char_type.value] = {
                "count": len(tools),
                "tools": tools
            }
        
        results["tests"].append({
            "name": "Tool Catalog",
            "success": True,
            "tool_assignments": tool_results
        })
        
        print(f"✅ Tool catalog configured for all teams")
        
    except Exception as e:
        results["tests"].append({
            "name": "Tool Catalog",
            "success": False,
            "error": str(e)
        })
        print(f"❌ Tool catalog test failed: {e}")
    
    # Test 3: Queue Consumer Service
    print("\n3️⃣ Testing Queue Consumer Service...")
    try:
        from autogen_agent.core.queue_consumer_service import QueueConsumerService, QueueBatch
        
        # Create test queue
        test_queue_file = "/tmp/test_s2_queue.json"
        test_batch = {
            "prompt": "Test prompt",
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "processing_mode": "s2_only"
        }
        
        with open(test_queue_file, 'w') as f:
            json.dump([test_batch], f)
        
        # Initialize consumer
        consumer = QueueConsumerService(
            queue_file=test_queue_file,
            poll_interval=1
        )
        
        # Read queue
        batches = await consumer._read_queue()
        
        results["tests"].append({
            "name": "Queue Consumer Service",
            "success": len(batches) > 0,
            "batches_read": len(batches),
            "queue_file": test_queue_file
        })
        
        print(f"✅ Queue consumer can read batches")
        
        # Cleanup
        os.remove(test_queue_file)
        
    except Exception as e:
        results["tests"].append({
            "name": "Queue Consumer Service",
            "success": False,
            "error": str(e)
        })
        print(f"❌ Queue consumer test failed: {e}")
    
    # Test 4: SCB Utilities
    print("\n4️⃣ Testing SCB Utilities...")
    try:
        from autogen_agent.utils.scb_utils import SCBWriter, SCBReader, SCBCoordinator
        from autogen_agent.clients.scb_client import SCBClient
        
        # Create SCB client
        scb_client = SCBClient()
        
        # Test writer
        writer = SCBWriter(scb_client)
        
        # Test reader
        reader = SCBReader(scb_client)
        
        # Test coordinator
        coordinator = SCBCoordinator(scb_client)
        
        results["tests"].append({
            "name": "SCB Utilities",
            "success": True,
            "components": ["SCBWriter", "SCBReader", "SCBCoordinator"],
            "scb_enabled": scb_client.is_enabled()
        })
        
        print(f"✅ SCB utilities initialized (SCB enabled: {scb_client.is_enabled()})")
        
    except Exception as e:
        results["tests"].append({
            "name": "SCB Utilities",
            "success": False,
            "error": str(e)
        })
        print(f"❌ SCB utilities test failed: {e}")
    
    # Test 5: Autonomous Team Manager
    print("\n5️⃣ Testing Autonomous Team Manager...")
    try:
        from autogen_agent.core.autonomous_team_manager import (
            AutonomousTeamManager, TeamStatus, TeamExecutionContext
        )
        from autogen_agent.core.tool_registry import ToolRegistry
        
        # Initialize tool registry
        tool_registry = ToolRegistry()
        tool_registry.load_tools()
        
        # Create manager
        manager = AutonomousTeamManager(
            tool_registry=tool_registry,
            scb_client=None,
            vtuber_client=None,
            execution_interval=60
        )
        
        # Verify internal structures
        results["tests"].append({
            "name": "Autonomous Team Manager",
            "success": True,
            "components": {
                "character_teams": type(manager.character_teams).__name__,
                "execution_contexts": type(manager.execution_contexts).__name__,
                "active_tasks": type(manager.active_tasks).__name__,
                "has_scb_writer": manager.scb_writer is not None,
                "has_semantic_storage": manager.semantic_storage is not None
            }
        })
        
        print(f"✅ Autonomous team manager structure verified")
        
    except Exception as e:
        results["tests"].append({
            "name": "Autonomous Team Manager",
            "success": False,
            "error": str(e)
        })
        print(f"❌ Autonomous team manager test failed: {e}")
    
    # Test 6: Team Insight Consolidator
    print("\n6️⃣ Testing Team Insight Consolidator...")
    try:
        from autogen_agent.core.team_insight_consolidator import (
            TeamInsightConsolidator, InsightType, ConsolidationResult
        )
        
        # Create consolidator
        consolidator = TeamInsightConsolidator(
            consolidation_interval=3600,
            batch_size=50
        )
        
        # Test insight tracking
        test_insight = {
            "team_type": "trader",
            "content": "Market analysis insight",
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.85
        }
        
        await consolidator.track_insight(
            team_type="trader",
            insight_type=InsightType.ANALYSIS,
            content=test_insight["content"],
            metadata={"confidence": test_insight["confidence"]}
        )
        
        # Get pending insights
        pending = consolidator.get_pending_insights()
        
        results["tests"].append({
            "name": "Team Insight Consolidator",
            "success": True,
            "pending_insights": len(pending),
            "insight_types": [t.value for t in InsightType]
        })
        
        print(f"✅ Team insight consolidator verified")
        
    except Exception as e:
        results["tests"].append({
            "name": "Team Insight Consolidator",
            "success": False,
            "error": str(e)
        })
        print(f"❌ Team insight consolidator test failed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 ARCHITECTURE VERIFICATION SUMMARY")
    print("="*80)
    
    total_tests = len(results["tests"])
    passed_tests = sum(1 for t in results["tests"] if t["success"])
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    
    print("\n📁 Architecture Components Verified:")
    for test in results["tests"]:
        status = "✅" if test["success"] else "❌"
        print(f"  {status} {test['name']}")
    
    # Save results
    results_file = f"/tmp/s2_architecture_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    return passed_tests == total_tests


async def main():
    """Main test runner"""
    success = await test_architecture()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())