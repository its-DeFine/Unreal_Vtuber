"""
🎯 Goal Management Tools - MCP Interface for Goal Setting & Tracking

These tools provide comprehensive goal management capabilities for the autonomous agent:
- Define new goals with SMART criteria
- Track goal progress and metrics
- Query goal-related memory and insights
- Generate performance reports
- Manage goal lifecycle

All tools integrate with the GoalManagementService and Cognee memory system.
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..services.goal_management_service import get_goal_management_service, GoalStatus, GoalCategory


async def define_autonomous_goal(natural_language_goal: str, priority: int = 5) -> Dict[str, Any]:
    """
    🎯 Define Autonomous Goal
    
    Create a new goal for the autonomous agent with SMART criteria.
    
    Args:
        natural_language_goal: Natural language description of the goal
        priority: Priority level 1-10 (10 = highest priority)
    
    Returns:
        Goal definition with ID and SMART criteria
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Define the goal
        goal = await goal_service.define_goal(natural_language_goal, priority)
        
        # Format response
        result = {
            "success": True,
            "goal_id": goal.id,
            "title": goal.title,
            "category": goal.category.value,
            "priority": goal.priority,
            "deadline": goal.time_bound_deadline.isoformat(),
            "smart_criteria": {
                "specific": goal.specific_details,
                "measurable": [
                    {
                        "metric": metric.metric_name,
                        "target": metric.target_value,
                        "unit": metric.unit
                    } for metric in goal.measurable_metrics
                ],
                "achievable": goal.achievable_plan,
                "relevant": goal.relevant_justification,
                "time_bound": goal.time_bound_deadline.strftime("%Y-%m-%d")
            },
            "success_criteria": goal.success_criteria,
            "milestones": goal.milestones,
            "evolution_triggers": goal.evolution_triggers
        }
        
        logging.info(f"🎯 [GOAL_TOOLS] Goal defined: {goal.id} - {goal.title}")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Goal definition failed: {e}")
        return {"success": False, "error": str(e)}


