"""
Orchestrator Main Entry Point
Lightweight, fast routing agent for VTuber system
Version: 2.0.1 - Test Update
"""
import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import structlog
from prometheus_client import Counter, Histogram, generate_latest

from .orchestrator_agent import OrchestratorAgent
from .api_registry import APIRegistry
from .models import StimulusRequest, RoutingDecision

# Setup structured logging
logger = structlog.get_logger()

# Metrics - Use a custom registry to avoid conflicts
from prometheus_client.registry import CollectorRegistry
metrics_registry = CollectorRegistry()

routing_counter = Counter('orchestrator_routing_total', 'Total routing decisions', ['system', 'persona'], registry=metrics_registry)
routing_latency = Histogram('orchestrator_routing_duration_seconds', 'Routing decision latency', registry=metrics_registry)
api_errors = Counter('orchestrator_api_errors_total', 'Total API errors', ['error_type'], registry=metrics_registry)

# Initialize FastAPI
app = FastAPI(title="VTuber Orchestrator", version="1.0.0")

# Global instances
orchestrator: OrchestratorAgent = None
api_registry: APIRegistry = None


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator and load API registry"""
    global orchestrator, api_registry
    
    logger.info("Starting VTuber Orchestrator...")
    
    # Load API registry
    api_registry = APIRegistry("/config/api_registry.yaml")
    await api_registry.load()
    
    # Initialize orchestrator agent
    orchestrator = OrchestratorAgent(api_registry)
    await orchestrator.initialize()
    
    logger.info("Orchestrator started successfully", 
                available_apis=list(api_registry.apis.keys()))


@app.post("/route")
async def route_stimulus(request: StimulusRequest) -> RoutingDecision:
    """
    Main routing endpoint - decides where to send stimuli
    Target latency: < 10ms
    """
    start_time = time.time()
    
    try:
        # Make routing decision
        with routing_latency.time():
            decision = await orchestrator.route(request)
        
        # Log decision
        logger.info("Routing decision made",
                   stimulus_id=request.stimulus_id,
                   preview=request.text[:50],
                   decision=decision.system,
                   latency_ms=int((time.time() - start_time) * 1000))
        
        # Update metrics
        routing_counter.labels(
            system=decision.system,
            persona=decision.config.get("persona", "none")
        ).inc()
        
        return decision
        
    except Exception as e:
        api_errors.labels(error_type=type(e).__name__).inc()
        logger.error("Routing error", error=str(e), stimulus_id=request.stimulus_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute")
async def execute_routing(decision: RoutingDecision):
    """
    Execute the routing decision by calling appropriate APIs
    """
    try:
        result = await orchestrator.execute_routing(decision)
        return result
    except Exception as e:
        api_errors.labels(error_type=type(e).__name__).inc()
        logger.error("Execution error", error=str(e), decision=decision)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process")
async def process_stimulus(request: StimulusRequest):
    """
    Combined endpoint that routes and executes in one call
    This is the main endpoint to use for processing stimuli
    """
    start_time = time.time()
    
    try:
        # First, make routing decision
        decision = await orchestrator.route(request)
        
        # Log the decision
        logger.info("Processing stimulus",
                   stimulus_id=request.stimulus_id,
                   routing=decision.system,
                   latency_ms=decision.latency_ms)
        
        # Then execute it
        result = await orchestrator.execute_routing(decision)
        
        # Return combined result
        total_latency = int((time.time() - start_time) * 1000)
        return {
            "stimulus_id": request.stimulus_id,
            "routing_decision": decision.dict(),
            "execution_results": result,
            "total_latency_ms": total_latency,
            "success": True
        }
        
    except Exception as e:
        api_errors.labels(error_type=type(e).__name__).inc()
        logger.error("Processing error", error=str(e), stimulus_id=request.stimulus_id)
        return {
            "stimulus_id": request.stimulus_id,
            "error": str(e),
            "success": False
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "apis": {}
    }
    
    # Check each API
    for api_name, api_config in api_registry.apis.items():
        is_healthy = await api_registry.check_health(api_name)
        health_status["apis"][api_name] = "healthy" if is_healthy else "unhealthy"
    
    # Overall health
    if all(status == "healthy" for status in health_status["apis"].values()):
        return health_status
    else:
        return JSONResponse(status_code=503, content=health_status)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(metrics_registry)


@app.get("/api/registry")
async def get_registry():
    """Return current API registry for debugging"""
    return api_registry.apis


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
        }
    )