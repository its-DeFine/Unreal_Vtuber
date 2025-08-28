"""
Orchestrator Agent - AutoGen-based routing intelligence
Version 1.0.1 - Auto-update test successful
"""
import json
import time
from typing import Dict, Any, Optional
import structlog
from autogen import AssistantAgent
import ollama

from .models import StimulusRequest, RoutingDecision
from .api_registry import APIRegistry

logger = structlog.get_logger()


class OrchestratorAgent:
    """
    Lightweight orchestrator using Ollama for fast routing decisions
    """
    
    def __init__(self, api_registry: APIRegistry):
        self.api_registry = api_registry
        self.ollama_client = None
        self.routing_prompt = self._build_routing_prompt()
        
    async def initialize(self):
        """Initialize Ollama connection"""
        try:
            self.ollama_client = ollama.AsyncClient()
            # Test connection
            await self.ollama_client.list()
            logger.info("Ollama connection established")
            logger.info("🚀 Running version 1.0.1 - Auto-update successful!")
        except Exception as e:
            logger.error("Failed to connect to Ollama", error=str(e))
            raise
    
    def _build_routing_prompt(self) -> str:
        """Build the system prompt with API registry info"""
        api_info = json.dumps(self.api_registry.get_capabilities(), indent=2)
        
        return f"""You are the VTuber System Orchestrator. Route incoming stimuli to the appropriate system.

Available Systems:
{api_info}

Routing Rules:
1. Use S1 for: real-time responses, quick answers, streaming, immediate reactions
2. Use S2 for: complex analysis, multi-step reasoning, deep research, planning
3. Use BOTH for: questions needing immediate response + deep analysis

Output Format (JSON only):
{{
    "system": "s1" | "s2" | "both",
    "config": {{
        "persona": "trader|educator|streamer",  // for s1
        "team": "trader|educator|streamer",      // for s2
        "coordination": "s1_then_s2|parallel"    // for both
    }},
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Respond with ONLY valid JSON. Be fast and decisive."""

    def _is_stop_command(self, text: str) -> bool:
        """Check if text is a stop command"""
        text_lower = text.lower()
        stop_phrases = [
            "stop system 2",
            "stop s2",
            "stop the system 2",
            "stop system two",
            "stop conversation",
            "stop processing",
            "stop talking",
            "stop the conversation",
            "stop the processing",
            "halt system 2",
            "halt s2",
            "interrupt system 2",
            "interrupt s2",
            "cancel system 2",
            "cancel s2"
        ]
        
        return any(phrase in text_lower for phrase in stop_phrases)
    
    def _quick_route_heuristic(self, text: str) -> Optional[RoutingDecision]:
        """Apply fast heuristics for common routing patterns"""
        text_lower = text.lower()
        
        # Check for explicit S1 initialization commands
        init_patterns = ["initialize", "init", "switch to", "use", "activate", "start"]
        s1_indicators = ["system 1", "system one", "s1", "persona"]
        
        if any(pattern in text_lower for pattern in init_patterns):
            if any(indicator in text_lower for indicator in s1_indicators):
                # Detect which persona is requested
                persona = "streamer"  # default
                if "trader" in text_lower:
                    persona = "trader"
                elif "educator" in text_lower or "teacher" in text_lower:
                    persona = "educator"
                elif "streamer" in text_lower:
                    persona = "streamer"
                
                return RoutingDecision(
                    stimulus_id="",
                    stimulus_text=text,
                    system="s1",
                    config={"persona": persona},
                    confidence=1.0,
                    reasoning=f"Explicit S1 initialization request for {persona}",
                    latency_ms=0
                )
        
        # Simple greetings/quick responses -> S1
        simple_patterns = [
            "hello", "hi", "hey", "how are you", "good morning", "good evening",
            "what time", "what's the weather", "thank you", "thanks", "bye"
        ]
        if any(pattern in text_lower for pattern in simple_patterns) or len(text.split()) < 5:
            return RoutingDecision(
                stimulus_id="",  # Will be filled by caller
                stimulus_text=text,
                system="s1",
                config={"persona": "streamer"},
                confidence=0.95,
                reasoning="Simple query - fast S1 response",
                latency_ms=0  # Will be filled by caller
            )
        
        # Complex analysis keywords -> S2
        complex_patterns = [
            "analyze", "explain in detail", "comprehensive", "create a plan",
            "compare and contrast", "deep dive", "research", "multiple steps"
        ]
        if any(pattern in text_lower for pattern in complex_patterns) or len(text.split()) > 30:
            return RoutingDecision(
                stimulus_id="",
                stimulus_text=text,
                system="s2",
                config={"team": "educator"},
                confidence=0.95,
                reasoning="Complex query requiring deep analysis",
                latency_ms=0
            )
        
        return None  # No heuristic match, use LLM
    
    async def route(self, request: StimulusRequest) -> RoutingDecision:
        """
        Make routing decision for incoming stimulus
        Target: < 10ms latency
        """
        start_time = time.time()
        
        # Check for stop commands first (immediate processing)
        if self._is_stop_command(request.text):
            logger.info("Stop command detected", stimulus_id=request.stimulus_id)
            return RoutingDecision(
                stimulus_id=request.stimulus_id,
                stimulus_text=request.text,
                system="stop",
                config={"action": "stop_s2_processing"},
                confidence=1.0,
                reasoning="Stop command detected - immediate system action required",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        
        # Try quick heuristic routing first
        heuristic_decision = self._quick_route_heuristic(request.text)
        if heuristic_decision:
            heuristic_decision.stimulus_id = request.stimulus_id
            heuristic_decision.latency_ms = int((time.time() - start_time) * 1000)
            logger.info("Used heuristic routing", 
                       stimulus_id=request.stimulus_id,
                       system=heuristic_decision.system,
                       latency_ms=heuristic_decision.latency_ms)
            return heuristic_decision
        
        try:
            # Fall back to LLM for complex routing decisions
            response = await self.ollama_client.chat(
                model='llama3.1:8b',
                messages=[
                    {
                        'role': 'system',
                        'content': self.routing_prompt
                    },
                    {
                        'role': 'user',
                        'content': f"Route this stimulus: {request.text}"
                    }
                ],
                options={
                    'temperature': 0.1,  # Very low for consistency
                    'num_predict': 200,  # Limit tokens for speed
                }
            )
            
            # Parse response
            decision_json = json.loads(response['message']['content'])
            
            # Build routing decision
            decision = RoutingDecision(
                stimulus_id=request.stimulus_id,
                stimulus_text=request.text,
                system=decision_json['system'],
                config=decision_json['config'],
                confidence=decision_json.get('confidence', 0.9),
                reasoning=decision_json.get('reasoning', ''),
                latency_ms=int((time.time() - start_time) * 1000)
            )
            
            # Log if over target latency
            if decision.latency_ms > 10:
                logger.warning("Routing latency exceeded target",
                             latency_ms=decision.latency_ms,
                             stimulus_id=request.stimulus_id)
            
            return decision
            
        except Exception as e:
            logger.error("Routing decision failed", 
                        error=str(e),
                        stimulus_id=request.stimulus_id)
            # Fallback to S1 on error
            return RoutingDecision(
                stimulus_id=request.stimulus_id,
                stimulus_text=request.text,
                system="s1",
                config={"persona": "streamer"},
                confidence=0.5,
                reasoning="Fallback due to routing error",
                latency_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute_routing(self, decision: RoutingDecision) -> Dict[str, Any]:
        """
        Execute the routing decision by calling appropriate APIs
        """
        results = {}
        
        if decision.system == "s1":
            results['s1'] = await self._call_s1(decision)
            
        elif decision.system == "s2":
            results['s2'] = await self._call_s2(decision)
            
        elif decision.system == "stop":
            results['stop'] = await self._execute_stop_command(decision)
            
        elif decision.system == "both":
            coordination = decision.config.get('coordination', 's1_then_s2')
            
            if coordination == "parallel":
                # Call both in parallel
                import asyncio
                s1_task = asyncio.create_task(self._call_s1(decision))
                s2_task = asyncio.create_task(self._call_s2(decision))
                results['s1'], results['s2'] = await asyncio.gather(s1_task, s2_task)
            else:
                # S1 first, then S2
                results['s1'] = await self._call_s1(decision)
                results['s2'] = await self._call_s2(decision)
        
        return results
    
    async def _call_s1(self, decision: RoutingDecision) -> Dict[str, Any]:
        """Call System 1 API"""
        endpoint = self.api_registry.apis['system1']['endpoint']
        persona = decision.config.get('persona', 'streamer')
        
        # Map persona types to actual character IDs
        character_mapping = {
            'trader': 'sophia_trader_template',
            'educator': 'diana_educator_template', 
            'streamer': 'luna_streamer_template'
        }
        character_id = character_mapping.get(persona, 'luna_streamer_template')
        
        logger.info("Forwarding to S1", 
                   stimulus_id=decision.stimulus_id,
                   persona=persona,
                   character_id=character_id)
        
        # Make API call
        import httpx
        async with httpx.AsyncClient() as client:
            # First, stop any ongoing speech to ensure clean transition
            try:
                stop_response = await client.post(
                    f"{endpoint}/speech/control",
                    json={"action": "stop"},
                    timeout=2.0
                )
                if stop_response.status_code == 200:
                    stop_result = stop_response.json()
                    if stop_result.get('streams_stopped', 0) > 0:
                        logger.info("Stopped ongoing speech before routing",
                                   streams_stopped=stop_result.get('streams_stopped'))
            except Exception as e:
                logger.warning("Could not stop speech", error=str(e))
            
            # Switch to the appropriate character
            try:
                char_response = await client.post(
                    f"{endpoint}/character/activate",
                    json={"character_id": character_id},
                    timeout=5.0
                )
                if char_response.status_code == 200:
                    logger.info(f"Activated character: {character_id}")
                else:
                    logger.warning(f"Failed to activate character: {char_response.status_code}")
            except Exception as e:
                logger.warning(f"Could not activate character: {e}")
            
            # Now send the new stimulus with error handling
            try:
                response = await client.post(
                    f"{endpoint}/process_text",
                    json={
                        "text": decision.stimulus_text,
                        "autonomous_context": f"Routed by orchestrator with persona: {persona}",
                        "direct_speech": True,
                        "interaction_mode": "interrupt"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Handle non-200 responses gracefully
                    error_text = await response.text()
                    logger.error("S1 returned error", 
                               status_code=response.status_code,
                               error=error_text)
                    return {
                        "success": False,
                        "error": f"S1 returned {response.status_code}: {error_text}",
                        "status_code": response.status_code
                    }
                    
            except httpx.TimeoutException:
                logger.error("S1 request timed out")
                return {
                    "success": False,
                    "error": "S1 request timed out after 10 seconds",
                    "timeout": True
                }
            except Exception as e:
                logger.error("S1 request failed", error=str(e))
                return {
                    "success": False,
                    "error": f"S1 request failed: {str(e)}",
                    "exception": str(type(e).__name__)
                }
    
    async def _call_s2(self, decision: RoutingDecision) -> Dict[str, Any]:
        """Call System 2 API"""
        endpoint = self.api_registry.apis['system2']['endpoint']
        team = decision.config.get('team', 'streamer')
        
        # Map team types to actual character IDs
        character_mapping = {
            'trader': 'sophia_trader_template',
            'educator': 'diana_educator_template', 
            'streamer': 'luna_streamer_template'
        }
        character_id = character_mapping.get(team, 'luna_streamer_template')
        
        logger.info("Forwarding to S2", 
                   stimulus_id=decision.stimulus_id,
                   team=team,
                   character_id=character_id)
        
        # Make API call
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{endpoint}/api/stimuli/receive",
                    json={
                        "stimuli_id": decision.stimulus_id,
                        "content": decision.stimulus_text,
                        "source": "orchestrator",
                        "priority": "high",
                        "category": team,
                        "confidence": decision.confidence,
                        "metadata": {
                            "processing_mode": "s2_only" if decision.system == "s2" else "s1_and_s2",
                            "character_type": team,
                            "character_id": character_id,
                            "orchestrator_reasoning": decision.reasoning
                        }
                    },
                    timeout=30.0  # Longer timeout for S2
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # Handle non-200 responses gracefully
                    error_text = await response.text()
                    logger.error("S2 returned error", 
                               status_code=response.status_code,
                               error=error_text)
                    return {
                        "success": False,
                        "error": f"S2 returned {response.status_code}: {error_text}",
                        "status_code": response.status_code,
                        "agent_decision": "rejected_error"
                    }
                    
            except httpx.TimeoutException:
                logger.error("S2 request timed out")
                return {
                    "success": False,
                    "error": "S2 request timed out after 30 seconds",
                    "timeout": True,
                    "agent_decision": "rejected_timeout"
                }
            except Exception as e:
                logger.error("S2 request failed", error=str(e))
                return {
                    "success": False,
                    "error": f"S2 request failed: {str(e)}",
                    "exception": str(type(e).__name__),
                    "agent_decision": "rejected_exception"
                }
    
    async def _execute_stop_command(self, decision: RoutingDecision) -> Dict[str, Any]:
        """Execute stop command for System 2"""
        logger.info("Executing stop command", stimulus_id=decision.stimulus_id)
        
        # Call S2 stop API
        endpoint = self.api_registry.apis['system2']['endpoint']
        
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{endpoint}/api/stimuli/stop",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Stop command executed successfully",
                               stopped_stimuli=result.get('stopped_stimuli_id'),
                               was_processing=result.get('was_processing'))
                    return result
                else:
                    logger.warning("Stop command failed",
                                 status_code=response.status_code,
                                 response=response.text)
                    return {
                        "success": False,
                        "error": f"Stop API returned {response.status_code}",
                        "message": "Failed to stop System 2 processing"
                    }
                    
            except Exception as e:
                logger.error("Stop command execution failed", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to execute stop command"
                }