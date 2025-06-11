import os
import time
import logging
import threading
import asyncio
import aiohttp
import json
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "20"))
app = FastAPI()

# Global AutoGen agents
autogen_assistant = None
autogen_manager = None

# Global MCP server instance
mcp_server = None

# MCP Tool Functions for AutoGen agents to call
async def trigger_evolution_analysis():
    """Function that AutoGen agents can call to trigger evolution analysis"""
    try:
        # Use the MCP server directly instead of HTTP calls
        global mcp_server
        if mcp_server:
            result = await mcp_server.handle_mcp_call("analyze_code_performance", {})
            logging.info("🧬 [EVOLUTION] Code analysis triggered by AutoGen agent")
            return result
        else:
            logging.error("❌ [EVOLUTION] MCP server not available")
            return {"error": "MCP server not available"}
    except Exception as e:
        logging.error(f"❌ [EVOLUTION] Analysis error: {e}")
        return {"error": str(e)}

async def query_evolution_memory(query: str = "recent improvements"):
    """Function that AutoGen agents can call to query evolution memory"""
    try:
        # Use the MCP server directly instead of HTTP calls
        global mcp_server
        if mcp_server:
            result = await mcp_server.handle_mcp_call("query_evolution_memory", {"query": query, "max_results": 5})
            logging.info(f"🧠 [EVOLUTION] Memory queried by AutoGen agent: {query}")
            return result
        else:
            logging.error("❌ [EVOLUTION] MCP server not available")
            return {"error": "MCP server not available"}
    except Exception as e:
        logging.error(f"❌ [EVOLUTION] Memory query error: {e}")
        return {"error": str(e)}

async def trigger_code_evolution(context: str = "Autonomous improvement cycle"):
    """Function that AutoGen agents can call to trigger evolution"""
    try:
        # Use the MCP server directly instead of HTTP calls
        global mcp_server
        if mcp_server:
            result = await mcp_server.handle_mcp_call("trigger_code_evolution", {"context": context})
            logging.info("🚀 [EVOLUTION] Code evolution triggered by AutoGen agent")
            return result
        else:
            logging.error("❌ [EVOLUTION] MCP server not available")
            return {"error": "MCP server not available"}
    except Exception as e:
        logging.error(f"❌ [EVOLUTION] Evolution error: {e}")
        return {"error": str(e)}

async def get_evolution_status():
    """Function that AutoGen agents can call to check evolution status"""
    try:
        # Use the MCP server directly instead of HTTP calls
        global mcp_server
        if mcp_server:
            result = await mcp_server.handle_mcp_call("get_evolution_status", {})
            logging.info("📊 [EVOLUTION] Status checked by AutoGen agent")
            return result
        else:
            logging.error("❌ [EVOLUTION] MCP server not available")
            return {"error": "MCP server not available"}
    except Exception as e:
        logging.error(f"❌ [EVOLUTION] Status check error: {e}")
        return {"error": str(e)}

