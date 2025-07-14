"""
Simplified S2 AutoGen Agent
==========================

Focused on 3 specialized teams:
- Trader (market analysis)
- Educator (teaching)
- Streamer (content creation)

With SCB and Neo4j integration for memory.
"""

import os
import asyncio
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .core.s2_queue_orchestrator import S2QueueOrchestrator
from .core.simplified_queue_consumer import initialize_queue_consumer, get_queue_consumer
from .api.stimuli_api import setup_stimuli_api
from .services.character_state_manager import initialize_character_state_manager
from .clients.scb_v2_client import SCBv2Client
from .services.neo4j_semantic_storage import Neo4jSemanticStorage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add startup logging immediately
print("🔥 [MODULE] simplified_main.py loaded")
logging.info("🔥 [MODULE] simplified_main.py logging initialized")

# Global instances
global_orchestrator = None
global_queue_consumer = None
global_scb_client = None
global_neo4j_client = None

# Track if we've done manual startup
_manual_startup_done = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown."""
    
    global _manual_startup_done
    
    print("🔄 [LIFESPAN] Starting FastAPI application...")
    logging.info("🔄 [LIFESPAN] Starting FastAPI application...")
    
    # Startup
    try:
        print("🚀 [LIFESPAN] Running startup tasks...")
        logging.info("🚀 [LIFESPAN] Running startup tasks...")
        await startup_tasks()
        print("✅ [LIFESPAN] Startup tasks completed")
        logging.info("✅ [LIFESPAN] Startup tasks completed")
    except Exception as e:
        print(f"❌ [LIFESPAN] Startup failed: {e}")
        logging.error(f"❌ [LIFESPAN] Startup failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    yield
    
    # Shutdown
    try:
        print("🛑 [LIFESPAN] Running shutdown tasks...")
        await shutdown_tasks()
        print("✅ [LIFESPAN] Shutdown tasks completed")
        logging.info("✅ [LIFESPAN] Shutdown tasks completed")
    except Exception as e:
        print(f"❌ [LIFESPAN] Shutdown failed: {e}")
        logging.error(f"❌ [LIFESPAN] Shutdown failed: {e}")


# Create FastAPI app
app = FastAPI(
    title="S2 Simplified AutoGen Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "s2_teams_enabled": True
    }
    
    # Add S2 status
    if global_queue_consumer:
        health_data["s2_teams_status"] = {
            "enabled": True,
            "queue_consumer": global_queue_consumer is not None,
            "orchestrator": global_orchestrator is not None,
            "queue_file": os.getenv("S2_QUEUE_FILE", "/tmp/s2_queue/s2_processing_queue.json"),
            "queue_stats": global_queue_consumer.get_stats() if global_queue_consumer else {}
        }
    
    # Add stimuli processing status
    if global_orchestrator:
        health_data["stimuli_processing"] = {
            "stimuli_processing": True,
            "ready_for_stimuli": True,
            "autonomous_state": "running"
        }
    
    return health_data


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for Prometheus monitoring."""
    import psutil
    
    global global_orchestrator, global_queue_consumer, global_scb_client, global_neo4j_client
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # Check service status
    orchestrator_running = 1 if global_orchestrator else 0
    queue_consumer_running = 1 if global_queue_consumer else 0
    scb_connected = 1 if global_scb_client else 0
    neo4j_connected = 1 if global_neo4j_client else 0
    
    # Get queue stats if available
    queue_size = 0
    if global_queue_consumer and hasattr(global_queue_consumer, 'get_stats'):
        try:
            stats = global_queue_consumer.get_stats()
            queue_size = stats.get('queue_size', 0) if isinstance(stats, dict) else 0
        except:
            queue_size = 0
    
    # Generate Prometheus-formatted metrics
    metrics_text = f"""# HELP autogen_cpu_percent CPU usage percentage
# TYPE autogen_cpu_percent gauge
autogen_cpu_percent{{service="autogen-agent"}} {cpu_percent}

# HELP autogen_memory_percent Memory usage percentage  
# TYPE autogen_memory_percent gauge
autogen_memory_percent{{service="autogen-agent"}} {memory.percent}

# HELP autogen_memory_available Available memory in bytes
# TYPE autogen_memory_available gauge
autogen_memory_available{{service="autogen-agent"}} {memory.available}

# HELP autogen_memory_total Total memory in bytes
# TYPE autogen_memory_total gauge
autogen_memory_total{{service="autogen-agent"}} {memory.total}

# HELP autogen_uptime Service uptime in seconds
# TYPE autogen_uptime counter
autogen_uptime{{service="autogen-agent"}} {time.time()}

# HELP autogen_service_status Service component status (1=running, 0=stopped)
# TYPE autogen_service_status gauge
autogen_service_status{{service="autogen-agent",component="orchestrator"}} {orchestrator_running}
autogen_service_status{{service="autogen-agent",component="queue_consumer"}} {queue_consumer_running}
autogen_service_status{{service="autogen-agent",component="scb_client"}} {scb_connected}
autogen_service_status{{service="autogen-agent",component="neo4j_client"}} {neo4j_connected}

# HELP autogen_queue_size Number of items in processing queue
# TYPE autogen_queue_size gauge
autogen_queue_size{{service="autogen-agent"}} {queue_size}

# HELP autogen_endpoint_status Endpoint availability status (1=available, 0=unavailable)
# TYPE autogen_endpoint_status gauge
autogen_endpoint_status{{service="autogen-agent",endpoint="health"}} 1
autogen_endpoint_status{{service="autogen-agent",endpoint="status"}} 1
autogen_endpoint_status{{service="autogen-agent",endpoint="test_process"}} 1
"""
    
    return Response(content=metrics_text, media_type="text/plain")


