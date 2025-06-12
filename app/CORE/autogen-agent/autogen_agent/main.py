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
    "performance_trends": []
}

# Global client instances for tool access
global_scb_client = None
global_vtuber_client = None
global_tool_registry = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "autogen_available": AUTOGEN_AVAILABLE,
        "analytics": {
            "cycles_completed": analytics_data["cycles_completed"],
            "tools_registered": len(global_tool_registry.tools) if global_tool_registry else 0
        }
    }

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

async def run_autogen_decision_cycle(iteration: int, scb: SCBClient, vtuber: VTuberClient):
    """Enhanced AutoGen decision cycle with multi-agent collaboration"""
    
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
        
        # 📊 STEP 7: Update analytics and goal progress
        await update_analytics_and_goals(iteration, agent_responses, evolution_enhanced)
        
        # 🎭 STEP 8: Send to VTuber ONLY if activated (no force_send for autonomous cycles)
        if final_response:
            vtuber.post_message(final_response)  # Respects activation state
        
        # 🔗 STEP 9: Update SCB state ONLY if AgentNet enabled
        scb_state = {
            "iteration": iteration,
            "tool_used": "autogen_multi_agent_collaboration",
            "success": True,
            "timestamp": time.time(),
            "llm_enhanced": True,
            "evolution_enhanced": evolution_enhanced,
            "agent_type": "microsoft_autogen_multi_agent",
            "agents_participated": list(agent_responses.keys()),
            "collaboration_score": len(agent_responses)
        }
        scb.publish_state(scb_state)  # Respects AgentNet activation
        
        analytics_data["cycles_completed"] += 1
        logging.info(f"✅ [AUTOGEN] Multi-agent cycle #{iteration} completed successfully")
        
    except Exception as e:
        logging.error(f"❌ [AUTOGEN] Decision cycle #{iteration} failed: {e}")
        
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

async def update_analytics_and_goals(iteration: int, agent_responses: dict, evolution_enhanced: bool):
    """Update analytics and goal tracking"""
    try:
        # Track tool usage
        for agent_name in agent_responses.keys():
            analytics_data["tools_used"][agent_name] = analytics_data["tools_used"].get(agent_name, 0) + 1
        
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
    global autogen_assistant, autogen_programmer, autogen_observer, autogen_manager
    
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
        
        # Create AutoGen programmer agent
        autogen_programmer = AssistantAgent(
            name="programmer_agent",
            system_message="""You are a specialized programmer agent focused on autonomous system development.
            Your responsibilities include:
            1. Analyzing code performance and suggesting optimizations
            2. Implementing goal-driven code improvements
            3. Writing analytics and monitoring code
            4. Creating tool enhancements and variable function calls
            5. Developing systematic testing and validation procedures
            
            When speaking, focus on technical implementation details, performance metrics, and code quality.
            Always consider how your suggestions align with current system goals.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=1,
        )
        
        # Create AutoGen observer agent
        autogen_observer = AssistantAgent(
            name="observer_agent",
            system_message="""You are a system observer agent specializing in analytics and performance monitoring.
            Your key functions are:
            1. Monitor agent interactions and system performance
            2. Track goal progress and achievement patterns
            3. Identify trends in tool usage and effectiveness
            4. Report on multi-agent coordination and communication
            5. Analyze system behavior and suggest optimization opportunities
            
            Provide analytical insights with specific metrics and data-driven observations.
            Focus on quantitative assessments and pattern recognition.""",
            llm_config=llm_config,
            max_consecutive_auto_reply=1,
        )
        
        # Initialize group chat with all agents
        global group_chat
        group_chat = GroupChat(
            agents=[autogen_assistant, autogen_programmer, autogen_observer],
            messages=[],
            max_round=3  # Allow 3 rounds of conversation per cycle
        )
        
        # Create AutoGen group chat manager
        autogen_manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=llm_config,
            system_message="""You are managing a multi-agent autonomous system with three specialized agents:
            - cognitive_ai_agent: Handles general AI processing and evolution
            - programmer_agent: Focuses on code development and optimization  
            - observer_agent: Monitors performance and provides analytics
            
            Coordinate their interactions to achieve system goals effectively."""
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
    
    # Initialize clients with new activation logic
    scb = SCBClient(redis_url)
    vtuber = VTuberClient(vtuber_endpoint)
    
    # Set global client references for API access
    global global_scb_client, global_vtuber_client, global_tool_registry
    global_scb_client = scb
    global_vtuber_client = vtuber
    global_tool_registry = registry
    
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
            global global_scb_client, global_vtuber_client, global_tool_registry
            global_scb_client = scb
            global_vtuber_client = vtuber
            global_tool_registry = ToolRegistry()
            global_tool_registry.load_tools()
            
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
        global_scb_client = scb
        global_vtuber_client = vtuber
        global_tool_registry = registry
        
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
