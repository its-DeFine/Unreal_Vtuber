import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from .cognitive_memory import CognitiveMemoryManager, MemoryEntry

class CognitiveDecisionEngine:
    """Enhanced decision engine with memory-aware, goal-directed decision making"""
    
    def __init__(self, memory_manager: CognitiveMemoryManager, tool_registry):
        self.memory = memory_manager
        self.tool_registry = tool_registry
        self.decision_history = []
        self.performance_metrics = {}
        
        logging.info("🧠 [COGNITIVE_DECISION] Enhanced decision engine initialized")
    
    async def make_intelligent_decision(self, context: Dict) -> Dict:
        """Make context-aware decisions using cognitive memory and tool performance"""
        
        decision_start_time = asyncio.get_event_loop().time()
        
        try:
            # 1. Enhance context with relevant memories
            logging.info("🔍 [COGNITIVE_DECISION] Enhancing context with memories...")
            relevant_memories = await self.memory.retrieve_relevant_context(
                query=self._extract_context_query(context),
                max_results=5
            )
            
            # 2. Select optimal tool based on context and memory
            logging.info("⚡ [COGNITIVE_DECISION] Selecting optimal tool...")
            selected_tool_name = await self._select_optimal_tool(context, relevant_memories)
            
            if not selected_tool_name:
                logging.warning("⚠️ [COGNITIVE_DECISION] No tool selected - using fallback")
                return await self._fallback_decision(context)
            
            # 3. Execute tool with enhanced context
            execution_result = await self._execute_tool_decision(
                selected_tool_name, context, relevant_memories
            )
            
            # 4. Store decision and result for learning
            decision_time = asyncio.get_event_loop().time() - decision_start_time
            await self._store_decision_outcome(
                context, selected_tool_name, execution_result, decision_time, relevant_memories
            )
            
            # 5. Update tool performance metrics
            await self._update_tool_performance(selected_tool_name, execution_result, decision_time)
            
            logging.info(f"✅ [COGNITIVE_DECISION] Decision completed in {decision_time:.2f}s using {selected_tool_name}")
            return execution_result
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_DECISION] Decision failed: {e}")
            return await self._fallback_decision(context)
    
    async def _select_optimal_tool(self, context: Dict, memories: List[MemoryEntry]) -> Optional[str]:
        """Select optimal tool based on context, memories, and performance history"""
        
        available_tools = list(self.tool_registry.tools.keys())
        if not available_tools:
            logging.warning("⚠️ [COGNITIVE_DECISION] No tools available")
            return None
        
        # If only one tool, use it
        if len(available_tools) == 1:
            return available_tools[0]
        
        # Score each tool based on multiple criteria
        tool_scores = {}
        
        for tool_name in available_tools:
            score = await self._calculate_tool_score(tool_name, context, memories)
            tool_scores[tool_name] = score
            logging.debug(f"🎯 [COGNITIVE_DECISION] Tool {tool_name}: score {score:.3f}")
        
        # Select tool with highest score
        if tool_scores:
            best_tool = max(tool_scores.items(), key=lambda x: x[1])
            logging.info(f"🎯 [COGNITIVE_DECISION] Selected tool: {best_tool[0]} (score: {best_tool[1]:.3f})")
            return best_tool[0]
        
        return available_tools[0]  # Fallback to first tool
    
    async def _calculate_tool_score(self, tool_name: str, context: Dict, memories: List[MemoryEntry]) -> float:
        """Calculate comprehensive tool score based on multiple factors"""
        
        score = 0.0
        
        # 1. Historical performance (40% weight)
        historical_performance = self._get_tool_historical_performance(tool_name)
        score += historical_performance * 0.4
        
        # 2. Context relevance from memories (30% weight)
        context_relevance = await self._calculate_context_relevance(tool_name, context, memories)
        score += context_relevance * 0.3
        
        # 3. Recent success rate (20% weight)
        recent_success = self._get_recent_success_rate(tool_name)
        score += recent_success * 0.2
        
        # 4. Diversity bonus - prefer less recently used tools (10% weight)
        diversity_bonus = self._calculate_diversity_bonus(tool_name)
        score += diversity_bonus * 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_tool_historical_performance(self, tool_name: str) -> float:
        """Get historical performance score for a tool"""
        if tool_name not in self.performance_metrics:
            return 0.5  # Default neutral score for new tools
        
        metrics = self.performance_metrics[tool_name]
        total_uses = metrics.get('total_uses', 0)
        if total_uses == 0:
            return 0.5
        
        success_rate = metrics.get('successes', 0) / total_uses
        avg_execution_time = metrics.get('avg_execution_time', 5.0)
        
        # Combine success rate and speed
        time_factor = max(0.1, 1.0 - (avg_execution_time / 10.0))  # Penalize slow tools
        return success_rate * time_factor
    
    async def _calculate_context_relevance(self, tool_name: str, context: Dict, memories: List[MemoryEntry]) -> float:
        """Calculate how relevant this tool is to the current context based on memories"""
        
        if not memories:
            return 0.5  # Default score if no memories
        
        relevance_scores = []
        
        for memory in memories:
            # Check if this tool was used successfully in similar contexts
            if tool_name in memory.content:
                # Weight by memory relevance and success
                memory_success = 1.0 if "Success: True" in memory.content else 0.3
                memory_weight = memory.relevance_score * memory_success
                relevance_scores.append(memory_weight)
        
        if relevance_scores:
            return sum(relevance_scores) / len(relevance_scores)
        
        return 0.5  # No specific evidence, neutral score
    
    def _get_recent_success_rate(self, tool_name: str, lookback_decisions: int = 10) -> float:
        """Get success rate for recent decisions using this tool"""
        recent_decisions = [d for d in self.decision_history[-lookback_decisions:] 
                          if d.get('tool') == tool_name]
        
        if not recent_decisions:
            return 0.5  # No recent data
        
        successes = sum(1 for d in recent_decisions if d.get('success', False))
        return successes / len(recent_decisions)
    
    def _calculate_diversity_bonus(self, tool_name: str) -> float:
        """Give bonus to tools that haven't been used recently"""
        if not self.decision_history:
            return 0.5
        
        # Check last 5 decisions
        recent_tools = [d.get('tool') for d in self.decision_history[-5:]]
        tool_count = recent_tools.count(tool_name)
        
        # More recent use = lower diversity bonus
        if tool_count == 0:
            return 1.0  # Not used recently
        elif tool_count == 1:
            return 0.7
        elif tool_count == 2:
            return 0.4
        else:
            return 0.1  # Used too frequently
    
    async def _execute_tool_decision(self, tool_name: str, context: Dict, memories: List[MemoryEntry]) -> Dict:
        """Execute the selected tool with enhanced context"""
        
        tool_function = self.tool_registry.tools.get(tool_name)
        if not tool_function:
            raise ValueError(f"Tool {tool_name} not found")
        
        # Enhance context with memory insights
        enhanced_context = context.copy()
        enhanced_context['relevant_memories'] = [
            {
                'content': memory.content,
                'relevance': memory.relevance_score,
                'timestamp': memory.timestamp
            }
            for memory in memories
        ]
        enhanced_context['memory_summary'] = self._create_memory_summary(memories)
        
        try:
            # Execute tool with enhanced context
            start_time = asyncio.get_event_loop().time()
            result = tool_function(enhanced_context)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Ensure result is a dict and add metadata
            if not isinstance(result, dict):
                result = {'message': str(result)}
            
            result['success'] = True
            result['execution_time'] = execution_time
            result['tool_used'] = tool_name
            result['memory_enhanced'] = len(memories) > 0
            
            return result
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_DECISION] Tool {tool_name} execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_used': tool_name,
                'execution_time': 0.0,
                'message': f"Tool {tool_name} failed: {e}"
            }
    
    def _create_memory_summary(self, memories: List[MemoryEntry]) -> str:
        """Create a summary of relevant memories for context enhancement"""
        if not memories:
            return "No relevant memories found."
        
        summary_parts = []
        for memory in memories[:3]:  # Top 3 most relevant
            # Extract key information from memory content
            lines = memory.content.split('\n')
            action_line = next((line for line in lines if 'Action Taken:' in line), '')
            result_line = next((line for line in lines if 'Success:' in line), '')
            
            if action_line or result_line:
                summary_parts.append(f"Previous: {action_line.strip()} {result_line.strip()}")
        
        return "; ".join(summary_parts) if summary_parts else "Memories available but no clear patterns."
    
    async def _store_decision_outcome(self, context: Dict, tool_name: str, result: Dict, 
                                    decision_time: float, memories: List[MemoryEntry]):
        """Store decision outcome for learning and analysis"""
        
        # Store in memory manager
        await self.memory.store_interaction(context, tool_name, result)
        
        # Add to decision history
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'tool': tool_name,
            'success': result.get('success', False),
            'execution_time': result.get('execution_time', decision_time),
            'context_size': len(str(context)),
            'memories_used': len(memories),
            'decision_time': decision_time
        }
        
        self.decision_history.append(decision_record)
        
        # Keep only last 100 decisions in memory
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-100:]
    
    async def _update_tool_performance(self, tool_name: str, result: Dict, decision_time: float):
        """Update performance metrics for the tool"""
        
        if tool_name not in self.performance_metrics:
            self.performance_metrics[tool_name] = {
                'total_uses': 0,
                'successes': 0,
                'total_execution_time': 0.0,
                'avg_execution_time': 0.0
            }
        
        metrics = self.performance_metrics[tool_name]
        metrics['total_uses'] += 1
        
        if result.get('success', False):
            metrics['successes'] += 1
        
        execution_time = result.get('execution_time', decision_time)
        metrics['total_execution_time'] += execution_time
        metrics['avg_execution_time'] = metrics['total_execution_time'] / metrics['total_uses']
    
    def _extract_context_query(self, context: Dict) -> str:
        """Extract a search query from the context for memory retrieval"""
        
        # Try to extract meaningful query from context
        if 'message' in context:
            return str(context['message'])
        elif 'action' in context:
            return str(context['action'])
        elif 'request' in context:
            return str(context['request'])
        else:
            # Fallback: use most recent values as query
            context_values = [str(v) for v in context.values() if isinstance(v, (str, int, float))]
            return " ".join(context_values[:3]) if context_values else "general query"
    
    async def _fallback_decision(self, context: Dict) -> Dict:
        """Fallback decision when intelligent selection fails"""
        
        logging.info("🔄 [COGNITIVE_DECISION] Using fallback decision")
        
        # Use the original naive selection from tool registry
        tool_function = self.tool_registry.select_tool(context)
        if tool_function:
            try:
                result = tool_function(context)
                if not isinstance(result, dict):
                    result = {'message': str(result)}
                result['success'] = True
                result['fallback'] = True
                return result
            except Exception as e:
                logging.error(f"❌ [COGNITIVE_DECISION] Fallback execution failed: {e}")
        
        # Ultimate fallback
        return {
            'success': False,
            'message': "No tools available or all tools failed",
            'fallback': True
        } 