async def get_active_goals(status_filter: str = None) -> Dict[str, Any]:
    """
    📋 Get Active Goals
    
    Retrieve all active goals with optional status filtering.
    
    Args:
        status_filter: Optional status filter (pending, in_progress, achieved, failed, paused)
    
    Returns:
        List of active goals with current status
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Parse status filter
        status_enum = None
        if status_filter:
            try:
                status_enum = GoalStatus(status_filter.lower())
            except ValueError:
                return {"success": False, "error": f"Invalid status: {status_filter}"}
        
        # Get goals
        goals = await goal_service.get_current_goals(status_enum)
        
        # Format goals for response
        formatted_goals = []
        for goal in goals:
            formatted_goals.append({
                "id": goal.id,
                "title": goal.title,
                "category": goal.category.value,
                "status": goal.status.value,
                "priority": goal.priority,
                "progress_percentage": goal.progress_percentage,
                "deadline": goal.time_bound_deadline.isoformat(),
                "created_at": goal.created_at.isoformat(),
                "metrics_count": len(goal.measurable_metrics),
                "milestones_count": len(goal.milestones),
                "success_criteria": goal.success_criteria[:2],  # First 2 for summary
                "evolution_triggers": goal.evolution_triggers
            })
        
        result = {
            "success": True,
            "total_goals": len(formatted_goals),
            "status_filter": status_filter or "all",
            "goals": formatted_goals,
            "summary": {
                "pending": len([g for g in goals if g.status == GoalStatus.PENDING]),
                "in_progress": len([g for g in goals if g.status == GoalStatus.IN_PROGRESS]),
                "achieved": len([g for g in goals if g.status == GoalStatus.ACHIEVED]),
                "failed": len([g for g in goals if g.status == GoalStatus.FAILED])
            }
        }
        
        logging.info(f"📋 [GOAL_TOOLS] Retrieved {len(formatted_goals)} goals")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Get goals failed: {e}")
        return {"success": False, "error": str(e)}


async def get_next_priority_goal() -> Dict[str, Any]:
    """
    🎯 Get Next Priority Goal
    
    Get the highest priority goal that's ready to work on.
    
    Returns:
        Next goal to focus on with detailed information
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Get next priority goal
        next_goal = await goal_service.get_next_priority_goal()
        
        if not next_goal:
            return {
                "success": True,
                "message": "No goals ready to work on",
                "suggestion": "Consider defining new goals or checking goal dependencies"
            }
        
        # Format detailed goal information
        result = {
            "success": True,
            "goal": {
                "id": next_goal.id,
                "title": next_goal.title,
                "description": next_goal.description,
                "category": next_goal.category.value,
                "status": next_goal.status.value,
                "priority": next_goal.priority,
                "progress_percentage": next_goal.progress_percentage,
                "deadline": next_goal.time_bound_deadline.isoformat(),
                "days_remaining": (next_goal.time_bound_deadline - datetime.now()).days,
                
                # SMART details
                "specific_details": next_goal.specific_details,
                "achievable_plan": next_goal.achievable_plan,
                "relevant_justification": next_goal.relevant_justification,
                
                # Metrics
                "metrics": [
                    {
                        "name": metric.metric_name,
                        "current": metric.current_value,
                        "target": metric.target_value,
                        "unit": metric.unit,
                        "progress": (metric.current_value / metric.target_value * 100) if metric.target_value > 0 else 0
                    } for metric in next_goal.measurable_metrics
                ],
                
                # Progress tracking
                "milestones": next_goal.milestones,
                "success_criteria": next_goal.success_criteria,
                "failure_conditions": next_goal.failure_conditions,
                
                # Context
                "evolution_triggers": next_goal.evolution_triggers,
                "learned_strategies": next_goal.learned_strategies
            },
            "recommended_actions": [
                "Review goal metrics and current progress",
                "Check if any evolution triggers should be activated",
                "Consider querying goal memory for similar successful patterns",
                "Update goal progress based on recent performance data"
            ]
        }
        
        logging.info(f"🎯 [GOAL_TOOLS] Next priority goal: {next_goal.id} - {next_goal.title}")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Get next goal failed: {e}")
        return {"success": False, "error": str(e)}


