"""
Simplified Queue Consumer for S2
================================

Processes stimuli from the queue using simplified specialized teams.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .simplified_autogen_team import SimplifiedAutoGenTeam
from ..services.character_state_manager import get_character_state_manager


class SimplifiedQueueConsumer:
    """
    Simplified queue consumer that processes stimuli with character-specific teams.
    """
    
    def __init__(
        self,
        queue_file: str = None,
        processed_file: str = None,
        poll_interval: float = 5.0
    ):
        # Use environment variables or defaults
        self.queue_file = Path(queue_file or os.getenv("S2_QUEUE_FILE", "/tmp/s2_queue/s2_processing_queue.json"))
        self.processed_file = Path(processed_file or os.getenv("S2_PROCESSED_FILE", "/tmp/s2_queue/s2_processed_stimuli.json"))
        self.poll_interval = poll_interval
        
        # Team management
        self.teams: Dict[str, SimplifiedAutoGenTeam] = {}
        self.character_mapping = {
            "dr._house_doctor_template": "trader",
            "weatherman_template": "streamer",
            "emma_teacher_template": "educator"
        }
        
        # Service state
        self.running = False
        self.processing_task = None
        
        # Clients
        self.scb_client = None
        self.neo4j_client = None
        
        # Statistics
        self.stats = {
            "processed": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat()
        }
        
        logging.info(f"🔄 [QUEUE] Simplified queue consumer initialized")
        logging.info(f"   Queue: {self.queue_file}")
        logging.info(f"   Poll interval: {self.poll_interval}s")
    
    async def initialize(self, llm_config: Dict[str, Any], scb_client=None, neo4j_client=None) -> bool:
        """Initialize teams and clients."""
        
        self.scb_client = scb_client
        self.neo4j_client = neo4j_client
        
        # Create teams for each type
        for team_type in ["trader", "educator", "streamer"]:
            try:
                logging.info(f"🔨 [QUEUE] Creating {team_type} team...")
                team = SimplifiedAutoGenTeam(team_type, llm_config)
                team.set_clients(scb_client, neo4j_client)
                
                if team.create_team():
                    self.teams[team_type] = team
                    logging.info(f"✅ [QUEUE] Created {team_type} team successfully")
                else:
                    logging.error(f"❌ [QUEUE] Failed to create {team_type} team")
                    
            except EOFError as e:
                logging.error(f"❌ [QUEUE] EOF Error creating {team_type} team - this usually means AutoGen is trying to read input: {e}")
                # Try to continue with other teams
            except Exception as e:
                logging.error(f"❌ [QUEUE] Error creating {team_type} team: {e}")
                import traceback
                traceback.print_exc()
        
        logging.info(f"📊 [QUEUE] Successfully created {len(self.teams)} teams: {list(self.teams.keys())}")
        return len(self.teams) > 0
    
    async def start(self):
        """Start processing queue."""
        if self.running:
            logging.warning("Queue consumer already running")
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._process_loop())
        logging.info("✅ [QUEUE] Queue consumer started")
    
    async def stop(self):
        """Stop processing queue."""
        self.running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logging.info("🛑 [QUEUE] Queue consumer stopped")
    
    async def _process_loop(self):
        """Main processing loop."""
        
        while self.running:
            try:
                # Read queue
                items = await self._read_queue()
                
                if items:
                    logging.info(f"📋 [QUEUE] Found {len(items)} items to process")
                    
                    # Process each item
                    for item in items:
                        await self._process_item(item)
                    
                    # Clear queue after processing
                    await self._write_queue([])
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logging.error(f"❌ [QUEUE] Error in process loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _read_queue(self) -> List[Dict[str, Any]]:
        """Read items from queue file."""
        
        if not self.queue_file.exists():
            return []
        
        try:
            with open(self.queue_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"❌ [QUEUE] Error reading queue: {e}")
            return []
    
    async def _write_queue(self, items: List[Dict[str, Any]]):
        """Write items to queue file."""
        
        try:
            # Ensure directory exists
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.queue_file, 'w') as f:
                json.dump(items, f, indent=2)
                
        except Exception as e:
            logging.error(f"❌ [QUEUE] Error writing queue: {e}")
    
    async def _process_item(self, item: Dict[str, Any]):
        """Process a single queue item."""
        
        start_time = datetime.now()
        
        try:
            # Get team type from character or metadata
            character_id = item.get("metadata", {}).get("character_id")
            team_type = self.character_mapping.get(character_id, "educator")  # Default to educator
            
            # Get appropriate team
            team = self.teams.get(team_type)
            if not team:
                raise Exception(f"No team available for type: {team_type}")
            
            logging.info(f"🤖 [QUEUE] Processing with {team_type} team")
            logging.info(f"   Content: {item.get('prompt', '')[:50]}...")
            
            # Create stimuli format
            stimuli = {
                "stimuli_id": f"queue_{item.get('timestamp', '')}",
                "content": item.get("prompt", ""),
                "source": item.get("source", "queue"),
                "metadata": item.get("metadata", {})
            }
            
            # Process with team
            result = await team.process_stimuli(stimuli)
            
            # Save to processed file
            processed_item = {
                **item,
                "processed_at": datetime.now().isoformat(),
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "team_type": team_type,
                "result": result
            }
            
            await self._save_processed(processed_item)
            
            if result.get("success"):
                self.stats["processed"] += 1
                logging.info(f"✅ [QUEUE] Processed successfully in {processed_item['processing_time']:.2f}s")
            else:
                self.stats["failed"] += 1
                logging.error(f"❌ [QUEUE] Processing failed: {result.get('error')}")
                
        except Exception as e:
            self.stats["failed"] += 1
            logging.error(f"❌ [QUEUE] Error processing item: {e}")
            
            # Save failed item
            await self._save_processed({
                **item,
                "processed_at": datetime.now().isoformat(),
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e),
                "success": False
            })
    
    async def _save_processed(self, item: Dict[str, Any]):
        """Save processed item to history."""
        
        try:
            # Read existing
            processed = []
            if self.processed_file.exists():
                with open(self.processed_file, 'r') as f:
                    processed = json.load(f)
            
            # Add new item
            processed.append(item)
            
            # Keep last 100
            if len(processed) > 100:
                processed = processed[-100:]
            
            # Write back
            self.processed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.processed_file, 'w') as f:
                json.dump(processed, f, indent=2)
                
        except Exception as e:
            logging.error(f"❌ [QUEUE] Error saving processed item: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        
        return {
            "running": self.running,
            "processed": self.stats["processed"],
            "failed": self.stats["failed"],
            "teams_available": list(self.teams.keys()),
            "start_time": self.stats["start_time"],
            "queue_file": str(self.queue_file),
            "poll_interval": self.poll_interval
        }


# Global instance
_queue_consumer: Optional[SimplifiedQueueConsumer] = None


def get_queue_consumer() -> Optional[SimplifiedQueueConsumer]:
    """Get the global queue consumer instance."""
    return _queue_consumer


async def initialize_queue_consumer(llm_config: Dict[str, Any], scb_client=None, neo4j_client=None) -> SimplifiedQueueConsumer:
    """Initialize the global queue consumer."""
    
    global _queue_consumer
    
    if _queue_consumer is None:
        _queue_consumer = SimplifiedQueueConsumer()
        
        if await _queue_consumer.initialize(llm_config, scb_client, neo4j_client):
            await _queue_consumer.start()
            logging.info("✅ [QUEUE] Global queue consumer initialized and started")
        else:
            logging.error("❌ [QUEUE] Failed to initialize queue consumer")
            _queue_consumer = None
    
    return _queue_consumer