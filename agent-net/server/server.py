import os, time, logging, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from server.register import register_to_orchestrator

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

# Hardcoded mock agents with different uptime scenarios for testing
MOCK_AGENTS = {
    "agent-001": {"uptime_percent": 99.5, "description": "Excellent uptime - full rate"},
    "agent-002": {"uptime_percent": 98.0, "description": "Good uptime - 50% rate"},
    "agent-003": {"uptime_percent": 92.0, "description": "Fair uptime - 10% rate"},
    "agent-004": {"uptime_percent": 85.0, "description": "Poor uptime - no jobs"}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting server")
    
    # Register to orchestrator if needed
    if not register_to_orchestrator():
        logger.warning("Failed to register to orchestrator, continuing anyway")
    
    yield
    
    logger.info("Shutting down server")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {"status": "ok"}

@app.post("/gpu-check")
async def gpu_check(request: Request):
    """
    Mock GPU Check Capability - Returns mock GPU information with uptime data
    This endpoint simulates GPU status checks with predefined uptime percentages
    """
    try:
        params = await request.json()
        logger.info(f"GPU check request received: {params}")
        
        # Extract agent_id from params or use default
        agent_id = params.get("agent_id", "agent-001")
        
        # Get mock data for this agent
        mock_agent = MOCK_AGENTS.get(agent_id, MOCK_AGENTS["agent-001"])
        logger.info(f"Using mock data for {agent_id}: {mock_agent['description']}")
        
        # Return mock response with uptime data
        response_data = {
            "status": "success",
            "agent_id": agent_id,
            "uptime_percent": mock_agent["uptime_percent"],
            "timestamp": time.time(),
            "gpu_count": 1,
            "devices": {
                0: {
                    "device_id": 0,
                    "uuid": f"GPU-MOCK-{agent_id}",
                    "name": "Mock GPU RTX 4090",
                    "memory": {
                        "total_bytes": 25769803776,  # 24GB
                        "free_bytes": 20000000000,    # ~18.6GB free
                        "used_bytes": 5769803776,     # ~5.4GB used
                        "usage_percentage": 22.4
                    },
                    "compute_capability": {
                        "major": 8,
                        "minor": 9,
                        "version": "8.9"
                    },
                    "utilization": {
                        "gpu_percent": 15,
                        "memory_percent": 22
                    }
                }
            },
            "system_info": {
                "capability": "gpu-check",
                "version": "1.0",
                "source": "mock_data",
                "description": mock_agent["description"]
            }
        }
        
        return Response(
            content=json.dumps(response_data), 
            media_type="application/json",
            headers={
                "X-Metadata": json.dumps({
                    "capability": "gpu-check",
                    "agent_id": agent_id,
                    "uptime_percent": mock_agent["uptime_percent"],
                    "timestamp": time.time(),
                    "source": "mock_data"
                })
            }
        )
        
    except Exception as e:
        logger.error(f"Error in GPU check: {e}")
        error_response = {
            "status": "error",
            "error": str(e),
            "timestamp": time.time(),
            "capability": "gpu-check"
        }
        return Response(
            content=json.dumps(error_response),
            media_type="application/json",
            status_code=500,
            headers={
                "X-Metadata": json.dumps({
                    "capability": "gpu-check",
                    "status": "error",
                    "timestamp": time.time()
                })
            }
        )

@app.post("/agent-net")
async def agent_net(request: Request):
    """
    Agent-net capability endpoint - routes to GPU check
    """
    params = await request.json()
    logger.info(f"Agent-net request received: {params}")
    
    # Agent-net capability always does GPU check with mock data
    return await gpu_check(request)

