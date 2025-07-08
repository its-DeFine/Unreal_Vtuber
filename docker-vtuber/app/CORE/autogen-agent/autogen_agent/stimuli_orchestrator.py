"""
Enhanced Stimuli-Responsive Orchestrator for System 2 (AutoGen Agent)

This module implements a sophisticated orchestration pattern with separate AutoGen teams:
1. Main autonomous team - continuous operations
2. Stimuli-specific team - dedicated stimuli analysis and decision-making

The orchestrator manages both teams concurrently and uses a unified action executor
for all stimuli responses (objective updates, knowledge push, placeholder actions).

Key Features:
1. Separate stimuli-specific AutoGen team
2. Unified stimuli action executor tool
3. Objective bridge for main team updates
4. Cognee knowledge integration
5. Placeholder action execution system
6. True concurrent team execution
"""

import os
import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import existing components
from .tool_registry import ToolRegistry
from .clients.scb_client import SCBClient
from .clients.vtuber_client import VTuberClient
from .agent_tool_bridge import AgentToolBridge

# Import new stimuli-specific components
try:
    from .stimuli_autogen_team import StimuliAutoGenTeam
    STIMULI_TEAM_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ [STIMULI_ORCHESTRATOR] StimuliAutoGenTeam not available: {e}")
    STIMULI_TEAM_AVAILABLE = False
    StimuliAutoGenTeam = None

from .objective_bridge import get_objective_bridge, initialize_objective_bridge

# Import new consolidation components
try:
    from .capacity_monitor import CapacityMonitor, initialize_capacity_monitor, get_capacity_monitor
    from .stimuli_consolidator import StimuliConsolidator, initialize_consolidator, get_consolidator
    CONSOLIDATION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ [STIMULI_ORCHESTRATOR] Consolidation components not available: {e}")
    CONSOLIDATION_AVAILABLE = False
    CapacityMonitor = None
    StimuliConsolidator = None


