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
            # Trader characters
            "dr._house_doctor_template": "trader",
            "gordon_trader_template": "trader", 
            "marcus_trader_template": "trader",
            # Educator characters
            "emma_teacher_template": "educator",
            "professor_smith_teacher_template": "educator",
            "sarah_educator_template": "educator",
            "diana_educator_template": "educator",
            # Streamer characters
            "weatherman_template": "streamer",
            "alex_streamer_template": "streamer",
            "mike_streamer_template": "streamer"
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
            logging.warning("⚠️ [QUEUE] Queue consumer already running")
            return
        
        logging.info("🚀 [QUEUE] Starting queue consumer...")
        self.running = True
        
        try:
            # Start the processing task with proper error handling
            await self._ensure_processing_task()
            logging.info("✅ [QUEUE] Queue consumer started successfully")
                
        except Exception as e:
            logging.error(f"❌ [QUEUE] Failed to start queue consumer: {e}")
            self.running = False
            raise
    
    async def _ensure_processing_task(self):
        """Ensure the processing task is running and healthy."""
        
        # Stop existing task if it's unhealthy
        if self.processing_task:
            if self.processing_task.cancelled() or self.processing_task.done():
                logging.warning(f"🔄 [QUEUE] Existing task is {self.processing_task.cancelled() and 'cancelled' or 'done'}, creating new task")
                self.processing_task = None
        
        # Create new task if needed
        if not self.processing_task:
            logging.info("🔨 [QUEUE] Creating new processing task...")
            self.processing_task = asyncio.create_task(self._process_loop_with_recovery())
            
            # Give the task a moment to start
            await asyncio.sleep(0.1)
            
            # Check if task started successfully
            if self.processing_task.done():
                exception = None
                try:
                    exception = self.processing_task.exception()
                except Exception as e:
                    exception = e
                logging.error(f"❌ [QUEUE] Processing task failed immediately: {exception}")
                self.running = False
                raise Exception(f"Processing task failed to start: {exception}")
            else:
                logging.info("✅ [QUEUE] Processing task created and running")
    
    async def _process_loop_with_recovery(self):
        """Process loop with automatic recovery from errors."""
        
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                logging.info(f"🔄 [QUEUE] Starting process loop (attempt {retry_count + 1})")
                await self._process_loop()
                
                # If we reach here, the loop exited normally
                if self.running:
                    logging.warning("🔄 [QUEUE] Process loop exited while running=True, restarting...")
                    retry_count += 1
                    await asyncio.sleep(2.0)  # Brief pause before retry
                
            except asyncio.CancelledError:
                logging.warning("🛑 [QUEUE] Process loop was cancelled")
                raise  # Re-raise cancellation
                
            except Exception as e:
                retry_count += 1
                logging.error(f"❌ [QUEUE] Process loop error (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    backoff_time = min(2.0 * retry_count, 10.0)  # Exponential backoff, max 10s
                    logging.info(f"⏳ [QUEUE] Retrying in {backoff_time}s...")
                    await asyncio.sleep(backoff_time)
                else:
                    logging.error("❌ [QUEUE] Max retries reached, giving up")
                    self.running = False
                    raise
        
        logging.info("🏁 [QUEUE] Process loop with recovery finished")
    
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
        
        loop_iteration = 0
        logging.info(f"🔄 [QUEUE] Starting processing loop with poll interval {self.poll_interval}s")
        
        while self.running:
            loop_iteration += 1
            try:
                logging.debug(f"🔍 [QUEUE] Loop iteration {loop_iteration}, running={self.running}")
                
                # Read queue
                items = await self._read_queue()
                logging.debug(f"📖 [QUEUE] Read {len(items) if items else 0} items from queue")
                
                if items:
                    logging.info(f"📋 [QUEUE] Found {len(items)} items to process in iteration {loop_iteration}")
                    
                    # Process each item
                    for i, item in enumerate(items):
                        logging.info(f"🔨 [QUEUE] Processing item {i+1}/{len(items)}: {item.get('metadata', {}).get('stimuli_id', 'unknown')}")
                        try:
                            await self._process_item(item)
                            logging.info(f"✅ [QUEUE] Successfully processed item {i+1}")
                        except Exception as item_error:
                            logging.error(f"❌ [QUEUE] Failed to process item {i+1}: {item_error}")
                            # Continue with other items
                    
                    # Clear queue after processing
                    logging.info(f"🧹 [QUEUE] Clearing queue after processing {len(items)} items")
                    await self._write_queue([])
                    logging.info(f"✅ [QUEUE] Queue cleared successfully")
                else:
                    logging.debug(f"⭕ [QUEUE] No items in queue (iteration {loop_iteration})")
                
                # Wait before next poll
                logging.debug(f"😴 [QUEUE] Sleeping for {self.poll_interval}s before next poll")
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logging.error(f"❌ [QUEUE] Error in process loop iteration {loop_iteration}: {e}")
                import traceback
                logging.error(f"❌ [QUEUE] Traceback: {traceback.format_exc()}")
                await asyncio.sleep(self.poll_interval)
        
        logging.warning(f"🛑 [QUEUE] Processing loop exited (running={self.running})")
    
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
            # Get team type from multiple sources
            metadata = item.get("metadata", {})
            
            # Check character_type first (direct team type)
            team_type = metadata.get("character_type")
            
            # If not found, check character_id mapping
            if not team_type:
                character_id = metadata.get("character_id")
                team_type = self.character_mapping.get(character_id)
            
            # If still not found, analyze content for team selection
            if not team_type:
                content = item.get("prompt", "").lower()
                if any(word in content for word in ["market", "trading", "bitcoin", "crypto", "stock", "invest"]):
                    team_type = "trader"
                elif any(word in content for word in ["teach", "learn", "explain", "education", "lesson"]):
                    team_type = "educator"
                elif any(word in content for word in ["stream", "content", "video", "audience", "engage"]):
                    team_type = "streamer"
                else:
                    team_type = "educator"  # Default
            
            logging.info(f"🎯 [QUEUE] Selected team type: {team_type} for item with metadata: {metadata}")
            
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
        
        # Check task status
        task_status = "not_created"
        task_exception = None
        
        if self.processing_task:
            try:
                if self.processing_task.cancelled():
                    task_status = "cancelled"
                elif self.processing_task.done():
                    task_status = "completed"
                    try:
                        task_exception = self.processing_task.exception()
                        if task_exception:
                            task_status = "failed"
                    except Exception as e:
                        task_status = "failed"
                        task_exception = e
                else:
                    task_status = "running"
            except Exception as e:
                task_status = "error"
                task_exception = e
        
        return {
            "running": self.running,
            "processed": self.stats["processed"],
            "failed": self.stats["failed"],
            "teams_available": list(self.teams.keys()),
            "start_time": self.stats["start_time"],
            "queue_file": str(self.queue_file),
            "poll_interval": self.poll_interval,
            "task_status": task_status,
            "task_exception": str(task_exception) if task_exception else None
        }
    
    def get_task_health(self) -> Dict[str, Any]:
        """Get detailed task health information."""
        
        health_info = {
            "consumer_running": self.running,
            "task_exists": self.processing_task is not None,
            "task_status": "unknown",
            "task_exception": None,
            "teams_count": len(self.teams),
            "queue_exists": self.queue_file.exists() if self.queue_file else False,
            "restart_available": True
        }
        
        if self.processing_task:
            try:
                if self.processing_task.cancelled():
                    health_info["task_status"] = "cancelled"
                elif self.processing_task.done():
                    health_info["task_status"] = "completed"
                    try:
                        exception = self.processing_task.exception()
                        if exception:
                            health_info["task_status"] = "failed"
                            health_info["task_exception"] = str(exception)
                    except Exception as e:
                        health_info["task_status"] = "failed"
                        health_info["task_exception"] = str(e)
                else:
                    health_info["task_status"] = "running"
            except Exception as e:
                health_info["task_status"] = "error"
                health_info["task_exception"] = str(e)
        else:
            health_info["task_status"] = "not_created"
        
        return health_info
    
    async def restart_processing_task(self):
        """Restart the processing task if it's not running properly."""
        
        if not self.running:
            logging.error("❌ [QUEUE] Cannot restart task - consumer not running")
            return False
        
        try:
            logging.info("🔄 [QUEUE] Manually restarting processing task...")
            
            # Cancel existing task if it exists
            if self.processing_task:
                if not self.processing_task.done():
                    self.processing_task.cancel()
                    try:
                        await self.processing_task
                    except asyncio.CancelledError:
                        pass
                self.processing_task = None
            
            # Create new task
            await self._ensure_processing_task()
            logging.info("✅ [QUEUE] Processing task restarted successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [QUEUE] Failed to restart processing task: {e}")
            return False


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