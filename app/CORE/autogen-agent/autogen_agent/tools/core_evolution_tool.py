"""
🧬 Core Evolution Tool - Real Darwin-Gödel Machine Integration

This tool integrates with the actual Darwin-Gödel Machine to perform:
- Real code analysis and improvement
- Autonomous system evolution  
- Performance optimization
- Learning pattern identification
- Self-modification with safety controls

Connected to: DarwinGodelEngine + CognitiveEvolutionEngine + Cognee
"""

import logging
import time
import asyncio
from typing import Dict, Any

async def run(context: Dict) -> Dict[str, Any]:
    """Core evolution tool with real Darwin-Gödel Machine integration"""
    
    iteration = context.get("iteration", 0)
    timestamp = time.time()
    
    # Extract cognitive context
    memory_summary = context.get("memory_summary", "")
    relevant_memories = context.get("relevant_memories", [])
    autonomous = context.get("autonomous", False)
    
    logging.info(f"🧬 [CORE_EVOLUTION] Starting Darwin-Gödel evolution cycle #{iteration}")
    
    try:
        # 🚀 REAL DARWIN-GÖDEL MACHINE INTEGRATION
        from ..services.evolution_service import EvolutionService
        
        # Initialize evolution service if not available in context
        evolution_service = context.get("evolution_service")
        if not evolution_service:
            evolution_service = EvolutionService()
            if not await evolution_service.initialize():
                logging.error("❌ [CORE_EVOLUTION] Failed to initialize evolution service")
                return _fallback_response(iteration, "Evolution service initialization failed")
        
        # 🔍 STEP 1: Analyze current performance
        performance_metrics = await evolution_service.collect_performance_metrics()
        logging.info(f"📊 [CORE_EVOLUTION] Performance metrics collected: {performance_metrics}")
        
        # 🧠 STEP 2: Query Cognee for historical insights
        memory_context = ""
        historical_insights = {}
        if memory_summary or relevant_memories:
            historical_insights = await evolution_service.get_historical_evolution_insights(
                query=f"code improvement iteration {iteration}",
                limit=5
            )
            memory_context = f" | Learning from {len(historical_insights.get('memories', []))} historical patterns"
        
        # 🎯 STEP 3: Determine evolution action based on iteration and performance
        evolution_action = _select_evolution_action(iteration, performance_metrics, historical_insights)
        
        # 🔧 STEP 4: Execute real evolution cycle
        evolution_result = await evolution_service.trigger_evolution_cycle(
            performance_context=performance_metrics,
            historical_context=historical_insights,
            evolution_focus=evolution_action["focus"]
        )
        
        # 📈 STEP 5: Process results and update metrics
        success = evolution_result.get("success", False)
        modifications_applied = evolution_result.get("modifications_applied", 0)
        performance_improvement = evolution_result.get("performance_improvement", 0.0)
        
        # 🎭 STEP 6: Generate comprehensive status message
        if success and modifications_applied > 0:
            evolution_message = f"🧬 Darwin-Gödel Evolution Cycle #{iteration} - {modifications_applied} improvements deployed"
            if performance_improvement > 0:
                evolution_message += f" (+{performance_improvement:.1%} performance)"
        elif success:
            evolution_message = f"🔍 Darwin-Gödel Analysis Cycle #{iteration} - {evolution_action['description']}"
        else:
            evolution_message = f"⚠️ Darwin-Gödel Cycle #{iteration} - {evolution_result.get('error', 'Unknown error')}"
        
        # Add memory enhancement context
        evolution_message += memory_context
        
        # Add autonomous indicator
        if autonomous:
            evolution_message += " [Autonomous Evolution Active]"
        
        # 📊 Calculate comprehensive evolution metrics
        evolution_metrics = {
            "iteration": iteration,
            "timestamp": timestamp,
            "evolution_action": evolution_action["type"],
            "success": success,
            "modifications_applied": modifications_applied,
            "performance_improvement": performance_improvement,
            "memory_enhanced": bool(historical_insights.get("memories")),
            "memory_count": len(historical_insights.get("memories", [])),
            "cognitive_mode": autonomous,
            "dgm_enabled": True,
            "real_modifications": evolution_result.get("real_modifications_enabled", False),
            "safety_checks_passed": evolution_result.get("safety_checks_passed", 0),
            "evolution_phase": _determine_evolution_phase(iteration, performance_improvement)
        }
        
        logging.info(f"🧬 [CORE_EVOLUTION] {evolution_message}")
        logging.info(f"📊 [CORE_EVOLUTION] Metrics: {evolution_metrics}")
        
        return {
            "message": evolution_message,
            "tool": "core_evolution_tool",
            "success": success,
            "evolution_metrics": evolution_metrics,
            "iteration": iteration,
            "memory_enhanced": evolution_metrics["memory_enhanced"],
            "memory_count": evolution_metrics["memory_count"],
            "cognitive": True,
            "autonomous": autonomous,
            "category": "darwin_godel_evolution",
            "phase": evolution_metrics["evolution_phase"],
            "modifications_applied": modifications_applied,
            "performance_improvement": performance_improvement,
            "dgm_integration": "active"
        }
        
    except Exception as e:
        logging.error(f"❌ [CORE_EVOLUTION] Darwin-Gödel evolution failed: {e}")
        return _fallback_response(iteration, str(e))

