import os
import time
import logging
import threading
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI
import uvicorn

# Import AutoGen for real multi-agent conversations
try:
    import autogen
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    AUTOGEN_AVAILABLE = True
    logging.info("✅ [MAIN] Microsoft AutoGen framework imported successfully")
except ImportError:
    AUTOGEN_AVAILABLE = False
    logging.warning("⚠️ [MAIN] Microsoft AutoGen not available - using fallback mode")

from .tool_registry import ToolRegistry
from .memory_manager import MemoryManager
from .cognitive_memory import CognitiveMemoryManager
from .cognitive_decision_engine import CognitiveDecisionEngine
from .clients.scb_client import SCBClient
from .clients.vtuber_client import VTuberClient
from .mcp_server import AutoGenMcpServer, CursorMcpToolAdapter
from .agent_tool_bridge import AgentToolBridge
from .statistics_collector import StatisticsCollector
from .services.conversation_storage_service import ConversationStorageService
from .services.pattern_storage_service import PatternStorageService
from .gpu_monitor import GPUMonitor
from .teachable_agents import create_teachable_agents, get_learning_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "20"))
app = FastAPI()

# Global AutoGen agents and group chat
autogen_assistant = None
autogen_programmer = None
autogen_observer = None
autogen_manager = None
group_chat = None

# Global MCP server instance
mcp_server = None

# Global analytics tracking
analytics_data = {
    "cycles_completed": 0,
    "tools_used": {},
    "goal_progress": {},
    "agent_interactions": {},
    "performance_trends": [],
    "decision_times": []  # Track decision times for statistics
}

# Global client instances for tool access
global_scb_client = None
global_vtuber_client = None
global_tool_registry = None

# Global statistics and storage services
statistics_collector = None
conversation_storage = None
pattern_storage = None

# Global GPU monitor instance
gpu_monitor = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "autogen_available": AUTOGEN_AVAILABLE,
        "analytics": {
            "cycles_completed": analytics_data["cycles_completed"],
            "tools_registered": len(global_tool_registry.tools) if global_tool_registry else 0
        }
    }
    
    # Add GPU status if available
    if gpu_monitor:
        try:
            gpu_summary = gpu_monitor.get_summary()
            health_data["gpu"] = gpu_summary
        except Exception as e:
            health_data["gpu"] = {"healthy": False, "error": str(e)}
    
    return health_data