async def update_goal_progress(goal_id: str, progress_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    📊 Update Goal Progress
    
    Update goal progress based on performance data and metrics.
    
    Args:
        goal_id: ID of the goal to update
        progress_data: Performance data and metrics for progress calculation
    
    Returns:
        Updated goal progress information
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Update goal progress
        success = await goal_service.update_goal_progress(goal_id, progress_data)
        
        if not success:
            return {"success": False, "error": f"Failed to update goal: {goal_id}"}
        
        # Get updated goal
        goal = goal_service.active_goals.get(goal_id)
        if not goal:
            return {"success": False, "error": f"Goal not found: {goal_id}"}
        
        result = {
            "success": True,
            "goal_id": goal_id,
            "title": goal.title,
            "previous_progress": goal.progress_percentage,  # This would need to be tracked separately
            "current_progress": goal.progress_percentage,
            "status": goal.status.value,
            "updated_at": goal.updated_at.isoformat(),
            
            "metrics_updated": [
                {
                    "name": metric.metric_name,
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "progress_percentage": (metric.current_value / metric.target_value * 100) if metric.target_value > 0 else 0
                } for metric in goal.measurable_metrics
            ],
            
            "milestones_achieved": [
                milestone for milestone in goal.milestones 
                if milestone.get("percentage", 0) <= goal.progress_percentage
            ],
            
            "next_actions": [
                "Continue monitoring progress toward target metrics",
                "Check if milestone achievements trigger evolution cycles",
                "Update Cognee memory with progress insights"
            ]
        }
        
        logging.info(f"📊 [GOAL_TOOLS] Updated progress for {goal_id}: {goal.progress_percentage:.1f}%")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Progress update failed: {e}")
        return {"success": False, "error": str(e)}


async def generate_goal_performance_report(timeframe_hours: int = 24) -> Dict[str, Any]:
    """
    📈 Generate Goal Performance Report
    
    Generate comprehensive performance metrics and goal progress report.
    
    Args:
        timeframe_hours: Hours of data to include in the report
    
    Returns:
        Comprehensive performance and goal progress report
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Generate performance metrics
        metrics = await goal_service.generate_performance_metrics(timeframe_hours)
        
        # Get current goals for analysis
        all_goals = await goal_service.get_current_goals()
        
        # Calculate goal-specific analytics
        goal_analytics = {
            "total_goals": len(all_goals),
            "by_status": {},
            "by_category": {},
            "by_priority": {},
            "progress_distribution": [],
            "upcoming_deadlines": [],
            "high_priority_goals": []
        }
        
        # Analyze goals by status
        for status in GoalStatus:
            status_goals = [g for g in all_goals if g.status == status]
            goal_analytics["by_status"][status.value] = len(status_goals)
        
        # Analyze goals by category
        for category in GoalCategory:
            category_goals = [g for g in all_goals if g.category == category]
            goal_analytics["by_category"][category.value] = len(category_goals)
        
        # Analyze goals by priority
        for priority in range(1, 11):
            priority_goals = [g for g in all_goals if g.priority == priority]
            goal_analytics["by_priority"][str(priority)] = len(priority_goals)
        
        # Progress distribution
        progress_ranges = [(0, 25), (25, 50), (50, 75), (75, 100)]
        for min_prog, max_prog in progress_ranges:
            count = len([g for g in all_goals if min_prog <= g.progress_percentage < max_prog])
            goal_analytics["progress_distribution"].append({
                "range": f"{min_prog}-{max_prog}%",
                "count": count
            })
        
        # Upcoming deadlines (next 7 days)
        upcoming_deadline = datetime.now() + timedelta(days=7)
        for goal in all_goals:
            if goal.time_bound_deadline <= upcoming_deadline and goal.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]:
                days_left = (goal.time_bound_deadline - datetime.now()).days
                goal_analytics["upcoming_deadlines"].append({
                    "id": goal.id,
                    "title": goal.title,
                    "days_left": days_left,
                    "progress": goal.progress_percentage
                })
        
        # High priority goals (8-10)
        high_priority = [g for g in all_goals if g.priority >= 8 and g.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]]
        goal_analytics["high_priority_goals"] = [
            {
                "id": goal.id,
                "title": goal.title,
                "priority": goal.priority,
                "progress": goal.progress_percentage,
                "category": goal.category.value
            } for goal in high_priority[:5]  # Top 5
        ]
        
        # Combine metrics with goal analytics
        result = {
            "success": True,
            "report_generated_at": datetime.now().isoformat(),
            "timeframe": f"{timeframe_hours} hours",
            
            # Performance metrics from goal service
            "performance_metrics": metrics,
            
            # Goal-specific analytics
            "goal_analytics": goal_analytics,
            
            # Recommendations
            "recommendations": [
                "Focus on high-priority goals with upcoming deadlines",
                "Review goals with <25% progress for potential issues",
                "Consider evolution triggers for performance-related goals",
                "Update goal progress more frequently for better tracking"
            ],
            
            # Key insights
            "insights": [
                f"Performance score: {metrics.get('performance_score', 'N/A')}",
                f"Total active goals: {goal_analytics['total_goals']}",
                f"Goals in progress: {goal_analytics['by_status'].get('in_progress', 0)}",
                f"Upcoming deadlines: {len(goal_analytics['upcoming_deadlines'])}",
                f"High priority goals: {len(goal_analytics['high_priority_goals'])}"
            ]
        }
        
        logging.info(f"📈 [GOAL_TOOLS] Generated performance report for {timeframe_hours}h")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Performance report failed: {e}")
        return {"success": False, "error": str(e)}


async def query_goal_memory(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    🧠 Query Goal Memory
    
    Search Cognee memory for goal-related insights and patterns.
    
    Args:
        query: Search query for goal-related memories
        limit: Maximum number of results to return
    
    Returns:
        Relevant goal memories and insights
    """
    try:
        goal_service = await get_goal_management_service()
        if not goal_service:
            return {"success": False, "error": "Goal management service not available"}
        
        # Query goal memory
        memories = await goal_service.query_goal_memory(query, limit)
        
        result = {
            "success": True,
            "query": query,
            "results_count": len(memories),
            "memories": memories,
            "insights": [],
            "patterns": []
        }
        
        # Extract insights from memories
        if memories:
            # Analyze memories for common patterns
            content_words = []
            for memory in memories:
                content = memory.get("content", "").lower()
                content_words.extend(content.split())
            
            # Find common themes (simplified)
            word_counts = {}
            for word in content_words:
                if len(word) > 4:  # Only consider meaningful words
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # Get top themes
            common_themes = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            result["insights"] = [
                f"Found {len(memories)} relevant goal memories",
                f"Average relevance score: {sum(m.get('relevance_score', 0) for m in memories) / len(memories):.2f}",
                f"Common themes: {', '.join([theme[0] for theme in common_themes[:3]])}"
            ]
            
            result["patterns"] = [
                f"Theme: {theme[0]} (mentioned {theme[1]} times)" 
                for theme in common_themes[:3]
            ]
        else:
            result["insights"] = ["No relevant goal memories found for this query"]
        
        logging.info(f"🧠 [GOAL_TOOLS] Queried goal memory: '{query}' - {len(memories)} results")
        return result
        
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Goal memory query failed: {e}")
        return {"success": False, "error": str(e)}


# Export tools for MCP registration
GOAL_MANAGEMENT_TOOLS = {
    "define_autonomous_goal": define_autonomous_goal,
    "get_active_goals": get_active_goals,
    "get_next_priority_goal": get_next_priority_goal,
    "update_goal_progress": update_goal_progress,
    "generate_goal_performance_report": generate_goal_performance_report,
    "query_goal_memory": query_goal_memory
}


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 Goal Management Tool Entry Point
    
    Main entry point for goal management operations.
    Handles goal creation, progress tracking, and memory queries.
    
    Args:
        context: Operation context containing action and parameters
    
    Returns:
        Result of the goal management operation
    """
    try:
        action = context.get("action", "get_active_goals")
        
        # Route to appropriate goal management function
        if action == "define_goal":
            return await define_autonomous_goal(
                context.get("goal", "Improve agent performance"),
                context.get("priority", 5)
            )
        
        elif action == "get_goals":
            return await get_active_goals(context.get("status_filter"))
        
        elif action == "next_goal":
            return await get_next_priority_goal()
        
        elif action == "update_progress":
            return await update_goal_progress(
                context.get("goal_id", ""),
                context.get("progress_data", {})
            )
        
        elif action == "generate_report":
            return await generate_goal_performance_report(
                context.get("timeframe_hours", 24)
            )
        
        elif action == "query_memory":
            return await query_goal_memory(
                context.get("query", "goal optimization"),
                context.get("limit", 5)
            )
        
        else:
            # Default action - get active goals overview
            goals_result = await get_active_goals()
            next_goal_result = await get_next_priority_goal()
            
            return {
                "success": True,
                "tool": "goal_management",
                "action": "overview",
                "current_goals": goals_result,
                "next_priority_goal": next_goal_result,
                "available_actions": [
                    "define_goal", "get_goals", "next_goal", 
                    "update_progress", "generate_report", "query_memory"
                ]
            }
            
    except Exception as e:
        logging.error(f"❌ [GOAL_TOOLS] Run function error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool": "goal_management",
            "action": context.get("action", "unknown")
        } 