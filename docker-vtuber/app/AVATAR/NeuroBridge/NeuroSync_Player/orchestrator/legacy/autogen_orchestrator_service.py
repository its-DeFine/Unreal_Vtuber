"""
AutoGen Orchestrator Service
===========================

FastAPI service that hosts the AutoGen Orchestrator V3 as a standalone microservice.
This service provides REST APIs for the NeuroSync Player to interact with the
multi-agent orchestration system.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

# Import orchestrator components
from autogen_orchestrator_v3 import (
    AutoGenOrchestratorV3,
    create_autogen_orchestrator_v3
)
from orchestrator_integration_v3 import (
    AutoGenOrchestrationWrapper,
    AutoGenOrchestrationConfig,
    create_autogen_integration
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/orchestrator.log')
    ]
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator_wrapper: Optional[AutoGenOrchestrationWrapper] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage orchestrator lifecycle"""
    global orchestrator_wrapper
    
    logger.info("🚀 Starting AutoGen Orchestrator Service")
    
    try:
        # Create orchestrator configuration
        config = AutoGenOrchestrationConfig()
        
        # Create Flask app for compatibility
        from flask import Flask
        flask_app = Flask(__name__)
        
        # Create orchestrator wrapper
        orchestrator_wrapper = create_autogen_integration(
            flask_app,
            autogen_enabled=True,
            persona=os.getenv('ORCHESTRATOR_PERSONA', 'interactive_streamer')
        )
        
        # Start orchestrator
        await orchestrator_wrapper.start_orchestrator()
        
        logger.info("✅ AutoGen Orchestrator Service started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start orchestrator: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AutoGen Orchestrator Service")
    
    if orchestrator_wrapper:
        await orchestrator_wrapper.stop_orchestrator()
    
    logger.info("✅ AutoGen Orchestrator Service stopped")


# Create FastAPI app
app = FastAPI(
    title="AutoGen Orchestrator V3",
    description="Multi-agent orchestration system for autonomous VTuber",
    version="3.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Main orchestrator endpoints
@app.get("/orchestrator/v3/health")
async def orchestrator_health():
    """Detailed orchestrator health check"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "orchestrator": "unavailable",
            "agents": "unavailable",
            "state_hooks": "unavailable"
        }
    }
    
    if orchestrator_wrapper.orchestrator:
        health["components"]["orchestrator"] = "healthy"
        health["components"]["agents"] = "healthy" if orchestrator_wrapper.orchestrator.agents else "unavailable"
    
    if orchestrator_wrapper.state_hooks:
        health["components"]["state_hooks"] = "healthy"
    
    # Overall status
    if all(status == "healthy" for status in health["components"].values()):
        health["status"] = "healthy"
    elif any(status == "healthy" for status in health["components"].values()):
        health["status"] = "degraded"
    else:
        health["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health)
    
    return health


@app.post("/orchestrator/v3/process")
async def process_input(request: Request):
    """Process external input through AutoGen pipeline"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    data = await request.json()
    
    # Validate required fields
    if 'input_type' not in data or 'content' not in data:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: input_type, content"
        )
    
    # Prepare context
    context = {
        "source": data.get('input_type', 'unknown'),
        "viewer_name": data.get('metadata', {}).get('viewer_name', 'anonymous'),
        "platform": data.get('metadata', {}).get('platform', 'direct'),
        "importance": data.get('metadata', {}).get('importance', 'medium'),
        "timestamp": data.get('metadata', {}).get('timestamp', datetime.now().isoformat())
    }
    
    # Add additional metadata
    if 'metadata' in data:
        context.update(data['metadata'])
    
    try:
        # Process through AutoGen
        result = await orchestrator_wrapper.process_with_autogen(
            text=data['content'],
            context=context
        )
        
        # Update viewer interaction if applicable
        if data['input_type'] == 'viewer_comment' and orchestrator_wrapper.state_hooks:
            orchestrator_wrapper.state_hooks.hook_viewer_interaction(
                viewer_name=context['viewer_name'],
                message=data['content']
            )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error processing input: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrator/v3/status")
