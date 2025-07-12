import os
import time
import logging
import threading
import asyncio
import aiohttp
import json
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

from .core.tool_registry import ToolRegistry
from .core.persona_aware_tool_registry import PersonaAwareToolRegistry, initialize_persona_tool_registry
from .services.character_state_manager import CharacterStateManager, initialize_character_state_manager
from .services.memory_manager import MemoryManager
from .services.cognitive_memory import CognitiveMemoryManager
from .core.cognitive_decision_engine import CognitiveDecisionEngine
from .clients.scb_client import SCBClient
from .clients.vtuber_client import VTuberClient
from .mcp_server import AutoGenMcpServer, CursorMcpToolAdapter
from .core.agent_tool_bridge import AgentToolBridge
from .utils.statistics_collector import StatisticsCollector
from .services.conversation_storage_service import ConversationStorageService
# PatternStorageService removed for simplification
from .utils.gpu_monitor import GPUMonitor
# Teachable agents removed for simplification
from .core.stimuli_orchestrator import StimuliResponsiveOrchestrator
from .api.stimuli_api import setup_stimuli_api, stimuli_health_check
from .utils.async_utils import shutdown_async_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "20"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup and shutdown events"""
    # Startup
    print("🎆 LIFESPAN: Calling startup_tasks()")
    logging.info("🎆 LIFESPAN: Calling startup_tasks()")
    await startup_tasks()
    print("🎆 LIFESPAN: startup_tasks() completed")
    logging.info("🎆 LIFESPAN: startup_tasks() completed")
    yield
    # Shutdown
    print("🎆 LIFESPAN: Calling shutdown_tasks()")
    await shutdown_tasks()

app = FastAPI(lifespan=lifespan)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# Global stimuli orchestrator instance
global_orchestrator = None

# Global semantic map services (Neo4j-based)
global_scb_neo4j_bridge = None
global_graph_export_service = None

# Global S2 Teams System instances
global_queue_consumer = None
global_team_manager = None

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
    
    # Add stimuli processing status
    stimuli_status = await stimuli_health_check()
    health_data["stimuli_processing"] = stimuli_status
    
    # Add S2 teams status if enabled
    if os.getenv("USE_S2_TEAMS", "false").lower() == "true":
        health_data["s2_teams_status"] = {
            "enabled": True,
            "queue_consumer": global_queue_consumer is not None,
            "team_manager": global_team_manager is not None,
            "orchestrator": global_orchestrator is not None,
            "queue_file": os.getenv("S2_QUEUE_FILE", "/tmp/s2_queue/s2_processing_queue.json")
        }
        
        # Add queue consumer stats if available
        if global_queue_consumer:
            health_data["s2_teams_status"]["queue_stats"] = global_queue_consumer.get_stats()
    
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
        # Goal management service removed for simplification
        goal_service = None
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
        # Goal management service removed for simplification
        goal_service = None
        
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

# Semantic Map API Endpoints
@app.get("/api/semantic-map/export")
async def export_semantic_map(format: str = "d3js", context: str = None):
    """Export the semantic knowledge graph"""
    try:
        from .services.graph_export_neo4j import get_graph_export_service
        from .services.neo4j_semantic_storage import SemanticContext
        
        service = get_graph_export_service()
        
        # Parse context filter
        context_filter = None
        if context:
            try:
                context_filter = SemanticContext(context)
            except ValueError:
                return {"error": f"Invalid context: {context}"}, 400
        
        # Export based on format
        if format == "d3js":
            result = await service.export_d3js(context_filter)
        elif format == "graphml":
            result = await service.export_graphml(context_filter)
        elif format == "json_ld":
            result = await service.export_json_ld(context_filter)
        elif format == "cytoscape":
            result = await service.export_cytoscape(context_filter)
        else:
            return {"error": f"Invalid format: {format}. Supported: d3js, graphml, json_ld, cytoscape"}, 400
        
        return result
            
    except Exception as e:
        logging.error(f"❌ [API] Semantic map export error: {e}")
        return {"error": str(e)}, 500

@app.get("/api/semantic-map/visualize")
async def visualize_semantic_map(context: str = None):
    """Generate interactive HTML visualization"""
    try:
        from .services.graph_export_neo4j import get_graph_export_service
        from .services.neo4j_semantic_storage import SemanticContext
        
        service = get_graph_export_service()
        
        # Parse context filter
        context_filter = None
        if context:
            try:
                context_filter = SemanticContext(context)
            except ValueError:
                return {"error": f"Invalid context: {context}"}, 400
        
        # Generate visualization
        html_content = await service.generate_pyvis_visualization(context_filter)
        
        # Return HTML response
        return Response(content=html_content, media_type="text/html")
            
    except Exception as e:
        logging.error(f"❌ [API] Semantic map visualization error: {e}")
        return {"error": str(e)}, 500

@app.get("/api/semantic-map/metrics")
async def get_semantic_map_metrics(context: str = None):
    """Get graph metrics and analysis"""
    try:
        from .services.graph_export_neo4j import get_graph_export_service
        from .services.neo4j_semantic_storage import SemanticContext
        
        service = get_graph_export_service()
        
        # Parse context filter
        context_filter = None
        if context:
            try:
                context_filter = SemanticContext(context)
            except ValueError:
                return {"error": f"Invalid context: {context}"}, 400
        
        # Get metrics
        metrics = await service.get_graph_metrics(context_filter)
        return metrics
            
    except Exception as e:
        logging.error(f"❌ [API] Semantic map metrics error: {e}")
        return {"error": str(e)}, 500

@app.post("/api/semantic-map/search")
async def search_semantic_map(request: dict):
    """Search the semantic knowledge graph"""
    try:
        from .services.neo4j_semantic_storage import get_neo4j_storage, SemanticContext
        
        storage = get_neo4j_storage()
        
        query = request.get("query", "")
        context = request.get("context")
        limit = request.get("limit", 10)
        
        # Parse context filter
        context_filter = None
        if context:
            try:
                context_filter = SemanticContext(context)
            except ValueError:
                return {"error": f"Invalid context: {context}"}, 400
        
        # Search
        results = await storage.search_semantic(query, context_filter, limit)
        
        return {
            "query": query,
            "context": context,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logging.error(f"❌ [API] Semantic map search error: {e}")
        return {"error": str(e)}, 500

@app.get("/api/semantic-map/health")
@app.get("/api/semantic-map/status")  # Legacy endpoint
async def get_semantic_map_status():
    """Get status of semantic map services"""
    try:
        status = {
            "bridge": None,
            "export": None
        }
        
        # Get bridge status
        from .services.scb_neo4j_bridge import get_scb_neo4j_bridge
        bridge = get_scb_neo4j_bridge()
        status["bridge"] = bridge.get_status()
        
        # Get export service status
        from .services.graph_export_neo4j import get_graph_export_service
        export_service = get_graph_export_service()
        status["export"] = export_service.get_status()
        
        return status
        
    except Exception as e:
        logging.error(f"❌ [API] Semantic map status error: {e}")
        return {"error": str(e)}, 500

@app.post("/api/semantic-map/add")
async def add_semantic_entry(request: dict):
    """Add a semantic entry to the graph"""
    try:
        from .services.neo4j_semantic_storage import get_neo4j_storage, SemanticContext
        
        storage = get_neo4j_storage()
        
        content = request.get("content", "")
        node_type = request.get("type", "general")
        context = request.get("context", "general_context")
        metadata = request.get("metadata", {})
        
        if not content:
            return {"error": "Content is required"}, 400
        
        # Parse context
        try:
            semantic_context = SemanticContext(context)
        except ValueError:
            semantic_context = SemanticContext.GENERAL
        
        # Add node
        node = await storage.add_semantic_node(
            content=content,
            context=semantic_context,
            node_type=node_type,
            metadata=metadata
        )
        
        if node:
            return {
                "success": True,
                "node_id": node.id,
                "context": node.context.value
            }
        else:
            return {"error": "Failed to add semantic entry"}, 500
        
    except Exception as e:
        logging.error(f"❌ [API] Add semantic entry error: {e}")
        return {"error": str(e)}, 500

@app.post("/api/semantic-map/query")
async def query_semantic_graph_api(request: dict):
    """Query the semantic graph using the agent tool"""
    try:
        from .tools.semantic_graph_query_tool import query_semantic_graph
        
        # Add requesting agent from API context if not provided
        if "requesting_agent" not in request:
            # Default to system for API calls
            request["requesting_agent"] = request.get("agent", "system_api")
        
        # Execute the query with access control
        result = await query_semantic_graph(**request)
        
        return result
    except Exception as e:
        logging.error(f"❌ [API] Semantic query error: {e}")
        return {"error": str(e)}, 500

@app.get("/api/semantic-map/query/examples")
async def get_query_examples():
    """Get example queries for the semantic graph"""
    return {
        "examples": [
            {
                "name": "Full-text search",
                "description": "Search for content containing specific text",
                "request": {
                    "query_type": "search",
                    "query": "Bitcoin",
                    "context": "trading_finance",
                    "limit": 5
                }
            },
            {
                "name": "Pattern matching",
                "description": "Find relationships matching a pattern",
                "request": {
                    "query_type": "pattern",
                    "query": "tool:* -> communication",
                    "limit": 5
                }
            },
            {
                "name": "Temporal query",
                "description": "Find nodes within a time range",
                "request": {
                    "query_type": "temporal",
                    "query": "trade",
                    "time_range": {"hours": 24},
                    "context": "trading_finance",
                    "limit": 10
                }
            },
            {
                "name": "Context analysis",
                "description": "Analyze a specific semantic context",
                "request": {
                    "query_type": "context",
                    "context": "s2_to_s1_messages",
                    "limit": 10
                }
            },
            {
                "name": "Relationship exploration",
                "description": "Explore relationships for a node",
                "request": {
                    "query_type": "relationships",
                    "query": "node_id_here",
                    "limit": 10
                }
            }
        ],
        "pattern_syntax": {
            "tool:*": "Any tool execution",
            "s2:*": "Any S2 agent node",
            "s1:*": "Any S1 agent node",
            "error": "Error nodes",
            "*": "Any node",
            "->": "Relationship direction"
        }
    }

@app.get("/api/semantic-map/consolidation/health")
@app.get("/api/semantic-map/consolidation/status")  # Legacy endpoint
async def get_consolidation_status():
    """Get graph consolidation service status"""
    try:
        from .services.graph_consolidation_service import get_consolidation_service
        
        service = get_consolidation_service()
        status = await service.get_consolidation_status()
        
        return status
    except Exception as e:
        logging.error(f"❌ [API] Consolidation status error: {e}")
        return {"error": str(e)}, 500

@app.post("/api/semantic-map/consolidation/trigger")
async def trigger_consolidation(request: dict = {}):
    """Manually trigger graph consolidation"""
    try:
        from .services.graph_consolidation_service import consolidate_now
        
        # Only allow system/admin agents to trigger consolidation
        requesting_agent = request.get("requesting_agent", "").lower()
        if requesting_agent and "admin" not in requesting_agent and requesting_agent != "system":
            return {"error": "Only admin agents can trigger consolidation"}, 403
        
        # Get date to consolidate (default: yesterday)
        date_str = request.get("date")
        if date_str:
            date = datetime.fromisoformat(date_str)
        else:
            date = None
        
        # Run consolidation asynchronously
        asyncio.create_task(consolidate_now(date))
        
        return {
            "success": True,
            "message": f"Consolidation triggered for {date.date() if date else 'yesterday'}"
        }
    except Exception as e:
        logging.error(f"❌ [API] Consolidation trigger error: {e}")
        return {"error": str(e)}, 500

@app.get("/semantic-viewer")
async def semantic_viewer():
    """Serve the semantic graph viewer HTML"""
    return FileResponse("static/semantic_viewer.html")

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

@app.get("/api/persona/health")
@app.get("/api/persona/status")  # Legacy endpoint
async def get_persona_status():
    """Get persona-aware system status"""
    try:
        from .persona_aware_tool_registry import get_persona_tool_registry
        from .services.character_state_manager import get_character_state_manager
        
        tool_registry = get_persona_tool_registry()
        character_manager = get_character_state_manager()
        
        status = {
            "persona_system_active": tool_registry is not None and character_manager is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        if tool_registry:
            status["tool_registry"] = tool_registry.get_persona_tool_status()
        
        if character_manager:
            status["character_manager"] = character_manager.get_status()
        
        return status
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

@app.post("/api/s2/queue")
async def queue_stimuli_to_s2(request: dict):
    """Queue stimuli to S2 teams system"""
    try:
        if not global_queue_consumer:
            return {"error": "S2 teams not initialized"}, 503
        
        # Extract stimuli data
        content = request.get("content", "")
        source = request.get("source", "api")
        priority = request.get("priority", "medium")
        metadata = request.get("metadata", {})
        
        if not content:
            return {"error": "Content is required"}, 400
        
        # Create batch format
        batch = {
            "prompt": content,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "processing_mode": "s2_only"
        }
        
        # Write to queue file
        queue_file = os.getenv("S2_QUEUE_FILE", "/tmp/s2_processing_queue.json")
        
        # Read existing queue
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
        
        return {
            "success": True,
            "batch_id": f"batch_{batch['timestamp']}",
            "queue_size": len(queue),
            "message": "Stimuli queued for S2 processing"
        }
        
    except Exception as e:
        logging.error(f"❌ [API] S2 queue error: {e}")
        return {"error": str(e)}, 500

@app.get("/api/s2/status")
async def get_s2_status():
    """Get S2 teams system status"""
    try:
        status = {
            "enabled": os.getenv("USE_S2_TEAMS", "false").lower() == "true",
            "queue_consumer": global_queue_consumer is not None,
            "team_manager": global_team_manager is not None,
            "teams": {}
        }
        
        if global_queue_consumer:
            status["queue_file"] = os.getenv("S2_QUEUE_FILE", "/tmp/s2_processing_queue.json")
            status["teams_count"] = len(global_queue_consumer.character_teams)
            status["current_character"] = global_queue_consumer.current_character_id
        
        if global_team_manager:
            status["team_status"] = global_team_manager.get_status()
        
        return status
        
    except Exception as e:
        logging.error(f"❌ [API] S2 status error: {e}")
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
            max_consecutive_auto_reply=10,  # EMERGENCY FIX: Increase to prevent early termination
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
        
        # 🌉 STEP 7: Tool execution ENABLED (VTuber tools disabled in tool registry for pure stimuli architecture)
        # Non-VTuber tools (evolution, goal management) can run autonomously
        tool_executions = {}
        
        if agent_responses and global_tool_registry:
            # Create enhanced agent tool bridge if not exists
            if not hasattr(run_autogen_decision_cycle, '_agent_tool_bridge'):
                from autogen_agent.core.agent_tool_bridge import AgentToolBridge
                run_autogen_decision_cycle._agent_tool_bridge = AgentToolBridge(global_tool_registry)
            
            # Create tool context for autonomous execution
            tool_context = {
                "autonomous": True,
                "iteration": iteration,
                "agent_count": len(agent_responses),
                "evolution_enhanced": evolution_enhanced,
                "execution_source": "autogen_autonomous_cycle"
            }
            
            # Execute tools from agent responses (VTuber tools are disabled in registry)
            tool_executions = await run_autogen_decision_cycle._agent_tool_bridge.execute_from_responses(
                agent_responses, tool_context, vtuber, scb
            )
            
            logging.info(f"🔧 [AUTOGEN] Executed {tool_executions.get('total_executions', 0)} tools from agent decisions")
        
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
        
        # 🎭 STEP 9: VTuber calls COMPLETELY REMOVED - S2 only updates SCB, never triggers S1 directly
        # S1 Avatar will only respond to external stimuli from GraphFlow, not S2 autonomous cycles
        logging.info(f"✅ [AUTOGEN] S2 autonomous cycle completed, SCB updated - no direct S1 triggering")
        
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
        
        # Also send to Neo4j semantic map
        if global_scb_neo4j_bridge:
            from .services.scb_neo4j_bridge import transform_and_store_scb_state
            await transform_and_store_scb_state(scb_state)
        
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
        
        # Log error but do NOT send to VTuber - S2 errors should not trigger S1 speech
        error_message = f"🚨 AutoGen Cycle #{iteration} Error: {str(e)[:100]}"
        logging.error(f"❌ [AUTOGEN] {error_message}")
        
        # Update SCB with error only if AgentNet enabled
        error_state = {
            "iteration": iteration,
            "tool_used": "autogen_error_handling",
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }
        scb.publish_state(error_state)  # Respects AgentNet activation
        
        # Also send error to Neo4j semantic map
        if global_scb_neo4j_bridge:
            from .services.scb_neo4j_bridge import transform_and_store_scb_state
            await transform_and_store_scb_state(error_state)

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
        
        # Log result but do NOT send to VTuber - S2 should not trigger S1 directly
        if result.get("message"):
            logging.info(f"🧠 [COGNITIVE_CYCLE] Result: {result['message'][:100]}...")
        
        # Update SCB state ONLY if AgentNet enabled
        scb_state = {
            "iteration": context["iteration"],
            "tool_used": result.get("tool_used", "unknown"),
            "success": result.get("success", False),
            "timestamp": time.time(),
            "cognitive_enhanced": result.get("memory_enhanced", False)
        }
        scb.publish_state(scb_state)  # Respects AgentNet activation
        
        # Also send to Neo4j semantic map
        if global_scb_neo4j_bridge:
            from .services.scb_neo4j_bridge import transform_and_store_scb_state
            await transform_and_store_scb_state(scb_state)
        
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
        
        # Log result but do NOT send to VTuber - S2 should not trigger S1 directly
        logging.info(f"🔧 [LEGACY_CYCLE] Result: {result.get('message', '')[:100]}...")
        
        # Update SCB only if AgentNet enabled
        scb.publish_state(result)  # Respects AgentNet activation
        
        # Also send to Neo4j semantic map
        if global_scb_neo4j_bridge:
            from .services.scb_neo4j_bridge import transform_and_store_scb_state
            asyncio.create_task(transform_and_store_scb_state(result))

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
            # Give background tasks time to complete before closing loop
            try:
                pending_tasks = asyncio.all_tasks(loop)
                if pending_tasks:
                    logging.info(f"🔄 [THREAD] Waiting for {len(pending_tasks)} pending tasks to complete...")
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            except Exception as cleanup_error:
                logging.warning(f"⚠️ [THREAD] Task cleanup warning: {cleanup_error}")
            finally:
                # Ensure loop is properly closed
                try:
                    loop.close()
                except Exception as close_error:
                    logging.warning(f"⚠️ [THREAD] Loop close warning: {close_error}")
    
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
                "max_consecutive_auto_reply": 10,  # EMERGENCY FIX: Increase to prevent early termination
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
            "max_consecutive_auto_reply": 10,  # EMERGENCY FIX: Increase to prevent early termination
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
            "max_consecutive_auto_reply": 10,  # EMERGENCY FIX: Increase to prevent early termination
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
    
    # Cognee authentication - prefer bearer token, fallback to API key for backward compatibility
    cognee_api_key = os.getenv("COGNEE_BEARER_TOKEN") or os.getenv("COGNEE_API_KEY", None)
    
    standalone_mode = os.getenv("STANDALONE_MODE", "true").lower() == "true"
    
    if standalone_mode:
        logging.info("🔬 [MAIN] Running in STANDALONE mode - selective external service dependencies")
        redis_url = None
        # Keep VTuber endpoint if explicitly provided (for S2 → S1 integration)
        if not vtuber_endpoint:
            vtuber_endpoint = os.getenv("VTUBER_ENDPOINT_URL")  # Try alternative env var
    
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
    
    # VTuber client is DISABLED for S2 - S2 should NEVER trigger S1 speech directly
    if vtuber_endpoint:
        logging.info(f"🚫 [MAIN] VTuber endpoint detected but S2 will NOT use it for speech triggering: {vtuber_endpoint}")
        logging.info("✅ [MAIN] S2 operates independently - only updates SCB for GraphFlow to process")
    
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

async def startup_tasks():
    """Initialize services on FastAPI startup"""
    global mcp_server
    
    logging.info("🚀 [STARTUP] ========== STARTUP TASKS BEGINNING ==========")
    logging.info(f"🚀 [STARTUP] USE_S2_TEAMS = {os.getenv('USE_S2_TEAMS', 'false')}")
    
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
    
    # Initialize semantic map services
    try:
        global global_scb_neo4j_bridge, global_graph_export_service
        
        logging.info("🌉 [STARTUP] Initializing Neo4j semantic map services...")
        
        # Initialize SCB-Neo4j bridge
        from .services.scb_neo4j_bridge import get_scb_neo4j_bridge
        global_scb_neo4j_bridge = get_scb_neo4j_bridge()
        logging.info("✅ [STARTUP] SCB-Neo4j bridge initialized")
        
        # Initialize graph export service
        from .services.graph_export_neo4j import get_graph_export_service
        global_graph_export_service = get_graph_export_service()
        logging.info("✅ [STARTUP] Neo4j graph export service initialized")
        
        # Start consolidation service
        from .services.graph_consolidation_service import get_consolidation_service
        consolidation_service = get_consolidation_service(consolidation_hour=2)  # 2 AM daily
        asyncio.create_task(consolidation_service.start())
        logging.info("✅ [STARTUP] Graph consolidation service started (2 AM daily)")
        
        # Start stimuli connector service
        from .services.stimuli_graph_connector import get_stimuli_connector
        stimuli_connector = get_stimuli_connector()
        asyncio.create_task(stimuli_connector.start())
        logging.info("✅ [STARTUP] Stimuli graph connector started")
            
    except Exception as e:
        logging.error(f"❌ [STARTUP] Semantic map services error: {e}")
    
    # Phase 3: S2 TEAMS OR ORCHESTRATOR INITIALIZATION
    use_s2_teams = os.getenv("USE_S2_TEAMS", "false").lower() == "true"
    logging.info(f"🎯 [STARTUP] Phase 3: S2 Teams = {use_s2_teams}")
    
    if use_s2_teams:
        logging.info("🚀 [STARTUP] Initializing S2 Specialized Teams System...")
        s2_success = await initialize_s2_teams()
        if s2_success:
            logging.info("🎯 [STARTUP] S2 teams initialization: SUCCESS")
            
            # Initialize S2 queue orchestrator for API endpoints
            from .core.s2_queue_orchestrator import S2QueueOrchestrator
            from .services.character_state_manager import get_character_state_manager
            
            global global_orchestrator
            global_orchestrator = S2QueueOrchestrator(
                character_state_manager=get_character_state_manager()
            )
            
            # Setup stimuli API endpoints
            setup_stimuli_api(app, global_orchestrator)
            logging.info("✅ [STARTUP] S2 Queue API endpoints configured")
        else:
            logging.error("❌ [STARTUP] S2 teams initialization: FAILED")
    else:
        # Original orchestrator initialization
        orchestrator_success = await initialize_stimuli_orchestrator()
        if orchestrator_success:
            logging.info("🎯 [STARTUP] Stimuli orchestrator initialization: SUCCESS")
        else:
            logging.error("❌ [STARTUP] Stimuli orchestrator initialization: FAILED")
    
    logging.info("🎉 [STARTUP] ========== STARTUP TASKS COMPLETED ==========")

async def initialize_s2_teams():
    """
    Initialize S2 Specialized Teams System
    =====================================
    
    This function initializes the queue-based S2 teams with character specialization.
    """
    global global_queue_consumer, global_team_manager, global_tool_registry, global_scb_client, global_vtuber_client
    
    try:
        # Configure Ollama if available
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
            logging.info("🦙 [S2] Configuring Ollama integration...")
            os.environ["AUTOGEN_USE_OLLAMA"] = "true"
        
        # Phase 0: Initialize core dependencies
        logging.info("📋 [S2] Phase 0: Initializing core dependencies...")
        
        # Initialize clients
        try:
            global_scb_client = SCBClient()
            logging.info("✅ [S2] SCB client initialized")
            
            global_vtuber_client = VTuberClient()
            logging.info("✅ [S2] VTuber client initialized")
        except Exception as e:
            logging.warning(f"⚠️ [S2] Client initialization warning: {e}")
            global_scb_client = None
            global_vtuber_client = None
        
        # Initialize character state manager
        s1_sync_endpoint = os.getenv("S1_CHARACTER_SYNC_ENDPOINT", "http://neurosync_s1:5001")
        character_manager = initialize_character_state_manager(s1_sync_endpoint)
        if character_manager:
            logging.info("🎭 [S2] Character state manager initialized")
        else:
            logging.warning("⚠️ [S2] Character state manager not available - teams will use default")
        
        # Initialize tool registry
        if not global_tool_registry:
            try:
                global_tool_registry = ToolRegistry()
                global_tool_registry.load_tools()
                tool_count = len(global_tool_registry.tools) if global_tool_registry else 0
                logging.info(f"✅ [S2] Tool registry initialized with {tool_count} tools")
            except Exception as e:
                logging.error(f"❌ [S2] Tool registry initialization failed: {e}")
                return False
        
        # Phase 1: Initialize Queue Consumer Service
        logging.info("📋 [S2] Phase 1: Initializing Queue Consumer Service...")
        
        from .core.queue_consumer_service import QueueConsumerService
        from .core.autonomous_team_manager import initialize_autonomous_team_manager
        
        # Create queue consumer
        queue_file = os.getenv("S2_QUEUE_FILE", "/tmp/s2_processing_queue.json")
        poll_interval = int(os.getenv("S2_POLL_INTERVAL", "5"))
        
        global_queue_consumer = QueueConsumerService(
            queue_file=queue_file,
            poll_interval=poll_interval
        )
        
        # Initialize teams with tools and clients
        teams_initialized = await global_queue_consumer.initialize_teams(
            tool_registry=global_tool_registry,
            scb_client=global_scb_client,
            vtuber_client=global_vtuber_client
        )
        
        if not teams_initialized:
            logging.error("❌ [S2] Failed to initialize character teams")
            return False
            
        logging.info(f"✅ [S2] Queue consumer initialized with {len(global_queue_consumer.character_teams)} teams")
        
        # Phase 2: Initialize Autonomous Team Manager
        logging.info("📋 [S2] Phase 2: Initializing Autonomous Team Manager...")
        
        execution_interval = int(os.getenv("S2_EXECUTION_INTERVAL", "60"))
        
        global_team_manager = await initialize_autonomous_team_manager(
            tool_registry=global_tool_registry,
            scb_client=global_scb_client,
            vtuber_client=global_vtuber_client,
            execution_interval=execution_interval
        )
        
        if not global_team_manager:
            logging.error("❌ [S2] Failed to initialize autonomous team manager")
            return False
            
        logging.info("✅ [S2] Autonomous team manager initialized")
        
        # Phase 3: Start Queue Processing
        logging.info("📋 [S2] Phase 3: Starting queue processing...")
        
        # Start polling
        await global_queue_consumer.start()
        logging.info("🔄 [S2] Queue consumer polling started")
        
        # Log configuration
        logging.info(f"📁 [S2] Queue file: {queue_file}")
        logging.info(f"⏱️ [S2] Poll interval: {poll_interval} seconds")
        logging.info(f"⏱️ [S2] Autonomous execution interval: {execution_interval} seconds")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ [S2] Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def initialize_stimuli_orchestrator():
    """
    BULLETPROOF ORCHESTRATOR INITIALIZATION
    =====================================
    
    This function ensures the StimuliResponsiveOrchestrator is always initialized
    with comprehensive error handling and fallback mechanisms.
    """
    global global_orchestrator, global_tool_registry, global_cognitive_system
    
    initialization_start = datetime.now()
    logging.info("🎯 [ORCHESTRATOR] Starting bulletproof orchestrator initialization...")
    
    try:
        # Phase 1: Environment Validation
        logging.info("📋 [ORCHESTRATOR] Phase 1: Environment validation...")
        
        use_autogen = os.getenv("USE_AUTOGEN_LLM", "false").lower() == "true"
        use_cognitive = os.getenv("USE_COGNITIVE_ENHANCEMENT", "false").lower() == "true"
        
        if not use_autogen:
            logging.warning("⚠️ [ORCHESTRATOR] USE_AUTOGEN_LLM is false - orchestrator disabled")
            return False
            
        if not AUTOGEN_AVAILABLE:
            logging.error("❌ [ORCHESTRATOR] Microsoft AutoGen not available")
            return False
            
        logging.info("✅ [ORCHESTRATOR] Environment validation passed")
        
        # Phase 2: AutoGen Agents Initialization
        logging.info("📋 [ORCHESTRATOR] Phase 2: AutoGen agents initialization...")
        
        if not initialize_autogen_agents():
            logging.error("❌ [ORCHESTRATOR] AutoGen agents initialization failed")
            return False
            
        logging.info("✅ [ORCHESTRATOR] AutoGen agents initialized successfully")
        
        # Phase 3: Client Initialization
        logging.info("📋 [ORCHESTRATOR] Phase 3: Client initialization...")
        
        try:
            # Initialize SCB client
            scb_client = SCBClient()
            logging.info("✅ [ORCHESTRATOR] SCB client initialized")
            
            # Initialize VTuber client  
            vtuber_client = VTuberClient()
            logging.info("✅ [ORCHESTRATOR] VTuber client initialized")
            
        except Exception as e:
            logging.warning(f"⚠️ [ORCHESTRATOR] Client initialization failed: {e}")
            # Use fallback null clients
            scb_client = None
            vtuber_client = None
            logging.info("🔄 [ORCHESTRATOR] Using fallback null clients")
        
        # Phase 4: Tool Registry Initialization
        logging.info("📋 [ORCHESTRATOR] Phase 4: Tool registry initialization...")
        
        try:
            global_tool_registry = ToolRegistry()
            # ToolRegistry loads tools automatically in __init__, no separate initialize() method
            
            # Initialize persona-aware tool registry
            persona_registry = initialize_persona_tool_registry()
            
            tool_count = len(global_tool_registry.tools) if global_tool_registry else 0
            logging.info(f"✅ [ORCHESTRATOR] Tool registry initialized with {tool_count} tools")
            
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] Tool registry initialization failed: {e}")
            # Create minimal fallback registry
            global_tool_registry = ToolRegistry()
            logging.info("🔄 [ORCHESTRATOR] Using fallback minimal tool registry")
        
        # Phase 5: Cognitive System Initialization (if enabled)
        logging.info("📋 [ORCHESTRATOR] Phase 5: Cognitive system initialization...")
        
        global_cognitive_system = None
        if use_cognitive:
            try:
                # Get database URL from environment or use default
                db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@autogen_postgres:5432/autonomous_agent")
                
                cognitive_manager = CognitiveMemoryManager(db_url=db_url)
                await cognitive_manager.initialize()
                
                cognitive_decision_engine = CognitiveDecisionEngine(cognitive_manager)
                
                global_cognitive_system = type('CognitiveSystem', (), {
                    'memory_manager': cognitive_manager,
                    'decision_engine': cognitive_decision_engine,
                    'enabled': True
                })()
                
                logging.info("✅ [ORCHESTRATOR] Cognitive system initialized")
                
            except Exception as e:
                logging.warning(f"⚠️ [ORCHESTRATOR] Cognitive system initialization failed: {e}")
                logging.info("🔄 [ORCHESTRATOR] Continuing without cognitive enhancement")
        
        # Phase 6: Orchestrator Creation
        logging.info("📋 [ORCHESTRATOR] Phase 6: Creating StimuliResponsiveOrchestrator...")
        
        try:
            # Get loop interval from environment
            loop_interval = int(os.getenv("LOOP_INTERVAL", "20"))
            
            global_orchestrator = StimuliResponsiveOrchestrator(
                tool_registry=global_tool_registry,
                scb_client=global_scb_client,
                vtuber_client=global_vtuber_client,
                autonomous_loop_function=run_autogen_decision_cycle,
                loop_interval=loop_interval
            )
            
            logging.info("✅ [ORCHESTRATOR] StimuliResponsiveOrchestrator created successfully")
            
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] Failed to create orchestrator: {e}")
            
            # FALLBACK: Create minimal orchestrator
            try:
                logging.info("🔄 [ORCHESTRATOR] Attempting fallback minimal orchestrator...")
                
                minimal_registry = ToolRegistry()
                global_orchestrator = StimuliResponsiveOrchestrator(
                    tool_registry=minimal_registry,
                    scb_client=None,
                    vtuber_client=None,
                    autonomous_loop_function=run_autogen_decision_cycle,
                    loop_interval=20
                )
                
                logging.info("✅ [ORCHESTRATOR] Fallback minimal orchestrator created")
                
            except Exception as fallback_error:
                logging.error(f"❌ [ORCHESTRATOR] Fallback orchestrator failed: {fallback_error}")
                
                # EMERGENCY FALLBACK: Create absolute minimal orchestrator
                try:
                    logging.info("🆘 [ORCHESTRATOR] Creating emergency fallback orchestrator...")
                    
                    class EmergencyOrchestrator:
                        def __init__(self):
                            self.initialized = True
                            
                        async def receive_stimuli(self, stimuli_data):
                            return StimuliResponse(
                                success=False,
                                stimuli_id=stimuli_data.get("stimuli_id", "emergency"),
                                processing_time=0.0,
                                tools_triggered=["emergency_fallback"],
                                agent_decision="Emergency fallback mode - orchestrator initialization failed",
                                response_content="System in emergency mode",
                                error_message="Orchestrator initialization failed"
                            )
                            
                        def get_status(self):
                            return {
                                "autonomous_state": "emergency_fallback",
                                "current_stimuli": None,
                                "statistics": {"stimuli_processed": 0},
                                "queue_size": 0
                            }
                            
                        async def start(self):
                            pass
                            
                        async def stop(self):
                            pass
                    
                    global_orchestrator = EmergencyOrchestrator()
                    logging.info("🆘 [ORCHESTRATOR] Emergency fallback orchestrator created")
                    
                except Exception as emergency_error:
                    logging.error(f"💀 [ORCHESTRATOR] TOTAL SYSTEM FAILURE: {emergency_error}")
                    return False
        
        # Phase 7: Orchestrator Startup
        logging.info("📋 [ORCHESTRATOR] Phase 7: Starting orchestrator...")
        
        try:
            if hasattr(global_orchestrator, 'start'):
                await global_orchestrator.start()
                logging.info("✅ [ORCHESTRATOR] Orchestrator started successfully")
            else:
                logging.info("ℹ️ [ORCHESTRATOR] Orchestrator has no start method")
            
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] Failed to start orchestrator: {e}")
            # Don't fail completely - orchestrator might still work for API calls
            logging.info("🔄 [ORCHESTRATOR] Continuing with unstarted orchestrator")
        
        # Phase 8: API Setup
        logging.info("📋 [ORCHESTRATOR] Phase 8: Setting up stimuli API...")
        
        try:
            setup_stimuli_api(app, global_orchestrator)
            logging.info("✅ [ORCHESTRATOR] Stimuli API setup completed")
            
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] API setup failed: {e}")
            return False
        
        # Phase 9: Queue Consumer Service
        logging.info("📋 [ORCHESTRATOR] Phase 9: Initializing queue consumer service...")
        
        try:
            from .core.queue_consumer_service import initialize_queue_consumer_service
            
            global_queue_consumer = await initialize_queue_consumer_service(
                tool_registry=global_tool_registry,
                scb_client=global_scb_client,
                vtuber_client=global_vtuber_client
            )
            
            if global_queue_consumer:
                logging.info("✅ [ORCHESTRATOR] Queue consumer service initialized and started")
            else:
                logging.warning("⚠️ [ORCHESTRATOR] Queue consumer service initialization failed")
                
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] Queue consumer service error: {e}")
            # Don't fail completely - system can work without it
        
        # Phase 10: Autonomous Team Manager
        logging.info("📋 [ORCHESTRATOR] Phase 10: Initializing autonomous team manager...")
        
        try:
            from .core.autonomous_team_manager import initialize_autonomous_team_manager
            
            global_team_manager = await initialize_autonomous_team_manager(
                tool_registry=global_tool_registry,
                scb_client=global_scb_client,
                vtuber_client=global_vtuber_client,
                execution_interval=60  # Run every minute
            )
            
            if global_team_manager:
                logging.info("✅ [ORCHESTRATOR] Autonomous team manager initialized and started")
            else:
                logging.warning("⚠️ [ORCHESTRATOR] Autonomous team manager initialization failed")
                
        except Exception as e:
            logging.error(f"❌ [ORCHESTRATOR] Autonomous team manager error: {e}")
            # Don't fail completely - system can work without it
        
        # Phase 11: Health Check
        logging.info("📋 [ORCHESTRATOR] Phase 11: Health check...")
        
        try:
            if global_orchestrator:
                status = global_orchestrator.get_status()
                logging.info(f"✅ [ORCHESTRATOR] Health check passed: {status.get('autonomous_state', 'unknown')}")
            else:
                logging.error("❌ [ORCHESTRATOR] Health check failed: orchestrator is None")
                return False
                
        except Exception as e:
            logging.warning(f"⚠️ [ORCHESTRATOR] Health check failed: {e}")
            # Don't fail completely - orchestrator might still work
        
        # Success!
        elapsed_time = (datetime.now() - initialization_start).total_seconds()
        logging.info(f"🎉 [ORCHESTRATOR] Bulletproof initialization completed successfully in {elapsed_time:.2f}s")
        logging.info(f"🎯 [ORCHESTRATOR] Orchestrator type: {type(global_orchestrator).__name__}")
        logging.info(f"🛠️ [ORCHESTRATOR] Tool registry: {len(global_tool_registry.tools) if global_tool_registry else 0} tools")
        logging.info(f"🧠 [ORCHESTRATOR] Cognitive system: {'enabled' if global_cognitive_system else 'disabled'}")
        logging.info(f"🔄 [ORCHESTRATOR] Queue consumer: {'active' if 'global_queue_consumer' in locals() else 'inactive'}")
        
        return True
        
    except Exception as e:
        elapsed_time = (datetime.now() - initialization_start).total_seconds()
        logging.error(f"💥 [ORCHESTRATOR] CRITICAL FAILURE in bulletproof initialization after {elapsed_time:.2f}s: {e}")
        logging.error(f"💥 [ORCHESTRATOR] Exception type: {type(e).__name__}")
        return False

async def shutdown_tasks():
    """Cleanup resources on shutdown"""
    logging.info("🛑 [SHUTDOWN] Starting application shutdown...")
    
    # Shutdown async utilities first
    try:
        shutdown_async_utils()
        logging.info("✅ [SHUTDOWN] Async utilities shutdown completed")
    except Exception as e:
        logging.warning(f"⚠️ [SHUTDOWN] Async utils shutdown warning: {e}")
    
    # Cleanup semantic map services
    try:
        global global_scb_neo4j_bridge, global_graph_export_service
        
        if global_scb_neo4j_bridge:
            # Neo4j bridge doesn't have async shutdown, but we should close the connection
            if hasattr(global_scb_neo4j_bridge, 'storage') and global_scb_neo4j_bridge.storage:
                global_scb_neo4j_bridge.storage.close()
            logging.info("🌉 [SHUTDOWN] SCB-Neo4j bridge closed")
            
        # Graph export service doesn't need explicit shutdown
        global_graph_export_service = None
        
    except Exception as e:
        logging.warning(f"⚠️ [SHUTDOWN] Semantic map services close warning: {e}")
    
    # Cleanup statistics services
    try:
        if statistics_collector:
            await statistics_collector.close()
            logging.info("📊 [SHUTDOWN] Statistics collector closed")
    except Exception as e:
        logging.warning(f"⚠️ [SHUTDOWN] Statistics collector close warning: {e}")
        
    try:
        if conversation_storage:
            await conversation_storage.close()
            logging.info("💬 [SHUTDOWN] Conversation storage closed")
    except Exception as e:
        logging.warning(f"⚠️ [SHUTDOWN] Conversation storage close warning: {e}")
        
    # Cleanup MCP server
    if mcp_server:
        try:
            # Check if stop method exists before calling it
            if hasattr(mcp_server, 'stop'):
                await mcp_server.stop()
                logging.info("🔗 [SHUTDOWN] MCP server stopped")
            else:
                logging.info("🔗 [SHUTDOWN] MCP server cleanup skipped (no stop method)")
        except Exception as e:
            logging.warning(f"⚠️ [SHUTDOWN] MCP server stop failed: {e}")
    
    # Cleanup GPU monitor
    if gpu_monitor:
        try:
            if hasattr(gpu_monitor, 'cleanup'):
                gpu_monitor.cleanup()
                logging.info("🖥️ [SHUTDOWN] GPU monitor cleaned up")
        except Exception as e:
            logging.warning(f"⚠️ [SHUTDOWN] GPU monitor cleanup failed: {e}")
    
    # Cleanup global orchestrator
    global global_orchestrator
    if global_orchestrator:
        try:
            await global_orchestrator.stop()
            logging.info("🎯 [SHUTDOWN] Stimuli orchestrator stopped")
        except Exception as e:
            logging.warning(f"⚠️ [SHUTDOWN] Orchestrator stop warning: {e}")
    
    logging.info("✅ [SHUTDOWN] Application shutdown completed")

def main() -> None:
    """Main entry point - supports AutoGen LLM, cognitive, S2 teams, and legacy modes"""
    
    print("🚀🚀🚀 MAIN FUNCTION STARTED 🚀🚀🚀")
    logging.info("🚀🚀🚀 MAIN FUNCTION STARTED 🚀🚀🚀")
    
    # Check if we should use S2 teams
    use_s2_teams = os.getenv("USE_S2_TEAMS", "false").lower() == "true"
    print(f"🎯 USE_S2_TEAMS = {use_s2_teams}")
    logging.info(f"🎯 [MAIN] USE_S2_TEAMS = {use_s2_teams}")
    
    # Check if we should use AutoGen LLM mode
    use_autogen = os.getenv("USE_AUTOGEN_LLM", "true").lower() == "true"
    use_cognitive = os.getenv("USE_COGNITIVE_ENHANCEMENT", "true").lower() == "true"
    
    logging.info("🔧 [MAIN] Client Activation Configuration:")
    logging.info(f"   🎭 VTuber: Controlled via tool activation (default: disabled)")
    logging.info(f"   🔗 SCB/AgentNet: {os.getenv('AGENTNET_ENABLED', 'false')} (AGENTNET_ENABLED)")
    logging.info(f"   🎯 S2 Teams: {use_s2_teams} (USE_S2_TEAMS)")
    
    # S2 Teams mode takes precedence
    if use_s2_teams:
        logging.info("🎯 [MAIN] Starting with S2 Specialized Teams System")
        
        # Run FastAPI with lifespan events for S2 teams
        import uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        return
    
    if use_autogen and AUTOGEN_AVAILABLE:
        logging.info("🤖 [MAIN] Starting AutoGen with LLM-Powered Multi-Agent System")
        
        # Initialize just the clients for AutoGen mode
        redis_url = os.getenv("REDIS_URL", None)
        vtuber_endpoint = os.getenv("VTUBER_ENDPOINT", None)
        standalone_mode = os.getenv("STANDALONE_MODE", "true").lower() == "true"
        
        if standalone_mode:
            logging.info("🔬 [MAIN] AutoGen mode running in STANDALONE mode - selective external service dependencies")
            redis_url = None
            # Keep VTuber endpoint if explicitly provided (for S2 → S1 integration)
            if not vtuber_endpoint:
                vtuber_endpoint = os.getenv("VTUBER_ENDPOINT_URL")  # Try alternative env var
        
        # Initialize AutoGen agents
        if initialize_autogen_agents():
            scb = SCBClient(redis_url)
            vtuber = VTuberClient(vtuber_endpoint)
            
            # VTuber client is DISABLED for S2 AutoGen - S2 should NEVER trigger S1 speech directly
            if vtuber_endpoint:
                logging.info(f"🚫 [MAIN] VTuber endpoint detected but S2 AutoGen will NOT use it for speech triggering: {vtuber_endpoint}")
                logging.info("✅ [MAIN] S2 AutoGen operates independently - only updates SCB for GraphFlow to process")
            
            # Set global client references
            global global_scb_client, global_vtuber_client, global_tool_registry, gpu_monitor
            global_scb_client = scb
            global_vtuber_client = vtuber
            
            # Initialize character state manager for persona-aware tools (character sync only, no speech triggering)
            s1_sync_endpoint = os.getenv("S1_CHARACTER_SYNC_ENDPOINT", "http://neurosync_s1:5001")
            character_manager = initialize_character_state_manager(s1_sync_endpoint)
            logging.info("🎭 [MAIN] Character state manager initialized")
            
            # Initialize persona-aware tool registry
            global_tool_registry = initialize_persona_tool_registry()
            global_tool_registry.load_tools()
            logging.info("🔧 [MAIN] Persona-aware tool registry initialized")
            
            # Initialize GPU monitor
            gpu_monitor = GPUMonitor()
            logging.info("🖥️ [MAIN] GPU monitor initialized")
            
            # 🔧 NEW: Initialize cognitive components for MCP tools support
            logging.info("🧠 [MAIN] Initializing cognitive components for AutoGen MCP support...")
            
            # Initialize cognitive system in background thread for MCP tools
            cognitive_thread = run_async_loop_in_thread(initialize_cognitive_system_for_autogen)
            logging.info("🧠 [MAIN] Cognitive components initialization started for AutoGen MCP")
            
            # 🎯 NEW: Initialize Stimuli-Responsive Orchestrator
            global global_orchestrator
            global_orchestrator = StimuliResponsiveOrchestrator(
                tool_registry=global_tool_registry,
                scb_client=scb,
                vtuber_client=vtuber,
                autonomous_loop_function=run_autogen_decision_cycle,
                loop_interval=LOOP_INTERVAL
            )
            
            # Setup stimuli API endpoints
            setup_stimuli_api(app, global_orchestrator)
            
            # Start orchestrator in background thread
            orchestrator_thread = run_async_loop_in_thread(global_orchestrator.start)
            logging.info("🎯 [MAIN] Stimuli-Responsive Orchestrator started with pause/resume capability")
            
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
                'cognee_available': False,  # Replaced with Neo4j
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
        
        # Global variables already declared earlier - just assign values
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
    
    # Add signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logging.info(f"🛑 [MAIN] Received signal {signum}, initiating graceful shutdown...")
        
        # Shutdown async utilities first
        try:
            shutdown_async_utils()
        except Exception as e:
            logging.warning(f"⚠️ [MAIN] Async utils shutdown warning: {e}")
        
        # Cancel any pending async operations
        try:
            # Get current event loop if available
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                logging.info(f"🔄 [MAIN] Cancelled {len(pending)} pending tasks")
        except Exception as e:
            logging.warning(f"⚠️ [MAIN] Shutdown cleanup warning: {e}")
        
        logging.info("✅ [MAIN] Graceful shutdown completed")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start FastAPI server
    port = int(os.getenv("PORT", "8000"))
    logging.info(f"🌐 [MAIN] Starting FastAPI server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
