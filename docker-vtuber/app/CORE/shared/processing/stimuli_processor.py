"""
Unified Stimuli Processing System
===============================

Consolidates all stimuli processing logic into a single, clean architecture.
Supports both S1/S2 routing and full AutoGen processing modes.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
import uuid

from ..config import get_config, SystemMode
from ..di import ServiceLifecycle, singleton
from ..errors import ErrorHandler, handle_errors, error_context, ErrorContext
from ..queue import QueueService, enqueue_stimuli


logger = logging.getLogger(__name__)


class ProcessingMode(str, Enum):
    """Stimuli processing modes"""
    S1_ONLY = "s1_only"  # Direct to avatar/speech
    S2_ONLY = "s2_only"  # Analysis teams only
    S1_AND_S2 = "s1_and_s2"  # Both systems
    AUTO = "auto"  # Intelligent routing


class TeamType(str, Enum):
    """Available team types"""
    TRADER = "trader"
    EDUCATOR = "educator"
    STREAMER = "streamer"
    GENERAL = "general"


@dataclass
class StimuliRequest:
    """Standardized stimuli request format"""
    id: str
    content: str
    source: str
    priority: str = "medium"
    processing_mode: ProcessingMode = ProcessingMode.AUTO
    team_preference: Optional[TeamType] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ProcessingResult:
    """Standardized processing result"""
    request_id: str
    success: bool
    processing_mode: ProcessingMode
    team_type: Optional[TeamType]
    response_content: Optional[str]
    analysis: Optional[Dict[str, Any]]
    processing_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StimuliRouter:
    """
    Intelligent stimuli routing based on content analysis and system state.
    Consolidates logic from GraphFlow emergency override and AutoGen team selection.
    """
    
    def __init__(self):
        self.s2_only_characters = {
            "dr._house_doctor_template",
            "trader",
            "financial_analyst"
        }
        
        # Content-based routing keywords
        self.routing_keywords = {
            ProcessingMode.S1_ONLY: [
                "avatar", "speak", "say", "voice", "immediate", "urgent_speech"
            ],
            ProcessingMode.S2_ONLY: [
                "analyze", "research", "calculate", "study", "investigate",
                "trading", "market", "financial", "education", "learning"
            ],
            ProcessingMode.S1_AND_S2: [
                "explain", "discuss", "tell", "show", "presentation"
            ]
        }
        
        # Team selection keywords
        self.team_keywords = {
            TeamType.TRADER: [
                "trading", "market", "stock", "crypto", "financial", "investment",
                "portfolio", "risk", "profit", "loss", "price", "chart"
            ],
            TeamType.EDUCATOR: [
                "teach", "learn", "education", "lesson", "curriculum", "assessment",
                "student", "knowledge", "study", "research", "academic"
            ],
            TeamType.STREAMER: [
                "stream", "content", "social", "community", "entertainment",
                "audience", "engagement", "trending", "viral", "broadcast"
            ]
        }
    
    @handle_errors(operation="route_stimuli", component="stimuli_router")
    async def route_stimuli(self, request: StimuliRequest) -> ProcessingMode:
        """
        Determine the appropriate processing mode for stimuli.
        
        Priority:
        1. Explicit processing mode in request
        2. Character-based routing (S2-only characters)
        3. Content analysis
        4. Default fallback
        """
        # Explicit mode specified
        if request.processing_mode != ProcessingMode.AUTO:
            return request.processing_mode
        
        # Character-based routing
        character = request.metadata.get("character_type")
        if character in self.s2_only_characters:
            return ProcessingMode.S2_ONLY
        
        # Content analysis
        content_lower = request.content.lower()
        
        # Check for S1-only keywords
        if any(keyword in content_lower for keyword in self.routing_keywords[ProcessingMode.S1_ONLY]):
            return ProcessingMode.S1_ONLY
        
        # Check for S2-only keywords
        if any(keyword in content_lower for keyword in self.routing_keywords[ProcessingMode.S2_ONLY]):
            return ProcessingMode.S2_ONLY
        
        # Check for both keywords
        if any(keyword in content_lower for keyword in self.routing_keywords[ProcessingMode.S1_AND_S2]):
            return ProcessingMode.S1_AND_S2
        
        # Priority-based fallback
        if request.priority in ["critical", "emergency"]:
            return ProcessingMode.S1_AND_S2
        elif request.priority == "high":
            return ProcessingMode.S2_ONLY
        else:
            return ProcessingMode.S1_AND_S2  # Default to both for maximum coverage
    
    @handle_errors(operation="select_team", component="stimuli_router")
    async def select_team(self, request: StimuliRequest) -> TeamType:
        """
        Select the appropriate team for S2 processing.
        """
        # Explicit team preference
        if request.team_preference:
            return request.team_preference
        
        # Character-based selection
        character = request.metadata.get("character_type")
        if character in ["dr._house_doctor_template", "trader"]:
            return TeamType.TRADER
        elif character in ["emma_teacher_template", "educator"]:
            return TeamType.EDUCATOR
        elif character in ["weatherman_template", "streamer"]:
            return TeamType.STREAMER
        
        # Content analysis
        content_lower = request.content.lower()
        
        # Calculate keyword scores for each team
        team_scores = {}
        for team, keywords in self.team_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            team_scores[team] = score
        
        # Return team with highest score, or general if tie
        if team_scores:
            best_team = max(team_scores, key=team_scores.get)
            if team_scores[best_team] > 0:
                return best_team
        
        return TeamType.GENERAL


class ProcessingStrategy(ABC):
    """Base class for processing strategies"""
    
    @abstractmethod
    async def process(self, request: StimuliRequest) -> ProcessingResult:
        """Process the stimuli request"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if strategy is healthy"""
        pass


