"""
🎯 Goal Management Service - Autonomous Goal Setting & Tracking

This service provides comprehensive goal management for the autonomous agent:
- SMART goal definition and parsing
- Performance metrics tracking and correlation
- Cognee integration for goal memory and learning
- Evolution-driven goal achievement strategies
- Real-time progress monitoring and adaptive metrics

Integration Points:
- Cognee: Historical goal patterns and success strategies
- Evolution Engine: Goal-driven performance improvements  
- Performance Analytics: Metrics tracking and trend analysis
- MCP Tools: Goal management via development interface
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from ..services.cognee_direct_service import CogneeDirectService
from ..services.evolution_service import EvolutionService

class GoalStatus(Enum):
    """Goal lifecycle status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"
    PAUSED = "paused"
    OBSOLETE = "obsolete"

class GoalCategory(Enum):
    """Goal categorization for better organization"""
    PERFORMANCE = "performance"  # Speed, efficiency, resource usage
    CAPABILITY = "capability"    # New features, tools, abilities
    LEARNING = "learning"        # Knowledge acquisition, pattern recognition
    INTERACTION = "interaction"  # User engagement, communication quality
    TECHNICAL = "technical"      # Code quality, architecture improvements
    AUTONOMOUS = "autonomous"    # Self-improvement, evolution capabilities

@dataclass
class GoalMetrics:
    """Specific metrics for measuring goal progress"""
    metric_name: str
    current_value: float
    target_value: float
    unit: str
    measurement_method: str
    baseline_value: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    last_measured: datetime
    confidence_score: float  # How confident we are in this measurement

@dataclass
class Goal:
    """Complete goal definition with SMART criteria"""
    id: str
    title: str
    description: str
    category: GoalCategory
    status: GoalStatus
    priority: int  # 1-10, 10 being highest priority
    
    # SMART criteria
    specific_details: str      # Specific: Clear, well-defined outcome
    measurable_metrics: List[GoalMetrics]  # Measurable: Quantifiable success criteria
    achievable_plan: List[str]  # Achievable: Concrete steps to reach goal
    relevant_justification: str  # Relevant: Why this goal matters for the agent
    time_bound_deadline: datetime  # Time-bound: Clear deadline
    
    # Progress tracking
    progress_percentage: float
    milestones: List[Dict[str, Any]]
    success_criteria: List[str]
    failure_conditions: List[str]
    
    # Context and relationships
    parent_goal_id: Optional[str]  # For hierarchical goals
    dependent_goal_ids: List[str]  # Goals that depend on this one
    blocking_goal_ids: List[str]   # Goals that block this one
    
    # Historical tracking
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    
    # Learning integration
    cognee_context_id: str  # Reference to Cognee knowledge
    evolution_triggers: List[str]  # What evolution cycles this goal should trigger
    learned_strategies: List[Dict[str, Any]]  # Successful approaches from memory

