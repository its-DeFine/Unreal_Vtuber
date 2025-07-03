"""
Enhanced API server with authentication and additional endpoints.

This module provides the FastAPI server with comprehensive API endpoints,
authentication middleware, and WebSocket support for the GraphFlow External
Stimuli System.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from functools import wraps
import secrets

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from .gateway.gateway_agent import GraphFlowGatewayAgent, create_gateway
from .models.stimuli import ExternalStimuli, Priority, ProcessingResult
from .models.decisions import ProcessingDecision
from .config.settings import GraphFlowConfig, load_config
from .utils.logging import configure_logging, get_structured_logger
from .utils.metrics import MetricsCollector


# Global instances
gateway: Optional[GraphFlowGatewayAgent] = None
logger = get_structured_logger("api_server")
metrics_collector = MetricsCollector()
websocket_connections: List[WebSocket] = []

# Security
security = HTTPBearer()

# Prometheus metrics
api_requests_total = Counter('graphflow_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
api_request_duration = Histogram('graphflow_api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
active_websocket_connections = Gauge('graphflow_active_websocket_connections', 'Active WebSocket connections')
stimuli_submissions_total = Counter('graphflow_stimuli_submissions_total', 'Total stimuli submissions', ['source', 'priority'])


# Request/Response models
class StimuliRequest(BaseModel):
    """Request model for stimuli submission."""
    content: str = Field(..., description="The content of the external stimuli")
    source: str = Field(..., description="The source system or component")
    priority: str = Field("medium", description="Priority level: low, medium, high, critical")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    request_id: Optional[str] = Field(None, description="Client-provided request ID for tracking")


class StimuliResponse(BaseModel):
    """Response model for stimuli submission."""
    success: bool
    stimuli_id: str
    request_id: Optional[str] = None
    processing_status: str
    estimated_processing_time: Optional[float] = None
    message: str
    timestamp: str


class StimuliStatusResponse(BaseModel):
    """Response model for stimuli status query."""
    stimuli_id: str
    status: str
    decision: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    status: str
    version: str = "1.0.0"
    uptime_seconds: float
    components: Dict[str, Dict[str, Any]]
    active_requests: int
    total_processed: int
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    checks: Dict[str, bool]
    message: str
    timestamp: str


class APIKeyInfo(BaseModel):
    """API key information from configuration."""
    key: str
    name: str
    permissions: List[str]
    rate_limit: int = 100  # requests per minute


# Storage for processed stimuli (in production, use a database)
processed_stimuli: Dict[str, ProcessingResult] = {}
app_start_time = datetime.now()


def load_api_keys() -> Dict[str, APIKeyInfo]:
    """Load API keys from configuration file."""
    try:
        with open("/app/config/api_keys.json", "r") as f:
            data = json.load(f)
            return {
                key_data["key"]: APIKeyInfo(**key_data)
                for key_data in data.get("api_keys", [])
            }
    except Exception as e:
        logger.warning(f"Failed to load API keys: {e}, using default")
        # Default API key for development
        return {
            "dev-key-123": APIKeyInfo(
                key="dev-key-123",
                name="Development Key",
                permissions=["read", "write", "admin"],
                rate_limit=1000
            )
        }


# Load API keys
API_KEYS = load_api_keys()


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> APIKeyInfo:
    """Verify API key from Authorization header."""
    token = credentials.credentials
    
    if token not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return API_KEYS[token]


def require_permission(permission: str):
    """Decorator to require specific permission for an endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, api_key: APIKeyInfo = Depends(verify_api_key), **kwargs):
            if permission not in api_key.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            return await func(*args, api_key=api_key, **kwargs)
        return wrapper
    return decorator


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global gateway
    
    logger.info("Starting GraphFlow API Server")
    
    # Check if gateway is already initialized (by main.py)
    if hasattr(app.state, 'gateway'):
        gateway = app.state.gateway
        logger.info("Using gateway from app state")
    else:
        # Standalone mode - create our own gateway
        config = load_config()
        configure_logging(
            log_level=config.log_level,
            enable_json=config.detailed_logging
        )
        gateway = await create_gateway(config)
        
        # Start background tasks only in standalone mode
        asyncio.create_task(background_health_check())
        asyncio.create_task(cleanup_old_results())
    
    yield
    
    # Shutdown
    logger.info("Shutting down GraphFlow API Server")
    
    # Close all WebSocket connections
    for ws in websocket_connections:
        await ws.close()
    
    # Only stop gateway if we created it
    if not hasattr(app.state, 'gateway') and gateway:
        await gateway.stop()