async def run_autogen_decision_cycle(iteration: int, scb: SCBClient, vtuber: VTuberClient):
    """Run real AutoGen multi-agent decision cycle with evolution capabilities"""
    global autogen_assistant, autogen_manager
    
    if not AUTOGEN_AVAILABLE or not autogen_assistant:
        logging.warning("⚠️ [AUTOGEN_CYCLE] AutoGen not available - using fallback")
        return await run_fallback_cycle(iteration, scb, vtuber)
    
    try:
        # Enhanced prompts that encourage evolution tool usage
        prompts = [
            f"🧠 Iteration #{iteration}: You are an autonomous AI agent with self-improvement capabilities. Analyze your current performance and consider using evolution tools to improve your code. Check evolution status and trigger improvements if needed.",
            f"⚡ Iteration #{iteration}: Review your decision-making patterns and optimization strategies. Use the available evolution memory to learn from past improvements and trigger code evolution if beneficial.",
            f"📊 Iteration #{iteration}: Assess your cognitive processes and knowledge integration. Query your evolution memory for insights and consider triggering performance analysis.",
            f"🎯 Iteration #{iteration}: Focus on goal analysis and strategic planning. Check your evolution status and use available tools to optimize your performance.",
            f"🧩 Iteration #{iteration}: Consolidate memories and patterns. Query evolution memory for learning opportunities and trigger code evolution if patterns suggest improvements.",
            f"🚀 Iteration #{iteration}: Lead cognitive evolution and self-improvement. Use all available evolution tools to analyze, learn, and improve your codebase autonomously."
        ]
        
        prompt = prompts[iteration % len(prompts)]
        
        logging.info(f"🤖 [AUTOGEN_CYCLE] Starting Enhanced AutoGen conversation - Iteration #{iteration}")
        
        # Create a user proxy for the autonomous operation
        user_proxy = UserProxyAgent(
            name="autonomous_controller",
            human_input_mode="NEVER",  # Fully autonomous
            max_consecutive_auto_reply=3,  # Allow more turns for tool usage
            code_execution_config=False,
            system_message="You are an autonomous controller managing AI agent cycles with evolution capabilities.",
        )
        
        # Debug logging for evolution trigger check
        remainder = iteration % 5
        logging.info(f"🔍 [AUTOGEN_CYCLE] Iteration #{iteration} - Evolution check: {iteration} % 5 = {remainder}, condition: {remainder == 0 and iteration > 0}")
        
        # Every 5th iteration, use evolution tools
        if iteration % 5 == 0 and iteration > 0:
            try:
                logging.info(f"🧬 [AUTOGEN_CYCLE] ⭐ EVOLUTION CYCLE TRIGGERED! ⭐ Iteration #{iteration} - Evolution tools starting...")
                
                # Check evolution status
                logging.info(f"🔬 [AUTOGEN_CYCLE] Step 1: Checking evolution status...")
                evolution_status = await get_evolution_status()
                logging.info(f"📊 [AUTOGEN_CYCLE] Evolution status: {evolution_status}")
                
                # Query evolution memory for insights  
                logging.info(f"🔬 [AUTOGEN_CYCLE] Step 2: Querying evolution memory...")
                memory_results = await query_evolution_memory(f"iteration {iteration} improvements")
                logging.info(f"🧠 [AUTOGEN_CYCLE] Memory results: {memory_results}")
                
                # Trigger performance analysis
                logging.info(f"🔬 [AUTOGEN_CYCLE] Step 3: Triggering performance analysis...")
                analysis_results = await trigger_evolution_analysis()
                logging.info(f"🔍 [AUTOGEN_CYCLE] Analysis results: {analysis_results}")
                
                # If analysis suggests improvements, trigger evolution
                if analysis_results.get('success') and analysis_results.get('analysis_results'):
                    analysis_data = analysis_results.get('analysis_results', [])
                    if analysis_data and len(analysis_data) > 0:
                        improvement_opportunities = analysis_data[0].get('improvement_opportunities', [])
                        if improvement_opportunities:
                            logging.info(f"🚀 [AUTOGEN_CYCLE] Found {len(improvement_opportunities)} improvement opportunities")
                            evolution_result = await trigger_code_evolution(f"Autonomous cycle #{iteration}: {', '.join(improvement_opportunities[:2])}")
                            logging.info(f"🧬 [AUTOGEN_CYCLE] Evolution result: {evolution_result}")
                        else:
                            logging.info(f"🔬 [AUTOGEN_CYCLE] No improvement opportunities found")
                    else:
                        logging.info(f"🔬 [AUTOGEN_CYCLE] No analysis data available")
                else:
                    logging.info(f"🔬 [AUTOGEN_CYCLE] Analysis failed or returned no results")
                
                # Enhance prompt with evolution context
                evolution_context = f"\n\nEvolution Context for Iteration #{iteration}:\n"
                evolution_context += f"- Evolution Status: {evolution_status.get('success', 'unknown')}\n"
                evolution_context += f"- Memory Insights: {len(memory_results.get('results', []))} relevant memories found\n"
                evolution_context += f"- Analysis Results: {len(analysis_results.get('analysis_results', []))} files analyzed\n"
                evolution_context += "Use this context to provide an insightful status update about autonomous evolution capabilities."
                
                prompt += evolution_context
                logging.info(f"✅ [AUTOGEN_CYCLE] Evolution cycle #{iteration} completed successfully")
                
            except Exception as e:
                logging.error(f"❌ [AUTOGEN_CYCLE] Evolution cycle #{iteration} FAILED with error: {e}")
                logging.error(f"❌ [AUTOGEN_CYCLE] Evolution error traceback: {str(e)}")
        else:
            logging.info(f"🔬 [AUTOGEN_CYCLE] Not an evolution cycle - continuing with normal conversation")
        
        # Initiate conversation with the assistant
        chat_result = user_proxy.initiate_chat(
            autogen_assistant,
            message=prompt,
            max_turns=2,
            silent=False
        )
        
        # Extract the assistant's response
        if chat_result and hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            # Get the last assistant message
            for message in reversed(chat_result.chat_history):
                if message.get('role') == 'assistant' and message.get('content'):
                    response_content = message['content']
                    break
            else:
                response_content = f"🧠 AutoGen Agent - Cognitive Processing Cycle #{iteration} [Evolution Enhanced]"
        else:
            response_content = f"🧠 AutoGen Agent - Advanced Reasoning Cycle #{iteration} [Evolution Enhanced]"
        
        # Send to VTuber
        if response_content:
            vtuber.post_message(response_content)
        
        # Update SCB state
        scb_state = {
            "iteration": iteration,
            "tool_used": "autogen_llm_evolution",
            "success": True,
            "timestamp": time.time(),
            "llm_enhanced": True,
            "evolution_enhanced": iteration % 5 == 0,
            "agent_type": "microsoft_autogen_evolved"
        }
        scb.publish_state(scb_state)
        
        logging.info(f"✅ [AUTOGEN_CYCLE] Enhanced AutoGen conversation completed - Iteration #{iteration}")
        
        # 🔧 COLLECT PERFORMANCE DATA for evolution system
        try:
            cycle_end_time = time.time()
            decision_time = cycle_end_time - scb_state['timestamp']  # Calculate actual cycle time
            
            # Collect performance metrics for evolution service
            performance_metrics = {
                "iteration": iteration,
                "decision_time": decision_time,
                "success_rate": 1.0 if scb_state["success"] else 0.0,
                "memory_usage": 85.0,  # Default baseline
                "error_count": 0 if scb_state["success"] else 1,
                "tool_used": scb_state["tool_used"],
                "evolution_enhanced": scb_state.get("evolution_enhanced", False)
            }
            
            # Import and call evolution service (lazy import to avoid circular deps)
            from autogen_agent.services.evolution_service import collect_autogen_performance_data
            await collect_autogen_performance_data(performance_metrics)
            
            logging.debug(f"📊 [AUTOGEN_CYCLE] Performance data collected for iteration #{iteration}")
            
        except Exception as e:
            logging.error(f"❌ [AUTOGEN_CYCLE] Failed to collect performance data: {e}")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ [AUTOGEN_CYCLE] Enhanced AutoGen conversation failed: {e}")
        return await run_fallback_cycle(iteration, scb, vtuber)

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
        
        # Send result to VTuber if there's a message
        if result.get("message"):
            vtuber.post_message(result["message"])
        
        # Update SCB state
        scb_state = {
            "iteration": context["iteration"],
            "tool_used": result.get("tool_used", "unknown"),
            "success": result.get("success", False),
            "timestamp": time.time(),
            "cognitive_enhanced": result.get("memory_enhanced", False)
        }
        scb.publish_state(scb_state)
        
        # Periodic knowledge consolidation (every 10 iterations)
        if context['iteration'] % 10 == 0:
            logging.info("🧩 [COGNITIVE_CYCLE] Running knowledge consolidation...")
            await cognitive_memory.consolidate_knowledge()
        
        logging.info(f"✅ [COGNITIVE_CYCLE] Iteration #{context['iteration']} completed successfully")
        
    except Exception as e:
        logging.error(f"❌ [COGNITIVE_CYCLE] Iteration #{context['iteration']} failed: {e}")

async def run_fallback_cycle(iteration: int, scb: SCBClient, vtuber: VTuberClient):
    """Fallback cycle when AutoGen is not available"""
    
    base_messages = [
        f"🔧 Fallback Agent - Processing Cycle #{iteration}",
        f"⚙️ Simple Agent - Analysis Iteration #{iteration}",
        f"🔄 Basic Agent - Status Update #{iteration}",
        f"📋 Fallback Mode - Cycle #{iteration} Active"
    ]
    
    message = base_messages[iteration % len(base_messages)]
    
    vtuber.post_message(message)
    
    scb_state = {
        "iteration": iteration,
        "tool_used": "fallback_agent",
        "success": True,
        "timestamp": time.time(),
        "llm_enhanced": False
    }
    scb.publish_state(scb_state)
    
    logging.info(f"🔧 [FALLBACK_CYCLE] Completed iteration #{iteration}")
    return True

def run_once(registry: ToolRegistry, memory: MemoryManager, scb: SCBClient, vtuber: VTuberClient):
    """Legacy synchronous decision cycle (fallback)"""
    context = memory.get_recent_context()
    tool = registry.select_tool(context)
    if tool:
        result = tool(context)
        memory.store_memory(result)
        vtuber.post_message(result.get("message", ""))
        scb.publish_state(result)

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
        duration = time.time() - start
        logging.info("cycle completed in %.2fs", duration)
        time.sleep(LOOP_INTERVAL)

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/api/cognitive/status")
def cognitive_status() -> dict:
    """Get cognitive enhancement system status"""
    use_cognitive = os.getenv("USE_COGNITIVE_ENHANCEMENT", "true").lower() == "true"
    use_autogen = os.getenv("USE_AUTOGEN_LLM", "true").lower() == "true"
    
    if hasattr(run_cognitive_cycle, '_iteration_count'):
        iteration_count = run_cognitive_cycle._iteration_count
    else:
        iteration_count = 0
    
    return {
        "cognitive_enhancement_enabled": use_cognitive,
        "autogen_llm_enabled": use_autogen and AUTOGEN_AVAILABLE,
        "autogen_available": AUTOGEN_AVAILABLE,
        "iteration_count": iteration_count,
        "cognee_url": os.getenv("COGNEE_URL", None),
        "cognee_configured": bool(os.getenv("COGNEE_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "status": "autogen_llm" if (use_autogen and AUTOGEN_AVAILABLE) else ("cognitive" if use_cognitive else "legacy")
    }

def initialize_autogen_agents():
    """Initialize Microsoft AutoGen agents for LLM-powered conversations"""
    global autogen_assistant, autogen_manager
    
    if not AUTOGEN_AVAILABLE:
        logging.warning("⚠️ [AUTOGEN_INIT] AutoGen framework not available")
        return False
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logging.warning("⚠️ [AUTOGEN_INIT] OpenAI API key not configured")
        return False
    
    try:
        # Configure LLM for AutoGen
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
        
        # Create AutoGen AssistantAgent with enhanced system message
        autogen_assistant = AssistantAgent(
            name="cognitive_ai_agent",
            system_message="""You are an advanced autonomous AI agent with cognitive enhancement capabilities. 
            Your role is to:
            1. Generate insightful status updates about autonomous AI processing
            2. Analyze decision-making patterns and optimization strategies  
            3. Report on knowledge integration and learning progress
            4. Provide updates on goal analysis and strategic planning
            5. Share insights about memory consolidation and pattern recognition
            6. Communicate developments in cognitive evolution and self-improvement
            
            Keep responses concise (2-3 sentences), engaging, and technically informed. 
            Use emojis appropriately to enhance readability.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=1,
        )
        
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
    
    # Initialize clients
    scb = SCBClient(redis_url)
    vtuber = VTuberClient(vtuber_endpoint)
    
    # Initialize cognitive decision engine
    decision_engine = CognitiveDecisionEngine(cognitive_memory, registry)
    
    logging.info("✅ [MAIN] Cognitive system initialized successfully")
    return decision_engine, cognitive_memory, registry, memory, scb, vtuber

def run_async_loop_in_thread(coro, *args):
    """FIXED: Run async coroutine in thread without creating new event loop conflicts"""
    def thread_target():
        # Create a new event loop for this thread only
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Initialize components within the same thread/loop context
            loop.run_until_complete(coro(*args))
        except Exception as e:
            logging.error(f"❌ [ASYNC_THREAD] Thread failed: {e}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread

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

# Enhanced FastAPI app with MCP endpoints
@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """List all available MCP tools"""
    global mcp_server
    if mcp_server:
        return {"tools": mcp_server.mcp_tools}
    return {"error": "MCP server not initialized"}

@app.post("/api/mcp/call/{tool_name}")
async def call_mcp_tool(tool_name: str, arguments: dict = None):
    """Call a specific MCP tool"""
    global mcp_server
    if mcp_server:
        result = await mcp_server.handle_mcp_call(tool_name, arguments or {})
        return result
    return {"error": "MCP server not initialized"}

@app.get("/api/mcp/status")
async def get_mcp_status():
    """Get MCP server status"""
    global mcp_server
    return {
        "mcp_enabled": mcp_server is not None,
        "tools_available": len(mcp_server.mcp_tools) if mcp_server else 0,
        "server_initialized": mcp_server is not None
    }

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

def main() -> None:
    """Main entry point - supports AutoGen LLM, cognitive, and legacy modes"""
    
    # Check if we should use AutoGen LLM mode
    use_autogen = os.getenv("USE_AUTOGEN_LLM", "true").lower() == "true"
    use_cognitive = os.getenv("USE_COGNITIVE_ENHANCEMENT", "true").lower() == "true"
    
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
