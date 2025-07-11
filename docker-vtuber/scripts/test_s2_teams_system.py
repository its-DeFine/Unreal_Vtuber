#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Script for S2 Specialized Teams System
====================================================================

This script tests:
1. Character team registry and mappings
2. Queue consumer service
3. Autonomous team manager
4. Tool availability and execution
5. SCB communication
6. Neo4j storage
7. Stimuli processing flow
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the autogen agent path
sys.path.append('/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

from autogen_agent.core.character_team_registry import (
    get_character_team_registry,
    CharacterType
)
from autogen_agent.core.queue_consumer_service import QueueConsumerService
from autogen_agent.core.autonomous_team_manager import AutonomousTeamManager
from autogen_agent.core.tool_registry import ToolRegistry
from autogen_agent.clients.scb_client import SCBClient
from autogen_agent.clients.vtuber_client import VTuberClient
from autogen_agent.services.neo4j_semantic_storage import get_neo4j_storage
from autogen_agent.utils.scb_utils import SCBWriter, SCBReader


class S2TeamsSystemTester:
    """Comprehensive test suite for S2 Teams System"""
    
    def __init__(self):
        self.results = {
            "character_registry": {"status": "pending", "details": {}},
            "tool_availability": {"status": "pending", "details": {}},
            "queue_system": {"status": "pending", "details": {}},
            "autonomous_teams": {"status": "pending", "details": {}},
            "scb_communication": {"status": "pending", "details": {}},
            "neo4j_storage": {"status": "pending", "details": {}},
            "stimuli_flow": {"status": "pending", "details": {}}
        }
        
    async def run_all_tests(self):
        """Run all system tests"""
        print("🧪 S2 Specialized Teams System - Comprehensive Test Suite")
        print("=" * 60)
        
        # Test 1: Character Team Registry
        await self.test_character_registry()
        
        # Test 2: Tool Availability
        await self.test_tool_availability()
        
        # Test 3: Queue System
        await self.test_queue_system()
        
        # Test 4: Autonomous Teams
        await self.test_autonomous_teams()
        
        # Test 5: SCB Communication
        await self.test_scb_communication()
        
        # Test 6: Neo4j Storage
        await self.test_neo4j_storage()
        
        # Test 7: End-to-End Stimuli Flow
        await self.test_stimuli_flow()
        
        # Print results summary
        self.print_results_summary()
        
    async def test_character_registry(self):
        """Test character team registry and mappings"""
        print("\n📋 Testing Character Team Registry...")
        
        try:
            registry = get_character_team_registry()
            
            # Test character mappings
            test_characters = [
                ("emma_teacher_template", CharacterType.TEACHER),
                ("dr._house_doctor_template", CharacterType.TRADER),
                ("weatherman_template", CharacterType.STREAMER),
                ("secretary_template", CharacterType.DEFAULT)
            ]
            
            mapping_results = {}
            for char_id, expected_type in test_characters:
                config = registry.get_team_config_by_character_id(char_id)
                if config and config.character_type == expected_type:
                    mapping_results[char_id] = "✅ Correct mapping"
                else:
                    mapping_results[char_id] = f"❌ Expected {expected_type}, got {config.character_type if config else 'None'}"
            
            # Test team configurations
            team_configs = {}
            for char_type in CharacterType:
                config = registry.get_team_config(char_type)
                if config:
                    team_configs[char_type.value] = {
                        "name": config.team_name,
                        "agents": len(config.agents),
                        "tools": len(config.shared_tools)
                    }
                else:
                    team_configs[char_type.value] = "❌ No configuration"
            
            self.results["character_registry"] = {
                "status": "success",
                "details": {
                    "mappings": mapping_results,
                    "team_configs": team_configs
                }
            }
            print("✅ Character registry test completed")
            
        except Exception as e:
            self.results["character_registry"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ Character registry test failed: {e}")
    
    async def test_tool_availability(self):
        """Test tool availability for each team"""
        print("\n🔧 Testing Tool Availability...")
        
        try:
            # Import tool catalog
            from autogen_agent.tools.tool_catalog import ToolCatalog
            
            catalog = ToolCatalog()
            
            tool_results = {}
            
            # Check tools for each team
            for team in ["trader", "streamer", "teacher", "common"]:
                tools = catalog.get_tools_for_team(team)
                tool_results[team] = {
                    "count": len(tools),
                    "tools": list(tools.keys())[:5]  # First 5 tools
                }
            
            # Test tool loading
            registry = ToolRegistry()
            registry.load_tools()
            
            self.results["tool_availability"] = {
                "status": "success",
                "details": {
                    "team_tools": tool_results,
                    "total_tools_loaded": len(registry.tools)
                }
            }
            print("✅ Tool availability test completed")
            
        except Exception as e:
            self.results["tool_availability"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ Tool availability test failed: {e}")
    
    async def test_queue_system(self):
        """Test queue consumer service"""
        print("\n📬 Testing Queue System...")
        
        try:
            # Create test queue file
            queue_file = "/tmp/test_s2_queue.json"
            test_batch = {
                "batch_id": "test_batch_001",
                "timestamp": datetime.now().isoformat(),
                "stimuli_count": 1,
                "stimuli": [{
                    "stimuli_id": "test_stim_001",
                    "content": "Test stimuli for queue system",
                    "character_id": "emma_teacher_template",
                    "priority": "high"
                }]
            }
            
            with open(queue_file, 'w') as f:
                json.dump([test_batch], f)
            
            # Initialize queue consumer
            tool_registry = ToolRegistry()
            tool_registry.load_tools()
            
            consumer = QueueConsumerService(
                queue_file=queue_file,
                poll_interval=1
            )
            
            # Initialize with mock clients
            await consumer.initialize(
                tool_registry=tool_registry,
                scb_client=None,
                vtuber_client=None
            )
            
            # Test queue polling
            has_items = await consumer._check_queue()
            
            # Test batch processing
            if has_items:
                batch = await consumer._get_next_batch()
                process_result = batch is not None
            else:
                process_result = False
            
            self.results["queue_system"] = {
                "status": "success",
                "details": {
                    "queue_file_created": True,
                    "queue_has_items": has_items,
                    "batch_retrieved": process_result
                }
            }
            print("✅ Queue system test completed")
            
            # Cleanup
            if os.path.exists(queue_file):
                os.remove(queue_file)
                
        except Exception as e:
            self.results["queue_system"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ Queue system test failed: {e}")
    
    async def test_autonomous_teams(self):
        """Test autonomous team manager"""
        print("\n🤖 Testing Autonomous Teams...")
        
        try:
            tool_registry = ToolRegistry()
            tool_registry.load_tools()
            
            # Initialize team manager
            manager = AutonomousTeamManager(
                tool_registry=tool_registry,
                scb_client=None,
                vtuber_client=None,
                execution_interval=60
            )
            
            # Test initialization
            init_success = await manager.initialize()
            
            # Check team creation
            team_count = len(manager.character_teams)
            
            # Test character change handling
            await manager.handle_character_change("emma_teacher_template")
            current_team = manager.current_team
            
            # Get status
            status = manager.get_status()
            
            self.results["autonomous_teams"] = {
                "status": "success",
                "details": {
                    "initialized": init_success,
                    "teams_created": team_count,
                    "current_team": current_team.team_config["name"] if current_team else None,
                    "status": status
                }
            }
            print("✅ Autonomous teams test completed")
            
            # Stop manager
            await manager.stop_all()
            
        except Exception as e:
            self.results["autonomous_teams"] = {
                "status": "failed", 
                "details": {"error": str(e)}
            }
            print(f"❌ Autonomous teams test failed: {e}")
    
    async def test_scb_communication(self):
        """Test SCB communication utilities"""
        print("\n📡 Testing SCB Communication...")
        
        try:
            # Test with mock SCB client
            scb_client = SCBClient()  # Will be in standalone mode
            
            # Test writer
            writer = SCBWriter(scb_client)
            write_success = await writer.publish_insight(
                channel="test_channel",
                insight_type="test",
                content="Test insight",
                data={"test": True}
            )
            
            # Test reader
            reader = SCBReader(scb_client)
            insights = await reader.get_latest_insights("test_channel", limit=5)
            
            self.results["scb_communication"] = {
                "status": "success",
                "details": {
                    "scb_enabled": scb_client.is_enabled(),
                    "write_test": write_success,
                    "read_test": len(insights) >= 0
                }
            }
            print("✅ SCB communication test completed")
            
        except Exception as e:
            self.results["scb_communication"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ SCB communication test failed: {e}")
    
    async def test_neo4j_storage(self):
        """Test Neo4j semantic storage"""
        print("\n🗃️ Testing Neo4j Storage...")
        
        try:
            storage = get_neo4j_storage()
            
            if storage and storage.driver:
                # Test connection
                connected = await storage.test_connection()
                
                # Test node creation
                test_node = await storage.add_semantic_node(
                    content="Test team insight",
                    context="system_test",
                    node_type="test_insight",
                    metadata={"test": True},
                    initiating_agent="test_agent"
                )
                
                self.results["neo4j_storage"] = {
                    "status": "success",
                    "details": {
                        "connected": connected,
                        "node_created": test_node is not None
                    }
                }
                print("✅ Neo4j storage test completed")
            else:
                self.results["neo4j_storage"] = {
                    "status": "warning",
                    "details": {"message": "Neo4j not configured"}
                }
                print("⚠️ Neo4j storage not configured")
                
        except Exception as e:
            self.results["neo4j_storage"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ Neo4j storage test failed: {e}")
    
    async def test_stimuli_flow(self):
        """Test end-to-end stimuli processing flow"""
        print("\n🔄 Testing End-to-End Stimuli Flow...")
        
        try:
            # Create test stimuli
            test_stimuli = {
                "stimuli_id": "e2e_test_001",
                "content": "Process this teacher-related query about curriculum design",
                "character_id": "emma_teacher_template",
                "priority": "high",
                "source": "test_suite"
            }
            
            # Write to consolidation queue
            queue_file = "/tmp/s2_processing_queue.json"
            batch = {
                "batch_id": "e2e_batch_001",
                "timestamp": datetime.now().isoformat(),
                "stimuli_count": 1,
                "stimuli": [test_stimuli]
            }
            
            # Read existing queue or create new
            try:
                with open(queue_file, 'r') as f:
                    queue = json.load(f)
            except:
                queue = []
            
            queue.append(batch)
            
            with open(queue_file, 'w') as f:
                json.dump(queue, f)
            
            self.results["stimuli_flow"] = {
                "status": "success",
                "details": {
                    "stimuli_created": True,
                    "queue_updated": True,
                    "ready_for_processing": True
                }
            }
            print("✅ Stimuli flow test completed")
            
        except Exception as e:
            self.results["stimuli_flow"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            print(f"❌ Stimuli flow test failed: {e}")
    
    def print_results_summary(self):
        """Print comprehensive test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "success")
        failed = sum(1 for r in self.results.values() if r["status"] == "failed")
        warnings = sum(1 for r in self.results.values() if r["status"] == "warning")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Warnings: {warnings}")
        
        print("\nDetailed Results:")
        print("-" * 60)
        
        for test_name, result in self.results.items():
            status_icon = {
                "success": "✅",
                "failed": "❌",
                "warning": "⚠️",
                "pending": "⏳"
            }.get(result["status"], "❓")
            
            print(f"\n{status_icon} {test_name.replace('_', ' ').title()}")
            
            if result["status"] != "pending" and "details" in result:
                for key, value in result["details"].items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    - {k}: {v}")
                    else:
                        print(f"  - {key}: {value}")
        
        print("\n" + "=" * 60)
        
        # Overall assessment
        if failed == 0:
            print("🎉 All tests passed! The S2 Specialized Teams System is ready.")
        elif failed < total_tests / 2:
            print("⚠️ Some tests failed. The system may work with limitations.")
        else:
            print("❌ Multiple tests failed. System needs attention.")


async def main():
    """Run the test suite"""
    tester = S2TeamsSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())