# Create FastAPI app
app = FastAPI(
    title="GraphFlow External Stimuli System API",
    description="Production-ready API for processing external stimuli through GraphFlow pipeline",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request, call_next):
    """Track API requests for metrics."""
    start_time = datetime.now()
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    duration = (datetime.now() - start_time).total_seconds()
    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    api_request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response


# API endpoints
@app.post("/api/v1/stimuli/submit", response_model=StimuliResponse, tags=["stimuli"])
@require_permission("write")
async def submit_stimuli(
    request: StimuliRequest,
    api_key: APIKeyInfo = Depends(verify_api_key)
):
    """
    Submit external stimuli for processing.
    
    Requires 'write' permission.
    """
    if not gateway:
        raise HTTPException(status_code=503, detail="Gateway not initialized")
    
    try:
        # Create stimuli object
        stimuli = ExternalStimuli(
            content=request.content,
            source=request.source,
            priority=Priority[request.priority.upper()],
            metadata={
                **request.metadata,
                "api_key_name": api_key.name,
                "request_id": request.request_id
            }
        )
        
        # Track submission
        stimuli_submissions_total.labels(
            source=request.source,
            priority=request.priority
        ).inc()
        
        # Process stimuli
        result = await gateway.process_stimuli(stimuli)
        
        # Store result
        processed_stimuli[result.stimuli_id] = result
        
        # Broadcast to WebSocket clients
        await broadcast_stimuli_update(result)
        
        return StimuliResponse(
            success=result.success,
            stimuli_id=result.stimuli_id,
            request_id=request.request_id,
            processing_status="completed" if result.success else "failed",
            estimated_processing_time=result.processing_time,
            message=f"Processed with decision: {result.decision.value}",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to process stimuli: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/status", response_model=SystemStatusResponse, tags=["system"])
async def get_system_status(api_key: APIKeyInfo = Depends(verify_api_key)):
    """Get overall system status."""
    if not gateway:
        raise HTTPException(status_code=503, detail="Gateway not initialized")
    
    try:
        health = await gateway.health_check()
        uptime = (datetime.now() - app_start_time).total_seconds()
        
        return SystemStatusResponse(
            status=health["status"],
            uptime_seconds=uptime,
            components=health["components"],
            active_requests=health["active_requests"],
            total_processed=len(processed_stimuli),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stimuli/{stimuli_id}/status", response_model=StimuliStatusResponse, tags=["stimuli"])
@require_permission("read")
async def get_stimuli_status(
    stimuli_id: str,
    api_key: APIKeyInfo = Depends(verify_api_key)
):
    """
    Get status of a specific stimuli by ID.
    
    Requires 'read' permission.
    """
    if stimuli_id not in processed_stimuli:
        raise HTTPException(status_code=404, detail="Stimuli not found")
    
    result = processed_stimuli[stimuli_id]
    
    return StimuliStatusResponse(
        stimuli_id=stimuli_id,
        status="completed" if result.success else "failed",
        decision=result.decision.value if result.decision else None,
        processing_time=result.processing_time,
        created_at=result.timestamp.isoformat(),
        updated_at=result.timestamp.isoformat(),
        metadata=result.metadata or {}
    )


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Health check endpoint (no authentication required)."""
    checks = {
        "gateway": gateway is not None,
        "api": True
    }
    
    if gateway:
        try:
            health = await gateway.health_check()
            checks.update({
                comp: data.get("healthy", False)
                for comp, data in health.get("components", {}).items()
            })
        except:
            pass
    
    all_healthy = all(checks.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "unhealthy",
        checks=checks,
        message="All systems operational" if all_healthy else "Some components unhealthy",
        timestamp=datetime.now().isoformat()
    )


@app.get("/metrics", tags=["monitoring"])
async def get_prometheus_metrics():
    """Prometheus metrics endpoint (no authentication for scraping)."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/stimuli")
async def websocket_stimuli(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time stimuli submission and updates.
    
    Requires API key as query parameter: /ws/stimuli?token=your-api-key
    """
    # Verify API key
    if token not in API_KEYS:
        await websocket.close(code=1008, reason="Invalid API key")
        return
    
    api_key = API_KEYS[token]
    
    await websocket.accept()
    websocket_connections.append(websocket)
    active_websocket_connections.inc()
    
    logger.info(f"WebSocket connection established for {api_key.name}")
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected as {api_key.name}",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Receive data
            data = await websocket.receive_json()
            
            if data.get("type") == "submit_stimuli" and "write" in api_key.permissions:
                try:
                    # Create stimuli object
                    stimuli_data = data.get("data", {})
                    stimuli = ExternalStimuli(
                        content=stimuli_data.get("content", ""),
                        source=stimuli_data.get("source", "websocket"),
                        priority=Priority[stimuli_data.get("priority", "medium").upper()],
                        metadata={
                            **stimuli_data.get("metadata", {}),
                            "api_key_name": api_key.name,
                            "transport": "websocket"
                        }
                    )
                    
                    # Process stimuli
                    result = await gateway.process_stimuli(stimuli)
                    
                    # Store result
                    processed_stimuli[result.stimuli_id] = result
                    
                    # Send response
                    await websocket.send_json({
                        "type": "stimuli_response",
                        "stimuli_id": result.stimuli_id,
                        "status": "completed" if result.success else "failed",
                        "data": {
                            "decision": result.decision.value,
                            "processing_time": result.processing_time,
                            "confidence_scores": result.confidence_scores
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Broadcast to other clients
                    await broadcast_stimuli_update(result, exclude=websocket)
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message type or insufficient permissions",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {api_key.name}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        active_websocket_connections.dec()


async def broadcast_stimuli_update(result: ProcessingResult, exclude: Optional[WebSocket] = None):
    """Broadcast stimuli processing update to all connected WebSocket clients."""
    message = {
        "type": "stimuli_update",
        "stimuli_id": result.stimuli_id,
        "data": {
            "status": "completed" if result.success else "failed",
            "decision": result.decision.value if result.decision else None,
            "source": result.metadata.get("source", "unknown"),
            "processing_time": result.processing_time
        },
        "timestamp": datetime.now().isoformat()
    }
    
    disconnected = []
    for ws in websocket_connections:
        if ws != exclude:
            try:
                await ws.send_json(message)
            except:
                disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)


async def background_health_check():
    """Periodic health check for all systems."""
    while True:
        try:
            if gateway:
                health = await gateway.health_check()
                logger.info(f"Health check: {health['status']}")
                
                # Alert if any component is unhealthy
                for component, data in health.get("components", {}).items():
                    if not data.get("healthy", False):
                        logger.warning(f"Component {component} is unhealthy: {data}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Background health check failed: {e}")
            await asyncio.sleep(30)


async def cleanup_old_results():
    """Clean up old processing results to prevent memory growth."""
    while True:
        try:
            # Remove results older than 1 hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            to_remove = []
            for stimuli_id, result in processed_stimuli.items():
                if result.timestamp < cutoff_time:
                    to_remove.append(stimuli_id)
            
            for stimuli_id in to_remove:
                del processed_stimuli[stimuli_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old processing results")
            
            await asyncio.sleep(300)  # Run every 5 minutes
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            await asyncio.sleep(300)


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app."""
    return app


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_config=None  # Use our custom logging
    )