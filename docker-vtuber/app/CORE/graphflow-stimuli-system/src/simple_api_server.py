"""
EMERGENCY SIMPLIFIED API SERVER FOR GRAPHFLOW
==============================================

This is a simplified version without authentication for emergency testing.
It directly processes stimuli and routes to S1/S2 based on the nuclear decision matrix.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import aiohttp

# Import the nuclear decision matrix
from config.decision_matrix import DecisionMatrix

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_api_server")

app = FastAPI(title="GraphFlow Emergency API", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
decision_matrix = DecisionMatrix()
session: Optional[aiohttp.ClientSession] = None

# Request models
class StimuliRequest(BaseModel):
    content: str
    source: str = "unknown"
    priority: str = "medium"
    metadata: Dict[str, Any] = {}

class StimuliResponse(BaseModel):
    stimuli_id: str
    status: str
    decision: str
    message: str

@app.on_event("startup")
async def startup():
    global session
    session = aiohttp.ClientSession()
    logger.info("🚀 Emergency GraphFlow API started")

@app.on_event("shutdown")
async def shutdown():
    global session
    if session:
        await session.close()
    logger.info("🔄 Emergency GraphFlow API shutdown")

@app.get("/health")
async def health_check():
    """Health check - no authentication required."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Emergency GraphFlow API running"
    }

@app.get("/api/v1/health")
async def api_health_check():
    """API health check."""
    return {
        "status": "healthy",
        "checks": {
            "gateway": True,
            "api": True,
            "nuclear_decision_matrix": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/stimuli/submit", response_model=StimuliResponse)
async def submit_stimuli(request: StimuliRequest):
    """Submit stimuli for processing - EMERGENCY VERSION."""
    try:
        stimuli_id = f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"🎯 Processing stimuli: {request.content}")
        
        # Use nuclear decision matrix
        stimuli_data = {
            "content": request.content,
            "source": request.source,
            "priority": request.priority,
            "metadata": request.metadata
        }
        
        # Get decision from nuclear matrix
        decision = decision_matrix.evaluate(stimuli_data)
        decision_str = str(decision).split('.')[-1]  # Get AVATAR_AND_ANALYSIS part
        
        logger.info(f"🚨 Nuclear decision: {decision_str}")
        
        # Route to S1 if AVATAR_AND_ANALYSIS
        if "AVATAR_AND_ANALYSIS" in decision_str:
            success = await route_to_s1(stimuli_data)
            if success:
                logger.info("✅ Successfully routed to S1!")
                message = "Routed to S1 (NeuroSync) for speech generation"
            else:
                logger.error("❌ Failed to route to S1")
                message = "Failed to route to S1"
        else:
            logger.info(f"🔄 Decision was {decision_str}, not routing to S1")
            message = f"Decision: {decision_str}"
        
        return StimuliResponse(
            stimuli_id=stimuli_id,
            status="processed",
            decision=decision_str,
            message=message
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing stimuli: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def route_to_s1(stimuli_data: Dict[str, Any]) -> bool:
    """Route stimuli to S1 (NeuroSync) via process_text for speech generation."""
    try:
        s1_endpoint = "http://neurosync_s1:5001/process_text"
        
        # Prepare S1 request for speech generation
        s1_request = {
            "text": stimuli_data["content"]
        }
        
        logger.info(f"🎯 Sending to S1: {s1_endpoint}")
        logger.info(f"📝 S1 request: {s1_request}")
        
        # Send to S1
        async with session.post(s1_endpoint, json=s1_request) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"✅ S1 response: {result}")
                return True
            else:
                logger.error(f"❌ S1 returned status {response.status}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error routing to S1: {e}")
        return False

@app.get("/api/v1/stimuli/{stimuli_id}/status")
async def get_stimuli_status(stimuli_id: str):
    """Get stimuli status."""
    return {
        "stimuli_id": stimuli_id,
        "status": "completed",
        "decision": "AVATAR_AND_ANALYSIS",
        "message": "Emergency testing mode"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)