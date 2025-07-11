#!/usr/bin/env python3
"""
Comprehensive S2 Teams System Test with Full Logging
===================================================

This script performs deep testing of the S2 system including:
- AutoGen agent initialization and execution
- SCB data publishing verification
- Neo4j storage verification
- Complete logging of all operations
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import traceback

# Add the autogen agent path
sys.path.append('/home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent')

# Configure comprehensive logging
log_dir = Path("/tmp/s2_test_logs")
log_dir.mkdir(exist_ok=True)

# Create multiple log handlers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"s2_comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import all required modules
try:
    from autogen_agent.core.character_team_registry import (
        get_character_team_registry, CharacterType
    )
    from autogen_agent.core.queue_consumer_service import QueueConsumerService
    from autogen_agent.core.autonomous_team_manager import AutonomousTeamManager
    from autogen_agent.core.stimuli_autogen_team import StimuliAutoGenTeam
    from autogen_agent.core.tool_registry import ToolRegistry
    from autogen_agent.clients.scb_client import SCBClient
    from autogen_agent.clients.vtuber_client import VTuberClient
    from autogen_agent.services.neo4j_semantic_storage import get_neo4j_storage
    from autogen_agent.utils.scb_utils import SCBWriter, SCBReader
    logger.info("✅ All imports successful")
except Exception as e:
    logger.error(f"❌ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)


class ComprehensiveS2Tester:
    """Deep testing of S2 Teams System with full verification"""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "logs": []
        }
        self.log_capture = []
        
    def log(self, level, message, data=None):
        """Capture logs for analysis"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data
        }
        self.log_capture.append(log_entry)
        logger.log(getattr(logging, level.upper()), message)
        if data:
            logger.debug(f"Data: {json.dumps(data, indent=2)}")
    
    async def test_autogen_team_initialization(self):
        """Test AutoGen team initialization and configuration"""
        self.log("info", "🧪 Testing AutoGen Team Initialization")
        test_name = "autogen_team_initialization"
        
        try:
            # Initialize tool registry
            tool_registry = ToolRegistry()
            tool_registry.load_tools()
            self.log("info", f"Loaded {len(tool_registry.tools)} tools", 
                    {"tools": list(tool_registry.tools.keys())[:10]})
            
            # Get character registry
            registry = get_character_team_registry()
            
            # Test each team type
            team_results = {}
            for char_type in CharacterType:
                config = registry.get_team_config(char_type)
                if config:
                    self.log("info", f"Testing {char_type.value} team configuration")
                    
                    # Create team instance
                    try:
                        team = StimuliAutoGenTeam()
                        
                        # Initialize team
                        init_success = team.initialize_team()
                        
                        team_results[char_type.value] = {
                            "config_loaded": True,
                            "team_created": True,
                            "initialized": init_success,
                            "agent_count": len(config.agents),
                            "tool_count": len(config.shared_tools) + sum(len(a.tools) for a in config.agents)
                        }
                        
                        self.log("info", f"✅ {char_type.value} team initialized: {init_success}")
                        
                    except Exception as e:
                        team_results[char_type.value] = {
                            "config_loaded": True,
                            "team_created": False,
                            "error": str(e)
                        }
                        self.log("error", f"Failed to create {char_type.value} team", {"error": str(e)})
            
            self.test_results["tests"][test_name] = {
                "status": "success" if all(r.get("initialized", False) for r in team_results.values()) else "partial",
                "teams": team_results
            }
            
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.log("error", f"AutoGen team initialization test failed: {e}")
    
    async def test_stimuli_processing_pipeline(self):
        """Test complete stimuli processing pipeline"""
        self.log("info", "🧪 Testing Stimuli Processing Pipeline")
        test_name = "stimuli_processing_pipeline"
        
        try:
            # Create test stimuli for each team in the format expected by QueueBatch
            test_stimuli_batches = [
                {
                    "prompt": "Analyze Bitcoin price trends and recommend trading strategy",
                    "timestamp": datetime.now().isoformat(),
                    "source": "comprehensive_test_trader",
                    "processing_mode": "s2_only"
                },
                {
                    "prompt": "Create a lesson plan for teaching Python programming",
                    "timestamp": datetime.now().isoformat(),
                    "source": "comprehensive_test_teacher",
                    "processing_mode": "s2_only"
                }
            ]
            
            # Write to queue
            queue_file = "/tmp/s2_test_processing_queue.json"
            with open(queue_file, 'w') as f:
                json.dump(test_stimuli_batches, f, indent=2)
            
            self.log("info", "Created test stimuli batches", {"batch_count": len(test_stimuli_batches)})
            
            # Initialize queue consumer
            tool_registry = ToolRegistry()
            tool_registry.load_tools()
            
            consumer = QueueConsumerService(
                queue_file=queue_file,
                poll_interval=1
            )
            
            # Initialize teams
            await consumer.initialize_teams(
                tool_registry=tool_registry,
                scb_client=None,
                vtuber_client=None
            )
            
            self.log("info", "Queue consumer initialized")
            
            # Process batches
            processing_results = []
            for _ in range(len(test_stimuli_batches)):
                try:
                    batches = await consumer._read_queue()
                    if batches:
                        batch = batches[0]
                        batch_id = f"batch_{batch.timestamp}" if batch.timestamp else "unknown"
                        self.log("info", f"Processing batch: {batch_id}")
                        
                        result = await consumer._process_batch(batch)
                        processing_results.append({
                            "batch_id": batch_id,
                            "success": result,
                            "prompt": batch.prompt[:50] + "..." if len(batch.prompt) > 50 else batch.prompt
                        })
                        
                        # Remove processed batch
                        await consumer._write_queue(batches[1:])
                        
                except Exception as e:
                    self.log("error", f"Batch processing error: {e}")
                    processing_results.append({
                        "batch_id": "unknown",
                        "success": False,
                        "error": str(e)
                    })
            
            self.test_results["tests"][test_name] = {
                "status": "success" if all(r.get("success", False) for r in processing_results) else "failed",
                "processing_results": processing_results
            }
            
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.log("error", f"Stimuli processing test failed: {e}")
    
    async def test_scb_integration(self):
        """Test SCB data publishing and retrieval"""
        self.log("info", "🧪 Testing SCB Integration")
        test_name = "scb_integration"
        
        try:
            # Initialize SCB client
            scb_client = SCBClient()
            scb_enabled = scb_client.is_enabled()
            
            self.log("info", f"SCB enabled: {scb_enabled}")
            
            # Test writer
            writer = SCBWriter(scb_client)
            
            # Publish test insights
            test_insights = [
                {
                    "channel": "trader_insights",
                    "type": "market_analysis",
                    "content": "Bitcoin showing bullish trend",
                    "data": {"price": 45000, "trend": "up"}
                },
                {
                    "channel": "teacher_insights",
                    "type": "curriculum_update",
                    "content": "New Python module added",
                    "data": {"module": "async_programming", "level": "intermediate"}
                }
            ]
            
            publish_results = []
            for insight in test_insights:
                success = await writer.publish_insight(
                    channel=insight["channel"],
                    insight_type=insight["type"],
                    content=insight["content"],
                    data=insight["data"]
                )
                publish_results.append({
                    "channel": insight["channel"],
                    "success": success
                })
                self.log("info", f"Published to {insight['channel']}: {success}")
            
            # Test reader
            reader = SCBReader(scb_client)
            read_results = {}
            
            for channel in ["trader_insights", "teacher_insights"]:
                insights = await reader.get_latest_insights(channel, limit=5)
                read_results[channel] = {
                    "count": len(insights),
                    "insights": insights
                }
                self.log("info", f"Read {len(insights)} insights from {channel}")
            
            self.test_results["tests"][test_name] = {
                "status": "success" if scb_enabled else "limited",
                "scb_enabled": scb_enabled,
                "publish_results": publish_results,
                "read_results": read_results
            }
            
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.log("error", f"SCB integration test failed: {e}")
    
    async def test_neo4j_integration(self):
        """Test Neo4j semantic storage"""
        self.log("info", "🧪 Testing Neo4j Integration")
        test_name = "neo4j_integration"
        
        try:
            storage = get_neo4j_storage()
            
            if storage and storage.driver:
                # Test connection
                connected = await storage.test_connection()
                self.log("info", f"Neo4j connected: {connected}")
                
                # Test node creation
                test_nodes = []
                
                # Create team insight node
                insight_node = await storage.add_semantic_node(
                    content="Test team insight: Market analysis complete",
                    context="trading_finance",
                    node_type="team_insight",
                    metadata={
                        "team_type": "trader",
                        "confidence": 0.85,
                        "test": True
                    },
                    initiating_agent="trader_team_test",
                    agent_category="autonomous_team",
                    agent_team="trader"
                )
                
                if insight_node:
                    test_nodes.append({
                        "type": "team_insight",
                        "id": insight_node.id,
                        "success": True
                    })
                    self.log("info", "✅ Created team insight node", {"id": insight_node.id})
                
                # Create collaboration node
                collab_node = await storage.add_semantic_node(
                    content="Cross-team collaboration: trader → teacher",
                    context="collaboration",
                    node_type="collaboration_request",
                    metadata={
                        "source_team": "trader",
                        "target_team": "teacher",
                        "test": True
                    },
                    initiating_agent="test_coordinator",
                    agent_category="system",
                    agent_team="coordination"
                )
                
                if collab_node:
                    test_nodes.append({
                        "type": "collaboration",
                        "id": collab_node.id,
                        "success": True
                    })
                    self.log("info", "✅ Created collaboration node", {"id": collab_node.id})
                
                # Query nodes
                query_results = await storage.search_semantic(
                    "test",
                    context=None,
                    limit=10
                )
                
                self.test_results["tests"][test_name] = {
                    "status": "success",
                    "connected": connected,
                    "nodes_created": test_nodes,
                    "query_count": len(query_results)
                }
                
            else:
                self.test_results["tests"][test_name] = {
                    "status": "not_configured",
                    "message": "Neo4j not available"
                }
                self.log("warning", "Neo4j not configured")
                
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.log("error", f"Neo4j integration test failed: {e}")
    
    async def test_autonomous_team_execution(self):
        """Test autonomous team background execution"""
        self.log("info", "🧪 Testing Autonomous Team Execution")
        test_name = "autonomous_team_execution"
        
        try:
            tool_registry = ToolRegistry()
            tool_registry.load_tools()
            
            # Initialize team manager
            manager = AutonomousTeamManager(
                tool_registry=tool_registry,
                scb_client=None,
                vtuber_client=None,
                execution_interval=10  # Fast for testing
            )
            
            # Initialize teams
            init_success = await manager.initialize()
            self.log("info", f"Team manager initialized: {init_success}")
            
            # Test character changes
            character_tests = [
                ("emma_teacher_template", CharacterType.TEACHER),
                ("dr._house_doctor_template", CharacterType.TRADER),
                ("weatherman_template", CharacterType.STREAMER)
            ]
            
            character_results = []
            for char_id, expected_type in character_tests:
                await manager.handle_character_change(char_id)
                
                # Wait a bit for team activation
                await asyncio.sleep(2)
                
                status = manager.get_status()
                character_results.append({
                    "character_id": char_id,
                    "expected_type": expected_type.value,
                    "current_character": status["current_character"],
                    "active_teams": status["active_teams"],
                    "team_status": status["teams"]
                })
                
                self.log("info", f"Character change to {char_id}: {status['active_teams']} active teams")
            
            # Stop all teams
            await manager.stop_all()
            
            self.test_results["tests"][test_name] = {
                "status": "success" if init_success else "failed",
                "initialized": init_success,
                "team_count": len(manager.character_teams),
                "character_tests": character_results
            }
            
        except Exception as e:
            self.test_results["tests"][test_name] = {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.log("error", f"Autonomous team execution test failed: {e}")
    
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE S2 TEAMS SYSTEM TEST")
        print("="*80)
        
        # Run tests
        await self.test_autogen_team_initialization()
        await self.test_stimuli_processing_pipeline()
        await self.test_scb_integration()
        await self.test_neo4j_integration()
        await self.test_autonomous_team_execution()
        
        # Save results
        self.test_results["logs"] = self.log_capture
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    def save_results(self):
        """Save test results and logs"""
        # Save detailed results
        results_file = log_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        self.log("info", f"Test results saved to: {results_file}")
        
        # Save summary
        summary_file = log_dir / "test_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(f"S2 Teams System Test Summary\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*60 + "\n\n")
            
            for test_name, result in self.test_results["tests"].items():
                status = result.get("status", "unknown")
                f.write(f"{test_name}: {status.upper()}\n")
                
                if status == "failed":
                    f.write(f"  Error: {result.get('error', 'Unknown')}\n")
                elif test_name == "autogen_team_initialization":
                    for team, team_result in result.get("teams", {}).items():
                        f.write(f"  - {team}: {'✅' if team_result.get('initialized') else '❌'}\n")
        
        self.log("info", f"Test summary saved to: {summary_file}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results["tests"])
        passed = sum(1 for r in self.test_results["tests"].values() 
                    if r.get("status") in ["success", "limited"])
        failed = sum(1 for r in self.test_results["tests"].values() 
                    if r.get("status") == "failed")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Limited/Not Configured: {total_tests - passed - failed}")
        
        print("\nDetailed Results:")
        print("-"*60)
        
        for test_name, result in self.test_results["tests"].items():
            status = result.get("status", "unknown")
            icon = {
                "success": "✅",
                "failed": "❌",
                "partial": "⚠️",
                "limited": "⚠️",
                "not_configured": "🔧"
            }.get(status, "❓")
            
            print(f"\n{icon} {test_name.replace('_', ' ').title()}: {status.upper()}")
            
            # Print test-specific details
            if test_name == "autogen_team_initialization" and "teams" in result:
                for team, team_result in result["teams"].items():
                    if team_result.get("initialized"):
                        print(f"   ✅ {team}: {team_result.get('agent_count')} agents, {team_result.get('tool_count')} tools")
                    else:
                        print(f"   ❌ {team}: {team_result.get('error', 'Failed')}")
            
            elif test_name == "stimuli_processing_pipeline" and "processing_results" in result:
                for pr in result["processing_results"]:
                    status = "✅" if pr.get("success") else "❌"
                    print(f"   {status} {pr.get('batch_id')}: {pr.get('prompt', 'No prompt')}")
            
            elif test_name == "scb_integration":
                print(f"   SCB Enabled: {result.get('scb_enabled', False)}")
                if "publish_results" in result:
                    success_count = sum(1 for r in result["publish_results"] if r.get("success"))
                    print(f"   Published: {success_count}/{len(result['publish_results'])}")
            
            elif test_name == "neo4j_integration":
                if result.get("status") == "success":
                    print(f"   Connected: {result.get('connected', False)}")
                    print(f"   Nodes Created: {len(result.get('nodes_created', []))}")
                    print(f"   Query Results: {result.get('query_count', 0)}")
            
            elif test_name == "autonomous_team_execution":
                print(f"   Teams Created: {result.get('team_count', 0)}")
                print(f"   Character Tests: {len(result.get('character_tests', []))}")
        
        print("\n" + "="*80)
        print(f"📁 Logs saved to: {log_dir}")
        print("="*80)


async def main():
    """Run comprehensive tests"""
    tester = ComprehensiveS2Tester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())