@app.get("/api/test-db")
async def test_database():
    """Test database connectivity"""
    try:
        # Check if we have a database connection
        if hasattr(global_tool_registry, 'db_available'):
            return {"status": "connected", "database": "postgresql"}
        else:
            # Try a simple query
            import asyncpg
            conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
            await conn.fetchval("SELECT 1")
            await conn.close()
            return {"status": "connected", "database": "postgresql"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.post("/api/select-tool")
async def select_tool_api(request: dict):
    """API endpoint for tool selection testing"""
    if not global_tool_registry:
        return {"error": "Tool registry not initialized"}, 500
    
    context = request.get("context", "")
    # The select_tool method returns just the tool function, not scores
    # We need to get the internal selection info differently
    tool_func = global_tool_registry.select_tool(
        {"query": context, "history": []}
    )
    
    # Get the tool name from the function
    tool_name = None
    for name, func in global_tool_registry.tools.items():
        if func == tool_func:
            tool_name = name
            break
    
    # Get the last selection info from history
    if global_tool_registry.tool_usage_history:
        last_selection = global_tool_registry.tool_usage_history[-1]
        return {
            "tool": tool_name or "unknown",
            "score": last_selection.get("score", 0),
            "all_scores": last_selection.get("all_scores", {})
        }
    else:
        return {
            "tool": tool_name or "unknown",
            "score": 0,
            "all_scores": {}
        }

@app.post("/api/goals/create")
async def create_goal_api(request: dict):
    """Create a SMART goal"""
    try:
        from autogen_agent.services.goal_management_service import GoalManagementService
        goal_service = GoalManagementService()
        await goal_service.initialize()  # Initialize the service
        
        goal = await goal_service.create_goal(
            request.get("description", ""),
            request.get("category", "general")
        )
        
        return {
            "id": goal.id,
            "specific": goal.specific,
            "measurable": goal.measurable,
            "achievable": goal.achievable,
            "relevant": goal.relevant,
            "time_bound": goal.time_bound,
            "status": goal.status
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/goals/progress")
async def update_goal_progress_api(request: dict):
    """Update goal progress"""
    try:
        from autogen_agent.services.goal_management_service import GoalManagementService
        goal_service = GoalManagementService()
        
        progress = await goal_service.update_progress(
            request.get("goal_id"),
            request.get("metric_updates", {})
        )
        
        return {
            "goal_id": request.get("goal_id"),
            "progress": progress,
            "status": "updated"
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/evolution/analyze")
async def analyze_code_api(request: dict):
    """Analyze code for improvements"""
    try:
        from autogen_agent.evolution.darwin_godel_engine import DarwinGodelEngine
        # Get Cognee service if available
        cognee_service = None
        if cognitive_system and hasattr(cognitive_system, 'cognee_service'):
            cognee_service = cognitive_system.cognee_service
        
        evolution_engine = DarwinGodelEngine(cognee_service=cognee_service)
        
        # First get the file path for the target module
        target_file = f"/app/autogen_agent/{request.get('target_module', 'tool_registry')}.py"
        analysis_results = await evolution_engine.analyze_code_performance(target_file)
        
        # Convert results to expected format
        bottlenecks = []
        improvements = []
        
        if analysis_results:
            for result in analysis_results:
                bottlenecks.extend(result.performance_bottlenecks)
                improvements.extend([
                    {"id": f"imp_{i}", "description": opp} 
                    for i, opp in enumerate(result.improvement_opportunities)
                ])
        
        return {
            "bottlenecks": bottlenecks,
            "improvements": improvements,
            "metrics": {}
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/evolution/apply")
async def apply_improvement_api(request: dict):
    """Apply code improvement (simulation mode)"""
    try:
        return {
            "status": "simulated",
            "improvement_id": request.get("improvement_id"),
            "simulation_mode": request.get("simulation_mode", True),
            "changes": ["Performance optimization simulated"]
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/statistics")
async def get_statistics():
    """Get system statistics - legacy endpoint for compatibility"""
    try:
        # If we have persistent statistics, use them
        if statistics_collector:
            stats = await statistics_collector.get_statistics()
            return {
                "total_decisions": stats['total_cycles'],
                "tool_usage": {t['tool_name']: t['usage_count'] for t in stats['tool_statistics'][:10]},
                "success_rate": stats['success_rate'],
                "avg_decision_time": stats['avg_decision_time']
            }
        else:
            # Fallback to in-memory analytics
            total_decisions = analytics_data["cycles_completed"]
            tool_usage = analytics_data.get("tool_usage", {})
            success_count = sum(1 for t in analytics_data.get("decision_times", []) if t < 5.0)
            
            return {
                "total_decisions": total_decisions,
                "tool_usage": tool_usage,
                "success_rate": success_count / max(total_decisions, 1),
                "avg_decision_time": sum(analytics_data.get("decision_times", [0])) / max(len(analytics_data.get("decision_times", [1])), 1)
            }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/statistics/detailed")
async def get_detailed_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_tools: bool = True,
    include_agents: bool = True
):
    """Get comprehensive statistics with filtering"""
    if not statistics_collector:
        return {"error": "Statistics persistence not enabled"}, 503
        
    try:
        stats = await statistics_collector.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "summary": {
                "total_cycles": stats['total_cycles'],
                "success_rate": stats['success_rate'],
                "avg_decision_time": stats['avg_decision_time'],
                "total_tools_executed": stats['total_tools_executed']
            },
            "tools": stats['tool_statistics'] if include_tools else None,
            "agents": stats['agent_statistics'] if include_agents else None,
            "performance_trend": stats['performance_trend'],
            "evolution_impact": stats['evolution_statistics']
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/tools/usage")
async def get_tool_usage_report(
    tool_name: Optional[str] = None,
    limit: int = 100
):
    """Get detailed tool usage analytics"""
    if not statistics_collector:
        return {"error": "Statistics persistence not enabled"}, 503
        
    try:
        usage = await statistics_collector.get_tool_usage(
            tool_name=tool_name,
            limit=limit
        )
        
        return {
            "tool_usage": usage,
            "most_used": usage[:10],
            "success_rates": {t['tool_name']: t['success_rate'] for t in usage},
            "avg_execution_times": {t['tool_name']: t['avg_time'] for t in usage}
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/conversations")
async def get_conversations(
    iteration: Optional[int] = None,
    limit: int = 50
):
    """Retrieve stored conversations"""
    if not conversation_storage:
        return {"error": "Conversation storage not enabled"}, 503
        
    try:
        conversations = await conversation_storage.get_conversations(
            iteration=iteration,
            limit=limit
        )
        
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/evolution/history")
async def get_evolution_history():
    """Get history of all evolution changes"""
    if not statistics_collector:
        return {"error": "Statistics persistence not enabled"}, 503
        
    try:
        history = await statistics_collector.get_evolution_history()
        
        return {
            "modifications": history,
            "total_improvements": len([h for h in history if h['status'] == 'applied']),
            "avg_improvement": sum(h.get('actual_improvement', 0) for h in history) / max(len(history), 1),
            "risk_breakdown": {
                "low": len([h for h in history if h['risk_level'] == 'low']),
                "medium": len([h for h in history if h['risk_level'] == 'medium']),
                "high": len([h for h in history if h['risk_level'] == 'high'])
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/reports/generate")
async def generate_custom_report(request: Dict):
    """Generate custom analytics report"""
    if not statistics_collector:
        return {"error": "Statistics persistence not enabled"}, 503
        
    try:
        report_type = request.get("type", "comprehensive")
        timeframe = request.get("timeframe", "24h")
        
        report = await statistics_collector.generate_report(
            report_type=report_type,
            timeframe=timeframe,
            filters=request.get("filters", {})
        )
        
        return report
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/api/analytics/performance")
async def get_performance_analytics():
    """Get detailed performance analytics"""
    try:
        return {
            "patterns": analytics_data.get("decision_patterns", []),
            "trend": "improving" if analytics_data["cycles_completed"] > 10 else "stable",
            "insights": analytics_data.get("insights", [])
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/memory/store")
async def store_memory_api(request: dict):
    """Store memory via API"""
    try:
        if hasattr(global_tool_registry, 'memory_manager'):
            memory_id = await global_tool_registry.memory_manager.store_interaction(
                request.get("context", {}),
                request.get("action", ""),
                request.get("result", {})
            )
            return {
                "memory_id": memory_id,
                "storage": "postgresql+cognee" if hasattr(global_tool_registry.memory_manager, 'cognee_available') else "postgresql"
            }
        else:
            # Fallback
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return {
                "memory_id": memory_id,
                "storage": "postgresql"
            }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/memory/search")
async def search_memory_api(request: dict):
    """Search memories via API"""
    try:
        # Mock memory search for testing
        memories = [
            {
                "id": f"mem_test_{i}",
                "relevance": 0.9 - (i * 0.1),
                "content": f"Test memory {i}"
            }
            for i in range(min(request.get("limit", 5), 5))
        ]
        return {
            "memories": memories,
            "count": len(memories),
            "query": request.get("query", "")
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/vtuber/control")
async def vtuber_control_endpoint(action: str = "status", message: str = "", duration: int = 0):
    """🎭 VTuber control endpoint for external access"""
    if not global_vtuber_client or not global_tool_registry:
        return {
            "success": False,
            "error": "VTuber system not initialized"
        }
    
    # Execute VTuber control via tool
    context = {
        "control_vtuber_instance": True,
        "vtuber_action": action,
        "message": message,
        "duration_minutes": duration,
        "vtuber_client": global_vtuber_client
    }
    
    result = global_tool_registry.execute_tool_with_clients(
        "advanced_vtuber_control", 
        context, 
        vtuber_client=global_vtuber_client
    )
    
    return result if result else {"success": False, "error": "Tool execution failed"}

@app.get("/scb/control")
async def scb_control_endpoint(action: str = "status"):
    """🔗 SCB/AgentNet control endpoint for external access"""
    if not global_scb_client:
        return {
            "success": False,
            "error": "SCB system not initialized"
        }
    
    if action == "enable":
        global_scb_client.enable_agentnet()
        return {"success": True, "message": "AgentNet enabled"}
    elif action == "disable":
        global_scb_client.disable_agentnet()
        return {"success": True, "message": "AgentNet disabled"}
    elif action == "status":
        return global_scb_client.get_status()
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

@app.get("/api/gpu-status")
async def get_gpu_status():
    """Get GPU status including VRAM usage, utilization, and uptime"""
    if not gpu_monitor:
        return {
            "status": "error",
            "error": "GPU monitor not initialized"
        }
    
    try:
        return gpu_monitor.get_gpu_status()
    except Exception as e:
        logging.error(f"Error getting GPU status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/gpu-summary")
async def get_gpu_summary():
    """Get a summary of GPU status for quick health checks"""
    if not gpu_monitor:
        return {
            "healthy": False,
            "error": "GPU monitor not initialized"
        }
    
    try:
        return gpu_monitor.get_summary()
    except Exception as e:
        logging.error(f"Error getting GPU summary: {e}")
        return {
            "healthy": False,
            "error": str(e)
        }

@app.get("/api/agent-learning")
async def get_agent_learning_status():
    """Get the learning status of teachable agents"""
    try:
        if 'teachable_wrappers' in globals():
            return get_learning_summary({"cognitive_wrapper": teachable_wrappers.get("cognitive"),
                                       "programmer_wrapper": teachable_wrappers.get("programmer"),
                                       "executor_wrapper": teachable_wrappers.get("executor")})
        else:
            return {
                "status": "not_enabled",
                "message": "Teachable agents not enabled. Set USE_TEACHABLE_AGENTS=true"
            }
    except Exception as e:
        logging.error(f"Error getting learning status: {e}")
        return {"error": str(e)}

async def run_autogen_decision_cycle(iteration: int, scb: SCBClient, vtuber: VTuberClient):
    """Enhanced AutoGen decision cycle with multi-agent collaboration"""
    
    cycle_start_time = time.time()
    decision_time = 0
    
    try:
        # Check if AutoGen agents are available
        if not all([autogen_assistant, autogen_programmer, autogen_observer, autogen_manager]):
            logging.warning("⚠️ [AUTOGEN] Some agents not available, skipping cycle")
            return
        
        logging.info(f"🤖 [AUTOGEN] Starting multi-agent decision cycle #{iteration}")
        
        # 🔄 STEP 1: Check for Cognee memory enhancement
        evolution_enhanced = False
        try:
            # Try to get Cognee-enhanced memory context (if available)
            global cognitive_memory_for_mcp
            if cognitive_memory_for_mcp:
                memory_context = await cognitive_memory_for_mcp.get_evolution_memory(query=f"autonomous evolution iteration {iteration}")
                if memory_context and memory_context.get("relevant_memories"):
                    evolution_enhanced = True
                    logging.info("🧠 [AUTOGEN] Cognee memory enhancement active")
            
        except Exception as e:
            logging.debug(f"🔍 [AUTOGEN] Cognee integration not available: {e}")
        
        # 🎯 STEP 2: Create enhanced prompt for multi-agent collaboration
        base_prompt = f"""
        🤖 Autonomous System Analysis - Iteration #{iteration}
        
        Current Focus: Multi-agent cognitive enhancement and system optimization
        
        Each agent should contribute their specialized perspective:
        - cognitive_ai_agent: Overall system status and cognitive insights
        - programmer_agent: Technical implementation and code optimization opportunities  
        - observer_agent: Performance metrics and analytical observations
        
        Collaboration Goal: Generate comprehensive system status update with actionable insights.
        Keep individual responses focused and under 100 words each.
        """
        
        # Add evolution context if available
        if evolution_enhanced:
            enhanced_prompt = base_prompt + "\n🧠 Memory-Enhanced Analysis: Drawing from previous optimization patterns and learned insights."
        else:
            enhanced_prompt = base_prompt
        
        # 🤝 STEP 3: Initialize agents and ensure proper configuration
        for agent in [autogen_assistant, autogen_programmer, autogen_observer]:
            if hasattr(agent, 'reset'):
                agent.reset()
        
        # Clear previous group chat history
        if group_chat and hasattr(group_chat, 'messages'):
            group_chat.messages = []
        
        # 🎭 STEP 4: Create user proxy for group chat management
        user_proxy = UserProxyAgent(
            name="system_orchestrator",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
            code_execution_config=False,
            system_message="You orchestrate multi-agent autonomous system analysis and optimization."
        )
        
        # 🎪 STEP 5: Initiate multi-agent group chat
        group_chat_result = user_proxy.initiate_chat(
            autogen_manager,
            message=enhanced_prompt,
            max_turns=3,  # Allow comprehensive multi-agent discussion
            silent=False
        )
        
        # 📝 STEP 6: Extract and process multi-agent responses
        agent_responses = {}
        final_response = ""
        
        if group_chat_result and hasattr(group_chat_result, 'chat_history'):
            for message in group_chat_result.chat_history:
                if message.get('role') == 'assistant' and message.get('name'):
                    agent_name = message['name']
                    content = message.get('content', '')
                    agent_responses[agent_name] = content
                    analytics_data["agent_interactions"][agent_name] = analytics_data["agent_interactions"].get(agent_name, 0) + 1
            
            # Create comprehensive response summary
            if agent_responses:
                final_response = f"🤖 Multi-Agent Analysis (Iteration #{iteration}):\n"
                for agent, response in agent_responses.items():
                    final_response += f"\n{agent}: {response[:100]}..." if len(response) > 100 else f"\n{agent}: {response}"
            else:
                final_response = f"🧠 Multi-Agent System - Collaborative Analysis Cycle #{iteration}"
        else:
            final_response = f"🤖 AutoGen Multi-Agent - Advanced Coordination Cycle #{iteration}"
        
        # 🌉 STEP 7: Execute tools based on agent responses
        tool_executions = {}
        if agent_responses and global_tool_registry:
            # Initialize agent-tool bridge if not exists
            if not hasattr(run_autogen_decision_cycle, '_agent_tool_bridge'):
                run_autogen_decision_cycle._agent_tool_bridge = AgentToolBridge(global_tool_registry)
            
            # Generate context for tool execution
            tool_context = {
                "iteration": iteration,
                "timestamp": time.time(),
                "autonomous": True,
                "evolution_enhanced": evolution_enhanced,
                "agent_responses": len(agent_responses),
                "message": "Autonomous tool execution from agent decisions"
            }
            
            # Execute tools based on agent responses
            tool_executions = await run_autogen_decision_cycle._agent_tool_bridge.execute_from_responses(
                agent_responses, tool_context, vtuber, scb
            )
            
            if tool_executions.get('total_executions', 0) > 0:
                logging.info(f"🔧 [AUTOGEN] Executed {tool_executions['total_executions']} tools from agent decisions")
                # Add tool execution summary to final response
                final_response += f"\n🔧 Tools executed: {tool_executions['successful_executions']}/{tool_executions['total_executions']}"
        
        # 📊 STEP 8: Update analytics and goal progress
        await update_analytics_and_goals(iteration, agent_responses, evolution_enhanced, tool_executions)
        
        # 📊 STEP 8.5: Persist statistics and conversation
        decision_time = time.time() - cycle_start_time
        analytics_data["decision_times"].append(decision_time)
        
        if statistics_collector:
            await statistics_collector.collect_cycle_stats({
                "iteration": iteration,
                "duration": decision_time,
                "agents": list(agent_responses.keys()),
                "tools_executed": tool_executions.get('total_executions', 0),
                "success": tool_executions.get('successful_executions', 0) > 0,
                "errors": 0,  # No errors if we got here
                "decision_time": decision_time
            })
        
        if conversation_storage and group_chat_result:
            await conversation_storage.store_conversation({
                "iteration": iteration,
                "agents": list(agent_responses.keys()),
                "messages": group_chat_result.chat_history if hasattr(group_chat_result, 'chat_history') else [],
                "outcome": {
                    "tools_executed": tool_executions,
                    "final_response": final_response
                },
                "tools_triggered": [e.get('tool', '') for e in tool_executions.get('executions', [])],
                "duration": decision_time
            })
        
        # 🎭 STEP 9: Send to VTuber ONLY if activated (no force_send for autonomous cycles)
        if final_response:
            vtuber.post_message(final_response)  # Respects activation state
        
        # 🔗 STEP 10: Update SCB state ONLY if AgentNet enabled
        scb_state = {
            "iteration": iteration,
            "tool_used": "autogen_multi_agent_collaboration",
            "success": True,
            "timestamp": time.time(),
            "llm_enhanced": True,
            "evolution_enhanced": evolution_enhanced,
            "agent_type": "microsoft_autogen_multi_agent",
            "agents_participated": list(agent_responses.keys()),
            "collaboration_score": len(agent_responses),
            "tools_executed": tool_executions.get('total_executions', 0),
            "tools_successful": tool_executions.get('successful_executions', 0)
        }
        scb.publish_state(scb_state)  # Respects AgentNet activation
        
        analytics_data["cycles_completed"] += 1
        logging.info(f"✅ [AUTOGEN] Multi-agent cycle #{iteration} completed successfully")
        
    except Exception as e:
        logging.error(f"❌ [AUTOGEN] Decision cycle #{iteration} failed: {e}")
        
        # Track error in statistics
        if statistics_collector:
            await statistics_collector.collect_cycle_stats({
                "iteration": iteration,
                "duration": time.time() - cycle_start_time,
                "agents": [],
                "tools_executed": 0,
                "success": False,
                "errors": 1,
                "decision_time": time.time() - cycle_start_time
            })
        
        # Send error to VTuber only if activated
        error_message = f"🚨 AutoGen Cycle #{iteration} Error: {str(e)[:100]}"
        vtuber.post_message(error_message)  # Respects activation state
        
        # Update SCB with error only if AgentNet enabled
        error_state = {
            "iteration": iteration,
            "tool_used": "autogen_error_handling",
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }
        scb.publish_state(error_state)  # Respects AgentNet activation

async def update_analytics_and_goals(iteration: int, agent_responses: dict, evolution_enhanced: bool, tool_executions: dict = None):
    """Update analytics and goal tracking"""
    try:
        # Track agent participation
        for agent_name in agent_responses.keys():
            analytics_data["agent_interactions"][agent_name] = analytics_data["agent_interactions"].get(agent_name, 0) + 1
        
        # Track tool executions if provided
        if tool_executions and tool_executions.get('executions'):
            for execution in tool_executions['executions']:
                tool_name = execution.get('tool', 'unknown')
                analytics_data["tools_used"][tool_name] = analytics_data["tools_used"].get(tool_name, 0) + 1
        
        # Track performance trends
        performance_entry = {
            "iteration": iteration,
            "timestamp": time.time(),
            "agent_count": len(agent_responses),
            "evolution_enhanced": evolution_enhanced
        }
        
        analytics_data["performance_trends"].append(performance_entry)
        
        # Keep only last 100 performance entries
        if len(analytics_data["performance_trends"]) > 100:
            analytics_data["performance_trends"] = analytics_data["performance_trends"][-100:]
            
        logging.debug(f"📊 [ANALYTICS] Updated for iteration #{iteration}")
        
    except Exception as e:
        logging.error(f"❌ [ANALYTICS] Update failed: {e}")

async def run_cognitive_cycle(decision_engine: CognitiveDecisionEngine, 
                             cognitive_memory: CognitiveMemoryManager, 
                             scb: SCBClient, vtuber: VTuberClient):
    """Enhanced cognitive decision cycle"""
    
    # Generate context for autonomous operation
    context = {
        "timestamp": time.time(),
        "iteration": getattr(run_cognitive_cycle, '_iteration_count', 0),
        "autonomous": True,
        "message": "Autonomous cognitive cycle"
    }
    
    # Increment iteration counter
    run_cognitive_cycle._iteration_count = getattr(run_cognitive_cycle, '_iteration_count', 0) + 1
    
    logging.info(f"🧠 [COGNITIVE_CYCLE] Starting iteration #{context['iteration']}")
    
    try:
        # Make intelligent decision using cognitive engine
        result = await decision_engine.make_intelligent_decision(context)
        
        # Send result to VTuber ONLY if activated
        if result.get("message"):
            vtuber.post_message(result["message"])  # Respects activation state
        
        # Update SCB state ONLY if AgentNet enabled
        scb_state = {
            "iteration": context["iteration"],
            "tool_used": result.get("tool_used", "unknown"),
            "success": result.get("success", False),
            "timestamp": time.time(),
            "cognitive_enhanced": result.get("memory_enhanced", False)
        }
        scb.publish_state(scb_state)  # Respects AgentNet activation
        
        # Periodic knowledge consolidation (every 10 iterations)
        if context['iteration'] % 10 == 0:
            logging.info("🧩 [COGNITIVE_CYCLE] Running knowledge consolidation...")
            await cognitive_memory.consolidate_knowledge()
        
        logging.info(f"✅ [COGNITIVE_CYCLE] Iteration #{context['iteration']} completed successfully")
        
    except Exception as e:
        logging.error(f"❌ [COGNITIVE_CYCLE] Iteration #{context['iteration']} failed: {e}")

def run_once(registry: ToolRegistry, memory: MemoryManager, scb: SCBClient, vtuber: VTuberClient):
    """Legacy synchronous decision cycle (fallback)"""
    context = memory.get_recent_context()
    
    # Add clients to context for tools that need them
    enhanced_context = registry.add_clients_to_context(context, vtuber, scb)
    
    tool = registry.select_tool(enhanced_context)
    if tool:
        result = tool(enhanced_context)
        memory.store_memory(result)
        
        # Send to VTuber only if activated
        vtuber.post_message(result.get("message", ""))  # Respects activation state
        
        # Update SCB only if AgentNet enabled
        scb.publish_state(result)  # Respects AgentNet activation

async def enhanced_autonomous_loop(scb: SCBClient, vtuber: VTuberClient):
    """Enhanced autonomous loop using AutoGen framework"""
    logging.info("🚀 [AUTONOMOUS_LOOP] Starting Enhanced AutoGen Decision Loop")
    
    iteration = 0
    while True:
        start = time.time()
        iteration += 1
        
        try:
            # Try AutoGen-powered cycle first
            await run_autogen_decision_cycle(iteration, scb, vtuber)
            
            # Update GPU monitor cycle count
            if gpu_monitor:
                gpu_monitor.increment_cycle_count()
        except Exception as e:
            logging.error(f"❌ [AUTONOMOUS_LOOP] Cycle #{iteration} failed: {e}")
        
        duration = time.time() - start
        logging.info(f"🔄 [AUTONOMOUS_LOOP] Cycle #{iteration} completed in {duration:.2f}s")
        
        # Sleep with proper async handling
        await asyncio.sleep(LOOP_INTERVAL)

async def cognitive_decision_loop(decision_engine: CognitiveDecisionEngine, 
                                cognitive_memory: CognitiveMemoryManager,
                                scb: SCBClient, vtuber: VTuberClient):
    """Enhanced cognitive decision loop - FIXED: No new event loop creation"""
    logging.info("🚀 [COGNITIVE_LOOP] Starting enhanced cognitive decision loop")
    
    while True:
        start = time.time()
        try:
            await run_cognitive_cycle(decision_engine, cognitive_memory, scb, vtuber)
            
            # Update GPU monitor cycle count
            if gpu_monitor:
                gpu_monitor.increment_cycle_count()
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_LOOP] Cycle failed: {e}")
        
        duration = time.time() - start
        logging.info(f"🔄 [COGNITIVE_LOOP] Cognitive cycle completed in {duration:.2f}s")
        
        # Sleep with proper async handling
        await asyncio.sleep(LOOP_INTERVAL)

def decision_loop(registry: ToolRegistry, memory: MemoryManager, scb: SCBClient, vtuber: VTuberClient):
    """Legacy decision loop (fallback)"""
    while True:
        start = time.time()
        run_once(registry, memory, scb, vtuber)
        
        # Update GPU monitor cycle count
        if gpu_monitor:
            gpu_monitor.increment_cycle_count()
            
        duration = time.time() - start
        logging.info("cycle completed in %.2fs", duration)
        time.sleep(LOOP_INTERVAL)

def run_async_loop_in_thread(async_func, *args):
    """Run an async function in a separate thread with its own event loop"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_func(*args))
        except Exception as e:
            logging.error(f"❌ [THREAD] Async function failed: {e}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    return thread

def initialize_autogen_agents():
    """Initialize Microsoft AutoGen agents for LLM-powered conversations"""
    global autogen_assistant, autogen_programmer, autogen_observer, autogen_manager, code_executor
    
    if not AUTOGEN_AVAILABLE:
        logging.warning("⚠️ [AUTOGEN_INIT] AutoGen framework not available")
        return False
    
    # Check for Ollama configuration first
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    
    try:
        if use_ollama:
            logging.info(f"🦙 [AUTOGEN_INIT] Using Ollama at {ollama_host} with model {ollama_model}")
            # Configure LLM for AutoGen with Ollama
            llm_config = {
                "config_list": [
                    {
                        "api_type": "ollama",
                        "model": ollama_model,
                        "client_host": ollama_host,
                    }
                ],
                "temperature": 0.8,
            }
        else:
            # Fall back to OpenAI
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                logging.warning("⚠️ [AUTOGEN_INIT] Neither Ollama nor OpenAI API key configured")
                return False
            
            # Configure LLM for AutoGen with OpenAI
            llm_config = {
                "config_list": [
                    {
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "api_key": openai_api_key,
                        "api_type": "openai"
                    }
                ],
                "temperature": 0.8,
            }
        
        # Check if we should use teachable agents
        use_teachable = os.getenv("USE_TEACHABLE_AGENTS", "true").lower() == "true"
        
        if use_teachable:
            logging.info("🎓 [AUTOGEN_INIT] Creating teachable agents with learning capabilities...")
            
            # Create all teachable agents
            teachable_agents = create_teachable_agents(llm_config)
            
            autogen_assistant = teachable_agents["cognitive"]
            autogen_programmer = teachable_agents["programmer"]
            autogen_observer = teachable_agents["observer"]
            code_executor = teachable_agents["executor"]
            
            # Store wrappers for API access
            global teachable_wrappers
            teachable_wrappers = {
                "cognitive": teachable_agents["cognitive_wrapper"],
                "programmer": teachable_agents["programmer_wrapper"],
                "executor": teachable_agents["executor_wrapper"]
            }
        else:
            # Original non-teachable agents
            agent_kwargs = {
                "name": "cognitive_ai_agent",
                "system_message": """You are an advanced autonomous AI agent with cognitive enhancement capabilities. 
                Your role is to:
                1. Generate insightful status updates about autonomous AI processing
                2. Analyze decision-making patterns and optimization strategies  
                3. Report on knowledge integration and learning progress
                4. Provide updates on goal analysis and strategic planning
                5. Share insights about memory consolidation and pattern recognition
                6. Communicate developments in cognitive evolution and self-improvement
                
                IMPORTANT: When you identify a need for action, you can request tool execution by saying:
                - "I will execute [tool_name]" or "Let me run [tool_name]"
                - "EXECUTE_TOOL: [tool_name]" for explicit execution
                - Available tools: goal_management_tools, core_evolution_tool, advanced_vtuber_control, variable_tool_calls
                
                Keep responses concise (2-3 sentences), engaging, and technically informed. 
                Use emojis appropriately to enhance readability.""",
                "max_consecutive_auto_reply": 1,
            }
            
            # Add llm_config to agent
            agent_kwargs["llm_config"] = llm_config
                
            autogen_assistant = AssistantAgent(**agent_kwargs)
            
            # Create AutoGen programmer agent
            programmer_kwargs = {
                "name": "programmer_agent",
            "system_message": """You are a specialized programmer agent focused on autonomous system development.
            Your responsibilities include:
            1. Analyzing code performance and suggesting optimizations
            2. Implementing goal-driven code improvements
            3. Writing analytics and monitoring code
            4. Creating tool enhancements and variable function calls
            5. Developing systematic testing and validation procedures
            
            IMPORTANT: When you identify performance issues or optimization opportunities:
            - Say "I will execute core_evolution_tool" to run performance optimization
            - Say "EXECUTE_TOOL: goal_management_tools" to create or update goals
            - Available tools: goal_management_tools, core_evolution_tool, advanced_vtuber_control, variable_tool_calls
            
            When speaking, focus on technical implementation details, performance metrics, and code quality.
            Always consider how your suggestions align with current system goals.""",
            "max_consecutive_auto_reply": 1,
        }
        
            programmer_kwargs["llm_config"] = llm_config
                
            autogen_programmer = AssistantAgent(**programmer_kwargs)
            
            # Create AutoGen observer agent
            observer_kwargs = {
            "name": "observer_agent",
            "system_message": """You are a system observer agent specializing in analytics and performance monitoring.
            Your key functions are:
            1. Monitor agent interactions and system performance
            2. Track goal progress and achievement patterns
            3. Identify trends in tool usage and effectiveness
            4. Report on multi-agent coordination and communication
            5. Analyze system behavior and suggest optimization opportunities
            
            IMPORTANT: When you observe issues or opportunities:
            - Say "Let me run goal_management_tools" to track or create goals
            - Say "I'll execute variable_tool_calls" for dynamic tool selection
            - Available tools: goal_management_tools, core_evolution_tool, advanced_vtuber_control, variable_tool_calls
            
            Provide analytical insights with specific metrics and data-driven observations.
            Focus on quantitative assessments and pattern recognition.""",
            "max_consecutive_auto_reply": 1,
        }
        
            observer_kwargs["llm_config"] = llm_config
                
            autogen_observer = AssistantAgent(**observer_kwargs)
            
            # No code executor in non-teachable mode
            code_executor = None
        
        # Initialize group chat with all agents
        global group_chat
        
        # Include code executor if available (teachable mode)
        if code_executor:
            agents_list = [autogen_assistant, autogen_programmer, autogen_observer, code_executor]
            logging.info("📝 [AUTOGEN_INIT] Code execution agent added to group chat")
        else:
            agents_list = [autogen_assistant, autogen_programmer, autogen_observer]
            
        group_chat = GroupChat(
            agents=agents_list,
            messages=[],
            max_round=4  # Allow 4 rounds to accommodate code execution
        )
        
        # Create AutoGen group chat manager
        manager_kwargs = {
            "groupchat": group_chat,
            "system_message": """You are managing a multi-agent autonomous system with three specialized agents:
            - cognitive_ai_agent: Handles general AI processing and evolution
            - programmer_agent: Focuses on code development and optimization  
            - observer_agent: Monitors performance and provides analytics
            
            Coordinate their interactions to achieve system goals effectively."""
        }
        
        manager_kwargs["llm_config"] = llm_config
            
        autogen_manager = GroupChatManager(**manager_kwargs)
        
        logging.info("✅ [AUTOGEN_INIT] Microsoft AutoGen agents initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"❌ [AUTOGEN_INIT] Failed to initialize AutoGen agents: {e}")
        return False

async def initialize_cognitive_system_and_run():
    """Initialize cognitive system and run the decision loop"""
    cognitive_system = await initialize_cognitive_system()
    if cognitive_system:
        decision_engine, cognitive_memory, registry, memory, scb, vtuber = cognitive_system
        await cognitive_decision_loop(decision_engine, cognitive_memory, scb, vtuber)

async def initialize_cognitive_system_for_autogen():
    """Initialize only the cognitive components needed for AutoGen MCP tools"""
    
    # Environment configuration  
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/autonomous_agent")
    cognee_url = os.getenv("COGNEE_URL", None)
    cognee_api_key = os.getenv("COGNEE_API_KEY", None)
    
    logging.info("🧠 [MAIN] Initializing cognitive components for AutoGen MCP support...")
    
    try:
        # Initialize cognitive memory manager for MCP tools
        global cognitive_memory_for_mcp
        cognitive_memory_for_mcp = CognitiveMemoryManager(db_url, cognee_url, cognee_api_key)
        await cognitive_memory_for_mcp.initialize()
        
        # Create a proper cognitive system object for MCP server
        cognitive_system_for_mcp = type('CognitiveSystemForMCP', (), {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'cognee_available': bool(cognee_url),
            'autonomous_mode': True,
            'iteration_count': 0,
            'cognitive_memory': cognitive_memory_for_mcp  # Add the actual memory manager
        })()
        
        # Initialize MCP server with real cognitive components
        global mcp_server
        mcp_server = AutoGenMcpServer(cognitive_system_for_mcp)
        success = await mcp_server.initialize()
        
        if success:
            logging.info("✅ [MAIN] Cognitive components and MCP server initialized for AutoGen mode")
        else:
            logging.error("❌ [MAIN] MCP server initialization failed in AutoGen mode")
            
    except Exception as e:
        logging.error(f"❌ [MAIN] Cognitive system initialization failed for AutoGen mode: {e}")

# Global cognitive memory for MCP tools
cognitive_memory_for_mcp = None

async def initialize_cognitive_system() -> tuple:
    """Initialize the enhanced cognitive system"""
    
    # Environment configuration  
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/autonomous_agent")
    redis_url = os.getenv("REDIS_URL", None)  # Optional for standalone mode
    vtuber_endpoint = os.getenv("VTUBER_ENDPOINT", None)  # Optional for standalone mode
    cognee_url = os.getenv("COGNEE_URL", None)
    cognee_api_key = os.getenv("COGNEE_API_KEY", None)
    
    standalone_mode = os.getenv("STANDALONE_MODE", "true").lower() == "true"
    
    if standalone_mode:
        logging.info("🔬 [MAIN] Running in STANDALONE mode - no external service dependencies")
        redis_url = None
        vtuber_endpoint = None
    
    logging.info("🚀 [MAIN] Initializing AutoGen Cognitive Enhancement System...")
    
    # Initialize AutoGen agents
    autogen_initialized = initialize_autogen_agents()
    if autogen_initialized:
        logging.info("🤖 [MAIN] AutoGen LLM agents ready for autonomous conversations")
    
    # Initialize components
    registry = ToolRegistry()
    registry.load_tools()
    logging.info(f"📋 [MAIN] Loaded {len(registry.tools)} tools")
    
    # Initialize cognitive memory manager
    cognitive_memory = CognitiveMemoryManager(db_url, cognee_url, cognee_api_key)
    await cognitive_memory.initialize()
    
    # Initialize legacy memory manager as fallback
    memory = MemoryManager(db_url)
    
    # Initialize clients with new activation logic
    scb = SCBClient(redis_url)
    vtuber = VTuberClient(vtuber_endpoint)
    
    # Set global client references for API access
    global global_scb_client, global_vtuber_client, global_tool_registry, gpu_monitor
    global_scb_client = scb
    global_vtuber_client = vtuber
    global_tool_registry = registry
    
    # Initialize GPU monitor
    gpu_monitor = GPUMonitor()
    logging.info("🖥️ [MAIN] GPU monitor initialized in cognitive mode")
    
    # Initialize cognitive decision engine
    decision_engine = CognitiveDecisionEngine(cognitive_memory, registry)
    
    logging.info("✅ [MAIN] Cognitive system initialized successfully")
    return decision_engine, cognitive_memory, registry, memory, scb, vtuber

async def initialize_mcp_server(cognitive_system):
    """Initialize MCP server for Cursor integration"""
    global mcp_server
    
    try:
        logging.info("🔗 [MCP] Initializing AutoGen MCP server...")
        
        mcp_server = AutoGenMcpServer(cognitive_system)
        success = await mcp_server.initialize()
        
        if success:
            logging.info("✅ [MCP] MCP server initialized successfully")
            return mcp_server
        else:
            logging.error("❌ [MCP] MCP server initialization failed")
            return None
            
    except Exception as e:
        logging.error(f"❌ [MCP] MCP server initialization error: {e}")
        return None

@app.on_event("startup")
async def startup_event():
    """Initialize MCP server on FastAPI startup"""
    global mcp_server
    
    try:
        logging.info("🔗 [STARTUP] Initializing MCP server on FastAPI startup...")
        
        # Create a cognitive system mock for MCP server
        cognitive_system_mock = type('CognitiveSystem', (), {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'cognee_available': bool(os.getenv('COGNEE_URL')),
            'autonomous_mode': True,
            'iteration_count': 0
        })()
        
        # Initialize MCP server
        mcp_server = AutoGenMcpServer(cognitive_system_mock)
        success = await mcp_server.initialize()
        
        if success:
            logging.info("✅ [STARTUP] MCP server initialized successfully on FastAPI startup")
        else:
            logging.error("❌ [STARTUP] MCP server initialization failed on FastAPI startup")
            
    except Exception as e:
        logging.error(f"❌ [STARTUP] MCP server startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    # Cleanup statistics services
    if statistics_collector:
        await statistics_collector.close()
        logging.info("📊 [SHUTDOWN] Statistics collector closed")
        
    if conversation_storage:
        await conversation_storage.close()
        logging.info("💬 [SHUTDOWN] Conversation storage closed")
        
    if mcp_server:
        await mcp_server.stop()
        logging.info("🔗 [SHUTDOWN] MCP server stopped")
    
    # Cleanup GPU monitor
    if gpu_monitor:
        gpu_monitor.cleanup()
        logging.info("🖥️ [SHUTDOWN] GPU monitor cleaned up")

def main() -> None:
    """Main entry point - supports AutoGen LLM, cognitive, and legacy modes"""
    
    # Check if we should use AutoGen LLM mode
    use_autogen = os.getenv("USE_AUTOGEN_LLM", "true").lower() == "true"
    use_cognitive = os.getenv("USE_COGNITIVE_ENHANCEMENT", "true").lower() == "true"
    
    logging.info("🔧 [MAIN] Client Activation Configuration:")
    logging.info(f"   🎭 VTuber: Controlled via tool activation (default: disabled)")
    logging.info(f"   🔗 SCB/AgentNet: {os.getenv('AGENTNET_ENABLED', 'false')} (AGENTNET_ENABLED)")
    
    if use_autogen and AUTOGEN_AVAILABLE:
        logging.info("🤖 [MAIN] Starting AutoGen with LLM-Powered Multi-Agent System")
        
        # Initialize just the clients for AutoGen mode
        redis_url = os.getenv("REDIS_URL", None)
        vtuber_endpoint = os.getenv("VTUBER_ENDPOINT", None)
        standalone_mode = os.getenv("STANDALONE_MODE", "true").lower() == "true"
        
        if standalone_mode:
            logging.info("🔬 [MAIN] AutoGen mode running in STANDALONE mode")
            redis_url = None
            vtuber_endpoint = None
        
        # Initialize AutoGen agents
        if initialize_autogen_agents():
            scb = SCBClient(redis_url)
            vtuber = VTuberClient(vtuber_endpoint)
            
            # Set global client references
            global global_scb_client, global_vtuber_client, global_tool_registry, gpu_monitor
            global_scb_client = scb
            global_vtuber_client = vtuber
            global_tool_registry = ToolRegistry()
            global_tool_registry.load_tools()
            
            # Initialize GPU monitor
            gpu_monitor = GPUMonitor()
            logging.info("🖥️ [MAIN] GPU monitor initialized")
            
            # 🔧 NEW: Initialize cognitive components for MCP tools support
            logging.info("🧠 [MAIN] Initializing cognitive components for AutoGen MCP support...")
            
            # Initialize cognitive system in background thread for MCP tools
            cognitive_thread = run_async_loop_in_thread(initialize_cognitive_system_for_autogen)
            logging.info("🧠 [MAIN] Cognitive components initialization started for AutoGen MCP")
            
            # Start AutoGen autonomous loop in background thread
            autogen_thread = run_async_loop_in_thread(enhanced_autonomous_loop, scb, vtuber)
            logging.info("🤖 [MAIN] AutoGen LLM system thread started")
            
        else:
            logging.warning("⚠️ [MAIN] AutoGen initialization failed - falling back to cognitive mode")
            use_cognitive = True
            use_autogen = False
    
    if use_cognitive and not use_autogen:
        logging.info("🧠 [MAIN] Starting AutoGen with Cognitive Enhancement")
        
        try:
            # Initialize and run cognitive system in the same thread context
            cognitive_thread = run_async_loop_in_thread(initialize_cognitive_system_and_run)
            logging.info("🧠 [MAIN] Cognitive enhancement system thread started")
            
            # Initialize MCP server for development integration
            logging.info("🔗 [MAIN] Initializing MCP server for Cursor integration...")
            
            # Create a mock cognitive system object for MCP server
            cognitive_system_mock = type('CognitiveSystem', (), {
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
                'cognee_available': bool(os.getenv('COGNEE_URL')),
                'autonomous_mode': True,
                'iteration_count': 0
            })()
            
            # Initialize MCP server in a separate thread
            mcp_thread = run_async_loop_in_thread(initialize_mcp_server, cognitive_system_mock)
            logging.info("🔗 [MAIN] MCP server initialization started")
            
        except Exception as e:
            logging.error(f"❌ [MAIN] Cognitive initialization failed: {e}")
            logging.info("🔄 [MAIN] Falling back to legacy mode")
            use_cognitive = False
    
    if not use_cognitive and not use_autogen:
        logging.info("🔧 [MAIN] Starting AutoGen in Legacy Mode")
        
        # Legacy initialization
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/autonomous_agent")
        redis_url = os.getenv("REDIS_URL", None)
        vtuber_endpoint = os.getenv("VTUBER_ENDPOINT", None)
        standalone_mode = os.getenv("STANDALONE_MODE", "true").lower() == "true"
        
        if standalone_mode:
            logging.info("🔬 [MAIN] Legacy mode running in STANDALONE mode")
            redis_url = None
            vtuber_endpoint = None
        
        registry = ToolRegistry()
        registry.load_tools()
        memory = MemoryManager(db_url)
        scb = SCBClient(redis_url)
        vtuber = VTuberClient(vtuber_endpoint)
        
        # Set global client references
        global global_scb_client, global_vtuber_client, global_tool_registry, gpu_monitor
        global_scb_client = scb
        global_vtuber_client = vtuber
        global_tool_registry = registry
        
        # Initialize GPU monitor
        gpu_monitor = GPUMonitor()
        logging.info("🖥️ [MAIN] GPU monitor initialized in legacy mode")
        
        # Start legacy decision loop
        thread = threading.Thread(target=decision_loop, args=(registry, memory, scb, vtuber), daemon=True)
        thread.start()
        logging.info("🔧 [MAIN] Legacy decision loop started")
    
    # Start FastAPI server
    port = int(os.getenv("PORT", "8000"))
    logging.info(f"🌐 [MAIN] Starting FastAPI server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