class GoalManagementService:
    """
    Comprehensive goal management with AI-driven insights
    """
    
    def __init__(self, cognee_service: CogneeDirectService, evolution_service: EvolutionService):
        self.cognee_service = cognee_service
        self.evolution_service = evolution_service
        
        # Goal storage (in-memory with Cognee persistence)
        self.active_goals: Dict[str, Goal] = {}
        self.goal_history: List[Goal] = []
        
        # Metrics tracking
        self.metrics_history: Dict[str, List[GoalMetrics]] = {}
        self.baseline_performance: Dict[str, float] = {}
        
        # Goal achievement patterns
        self.success_patterns: Dict[str, List[str]] = {}
        self.failure_patterns: Dict[str, List[str]] = {}
        
        # Configuration
        self.goal_evaluation_interval = 300  # 5 minutes
        self.last_evaluation_time = None
        
        logging.info("🎯 [GOAL_MANAGEMENT] Service initialized")
    
    async def initialize(self) -> bool:
        """Initialize goal management service"""
        try:
            # Load existing goals from Cognee
            await self._load_goals_from_memory()
            
            # Establish baseline performance metrics
            await self._establish_baseline_metrics()
            
            logging.info("✅ [GOAL_MANAGEMENT] Service initialized successfully")
            return True
        except Exception as e:
            logging.error(f"❌ [GOAL_MANAGEMENT] Initialization failed: {e}")
            return False
    
    async def define_goal(self, natural_language_goal: str, priority: int = 5) -> Goal:
        """
        Define a new goal from natural language description using AI enhancement
        """
        try:
            logging.info(f"🎯 [GOAL_MANAGEMENT] Defining new goal: {natural_language_goal[:100]}...")
            
            # Use Cognee to enhance goal definition with SMART criteria
            goal_analysis = await self._analyze_goal_with_ai(natural_language_goal)
            
            # Generate unique goal ID
            goal_id = f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(natural_language_goal.encode()).hexdigest()[:8]}"
            
            # Create comprehensive goal object
            goal = Goal(
                id=goal_id,
                title=goal_analysis["title"],
                description=goal_analysis["description"],
                category=GoalCategory(goal_analysis["category"]),
                status=GoalStatus.PENDING,
                priority=priority,
                
                # SMART criteria from AI analysis
                specific_details=goal_analysis["specific_details"],
                measurable_metrics=self._create_metrics_from_analysis(goal_analysis["metrics"]),
                achievable_plan=goal_analysis["achievable_steps"],
                relevant_justification=goal_analysis["relevance"],
                time_bound_deadline=datetime.now() + timedelta(days=goal_analysis["estimated_days"]),
                
                # Initialize progress tracking
                progress_percentage=0.0,
                milestones=goal_analysis["milestones"],
                success_criteria=goal_analysis["success_criteria"],
                failure_conditions=goal_analysis["failure_conditions"],
                
                # Context
                parent_goal_id=None,
                dependent_goal_ids=[],
                blocking_goal_ids=[],
                
                # Timestamps
                created_at=datetime.now(),
                updated_at=datetime.now(),
                started_at=None,
                completed_at=None,
                estimated_completion=datetime.now() + timedelta(days=goal_analysis["estimated_days"]),
                
                # Learning integration
                cognee_context_id=f"goal_context_{goal_id}",
                evolution_triggers=goal_analysis["evolution_triggers"],
                learned_strategies=[]
            )
            
            # Store in active goals
            self.active_goals[goal_id] = goal
            
            # Store in Cognee for institutional memory
            await self._store_goal_in_cognee(goal)
            
            logging.info(f"✅ [GOAL_MANAGEMENT] Goal defined successfully: {goal_id} - {goal.title}")
            return goal
            
        except Exception as e:
            logging.error(f"❌ [GOAL_MANAGEMENT] Goal definition failed: {e}")
            raise
    
    async def update_goal_progress(self, goal_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Update goal progress based on agent performance and actions
        """
        try:
            if goal_id not in self.active_goals:
                logging.warning(f"⚠️ [GOAL_MANAGEMENT] Goal not found: {goal_id}")
                return False
            
            goal = self.active_goals[goal_id]
            
            # Calculate new progress based on metrics
            new_progress = await self._calculate_progress_update(goal, progress_data)
            
            # Update metrics
            updated_metrics = await self._update_goal_metrics(goal, progress_data)
            
            # Check milestone achievements
            milestone_updates = await self._check_milestone_progress(goal, progress_data)
            
            # Update goal object
            goal.progress_percentage = new_progress
            goal.measurable_metrics = updated_metrics
            goal.milestones = milestone_updates
            goal.updated_at = datetime.now()
            
            # Check for goal completion
            if new_progress >= 100.0:
                await self._mark_goal_achieved(goal_id)
            elif any(self._check_failure_condition(goal, condition) for condition in goal.failure_conditions):
                await self._mark_goal_failed(goal_id)
            
            # Store updated progress in Cognee
            await self._store_progress_in_cognee(goal, progress_data)
            
            logging.info(f"📊 [GOAL_MANAGEMENT] Progress updated for {goal_id}: {new_progress:.1f}%")
            return True
            
        except Exception as e:
            logging.error(f"❌ [GOAL_MANAGEMENT] Progress update failed for {goal_id}: {e}")
            return False
    
    async def get_current_goals(self, status_filter: Optional[GoalStatus] = None) -> List[Goal]:
        """Get current goals with optional status filtering"""
        goals = list(self.active_goals.values())
        
        if status_filter:
            goals = [g for g in goals if g.status == status_filter]
        
        # Sort by priority and creation date
        goals.sort(key=lambda g: (-g.priority, g.created_at))
        
        return goals
    
    async def get_next_priority_goal(self) -> Optional[Goal]:
        """Get the highest priority goal that's ready to work on"""
        pending_goals = await self.get_current_goals(GoalStatus.PENDING)
        in_progress_goals = await self.get_current_goals(GoalStatus.IN_PROGRESS)
        
        # Prioritize in-progress goals first, then pending
        candidate_goals = in_progress_goals + pending_goals
        
        for goal in candidate_goals:
            # Check if blocking goals are resolved
            if await self._are_blocking_goals_resolved(goal):
                return goal
        
        return None
    
    async def generate_performance_metrics(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """
        Generate comprehensive performance metrics for goal tracking
        """
        try:
            # Get performance data from evolution service
            evolution_status = await self.evolution_service.get_evolution_status()
            performance_history = await self.evolution_service.get_performance_history(limit=50)
            
            # Calculate metrics
            current_time = datetime.now()
            timeframe_start = current_time - timedelta(hours=timeframe_hours)
            
            # Filter recent performance data
            recent_performance = [
                p for p in performance_history 
                if datetime.fromisoformat(p["timestamp"]) >= timeframe_start
            ]
            
            if not recent_performance:
                logging.warning("⚠️ [GOAL_MANAGEMENT] No recent performance data available")
                return self._get_baseline_metrics()
            
            # Calculate comprehensive metrics
            metrics = {
                "timeframe": f"{timeframe_hours}h",
                "data_points": len(recent_performance),
                
                # Core performance metrics
                "average_decision_time": sum(p["decision_time"] for p in recent_performance) / len(recent_performance),
                "average_success_rate": sum(p["success_rate"] for p in recent_performance) / len(recent_performance),
                "total_iterations": recent_performance[-1]["iteration_count"] if recent_performance else 0,
                "error_rate": sum(p["error_count"] for p in recent_performance) / len(recent_performance),
                
                # Trend analysis
                "decision_time_trend": self._calculate_trend([p["decision_time"] for p in recent_performance]),
                "success_rate_trend": self._calculate_trend([p["success_rate"] for p in recent_performance]),
                
                # Evolution metrics
                "evolution_cycles": evolution_status.get("total_evolution_cycles", 0),
                "evolution_success_rate": evolution_status.get("success_rate", 0),
                "evolution_enabled": evolution_status.get("evolution_enabled", False),
                
                # Goal-specific metrics
                "active_goals_count": len(self.active_goals),
                "goals_in_progress": len([g for g in self.active_goals.values() if g.status == GoalStatus.IN_PROGRESS]),
                "goals_pending": len([g for g in self.active_goals.values() if g.status == GoalStatus.PENDING]),
                
                # Performance assessment
                "performance_score": self._calculate_overall_performance_score(recent_performance),
                "improvement_opportunities": await self._identify_improvement_opportunities(recent_performance),
                
                "timestamp": current_time.isoformat()
            }
            
            logging.info(f"📊 [GOAL_MANAGEMENT] Generated metrics for {timeframe_hours}h: score={metrics['performance_score']:.2f}")
            return metrics
            
        except Exception as e:
            logging.error(f"❌ [GOAL_MANAGEMENT] Metrics generation failed: {e}")
            return self._get_baseline_metrics()
    
    async def query_goal_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query Cognee for goal-related historical insights
        """
        try:
            # Search for goal-related memories
            search_query = f"goal achievement strategy success pattern: {query}"
            results = await self.cognee_service.search(search_query, limit=limit)
            
            if not results:
                logging.info(f"🔍 [GOAL_MANAGEMENT] No goal memories found for: {query}")
                return []
            
            # Format results for goal context
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "relevance_score": result.get("relevance_score", 0.0),
                    "source": result.get("source", "cognee_goal_memory"),
                    "goal_context": self._extract_goal_context(result.get("content", ""))
                })
            
            logging.info(f"🧠 [GOAL_MANAGEMENT] Found {len(formatted_results)} goal memories for: {query}")
            return formatted_results
            
        except Exception as e:
            logging.error(f"❌ [GOAL_MANAGEMENT] Goal memory query failed: {e}")
            return []
    
    async def _analyze_goal_with_ai(self, natural_language_goal: str) -> Dict[str, Any]:
        """
        Use Cognee to analyze and enhance goal definition with SMART criteria
        """
        analysis_prompt = f"""
Analyze this goal and create SMART criteria: "{natural_language_goal}"

For an autonomous AI agent system, provide:

SPECIFIC: What exactly should be achieved?
MEASURABLE: What metrics can track progress? (decision_time, success_rate, error_count, etc.)
ACHIEVABLE: What concrete steps are needed?
RELEVANT: Why is this important for the agent?
TIME-BOUND: How many days to achieve this?

Also provide:
- Goal category (performance, capability, learning, interaction, technical, autonomous)
- Success criteria (clear conditions for completion)
- Failure conditions (clear conditions for failure)
- Milestones (progress checkpoints)
- Evolution triggers (what system improvements this goal should drive)

Return specific, actionable analysis for autonomous AI agent evolution.
"""
        
        # Query Cognee for similar goals and best practices
        similar_goals = await self.cognee_service.search(f"goal strategy pattern: {natural_language_goal[:50]}", limit=3)
        
        if similar_goals:
            analysis_prompt += f"\n\nHistorical context from similar goals:\n{json.dumps(similar_goals[:2], indent=2)}"
        
        # Store analysis request in Cognee for learning
        await self.cognee_service.add_data([analysis_prompt])
        
        # For now, return structured analysis (in production, this would use LLM)
        return self._generate_smart_analysis(natural_language_goal)
    
    def _generate_smart_analysis(self, goal_text: str) -> Dict[str, Any]:
        """
        Generate SMART analysis for the goal (placeholder for LLM integration)
        """
        # Analyze goal text for key patterns
        goal_lower = goal_text.lower()
        
        # Determine category
        if any(word in goal_lower for word in ["faster", "speed", "time", "performance"]):
            category = "performance"
        elif any(word in goal_lower for word in ["learn", "understand", "knowledge"]):
            category = "learning"
        elif any(word in goal_lower for word in ["feature", "capability", "tool"]):
            category = "capability"
        elif any(word in goal_lower for word in ["code", "architecture", "quality"]):
            category = "technical"
        elif any(word in goal_lower for word in ["autonomous", "evolution", "improve"]):
            category = "autonomous"
        else:
            category = "interaction"
        
        # Generate structured analysis
        return {
            "title": goal_text[:50] + "..." if len(goal_text) > 50 else goal_text,
            "description": f"Autonomous agent goal: {goal_text}",
            "category": category,
            "specific_details": f"Achieve measurable improvement in {category} domain through systematic optimization",
            "metrics": [
                {"name": "decision_time", "target": 2.0, "unit": "seconds"},
                {"name": "success_rate", "target": 0.95, "unit": "percentage"},
                {"name": "error_count", "target": 0, "unit": "count"}
            ],
            "achievable_steps": [
                "Analyze current performance baseline",
                "Identify specific improvement opportunities", 
                "Implement targeted optimizations",
                "Measure and validate improvements"
            ],
            "relevance": f"This goal enhances agent {category} capabilities for better autonomous operation",
            "estimated_days": 7,
            "success_criteria": [
                "All target metrics achieved",
                "Improvements sustained for 24+ hours",
                "No negative side effects detected"
            ],
            "failure_conditions": [
                "No progress after 50% of timeline",
                "Performance degradation detected",
                "Critical errors introduced"
            ],
            "milestones": [
                {"name": "Baseline Established", "percentage": 20},
                {"name": "Improvement Plan Created", "percentage": 40},
                {"name": "Initial Implementation", "percentage": 70},
                {"name": "Validation Complete", "percentage": 100}
            ],
            "evolution_triggers": [
                "performance_degradation",
                "goal_progress_update",
                "milestone_achievement"
            ]
        }
    
    def _create_metrics_from_analysis(self, metrics_data: List[Dict]) -> List[GoalMetrics]:
        """Create GoalMetrics objects from analysis data"""
        metrics = []
        for metric_data in metrics_data:
            metrics.append(GoalMetrics(
                metric_name=metric_data["name"],
                current_value=0.0,  # Will be updated with first measurement
                target_value=metric_data["target"],
                unit=metric_data["unit"],
                measurement_method="performance_monitoring",
                baseline_value=0.0,  # Will be established
                trend_direction="stable",
                last_measured=datetime.now(),
                confidence_score=0.8
            ))
        return metrics
    
    async def _calculate_progress_update(self, goal: Goal, progress_data: Dict[str, Any]) -> float:
        """Calculate new progress percentage based on metrics achievement"""
        total_progress = 0.0
        metric_count = len(goal.measurable_metrics)
        
        if metric_count == 0:
            return goal.progress_percentage
        
        for metric in goal.measurable_metrics:
            current_value = progress_data.get(metric.metric_name, metric.current_value)
            
            # Calculate progress toward target
            if metric.target_value != metric.baseline_value:
                progress_ratio = abs(current_value - metric.baseline_value) / abs(metric.target_value - metric.baseline_value)
                metric_progress = min(100.0, progress_ratio * 100.0)
            else:
                metric_progress = 100.0 if current_value == metric.target_value else 0.0
            
            total_progress += metric_progress
        
        return total_progress / metric_count
    
    async def _store_goal_in_cognee(self, goal: Goal):
        """Store goal definition in Cognee for institutional memory"""
        goal_summary = f"""
Goal Definition - {goal.id}

🎯 Title: {goal.title}
📝 Description: {goal.description}
🏷️ Category: {goal.category.value}
⭐ Priority: {goal.priority}/10
📅 Deadline: {goal.time_bound_deadline.isoformat()}

🔍 SMART Criteria:
- Specific: {goal.specific_details}
- Measurable: {len(goal.measurable_metrics)} metrics defined
- Achievable: {len(goal.achievable_plan)} steps planned
- Relevant: {goal.relevant_justification}
- Time-bound: {goal.time_bound_deadline.strftime('%Y-%m-%d')}

📊 Success Criteria:
{chr(10).join(f"- {criterion}" for criterion in goal.success_criteria)}

🚫 Failure Conditions:
{chr(10).join(f"- {condition}" for condition in goal.failure_conditions)}

🎯 Target Metrics:
{chr(10).join(f"- {metric.metric_name}: {metric.target_value} {metric.unit}" for metric in goal.measurable_metrics)}

⚡ Evolution Triggers:
{chr(10).join(f"- {trigger}" for trigger in goal.evolution_triggers)}

🕒 Created: {goal.created_at.isoformat()}
"""
        
        await self.cognee_service.add_data([goal_summary])
        logging.info(f"💾 [GOAL_MANAGEMENT] Stored goal in Cognee: {goal.id}")
    
    def _calculate_overall_performance_score(self, performance_data: List[Dict]) -> float:
        """Calculate overall performance score (0-100)"""
        if not performance_data:
            return 50.0  # Neutral baseline
        
        # Weight different metrics
        weights = {
            "decision_time": 0.3,    # 30% - speed is important
            "success_rate": 0.4,     # 40% - success is most important
            "error_count": 0.3       # 30% - reliability matters
        }
        
        # Calculate normalized scores
        avg_decision_time = sum(p["decision_time"] for p in performance_data) / len(performance_data)
        avg_success_rate = sum(p["success_rate"] for p in performance_data) / len(performance_data)
        avg_error_count = sum(p["error_count"] for p in performance_data) / len(performance_data)
        
        # Normalize to 0-100 scale
        time_score = max(0, 100 - (avg_decision_time - 1.0) * 25)  # 1s = 100, 5s = 0
        success_score = avg_success_rate * 100
        error_score = max(0, 100 - avg_error_count * 20)  # 0 errors = 100, 5 errors = 0
        
        # Calculate weighted average
        overall_score = (
            time_score * weights["decision_time"] +
            success_score * weights["success_rate"] +
            error_score * weights["error_count"]
        )
        
        return max(0.0, min(100.0, overall_score))
    
    def _get_baseline_metrics(self) -> Dict[str, Any]:
        """Return baseline metrics when no data is available"""
        return {
            "timeframe": "baseline",
            "data_points": 0,
            "average_decision_time": 2.5,
            "average_success_rate": 0.8,
            "total_iterations": 0,
            "error_rate": 0.0,
            "decision_time_trend": "stable",
            "success_rate_trend": "stable",
            "evolution_cycles": 0,
            "evolution_success_rate": 0.0,
            "evolution_enabled": False,
            "active_goals_count": len(self.active_goals),
            "performance_score": 50.0,
            "improvement_opportunities": ["Establish baseline performance data"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple trend calculation
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        if second_half > first_half * 1.05:
            return "increasing"
        elif second_half < first_half * 0.95:
            return "decreasing"
        else:
            return "stable"

# Global service instance
_goal_management_service: Optional[GoalManagementService] = None

async def get_goal_management_service() -> Optional[GoalManagementService]:
    """Get or create the global goal management service instance"""
    global _goal_management_service
    
    if _goal_management_service is None:
        # Import services
        from .cognee_direct_service import get_cognee_direct_service
        from .evolution_service import get_evolution_service
        
        cognee_service = await get_cognee_direct_service()
        evolution_service = await get_evolution_service()
        
        if cognee_service and evolution_service:
            _goal_management_service = GoalManagementService(cognee_service, evolution_service)
            await _goal_management_service.initialize()
    
    return _goal_management_service 