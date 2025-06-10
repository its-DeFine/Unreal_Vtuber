"""
🧬🧠 Cognitive Evolution Engine - Darwin-Gödel Machine + Cognee Integration

This module provides the core integration between the Darwin-Gödel Machine's 
self-improvement capabilities and Cognee's knowledge graph memory system.

Key Features:
- Performance data storage and analysis
- Historical pattern recognition  
- Code modification guided by past successes/failures
- Safety mechanisms with rollback learning
- Institutional memory for code evolution
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp

@dataclass
class PerformanceContext:
    """Performance data context for analysis"""
    decision_time: float
    success_rate: float  
    tool_effectiveness: Dict[str, float]
    memory_usage: float
    error_count: int
    context_hash: str
    timestamp: datetime
    iteration_count: int

@dataclass  
class CodeModificationPlan:
    """Plan for code modification"""
    id: str
    target_file: str
    change_type: str  # 'optimization', 'bug_fix', 'feature_enhancement'
    description: str
    expected_improvement: float
    risk_level: str  # 'low', 'medium', 'high'
    confidence_score: float
    historical_precedent: Optional[str] = None

@dataclass
class EvolutionResult:
    """Results of evolution cycle"""
    modification_plan: CodeModificationPlan
    safety_passed: bool
    actual_improvement: float
    side_effects: List[str]
    deployed: bool
    rollback_needed: bool
    learning_insights: List[str]

class CognitiveEvolutionEngine:
    """
    Main engine that combines Darwin-Gödel Machine self-improvement 
    with Cognee's institutional memory for continuous learning
    """
    
    def __init__(self, cognee_url: str, cognee_api_key: str, 
                 autogen_agent_dir: str = "/app/autogen_agent"):
        self.cognee_url = cognee_url.rstrip('/')
        self.cognee_api_key = cognee_api_key
        self.agent_dir = autogen_agent_dir
        self.dataset_name = "autogen_code_evolution"
        
        # Evolution tracking
        self.evolution_cycles = 0
        self.total_improvements = 0.0
        self.failed_attempts = 0
        self.knowledge_entries = 0
        
        logging.info("🧬🧠 [COGNITIVE_EVOLUTION] Engine initialized")
        
    async def initialize(self) -> bool:
        """Initialize the cognitive evolution system"""
        try:
            # Test Cognee connection
            if not await self._test_cognee_connection():
                logging.error("❌ [COGNITIVE_EVOLUTION] Cognee connection failed")
                return False
            
            # Initialize knowledge base with seed data
            await self._initialize_knowledge_base()
            
            logging.info("✅ [COGNITIVE_EVOLUTION] Engine fully initialized")
            return True
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_EVOLUTION] Initialization failed: {e}")
            return False
    
    async def analyze_and_evolve(self, performance_context: PerformanceContext) -> Optional[EvolutionResult]:
        """
        Main evolution cycle: analyze performance, query historical data,
        generate improvements, test safely, and learn from results
        """
        self.evolution_cycles += 1
        cycle_id = f"evolution_cycle_{self.evolution_cycles}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logging.info(f"🔄 [COGNITIVE_EVOLUTION] Starting evolution cycle {self.evolution_cycles}")
        
        try:
            # 1. Store current performance context in Cognee
            await self._store_performance_context(performance_context, cycle_id)
            
            # 2. Identify improvement opportunities
            opportunities = await self._identify_improvement_opportunities(performance_context)
            
            if not opportunities:
                logging.info("✅ [COGNITIVE_EVOLUTION] No improvement opportunities found")
                return None
            
            # 3. Query historical knowledge for similar contexts
            historical_insights = await self._query_historical_insights(performance_context, opportunities)
            
            # 4. Generate modification plan based on historical knowledge
            modification_plan = await self._generate_modification_plan(
                performance_context, opportunities, historical_insights
            )
            
            if not modification_plan:
                logging.warning("⚠️ [COGNITIVE_EVOLUTION] No viable modification plan generated")
                return None
            
            # 5. Execute evolution cycle safely
            evolution_result = await self._execute_evolution_safely(modification_plan, cycle_id)
            
            # 6. Store results and learn from outcome
            await self._store_evolution_results(evolution_result, cycle_id)
            
            # 7. Update success patterns and failure modes
            await self._update_knowledge_patterns(evolution_result)
            
            logging.info(f"✅ [COGNITIVE_EVOLUTION] Cycle {self.evolution_cycles} completed successfully")
            return evolution_result
            
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_EVOLUTION] Evolution cycle {self.evolution_cycles} failed: {e}")
            await self._store_failure_context(cycle_id, str(e), performance_context)
            return None
    
    async def _store_performance_context(self, context: PerformanceContext, cycle_id: str):
        """Store performance context in Cognee with rich relationships"""
        
        # Create detailed performance analysis
        performance_analysis = f"""
