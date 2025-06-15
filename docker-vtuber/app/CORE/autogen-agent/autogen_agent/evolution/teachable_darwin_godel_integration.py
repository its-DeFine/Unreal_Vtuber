"""
Integration layer between Teachable Agents and Darwin-Gödel System
Allows agents to learn from code evolution and apply insights
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TeachableDarwinGodelIntegration:
    """
    Connects teachable agents with Darwin-Gödel evolution system
    so agents can learn from code improvements and apply that knowledge
    """
    
    def __init__(self, teachable_agents: Dict[str, Any], darwin_godel_engine: Any):
        self.teachable_agents = teachable_agents
        self.dgm_engine = darwin_godel_engine
        self.integration_enabled = True
        
        logger.info("🔗 Teachable-DGM Integration initialized")
    
    async def teach_agents_about_evolution(self, evolution_result: Dict[str, Any]):
        """
        Teach agents about a successful code evolution
        
        Args:
            evolution_result: Result from Darwin-Gödel evolution cycle
        """
        if not self.integration_enabled:
            return
        
        try:
            # Extract key information
            improvement_type = evolution_result.get('modification_type', 'optimization')
            performance_gain = evolution_result.get('expected_improvement', 0.0)
            code_change = evolution_result.get('generated_code', '')
            target_file = evolution_result.get('target_file', '')
            
            # Create teaching message for cognitive agent
            cognitive_teaching = f"""
I've learned something important about code optimization:

🎯 Optimization Type: {improvement_type}
📈 Performance Improvement: {performance_gain * 100:.1f}%
📁 Target: {target_file}

Key Pattern: When we see similar performance bottlenecks in the future, 
we can apply this type of optimization. The approach was to {evolution_result.get('opportunity', 'optimize the code')}.

Remember this pattern for future use.
"""
            
            # Teach cognitive agent
            if "cognitive" in self.teachable_agents:
                await self._teach_agent(
                    self.teachable_agents["cognitive"],
                    cognitive_teaching
                )
            
            # Create teaching message for programmer agent
            programmer_teaching = f"""
I've learned a new code optimization pattern:

📝 Code Pattern: {improvement_type}
🔧 Implementation Approach:
```python
# Original approach had performance issues
# New approach achieved {performance_gain * 100:.1f}% improvement
# Key insight: {evolution_result.get('opportunity', 'optimization strategy')}
```

This pattern can be reused when we encounter similar code structures.
Store this as a successful optimization template.
"""
            
            # Teach programmer agent
            if "programmer" in self.teachable_agents:
                await self._teach_agent(
                    self.teachable_agents["programmer"],
                    programmer_teaching
                )
            
            logger.info(f"✅ Taught agents about {improvement_type} evolution")
            
        except Exception as e:
            logger.error(f"Error teaching agents about evolution: {e}")
    
    async def get_agent_insights_for_evolution(self, code_context: str, opportunity: str) -> List[Dict]:
        """
        Query teachable agents for insights about similar optimizations
        
        Returns:
            List of insights from agent memories
        """
        insights = []
        
        try:
            # Query cognitive agent for strategic insights
            if "cognitive" in self.teachable_agents:
                cognitive_query = f"What optimization strategies have worked for {opportunity}?"
                cognitive_insights = await self._query_agent_memory(
                    self.teachable_agents["cognitive"],
                    cognitive_query
                )
                insights.extend(cognitive_insights)
            
            # Query programmer agent for code patterns
            if "programmer" in self.teachable_agents:
                programmer_query = f"Show code patterns for {opportunity} optimization"
                programmer_insights = await self._query_agent_memory(
                    self.teachable_agents["programmer"],
                    programmer_query
                )
                insights.extend(programmer_insights)
            
            # Format insights for Darwin-Gödel
            formatted_insights = []
            for insight in insights:
                formatted_insights.append({
                    "approach": insight.get("content", ""),
                    "performance_gain": self._extract_performance_gain(insight),
                    "source": insight.get("agent", "unknown")
                })
            
            return formatted_insights
            
        except Exception as e:
            logger.error(f"Error getting agent insights: {e}")
            return []
    
    async def create_evolution_learning_loop(self):
        """
        Create a continuous learning loop between agents and evolution
        """
        logger.info("🔄 Starting evolution learning loop")
        
        # This would be called after each evolution cycle
        # 1. Darwin-Gödel generates improvement
        # 2. Agents learn from the improvement
        # 3. Next evolution uses agent insights
        # 4. Repeat
        
        return {
            "status": "learning_loop_active",
            "message": "Agents now learn from each code evolution"
        }
    
    async def _teach_agent(self, agent: Any, message: str):
        """Teach an agent by sending a message"""
        # In real implementation, this would use agent's receive method
        # For now, we'll simulate it
        logger.info(f"Teaching agent: {message[:100]}...")
    
    async def _query_agent_memory(self, agent: Any, query: str) -> List[Dict]:
        """Query an agent's memory for insights"""
        # In real implementation, this would search agent's vector DB
        # For now, return empty list
        return []
    
    def _extract_performance_gain(self, insight: Dict) -> float:
        """Extract performance gain from insight text"""
        # Simple extraction - in practice would use NLP
        import re
        
        text = insight.get("content", "")
        match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*improvement', text, re.IGNORECASE)
        
        if match:
            return float(match.group(1)) / 100.0
        return 0.0


def create_integrated_system(teachable_agents: Dict[str, Any], 
                           darwin_godel_engine: Any) -> TeachableDarwinGodelIntegration:
    """
    Create an integrated system where teachable agents learn from evolution
    
    Args:
        teachable_agents: Dictionary of teachable agent instances
        darwin_godel_engine: Darwin-Gödel engine instance
        
    Returns:
        Integration system
    """
    integration = TeachableDarwinGodelIntegration(
        teachable_agents=teachable_agents,
        darwin_godel_engine=darwin_godel_engine
    )
    
    logger.info("🧬🎓 Created integrated Teachable-DGM system")
    return integration


# Example usage in main evolution cycle
async def enhanced_evolution_cycle(integration: TeachableDarwinGodelIntegration,
                                 target_file: str):
    """
    Run evolution cycle with agent learning
    """
    # 1. Get insights from agents
    agent_insights = await integration.get_agent_insights_for_evolution(
        code_context="performance optimization",
        opportunity="reduce decision time"
    )
    
    # 2. Run Darwin-Gödel evolution with insights
    # (This would be passed to the LLM as examples)
    evolution_result = {
        "modification_type": "algorithm_optimization",
        "expected_improvement": 0.35,
        "opportunity": "replaced naive loop with efficient algorithm",
        "target_file": target_file,
        "generated_code": "# Optimized code here"
    }
    
    # 3. Teach agents about the result
    await integration.teach_agents_about_evolution(evolution_result)
    
    return evolution_result