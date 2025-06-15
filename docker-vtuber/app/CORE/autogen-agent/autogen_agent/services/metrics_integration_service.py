"""
📊 Metrics Integration Service - Comprehensive Performance & Goal Tracking

This service integrates performance monitoring, goal tracking, and memory storage:
- Real-time performance data collection from agent operations
- Goal progress correlation with performance metrics
- Cognee integration for historical pattern analysis
- Evolution triggers based on performance and goal status
- Comprehensive metrics reporting and analytics

Integration Architecture:
- Performance Data → Goal Progress → Cognee Memory → Evolution Triggers
- Real-time decision metrics → Goal achievement tracking → Historical learning
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..services.cognee_direct_service import CogneeDirectService
from ..services.evolution_service import EvolutionService
from ..services.goal_management_service import GoalManagementService, get_goal_management_service

@dataclass
class MetricsSnapshot:
    """Real-time metrics snapshot for correlation analysis"""
    timestamp: datetime
    iteration_count: int
    decision_time: float
    success_rate: float
    memory_usage: float
    error_count: int
    tool_used: str
    context_hash: str
    
    # Goal-related metrics
    active_goals_count: int
    goals_progress_avg: float
    high_priority_goals_count: int
    overdue_goals_count: int
    
    # Performance scoring
    overall_performance_score: float
    trend_direction: str
    improvement_opportunities: List[str]

class MetricsIntegrationService:
    """
    Comprehensive metrics integration and correlation system
    """
    
    def __init__(self, cognee_service: CogneeDirectService, evolution_service: EvolutionService):
        self.cognee_service = cognee_service
        self.evolution_service = evolution_service
        self.goal_service = None  # Will be initialized lazily
        
        # Metrics storage
        self.metrics_history: List[MetricsSnapshot] = []
        self.performance_baselines: Dict[str, float] = {}
        
        # Correlation patterns
        self.goal_performance_correlations: Dict[str, List[float]] = {}
        self.trigger_patterns: Dict[str, int] = {}
        
        # Configuration
        self.metrics_collection_interval = 30  # seconds
        self.correlation_analysis_interval = 300  # 5 minutes
        self.memory_storage_interval = 600  # 10 minutes
        
        logging.info("📊 [METRICS_INTEGRATION] Service initialized")
    
    async def initialize(self) -> bool:
        """Initialize metrics integration service"""
        try:
            # Get goal management service
            self.goal_service = await get_goal_management_service()
            
            # Establish performance baselines
            await self._establish_baselines()
            
            # Load historical patterns from Cognee
            await self._load_historical_patterns()
            
            logging.info("✅ [METRICS_INTEGRATION] Service initialized successfully")
            return True
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Initialization failed: {e}")
            return False
    
    async def collect_real_time_metrics(self, agent_performance_data: Dict[str, Any]) -> MetricsSnapshot:
        """
        Collect comprehensive real-time metrics combining performance and goal data
        """
        try:
            # Extract agent performance data
            timestamp = datetime.now()
            iteration_count = agent_performance_data.get("iteration", 0)
            decision_time = agent_performance_data.get("decision_time", 2.5)
            success_rate = agent_performance_data.get("success_rate", 1.0)
            memory_usage = agent_performance_data.get("memory_usage", 85.0)
            error_count = agent_performance_data.get("error_count", 0)
            tool_used = agent_performance_data.get("tool_used", "unknown")
            context_hash = agent_performance_data.get("context_hash", f"ctx_{iteration_count}")
            
            # Get goal-related metrics
            goal_metrics = await self._collect_goal_metrics()
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(
                decision_time, success_rate, error_count, memory_usage
            )
            
            # Determine trend direction
            trend_direction = self._analyze_trend_direction()
            
            # Identify improvement opportunities
            improvement_opportunities = self._identify_improvement_opportunities(
                decision_time, success_rate, error_count, goal_metrics
            )
            
            # Create metrics snapshot
            snapshot = MetricsSnapshot(
                timestamp=timestamp,
                iteration_count=iteration_count,
                decision_time=decision_time,
                success_rate=success_rate,
                memory_usage=memory_usage,
                error_count=error_count,
                tool_used=tool_used,
                context_hash=context_hash,
                
                # Goal metrics
                active_goals_count=goal_metrics["active_count"],
                goals_progress_avg=goal_metrics["avg_progress"],
                high_priority_goals_count=goal_metrics["high_priority_count"],
                overdue_goals_count=goal_metrics["overdue_count"],
                
                # Analysis
                overall_performance_score=performance_score,
                trend_direction=trend_direction,
                improvement_opportunities=improvement_opportunities
            )
            
            # Store snapshot
            self.metrics_history.append(snapshot)
            
            # Keep history manageable
            if len(self.metrics_history) > 200:
                self.metrics_history = self.metrics_history[-100:]
            
            # Update goal progress based on performance
            await self._update_goal_progress_from_metrics(snapshot)
            
            # Check for evolution triggers
            await self._check_evolution_triggers(snapshot)
            
            logging.debug(f"📊 [METRICS_INTEGRATION] Collected metrics: iteration={iteration_count}, score={performance_score:.1f}")
            return snapshot
            
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Metrics collection failed: {e}")
            raise
    
    async def store_metrics_in_memory(self, snapshot: MetricsSnapshot) -> bool:
        """
        Store metrics snapshot in Cognee for historical analysis
        """
        try:
            # Create comprehensive metrics summary for Cognee
            metrics_summary = f"""