async def get_status():
    """Get comprehensive orchestrator status"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    return orchestrator_wrapper.get_comprehensive_status()


@app.get("/orchestrator/v3/persona")
async def get_persona():
    """Get current persona configuration"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    current_persona = orchestrator_wrapper.config.persona
    available_personas = []
    current_config = {}
    
    if orchestrator_wrapper.orchestrator:
        personas = orchestrator_wrapper.orchestrator.config.get('personas', {})
        available_personas = list(personas.keys())
        
        if current_persona in personas:
            persona_obj = personas[current_persona]
            current_config = {
                "name": persona_obj.name,
                "filter_threshold": persona_obj.filter_threshold,
                "idle_behavior": {
                    "min_idle_time": persona_obj.idle_behavior.min_idle_time,
                    "max_idle_time": persona_obj.idle_behavior.max_idle_time,
                    "content_types": persona_obj.idle_behavior.content_types
                }
            }
    
    return {
        "current_persona": current_persona,
        "available_personas": available_personas,
        "config": current_config
    }


@app.put("/orchestrator/v3/persona")
async def update_persona(request: Request):
    """Update current persona"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    data = await request.json()
    
    if 'persona' not in data:
        raise HTTPException(status_code=400, detail="Missing required field: persona")
    
    success = await orchestrator_wrapper.update_persona(data['persona'])
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update persona to {data['persona']}"
        )
    
    return {
        "status": "success",
        "current_persona": data['persona'],
        "message": f"Persona updated to {data['persona']}"
    }


@app.post("/orchestrator/v3/event")
async def handle_event(request: Request):
    """Handle external events"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    data = await request.json()
    
    if 'event_type' not in data or 'payload' not in data:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: event_type, payload"
        )
    
    try:
        await orchestrator_wrapper.handle_external_event(
            event_type=data['event_type'],
            payload=data['payload']
        )
        
        return {
            "status": "success",
            "event_type": data['event_type'],
            "message": f"Event {data['event_type']} processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error handling event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrator/v3/metrics")
async def get_metrics():
    """Get Prometheus-format metrics"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    metrics = orchestrator_wrapper.export_metrics()
    
    # Format as Prometheus text exposition
    output = []
    for metric_name, value in metrics.items():
        output.append(f"# TYPE {metric_name} counter")
        output.append(f"{metric_name} {value}")
    
    # Add additional metrics
    if orchestrator_wrapper.orchestrator:
        output.append("# TYPE autogen_agent_count gauge")
        output.append(f"autogen_agent_count {len(orchestrator_wrapper.orchestrator.agents)}")
    
    return PlainTextResponse(
        content='\n'.join(output),
        media_type='text/plain; version=0.0.4'
    )


@app.post("/orchestrator/v3/activity")
async def update_activity(request: Request):
    """Update current stream activity"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    data = await request.json()
    
    if 'activity' not in data:
        raise HTTPException(status_code=400, detail="Missing required field: activity")
    
    if orchestrator_wrapper.state_hooks:
        orchestrator_wrapper.state_hooks.hook_activity_change(data['activity'])
    
    return {
        "status": "success",
        "current_activity": data['activity'],
        "message": f"Activity updated to {data['activity']}"
    }


@app.post("/orchestrator/v3/viewers")
async def update_viewers(request: Request):
    """Update viewer count"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    data = await request.json()
    
    if 'count' not in data:
        raise HTTPException(status_code=400, detail="Missing required field: count")
    
    orchestrator_wrapper.update_viewer_count(data['count'])
    
    return {
        "status": "success",
        "viewer_count": data['count'],
        "message": f"Viewer count updated to {data['count']}"
    }


@app.get("/orchestrator/v3/debug")
async def get_debug_info():
    """Get debug information"""
    if not orchestrator_wrapper:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    debug_info = {
        "config": {
            "autogen_enabled": orchestrator_wrapper.config.autogen_enabled,
            "persona": orchestrator_wrapper.config.persona,
            "group_chat_enabled": orchestrator_wrapper.config.group_chat_enabled,
            "agent_timeout": orchestrator_wrapper.config.agent_timeout,
            "max_agent_rounds": orchestrator_wrapper.config.max_agent_rounds
        },
        "state": orchestrator_wrapper.state_hooks.get_enhanced_state() if orchestrator_wrapper.state_hooks else {},
        "metrics": orchestrator_wrapper.metrics,
        "performance_traces": len(orchestrator_wrapper.performance_traces),
        "errors": orchestrator_wrapper.metrics.get('errors', 0)
    }
    
    return debug_info


# Error handling
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    # Run the service
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "autogen_orchestrator_service:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )