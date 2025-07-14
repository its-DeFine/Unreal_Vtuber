"""
FastAPI endpoints for stimuli reception from GraphFlow External Stimuli System.

This module provides REST API endpoints that allow GraphFlow to send stimuli
to System 2 (AutoGen Agent) for processing. The orchestrator will pause
autonomous operations, process the stimuli, and resume autonomous operations.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from autogen_agent.core.stimuli_response import StimuliResponse
from autogen_agent.core.s2_queue_orchestrator import S2QueueOrchestrator


class StimuliSubmissionRequest(BaseModel):
    """Request model for stimuli submission from GraphFlow"""
    stimuli_id: str = Field(..., description="Unique identifier for the stimuli")
    content: str = Field(..., description="Content of the stimuli")
    source: str = Field(..., description="Source of the stimuli (e.g., 'admin_console', 'chat_interface')")
    priority: str = Field(default="medium", description="Priority level: low, medium, high, critical, emergency")
    category: Optional[str] = Field(None, description="Stimuli category from GraphFlow categorization")
    confidence: Optional[float] = Field(None, description="Confidence score from categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class StimuliSubmissionResponse(BaseModel):
    """Response model for stimuli submission"""
    success: bool
    stimuli_id: str
    processing_time: float
    tools_triggered: list[str]
    agent_decision: Optional[str] = None
    response_content: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str


class OrchestratorStatusResponse(BaseModel):
    """Response model for orchestrator status"""
    autonomous_state: str
    current_stimuli: Optional[str]
    statistics: Dict[str, Any]
    queue_size: int
    uptime: str
    is_processing: bool = False
    processing_duration_seconds: Optional[float] = None


# Global orchestrator instance (will be set by main.py)
global_orchestrator: Optional[S2QueueOrchestrator] = None


def setup_stimuli_api(app: FastAPI, orchestrator: S2QueueOrchestrator):
    """Setup stimuli API endpoints on the provided FastAPI app"""
    global global_orchestrator
    global_orchestrator = orchestrator
    
    @app.post("/api/stimuli/receive", response_model=StimuliSubmissionResponse)
    async def receive_stimuli(request: StimuliSubmissionRequest) -> StimuliSubmissionResponse:
        """
        Main endpoint for receiving stimuli from GraphFlow External Stimuli System.
        
        This endpoint:
        1. Validates the incoming stimuli request
        2. Passes it to the orchestrator for processing
        3. Returns the processing result
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Stimuli orchestrator not initialized"
            )
        
        start_time = time.time()
        
        try:
            logging.info(f"📨 [STIMULI_API] Received stimuli from GraphFlow: {request.stimuli_id}")
            logging.info(f"   Content: {request.content[:100]}...")
            logging.info(f"   Source: {request.source}, Priority: {request.priority}")
            
            # Convert request to dict for orchestrator
            stimuli_data = {
                "stimuli_id": request.stimuli_id,
                "content": request.content,
                "source": request.source,
                "priority": request.priority,
                "category": request.category,
                "confidence": request.confidence,
                "metadata": request.metadata
            }
            
            # Process the stimuli through the orchestrator
            response = await global_orchestrator.receive_stimuli(stimuli_data)
            
            # Convert orchestrator response to API response
            api_response = StimuliSubmissionResponse(
                success=response.success,
                stimuli_id=response.stimuli_id,
                processing_time=response.processing_time,
                tools_triggered=response.tools_triggered,
                agent_decision=response.agent_decision,
                response_content=response.response_content,
                error_message=response.error_message,
                timestamp=datetime.now().isoformat()
            )
            
            total_time = time.time() - start_time
            logging.info(f"✅ [STIMULI_API] Stimuli processed successfully in {total_time:.3f}s")
            
            return api_response
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Error processing stimuli: {str(e)}"
            logging.error(f"❌ [STIMULI_API] {error_msg}")
            
            return StimuliSubmissionResponse(
                success=False,
                stimuli_id=request.stimuli_id,
                processing_time=total_time,
                tools_triggered=[],
                error_message=error_msg,
                timestamp=datetime.now().isoformat()
            )
    
    @app.get("/api/admin/control-panel")
    async def get_admin_control_panel():
        """
        Admin control panel endpoint - provides admin operation history and system status
        This serves as a centralized control panel for admin operations
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503,
                detail="Orchestrator not initialized"
            )
        
        try:
            # Get consolidation system status including admin operations
            consolidation_status = {}
            if hasattr(global_orchestrator, 'consolidator') and global_orchestrator.consolidator:
                consolidation_status = global_orchestrator.consolidator.get_status()
            else:
                consolidation_status = {"status": "not_available", "message": "Consolidator not initialized"}
            
            # Get character system status from S1
            import aiohttp
            s1_characters = {}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://neurosync_s1:5001/character/list") as response:
                        if response.status == 200:
                            s1_characters = await response.json()
            except Exception as e:
                logging.warning(f"Could not fetch S1 characters: {e}")
                s1_characters = {"error": "Could not fetch characters"}
            
            control_panel_data = {
                "timestamp": datetime.now().isoformat(),
                "admin_operations": consolidation_status.get("admin_operations", {}),
                "s1_characters": s1_characters,
                "consolidation_stats": consolidation_status.get("statistics", {}),
                "system_capacity": consolidation_status.get("capacity_status", {}),
                "pending_operations": consolidation_status.get("pending_stimuli", 0),
                "design_note": "Admin operations are processed silently by default. Use 'announce:' prefix for S1 speech output."
            }
            
            return control_panel_data
            
        except Exception as e:
            logging.error(f"Error generating admin control panel: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating control panel: {str(e)}"
            )

    @app.get("/api/stimuli/status", response_model=OrchestratorStatusResponse)
    async def get_orchestrator_status() -> OrchestratorStatusResponse:
        """
        Get current status of the stimuli orchestrator.
        
        Returns information about:
        - Current autonomous state (running/paused/stopped)
        - Currently processing stimuli
        - Processing statistics
        - Queue status
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Stimuli orchestrator not initialized"
            )
        
        try:
            status = global_orchestrator.get_status()
            
            # Get processing state from queue consumer if available
            is_processing = False
            processing_duration = None
            current_stimuli_id = None
            
            if hasattr(global_orchestrator, 'queue_consumer') and global_orchestrator.queue_consumer:
                consumer_stats = global_orchestrator.queue_consumer.get_stats()
                is_processing = consumer_stats.get('is_processing', False)
                processing_duration = consumer_stats.get('processing_duration_seconds')
                current_stimuli_id = consumer_stats.get('current_stimuli_id')
            
            return OrchestratorStatusResponse(
                autonomous_state=status["autonomous_state"],
                current_stimuli=current_stimuli_id or status["current_stimuli"],
                statistics=status["statistics"],
                queue_size=status["queue_size"],
                uptime="N/A",  # TODO: Add uptime tracking
                is_processing=is_processing,
                processing_duration_seconds=processing_duration
            )
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error getting orchestrator status: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error getting status: {str(e)}"
            )
    
    @app.post("/api/stimuli/control/pause")
    async def pause_autonomous_mode():
        """
        Manually pause autonomous operations.
        Useful for maintenance or debugging.
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Stimuli orchestrator not initialized"
            )
        
        try:
            await global_orchestrator._pause_autonomous_mode()
            logging.info("⏸️ [STIMULI_API] Autonomous mode paused via API")
            return {"success": True, "message": "Autonomous mode paused"}
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error pausing autonomous mode: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error pausing autonomous mode: {str(e)}"
            )
    
    @app.post("/api/stimuli/control/resume")
    async def resume_autonomous_mode():
        """
        Manually resume autonomous operations.
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Stimuli orchestrator not initialized"
            )
        
        try:
            await global_orchestrator._resume_autonomous_mode()
            logging.info("▶️ [STIMULI_API] Autonomous mode resumed via API")
            return {"success": True, "message": "Autonomous mode resumed"}
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error resuming autonomous mode: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error resuming autonomous mode: {str(e)}"
            )
    
    @app.get("/api/queue/health")
    async def get_queue_health():
        """
        Get detailed health information about the queue consumer task.
        """
        from ..core.simplified_queue_consumer import get_queue_consumer
        
        queue_consumer = get_queue_consumer()
        if not queue_consumer:
            raise HTTPException(
                status_code=503,
                detail="Queue consumer not initialized"
            )
        
        try:
            health_info = queue_consumer.get_task_health()
            
            # Add overall health assessment
            overall_health = "healthy"
            if not health_info["consumer_running"]:
                overall_health = "stopped"
            elif health_info["task_status"] == "failed":
                overall_health = "failed"
            elif health_info["task_status"] in ["completed", "cancelled", "not_created"]:
                overall_health = "unhealthy"
            elif health_info["teams_count"] == 0:
                overall_health = "degraded"
            
            health_info["overall_health"] = overall_health
            health_info["timestamp"] = datetime.now().isoformat()
            
            return health_info
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error getting queue health: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting queue health: {str(e)}"
            )
    
    @app.post("/api/queue/restart")
    async def restart_queue_processing():
        """
        Restart the queue processing task if it's not running properly.
        """
        from ..core.simplified_queue_consumer import get_queue_consumer
        
        queue_consumer = get_queue_consumer()
        if not queue_consumer:
            raise HTTPException(
                status_code=503,
                detail="Queue consumer not initialized"
            )
        
        try:
            logging.info("🔄 [STIMULI_API] Manual queue restart requested")
            success = await queue_consumer.restart_processing_task()
            
            if success:
                return {
                    "success": True,
                    "message": "Queue processing task restarted successfully",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to restart queue processing task"
                )
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error restarting queue: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error restarting queue: {str(e)}"
            )
    
    @app.post("/api/stimuli/stop")
    async def stop_conversation():
        """
        Stop the current System 2 conversation/processing immediately.
        This can be used to interrupt long-running AutoGen team discussions.
        """
        from ..core.simplified_queue_consumer import get_queue_consumer
        
        queue_consumer = get_queue_consumer()
        if not queue_consumer:
            raise HTTPException(
                status_code=503,
                detail="Queue consumer not initialized"
            )
        
        try:
            logging.info("⏹️ [STIMULI_API] Stop conversation requested")
            result = await queue_consumer.stop_current_processing()
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": result.get("message", "Processing stopped"),
                    "stopped_stimuli_id": result.get("stopped_stimuli_id"),
                    "processing_duration_seconds": result.get("processing_duration_seconds"),
                    "was_processing": result.get("was_processing", False),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "No processing to stop"),
                    "was_processing": result.get("was_processing", False),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error stopping conversation: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error stopping conversation: {str(e)}"
            )
    
    @app.get("/api/stimuli/processing-state")
    async def get_processing_state():
        """
        Get detailed information about current processing state.
        This endpoint provides real-time information about whether the system
        is currently processing stimuli and can accept new requests.
        """
        from ..core.simplified_queue_consumer import get_queue_consumer
        
        queue_consumer = get_queue_consumer()
        if not queue_consumer:
            return {
                "is_processing": False,
                "current_stimuli_id": None,
                "processing_duration_seconds": None,
                "status": "queue_consumer_not_initialized",
                "can_accept_new_stimuli": False,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            stats = queue_consumer.get_stats()
            
            return {
                "is_processing": stats.get('is_processing', False),
                "current_stimuli_id": stats.get('current_stimuli_id'),
                "processing_duration_seconds": stats.get('processing_duration_seconds'),
                "status": "running" if stats.get('running', False) else "stopped",
                "can_accept_new_stimuli": not stats.get('is_processing', False),
                "queue_consumer_stats": {
                    "processed": stats.get('processed', 0),
                    "failed": stats.get('failed', 0),
                    "teams_available": stats.get('teams_available', []),
                    "task_status": stats.get('task_status', 'unknown')
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error getting processing state: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting processing state: {str(e)}"
            )
    
    @app.get("/api/stimuli/tools")
    async def get_available_tools():
        """
        Get list of available tools that can be triggered by stimuli.
        """
        try:
            # Get tools from the queue consumer's teams
            from ..core.simplified_queue_consumer import get_queue_consumer
            
            queue_consumer = get_queue_consumer()
            if not queue_consumer:
                return {
                    "available_tools": [],
                    "tool_count": 0,
                    "tool_details": {},
                    "status": "Queue consumer not initialized"
                }
            
            # Aggregate tools from all teams
            all_tools = {}
            tools_by_team = {}
            
            for team_type, team in queue_consumer.teams.items():
                if hasattr(team, 'tool_bridge'):
                    team_tools = team.tool_bridge.get_tool_summary()
                    tools_by_team[team_type] = {
                        "count": team_tools["tools_count"],
                        "tools": list(team_tools["tools"].keys())
                    }
                    
                    # Merge tool details
                    for tool_name, tool_info in team_tools["tools"].items():
                        if tool_name not in all_tools:
                            all_tools[tool_name] = {
                                "description": tool_info["description"],
                                "parameters": tool_info["parameters"],
                                "required_params": tool_info["required_params"],
                                "teams": [team_type]
                            }
                        else:
                            # Tool exists in multiple teams
                            if team_type not in all_tools[tool_name]["teams"]:
                                all_tools[tool_name]["teams"].append(team_type)
            
            # Get unique tool names
            unique_tools = list(all_tools.keys())
            
            return {
                "available_tools": unique_tools,
                "tool_count": len(unique_tools),
                "tools_by_team": tools_by_team,
                "tool_details": all_tools
            }
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error getting available tools: {e}")
            return {
                "available_tools": [],
                "tool_count": 0,
                "tool_details": {},
                "error": str(e)
            }
    
    logging.info("🔗 [STIMULI_API] Stimuli API endpoints registered successfully")


# Health check endpoint specifically for stimuli processing
async def stimuli_health_check():
    """Health check specifically for stimuli processing capabilities"""
    if not global_orchestrator:
        return {
            "stimuli_processing": False,
            "error": "Orchestrator not initialized"
        }
    
    try:
        status = global_orchestrator.get_status()
        return {
            "stimuli_processing": True,
            "autonomous_state": status["autonomous_state"],
            "ready_for_stimuli": status["autonomous_state"] in ["running", "paused"],
            "statistics": status["statistics"]
        }
        
    except Exception as e:
        return {
            "stimuli_processing": False,
            "error": str(e)
        }