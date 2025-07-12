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

from .core.s2_queue_orchestrator import S2QueueOrchestrator
from .core.simplified_queue_consumer import initialize_queue_consumer, get_queue_consumer
from .api.stimuli_api import setup_stimuli_api
from .services.character_state_manager import initialize_character_state_manager
from .clients.scb_client import SCBClient
from .services.neo4j_semantic_storage import Neo4jSemanticStorage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Global instances
global_orchestrator = None
global_queue_consumer = None
global_scb_client = None
global_neo4j_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown."""
    # Startup
    await startup_tasks()
    yield
    # Shutdown
    await shutdown_tasks()


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
        
        # SCB Client
        try:
            global_scb_client = SCBClient()
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
            await global_neo4j_client.initialize()
            logging.info("✅ [STARTUP] Neo4j client initialized")
        except Exception as e:
            logging.warning(f"⚠️ [STARTUP] Neo4j client initialization failed: {e}")
            global_neo4j_client = None
        
        # Initialize character state manager
        s1_endpoint = os.getenv("S1_CHARACTER_SYNC_ENDPOINT", "http://neurosync_s1:5001")
        char_manager = initialize_character_state_manager(s1_endpoint)
        logging.info("🎭 [STARTUP] Character state manager initialized")
        
        # Initialize S2 queue orchestrator
        global_orchestrator = S2QueueOrchestrator(
            character_state_manager=char_manager
        )
        
        # Setup stimuli API endpoints
        setup_stimuli_api(app, global_orchestrator)
        logging.info("✅ [STARTUP] Stimuli API endpoints configured")
        
        # Initialize queue consumer with LLM config
        llm_config = get_llm_config()
        
        global_queue_consumer = await initialize_queue_consumer(
            llm_config=llm_config,
            scb_client=global_scb_client,
            neo4j_client=global_neo4j_client
        )
        
        if global_queue_consumer:
            logging.info("✅ [STARTUP] Queue consumer initialized and started")
        else:
            logging.error("❌ [STARTUP] Failed to initialize queue consumer")
        
        logging.info("🎉 [STARTUP] Simplified S2 system ready!")
        
    except Exception as e:
        logging.error(f"❌ [STARTUP] Initialization error: {e}")
        import traceback
        traceback.print_exc()


async def shutdown_tasks():
    """Cleanup on shutdown."""
    
    logging.info("🔄 [SHUTDOWN] Shutting down services...")
    
    # Stop queue consumer
    if global_queue_consumer:
        await global_queue_consumer.stop()
    
    # Close Neo4j connection
    if global_neo4j_client:
        await global_neo4j_client.close()
    
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
                "api_key": "ollama"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)