class StimuliPriority(Enum):
    """Priority levels for stimuli processing"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AutonomousState(Enum):
    """States of the autonomous system"""
    RUNNING = "running"
    PAUSED = "paused"
    PROCESSING_STIMULI = "processing_stimuli"
    STOPPED = "stopped"


@dataclass
class StimuliRequest:
    """Represents a stimuli request from GraphFlow"""
    stimuli_id: str
    content: str
    source: str
    priority: StimuliPriority
    metadata: Dict[str, Any]
    timestamp: datetime
    category: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class StimuliResponse:
    """Response from stimuli processing"""
    stimuli_id: str
    success: bool
    processing_time: float
    tools_triggered: List[str]
    agent_decision: Optional[str] = None
    response_content: Optional[str] = None
    error_message: Optional[str] = None


class StimuliResponsiveOrchestrator:
    """
    Enhanced orchestrator that manages both main autonomous team and stimuli-specific team
    with unified action execution through stimuli_action_executor tool
    """
    
    def __init__(self, 
                 tool_registry: ToolRegistry,
                 scb_client: SCBClient, 
                 vtuber_client: VTuberClient,
                 autonomous_loop_function,
                 loop_interval: int = 20,
                 enable_consolidation: bool = True):
        self.tool_registry = tool_registry
        self.scb_client = scb_client
        self.vtuber_client = vtuber_client
        self.autonomous_loop_function = autonomous_loop_function
        self.loop_interval = loop_interval
        self.enable_consolidation = enable_consolidation
        
        # State management for main autonomous team
        self.autonomous_state = AutonomousState.STOPPED
        self.autonomous_task: Optional[asyncio.Task] = None
        self.stimuli_queue = asyncio.Queue()
        self.current_stimuli: Optional[StimuliRequest] = None
        
        # Initialize stimuli-specific AutoGen team
        if STIMULI_TEAM_AVAILABLE and StimuliAutoGenTeam:
            self.stimuli_team = StimuliAutoGenTeam()
            self.stimuli_team_initialized = False
        else:
            self.stimuli_team = None
            self.stimuli_team_initialized = False
        
        # Initialize objective bridge for team coordination
        self.objective_bridge = None
        
        # Agent tool bridge for legacy compatibility
        self.agent_tool_bridge = AgentToolBridge(tool_registry)
        
        # Initialize consolidation components
        self.capacity_monitor: Optional[CapacityMonitor] = None
        self.consolidator: Optional[StimuliConsolidator] = None
        self.consolidation_enabled = False
        
        # Enhanced statistics
        self.stats = {
            "stimuli_processed": 0,
            "autonomous_cycles": 0,
            "avg_stimuli_processing_time": 0.0,
            "stimuli_team_decisions": 0,
            "objective_updates": 0,
            "knowledge_pushes": 0,
            "placeholder_actions": 0,
            "tools_triggered_count": {},
            "last_stimuli_timestamp": None,
            "concurrent_operations": 0
        }
        
        logging.info("🎯 [STIMULI_ORCHESTRATOR] Enhanced orchestrator initialized with dual-team architecture")
    
    async def start(self):
        """Start the orchestrator with autonomous mode enabled"""
        logging.info("🚀 [STIMULI_ORCHESTRATOR] Starting enhanced orchestrator...")
        
        # Initialize objective bridge
        self.objective_bridge = await initialize_objective_bridge()
        logging.info("🌉 [STIMULI_ORCHESTRATOR] Objective bridge initialized")
        
        # Initialize stimuli-specific AutoGen team
        if self.stimuli_team and self.stimuli_team.initialize_team():
            self.stimuli_team_initialized = True
            logging.info("🎯 [STIMULI_ORCHESTRATOR] Stimuli AutoGen team initialized successfully")
        else:
            self.stimuli_team_initialized = False
            logging.warning("⚠️ [STIMULI_ORCHESTRATOR] Stimuli team not available - using legacy mode")
        
        # Initialize consolidation components
        if self.enable_consolidation and CONSOLIDATION_AVAILABLE:
            await self._initialize_consolidation()
        
        # Start autonomous loop
        await self._start_autonomous_mode()
        
        # Start stimuli processing in background
        asyncio.create_task(self._stimuli_processing_loop())
        
        logging.info("✅ [STIMULI_ORCHESTRATOR] Enhanced orchestrator started successfully")
    
    async def stop(self):
        """Stop the orchestrator completely"""
        logging.info("🛑 [STIMULI_ORCHESTRATOR] Stopping orchestrator...")
        
        # Stop consolidation components
        if self.consolidation_enabled:
            await self._shutdown_consolidation()
        
        await self._stop_autonomous_mode()
        self.autonomous_state = AutonomousState.STOPPED
        
        logging.info("✅ [STIMULI_ORCHESTRATOR] Orchestrator stopped")
    
    async def receive_stimuli(self, stimuli_data: Dict[str, Any]) -> StimuliResponse:
        """
        Main entry point for receiving stimuli from GraphFlow.
        Routes through consolidation system if enabled, otherwise processes directly.
        """
        start_time = time.time()
        
        # Create stimuli request
        stimuli_request = StimuliRequest(
            stimuli_id=stimuli_data.get("stimuli_id", f"stimuli_{int(time.time())}"),
            content=stimuli_data.get("content", ""),
            source=stimuli_data.get("source", "unknown"),
            priority=StimuliPriority(stimuli_data.get("priority", "medium")),
            metadata=stimuli_data.get("metadata", {}),
            timestamp=datetime.now(),
            category=stimuli_data.get("category"),
            confidence=stimuli_data.get("confidence")
        )
        
        logging.info(f"📨 [STIMULI_ORCHESTRATOR] Received stimuli: {stimuli_request.stimuli_id} "
                    f"(priority: {stimuli_request.priority.value})")
        
        try:
            # Route through consolidation if enabled and available
            if self.consolidation_enabled and self.consolidator:
                return await self._process_stimuli_with_consolidation(stimuli_request, stimuli_data)
            else:
                # Use legacy direct processing
                return await self._process_stimuli_direct(stimuli_request)
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error processing stimuli {stimuli_request.stimuli_id}: {e}")
            
            # Ensure autonomous mode is resumed even on error
            if self.autonomous_state == AutonomousState.PAUSED:
                await self._resume_autonomous_mode()
            
            return StimuliResponse(
                stimuli_id=stimuli_request.stimuli_id,
                success=False,
                processing_time=time.time() - start_time,
                tools_triggered=[],
                error_message=str(e)
            )
    
    async def _process_stimuli_direct(self, stimuli_request: StimuliRequest) -> StimuliResponse:
        """Process individual stimuli directly (legacy mode without consolidation)"""
        start_time = time.time()
        self.current_stimuli = stimuli_request
        
        logging.info(f"🔄 [STIMULI_ORCHESTRATOR] Processing stimuli directly: {stimuli_request.content[:100]}...")
        
        try:
            # Pause autonomous operations for critical/emergency stimuli
            if stimuli_request.priority in [StimuliPriority.CRITICAL, StimuliPriority.EMERGENCY]:
                await self._pause_autonomous_mode()
                logging.info(f"⏸️ [STIMULI_ORCHESTRATOR] Paused autonomous mode for {stimuli_request.priority.value} stimuli")
            
            # Use stimuli-specific AutoGen team if available
            if self.stimuli_team_initialized:
                team_decision = await self._process_stimuli_with_autogen_team(stimuli_request)
                
                # Execute unified action based on team decision
                action_result = await self._execute_unified_action(team_decision, stimuli_request)
                
                result = StimuliResponse(
                    stimuli_id=stimuli_request.stimuli_id,
                    success=action_result.get("success", False),
                    processing_time=time.time() - start_time,
                    tools_triggered=[action_result.get("tool_used", "stimuli_action_executor")],
                    agent_decision=team_decision.get("agent_reasoning", ""),
                    response_content=action_result.get("message", "")
                )
            else:
                # Fallback to legacy tool selection
                result = await self._process_stimuli_legacy(stimuli_request)
            
            # Resume autonomous operations if they were paused
            if stimuli_request.priority in [StimuliPriority.CRITICAL, StimuliPriority.EMERGENCY]:
                await self._resume_autonomous_mode()
                logging.info("▶️ [STIMULI_ORCHESTRATOR] Resumed autonomous mode")
            
            return result
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error processing stimuli: {e}")
            
            # Ensure autonomous mode is resumed even on error
            if self.autonomous_state == AutonomousState.PAUSED:
                await self._resume_autonomous_mode()
            
            return StimuliResponse(
                stimuli_id=stimuli_request.stimuli_id,
                success=False,
                processing_time=time.time() - start_time,
                tools_triggered=[],
                error_message=str(e)
            )
    
    async def _process_stimuli_with_consolidation(self, stimuli_request: StimuliRequest, stimuli_data: Dict[str, Any]) -> StimuliResponse:
        """Process stimuli through the consolidation system"""
        start_time = time.time()
        
        try:
            logging.info(f"🔗 [STIMULI_ORCHESTRATOR] Processing stimuli with consolidation: {stimuli_request.stimuli_id}")
            
            # Register S2 discussion with capacity monitor if this goes to S2
            if self.capacity_monitor:
                discussion_id = f"stimuli_{stimuli_request.stimuli_id}"
                self.capacity_monitor.register_s2_discussion_start(discussion_id)
            
            # Add stimuli to consolidator
            stimuli_id = await self.consolidator.add_stimuli(stimuli_data)
            
            # For now, return a success response - the consolidator will handle actual processing
            # In the future, this could wait for batch completion or return immediately
            return StimuliResponse(
                stimuli_id=stimuli_request.stimuli_id,
                success=True,
                processing_time=time.time() - start_time,
                tools_triggered=["consolidation_system"],
                agent_decision="Stimuli added to consolidation queue for intelligent batching",
                response_content=f"Stimuli {stimuli_id} queued for consolidation processing"
            )
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error in consolidation processing: {e}")
            # Fallback to direct processing
            logging.info("⚡ [STIMULI_ORCHESTRATOR] Falling back to direct processing")
            return await self._process_stimuli_direct(stimuli_request)
        
        finally:
            # Clean up S2 discussion tracking
            if self.capacity_monitor:
                discussion_id = f"stimuli_{stimuli_request.stimuli_id}"
                self.capacity_monitor.register_s2_discussion_end(discussion_id)
    
    async def _process_stimuli_with_autogen_team(self, stimuli_request: StimuliRequest) -> Dict[str, Any]:
        """Process stimuli using the dedicated AutoGen team"""
        try:
            # Prepare stimuli data for team analysis
            stimuli_data = {
                "content": stimuli_request.content,
                "source": stimuli_request.source,
                "priority": stimuli_request.priority.value,
                "category": stimuli_request.category,
                "metadata": stimuli_request.metadata,
                "timestamp": stimuli_request.timestamp.isoformat()
            }
            
            # Process with stimuli AutoGen team
            team_decision = await self.stimuli_team.process_stimuli_with_team(stimuli_data)
            
            # Update statistics
            self.stats["stimuli_team_decisions"] += 1
            
            logging.info(f"🎯 [STIMULI_ORCHESTRATOR] Team decision: {team_decision.get('action_type', 'unknown')}")
            return team_decision
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error in team processing: {e}")
            # Return default knowledge push action
            return {
                "action_type": "knowledge_push",
                "knowledge_data": {
                    "error": str(e),
                    "stimuli_content": stimuli_request.content,
                    "timestamp": datetime.now().isoformat()
                },
                "agent_reasoning": f"Error in team processing: {e}",
                "priority": "low"
            }
    
    async def _execute_unified_action(self, team_decision: Dict[str, Any], stimuli_request: StimuliRequest) -> Dict[str, Any]:
        """Execute the unified action based on team decision"""
        try:
            # Prepare context for stimuli_action_executor tool
            action_context = {
                **team_decision,  # Include all team decision parameters
                "vtuber_client": self.vtuber_client,
                "scb_client": self.scb_client,
                "stimuli_id": stimuli_request.stimuli_id,
                "stimuli_request": {
                    "content": stimuli_request.content,
                    "source": stimuli_request.source,
                    "priority": stimuli_request.priority.value,
                    "category": stimuli_request.category
                }
            }
            
            # Execute the stimuli_action_executor tool
            action_result = await self.tool_registry.execute_tool_async("stimuli_action_executor", action_context)
            
            # Update statistics based on action type
            action_type = team_decision.get("action_type", "unknown")
            if action_type == "objective_update":
                self.stats["objective_updates"] += 1
                
                # Add objectives to bridge if available
                if self.objective_bridge and "objective_updates" in team_decision:
                    self.objective_bridge.add_objectives_from_stimuli(
                        team_decision["objective_updates"],
                        source="stimuli_team_decision"
                    )
                    
            elif action_type == "knowledge_push":
                self.stats["knowledge_pushes"] += 1
            elif action_type == "placeholder_action":
                self.stats["placeholder_actions"] += 1
            
            logging.info(f"✅ [STIMULI_ORCHESTRATOR] Unified action executed: {action_type}")
            return action_result
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error executing unified action: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Action execution failed: {e}"
            }
    
    async def _process_stimuli_legacy(self, stimuli_request: StimuliRequest) -> StimuliResponse:
        """Legacy stimuli processing method (fallback)"""
        start_time = time.time()
        
        try:
            # Determine which tools should be triggered based on stimuli content and category
            selected_tools = await self._select_tools_for_stimuli(stimuli_request)
            
            # Prepare context for tool execution
            context = {
                "stimuli_content": stimuli_request.content,
                "stimuli_source": stimuli_request.source,
                "stimuli_priority": stimuli_request.priority.value,
                "stimuli_category": stimuli_request.category,
                "timestamp": stimuli_request.timestamp.isoformat(),
                "metadata": stimuli_request.metadata
            }
            
            # Execute selected tools
            tools_triggered = []
            agent_decision = None
            response_content = None
            
            if selected_tools:
                for tool_name in selected_tools:
                    try:
                        logging.info(f"🔧 [STIMULI_ORCHESTRATOR] Triggering tool: {tool_name}")
                        
                        # Use agent tool bridge to execute with proper context
                        tool_result = await self.agent_tool_bridge.execute_tool_with_context(
                            tool_name, 
                            context, 
                            stimuli_triggered=True,
                            vtuber_client=self.vtuber_client,
                            scb_client=self.scb_client
                        )
                        tools_triggered.append(tool_name)
                        
                        # Update statistics
                        if tool_name not in self.stats["tools_triggered_count"]:
                            self.stats["tools_triggered_count"][tool_name] = 0
                        self.stats["tools_triggered_count"][tool_name] += 1
                        
                        logging.info(f"✅ [STIMULI_ORCHESTRATOR] Tool {tool_name} executed successfully")
                        
                    except Exception as e:
                        logging.error(f"❌ [STIMULI_ORCHESTRATOR] Tool {tool_name} failed: {e}")
            
            # Generate agent decision based on stimuli and tools triggered
            agent_decision = await self._generate_agent_decision(stimuli_request, tools_triggered)
            
            processing_time = time.time() - start_time
            
            response = StimuliResponse(
                stimuli_id=stimuli_request.stimuli_id,
                success=True,
                processing_time=processing_time,
                tools_triggered=tools_triggered,
                agent_decision=agent_decision,
                response_content=response_content
            )
            
            logging.info(f"✅ [STIMULI_ORCHESTRATOR] Stimuli processed successfully in {processing_time:.3f}s")
            return response
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error processing stimuli: {e}")
            raise
        finally:
            self.current_stimuli = None
    
    async def _select_tools_for_stimuli(self, stimuli_request: StimuliRequest) -> List[str]:
        """Select appropriate tools based on stimuli content, category, and priority"""
        selected_tools = []
        
        # Check if stimuli_action_executor is available (should always be used for stimuli)
        available_tools = list(self.tool_registry.tools.keys())
        
        if "stimuli_action_executor" in available_tools:
            # Always use stimuli_action_executor for all stimuli processing
            selected_tools.append("stimuli_action_executor")
            logging.info(f"🎯 [STIMULI_ORCHESTRATOR] Selected unified tool: stimuli_action_executor")
        else:
            # Fallback: Log error and check for alternative tools
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] stimuli_action_executor not available! Available tools: {available_tools}")
            
            # Try to use goal_management_tools as a fallback for basic processing
            if "goal_management_tools" in available_tools:
                selected_tools.append("goal_management_tools")
                logging.warning(f"⚠️ [STIMULI_ORCHESTRATOR] Using fallback tool: goal_management_tools")
        
        logging.info(f"🎯 [STIMULI_ORCHESTRATOR] Selected tools: {selected_tools}")
        return selected_tools
    
    async def _generate_agent_decision(self, stimuli_request: StimuliRequest, tools_triggered: List[str]) -> str:
        """Generate agent decision summary for the stimuli response"""
        
        decision_parts = []
        
        if stimuli_request.priority in [StimuliPriority.EMERGENCY, StimuliPriority.CRITICAL]:
            decision_parts.append(f"High-priority {stimuli_request.priority.value} stimuli processed")
        
        if tools_triggered:
            decision_parts.append(f"Triggered tools: {', '.join(tools_triggered)}")
        
        if stimuli_request.category:
            decision_parts.append(f"Category: {stimuli_request.category}")
        
        if not decision_parts:
            decision_parts.append("Stimuli acknowledged and processed")
        
        return "; ".join(decision_parts)
    
    async def _start_autonomous_mode(self):
        """Start the autonomous loop in background"""
        if self.autonomous_state != AutonomousState.RUNNING:
            self.autonomous_task = asyncio.create_task(
                self._autonomous_loop_wrapper()
            )
            self.autonomous_state = AutonomousState.RUNNING
            logging.info("▶️ [STIMULI_ORCHESTRATOR] Autonomous mode started")
    
    async def _pause_autonomous_mode(self):
        """Pause autonomous operations"""
        if self.autonomous_state == AutonomousState.RUNNING:
            self.autonomous_state = AutonomousState.PAUSED
            logging.info("⏸️ [STIMULI_ORCHESTRATOR] Autonomous mode paused")
    
    async def _resume_autonomous_mode(self):
        """Resume autonomous operations"""
        if self.autonomous_state == AutonomousState.PAUSED:
            self.autonomous_state = AutonomousState.RUNNING
            logging.info("▶️ [STIMULI_ORCHESTRATOR] Autonomous mode resumed")
    
    async def _stop_autonomous_mode(self):
        """Stop autonomous operations completely"""
        if self.autonomous_task and not self.autonomous_task.done():
            self.autonomous_task.cancel()
            try:
                await self.autonomous_task
            except asyncio.CancelledError:
                pass
        
        self.autonomous_state = AutonomousState.STOPPED
        logging.info("🛑 [STIMULI_ORCHESTRATOR] Autonomous mode stopped")
    
    async def _autonomous_loop_wrapper(self):
        """Enhanced wrapper for the autonomous loop that integrates stimuli objectives"""
        iteration = 0
        last_restart_time = datetime.now().isoformat()
        
        while self.autonomous_state != AutonomousState.STOPPED:
            try:
                # Only run if not paused
                if self.autonomous_state == AutonomousState.RUNNING:
                    iteration += 1
                    start_time = time.time()
                    
                    # Check for new objectives from stimuli team (every 10 cycles)
                    if iteration % 10 == 1 and self.objective_bridge:
                        await self._integrate_stimuli_objectives()
                    
                    # Run the enhanced autonomous loop function with objectives
                    await self._run_enhanced_autonomous_cycle(iteration)
                    
                    # Update statistics
                    self.stats["autonomous_cycles"] += 1
                    self.stats["concurrent_operations"] += 1
                    
                    duration = time.time() - start_time
                    logging.info(f"🔄 [STIMULI_ORCHESTRATOR] Enhanced autonomous cycle #{iteration} completed in {duration:.2f}s")
                
                # Sleep for the loop interval, but check for state changes frequently
                sleep_time = 0
                while sleep_time < self.loop_interval and self.autonomous_state == AutonomousState.RUNNING:
                    await asyncio.sleep(1)
                    sleep_time += 1
                
            except asyncio.CancelledError:
                logging.info("🛑 [STIMULI_ORCHESTRATOR] Enhanced autonomous loop cancelled")
                break
            except Exception as e:
                logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error in enhanced autonomous loop: {e}")
                await asyncio.sleep(self.loop_interval)
    
    async def _integrate_stimuli_objectives(self):
        """Integrate objectives from stimuli team into main team context"""
        try:
            if not self.objective_bridge:
                return
                
            # Get current objectives for main team
            current_objectives = self.objective_bridge.get_current_objectives()
            
            if current_objectives:
                objectives_summary = self.objective_bridge.get_objectives_for_main_team_prompt()
                logging.info(f"🎯 [STIMULI_ORCHESTRATOR] Integrated {len(current_objectives)} objectives from stimuli team")
                
                # Store in shared context for main team access
                # This could be enhanced to directly modify the autonomous loop function's context
                
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error integrating stimuli objectives: {e}")
    
    async def _run_enhanced_autonomous_cycle(self, iteration: int):
        """Run enhanced autonomous cycle with stimuli objectives integration"""
        try:
            # Get objectives context if available
            objectives_context = ""
            if self.objective_bridge:
                objectives_context = self.objective_bridge.get_objectives_for_main_team_prompt()
            
            # Run the original autonomous loop function
            # Note: This could be enhanced to pass objectives_context to the function
            await self.autonomous_loop_function(iteration, self.scb_client, self.vtuber_client)
            
        except Exception as e:
            logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error in enhanced autonomous cycle: {e}")
            raise
    
    async def _stimuli_processing_loop(self):
        """Background loop for processing queued stimuli"""
        while True:
            try:
                # Process any queued stimuli (for future async processing)
                if not self.stimuli_queue.empty():
                    stimuli_data = await self.stimuli_queue.get()
                    await self.receive_stimuli(stimuli_data)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logging.error(f"❌ [STIMULI_ORCHESTRATOR] Error in stimuli processing loop: {e}")
                await asyncio.sleep(1)
    
    def _update_stats(self, response: StimuliResponse, processing_time: float):
        """Update orchestrator statistics"""
        self.stats["stimuli_processed"] += 1
        self.stats["last_stimuli_timestamp"] = datetime.now().isoformat()
        
        # Update average processing time
        current_avg = self.stats["avg_stimuli_processing_time"]
        total_processed = self.stats["stimuli_processed"]
        self.stats["avg_stimuli_processing_time"] = (
            (current_avg * (total_processed - 1) + processing_time) / total_processed
        )
    
    async def _initialize_consolidation(self):
        """Initialize consolidation components"""
        try:
            # Initialize capacity monitor
            s1_endpoint = os.getenv("S1_AVATAR_ENDPOINT", "http://neurosync:5001")
            self.capacity_monitor = initialize_capacity_monitor(
                s1_endpoint=s1_endpoint,
                s1_temp_dir="/tmp",
                s2_max_concurrent=1,
                monitoring_interval=2.0
            )
            
            # Start capacity monitoring
            await self.capacity_monitor.start_monitoring()
            
            # Initialize consolidator
            self.consolidator = initialize_consolidator(
                capacity_monitor=self.capacity_monitor,
                max_batch_size=3,
                batch_timeout=3.0,
                similarity_threshold=0.7
            )
            
            # Start consolidation processing
            await self.consolidator.start_processing()
            
            self.consolidation_enabled = True
            logging.info("✅ [STIMULI_ORCHESTRATOR] Consolidation system initialized")
            
        except Exception as e:
            logging.error("❌ [STIMULI_ORCHESTRATOR] Failed to initialize consolidation: %s", e)
            self.consolidation_enabled = False
    
    async def _shutdown_consolidation(self):
        """Shutdown consolidation components"""
        try:
            if self.consolidator:
                await self.consolidator.stop_processing()
            
            if self.capacity_monitor:
                await self.capacity_monitor.stop_monitoring()
            
            self.consolidation_enabled = False
            logging.info("✅ [STIMULI_ORCHESTRATOR] Consolidation system shutdown")
            
        except Exception as e:
            logging.error("❌ [STIMULI_ORCHESTRATOR] Error shutting down consolidation: %s", e)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status including consolidation architecture"""
        status = {
            "autonomous_state": self.autonomous_state.value,
            "current_stimuli": self.current_stimuli.stimuli_id if self.current_stimuli else None,
            "statistics": self.stats,
            "queue_size": self.stimuli_queue.qsize(),
            "stimuli_team": {
                "initialized": self.stimuli_team_initialized,
                "status": self.stimuli_team.get_team_status() if self.stimuli_team_initialized else None
            },
            "objective_bridge": {
                "initialized": bool(self.objective_bridge),
                "summary": self.objective_bridge.get_objectives_summary() if self.objective_bridge else None
            },
            "consolidation": {
                "enabled": self.consolidation_enabled,
                "capacity_monitor": self.capacity_monitor.get_combined_capacity() if self.capacity_monitor else None,
                "consolidator_status": self.consolidator.get_status() if self.consolidator else None
            },
            "architecture": {
                "main_team": "autonomous_operations",
                "stimuli_team": "dedicated_stimuli_analysis", 
                "action_executor": "unified_stimuli_action_executor",
                "consolidation_system": "intelligent_batching" if self.consolidation_enabled else "disabled",
                "capacity_monitoring": "active" if self.consolidation_enabled else "disabled",
                "concurrent_execution": True
            }
        }
        
        return status
    
    def get_stimuli_team_learning_summary(self) -> Dict[str, Any]:
        """Get learning summary for stimuli team (if teachable agents enabled)"""
        if self.stimuli_team_initialized and self.stimuli_team:
            return self.stimuli_team.get_learning_summary()
        else:
            return {"status": "not_available", "message": "Stimuli team not initialized or teachable agents disabled"}