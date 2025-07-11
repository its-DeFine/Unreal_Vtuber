"""
Queue Consumer Service for S2 Stimuli Processing
===============================================

This service reads from the file-based queue (/tmp/s2_processing_queue.json)
and triggers the specialized AutoGen teams to process consolidated stimuli.

Architecture:
- Polls the queue file for new batches
- Processes batches through the appropriate specialized team
- Manages batch status and cleanup
- Handles character-specific team routing
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .stimuli_autogen_team import StimuliAutoGenTeam
from .stimuli_orchestrator import StimuliResponse
from ..services.character_state_manager import get_character_state_manager
from .specialized_teams import create_specialized_team
from .character_team_registry import CharacterType


@dataclass
class QueueBatch:
    """Represents a batch from the processing queue"""
    prompt: str
    timestamp: str
    source: str
    processing_mode: str
    status: str = "pending"
    processing_started: Optional[str] = None
    processing_completed: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0


class QueueConsumerService:
    """
    Service that consumes stimuli batches from the file queue
    and processes them through specialized AutoGen teams.
    """
    
    def __init__(
        self,
        queue_file: str = "/tmp/s2_processing_queue.json",
        processed_file: str = "/tmp/s2_processed_stimuli.json",
        poll_interval: float = 2.0,
        max_retries: int = 3
    ):
        self.queue_file = Path(queue_file)
        self.processed_file = Path(processed_file)
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        
        # Team management
        self.character_teams: Dict[str, StimuliAutoGenTeam] = {}
        self.default_team: Optional[StimuliAutoGenTeam] = None
        self.current_character_id: Optional[str] = None
        
        # Service state
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "batches_processed": 0,
            "batches_failed": 0,
            "total_processing_time": 0.0,
            "last_processed": None
        }
        
        logging.info("🔄 [QUEUE_CONSUMER] Queue consumer service initialized")
    
    async def initialize_teams(self, tool_registry, scb_client=None, vtuber_client=None):
        """Initialize specialized teams for each character type"""
        
        logging.info("🤖 [QUEUE_CONSUMER] Initializing character-specific teams...")
        
        # Create specialized teams for each character type
        for char_type in CharacterType:
            try:
                team = create_specialized_team(char_type)
                
                if team:
                    # Set tool registry
                    team.tool_registry = tool_registry
                    
                    if team.initialize_team():
                        self.character_teams[char_type.value] = team
                        logging.info(f"✅ [QUEUE_CONSUMER] Initialized {team.team_name}")
                else:
                    logging.error(f"❌ [QUEUE_CONSUMER] Failed to initialize {char_type.value} team")
                    
            except Exception as e:
                logging.error(f"❌ [QUEUE_CONSUMER] Error creating {char_type.value} team: {e}")
        
        # Set default team
        self.default_team = self.character_teams.get("default")
        
        # Get current character from character state manager
        try:
            char_manager = get_character_state_manager()
            if char_manager:
                current_char = await char_manager.get_current_character()
                if current_char:
                    self.current_character_id = current_char.get("id")
                    logging.info(f"🎭 [QUEUE_CONSUMER] Current character: {self.current_character_id}")
        except Exception as e:
            logging.warning(f"⚠️ [QUEUE_CONSUMER] Could not get current character: {e}")
        
        logging.info(f"✅ [QUEUE_CONSUMER] Initialized {len(self.character_teams)} character teams")
        return len(self.character_teams) > 0
    
    def _get_team_for_character(self, character_id: Optional[str] = None) -> Optional[StimuliAutoGenTeam]:
        """Get the appropriate team based on character ID"""
        
        if not character_id:
            character_id = self.current_character_id
        
        if not character_id:
            return self.default_team
        
        # Use the character team registry for mapping
        from .character_team_registry import get_character_team_registry
        registry = get_character_team_registry()
        
        # Get team config for character
        team_config = registry.get_team_config_by_character_id(character_id)
        if not team_config:
            return self.default_team
        
        # Get team type
        team_type = team_config.character_type.value
        
        return self.character_teams.get(team_type, self.default_team)
    
    async def handle_character_change(self, new_character_id: str):
        """Handle character change notification"""
        
        old_character = self.current_character_id
        self.current_character_id = new_character_id
        
        logging.info(f"🔄 [QUEUE_CONSUMER] Character changed from {old_character} to {new_character_id}")
        
        # Get new team
        new_team = self._get_team_for_character(new_character_id)
        if new_team:
            logging.info(f"🤖 [QUEUE_CONSUMER] Activated team: {new_team.team_config.get('name', 'Unknown')}")
    
    async def _read_queue(self) -> List[QueueBatch]:
        """Read pending batches from the queue file"""
        
        if not self.queue_file.exists():
            return []
        
        try:
            with open(self.queue_file, 'r') as f:
                raw_batches = json.load(f)
            
            # Convert to QueueBatch objects
            batches = []
            for raw in raw_batches:
                batch = QueueBatch(
                    prompt=raw.get("prompt", ""),
                    timestamp=raw.get("timestamp", ""),
                    source=raw.get("source", ""),
                    processing_mode=raw.get("processing_mode", "s2_only"),
                    metadata=raw.get("metadata", {})
                )
                batches.append(batch)
            
            return batches
            
        except Exception as e:
            logging.error(f"❌ [QUEUE_CONSUMER] Error reading queue: {e}")
            return []
    
    async def _write_queue(self, batches: List[QueueBatch]):
        """Write remaining batches back to queue file"""
        
        try:
            raw_batches = []
            for batch in batches:
                if batch.status == "pending":
                    raw_batches.append({
                        "prompt": batch.prompt,
                        "timestamp": batch.timestamp,
                        "source": batch.source,
                        "processing_mode": batch.processing_mode,
                        "metadata": batch.metadata
                    })
            
            with open(self.queue_file, 'w') as f:
                json.dump(raw_batches, f, indent=2)
                
        except Exception as e:
            logging.error(f"❌ [QUEUE_CONSUMER] Error writing queue: {e}")
    
    async def _save_processed(self, batch: QueueBatch):
        """Save processed batch to history file"""
        
        try:
            # Read existing processed batches
            processed = []
            if self.processed_file.exists():
                with open(self.processed_file, 'r') as f:
                    processed = json.load(f)
            
            # Add new batch
            processed.append({
                "prompt": batch.prompt,
                "timestamp": batch.timestamp,
                "source": batch.source,
                "processing_mode": batch.processing_mode,
                "status": batch.status,
                "processing_started": batch.processing_started,
                "processing_completed": batch.processing_completed,
                "result": batch.result,
                "error": batch.error
            })
            
            # Keep only last 100 processed batches
            if len(processed) > 100:
                processed = processed[-100:]
            
            # Write back
            with open(self.processed_file, 'w') as f:
                json.dump(processed, f, indent=2)
                
        except Exception as e:
            logging.error(f"❌ [QUEUE_CONSUMER] Error saving processed batch: {e}")
    
    async def _process_batch(self, batch: QueueBatch) -> bool:
        """Process a single batch through the appropriate team"""
        
        batch.processing_started = datetime.now().isoformat()
        start_time = datetime.now()
        
        try:
            # Check if character_id is in metadata
            character_id = None
            if batch.metadata:
                character_id = batch.metadata.get("character_id")
            
            # Get appropriate team
            team = self._get_team_for_character(character_id)
            if not team:
                raise Exception("No team available for processing")
            
            # Log which team is being used
            from .character_team_registry import get_character_team_registry
            registry = get_character_team_registry()
            team_config = registry.get_team_config_by_character_id(character_id or self.current_character_id)
            if team_config:
                logging.info(f"🤖 [QUEUE_CONSUMER] Using team: {team_config.team_name} (type: {team_config.character_type.value})")
            
            logging.info(f"🔄 [QUEUE_CONSUMER] Processing batch from {batch.timestamp}")
            
            # Create stimuli data from batch
            stimuli_data = {
                "stimuli_id": f"batch_{batch.timestamp}",
                "content": batch.prompt,
                "source": batch.source,
                "priority": "high",
                "metadata": {
                    "batch_timestamp": batch.timestamp,
                    "processing_mode": batch.processing_mode,
                    "character_id": character_id or self.current_character_id,
                    "team_type": team_config.character_type.value if team_config else "default"
                }
            }
            
            # Merge any additional metadata from batch
            if batch.metadata:
                stimuli_data["metadata"].update(batch.metadata)
            
            # Process through team
            result = await team.process_stimuli_with_team(stimuli_data)
            
            # Update batch with results
            batch.status = "completed" if result.get("success") else "failed"
            batch.result = result
            batch.processing_completed = datetime.now().isoformat()
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["batches_processed"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["last_processed"] = batch.timestamp
            
            logging.info(f"✅ [QUEUE_CONSUMER] Processed batch in {processing_time:.2f}s")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ [QUEUE_CONSUMER] Error processing batch: {e}")
            
            batch.status = "failed"
            batch.error = str(e)
            batch.processing_completed = datetime.now().isoformat()
            
            self.stats["batches_failed"] += 1
            
            return False
    
    async def _processing_loop(self):
        """Main processing loop"""
        
        logging.info("🚀 [QUEUE_CONSUMER] Starting processing loop")
        
        while self.running:
            try:
                # Read queue
                batches = await self._read_queue()
                
                if batches:
                    logging.info(f"📋 [QUEUE_CONSUMER] Found {len(batches)} batches to process")
                    
                    # Process each batch
                    remaining_batches = []
                    
                    for batch in batches:
                        if batch.status == "pending":
                            success = await self._process_batch(batch)
                            
                            # Save processed batch
                            await self._save_processed(batch)
                            
                            # If failed and retries available, keep in queue
                            if not success and batch.retry_count < self.max_retries:
                                batch.retry_count += 1
                                batch.status = "pending"
                                remaining_batches.append(batch)
                                logging.info(f"🔄 [QUEUE_CONSUMER] Retrying batch (attempt {batch.retry_count}/{self.max_retries})")
                            elif success:
                                logging.info(f"✅ [QUEUE_CONSUMER] Batch processed successfully, removing from queue")
                        else:
                            remaining_batches.append(batch)
                    
                    # Write remaining batches back to queue
                    await self._write_queue(remaining_batches)
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logging.error(f"❌ [QUEUE_CONSUMER] Error in processing loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def start(self):
        """Start the queue consumer service"""
        
        if self.running:
            logging.warning("⚠️ [QUEUE_CONSUMER] Service already running")
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._processing_loop())
        
        logging.info("✅ [QUEUE_CONSUMER] Queue consumer service started")
    
    async def stop(self):
        """Stop the queue consumer service"""
        
        if not self.running:
            return
        
        self.running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logging.info("🛑 [QUEUE_CONSUMER] Queue consumer service stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        
        avg_time = 0.0
        if self.stats["batches_processed"] > 0:
            avg_time = self.stats["total_processing_time"] / self.stats["batches_processed"]
        
        return {
            "batches_processed": self.stats["batches_processed"],
            "batches_failed": self.stats["batches_failed"],
            "average_processing_time": avg_time,
            "last_processed": self.stats["last_processed"],
            "service_running": self.running,
            "current_character": self.current_character_id,
            "active_teams": list(self.character_teams.keys())
        }


# Global instance
_queue_consumer_service: Optional[QueueConsumerService] = None


def get_queue_consumer_service() -> Optional[QueueConsumerService]:
    """Get the global queue consumer service instance"""
    return _queue_consumer_service


async def initialize_queue_consumer_service(
    tool_registry,
    scb_client=None,
    vtuber_client=None
) -> QueueConsumerService:
    """Initialize and return the global queue consumer service"""
    
    global _queue_consumer_service
    
    if _queue_consumer_service is None:
        _queue_consumer_service = QueueConsumerService()
        
        # Initialize teams
        if await _queue_consumer_service.initialize_teams(
            tool_registry=tool_registry,
            scb_client=scb_client,
            vtuber_client=vtuber_client
        ):
            # Start the service
            await _queue_consumer_service.start()
            logging.info("✅ [QUEUE_CONSUMER] Global queue consumer service initialized")
        else:
            logging.error("❌ [QUEUE_CONSUMER] Failed to initialize teams")
            _queue_consumer_service = None
    
    return _queue_consumer_service