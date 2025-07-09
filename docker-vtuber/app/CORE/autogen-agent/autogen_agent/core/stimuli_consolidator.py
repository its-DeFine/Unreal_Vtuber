"""
Stimuli Consolidation Engine

This module implements intelligent consolidation of multiple stimuli into unified commands
for both System 1 (S1 Avatar) and System 2 (AutoGen). It batches stimuli, analyzes them
for consolidation opportunities, and generates unified prompts that respect system capacity.

Key Features:
1. Intelligent stimuli batching based on content similarity and priority
2. Unified command generation for both S1 and S2 systems
3. Capacity-aware processing that respects system limitations
4. WebSocket-based continuous streaming support
5. Configurable consolidation strategies and thresholds
"""

import asyncio
import logging
import json
import os
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from ..utils.capacity_monitor import CapacityMonitor, CapacityStatus


class ConsolidationStrategy(Enum):
    """Different strategies for consolidating stimuli"""
    IMMEDIATE = "immediate"           # Process immediately, no batching
    TIME_BASED = "time_based"         # Batch within time window
    CONTENT_BASED = "content_based"   # Batch based on content similarity
    PRIORITY_BASED = "priority_based" # Batch based on priority levels
    INTELLIGENT = "intelligent"      # AI-driven consolidation analysis


class ProcessingMode(Enum):
    """Processing modes for consolidated stimuli"""
    S1_ONLY = "s1_only"              # Process only through S1 Avatar
    S2_ONLY = "s2_only"              # Process only through S2 AutoGen
    PARALLEL = "parallel"            # Process through both systems
    SEQUENTIAL = "sequential"        # Process S2 first, then S1
    ADAPTIVE = "adaptive"            # Choose based on capacity and content


@dataclass
class StimuliItem:
    """Represents a single stimuli item for consolidation"""
    stimuli_id: str
    content: str
    source: str
    priority: str
    category: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    confidence: Optional[float] = None
    original_request: Optional[Dict[str, Any]] = None


@dataclass
class ConsolidatedBatch:
    """Represents a batch of consolidated stimuli"""
    batch_id: str
    stimuli_items: List[StimuliItem]
    consolidation_strategy: ConsolidationStrategy
    processing_mode: ProcessingMode
    unified_s1_prompt: Optional[str] = None
    unified_s2_prompt: Optional[str] = None
    priority_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    estimated_processing_time: float = 0.0
    target_systems: List[str] = field(default_factory=list)