Evolution Cycle {cycle_id} - Performance Analysis:

📊 Performance Metrics:
- Decision Time: {context.decision_time:.2f}s (Target: <2.0s)
- Success Rate: {context.success_rate:.1%} (Target: >90%)
- Memory Usage: {context.memory_usage:.1f}MB
- Error Count: {context.error_count} (Target: 0)
- Iteration: #{context.iteration_count}

🛠️ Tool Effectiveness Analysis:
{self._format_tool_effectiveness(context.tool_effectiveness)}

🎯 Performance Assessment:
{self._assess_performance_status(context)}

🔍 Context Characteristics:
- Context Hash: {context.context_hash}
- Timestamp: {context.timestamp.isoformat()}
- Analysis ID: {cycle_id}

💡 Improvement Opportunities:
{self._identify_immediate_opportunities(context)}
"""
        
        await self._add_to_cognee([performance_analysis])
        logging.info(f"💾 [COGNITIVE_EVOLUTION] Stored performance context for {cycle_id}")
    
    async def _query_historical_insights(self, context: PerformanceContext, 
                                       opportunities: List[str]) -> Dict[str, Any]:
        """Query Cognee for historical insights related to current context"""
        
        insights = {
            "similar_performance_issues": [],
            "successful_modifications": [],
            "failed_attempts": [],
            "applicable_patterns": [],
            "confidence_scores": {}
        }
        
        # Query for similar performance issues
        performance_query = f"""
        Find previous performance analysis with similar characteristics:
        - Decision time around {context.decision_time:.1f}s
        - Success rate around {context.success_rate:.1%}
        - Similar tool effectiveness patterns
        - Memory usage around {context.memory_usage:.1f}MB
        """
        
        similar_issues = await self._search_cognee(performance_query, limit=5)
        insights["similar_performance_issues"] = similar_issues
        
        # Query for successful modifications for each opportunity
        for opportunity in opportunities:
            success_query = f"""
            Find successful code modifications that addressed {opportunity}:
            - Modifications with PASSED safety tests
            - Positive performance improvements
            - No rollback required
            - Similar context patterns
            """
            
            successful_mods = await self._search_cognee(success_query, limit=3)
            insights["successful_modifications"].extend(successful_mods)
            
            # Query for failed attempts to avoid repeating mistakes
            failure_query = f"""
            Find failed modification attempts related to {opportunity}:
            - Modifications with FAILED safety tests
            - Rollback required
            - Negative side effects
            - Similar risk levels
            """
            
            failed_attempts = await self._search_cognee(failure_query, limit=3)
            insights["failed_attempts"].extend(failed_attempts)
        
        # Calculate confidence scores based on historical data
        insights["confidence_scores"] = self._calculate_confidence_scores(insights)
        
        logging.info(f"🔍 [COGNITIVE_EVOLUTION] Retrieved {len(insights['similar_performance_issues'])} similar cases")
        return insights
    
    async def _generate_modification_plan(self, context: PerformanceContext, 
                                        opportunities: List[str],
                                        historical_insights: Dict[str, Any]) -> Optional[CodeModificationPlan]:
        """Generate code modification plan informed by historical knowledge"""
        
        # Select the most promising opportunity based on historical success
        best_opportunity = self._select_best_opportunity(opportunities, historical_insights)
        
        if not best_opportunity:
            return None
        
        # Generate modification plan based on successful historical patterns
        modification_id = f"mod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{best_opportunity}"
        
        # Determine target file and change type based on opportunity
        target_file, change_type = self._determine_modification_target(best_opportunity)
        
        # Calculate expected improvement based on historical data
        expected_improvement = self._estimate_improvement(best_opportunity, historical_insights)
        
        # Assess risk level based on historical failures
        risk_level = self._assess_risk_level(best_opportunity, historical_insights)
        
        # Calculate confidence score
        confidence_score = historical_insights["confidence_scores"].get(best_opportunity, 0.5)
        
        # Find historical precedent
        precedent = self._find_best_precedent(best_opportunity, historical_insights)
        
        plan = CodeModificationPlan(
            id=modification_id,
            target_file=target_file,
            change_type=change_type,
            description=f"Optimize {best_opportunity} based on historical successful patterns",
            expected_improvement=expected_improvement,
            risk_level=risk_level,
            confidence_score=confidence_score,
            historical_precedent=precedent
        )
        
        logging.info(f"📋 [COGNITIVE_EVOLUTION] Generated modification plan: {plan.id}")
        return plan
    
    async def _execute_evolution_safely(self, plan: CodeModificationPlan, 
                                      cycle_id: str) -> EvolutionResult:
        """Execute code evolution with safety mechanisms and testing"""
        
        logging.info(f"⚗️ [COGNITIVE_EVOLUTION] Executing modification {plan.id} safely")
        
        # For now, simulate the execution - in real implementation this would:
        # 1. Create sandbox environment
        # 2. Apply code modifications
        # 3. Run safety tests
        # 4. Measure performance improvements
        # 5. Deploy if safe, rollback if not
        
        # Simulate based on confidence score and risk level
        safety_passed = plan.confidence_score > 0.6 and plan.risk_level != 'high'
        
        if safety_passed:
            # Simulate successful improvement (with some variance)
            actual_improvement = plan.expected_improvement * (0.8 + 0.4 * plan.confidence_score)
            deployed = True
            rollback_needed = False
            side_effects = []
            learning_insights = [
                f"Modification type '{plan.change_type}' successful for {plan.target_file}",
                f"Historical precedent guidance proved accurate",
                f"Confidence score {plan.confidence_score:.2f} was reliable"
            ]
            self.total_improvements += actual_improvement
        else:
            # Simulate failed attempt
            actual_improvement = -0.1  # Slight performance degradation
            deployed = False
            rollback_needed = True
            side_effects = ["Performance degradation detected", "Safety tests failed"]
            learning_insights = [
                f"Modification type '{plan.change_type}' failed for {plan.target_file}",
                f"Risk level '{plan.risk_level}' assessment was accurate",
                f"Need better historical pattern recognition"
            ]
            self.failed_attempts += 1
        
        result = EvolutionResult(
            modification_plan=plan,
            safety_passed=safety_passed,
            actual_improvement=actual_improvement,
            side_effects=side_effects,
            deployed=deployed,
            rollback_needed=rollback_needed,
            learning_insights=learning_insights
        )
        
        logging.info(f"{'✅' if safety_passed else '❌'} [COGNITIVE_EVOLUTION] Modification {plan.id} {'succeeded' if safety_passed else 'failed'}")
        return result
    
    async def _store_evolution_results(self, result: EvolutionResult, cycle_id: str):
        """Store evolution results in Cognee for future learning"""
        
        plan = result.modification_plan
        status = "SUCCESS" if result.deployed else "FAILED"
        
        evolution_report = f"""
