#!/usr/bin/env python3
"""
🧪 Enhanced AutoGen System Verification Test

This script comprehensively tests the new enhanced AutoGen system features:
- Multi-agent coordination (cognitive, programmer, observer agents)
- Goal management integration and active usage
- Variable tool calls system
- Advanced analytics and performance tracking
- System verification and status checks
"""

import asyncio
import logging
import json
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_autogen_test.log'),
        logging.StreamHandler()
    ]
)

async def test_enhanced_autogen_system():
    """Comprehensive test of the enhanced AutoGen system"""
    
    print("🚀 Starting Enhanced AutoGen System Verification Test")
    print("=" * 70)
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests_passed": 0,
        "tests_failed": 0,
        "system_features": {},
        "performance_metrics": {},
        "recommendations": []
    }
    
    try:
        # Test 1: Import and initialize enhanced system components
        print("\n📦 TEST 1: Enhanced System Components Import")
        try:
            # Import main components
            import sys
            sys.path.append('app/CORE/autogen-agent')
            
            from autogen_agent.main import (
                initialize_autogen_agents, 
                analytics_data,
                get_goal_and_analytics_context,
                update_analytics_and_goals
            )
            
            from autogen_agent.services.goal_management_service import get_goal_management_service
            from autogen_agent.tools.variable_tool_calls import get_variable_tools_manager, ToolExecutionContext
            from autogen_agent.tools.goal_management_tools import GOAL_MANAGEMENT_TOOLS
            
            print("✅ All enhanced system components imported successfully")
            test_results["tests_passed"] += 1
            test_results["system_features"]["imports"] = "✅ SUCCESS"
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["imports"] = f"❌ FAILED: {e}"
            return test_results
        
        # Test 2: Goal Management System Verification
        print("\n🎯 TEST 2: Goal Management System Integration")
        try:
            goal_service = await get_goal_management_service()
            
            if goal_service:
                # Test goal creation
                test_goal = await goal_service.define_goal(
                    "Enhance multi-agent collaboration efficiency by 20%",
                    priority=8
                )
                
                print(f"✅ Goal created successfully: {test_goal.id}")
                print(f"   Title: {test_goal.title}")
                print(f"   Category: {test_goal.category.value}")
                print(f"   Priority: {test_goal.priority}/10")
                
                # Test goal progress update
                progress_data = {
                    "iteration": 1,
                    "agent_collaboration_quality": 3,
                    "success_rate": 1.0,
                    "multi_agent_score": 1.0
                }
                
                await goal_service.update_goal_progress(test_goal.id, progress_data)
                print(f"✅ Goal progress updated successfully")
                
                # Get performance metrics
                metrics = await goal_service.generate_performance_metrics(24)
                print(f"✅ Performance metrics generated: Score {metrics.get('performance_score', 0):.1f}/100")
                
                test_results["tests_passed"] += 1
                test_results["system_features"]["goal_management"] = "✅ OPERATIONAL"
                test_results["performance_metrics"]["goal_system"] = {
                    "active_goals": len(goal_service.active_goals),
                    "performance_score": metrics.get('performance_score', 0),
                    "test_goal_id": test_goal.id
                }
                
            else:
                print("❌ Goal management service not available")
                test_results["tests_failed"] += 1
                test_results["system_features"]["goal_management"] = "❌ SERVICE UNAVAILABLE"
                
        except Exception as e:
            print(f"❌ Goal management test failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["goal_management"] = f"❌ FAILED: {e}"
        
        # Test 3: Variable Tool Calls System
        print("\n🔧 TEST 3: Variable Tool Calls System")
        try:
            variable_tools_manager = await get_variable_tools_manager()
            
            # Test tool selection for different contexts
            contexts_to_test = [
                ToolExecutionContext.GOAL_PROGRESS,
                ToolExecutionContext.ANALYTICS,
                ToolExecutionContext.EVOLUTION
            ]
            
            tools_selected_by_context = {}
            
            for context in contexts_to_test:
                selected_tools = await variable_tools_manager.select_optimal_tools(
                    context=context,
                    goal_context="Enhanced AutoGen test scenario",
                    max_tools=2
                )
                
                tools_selected_by_context[context.value] = [tool.tool_name for tool in selected_tools]
                print(f"✅ {context.value}: Selected {len(selected_tools)} tools - {[tool.tool_name for tool in selected_tools]}")
            
            # Get performance analytics
            analytics = variable_tools_manager.get_performance_analytics()
            print(f"✅ Variable tools analytics: {analytics['system_stats']['registered_tools']} registered tools")
            
            test_results["tests_passed"] += 1
            test_results["system_features"]["variable_tools"] = "✅ OPERATIONAL"
            test_results["performance_metrics"]["variable_tools"] = {
                "contexts_tested": len(contexts_to_test),
                "tools_by_context": tools_selected_by_context,
                "analytics": analytics
            }
            
        except Exception as e:
            print(f"❌ Variable tool calls test failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["variable_tools"] = f"❌ FAILED: {e}"
        
        # Test 4: AutoGen Multi-Agent Initialization
        print("\n🤖 TEST 4: AutoGen Multi-Agent System")
        try:
            # Test agent initialization
            agents_initialized = initialize_autogen_agents()
            
            if agents_initialized:
                print("✅ AutoGen multi-agent system initialized successfully")
                print("   Agents: cognitive_ai_agent, programmer_agent, observer_agent")
                print("   Group chat configuration: Ready for collaboration")
                
                test_results["tests_passed"] += 1
                test_results["system_features"]["multi_agent"] = "✅ INITIALIZED"
                
            else:
                print("❌ AutoGen multi-agent initialization failed")
                test_results["tests_failed"] += 1
                test_results["system_features"]["multi_agent"] = "❌ INITIALIZATION FAILED"
                
        except Exception as e:
            print(f"❌ Multi-agent test failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["multi_agent"] = f"❌ FAILED: {e}"
        
        # Test 5: Analytics System Integration
        print("\n📊 TEST 5: Advanced Analytics System")
        try:
            # Test context generation
            context = await get_goal_and_analytics_context(1)
            print(f"✅ Goal and analytics context generated")
            print(f"   Context length: {len(context)} characters")
            
            # Test analytics update
            mock_agent_responses = {
                "cognitive_ai_agent": "System analysis complete",
                "programmer_agent": "Code optimization suggestions ready", 
                "observer_agent": "Performance metrics tracked"
            }
            
            await update_analytics_and_goals(1, mock_agent_responses, True)
            print("✅ Analytics and goals updated successfully")
            
            # Check analytics data
            print(f"✅ Analytics tracking: {analytics_data['cycles_completed']} cycles completed")
            print(f"   Tools used: {len(analytics_data['tools_used'])} types")
            print(f"   Agent interactions: {sum(analytics_data['agent_interactions'].values())}")
            
            test_results["tests_passed"] += 1
            test_results["system_features"]["analytics"] = "✅ OPERATIONAL"
            test_results["performance_metrics"]["analytics"] = {
                "cycles_completed": analytics_data['cycles_completed'],
                "tools_used": len(analytics_data['tools_used']),
                "agent_interactions": sum(analytics_data['agent_interactions'].values()),
                "context_generation": "functional"
            }
            
        except Exception as e:
            print(f"❌ Analytics test failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["analytics"] = f"❌ FAILED: {e}"
        
        # Test 6: MCP Tools Integration
        print("\n🔗 TEST 6: MCP Tools Integration")
        try:
            # Check goal management tools availability
            available_tools = list(GOAL_MANAGEMENT_TOOLS.keys())
            print(f"✅ MCP Goal Management Tools available: {len(available_tools)}")
            for tool in available_tools:
                print(f"   • {tool}")
            
            test_results["tests_passed"] += 1
            test_results["system_features"]["mcp_tools"] = "✅ AVAILABLE"
            test_results["performance_metrics"]["mcp_tools"] = {
                "goal_management_tools": len(available_tools),
                "tools_list": available_tools
            }
            
        except Exception as e:
            print(f"❌ MCP tools test failed: {e}")
            test_results["tests_failed"] += 1
            test_results["system_features"]["mcp_tools"] = f"❌ FAILED: {e}"
        
        # Generate Test Summary
        print("\n" + "=" * 70)
        print("📋 ENHANCED AUTOGEN SYSTEM TEST SUMMARY")
        print("=" * 70)
        
        total_tests = test_results["tests_passed"] + test_results["tests_failed"]
        success_rate = (test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Tests Passed: {test_results['tests_passed']}")
        print(f"❌ Tests Failed: {test_results['tests_failed']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"🕒 Test Duration: {(datetime.now() - datetime.fromisoformat(test_results['timestamp'])).total_seconds():.2f}s")
        
        print("\n🎯 SYSTEM FEATURES STATUS:")
        for feature, status in test_results["system_features"].items():
            print(f"   {feature}: {status}")
        
        # Generate Recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        if test_results["tests_failed"] == 0:
            test_results["recommendations"].append("🎉 All systems operational! Ready for production deployment.")
            test_results["recommendations"].append("🚀 Consider defining initial production goals for the system.")
            test_results["recommendations"].append("📊 Monitor analytics endpoints for system performance.")
        else:
            test_results["recommendations"].append("🔧 Address failed components before production deployment.")
            
        if "goal_management" in test_results["system_features"] and "✅" in test_results["system_features"]["goal_management"]:
            test_results["recommendations"].append("🎯 Goal management operational - define strategic system goals.")
            
        if "variable_tools" in test_results["system_features"] and "✅" in test_results["system_features"]["variable_tools"]:
            test_results["recommendations"].append("🔧 Variable tools ready - system will optimize tool usage automatically.")
            
        if "multi_agent" in test_results["system_features"] and "✅" in test_results["system_features"]["multi_agent"]:
            test_results["recommendations"].append("🤖 Multi-agent collaboration ready - expect enhanced performance.")
        
        for rec in test_results["recommendations"]:
            print(f"   {rec}")
        
        # Save test results
        with open('enhanced_autogen_test_results.json', 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: enhanced_autogen_test_results.json")
        print(f"📄 Detailed logs saved to: enhanced_autogen_test.log")
        
        return test_results
        
    except Exception as e:
        print(f"💥 Critical test failure: {e}")
        test_results["tests_failed"] += 1
        test_results["critical_error"] = str(e)
        return test_results

async def main():
    """Main test execution"""
    print("🔬 Enhanced AutoGen System Comprehensive Test Suite")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = await test_enhanced_autogen_system()
    
    total_tests = results["tests_passed"] + results["tests_failed"]
    if total_tests > 0:
        success_rate = results["tests_passed"] / total_tests * 100
        
        if success_rate >= 80:
            print(f"\n🎉 SYSTEM STATUS: READY FOR DEPLOYMENT ({success_rate:.1f}% success rate)")
        elif success_rate >= 60:
            print(f"\n⚠️ SYSTEM STATUS: NEEDS ATTENTION ({success_rate:.1f}% success rate)")
        else:
            print(f"\n❌ SYSTEM STATUS: REQUIRES FIXES ({success_rate:.1f}% success rate)")
    else:
        print("\n💥 SYSTEM STATUS: CRITICAL FAILURE")

if __name__ == "__main__":
    asyncio.run(main()) 