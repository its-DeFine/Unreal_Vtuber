"""
Simplified Queue Consumer for S2
================================

Processes stimuli from the queue using simplified specialized teams.
"""

import os
import json
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .simplified_autogen_team import SimplifiedAutoGenTeam
from ..services.character_state_manager import get_character_state_manager
from ..config.processing_config import ProcessingConfig, TeamConfig, FileConfig
from ..utils.error_handler import error_handler, with_error_handling

logger = logging.getLogger(__name__)


class SimplifiedQueueConsumer:
    """
    Simplified queue consumer that processes stimuli with character-specific teams.
    """
    
    def __init__(
        self,
        queue_file: str = None,
        processed_file: str = None,
        poll_interval: float = None
    ):
        # Use environment variables or defaults from config
        self.queue_file = Path(queue_file or os.getenv("S2_QUEUE_FILE", FileConfig.DEFAULT_QUEUE_FILE))
        self.processed_file = Path(processed_file or os.getenv("S2_PROCESSED_FILE", FileConfig.DEFAULT_PROCESSED_FILE))
        self.poll_interval = poll_interval or ProcessingConfig.DEFAULT_POLL_INTERVAL
        
        # Team management
        self.teams: Dict[str, SimplifiedAutoGenTeam] = {}
        self.character_mapping = {
            # Trader characters
            "gordon_trader_template": "trader", 
            "marcus_trader_template": "trader",
            # Educator characters
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
        self.is_processing = False  # Track if currently processing a stimuli
        self.current_stimuli_id = None  # Track current stimuli being processed
        self.processing_start_time = None  # Track when current processing started
        self.stop_requested = False  # Flag to stop current processing
        self.current_team = None  # Track current team being used
        
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
        max_retries = ProcessingConfig.MAX_RETRIES
        
        logging.info(f"🔄 [QUEUE] Starting process loop with recovery (max_retries={max_retries})")
        
        while self.running and retry_count < max_retries:
            try:
                error_handler.log_success("queue", f"starting_process_loop_attempt_{retry_count + 1}")
                await self._process_loop()
                
                # If we reach here, the loop exited normally
                if self.running:
                    error_handler.log_warning("queue", "Process loop exited while running=True, restarting")
                    retry_count += 1
                    await asyncio.sleep(ProcessingConfig.BACKOFF_BASE_SECONDS)
                
            except asyncio.CancelledError:
                error_handler.log_warning("queue", "Process loop was cancelled")
                if not self.running:
                    # If we're not running, cancellation is expected
                    logging.info("🛑 [QUEUE] Process loop cancelled during shutdown")
                    raise
                else:
                    # If we're still running, this is unexpected cancellation
                    logging.warning("⚠️ [QUEUE] Unexpected cancellation while running, will retry")
                    retry_count += 1
                    await asyncio.sleep(ProcessingConfig.BACKOFF_BASE_SECONDS)
                    continue
                
            except Exception as e:
                retry_count += 1
                context = {"attempt": retry_count, "max_retries": max_retries}
                error_handler.log_with_traceback("queue", "process_loop", e, context=context)
                
                if retry_count < max_retries:
                    backoff_time = min(
                        ProcessingConfig.BACKOFF_BASE_SECONDS * retry_count, 
                        ProcessingConfig.BACKOFF_MAX_SECONDS
                    )
                    error_handler.log_success("queue", f"retrying_in_{backoff_time}s")
                    await asyncio.sleep(backoff_time)
                else:
                    error_handler.log_with_traceback("queue", "max_retries_reached", e)
                    self.running = False
                    raise
        
        error_handler.log_success("queue", "process_loop_with_recovery_finished")
    
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
        """
        Process a single queue item with comprehensive error handling.
        
        Args:
            item: Queue item containing prompt, metadata, and source information
        """
        start_time = datetime.now()
        
        # Generate or extract unique stimuli ID for tracking
        stimuli_id = item.get("metadata", {}).get("stimuli_id")
        if not stimuli_id:
            stimuli_id = f"s2_{uuid.uuid4().hex[:8]}"
            # Add to metadata for downstream processing
            if "metadata" not in item:
                item["metadata"] = {}
            item["metadata"]["stimuli_id"] = stimuli_id
        
        # Set processing state
        self.is_processing = True
        self.current_stimuli_id = stimuli_id
        self.processing_start_time = start_time
        self.stop_requested = False
        
        # 🔥 ENHANCED: S2_RECEIVED timestamp with more context
        logger.info(f"S2_RECEIVED {stimuli_id} {start_time.isoformat()}")
        logger.info(f"📨 [QUEUE] Processing item: {stimuli_id} - {item.get('prompt', '')[:100]}...")
        
        try:
            # Determine which team should handle this item
            team_type = self._determine_team_type(item)
            team = self._get_team_for_type(team_type)
            self.current_team = team
            
            # Create properly formatted stimuli with stimuli_id
            stimuli = self._create_stimuli_payload(item)
            stimuli["stimuli_id"] = stimuli_id  # 🔥 ENSURE stimuli_id is in stimuli
            
            # 🔥 ENHANCED: S2_PROCESSING_START timestamp
            processing_start_time = datetime.now()
            logger.info(f"S2_PROCESSING_START {stimuli_id} {processing_start_time.isoformat()}")
            
            # Check if stop was requested before processing
            if self.stop_requested:
                logger.info(f"⏹️ [QUEUE] Stop requested, cancelling processing for {stimuli_id}")
                result = {
                    "success": False,
                    "error": "Processing stopped by user request",
                    "stopped": True
                }
            else:
                # Process with the selected team
                result = await self._execute_team_processing(team, team_type, stimuli)
            
            # Check again if stop was requested during processing
            if self.stop_requested:
                logger.info(f"⏹️ [QUEUE] Stop requested during processing, marking as stopped for {stimuli_id}")
                result["stopped"] = True
            
            # 🔥 ENHANCED: S2_PROCESSING_COMPLETE timestamp
            processing_complete_time = datetime.now()
            logger.info(f"S2_PROCESSING_COMPLETE {stimuli_id} {processing_complete_time.isoformat()}")
            
            # Handle the processing result
            await self._handle_processing_result(item, start_time, team_type, result)
            
        except Exception as e:
            await self._handle_processing_error(item, start_time, e)
        finally:
            # Clear processing state - ALWAYS clear to prevent stuck states
            self.is_processing = False
            self.current_stimuli_id = None
            self.processing_start_time = None
            self.stop_requested = False
            self.current_team = None
            logger.info(f"✅ [QUEUE] Processing state cleared for {stimuli_id}")
    
    def _determine_team_type(self, item: Dict[str, Any]) -> str:
        """
        Determine the appropriate team type for processing this item.
        
        Args:
            item: Queue item with metadata and content
            
        Returns:
            Team type string (trader, educator, or streamer)
        """
        metadata = item.get("metadata", {})
        
        # Priority 1: Direct character_type specification
        team_type = metadata.get("character_type")
        if team_type and team_type in TeamConfig.VALID_TEAM_TYPES:
            return team_type
        
        # Priority 2: Character ID mapping
        character_id = metadata.get("character_id")
        if character_id and character_id in self.character_mapping:
            return self.character_mapping[character_id]
        
        # Priority 3: Content analysis
        return self._analyze_content_for_team(item.get("prompt", ""))
    
    def _analyze_content_for_team(self, content: str) -> str:
        """
        Analyze content to determine the most appropriate team type.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Team type based on keyword analysis
        """
        content_lower = content.lower()
        
        # Check keywords for each team type
        for team_type, keywords in TeamConfig.TEAM_KEYWORDS.items():
            if any(keyword in content_lower for keyword in keywords):
                return team_type
        
        # Default team if no keywords match
        return TeamConfig.DEFAULT_TEAM
    
    def _get_team_for_type(self, team_type: str) -> SimplifiedAutoGenTeam:
        """
        Get the team instance for the specified type.
        
        Args:
            team_type: Type of team needed
            
        Returns:
            Team instance
            
        Raises:
            Exception: If team is not available
        """
        team = self.teams.get(team_type)
        if not team:
            raise Exception(f"No team available for type: {team_type}")
        return team
    
    def _create_stimuli_payload(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create properly formatted stimuli payload from queue item.
        
        Args:
            item: Raw queue item
            
        Returns:
            Formatted stimuli dictionary
        """
        # Extract stimuli_id from metadata or generate one
        metadata = item.get("metadata", {})
        stimuli_id = metadata.get("stimuli_id") or f"queue_{int(datetime.now().timestamp())}"
        
        return {
            "stimuli_id": stimuli_id,  # 🔥 ENSURE stimuli_id is properly set
            "content": item.get("prompt", ""),
            "source": item.get("source", "queue"),
            "metadata": metadata
        }
    
    @with_error_handling("queue", "team_processing")
    async def _execute_team_processing(
        self, 
        team: SimplifiedAutoGenTeam, 
        team_type: str, 
        stimuli: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute team processing with proper logging.
        
        Args:
            team: Team instance to process with
            team_type: Type of team for logging
            stimuli: Formatted stimuli to process
            
        Returns:
            Processing result from team
        """
        stimuli_id = stimuli.get("stimuli_id", "unknown")
        
        # S2_PROCESSING_START timestamp
        processing_start_time = datetime.now()
        logger.info(f"S2_PROCESSING_START {stimuli_id} {processing_start_time.isoformat()}")
        
        error_handler.log_success("queue", f"selected_team_{team_type}", 
                                 context={"content_preview": stimuli["content"][:50]})
        
        result = await team.process_stimuli(stimuli)
        
        # S2_PROCESSING_COMPLETE timestamp
        processing_complete_time = datetime.now()
        logger.info(f"S2_PROCESSING_COMPLETE {stimuli_id} {processing_complete_time.isoformat()}")
        
        return result
    
    async def _handle_processing_result(
        self, 
        item: Dict[str, Any], 
        start_time: datetime, 
        team_type: str, 
        result: Dict[str, Any]
    ):
        """
        Handle successful processing result and update statistics.
        
        Args:
            item: Original queue item
            start_time: When processing started
            team_type: Type of team that processed
            result: Processing result
        """
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Check if we need to forward to S1
        processing_mode = item.get("processing_mode", "s2_only")
        if processing_mode == "s1_and_s2" and result.get("success"):
            await self._forward_to_s1(item, result)
        
        processed_item = {
            **item,
            "processed_at": datetime.now().isoformat(),
            "processing_time": processing_time,
            "team_type": team_type,
            "result": result
        }
        
        await self._save_processed(processed_item)
        
        if result.get("success"):
            self.stats["processed"] += 1
            error_handler.log_success("queue", "process_item", processing_time)
        else:
            self.stats["failed"] += 1
            error_handler.log_warning("queue", f"Team processing failed: {result.get('error')}")
    
    async def _handle_processing_error(
        self, 
        item: Dict[str, Any], 
        start_time: datetime, 
        error: Exception
    ):
        """
        Handle processing errors and save failed item details.
        
        Args:
            item: Original queue item
            start_time: When processing started
            error: Exception that occurred
        """
        self.stats["failed"] += 1
        processing_time = (datetime.now() - start_time).total_seconds()
        
        error_handler.log_with_traceback("queue", "process_item", error, 
                                       context={"processing_time": f"{processing_time:.2f}s"})
        
        # Save failed item for debugging
        failed_item = {
            **item,
            "processed_at": datetime.now().isoformat(),
            "processing_time": processing_time,
            "error": str(error),
            "success": False
        }
        
        await self._save_processed(failed_item)
    
    async def _forward_to_s1(self, item: Dict[str, Any], s2_result: Dict[str, Any]):
        """
        Forward processed content to S1 for speech generation.
        
        Args:
            item: Original queue item with metadata
            s2_result: Result from S2 processing
        """
        try:
            import aiohttp
            
            # Extract insights or summary from S2 result
            insights = s2_result.get("insights", {})
            content = item.get("prompt", "")
            
            # Create enhanced content with S2 insights
            enhanced_content = content
            if insights:
                # Add key insights to the speech content
                key_insights = []
                for category, items in insights.items():
                    if items and isinstance(items, list):
                        key_insights.extend(items[:1])  # Take first insight from each category
                
                if key_insights:
                    enhanced_content = f"{content}. {'. '.join(key_insights)}"
            
            # Get character information
            metadata = item.get("metadata", {})
            character_id = metadata.get("character_id") or metadata.get("character_type")
            
            logging.info(f"🔊 [QUEUE] Forwarding to S1 for speech generation")
            logging.info(f"   Character: {character_id}")
            logging.info(f"   Content preview: {enhanced_content[:100]}...")
            
            async with aiohttp.ClientSession() as session:
                # First, set the character if specified
                if character_id:
                    try:
                        char_payload = {"character_id": character_id}
                        async with session.post(
                            "http://neurosync_s1:5001/character/activate",
                            json=char_payload,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                logging.info(f"✅ [QUEUE] Character {character_id} activated in S1")
                            else:
                                logging.warning(f"⚠️ [QUEUE] Failed to activate character: {resp.status}")
                    except Exception as e:
                        logging.warning(f"⚠️ [QUEUE] Could not activate character: {e}")
                
                # Send text for speech generation
                try:
                    speech_payload = {"text": enhanced_content}
                    async with session.post(
                        "http://neurosync_s1:5001/process_text",
                        json=speech_payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            speech_result = await resp.json()
                            logging.info(f"✅ [QUEUE] S1 speech generation successful")
                            logging.info(f"   Audio file: {speech_result.get('audio_file', 'N/A')}")
                        else:
                            error_text = await resp.text()
                            logging.error(f"❌ [QUEUE] S1 returned {resp.status}: {error_text}")
                except Exception as e:
                    logging.error(f"❌ [QUEUE] Failed to send to S1: {e}")
                    
        except Exception as e:
            logging.error(f"❌ [QUEUE] Error forwarding to S1: {e}")
            import traceback
            traceback.print_exc()
    
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
        
        # Calculate processing duration if currently processing
        processing_duration = None
        if self.is_processing and self.processing_start_time:
            processing_duration = (datetime.now() - self.processing_start_time).total_seconds()
        
        return {
            "running": self.running,
            "processed": self.stats["processed"],
            "failed": self.stats["failed"],
            "teams_available": list(self.teams.keys()),
            "start_time": self.stats["start_time"],
            "queue_file": str(self.queue_file),
            "poll_interval": self.poll_interval,
            "task_status": task_status,
            "task_exception": str(task_exception) if task_exception else None,
            "is_processing": self.is_processing,
            "current_stimuli_id": self.current_stimuli_id,
            "processing_duration_seconds": processing_duration
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
    
    async def stop_current_processing(self):
        """Stop the current processing immediately."""
        
        if not self.is_processing:
            logging.info("ℹ️ [QUEUE] No processing currently active to stop")
            return {
                "success": False,
                "message": "No processing currently active",
                "was_processing": False
            }
        
        # Capture current state before clearing
        current_stimuli = self.current_stimuli_id
        processing_duration = None
        if self.processing_start_time:
            processing_duration = (datetime.now() - self.processing_start_time).total_seconds()
        
        try:
            logging.info(f"⏹️ [QUEUE] Stopping current processing: {current_stimuli}")
            
            # Set stop flag
            self.stop_requested = True
            
            # Try to stop the current team processing if available
            if self.current_team and hasattr(self.current_team, 'stop_processing'):
                try:
                    self.current_team.stop_processing()
                    logging.info("🛑 [QUEUE] Team processing stop requested")
                except Exception as e:
                    logging.warning(f"⚠️ [QUEUE] Could not stop team processing: {e}")
            
            # Wait a moment for graceful stop
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logging.error(f"❌ [QUEUE] Error during stop processing: {e}")
        
        finally:
            # ALWAYS clear the state to prevent stuck processing
            logging.info("🧹 [QUEUE] Clearing processing state")
            self.is_processing = False
            self.current_stimuli_id = None
            self.processing_start_time = None
            self.stop_requested = False
            self.current_team = None
            
            return {
                "success": True,
                "message": f"Stopped processing of stimuli: {current_stimuli}",
                "stopped_stimuli_id": current_stimuli,
                "processing_duration_seconds": processing_duration,
                "was_processing": True
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