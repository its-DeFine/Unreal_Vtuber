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

from autogen_agent.core.stimuli_orchestrator import StimuliResponsiveOrchestrator, StimuliResponse


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


# Global orchestrator instance (will be set by main.py)
global_orchestrator: Optional[StimuliResponsiveOrchestrator] = None


def setup_stimuli_api(app: FastAPI, orchestrator: StimuliResponsiveOrchestrator):
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
            consolidation_status = global_orchestrator.consolidator.get_status() if global_orchestrator.consolidator else {}
            
            # Get character system status from S1
            import aiohttp
            s1_characters = {}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://neurosync:5001/character/list") as response:
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
            
            return OrchestratorStatusResponse(
                autonomous_state=status["autonomous_state"],
                current_stimuli=status["current_stimuli"],
                statistics=status["statistics"],
                queue_size=status["queue_size"],
                uptime="N/A"  # TODO: Add uptime tracking
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
    
    @app.get("/api/stimuli/tools")
    async def get_available_tools():
        """
        Get list of available tools that can be triggered by stimuli.
        """
        if not global_orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Stimuli orchestrator not initialized"
            )
        
        try:
            available_tools = list(global_orchestrator.tool_registry.tools.keys())
            
            return {
                "available_tools": available_tools,
                "tool_count": len(available_tools),
                "tool_details": {
                    tool_name: {
                        "description": tool.description if hasattr(tool, 'description') else "No description",
                        "category": getattr(tool, 'category', 'general')
                    }
                    for tool_name, tool in global_orchestrator.tool_registry.tools.items()
                }
            }
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_API] Error getting available tools: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error getting tools: {str(e)}"
            )
    
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