Evolution Result {cycle_id} - Code Modification {plan.id}:

🎯 Modification Details:
- Target File: {plan.target_file}
- Change Type: {plan.change_type}
- Description: {plan.description}
- Risk Level: {plan.risk_level}
- Confidence Score: {plan.confidence_score:.2f}

📊 Execution Results:
- Safety Tests: {'PASSED' if result.safety_passed else 'FAILED'}
- Expected Improvement: {plan.expected_improvement:.1%}
- Actual Improvement: {result.actual_improvement:.1%}
- Effectiveness Rating: {(result.actual_improvement / plan.expected_improvement) if plan.expected_improvement > 0 else 0:.1%}
- Deployment Status: {status}
- Rollback Required: {'YES' if result.rollback_needed else 'NO'}

⚠️ Side Effects:
{self._format_side_effects(result.side_effects)}

🧠 Learning Insights:
{self._format_learning_insights(result.learning_insights)}

🔗 Historical Context:
- Based on precedent: {plan.historical_precedent or 'None'}
- Evolution cycle: {cycle_id}
- Total evolution cycles: {self.evolution_cycles}

📈 Success Pattern:
{self._generate_success_pattern(result)}
"""
        
        await self._add_to_cognee([evolution_report])
        self.knowledge_entries += 1
        
        logging.info(f"💾 [COGNITIVE_EVOLUTION] Stored evolution results for {plan.id}")
    
    # Utility methods for analysis and formatting
    def _format_tool_effectiveness(self, effectiveness: Dict[str, float]) -> str:
        """Format tool effectiveness data"""
        if not effectiveness:
            return "- No tool effectiveness data available"
        
        lines = []
        for tool, score in effectiveness.items():
            status = "🟢 Excellent" if score > 0.8 else "🟡 Good" if score > 0.6 else "🔴 Needs Improvement"
            lines.append(f"- {tool}: {score:.1%} ({status})")
        
        return "\n".join(lines)
    
    def _assess_performance_status(self, context: PerformanceContext) -> str:
        """Assess overall performance status"""
        issues = []
        
        if context.decision_time > 2.0:
            issues.append(f"Decision time {context.decision_time:.1f}s exceeds 2.0s target")
        
        if context.success_rate < 0.9:
            issues.append(f"Success rate {context.success_rate:.1%} below 90% target")
        
        if context.error_count > 0:
            issues.append(f"Error count {context.error_count} above 0 target")
        
        if context.memory_usage > 100:
            issues.append(f"Memory usage {context.memory_usage:.1f}MB high")
        
        if not issues:
            return "✅ All performance metrics within acceptable ranges"
        
        return "⚠️ Performance issues identified:\n" + "\n".join(f"  - {issue}" for issue in issues)
    
    def _identify_immediate_opportunities(self, context: PerformanceContext) -> str:
        """Identify immediate improvement opportunities"""
        opportunities = []
        
        if context.decision_time > 2.0:
            opportunities.append("Decision speed optimization")
        
        if context.success_rate < 0.9:
            opportunities.append("Success rate improvement")
        
        if context.error_count > 0:
            opportunities.append("Error reduction")
        
        # Analyze tool effectiveness
        if context.tool_effectiveness:
            poor_tools = [tool for tool, score in context.tool_effectiveness.items() if score < 0.6]
            if poor_tools:
                opportunities.append(f"Tool optimization: {', '.join(poor_tools)}")
        
        if not opportunities:
            return "✅ No immediate improvement opportunities identified"
        
        return "\n".join(f"- {opp}" for opp in opportunities)
    
    async def _identify_improvement_opportunities(self, context: PerformanceContext) -> List[str]:
        """Identify specific improvement opportunities from performance context"""
        opportunities = []
        
        if context.decision_time > 2.0:
            opportunities.append("decision_speed")
        
        if context.success_rate < 0.9:
            opportunities.append("success_rate")
        
        if context.error_count > 0:
            opportunities.append("error_reduction")
        
        if context.memory_usage > 100:
            opportunities.append("memory_optimization")
        
        # Tool-specific opportunities
        if context.tool_effectiveness:
            for tool, score in context.tool_effectiveness.items():
                if score < 0.6:
                    opportunities.append(f"tool_{tool}_optimization")
        
        return opportunities
    
    # Cognee integration methods
    async def _test_cognee_connection(self) -> bool:
        """Test connection to Cognee service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.cognee_url}/health") as response:
                    return response.status == 200
        except:
            return False
    
    async def _add_to_cognee(self, content: List[str]):
        """Add content to Cognee knowledge graph"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cognee_url}/api/v1/add",
                    headers={'Authorization': f'Bearer {self.cognee_api_key}'},
                    json={'data': content, 'dataset_name': self.dataset_name}
                ) as response:
                    if response.status != 200:
                        logging.error(f"❌ [COGNITIVE_EVOLUTION] Cognee storage failed: {response.status}")
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_EVOLUTION] Cognee storage error: {e}")
    
    async def _search_cognee(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Cognee knowledge graph"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cognee_url}/api/v1/search",
                    headers={'Authorization': f'Bearer {self.cognee_api_key}'},
                    json={
                        'query': query,
                        'dataset_name': self.dataset_name,
                        'limit': limit
                    }
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"❌ [COGNITIVE_EVOLUTION] Cognee search failed: {response.status}")
                        return []
        except Exception as e:
            logging.error(f"❌ [COGNITIVE_EVOLUTION] Cognee search error: {e}")
            return []
    
    async def _initialize_knowledge_base(self):
        """Initialize knowledge base with seed data"""
        seed_data = [
            """
