"""
🧬 Evolution Service - Integration Layer for Cognitive Evolution

This service integrates the Cognitive Evolution Engine (Darwin-Gödel + Cognee)
with the live AutoGen system, providing:

- Performance monitoring and data collection
- Evolution cycle triggering and management  
- MCP endpoint integration for development control
- Safety oversight and rollback capabilities
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..evolution.cognitive_evolution_engine import (
    CognitiveEvolutionEngine, 
    PerformanceContext, 
    EvolutionResult
)
from ..evolution.darwin_godel_engine import DarwinGodelEngine

class EvolutionService:
    """
    Service layer that manages the integration between AutoGen agents
    and the Cognitive Evolution Engine for continuous self-improvement
    """
    
    def __init__(self, cognee_url: str, cognee_api_key: str, 
                 autogen_agent_dir: str = "/app/autogen_agent"):
        self.cognee_url = cognee_url
        self.cognee_api_key = cognee_api_key
        self.agent_dir = autogen_agent_dir
        
        # Initialize evolution components
        self.evolution_engine = None
        self.dgm_engine = None
        
        # Service state
        self.evolution_enabled = False
        self.auto_evolution_enabled = False
        self.evolution_interval = 300  # 5 minutes default
        self.last_evolution_time = None
        
        # Performance tracking
        self.performance_history = []
        self.current_performance = None
        
        # Evolution statistics
        self.total_evolution_cycles = 0
        self.successful_improvements = 0
        self.failed_attempts = 0
        
        logging.info("🧬 [EVOLUTION_SERVICE] Service initialized")
    
    async def initialize(self) -> bool:
        """Initialize the evolution service and its components"""
        try:
            logging.info("🔧 [EVOLUTION_SERVICE] Initializing evolution components...")
            
            # Initialize Darwin-Gödel Machine
            self.dgm_engine = DarwinGodelEngine(self.agent_dir)
            if not await self.dgm_engine.initialize():
                logging.error("❌ [EVOLUTION_SERVICE] DGM engine initialization failed")
                return False
            
            # Initialize Cognitive Evolution Engine
            self.evolution_engine = CognitiveEvolutionEngine(
                self.cognee_url, 
                self.cognee_api_key, 
                self.agent_dir
            )
            if not await self.evolution_engine.initialize():
                logging.error("❌ [EVOLUTION_SERVICE] Cognitive evolution engine initialization failed")
                return False
            
            self.evolution_enabled = True
            logging.info("✅ [EVOLUTION_SERVICE] All components initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [EVOLUTION_SERVICE] Initialization failed: {e}")
            return False
    
    async def collect_performance_data(self, agent_metrics: Dict[str, Any]) -> bool:
        """
        Collect performance data from the running AutoGen system
        """
        try:
            # Extract performance metrics from agent data
            performance_context = PerformanceContext(
                decision_time=agent_metrics.get('decision_time', 0.0),
                success_rate=agent_metrics.get('success_rate', 0.0),
                tool_effectiveness=agent_metrics.get('tool_effectiveness', {}),
                memory_usage=agent_metrics.get('memory_usage', 0.0),
                error_count=agent_metrics.get('error_count', 0),
                context_hash=agent_metrics.get('context_hash', 'unknown'),
                timestamp=datetime.now(),
                iteration_count=agent_metrics.get('iteration_count', 0)
            )
            
            # Store in performance history
            self.performance_history.append(performance_context)
            self.current_performance = performance_context
            
            # Keep only recent history (last 100 entries)
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            logging.info(f"📊 [EVOLUTION_SERVICE] Performance data collected: {performance_context.decision_time:.2f}s decision time")
            
            # Check if automatic evolution should trigger
            if self.auto_evolution_enabled and self._should_trigger_evolution():
                asyncio.create_task(self._trigger_evolution_cycle())
            
            return True
            
        except Exception as e:
            logging.error(f"❌ [EVOLUTION_SERVICE] Performance data collection failed: {e}")
            return False
    
    async def trigger_evolution_manually(self, context: str = "") -> Dict[str, Any]:
        """
        Manually trigger an evolution cycle
        """
        if not self.evolution_enabled:
            return {"success": False, "error": "Evolution service not initialized"}
        
        if not self.current_performance:
            return {"success": False, "error": "No performance data available"}
        
        try:
            logging.info(f"🚀 [EVOLUTION_SERVICE] Manually triggering evolution cycle with context: {context}")
            
            result = await self.evolution_engine.analyze_and_evolve(self.current_performance)
            
            if result:
                self.total_evolution_cycles += 1
                if result.deployed:
                    self.successful_improvements += 1
                else:
                    self.failed_attempts += 1
                
                self.last_evolution_time = datetime.now()
                
                return {
                    "success": True,
                    "evolution_result": {
                        "modification_id": result.modification_plan.id,
                        "target_file": result.modification_plan.target_file,
                        "deployed": result.deployed,
                        "improvement": result.actual_improvement,
                        "safety_passed": result.safety_passed
                    }
                }
            else:
                return {"success": True, "message": "No evolution opportunities found"}
                
        except Exception as e:
            logging.error(f"❌ [EVOLUTION_SERVICE] Manual evolution trigger failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _trigger_evolution_cycle(self):
        """Internal method to trigger evolution cycle"""
        result = await self.trigger_evolution_manually("Automatic evolution trigger")
        if result["success"]:
            logging.info("🔄 [EVOLUTION_SERVICE] Automatic evolution cycle completed")
        else:
            logging.warning(f"⚠️ [EVOLUTION_SERVICE] Automatic evolution cycle failed: {result.get('error')}")
    
    def _should_trigger_evolution(self) -> bool:
        """Determine if evolution should be triggered automatically"""
        
        # Don't trigger if not enough time has passed
        if self.last_evolution_time:
            time_since_last = datetime.now() - self.last_evolution_time
            if time_since_last.total_seconds() < self.evolution_interval:
                return False
        
        # Don't trigger if we don't have enough performance data
        if len(self.performance_history) < 5:
            return False
        
        # Check for performance degradation
        recent_performance = self.performance_history[-5:]
        avg_decision_time = sum(p.decision_time for p in recent_performance) / len(recent_performance)
        avg_success_rate = sum(p.success_rate for p in recent_performance) / len(recent_performance)
        
        # Trigger if performance is below thresholds
        if avg_decision_time > 3.0 or avg_success_rate < 0.8:
            logging.info(f"🎯 [EVOLUTION_SERVICE] Performance degradation detected - triggering evolution")
            return True
        
        return False
    
    async def enable_auto_evolution(self, interval: int = 300) -> Dict[str, Any]:
        """Enable automatic evolution with specified interval"""
        if not self.evolution_enabled:
            return {"success": False, "error": "Evolution service not initialized"}
        
        self.auto_evolution_enabled = True
        self.evolution_interval = interval
        
        logging.info(f"🔄 [EVOLUTION_SERVICE] Auto-evolution enabled with {interval}s interval")
        return {"success": True, "auto_evolution_enabled": True, "interval": interval}
    
    async def disable_auto_evolution(self) -> Dict[str, Any]:
        """Disable automatic evolution"""
        self.auto_evolution_enabled = False
        
        logging.info("⏸️ [EVOLUTION_SERVICE] Auto-evolution disabled")
        return {"success": True, "auto_evolution_enabled": False}
    
    async def get_evolution_status(self) -> Dict[str, Any]:
        """Get current evolution service status"""
        
        # Calculate performance trends
        performance_trend = "stable"
        if len(self.performance_history) >= 2:
            recent = self.performance_history[-1]
            previous = self.performance_history[-2]
            
            if recent.decision_time > previous.decision_time * 1.1:
                performance_trend = "degrading"
            elif recent.decision_time < previous.decision_time * 0.9:
                performance_trend = "improving"
        
        status = {
            "evolution_enabled": self.evolution_enabled,
            "auto_evolution_enabled": self.auto_evolution_enabled,
            "evolution_interval": self.evolution_interval,
            "last_evolution_time": self.last_evolution_time.isoformat() if self.last_evolution_time else None,
            "total_evolution_cycles": self.total_evolution_cycles,
            "successful_improvements": self.successful_improvements,
            "failed_attempts": self.failed_attempts,
            "success_rate": (self.successful_improvements / max(self.total_evolution_cycles, 1)) * 100,
            "performance_data_points": len(self.performance_history),
            "current_performance": {
                "decision_time": self.current_performance.decision_time if self.current_performance else None,
                "success_rate": self.current_performance.success_rate if self.current_performance else None,
                "trend": performance_trend
            }
        }
        
        # Add engine statistics
        if self.evolution_engine:
            engine_stats = self.evolution_engine.get_evolution_stats()
            status["engine_stats"] = engine_stats
        
        if self.dgm_engine:
            dgm_stats = self.dgm_engine.get_engine_stats()
            status["dgm_stats"] = dgm_stats
        
        return status
    
    async def get_performance_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent performance history"""
        
        recent_history = self.performance_history[-limit:]
        
        return [
            {
                "timestamp": p.timestamp.isoformat(),
                "decision_time": p.decision_time,
                "success_rate": p.success_rate,
                "memory_usage": p.memory_usage,
                "error_count": p.error_count,
                "iteration_count": p.iteration_count
            }
            for p in recent_history
        ]
    
    async def analyze_code_performance(self, target_file: str = None) -> Dict[str, Any]:
        """Trigger code analysis and return results"""
        if not self.dgm_engine:
            return {"success": False, "error": "DGM engine not initialized"}
        
        try:
            analysis_results = await self.dgm_engine.analyze_code_performance(target_file)
            
            formatted_results = []
            for result in analysis_results:
                formatted_results.append({
                    "file_path": result.file_path,
                    "complexity_score": result.complexity_score,
                    "performance_bottlenecks": result.performance_bottlenecks,
                    "improvement_opportunities": result.improvement_opportunities,
                    "risk_assessment": result.risk_assessment,
                    "current_metrics": result.current_metrics
                })
            
            return {
                "success": True,
                "analysis_results": formatted_results,
                "files_analyzed": len(formatted_results)
            }
            
        except Exception as e:
            logging.error(f"❌ [EVOLUTION_SERVICE] Code analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_evolution_memory(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Query Cognee evolution memory"""
        if not self.evolution_engine:
            return {"success": False, "error": "Evolution engine not initialized"}
        
        try:
            results = await self.evolution_engine._search_cognee(query, max_results)
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logging.error(f"❌ [EVOLUTION_SERVICE] Memory query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get overall service statistics"""
        return {
            "service_initialized": self.evolution_enabled,
            "auto_evolution_enabled": self.auto_evolution_enabled,
            "evolution_interval": self.evolution_interval,
            "total_cycles": self.total_evolution_cycles,
            "success_rate": (self.successful_improvements / max(self.total_evolution_cycles, 1)) * 100,
            "performance_history_size": len(self.performance_history),
            "cognee_url": self.cognee_url,
            "agent_dir": self.agent_dir
        }

# Global evolution service instance
evolution_service = None

async def get_evolution_service() -> Optional[EvolutionService]:
    """Get the global evolution service instance"""
    global evolution_service
    
    if evolution_service is None:
        cognee_url = os.getenv("COGNEE_URL")
        cognee_api_key = os.getenv("COGNEE_API_KEY") 
        
        if cognee_url and cognee_api_key:
            evolution_service = EvolutionService(cognee_url, cognee_api_key)
            await evolution_service.initialize()
            logging.info("✅ [EVOLUTION_SERVICE] Global service instance created")
        else:
            logging.warning("⚠️ [EVOLUTION_SERVICE] Missing Cognee configuration")
    
    return evolution_service

async def collect_autogen_performance_data(agent_metrics: Dict[str, Any]) -> bool:
    """Utility function to collect performance data from AutoGen agents"""
    service = await get_evolution_service()
    if service:
        return await service.collect_performance_data(agent_metrics)
    return False 