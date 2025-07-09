"""
SCB to Cognee Bridge Service

This service transforms SCB (Shared Context Blackboard) data into semantic knowledge graphs
using Cognee. It solves the repetition problem by only storing meaningful changes and
creating semantic relationships between different contexts.

Key Features:
1. Monitors SCB state changes and extracts only meaningful updates
2. Transforms flat SCB data into semantic chunks with relationships
3. Maintains multiple semantic contexts (general, S2→S1, S1→S2, tools, etc.)
4. Enables graph visualization and export capabilities
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..clients.scb_client import SCBClient
from .cognee_service import CogneeService
from .cognee_direct_service import CogneeDirectService, get_cognee_direct_service


class SemanticContext(Enum):
    """Different semantic contexts for organizing knowledge"""
    GENERAL = "general_context"              # General system coordination
    S2_TO_S1 = "s2_to_s1_messages"         # S2 (AutoGen) → S1 (Avatar) messages
    S1_TO_S2 = "s1_to_s2_feedback"         # S1 (Avatar) → S2 (AutoGen) feedback
    TOOL_EXECUTION = "tool_executions"      # Tool execution history with relationships
    STIMULI_PROCESSING = "stimuli_context"  # Stimuli processing and decisions
    AGENT_STATE = "agent_state"            # Agent state changes
    TRADING_FINANCE = "trading_finance"     # S2 trading and financial data
    SYSTEM_EVENTS = "system_events"        # System-level events and errors


@dataclass
class SemanticEntry:
    """Represents a semantic entry to be added to Cognee"""
    context: SemanticContext
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "scb_bridge"
    content_hash: Optional[str] = None


class SCBCogneeBridge:
    """
    Bridge service that transforms SCB data into Cognee semantic knowledge graphs
    """
    
    def __init__(self, 
                 scb_client: Optional[SCBClient] = None,
                 cognee_service: Optional[CogneeService] = None,
                 use_direct_cognee: bool = True):
        """
        Initialize the bridge service
        
        Args:
            scb_client: Optional SCB client instance
            cognee_service: Optional Cognee service instance
            use_direct_cognee: Whether to use CogneeDirectService (with Ollama)
        """
        self.scb_client = scb_client
        self.cognee_service = cognee_service
        self.use_direct_cognee = use_direct_cognee
        self.cognee_direct = None
        
        # Track previous states to detect changes
        self.previous_states: Dict[str, str] = {}
        self.processed_hashes: Set[str] = set()
        
        # Context-specific buffers for batching
        self.context_buffers: Dict[SemanticContext, List[SemanticEntry]] = {
            context: [] for context in SemanticContext
        }
        
        # Configuration
        self.batch_size = 5
        self.batch_timeout = 3.0  # seconds
        self.enable_deduplication = True
        
        # Processing state
        self.processing_active = False
        self.processor_task: Optional[asyncio.Task] = None
        
        logging.info("🌉 [SCB_COGNEE_BRIDGE] Initialized bridge service")
    
    async def initialize(self) -> bool:
        """Initialize the bridge service and its dependencies"""
        try:
            # Initialize Cognee service
            if self.use_direct_cognee:
                self.cognee_direct = await get_cognee_direct_service()
                if not self.cognee_direct:
                    logging.error("❌ [SCB_COGNEE_BRIDGE] Failed to initialize CogneeDirectService")
                    return False
                logging.info("✅ [SCB_COGNEE_BRIDGE] Using CogneeDirectService with Ollama")
            elif self.cognee_service:
                initialized = await self.cognee_service.initialize()
                if not initialized:
                    logging.error("❌ [SCB_COGNEE_BRIDGE] Failed to initialize CogneeService")
                    return False
                logging.info("✅ [SCB_COGNEE_BRIDGE] Using CogneeService")
            else:
                logging.error("❌ [SCB_COGNEE_BRIDGE] No Cognee service available")
                return False
            
            # Start processing loop
            self.processing_active = True
            self.processor_task = asyncio.create_task(self._processing_loop())
            
            logging.info("🚀 [SCB_COGNEE_BRIDGE] Bridge service initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [SCB_COGNEE_BRIDGE] Initialization error: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the bridge service"""
        self.processing_active = False
        
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining buffered entries
        await self._flush_all_buffers()
        
        logging.info("🛑 [SCB_COGNEE_BRIDGE] Bridge service shutdown")
    
    async def transform_scb_state(self, scb_state: Dict[str, Any]) -> List[SemanticEntry]:
        """
        Transform SCB state into semantic entries
        
        Args:
            scb_state: Raw SCB state data
            
        Returns:
            List of semantic entries to be added to Cognee
        """
        entries = []
        
        try:
            # Extract relevant fields and determine context
            tool_used = scb_state.get("tool_used", "")
            success = scb_state.get("success", False)
            timestamp = scb_state.get("timestamp", datetime.now().timestamp())
            
            # Tool execution context
            if tool_used and tool_used != "unknown":
                tool_entry = await self._create_tool_execution_entry(scb_state)
                if tool_entry:
                    entries.append(tool_entry)
            
            # Agent communication context
            if "agent_responses" in scb_state:
                comm_entries = await self._create_communication_entries(scb_state)
                entries.extend(comm_entries)
            
            # Stimuli processing context
            if "stimuli_id" in scb_state or "stimuli" in scb_state.get("metadata", {}):
                stimuli_entry = await self._create_stimuli_entry(scb_state)
                if stimuli_entry:
                    entries.append(stimuli_entry)
            
            # System events (errors, warnings)
            if not success or "error" in scb_state:
                event_entry = await self._create_system_event_entry(scb_state)
                if event_entry:
                    entries.append(event_entry)
            
            # Trading/finance context
            if any(keyword in str(scb_state).lower() for keyword in ["trading", "finance", "portfolio", "market"]):
                finance_entry = await self._create_finance_entry(scb_state)
                if finance_entry:
                    entries.append(finance_entry)
            
        except Exception as e:
            logging.error(f"❌ [SCB_COGNEE_BRIDGE] Error transforming SCB state: {e}")
        
        return entries
    
    async def _create_tool_execution_entry(self, scb_state: Dict[str, Any]) -> Optional[SemanticEntry]:
        """Create semantic entry for tool execution"""
        tool_name = scb_state.get("tool_used", "")
        success = scb_state.get("success", False)
        
        # Generate content that describes the tool execution
        content = f"Tool '{tool_name}' was executed with {'success' if success else 'failure'}"
        
        # Add details if available
        if "tool_result" in scb_state:
            content += f". Result: {str(scb_state['tool_result'])[:200]}"
        
        # Create relationships
        relationships = []
        if "triggered_by" in scb_state:
            relationships.append({
                "type": "triggered_by",
                "target": scb_state["triggered_by"],
                "context": "tool_execution"
            })
        
        if "stimuli_id" in scb_state:
            relationships.append({
                "type": "responds_to",
                "target": f"stimuli_{scb_state['stimuli_id']}",
                "context": "stimuli_response"
            })
        
        return SemanticEntry(
            context=SemanticContext.TOOL_EXECUTION,
            content=content,
            metadata={
                "tool_name": tool_name,
                "success": success,
                "timestamp": scb_state.get("timestamp", datetime.now().timestamp())
            },
            relationships=relationships,
            source="tool_executor"
        )
    
    async def _create_communication_entries(self, scb_state: Dict[str, Any]) -> List[SemanticEntry]:
        """Create semantic entries for agent communications"""
        entries = []
        agent_responses = scb_state.get("agent_responses", {})
        
        for agent_name, response in agent_responses.items():
            # Determine communication direction
            if "s2" in agent_name.lower() or "autogen" in agent_name.lower():
                context = SemanticContext.S2_TO_S1
            elif "s1" in agent_name.lower() or "avatar" in agent_name.lower():
                context = SemanticContext.S1_TO_S2
            else:
                context = SemanticContext.GENERAL
            
            # Extract meaningful content
            if isinstance(response, dict):
                content = response.get("message", str(response))
            else:
                content = str(response)
            
            # Skip empty or repetitive content
            if not content or len(content) < 10:
                continue
            
            entry = SemanticEntry(
                context=context,
                content=f"{agent_name}: {content}",
                metadata={
                    "agent": agent_name,
                    "response_type": "communication",
                    "iteration": scb_state.get("iteration", 0)
                },
                relationships=[{
                    "type": "said_by",
                    "target": agent_name,
                    "context": "agent_communication"
                }],
                source=agent_name
            )
            
            entries.append(entry)
        
        return entries
    
    async def _create_stimuli_entry(self, scb_state: Dict[str, Any]) -> Optional[SemanticEntry]:
        """Create semantic entry for stimuli processing"""
        stimuli_id = scb_state.get("stimuli_id") or scb_state.get("metadata", {}).get("stimuli", {}).get("id")
        
        if not stimuli_id:
            return None
        
        content = f"Processed stimuli {stimuli_id}"
        
        # Add stimuli details
        if "stimuli_type" in scb_state:
            content += f" of type '{scb_state['stimuli_type']}'"
        
        if "decision" in scb_state:
            content += f". Decision: {scb_state['decision']}"
        
        return SemanticEntry(
            context=SemanticContext.STIMULI_PROCESSING,
            content=content,
            metadata={
                "stimuli_id": stimuli_id,
                "processing_time": scb_state.get("processing_time", 0),
                "priority": scb_state.get("priority", "medium")
            },
            relationships=[{
                "type": "processes",
                "target": f"stimuli_{stimuli_id}",
                "context": "stimuli_processing"
            }],
            source="stimuli_processor"
        )
    
    async def _create_system_event_entry(self, scb_state: Dict[str, Any]) -> Optional[SemanticEntry]:
        """Create semantic entry for system events (errors, warnings)"""
        error = scb_state.get("error", "")
        
        if not error and scb_state.get("success", True):
            return None
        
        content = f"System event: {error if error else 'Operation failed'}"
        
        return SemanticEntry(
            context=SemanticContext.SYSTEM_EVENTS,
            content=content,
            metadata={
                "event_type": "error" if error else "failure",
                "severity": "high" if "critical" in str(error).lower() else "medium",
                "timestamp": scb_state.get("timestamp", datetime.now().timestamp())
            },
            source="system_monitor"
        )
    
    async def _create_finance_entry(self, scb_state: Dict[str, Any]) -> Optional[SemanticEntry]:
        """Create semantic entry for trading/finance data"""
        # Extract finance-related content
        content_parts = []
        
        if "portfolio" in scb_state:
            content_parts.append(f"Portfolio update: {scb_state['portfolio']}")
        
        if "trade" in scb_state:
            content_parts.append(f"Trade executed: {scb_state['trade']}")
        
        if "market_analysis" in scb_state:
            content_parts.append(f"Market analysis: {scb_state['market_analysis']}")
        
        if not content_parts:
            # Try to extract from general content
            for key, value in scb_state.items():
                if any(keyword in str(key).lower() for keyword in ["trading", "finance", "market"]):
                    content_parts.append(f"{key}: {value}")
        
        if not content_parts:
            return None
        
        return SemanticEntry(
            context=SemanticContext.TRADING_FINANCE,
            content=" | ".join(content_parts),
            metadata={
                "domain": "finance",
                "timestamp": scb_state.get("timestamp", datetime.now().timestamp())
            },
            source="finance_tracker"
        )
    
    async def add_semantic_entry(self, entry: SemanticEntry):
        """Add a semantic entry to the appropriate buffer"""
        # Deduplicate if enabled
        if self.enable_deduplication:
            content_hash = hashlib.md5(entry.content.encode()).hexdigest()
            if content_hash in self.processed_hashes:
                logging.debug(f"🔁 [SCB_COGNEE_BRIDGE] Skipping duplicate entry: {content_hash}")
                return
            
            entry.content_hash = content_hash
            self.processed_hashes.add(content_hash)
        
        # Add to context buffer
        self.context_buffers[entry.context].append(entry)
        
        # Check if we should flush this buffer
        if len(self.context_buffers[entry.context]) >= self.batch_size:
            await self._flush_buffer(entry.context)
    
    async def _processing_loop(self):
        """Main processing loop that flushes buffers periodically"""
        while self.processing_active:
            try:
                # Wait for batch timeout
                await asyncio.sleep(self.batch_timeout)
                
                # Flush all non-empty buffers
                await self._flush_all_buffers()
                
            except Exception as e:
                logging.error(f"❌ [SCB_COGNEE_BRIDGE] Error in processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _flush_buffer(self, context: SemanticContext):
        """Flush a specific context buffer to Cognee"""
        entries = self.context_buffers[context]
        if not entries:
            return
        
        try:
            # Prepare data for Cognee
            cognee_data = []
            
            for entry in entries:
                # Format entry for Cognee with semantic metadata
                formatted_content = f"[{context.value}] {entry.content}"
                
                # Add relationships as part of the content
                if entry.relationships:
                    rel_strings = [f"{r['type']}:{r['target']}" for r in entry.relationships]
                    formatted_content += f" | Relations: {', '.join(rel_strings)}"
                
                # Add metadata
                if entry.metadata:
                    formatted_content += f" | Metadata: {json.dumps(entry.metadata)}"
                
                cognee_data.append(formatted_content)
            
            # Send to Cognee
            if self.cognee_direct:
                result = await self.cognee_direct.add_data(cognee_data)
                logging.info(f"📤 [SCB_COGNEE_BRIDGE] Sent {len(entries)} entries to Cognee Direct for context {context.value}")
            elif self.cognee_service:
                result = await self.cognee_service.add_data(cognee_data)
                logging.info(f"📤 [SCB_COGNEE_BRIDGE] Sent {len(entries)} entries to Cognee for context {context.value}")
            else:
                logging.warning("⚠️ [SCB_COGNEE_BRIDGE] No Cognee service available")
                return
            
            # Clear the buffer
            self.context_buffers[context].clear()
            
            # Optionally trigger cognify for important contexts
            if context in [SemanticContext.S2_TO_S1, SemanticContext.TOOL_EXECUTION]:
                asyncio.create_task(self._trigger_cognify())
            
        except Exception as e:
            logging.error(f"❌ [SCB_COGNEE_BRIDGE] Error flushing buffer for {context.value}: {e}")
    
    async def _flush_all_buffers(self):
        """Flush all context buffers"""
        for context in SemanticContext:
            if self.context_buffers[context]:
                await self._flush_buffer(context)
    
    async def _trigger_cognify(self):
        """Trigger Cognee processing to create knowledge graph relationships"""
        try:
            if self.cognee_direct:
                await self.cognee_direct.cognify()
                logging.info("🧩 [SCB_COGNEE_BRIDGE] Triggered Cognee Direct processing")
            elif self.cognee_service:
                await self.cognee_service.cognify()
                logging.info("🧩 [SCB_COGNEE_BRIDGE] Triggered Cognee processing")
        except Exception as e:
            logging.warning(f"⚠️ [SCB_COGNEE_BRIDGE] Cognify failed (non-critical): {e}")
    
    async def search_semantic_context(self, query: str, context: Optional[SemanticContext] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the semantic knowledge graph
        
        Args:
            query: Search query
            context: Optional specific context to search within
            limit: Maximum results
            
        Returns:
            List of search results
        """
        # Add context filter to query if specified
        if context:
            query = f"[{context.value}] {query}"
        
        try:
            if self.cognee_direct:
                results = await self.cognee_direct.search(query, limit=limit)
            elif self.cognee_service:
                results = await self.cognee_service.search(query, search_type="CHUNKS", limit=limit)
            else:
                logging.warning("⚠️ [SCB_COGNEE_BRIDGE] No Cognee service available for search")
                return []
            
            logging.info(f"🔍 [SCB_COGNEE_BRIDGE] Found {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logging.error(f"❌ [SCB_COGNEE_BRIDGE] Search error: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get bridge service status"""
        buffer_sizes = {context.value: len(entries) for context, entries in self.context_buffers.items()}
        
        return {
            "service": "scb_cognee_bridge",
            "processing_active": self.processing_active,
            "cognee_service": "direct" if self.cognee_direct else "http" if self.cognee_service else "none",
            "buffer_sizes": buffer_sizes,
            "total_buffered": sum(buffer_sizes.values()),
            "processed_hashes": len(self.processed_hashes),
            "deduplication_enabled": self.enable_deduplication
        }


# Global bridge instance
_global_bridge: Optional[SCBCogneeBridge] = None


async def get_scb_cognee_bridge() -> Optional[SCBCogneeBridge]:
    """Get or create the global bridge instance"""
    global _global_bridge
    
    if _global_bridge is None:
        _global_bridge = SCBCogneeBridge(use_direct_cognee=True)
        initialized = await _global_bridge.initialize()
        if not initialized:
            _global_bridge = None
    
    return _global_bridge


async def transform_and_store_scb_state(scb_state: Dict[str, Any]) -> bool:
    """
    Convenience function to transform and store SCB state
    
    Args:
        scb_state: SCB state to transform and store
        
    Returns:
        bool: Success status
    """
    bridge = await get_scb_cognee_bridge()
    if not bridge:
        return False
    
    try:
        # Transform the state
        entries = await bridge.transform_scb_state(scb_state)
        
        # Add entries to buffers
        for entry in entries:
            await bridge.add_semantic_entry(entry)
        
        return True
        
    except Exception as e:
        logging.error(f"❌ [SCB_COGNEE_BRIDGE] Error transforming state: {e}")
        return False