class S1ProcessingStrategy(ProcessingStrategy):
    """S1 (Avatar/Speech) processing strategy"""
    
    def __init__(self):
        self.vtuber_client = None  # Will be injected
    
    @handle_errors(operation="s1_process", component="s1_strategy")
    async def process(self, request: StimuliRequest) -> ProcessingResult:
        """Process stimuli through S1 system"""
        start_time = time.time()
        
        try:
            # This would interface with the existing VTuber/Avatar system
            # For now, simulate processing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            result = ProcessingResult(
                request_id=request.id,
                success=True,
                processing_mode=ProcessingMode.S1_ONLY,
                team_type=None,
                response_content=f"Avatar response to: {request.content[:50]}...",
                analysis=None,
                processing_time=time.time() - start_time,
                metadata={"strategy": "s1", "simulated": True}
            )
            
            logger.info(f"S1 processing completed for request {request.id}")
            return result
            
        except Exception as e:
            return ProcessingResult(
                request_id=request.id,
                success=False,
                processing_mode=ProcessingMode.S1_ONLY,
                team_type=None,
                response_content=None,
                analysis=None,
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def health_check(self) -> bool:
        """Check S1 system health"""
        # Would check VTuber/Avatar system status
        return True


class S2ProcessingStrategy(ProcessingStrategy):
    """S2 (AutoGen Teams) processing strategy"""
    
    def __init__(self, queue_service: QueueService, router: StimuliRouter):
        self.queue_service = queue_service
        self.router = router
    
    @handle_errors(operation="s2_process", component="s2_strategy")
    async def process(self, request: StimuliRequest) -> ProcessingResult:
        """Process stimuli through S2 system"""
        start_time = time.time()
        
        try:
            # Determine team type
            team_type = await self.router.select_team(request)
            
            # Enqueue for team processing
            queue_name = f"s2_{team_type.value}"
            
            payload = {
                "stimuli_id": request.id,
                "content": request.content,
                "source": request.source,
                "priority": request.priority,
                "team_type": team_type.value,
                "metadata": request.metadata,
                "created_at": request.created_at.isoformat()
            }
            
            message_id = await self.queue_service.enqueue(
                queue_name=queue_name,
                payload=payload,
                metadata={"type": "s2_processing", "team": team_type.value}
            )
            
            result = ProcessingResult(
                request_id=request.id,
                success=True,
                processing_mode=ProcessingMode.S2_ONLY,
                team_type=team_type,
                response_content=None,  # Will be available later from queue processing
                analysis={"queued": True, "message_id": message_id},
                processing_time=time.time() - start_time,
                metadata={"strategy": "s2", "team": team_type.value, "queue": queue_name}
            )
            
            logger.info(f"S2 processing queued for request {request.id} with team {team_type.value}")
            return result
            
        except Exception as e:
            return ProcessingResult(
                request_id=request.id,
                success=False,
                processing_mode=ProcessingMode.S2_ONLY,
                team_type=None,
                response_content=None,
                analysis=None,
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def health_check(self) -> bool:
        """Check S2 system health"""
        return await self.queue_service.health_check()


@singleton()
class StimuliProcessor(ServiceLifecycle):
    """
    Unified stimuli processing service.
    
    Consolidates all stimuli processing logic from:
    - GraphFlow gateway routing
    - AutoGen orchestrators  
    - S2 queue consumers
    - Emergency override logic
    
    Features:
    - Intelligent routing
    - Multiple processing strategies
    - Unified error handling
    - Performance monitoring
    - Backward compatibility
    """
    
    def __init__(self, queue_service: QueueService = None, error_handler: ErrorHandler = None):
        self.queue_service = queue_service
        self.error_handler = error_handler
        self.router = StimuliRouter()
        
        # Processing strategies
        self.strategies: Dict[ProcessingMode, ProcessingStrategy] = {}
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "by_mode": {mode.value: 0 for mode in ProcessingMode},
            "by_team": {team.value: 0 for team in TeamType},
            "average_processing_time": 0.0
        }
        
        self._running = False
    
    async def start(self):
        """Start the stimuli processor"""
        if self._running:
            return
        
        # Initialize strategies
        self.strategies[ProcessingMode.S1_ONLY] = S1ProcessingStrategy()
        self.strategies[ProcessingMode.S2_ONLY] = S2ProcessingStrategy(
            self.queue_service, self.router
        )
        # S1_AND_S2 will use both strategies
        
        self._running = True
        logger.info("Stimuli processor started")
    
    async def stop(self):
        """Stop the stimuli processor"""
        self._running = False
        logger.info("Stimuli processor stopped")
    
    async def health_check(self) -> bool:
        """Check processor health"""
        if not self._running:
            return False
        
        # Check all strategies
        for strategy in self.strategies.values():
            if not await strategy.health_check():
                return False
        
        return True
    
    @handle_errors(operation="process_stimuli", component="stimuli_processor")
    async def process_stimuli(
        self,
        content: str,
        source: str,
        priority: str = "medium",
        processing_mode: ProcessingMode = ProcessingMode.AUTO,
        team_preference: Optional[TeamType] = None,
        metadata: Dict[str, Any] = None
    ) -> Union[ProcessingResult, List[ProcessingResult]]:
        """
        Process stimuli with unified logic.
        
        Args:
            content: Stimuli content
            source: Source of stimuli
            priority: Priority level
            processing_mode: How to process (auto-detected if AUTO)
            team_preference: Preferred team for S2 processing
            metadata: Additional metadata
        
        Returns:
            ProcessingResult or list of results for S1_AND_S2 mode
        """
        if not self._running:
            raise RuntimeError("Stimuli processor not started")
        
        # Create standardized request
        request = StimuliRequest(
            id=str(uuid.uuid4()),
            content=content,
            source=source,
            priority=priority,
            processing_mode=processing_mode,
            team_preference=team_preference,
            metadata=metadata or {}
        )
        
        # Determine actual processing mode
        actual_mode = await self.router.route_stimuli(request)
        
        async with error_context(
            operation="process_stimuli",
            component="stimuli_processor",
            metadata={"request_id": request.id, "mode": actual_mode.value}
        ):
            if actual_mode == ProcessingMode.S1_AND_S2:
                # Process with both strategies
                results = await asyncio.gather(
                    self._process_with_strategy(request, ProcessingMode.S1_ONLY),
                    self._process_with_strategy(request, ProcessingMode.S2_ONLY),
                    return_exceptions=True
                )
                
                # Filter out exceptions and return valid results
                valid_results = [r for r in results if isinstance(r, ProcessingResult)]
                
                if valid_results:
                    self._update_stats(valid_results)
                    return valid_results
                else:
                    # Both failed, create error result
                    return ProcessingResult(
                        request_id=request.id,
                        success=False,
                        processing_mode=actual_mode,
                        team_type=None,
                        response_content=None,
                        analysis=None,
                        processing_time=0.0,
                        error_message="Both S1 and S2 processing failed"
                    )
            else:
                # Process with single strategy
                result = await self._process_with_strategy(request, actual_mode)
                self._update_stats([result])
                return result
    
    async def _process_with_strategy(
        self,
        request: StimuliRequest,
        mode: ProcessingMode
    ) -> ProcessingResult:
        """Process request with specific strategy"""
        if mode not in self.strategies:
            raise ValueError(f"No strategy available for mode: {mode}")
        
        strategy = self.strategies[mode]
        
        # Update request mode for strategy
        request.processing_mode = mode
        
        return await strategy.process(request)
    
    def _update_stats(self, results: List[ProcessingResult]):
        """Update processing statistics"""
        for result in results:
            self.stats["total_processed"] += 1
            
            if result.success:
                self.stats["successful"] += 1
            else:
                self.stats["failed"] += 1
            
            self.stats["by_mode"][result.processing_mode.value] += 1
            
            if result.team_type:
                self.stats["by_team"][result.team_type.value] += 1
            
            # Update average processing time
            total = self.stats["total_processed"]
            current_avg = self.stats["average_processing_time"]
            self.stats["average_processing_time"] = (
                (current_avg * (total - 1) + result.processing_time) / total
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()
    
    # Backward compatibility methods
    async def process_s2_only(
        self,
        content: str,
        source: str,
        character_type: str = None
    ) -> ProcessingResult:
        """Backward compatibility for S2-only processing"""
        metadata = {"character_type": character_type} if character_type else {}
        
        result = await self.process_stimuli(
            content=content,
            source=source,
            processing_mode=ProcessingMode.S2_ONLY,
            metadata=metadata
        )
        
        return result if isinstance(result, ProcessingResult) else result[0]
    
    async def process_graphflow_stimuli(
        self,
        stimuli_data: Dict[str, Any]
    ) -> Union[ProcessingResult, List[ProcessingResult]]:
        """Backward compatibility for GraphFlow stimuli format"""
        return await self.process_stimuli(
            content=stimuli_data.get("content", ""),
            source=stimuli_data.get("source", "graphflow"),
            priority=stimuli_data.get("priority", "medium"),
            metadata=stimuli_data.get("metadata", {})
        )


# Convenience functions for backward compatibility
async def process_stimuli_unified(
    content: str,
    source: str,
    **kwargs
) -> Union[ProcessingResult, List[ProcessingResult]]:
    """Unified stimuli processing function"""
    from ..di import get_container
    
    processor = get_container().get(StimuliProcessor)
    return await processor.process_stimuli(content, source, **kwargs)


async def enqueue_for_s2_team(
    content: str,
    team_type: str,
    metadata: Dict[str, Any] = None
) -> str:
    """Enqueue stimuli for specific S2 team (backward compatibility)"""
    team_enum = TeamType(team_type) if team_type in [t.value for t in TeamType] else TeamType.GENERAL
    
    from ..di import get_container
    processor = get_container().get(StimuliProcessor)
    
    result = await processor.process_stimuli(
        content=content,
        source="legacy_api",
        processing_mode=ProcessingMode.S2_ONLY,
        team_preference=team_enum,
        metadata=metadata or {}
    )
    
    if isinstance(result, ProcessingResult):
        return result.request_id
    else:
        return result[0].request_id