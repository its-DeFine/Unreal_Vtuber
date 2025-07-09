"""
Tool Management Tool

This tool allows the autonomous team to manage their own tools dynamically,
including creating new tools, listing available tools, and checking their
autonomy level to see what operations they can perform.

This is a meta-tool that enhances the team's self-modification capabilities.
"""

import logging
import json
import inspect
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Tool Management Entry Point
    
    Manage tools dynamically - create, list, inspect, and monitor tool performance.
    
    Args:
        context: Operation context containing:
            - action: Operation to perform (create, list, inspect, performance, autonomy_status)
            - tool_registry: Tool registry instance (injected)
            - Additional parameters based on action
    
    Returns:
        Result of the tool management operation
    """
    try:
        action = context.get("action", "list")
        tool_registry = context.get("tool_registry")
        
        if not tool_registry:
            # Try to get from global context
            from autogen_agent.tool_registry import ToolRegistry
            tool_registry = ToolRegistry()
            
        # Route to appropriate operation
        if action == "create":
            return await _create_tool(tool_registry, context)
        
        elif action == "list":
            return await _list_tools(tool_registry, context)
        
        elif action == "inspect":
            return await _inspect_tool(tool_registry, context)
        
        elif action == "performance":
            return await _get_performance(tool_registry, context)
        
        elif action == "unregister":
            return await _unregister_tool(tool_registry, context)
        
        elif action == "autonomy_status":
            return await _check_autonomy_status(context)
        
        elif action == "request_upgrade":
            return await _request_autonomy_upgrade(context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": [
                    "create", "list", "inspect", "performance", 
                    "unregister", "autonomy_status", "request_upgrade"
                ]
            }
            
    except Exception as e:
        logger.error(f"❌ [TOOL_MANAGEMENT] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _create_tool(tool_registry, context: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new tool dynamically"""
    from autogen_agent.autonomy_config import check_autonomy
    
    # Check autonomy
    autonomy_check = check_autonomy("tool_create")
    if not autonomy_check['allowed']:
        return {
            "success": False,
            "error": "Insufficient autonomy level",
            "details": autonomy_check
        }
    
    tool_name = context.get("tool_name")
    tool_code = context.get("tool_code")
    metadata = context.get("metadata", {})
    
    if not tool_name or not tool_code:
        return {
            "success": False,
            "error": "tool_name and tool_code are required"
        }
    
    try:
        # Create a function from the code
        # SAFETY: This is dangerous and should only be done with approval
        namespace = {
            "logging": logging,
            "json": json,
            "Dict": Dict,
            "Any": Any,
            "List": List,
            "Optional": Optional,
            "datetime": datetime
        }
        
        # Execute the code to define the function
        exec(tool_code, namespace)
        
        # Find the 'run' function
        if 'run' not in namespace:
            return {
                "success": False,
                "error": "Tool code must define a 'run' function"
            }
        
        tool_func = namespace['run']
        
        # Add metadata
        metadata.update({
            "created_by": "autonomous_team",
            "created_at": datetime.now().isoformat(),
            "source": "tool_management"
        })
        
        # Register the tool
        result = tool_registry.register_runtime_tool(
            tool_name=tool_name,
            tool_func=tool_func,
            metadata=metadata,
            require_approval=True  # Always require approval for safety
        )
        
        logger.info(f"🔧 [TOOL_MANAGEMENT] Tool creation requested: {tool_name}")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create tool: {str(e)}"
        }


async def _list_tools(tool_registry, context: Dict[str, Any]) -> Dict[str, Any]:
    """List all available tools"""
    try:
        # Get all tools
        all_tools = tool_registry.list_tools()
        
        # Get runtime tools
        runtime_tools = tool_registry.list_runtime_tools()
        
        # Get tool status
        status = tool_registry.get_tool_status()
        
        # Categorize tools
        categories = {
            "core": [],
            "runtime": [],
            "disabled": status.get("disabled_tools", [])
        }
        
        # Separate core and runtime
        runtime_names = {t['name'] for t in runtime_tools}
        
        for tool_name in all_tools:
            if tool_name in runtime_names:
                categories["runtime"].append(tool_name)
            else:
                categories["core"].append(tool_name)
        
        return {
            "success": True,
            "total_tools": len(all_tools),
            "categories": categories,
            "async_tools": status.get("async_tools", []),
            "sync_tools": status.get("sync_tools", []),
            "performance_summary": status.get("performance_summary", {}),
            "intelligent_selection": status.get("intelligent_selection_enabled", False)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list tools: {str(e)}"
        }


