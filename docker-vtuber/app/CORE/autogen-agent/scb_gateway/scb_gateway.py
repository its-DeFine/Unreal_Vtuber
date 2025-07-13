"""
SCB Gateway Service

A FastAPI service that provides HTTP API access to the Shared Contextual Bridge (SCB).
This allows external services to read and write SCB data without direct Redis access.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
from redis.exceptions import RedisError

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SCB Gateway",
    description="HTTP API for Shared Contextual Bridge",
    version="1.0.0"
)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None

# Character limits
DEFAULT_CHAR_LIMIT = 1000
CHAR_LIMITS = {
    "trader": int(os.getenv("SCB_MAX_CHARS_TRADER", DEFAULT_CHAR_LIMIT)),
    "educator": int(os.getenv("SCB_MAX_CHARS_EDUCATOR", DEFAULT_CHAR_LIMIT)),
    "streamer": int(os.getenv("SCB_MAX_CHARS_STREAMER", DEFAULT_CHAR_LIMIT)),
    "global": int(os.getenv("SCB_MAX_CHARS_GLOBAL", DEFAULT_CHAR_LIMIT)),
}


# Pydantic models
class SCBEvent(BaseModel):
    type: str
    content: str
    timestamp: Optional[float] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SCBWriteRequest(BaseModel):
    events: List[SCBEvent]
    append: bool = True


class SCBSliceResponse(BaseModel):
    team: str
    events: List[Dict[str, Any]]
    char_count: int
    timestamp: float


# Helper functions
def get_redis_client():
    """Get or create Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL)
    return redis_client


def enforce_char_limit(events: List[Dict[str, Any]], team: str) -> List[Dict[str, Any]]:
    """Enforce character limit for a team's events"""
    char_limit = CHAR_LIMITS.get(team, DEFAULT_CHAR_LIMIT)
    
    # Start from the end and work backwards
    trimmed_events = []
    total_chars = 0
    
    for event in reversed(events):
        event_str = json.dumps(event)
        event_chars = len(event_str)
        
        if total_chars + event_chars <= char_limit:
            trimmed_events.insert(0, event)
            total_chars += event_chars
        else:
            break
    
    return trimmed_events


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client = get_redis_client()
        client.ping()
        return {"status": "healthy", "service": "scb_gateway", "redis": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/scb/global/slice", response_model=SCBSliceResponse)
async def get_global_slice():
    """Get the global SCB slice"""
    try:
        client = get_redis_client()
        data = client.get("scb:global")
        
        if data:
            events = json.loads(data)
            events = enforce_char_limit(events, "global")
        else:
            events = []
        
        char_count = sum(len(json.dumps(e)) for e in events)
        
        return SCBSliceResponse(
            team="global",
            events=events,
            char_count=char_count,
            timestamp=datetime.now().timestamp()
        )
    except Exception as e:
        logger.error(f"Error getting global slice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scb/team/{team}/slice", response_model=SCBSliceResponse)
async def get_team_slice(team: str):
    """Get a team's SCB slice"""
    try:
        client = get_redis_client()
        data = client.get(f"scb:team:{team}")
        
        if data:
            events = json.loads(data)
            events = enforce_char_limit(events, team)
        else:
            events = []
        
        char_count = sum(len(json.dumps(e)) for e in events)
        
        return SCBSliceResponse(
            team=team,
            events=events,
            char_count=char_count,
            timestamp=datetime.now().timestamp()
        )
    except Exception as e:
        logger.error(f"Error getting team {team} slice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scb/global/write")
async def write_global_slice(request: SCBWriteRequest):
    """Write events to the global SCB"""
    try:
        client = get_redis_client()
        
        # Convert events to dicts
        new_events = []
        for event in request.events:
            event_dict = event.dict()
            if event_dict.get("timestamp") is None:
                event_dict["timestamp"] = datetime.now().timestamp()
            new_events.append(event_dict)
        
        if request.append:
            # Get existing events
            data = client.get("scb:global")
            if data:
                existing_events = json.loads(data)
            else:
                existing_events = []
            
            # Append new events
            all_events = existing_events + new_events
        else:
            all_events = new_events
        
        # Enforce char limit
        all_events = enforce_char_limit(all_events, "global")
        
        # Save back to Redis
        client.set("scb:global", json.dumps(all_events))
        
        return {
            "status": "success",
            "events_written": len(new_events),
            "total_events": len(all_events)
        }
    except Exception as e:
        logger.error(f"Error writing to global SCB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scb/team/{team}/write")
async def write_team_slice(team: str, request: SCBWriteRequest):
    """Write events to a team's SCB"""
    try:
        client = get_redis_client()
        
        # Convert events to dicts
        new_events = []
        for event in request.events:
            event_dict = event.dict()
            if event_dict.get("timestamp") is None:
                event_dict["timestamp"] = datetime.now().timestamp()
            new_events.append(event_dict)
        
        if request.append:
            # Get existing events
            data = client.get(f"scb:team:{team}")
            if data:
                existing_events = json.loads(data)
            else:
                existing_events = []
            
            # Append new events
            all_events = existing_events + new_events
        else:
            all_events = new_events
        
        # Enforce char limit
        all_events = enforce_char_limit(all_events, team)
        
        # Save back to Redis
        client.set(f"scb:team:{team}", json.dumps(all_events))
        
        return {
            "status": "success",
            "team": team,
            "events_written": len(new_events),
            "total_events": len(all_events)
        }
    except Exception as e:
        logger.error(f"Error writing to team {team} SCB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/scb/global")
async def clear_global_scb():
    """Clear the global SCB"""
    try:
        client = get_redis_client()
        client.delete("scb:global")
        return {"status": "success", "message": "Global SCB cleared"}
    except Exception as e:
        logger.error(f"Error clearing global SCB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/scb/team/{team}")
async def clear_team_scb(team: str):
    """Clear a team's SCB"""
    try:
        client = get_redis_client()
        client.delete(f"scb:team:{team}")
        return {"status": "success", "message": f"Team {team} SCB cleared"}
    except Exception as e:
        logger.error(f"Error clearing team {team} SCB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scb/stats")
async def get_scb_stats():
    """Get statistics about all SCB slices"""
    try:
        client = get_redis_client()
        stats = {}
        
        # Check global
        data = client.get("scb:global")
        if data:
            events = json.loads(data)
            char_count = sum(len(json.dumps(e)) for e in events)
            stats["global"] = {
                "event_count": len(events),
                "char_count": char_count,
                "char_limit": CHAR_LIMITS.get("global", DEFAULT_CHAR_LIMIT)
            }
        
        # Check teams
        for team in ["trader", "educator", "streamer"]:
            data = client.get(f"scb:team:{team}")
            if data:
                events = json.loads(data)
                char_count = sum(len(json.dumps(e)) for e in events)
                stats[f"team_{team}"] = {
                    "event_count": len(events),
                    "char_count": char_count,
                    "char_limit": CHAR_LIMITS.get(team, DEFAULT_CHAR_LIMIT)
                }
        
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error getting SCB stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300) 