def _select_evolution_action(iteration: int, performance_metrics: Dict, historical_insights: Dict) -> Dict[str, str]:
    """Select evolution action based on performance data and historical insights"""
    
    # Analyze performance trends
    decision_time = performance_metrics.get("decision_time", 2.5)
    success_rate = performance_metrics.get("success_rate", 0.75)
    error_count = performance_metrics.get("error_count", 0)
    
    # Priority-based evolution actions
    if error_count > 3:
        return {
            "type": "error_reduction",
            "focus": "error_handling",
            "description": "Analyzing error patterns for code stability improvements"
        }
    elif decision_time > 3.0:
        return {
            "type": "performance_optimization", 
            "focus": "decision_speed",
            "description": "Optimizing decision-making algorithms for faster response"
        }
    elif success_rate < 0.7:
        return {
            "type": "accuracy_improvement",
            "focus": "success_rate", 
            "description": "Enhancing tool selection accuracy and effectiveness"
        }
    else:
        # Cycle through different improvement areas
        cycle_actions = [
            {
                "type": "code_analysis",
                "focus": "architecture",
                "description": "Analyzing code architecture for optimization opportunities"
            },
            {
                "type": "memory_optimization",
                "focus": "memory_usage",
                "description": "Optimizing memory usage and knowledge consolidation"
            },
            {
                "type": "tool_enhancement", 
                "focus": "tool_effectiveness",
                "description": "Improving tool selection and execution strategies"
            },
            {
                "type": "learning_acceleration",
                "focus": "pattern_recognition", 
                "description": "Accelerating learning from successful patterns"
            }
        ]
        
        action_index = iteration % len(cycle_actions)
        return cycle_actions[action_index]

def _determine_evolution_phase(iteration: int, performance_improvement: float) -> str:
    """Determine current evolution phase based on iteration and performance"""
    if iteration < 5:
        return "initialization"
    elif iteration < 20:
        return "learning_phase"
    elif iteration < 50:
        return "optimization_phase"
    elif performance_improvement > 0.1:
        return "breakthrough_phase"
    else:
        return "refinement_phase"

def _fallback_response(iteration: int, error_message: str) -> Dict[str, Any]:
    """Fallback response when DGM integration fails"""
    
    # Enhanced fallback evolution actions
    fallback_actions = [
        "🧬 Analyzing autonomous system patterns and decision quality",
        "🔍 Evaluating cognitive enhancement algorithms and memory integration", 
        "📊 Monitoring performance metrics and identifying optimization opportunities",
        "⚡ Processing goal achievement patterns and success strategies",
        "🧠 Consolidating knowledge graph relationships and learned insights",
        "🎯 Refining tool orchestration and selection methodologies",
        "🔄 Analyzing feedback loops for continuous improvement patterns",
        "📈 Measuring cognitive enhancement effectiveness and impact",
        "🛠️ Identifying system architecture evolution opportunities",
        "🚀 Advancing autonomous capabilities through pattern recognition"
    ]
    
    action_index = iteration % len(fallback_actions)
    message = f"{fallback_actions[action_index]} - Cycle #{iteration} (Fallback Mode)"
    
    if error_message:
        message += f" | Error: {error_message[:50]}..."
    
    return {
        "message": message,
        "tool": "core_evolution_tool",
        "success": False,
        "evolution_metrics": {
            "iteration": iteration,
            "timestamp": time.time(),
            "action_category": "fallback_evolution",
            "dgm_enabled": False,
            "error": error_message
        },
        "iteration": iteration,
        "cognitive": True,
        "category": "fallback_evolution",
        "dgm_integration": "failed"
    } 