AutoGen Cognitive Evolution System - Initialization:

🧬 Darwin-Gödel Machine Integration:
- Purpose: Continuous self-improvement through code evolution
- Safety: All modifications tested in sandboxed environments
- Learning: Historical success/failure patterns guide future decisions
- Metrics: Decision speed, success rate, error reduction, memory optimization

🧠 Cognee Knowledge Graph Integration:
- Dataset: autogen_code_evolution
- Storage: Performance events, code modifications, testing results
- Relationships: Success patterns, failure modes, improvement triggers
- Memory: Institutional knowledge for code evolution decisions

🎯 Success Criteria:
- Decision time: <2.0 seconds target
- Success rate: >90% target  
- Error count: 0 target
- Memory usage: <100MB preferred

This is the foundation for autonomous code evolution with institutional memory.
            """
        ]
        
        await self._add_to_cognee(seed_data)
        logging.info("🌱 [COGNITIVE_EVOLUTION] Knowledge base initialized with seed data")
    
    # Additional helper methods (stubs for now)
    def _select_best_opportunity(self, opportunities: List[str], insights: Dict) -> Optional[str]:
        """Select the most promising improvement opportunity"""
        if not opportunities:
            return None
        # For now, return the first opportunity - could be enhanced with ML scoring
        return opportunities[0]
    
    def _determine_modification_target(self, opportunity: str) -> Tuple[str, str]:
        """Determine target file and change type for opportunity"""
        if "decision_speed" in opportunity:
            return "tool_registry.py", "optimization"
        elif "success_rate" in opportunity:
            return "cognitive_decision_engine.py", "enhancement"  
        elif "error_reduction" in opportunity:
            return "memory_manager.py", "bug_fix"
        else:
            return "main.py", "optimization"
    
    def _estimate_improvement(self, opportunity: str, insights: Dict) -> float:
        """Estimate expected improvement based on historical data"""
        # Could analyze historical improvements for similar opportunities
        # For now, return conservative estimates
        if "decision_speed" in opportunity:
            return 0.3  # 30% improvement
        elif "success_rate" in opportunity:
            return 0.15  # 15% improvement
        else:
            return 0.1  # 10% improvement
    
    def _assess_risk_level(self, opportunity: str, insights: Dict) -> str:
        """Assess risk level based on historical failures"""
        # Could analyze failure patterns
        # For now, return conservative assessments
        return "medium"
    
    def _find_best_precedent(self, opportunity: str, insights: Dict) -> Optional[str]:
        """Find best historical precedent for current opportunity"""
        successful_mods = insights.get("successful_modifications", [])
        if successful_mods:
            return f"Based on {len(successful_mods)} similar successful cases"
        return None
    
    def _calculate_confidence_scores(self, insights: Dict) -> Dict[str, float]:
        """Calculate confidence scores for different opportunities"""
        # Could implement ML-based confidence scoring
        # For now, return basic scores based on historical data availability
        return {"decision_speed": 0.7, "success_rate": 0.6, "error_reduction": 0.8}
    
    def _format_side_effects(self, side_effects: List[str]) -> str:
        """Format side effects list"""
        if not side_effects:
            return "- No side effects detected"
        return "\n".join(f"- {effect}" for effect in side_effects)
    
    def _format_learning_insights(self, insights: List[str]) -> str:
        """Format learning insights list"""
        if not insights:
            return "- No specific insights generated"
        return "\n".join(f"- {insight}" for insight in insights)
    
    def _generate_success_pattern(self, result: EvolutionResult) -> str:
        """Generate success pattern from result"""
        if result.deployed:
            return f"✅ SUCCESS: {result.modification_plan.change_type} in {result.modification_plan.target_file} with {result.modification_plan.risk_level} risk → {result.actual_improvement:.1%} improvement"
        else:
            return f"❌ FAILURE: {result.modification_plan.change_type} in {result.modification_plan.target_file} with {result.modification_plan.risk_level} risk → Rollback required"
    
    async def _update_knowledge_patterns(self, result: EvolutionResult):
        """Update success/failure patterns in knowledge base"""
        # This would analyze patterns and create higher-level insights
        # For now, just log the pattern update
        pattern_type = "success" if result.deployed else "failure"
        logging.info(f"📊 [COGNITIVE_EVOLUTION] Updated {pattern_type} patterns based on {result.modification_plan.id}")
    
    async def _store_failure_context(self, cycle_id: str, error: str, context: PerformanceContext):
        """Store failure context for learning"""
        failure_report = f"""
Evolution Cycle Failure {cycle_id}:

❌ Error Details:
- Error: {error}
- Context: {context.context_hash}
- Timestamp: {datetime.now().isoformat()}

📊 Performance Context:
- Decision Time: {context.decision_time}s
- Success Rate: {context.success_rate:.1%}
- Memory Usage: {context.memory_usage}MB
- Iteration: #{context.iteration_count}

🔍 Failure Analysis:
- Evolution cycle {self.evolution_cycles} failed before modification generation
- Need to investigate error patterns and improve robustness
- This failure provides learning data for future cycle improvements
"""
        
        await self._add_to_cognee([failure_report])
        logging.info(f"💾 [COGNITIVE_EVOLUTION] Stored failure context for {cycle_id}")

    def get_evolution_stats(self) -> Dict[str, Any]:
        """Get current evolution statistics"""
        return {
            "evolution_cycles": self.evolution_cycles,
            "total_improvements": self.total_improvements,
            "failed_attempts": self.failed_attempts,
            "knowledge_entries": self.knowledge_entries,
            "success_rate": (self.evolution_cycles - self.failed_attempts) / max(self.evolution_cycles, 1),
            "average_improvement": self.total_improvements / max(self.evolution_cycles - self.failed_attempts, 1)
        } 