Performance Metrics Snapshot - Iteration #{snapshot.iteration_count}

🕒 Timestamp: {snapshot.timestamp.isoformat()}
⚡ Performance Score: {snapshot.overall_performance_score:.1f}/100
📈 Trend: {snapshot.trend_direction}

🚀 Agent Performance:
- Decision Time: {snapshot.decision_time:.2f}s
- Success Rate: {snapshot.success_rate:.1%}
- Memory Usage: {snapshot.memory_usage:.1f}MB
- Error Count: {snapshot.error_count}
- Tool Used: {snapshot.tool_used}

🎯 Goal Status:
- Active Goals: {snapshot.active_goals_count}
- Average Progress: {snapshot.goals_progress_avg:.1f}%
- High Priority Goals: {snapshot.high_priority_goals_count}
- Overdue Goals: {snapshot.overdue_goals_count}

🔍 Analysis:
- Context Hash: {snapshot.context_hash}
- Improvement Opportunities: {', '.join(snapshot.improvement_opportunities[:3])}

📊 Performance Classification:
{self._classify_performance(snapshot.overall_performance_score)}

🎯 Goal-Performance Correlation:
{self._analyze_goal_performance_correlation(snapshot)}
"""
            
            # Store in Cognee
            await self.cognee_service.add_data([metrics_summary])
            
            logging.info(f"💾 [METRICS_INTEGRATION] Stored metrics snapshot for iteration #{snapshot.iteration_count}")
            return True
            
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Metrics storage failed: {e}")
            return False
    
    async def generate_comprehensive_report(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """
        Generate comprehensive metrics and goal correlation report
        """
        try:
            # Filter metrics by timeframe
            cutoff_time = datetime.now() - timedelta(hours=timeframe_hours)
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
            
            if not recent_metrics:
                return self._get_baseline_report(timeframe_hours)
            
            # Calculate aggregate metrics
            avg_decision_time = sum(m.decision_time for m in recent_metrics) / len(recent_metrics)
            avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
            avg_performance_score = sum(m.overall_performance_score for m in recent_metrics) / len(recent_metrics)
            total_errors = sum(m.error_count for m in recent_metrics)
            
            # Goal correlation analysis
            goal_correlation = await self._analyze_goal_performance_correlation_detailed(recent_metrics)
            
            # Trend analysis
            trend_analysis = self._analyze_performance_trends(recent_metrics)
            
            # Tool effectiveness analysis
            tool_effectiveness = self._analyze_tool_effectiveness(recent_metrics)
            
            # Evolution triggers analysis
            evolution_analysis = await self._analyze_evolution_patterns(recent_metrics)
            
            # Generate improvement recommendations
            recommendations = self._generate_improvement_recommendations(recent_metrics, goal_correlation)
            
            report = {
                "report_type": "comprehensive_metrics_and_goals",
                "generated_at": datetime.now().isoformat(),
                "timeframe_hours": timeframe_hours,
                "data_points": len(recent_metrics),
                
                # Core Performance Metrics
                "performance_summary": {
                    "average_decision_time": avg_decision_time,
                    "average_success_rate": avg_success_rate,
                    "overall_performance_score": avg_performance_score,
                    "total_errors": total_errors,
                    "performance_grade": self._get_performance_grade(avg_performance_score)
                },
                
                # Goal Integration Analysis
                "goal_performance_correlation": goal_correlation,
                
                # Trend Analysis
                "trend_analysis": trend_analysis,
                
                # Tool Effectiveness
                "tool_effectiveness": tool_effectiveness,
                
                # Evolution Integration
                "evolution_analysis": evolution_analysis,
                
                # Recommendations
                "recommendations": recommendations,
                
                # Key Insights
                "key_insights": self._generate_key_insights(recent_metrics, goal_correlation),
                
                # Performance Classification
                "performance_classification": {
                    "excellent": len([m for m in recent_metrics if m.overall_performance_score >= 90]),
                    "good": len([m for m in recent_metrics if 70 <= m.overall_performance_score < 90]),
                    "fair": len([m for m in recent_metrics if 50 <= m.overall_performance_score < 70]),
                    "poor": len([m for m in recent_metrics if m.overall_performance_score < 50])
                }
            }
            
            logging.info(f"📈 [METRICS_INTEGRATION] Generated comprehensive report: {timeframe_hours}h, score={avg_performance_score:.1f}")
            return report
            
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Report generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_performance_patterns(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Query Cognee for performance and goal patterns
        """
        try:
            # Search for performance patterns
            search_query = f"performance metrics goal correlation pattern: {query}"
            results = await self.cognee_service.search(search_query, limit=limit)
            
            # Analyze patterns from results
            patterns = []
            correlations = []
            
            for result in results:
                content = result.get("content", "")
                
                # Extract performance scores
                if "Performance Score:" in content:
                    score_match = content.split("Performance Score:")[1].split("/")[0].strip()
                    try:
                        score = float(score_match)
                        patterns.append({"type": "performance_score", "value": score, "context": content[:200]})
                    except:
                        pass
                
                # Extract goal correlations
                if "Goal-Performance Correlation:" in content:
                    correlation_text = content.split("Goal-Performance Correlation:")[1].split("\n")[0]
                    correlations.append({"text": correlation_text.strip(), "context": content[:200]})
            
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "patterns_found": len(patterns),
                "correlations_found": len(correlations),
                "performance_patterns": patterns,
                "goal_correlations": correlations,
                "raw_results": results
            }
            
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Pattern query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _collect_goal_metrics(self) -> Dict[str, Any]:
        """Collect current goal-related metrics"""
        if not self.goal_service:
            return {"active_count": 0, "avg_progress": 0, "high_priority_count": 0, "overdue_count": 0}
        
        try:
            # Get all active goals
            goals = await self.goal_service.get_current_goals()
            
            if not goals:
                return {"active_count": 0, "avg_progress": 0, "high_priority_count": 0, "overdue_count": 0}
            
            # Calculate metrics
            active_count = len(goals)
            avg_progress = sum(g.progress_percentage for g in goals) / len(goals)
            high_priority_count = len([g for g in goals if g.priority >= 8])
            
            # Count overdue goals
            now = datetime.now()
            overdue_count = len([g for g in goals if g.time_bound_deadline < now and g.progress_percentage < 100])
            
            return {
                "active_count": active_count,
                "avg_progress": avg_progress,
                "high_priority_count": high_priority_count,
                "overdue_count": overdue_count
            }
            
        except Exception as e:
            logging.error(f"❌ [METRICS_INTEGRATION] Goal metrics collection failed: {e}")
            return {"active_count": 0, "avg_progress": 0, "high_priority_count": 0, "overdue_count": 0}
    
    def _calculate_performance_score(self, decision_time: float, success_rate: float, 
                                   error_count: int, memory_usage: float) -> float:
        """Calculate overall performance score (0-100)"""
        # Weight different metrics
        time_score = max(0, 100 - (decision_time - 1.0) * 20)  # 1s = 100, 6s = 0
        success_score = success_rate * 100
        error_score = max(0, 100 - error_count * 15)  # 0 errors = 100, 7 errors = 0
        memory_score = max(0, 100 - max(0, memory_usage - 50) * 2)  # 50MB = 100, 100MB = 0
        
        # Weighted average
        weights = {"time": 0.3, "success": 0.4, "error": 0.2, "memory": 0.1}
        overall_score = (
            time_score * weights["time"] +
            success_score * weights["success"] +
            error_score * weights["error"] +
            memory_score * weights["memory"]
        )
        
        return max(0.0, min(100.0, overall_score))
    
    def _classify_performance(self, score: float) -> str:
        """Classify performance score into categories"""
        if score >= 90:
            return "🌟 EXCELLENT - Optimal autonomous operation"
        elif score >= 70:
            return "✅ GOOD - Solid performance with minor optimization opportunities"
        elif score >= 50:
            return "⚠️ FAIR - Functional but needs improvement"
        else:
            return "❌ POOR - Significant optimization required"
    
    def _analyze_goal_performance_correlation(self, snapshot: MetricsSnapshot) -> str:
        """Analyze correlation between goals and performance"""
        if snapshot.active_goals_count == 0:
            return "No active goals to correlate with performance"
        
        if snapshot.goals_progress_avg > 75 and snapshot.overall_performance_score > 80:
            return "Strong positive correlation: High goal progress with excellent performance"
        elif snapshot.goals_progress_avg < 25 and snapshot.overall_performance_score < 60:
            return "Concerning correlation: Low goal progress with poor performance"
        elif snapshot.overdue_goals_count > 0:
            return f"Performance impact from {snapshot.overdue_goals_count} overdue goals"
        else:
            return "Moderate correlation: Goals and performance are reasonably aligned"
    
    def _get_performance_grade(self, score: float) -> str:
        """Get letter grade for performance score"""
        if score >= 95: return "A+"
        elif score >= 90: return "A"
        elif score >= 85: return "A-"
        elif score >= 80: return "B+"
        elif score >= 75: return "B"
        elif score >= 70: return "B-"
        elif score >= 65: return "C+"
        elif score >= 60: return "C"
        elif score >= 55: return "C-"
        elif score >= 50: return "D"
        else: return "F"
    
    async def _establish_baselines(self):
        """Establish performance baselines"""
        self.performance_baselines = {
            "decision_time": 2.5,
            "success_rate": 0.8,
            "error_count": 0.2,
            "memory_usage": 85.0,
            "performance_score": 70.0
        }
        logging.info("📊 [METRICS_INTEGRATION] Performance baselines established")
    
    async def _load_historical_patterns(self):
        """Load historical patterns from Cognee"""
        # Placeholder for loading historical correlation patterns
        logging.info("🔍 [METRICS_INTEGRATION] Historical patterns loaded")

# Global service instance
_metrics_integration_service: Optional[MetricsIntegrationService] = None

async def get_metrics_integration_service() -> Optional[MetricsIntegrationService]:
    """Get or create the global metrics integration service instance"""
    global _metrics_integration_service
    
    if _metrics_integration_service is None:
        from .cognee_direct_service import get_cognee_direct_service
        from .evolution_service import get_evolution_service
        
        cognee_service = await get_cognee_direct_service()
        evolution_service = await get_evolution_service()
        
        if cognee_service and evolution_service:
            _metrics_integration_service = MetricsIntegrationService(cognee_service, evolution_service)
            await _metrics_integration_service.initialize()
    
    return _metrics_integration_service 