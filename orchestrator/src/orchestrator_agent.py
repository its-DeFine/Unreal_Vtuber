"""
Orchestrator Agent - AutoGen-based routing intelligence
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

    async def route(self, request: StimulusRequest) -> RoutingDecision:
        """
        Make routing decision for incoming stimulus
        Target: < 10ms latency
        """
        start_time = time.time()
        
        try:
            # Quick intent classification using Ollama
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
        
        logger.info("Forwarding to S1", 
                   stimulus_id=decision.stimulus_id,
                   persona=persona)
        
        # Make API call
        import httpx
        async with httpx.AsyncClient() as client:
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
            return response.json()
    
    async def _call_s2(self, decision: RoutingDecision) -> Dict[str, Any]:
        """Call System 2 API"""
        endpoint = self.api_registry.apis['system2']['endpoint']
        team = decision.config.get('team', 'streamer')
        
        logger.info("Forwarding to S2", 
                   stimulus_id=decision.stimulus_id,
                   team=team)
        
        # Make API call
        import httpx
        async with httpx.AsyncClient() as client:
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
                        "character_type": f"{team}_template",
                        "orchestrator_reasoning": decision.reasoning
                    }
                },
                timeout=30.0  # Longer timeout for S2
            )
            return response.json()