@app.get("/api/status")
async def get_status():
    """Get detailed system status."""
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "queue_consumer": "running" if global_queue_consumer else "stopped",
            "orchestrator": "running" if global_orchestrator else "stopped",
            "scb": "connected" if global_scb_client else "disconnected",
            "neo4j": "connected" if global_neo4j_client else "disconnected"
        }
    }
    
    if global_queue_consumer:
        status["queue_stats"] = global_queue_consumer.get_stats()
    
    if global_orchestrator:
        status["orchestrator_stats"] = global_orchestrator.get_status()
    
    return status


@app.post("/api/test/process")
async def test_process_stimuli(request: dict):
    """Test endpoint to process stimuli directly."""
    
    if not global_queue_consumer:
        raise HTTPException(status_code=503, detail="Queue consumer not initialized")
    
    # Get appropriate team
    team_type = request.get("team_type", "educator")
    team = global_queue_consumer.teams.get(team_type)
    
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_type} not found")
    
    # Create stimuli
    stimuli = {
        "stimuli_id": f"test_{datetime.now().timestamp()}",
        "content": request.get("content", "Test stimuli"),
        "metadata": request.get("metadata", {})
    }
    
    # Process
    result = await team.process_stimuli(stimuli)
    
    return {
        "status": "success" if result.get("success") else "failed",
        "result": result
    }


async def startup_tasks():
    """Initialize all services on startup."""
    
    global global_orchestrator, global_queue_consumer, global_scb_client, global_neo4j_client
    
    logging.info("🚀 [STARTUP] Initializing simplified S2 system...")
    
    try:
        # Initialize clients
        logging.info("📡 [STARTUP] Initializing service clients...")
        
        # SCB v2 Client
        try:
            global_scb_client = SCBv2Client()
            logging.info("✅ [STARTUP] SCB client initialized")
        except Exception as e:
            logging.warning(f"⚠️ [STARTUP] SCB client initialization failed: {e}")
            global_scb_client = None
        
        # Neo4j Client
        try:
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
            
            global_neo4j_client = Neo4jSemanticStorage(neo4j_uri, neo4j_user, neo4j_password)
            # No need to call initialize - constructor handles connection
            logging.info("✅ [STARTUP] Neo4j client initialized")
        except Exception as e:
            logging.warning(f"⚠️ [STARTUP] Neo4j client initialization failed: {e}")
            global_neo4j_client = None
        
        # Initialize character state manager
        s1_endpoint = os.getenv("S1_CHARACTER_SYNC_ENDPOINT", "http://neurosync_s1:5001")
        char_manager = initialize_character_state_manager(s1_endpoint)
        logging.info("🎭 [STARTUP] Character state manager initialized")
        
        # Initialize queue consumer with LLM config first
        llm_config = get_llm_config()
        
        global_queue_consumer = await initialize_queue_consumer(
            llm_config=llm_config,
            scb_client=global_scb_client,
            neo4j_client=global_neo4j_client
        )
        
        # Initialize S2 queue orchestrator with queue consumer reference
        global_orchestrator = S2QueueOrchestrator(
            character_state_manager=char_manager,
            queue_consumer=global_queue_consumer
        )
        
        # Setup stimuli API endpoints
        setup_stimuli_api(app, global_orchestrator)
        logging.info("✅ [STARTUP] Stimuli API endpoints configured")
        
        if global_queue_consumer:
            logging.info("✅ [STARTUP] Queue consumer initialized and started")
            logging.info("✅ [STARTUP] S2 queue orchestrator configured with processing state management")
            
            # Start periodic health check task
            asyncio.create_task(periodic_health_check())
            logging.info("✅ [STARTUP] Periodic health check task started")
        else:
            logging.error("❌ [STARTUP] Failed to initialize queue consumer")
            logging.warning("⚠️ [STARTUP] S2 queue orchestrator running without processing state management")
        
        logging.info("🎉 [STARTUP] Simplified S2 system ready!")
        
    except Exception as e:
        logging.error(f"❌ [STARTUP] Initialization error: {e}")
        import traceback
        traceback.print_exc()