async def _inspect_tool(tool_registry, context: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect a specific tool"""
    tool_name = context.get("tool_name")
    
    if not tool_name:
        return {
            "success": False,
            "error": "tool_name is required"
        }
    
    try:
        # Get the tool
        tool = tool_registry.get_tool_by_name(tool_name)
        
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        # Get tool info
        info = {
            "name": tool_name,
            "is_async": tool_registry.is_tool_async(tool_name),
            "has_run_method": hasattr(tool, 'run'),
            "module": tool.__module__ if hasattr(tool, '__module__') else None
        }
        
        # Get performance metrics
        if tool_name in tool_registry.tool_performance:
            info["performance"] = tool_registry.tool_performance[tool_name]
        
        # Try to get signature
        try:
            if hasattr(tool, 'run'):
                sig = inspect.signature(tool.run)
            else:
                sig = inspect.signature(tool)
            
            info["signature"] = str(sig)
            info["parameters"] = list(sig.parameters.keys())
        except:
            pass
        
        # Try to get docstring
        try:
            if hasattr(tool, 'run'):
                info["docstring"] = inspect.getdoc(tool.run)
            else:
                info["docstring"] = inspect.getdoc(tool)
        except:
            pass
        
        # Check if it's a runtime tool
        runtime_tools = tool_registry.list_runtime_tools()
        is_runtime = any(t['name'] == tool_name for t in runtime_tools)
        info["is_runtime"] = is_runtime
        
        return {
            "success": True,
            "tool_info": info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to inspect tool: {str(e)}"
        }


async def _get_performance(tool_registry, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get tool performance metrics"""
    try:
        # Get specific tool or all tools
        tool_name = context.get("tool_name")
        
        if tool_name:
            # Get specific tool performance
            if tool_name not in tool_registry.tool_performance:
                return {
                    "success": False,
                    "error": f"No performance data for tool '{tool_name}'"
                }
            
            performance = tool_registry.tool_performance[tool_name]
            
            # Calculate additional metrics
            if performance['total_uses'] > 0:
                success_rate = performance['successes'] / performance['total_uses']
            else:
                success_rate = 0.0
            
            return {
                "success": True,
                "tool_name": tool_name,
                "performance": {
                    **performance,
                    "success_rate": success_rate
                }
            }
        else:
            # Get all tool performance
            all_performance = {}
            
            for name, perf in tool_registry.tool_performance.items():
                if perf['total_uses'] > 0:
                    success_rate = perf['successes'] / perf['total_uses']
                else:
                    success_rate = 0.0
                
                all_performance[name] = {
                    **perf,
                    "success_rate": success_rate
                }
            
            # Sort by usage
            sorted_tools = sorted(
                all_performance.items(),
                key=lambda x: x[1]['total_uses'],
                reverse=True
            )
            
            return {
                "success": True,
                "total_tools": len(all_performance),
                "performance_by_tool": dict(sorted_tools[:20]),  # Top 20
                "usage_history_length": len(tool_registry.tool_usage_history)
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get performance: {str(e)}"
        }


async def _unregister_tool(tool_registry, context: Dict[str, Any]) -> Dict[str, Any]:
    """Unregister a tool"""
    from autogen_agent.autonomy_config import check_autonomy
    
    # Check autonomy
    autonomy_check = check_autonomy("tool_create")  # Same permission as create
    if not autonomy_check['allowed']:
        return {
            "success": False,
            "error": "Insufficient autonomy level",
            "details": autonomy_check
        }
    
    tool_name = context.get("tool_name")
    
    if not tool_name:
        return {
            "success": False,
            "error": "tool_name is required"
        }
    
    try:
        result = tool_registry.unregister_tool(tool_name)
        
        if result['success']:
            logger.info(f"🗑️ [TOOL_MANAGEMENT] Tool unregistered: {tool_name}")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to unregister tool: {str(e)}"
        }


async def _check_autonomy_status(context: Dict[str, Any]) -> Dict[str, Any]:
    """Check current autonomy status and capabilities"""
    try:
        from autogen_agent.autonomy_config import get_autonomy_manager
        
        manager = get_autonomy_manager()
        status = manager.get_status()
        
        # Add capability descriptions
        capabilities = []
        
        if status['can_modify_files']:
            capabilities.append("Can modify core system files")
        else:
            capabilities.append("Cannot modify files (read-only)")
        
        if status['can_create_tools']:
            capabilities.append("Can create and register new tools")
        else:
            capabilities.append("Cannot create new tools")
        
        if status['requires_approval']:
            capabilities.append("All changes require human approval")
        else:
            capabilities.append("Can make changes without approval (DANGEROUS!)")
        
        status['capabilities_summary'] = capabilities
        
        # Check upgrade eligibility
        evaluation = manager.evaluate_autonomy_upgrade()
        status['upgrade_evaluation'] = evaluation
        
        return {
            "success": True,
            "autonomy_status": status
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check autonomy: {str(e)}"
        }


async def _request_autonomy_upgrade(context: Dict[str, Any]) -> Dict[str, Any]:
    """Request autonomy level upgrade"""
    try:
        from autogen_agent.autonomy_config import get_autonomy_manager
        
        manager = get_autonomy_manager()
        
        # First evaluate eligibility
        evaluation = manager.evaluate_autonomy_upgrade()
        
        if not evaluation['eligible']:
            return {
                "success": False,
                "error": "Not eligible for autonomy upgrade",
                "evaluation": evaluation,
                "suggestion": "Continue operating safely to meet upgrade criteria"
            }
        
        # Create upgrade request
        upgrade_request = {
            "type": "autonomy_upgrade",
            "current_level": evaluation['current_level'],
            "requested_level": evaluation['next_level'],
            "metrics": evaluation['metrics'],
            "timestamp": datetime.now().isoformat(),
            "justification": "All upgrade criteria met"
        }
        
        logger.info(f"📈 [TOOL_MANAGEMENT] Autonomy upgrade requested: {upgrade_request}")
        
        # In production, this would go to approval system
        # For now, return the request
        return {
            "success": True,
            "status": "upgrade_requested",
            "upgrade_request": upgrade_request,
            "message": "Autonomy upgrade request submitted for approval"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to request upgrade: {str(e)}"
        }


# Tool metadata
TOOL_METADATA = {
    "name": "tool_management",
    "description": "Manage tools dynamically - create, inspect, and monitor performance",
    "version": "1.0.0",
    "author": "Autonomous Team Enhancement",
    "capabilities": [
        "create_tools",
        "list_tools",
        "inspect_tools",
        "monitor_performance",
        "check_autonomy",
        "request_upgrades"
    ],
    "required_context": ["tool_registry"],
    "example_usage": {
        "list": {
            "action": "list"
        },
        "create": {
            "action": "create",
            "tool_name": "hello_world_tool",
            "tool_code": "async def run(context):\n    return {'message': 'Hello World!'}"
        },
        "autonomy": {
            "action": "autonomy_status"
        }
    }
}