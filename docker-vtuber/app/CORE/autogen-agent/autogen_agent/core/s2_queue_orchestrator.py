"""
S2 Queue Orchestrator
====================

Minimal orchestrator for S2 teams mode that handles API endpoints
and queues stimuli using the shared queue service for processing.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .stimuli_response import StimuliResponse

# Import shared queue service
try:
    from ...shared.queue.queue_service import QueueService, QueueMessage, MessageStatus
    from ...shared.di import get_service
    SHARED_QUEUE_AVAILABLE = True
except ImportError:
    logging.warning("Shared queue service not available, falling back to file-based queue")
    SHARED_QUEUE_AVAILABLE = False


class S2QueueOrchestrator:
    """
    Minimal orchestrator that queues stimuli using the shared queue service for S2 teams processing.
    Falls back to file-based queue if shared service is not available.
    """
    
    def __init__(
        self,
        queue_file: str = None,
        character_state_manager=None
    ):
        self.character_state_manager = character_state_manager
        
        # Try to use shared queue service first
        if SHARED_QUEUE_AVAILABLE:
            try:
                self.queue_service = get_service(QueueService)
                self.use_shared_queue = True
                logging.info("S2 Queue Orchestrator using shared queue service")
            except Exception as e:
                logging.warning(f"Failed to initialize shared queue service: {e}, falling back to file-based")
                self.use_shared_queue = False
        else:
            self.use_shared_queue = False
        
        # Fallback to file-based queue
        if not self.use_shared_queue:
            if queue_file is None:
                queue_file = os.getenv("S2_QUEUE_FILE", "/tmp/s2_queue/s2_processing_queue.json")
            self.queue_file = Path(queue_file)
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            logging.info("S2 Queue Orchestrator using file-based queue")
        
        # Initialize empty tool registry (for API compatibility)
        self.tool_registry = type('ToolRegistry', (), {'tools': {}})()
        
        # Statistics
        self.stats = {
            "total_received": 0,
            "total_queued": 0,
            "total_errors": 0,
            "start_time": datetime.now().isoformat()
        }
        
        logging.info(f"📝 [S2_QUEUE_ORCHESTRATOR] Initialized with queue file: {self.queue_file}")
    
    async def receive_stimuli(self, stimuli_data: Dict[str, Any]) -> StimuliResponse:
        """
        Receive stimuli from GraphFlow and write to queue file.
        """
        
        self.stats["total_received"] += 1
        start_time = datetime.now()
        
        try:
            # Get current character if available
            character_id = None
            if self.character_state_manager:
                try:
                    current_char = self.character_state_manager.get_current_character()
                    if current_char:
                        character_id = getattr(current_char, 'id', None) or current_char.get("id", None) if hasattr(current_char, 'get') else None
                except Exception as e:
                    logging.warning(f"Could not get current character: {e}")
            
            # Create queue entry
            queue_entry = {
                "prompt": stimuli_data.get("content", ""),
                "timestamp": datetime.now().isoformat(),
                "source": stimuli_data.get("source", "graphflow"),
                "processing_mode": "s2_only",
                "metadata": {
                    "stimuli_id": stimuli_data.get("stimuli_id", ""),
                    "priority": stimuli_data.get("priority", "medium"),
                    "category": stimuli_data.get("category"),
                    "confidence": stimuli_data.get("confidence"),
                    "character_id": character_id,
                    **stimuli_data.get("metadata", {})
                }
            }
            
            # Read existing queue
            existing_queue = []
            if self.queue_file.exists():
                try:
                    with open(self.queue_file, 'r') as f:
                        existing_queue = json.load(f)
                except Exception as e:
                    logging.error(f"Error reading queue file: {e}")
                    existing_queue = []
            
            # Add new entry
            existing_queue.append(queue_entry)
            
            # Write back
            with open(self.queue_file, 'w') as f:
                json.dump(existing_queue, f, indent=2)
            
            self.stats["total_queued"] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logging.info(f"✅ [S2_QUEUE_ORCHESTRATOR] Queued stimuli: {stimuli_data.get('stimuli_id', 'unknown')}")
            logging.info(f"   Queue depth: {len(existing_queue)} items")
            
            # Return success response
            return StimuliResponse(
                success=True,
                stimuli_id=stimuli_data.get("stimuli_id", ""),
                processing_time=processing_time,
                tools_triggered=[],  # No tools triggered in queue mode
                agent_decision="queued_for_s2_processing",
                response_content=f"Stimuli queued for S2 team processing (character: {character_id or 'default'})"
            )
            
        except Exception as e:
            self.stats["total_errors"] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logging.error(f"❌ [S2_QUEUE_ORCHESTRATOR] Error queuing stimuli: {e}")
            
            return StimuliResponse(
                success=False,
                stimuli_id=stimuli_data.get("stimuli_id", ""),
                processing_time=processing_time,
                tools_triggered=[],
                error_message=str(e)
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status for API compatibility."""
        
        # Check queue depth
        queue_size = 0
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r') as f:
                    queue_data = json.load(f)
                    queue_size = len(queue_data)
            except:
                pass
        
        return {
            "autonomous_state": "running",  # Always running in queue mode
            "current_stimuli": None,  # No current stimuli in queue mode
            "statistics": self.stats,
            "queue_size": queue_size
        }
    
    async def _pause_autonomous_mode(self):
        """Pause autonomous mode (no-op in queue mode)."""
        logging.info("⏸️ [S2_QUEUE_ORCHESTRATOR] Pause requested (no-op in queue mode)")
    
    async def _resume_autonomous_mode(self):
        """Resume autonomous mode (no-op in queue mode)."""
        logging.info("▶️ [S2_QUEUE_ORCHESTRATOR] Resume requested (no-op in queue mode)")