class StimuliConsolidator:
    """
    Main consolidation engine that batches stimuli and creates unified commands
    """
    
    def __init__(self, 
                 capacity_monitor: CapacityMonitor,
                 max_batch_size: int = 5,
                 batch_timeout: float = 3.0,
                 similarity_threshold: float = 0.7,
                 default_strategy: ConsolidationStrategy = ConsolidationStrategy.INTELLIGENT):
        """
        Initialize the stimuli consolidator
        
        Args:
            capacity_monitor: Monitor for system capacity
            max_batch_size: Maximum stimuli per batch
            batch_timeout: Maximum time to wait for batch completion (seconds)
            similarity_threshold: Threshold for content similarity grouping
            default_strategy: Default consolidation strategy
        """
        self.capacity_monitor = capacity_monitor
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
        self.similarity_threshold = similarity_threshold
        self.default_strategy = default_strategy
        
        # Pending stimuli waiting for consolidation
        self.pending_stimuli: List[StimuliItem] = []
        self.batch_queue: List[ConsolidatedBatch] = []
        
        # Processing state
        self.processing_active = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_stimuli_received": 0,
            "total_batches_created": 0,
            "total_stimuli_processed": 0,
            "consolidation_ratios": [],
            "average_batch_size": 0.0,
            "processing_times": []
        }
        
        logging.info("🔗 [CONSOLIDATOR] Initialized with max_batch_size=%d, timeout=%.1fs", 
                    max_batch_size, batch_timeout)
    
    async def start_processing(self):
        """Start the consolidation processing loop"""
        if self.processing_active:
            logging.warning("⚠️ [CONSOLIDATOR] Processing already active")
            return
        
        self.processing_active = True
        self.processor_task = asyncio.create_task(self._processing_loop())
        logging.info("🚀 [CONSOLIDATOR] Started consolidation processing")
    
    async def stop_processing(self):
        """Stop the consolidation processing"""
        self.processing_active = False
        
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logging.info("🛑 [CONSOLIDATOR] Stopped consolidation processing")
    
    async def add_stimuli(self, stimuli_data: Dict[str, Any]) -> str:
        """
        Add a new stimuli for consolidation
        
        Args:
            stimuli_data: Raw stimuli data from API
            
        Returns:
            str: Stimuli ID for tracking
        """
        stimuli_item = StimuliItem(
            stimuli_id=stimuli_data.get("stimuli_id", f"stimuli_{len(self.pending_stimuli)}_{int(datetime.now().timestamp())}"),
            content=stimuli_data.get("content", ""),
            source=stimuli_data.get("source", "unknown"),
            priority=stimuli_data.get("priority", "medium"),
            category=stimuli_data.get("category"),
            metadata=stimuli_data.get("metadata", {}),
            timestamp=datetime.now(),
            confidence=stimuli_data.get("confidence"),
            original_request=stimuli_data
        )
        
        self.pending_stimuli.append(stimuli_item)
        self.stats["total_stimuli_received"] += 1
        
        logging.info("📥 [CONSOLIDATOR] Added stimuli: %s (pending: %d)", 
                    stimuli_item.stimuli_id, len(self.pending_stimuli))
        
        return stimuli_item.stimuli_id
    
    async def _processing_loop(self):
        """Main processing loop for consolidation"""
        while self.processing_active:
            try:
                # Check if we should create a batch
                should_batch = await self._should_create_batch()
                
                if should_batch and self.pending_stimuli:
                    batch = await self._create_consolidated_batch()
                    if batch:
                        self.batch_queue.append(batch)
                        logging.info("📦 [CONSOLIDATOR] Created batch: %s with %d stimuli", 
                                   batch.batch_id, len(batch.stimuli_items))
                
                # Process queued batches
                await self._process_batch_queue()
                
                await asyncio.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logging.error("❌ [CONSOLIDATOR] Error in processing loop: %s", e)
                await asyncio.sleep(1.0)
    
    async def _should_create_batch(self) -> bool:
        """Determine if we should create a batch now"""
        if not self.pending_stimuli:
            return False
        
        # Check batch size threshold
        if len(self.pending_stimuli) >= self.max_batch_size:
            return True
        
        # Check timeout threshold
        oldest_stimuli = min(self.pending_stimuli, key=lambda s: s.timestamp)
        age = (datetime.now() - oldest_stimuli.timestamp).total_seconds()
        if age >= self.batch_timeout:
            return True
        
        # Check for high priority stimuli
        high_priority_count = sum(1 for s in self.pending_stimuli 
                                 if s.priority in ["high", "critical", "emergency"])
        if high_priority_count >= 2:
            return True
        
        # Check system capacity for immediate processing
        capacity = self.capacity_monitor.get_combined_capacity()
        if (capacity["overall_status"] == "fully_available" and 
            len(self.pending_stimuli) >= 2):
            return True
        
        return False
    
    async def _process_admin_commands(self):
        """Process admin commands directly through the admin character tool"""
        if not self.pending_stimuli:
            logging.info("🔍 [CONSOLIDATOR] No pending stimuli to process for admin commands")
            return
        
        admin_stimuli = []
        
        # Identify admin commands
        for stimuli in self.pending_stimuli[:]:
            content_lower = stimuli.content.lower()
            logging.info("🔍 [CONSOLIDATOR] Checking stimuli: %s", content_lower)
            if any(indicator in content_lower for indicator in ["admin:", "create character", "switch character", "list characters"]):
                admin_stimuli.append(stimuli)
                logging.info("🔍 [CONSOLIDATOR] Found admin command: %s", stimuli.content)
        
        # Process each admin command
        for admin_stimuli_item in admin_stimuli:
            try:
                logging.info("🔧 [CONSOLIDATOR] Processing admin command: %s", admin_stimuli_item.content)
                
                # Import admin character tool
                from .tools.admin_character_tool import execute_admin_character_tool
                
                # Create context for admin tool
                context = {
                    "content": admin_stimuli_item.content,
                    "source": admin_stimuli_item.source,
                    "priority": admin_stimuli_item.priority,
                    "stimuli_id": admin_stimuli_item.stimuli_id
                }
                
                # Execute admin command
                result = await execute_admin_character_tool(context)
                
                if result.get("success"):
                    logging.info("✅ [CONSOLIDATOR] Admin command executed successfully: %s", result.get("response", ""))
                    
                    # DESIGN DECISION: Admin operations should be silent by default
                    # Only send to S1 if explicitly requested via "announce" flag
                    admin_response = result.get("response", "")
                    should_announce = (
                        result.get("announce_to_s1", False) or  # Explicit announcement flag
                        "announce:" in admin_stimuli_item.content.lower()  # Explicit announce request
                    )
                    
                    logging.info("🔍 [CONSOLIDATOR] Admin announcement check: announce_to_s1=%s, content_has_announce=%s, should_announce=%s", 
                                result.get("announce_to_s1", False), 
                                "announce:" in admin_stimuli_item.content.lower(),
                                should_announce)
                    
                    if should_announce and admin_response and not result.get("skip"):
                        logging.info("📢 [CONSOLIDATOR] Announcing admin result to S1: %s", admin_response[:100])
                        await self._send_to_s1(admin_response)
                    else:
                        logging.info("🔇 [CONSOLIDATOR] Admin operation completed silently (no S1 announcement)")
                        
                    # Store admin operation result for S2 logging/history
                    await self._log_admin_operation(admin_stimuli_item, result)
                        
                else:
                    if not result.get("skip"):
                        logging.error("❌ [CONSOLIDATOR] Admin command failed: %s", result.get("error", "Unknown error"))
                
                # Remove processed admin stimuli
                if admin_stimuli_item in self.pending_stimuli:
                    self.pending_stimuli.remove(admin_stimuli_item)
                    
            except Exception as e:
                logging.error("❌ [CONSOLIDATOR] Error processing admin command: %s", e)
                # Remove the problematic stimuli to prevent infinite loops
                if admin_stimuli_item in self.pending_stimuli:
                    self.pending_stimuli.remove(admin_stimuli_item)
    
    async def _log_admin_operation(self, admin_stimuli_item: 'StimuliItem', result: Dict[str, Any]):
        """Log admin operation result for S2 system history and control panel access"""
        try:
            admin_log_entry = {
                "timestamp": datetime.now().isoformat(),
                "stimuli_id": admin_stimuli_item.stimuli_id,
                "command": admin_stimuli_item.content,
                "source": admin_stimuli_item.source,
                "priority": admin_stimuli_item.priority,
                "result": {
                    "success": result.get("success", False),
                    "response": result.get("response", ""),
                    "command_type": result.get("command_type", "unknown"),
                    "character_data": result.get("character_data", {}),
                    "error": result.get("error")
                }
            }
            
            # Store in consolidation stats for S2 access
            if not hasattr(self, 'admin_operation_history'):
                self.admin_operation_history = []
            
            self.admin_operation_history.append(admin_log_entry)
            
            # Keep only last 100 admin operations
            if len(self.admin_operation_history) > 100:
                self.admin_operation_history = self.admin_operation_history[-100:]
                
            # Update stats
            self.stats["admin_operations_processed"] = self.stats.get("admin_operations_processed", 0) + 1
            
            logging.info("📝 [CONSOLIDATOR] Admin operation logged for S2 access: %s", admin_stimuli_item.stimuli_id)
            
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error logging admin operation: %s", e)
    
    async def _create_consolidated_batch(self) -> Optional[ConsolidatedBatch]:
        """Create a consolidated batch from pending stimuli"""
        if not self.pending_stimuli:
            return None
        
        try:
            # FIRST: Check for admin commands and process them directly
            await self._process_admin_commands()
            
            # If no regular stimuli remain, return None
            if not self.pending_stimuli:
                return None
            
            # Determine consolidation strategy
            strategy = await self._select_consolidation_strategy()
            
            # Group stimuli based on strategy
            grouped_stimuli = await self._group_stimuli_by_strategy(strategy)
            
            # Take the best group for this batch
            if not grouped_stimuli:
                # Fallback: take all pending stimuli
                batch_stimuli = self.pending_stimuli[:self.max_batch_size]
            else:
                # Take the largest or highest priority group
                batch_stimuli = max(grouped_stimuli, key=lambda g: len(g))
                if len(batch_stimuli) > self.max_batch_size:
                    batch_stimuli = batch_stimuli[:self.max_batch_size]
            
            # Remove selected stimuli from pending
            for stimuli in batch_stimuli:
                if stimuli in self.pending_stimuli:
                    self.pending_stimuli.remove(stimuli)
            
            # Determine processing mode
            processing_mode = await self._select_processing_mode(batch_stimuli)
            
            # Create consolidated batch
            batch = ConsolidatedBatch(
                batch_id=f"batch_{int(datetime.now().timestamp())}_{len(batch_stimuli)}",
                stimuli_items=batch_stimuli,
                consolidation_strategy=strategy,
                processing_mode=processing_mode,
                priority_score=self._calculate_priority_score(batch_stimuli)
            )
            
            # Generate unified prompts
            await self._generate_unified_prompts(batch)
            
            self.stats["total_batches_created"] += 1
            self._update_stats(batch)
            
            return batch
            
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error creating batch: %s", e)
            return None
    
    async def _select_consolidation_strategy(self) -> ConsolidationStrategy:
        """Select the best consolidation strategy for current stimuli"""
        if len(self.pending_stimuli) == 1:
            return ConsolidationStrategy.IMMEDIATE
        
        # Check for emergency/critical priority
        has_critical = any(s.priority in ["critical", "emergency"] for s in self.pending_stimuli)
        if has_critical:
            return ConsolidationStrategy.PRIORITY_BASED
        
        # Check content similarity
        if await self._has_similar_content():
            return ConsolidationStrategy.CONTENT_BASED
        
        # Default to intelligent strategy
        return ConsolidationStrategy.INTELLIGENT
    
    async def _has_similar_content(self) -> bool:
        """Check if pending stimuli have similar content"""
        if len(self.pending_stimuli) < 2:
            return False
        
        # Simple keyword-based similarity check
        all_words = set()
        stimuli_words = []
        
        for stimuli in self.pending_stimuli:
            words = set(stimuli.content.lower().split())
            stimuli_words.append(words)
            all_words.update(words)
        
        # Calculate average similarity
        similarity_scores = []
        for i in range(len(stimuli_words)):
            for j in range(i + 1, len(stimuli_words)):
                words1, words2 = stimuli_words[i], stimuli_words[j]
                if words1 and words2:
                    intersection = len(words1.intersection(words2))
                    union = len(words1.union(words2))
                    similarity = intersection / union if union > 0 else 0
                    similarity_scores.append(similarity)
        
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            return avg_similarity >= self.similarity_threshold
        
        return False
    
    async def _group_stimuli_by_strategy(self, strategy: ConsolidationStrategy) -> List[List[StimuliItem]]:
        """Group stimuli based on the selected strategy"""
        if strategy == ConsolidationStrategy.IMMEDIATE:
            return [[s] for s in self.pending_stimuli]
        
        elif strategy == ConsolidationStrategy.PRIORITY_BASED:
            priority_groups = defaultdict(list)
            for stimuli in self.pending_stimuli:
                priority_groups[stimuli.priority].append(stimuli)
            return list(priority_groups.values())
        
        elif strategy == ConsolidationStrategy.CONTENT_BASED:
            # Simple content-based grouping by category and keywords
            category_groups = defaultdict(list)
            for stimuli in self.pending_stimuli:
                key = stimuli.category or "uncategorized"
                category_groups[key].append(stimuli)
            return list(category_groups.values())
        
        elif strategy == ConsolidationStrategy.TIME_BASED:
            # Group by time window (e.g., last 5 seconds)
            cutoff = datetime.now() - timedelta(seconds=5)
            recent = [s for s in self.pending_stimuli if s.timestamp >= cutoff]
            older = [s for s in self.pending_stimuli if s.timestamp < cutoff]
            return [group for group in [recent, older] if group]
        
        else:  # INTELLIGENT
            # For now, use a combination of priority and content
            return await self._intelligent_grouping()
    
    async def _intelligent_grouping(self) -> List[List[StimuliItem]]:
        """Intelligent grouping using multiple factors"""
        groups = []
        remaining = self.pending_stimuli.copy()
        
        while remaining:
            # Start with the highest priority item
            pivot = max(remaining, key=lambda s: self._get_priority_value(s.priority))
            group = [pivot]
            remaining.remove(pivot)
            
            # Add related items to the group
            to_remove = []
            for stimuli in remaining:
                if self._should_group_together(pivot, stimuli):
                    group.append(stimuli)
                    to_remove.append(stimuli)
                    if len(group) >= self.max_batch_size:
                        break
            
            for item in to_remove:
                remaining.remove(item)
            
            groups.append(group)
        
        return groups
    
    def _should_group_together(self, item1: StimuliItem, item2: StimuliItem) -> bool:
        """Determine if two stimuli items should be grouped together"""
        # Same priority level
        if item1.priority == item2.priority:
            return True
        
        # Same category
        if item1.category and item2.category and item1.category == item2.category:
            return True
        
        # Similar source
        if item1.source == item2.source:
            return True
        
        # Content similarity (simple keyword check)
        words1 = set(item1.content.lower().split())
        words2 = set(item2.content.lower().split())
        if words1 and words2:
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            similarity = intersection / union if union > 0 else 0
            if similarity >= 0.3:  # Lower threshold for grouping
                return True
        
        return False
    
    def _get_priority_value(self, priority: str) -> int:
        """Convert priority string to numeric value"""
        priority_values = {
            "emergency": 5,
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_values.get(priority.lower(), 2)
    
    async def _select_processing_mode(self, stimuli_items: List[StimuliItem]) -> ProcessingMode:
        """Select the best processing mode for the batch"""
        capacity = self.capacity_monitor.get_combined_capacity()
        
        # Check system availability
        s1_available = capacity["s1_capacity"]["status"] in ["available", "busy"]
        s2_available = capacity["s2_capacity"]["status"] in ["available", "busy"]
        
        # Check content type preferences
        has_simple_content = any(len(s.content.split()) <= 10 for s in stimuli_items)
        has_complex_content = any(len(s.content.split()) > 20 for s in stimuli_items)
        
        # Priority-based decisions
        has_high_priority = any(s.priority in ["high", "critical", "emergency"] for s in stimuli_items)
        
        if has_high_priority and s1_available:
            return ProcessingMode.S1_ONLY if has_simple_content else ProcessingMode.PARALLEL
        
        if s1_available and s2_available:
            if has_simple_content and not has_complex_content:
                return ProcessingMode.S1_ONLY
            elif has_complex_content:
                return ProcessingMode.PARALLEL
            else:
                return ProcessingMode.ADAPTIVE
        
        elif s1_available:
            return ProcessingMode.S1_ONLY
        elif s2_available:
            return ProcessingMode.S2_ONLY
        else:
            # Both systems busy, choose based on estimated wait time
            s1_wait = capacity["s1_capacity"].get("estimated_free_time", float("inf"))
            s2_wait = capacity["s2_capacity"].get("estimated_free_time", float("inf"))
            return ProcessingMode.S1_ONLY if s1_wait <= s2_wait else ProcessingMode.S2_ONLY
    
    async def _generate_unified_prompts(self, batch: ConsolidatedBatch):
        """Generate unified prompts for both S1 and S2 systems"""
        try:
            # Generate S1 prompt (simple, direct speech)
            if batch.processing_mode in [ProcessingMode.S1_ONLY, ProcessingMode.PARALLEL, ProcessingMode.SEQUENTIAL]:
                batch.unified_s1_prompt = self._generate_s1_prompt(batch)
            
            # Generate S2 prompt (detailed analysis request)
            if batch.processing_mode in [ProcessingMode.S2_ONLY, ProcessingMode.PARALLEL, ProcessingMode.SEQUENTIAL]:
                batch.unified_s2_prompt = self._generate_s2_prompt(batch)
            
            # Set target systems
            if batch.processing_mode == ProcessingMode.S1_ONLY:
                batch.target_systems = ["s1"]
            elif batch.processing_mode == ProcessingMode.S2_ONLY:
                batch.target_systems = ["s2"]
            else:
                batch.target_systems = ["s1", "s2"]
            
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error generating prompts: %s", e)
    
    def _generate_s1_prompt(self, batch: ConsolidatedBatch) -> str:
        """Generate unified prompt for S1 Avatar (speech synthesis)"""
        if len(batch.stimuli_items) == 1:
            return batch.stimuli_items[0].content
        
        # Multiple stimuli - create consolidated response with actual content
        priority_levels = [s.priority for s in batch.stimuli_items]
        has_urgent = any(p in ["critical", "emergency", "high"] for p in priority_levels)
        
        # Include actual stimuli content for meaningful speech
        content_parts = []
        for i, stimuli in enumerate(batch.stimuli_items, 1):
            content_parts.append(f"{stimuli.content}")
        
        if has_urgent:
            return f"I have {len(batch.stimuli_items)} important updates: " + ". ".join(content_parts)
        else:
            return f"I have {len(batch.stimuli_items)} messages: " + ". ".join(content_parts)
    
    def _generate_s2_prompt(self, batch: ConsolidatedBatch) -> str:
        """Generate unified prompt for S2 AutoGen team (detailed analysis)"""
        prompt_parts = [
            f"🎯 CONSOLIDATED STIMULI ANALYSIS REQUEST",
            f"",
            f"Batch Information:",
            f"- Batch ID: {batch.batch_id}",
            f"- Total Stimuli: {len(batch.stimuli_items)}",
            f"- Consolidation Strategy: {batch.consolidation_strategy.value}",
            f"- Priority Score: {batch.priority_score:.2f}",
            f"",
            f"Stimuli Details:"
        ]
        
        for i, stimuli in enumerate(batch.stimuli_items, 1):
            prompt_parts.extend([
                f"",
                f"{i}. Stimuli ID: {stimuli.stimuli_id}",
                f"   Content: {stimuli.content}",
                f"   Source: {stimuli.source}",
                f"   Priority: {stimuli.priority}",
                f"   Category: {stimuli.category or 'uncategorized'}",
                f"   Timestamp: {stimuli.timestamp.strftime('%H:%M:%S')}"
            ])
        
        prompt_parts.extend([
            f"",
            f"Team Objective:",
            f"Analyze these consolidated stimuli and determine optimal unified response(s).",
            f"Consider relationships between stimuli, priority levels, and system objectives.",
            f"Provide consolidated recommendations for action."
        ])
        
        return "\n".join(prompt_parts)
    
    def _calculate_priority_score(self, stimuli_items: List[StimuliItem]) -> float:
        """Calculate overall priority score for the batch"""
        priority_weights = {
            "emergency": 1.0,
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.2
        }
        
        total_weight = sum(priority_weights.get(s.priority.lower(), 0.4) for s in stimuli_items)
        return total_weight / len(stimuli_items) if stimuli_items else 0.0
    
    async def _process_batch_queue(self):
        """Process queued batches based on capacity and priority"""
        if not self.batch_queue:
            return
        
        capacity = self.capacity_monitor.get_combined_capacity()
        if not capacity["can_accept_stimuli"]:
            return
        
        # Sort by priority score (highest first)
        self.batch_queue.sort(key=lambda b: b.priority_score, reverse=True)
        
        # Process the highest priority batch that can be handled
        for batch in self.batch_queue[:]:
            if await self._can_process_batch(batch, capacity):
                await self._execute_batch(batch)
                self.batch_queue.remove(batch)
                break
    
    async def _can_process_batch(self, batch: ConsolidatedBatch, capacity: Dict[str, Any]) -> bool:
        """Check if a batch can be processed given current capacity"""
        required_systems = set(batch.target_systems)
        
        if "s1" in required_systems:
            if capacity["s1_capacity"]["status"] not in ["available", "busy"]:
                return False
        
        if "s2" in required_systems:
            if capacity["s2_capacity"]["status"] not in ["available", "busy"]:
                return False
        
        return True
    
    async def _execute_batch(self, batch: ConsolidatedBatch):
        """Execute a consolidated batch by sending requests to actual systems"""
        start_time = datetime.now()
        
        try:
            logging.info("🚀 [CONSOLIDATOR] Executing batch: %s with %d stimuli", 
                        batch.batch_id, len(batch.stimuli_items))
            
            logging.info("   S1 Prompt: %s", batch.unified_s1_prompt[:100] if batch.unified_s1_prompt else "None")
            logging.info("   S2 Prompt: %s", batch.unified_s2_prompt[:100] if batch.unified_s2_prompt else "None")
            logging.info("   Target Systems: %s", batch.target_systems)
            
            # Execute on target systems
            if "s1" in batch.target_systems and batch.unified_s1_prompt:
                await self._send_to_s1(batch.unified_s1_prompt)
            
            if "s2" in batch.target_systems and batch.unified_s2_prompt:
                await self._send_to_s2(batch.unified_s2_prompt)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["total_stimuli_processed"] += len(batch.stimuli_items)
            self.stats["processing_times"].append(processing_time)
            
            logging.info("✅ [CONSOLIDATOR] Batch executed in %.3fs", processing_time)
            
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error executing batch: %s", e)
    
    async def _send_to_s1(self, prompt: str):
        """Send consolidated prompt to S1 Avatar for speech synthesis"""
        try:
            import aiohttp
            s1_endpoint = os.getenv("S1_AVATAR_ENDPOINT", "http://neurosync:5001")
            
            payload = {
                "text": prompt,
                "direct_speech": True,  # Enable direct speech to trigger TTS and blendshape generation
                "autonomous_context": {
                    "source": "reactive_orchestrator",  # Required for direct speech processing
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{s1_endpoint}/process_text", 
                                      json=payload, 
                                      timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        logging.info("✅ [CONSOLIDATOR] S1 request successful: %s", result.get("status", "unknown"))
                    else:
                        logging.error("❌ [CONSOLIDATOR] S1 request failed with status: %d", response.status)
                        
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error sending to S1: %s", e)
    
    async def _send_to_s2(self, prompt: str):
        """Send consolidated prompt to S2 AutoGen (placeholder for now)"""
        try:
            # For now, just log - S2 processing could be implemented later
            logging.info("📝 [CONSOLIDATOR] S2 prompt would be processed: %s", prompt[:100])
        except Exception as e:
            logging.error("❌ [CONSOLIDATOR] Error sending to S2: %s", e)
    
    def _update_stats(self, batch: ConsolidatedBatch):
        """Update consolidation statistics"""
        batch_size = len(batch.stimuli_items)
        
        # Update consolidation ratio (how many stimuli were batched together)
        if batch_size > 1:
            self.stats["consolidation_ratios"].append(batch_size)
        
        # Update average batch size
        total_batches = self.stats["total_batches_created"]
        if total_batches > 0:
            total_stimuli = sum(self.stats["consolidation_ratios"]) + (total_batches - len(self.stats["consolidation_ratios"]))
            self.stats["average_batch_size"] = total_stimuli / total_batches
    
    def get_status(self) -> Dict[str, Any]:
        """Get current consolidator status"""
        return {
            "processing_active": self.processing_active,
            "pending_stimuli": len(self.pending_stimuli),
            "batch_queue": len(self.batch_queue),
            "statistics": self.stats,
            "configuration": {
                "max_batch_size": self.max_batch_size,
                "batch_timeout": self.batch_timeout,
                "similarity_threshold": self.similarity_threshold,
                "default_strategy": self.default_strategy.value
            },
            "capacity_status": self.capacity_monitor.get_combined_capacity(),
            "admin_operations": {
                "total_processed": self.stats.get("admin_operations_processed", 0),
                "recent_history": getattr(self, 'admin_operation_history', [])[-5:],  # Last 5 operations
                "history_count": len(getattr(self, 'admin_operation_history', []))
            }
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status for debugging"""
        return {
            **self.get_status(),
            "pending_stimuli_details": [
                {
                    "id": s.stimuli_id,
                    "content": s.content[:50],
                    "priority": s.priority,
                    "age_seconds": (datetime.now() - s.timestamp).total_seconds()
                }
                for s in self.pending_stimuli
            ],
            "batch_queue_details": [
                {
                    "id": b.batch_id,
                    "stimuli_count": len(b.stimuli_items),
                    "strategy": b.consolidation_strategy.value,
                    "mode": b.processing_mode.value,
                    "priority_score": b.priority_score,
                    "target_systems": b.target_systems
                }
                for b in self.batch_queue
            ]
        }


# Global consolidator instance
global_consolidator: Optional[StimuliConsolidator] = None


def get_consolidator() -> Optional[StimuliConsolidator]:
    """Get the global consolidator instance"""
    return global_consolidator


def initialize_consolidator(capacity_monitor: CapacityMonitor, **kwargs) -> StimuliConsolidator:
    """Initialize the global consolidator"""
    global global_consolidator
    
    if global_consolidator:
        logging.warning("⚠️ [CONSOLIDATOR] Already initialized")
        return global_consolidator
    
    global_consolidator = StimuliConsolidator(capacity_monitor, **kwargs)
    logging.info("✅ [CONSOLIDATOR] Global consolidator initialized")
    return global_consolidator