async def periodic_health_check():
    """Periodic health check to ensure queue consumer is running."""
    
    health_check_interval = 30  # Check every 30 seconds
    
    while True:
        try:
            await asyncio.sleep(health_check_interval)
            
            if global_queue_consumer and global_queue_consumer.running:
                # Check if processing task is healthy
                if global_queue_consumer.processing_task:
                    if global_queue_consumer.processing_task.done() or global_queue_consumer.processing_task.cancelled():
                        logging.warning("⚠️ [HEALTH_CHECK] Processing task is not healthy, restarting...")
                        try:
                            await global_queue_consumer.restart_processing_task()
                            logging.info("✅ [HEALTH_CHECK] Processing task restarted successfully")
                        except Exception as e:
                            logging.error(f"❌ [HEALTH_CHECK] Failed to restart processing task: {e}")
                else:
                    logging.warning("⚠️ [HEALTH_CHECK] No processing task found, creating one...")
                    try:
                        await global_queue_consumer._ensure_processing_task()
                        logging.info("✅ [HEALTH_CHECK] Processing task created successfully")
                    except Exception as e:
                        logging.error(f"❌ [HEALTH_CHECK] Failed to create processing task: {e}")
            
        except asyncio.CancelledError:
            logging.info("🛑 [HEALTH_CHECK] Health check cancelled")
            break
        except Exception as e:
            logging.error(f"❌ [HEALTH_CHECK] Health check error: {e}")


async def shutdown_tasks():
    """Cleanup on shutdown."""
    
    logging.info("🔄 [SHUTDOWN] Shutting down services...")
    
    # Stop queue consumer
    if global_queue_consumer:
        await global_queue_consumer.stop()
    
    # Close Neo4j connection
    if global_neo4j_client:
        try:
            # Neo4j client may not have async close method
            if hasattr(global_neo4j_client, 'close'):
                await global_neo4j_client.close()
            elif hasattr(global_neo4j_client, '_driver') and global_neo4j_client._driver:
                global_neo4j_client._driver.close()
        except Exception as e:
            logging.warning(f"Warning closing Neo4j: {e}")
    
    logging.info("👋 [SHUTDOWN] Shutdown complete")


def get_llm_config():
    """Get LLM configuration."""
    
    # Check if using Ollama
    if os.getenv("USE_OLLAMA", "true").lower() == "true":
        ollama_host = os.getenv("OLLAMA_HOST", "http://vtuber-ollama:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        
        return {
            "config_list": [{
                "model": ollama_model,
                "base_url": f"{ollama_host}/v1",
                "api_key": "ollama",
                "price": [0, 0]  # Set price to 0 to suppress warnings
            }],
            "temperature": 0.7,
            "max_tokens": 2048,
            "cache_seed": None  # Disable caching for consistent responses
        }
    else:
        # OpenAI configuration
        return {
            "config_list": [{
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "api_key": os.getenv("OPENAI_API_KEY")
            }],
            "temperature": 0.7,
            "max_tokens": 2048,
            "cache_seed": None
        }


print(f"🔍 [MODULE] __name__ = {__name__}")

if __name__ == "__main__":
    print("🚀 [MAIN] __main__ block entered!")
    import uvicorn
    import asyncio
    
    # Add startup logging
    print("🚀 [MAIN] Starting S2 AutoGen Agent...")
    logging.info("🚀 [MAIN] Starting S2 AutoGen Agent...")
    
    # Try manual startup first to debug
    async def manual_startup_test():
        try:
            print("🔍 [DEBUG] Testing manual startup...")
            logging.info("🔍 [DEBUG] Testing manual startup...")
            await startup_tasks()
            print("✅ [DEBUG] Manual startup completed")
            logging.info("✅ [DEBUG] Manual startup completed")
            return True
        except Exception as e:
            print(f"❌ [DEBUG] Manual startup failed: {e}")
            logging.error(f"❌ [DEBUG] Manual startup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Skip manual startup test to avoid dual event loop issue
    # The lifespan function will handle startup tasks properly
    print("⏭️ [MAIN] Skipping manual startup test (will be handled by lifespan)")
    logging.info("⏭️ [MAIN] Skipping manual startup test (will be handled by lifespan)")
    
    # Run with proper lifespan support
    print("🌐 [MAIN] Starting uvicorn server...")
    uvicorn.run(
        app,  # Use the app directly since we're in the same module
        host="0.0.0.0", 
        port=8000,
        reload=False,
        log_level="info"
    )
else:
    print("🔄 [MODULE] Not running as main, module imported")