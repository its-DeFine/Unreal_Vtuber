"""
SCB (Shared Context Blackboard) Operations Tool

This tool provides direct access to the SCB/Redis layer, enabling the autonomous team to:
1. Read system-wide state from other agents
2. Publish their own state and decisions
3. Query historical states
4. Subscribe to specific channels (future)
5. Coordinate with other agents

This significantly enhances multi-agent awareness and coordination capabilities.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔄 SCB Operations Tool Entry Point
    
    Provides direct access to the Shared Context Blackboard for multi-agent coordination.
    
    Args:
        context: Operation context containing:
            - action: Operation to perform (read, write, query, list)
            - scb_client: SCB client instance (injected by enhanced context)
            - Additional parameters based on action
    
    Returns:
        Result of the SCB operation
    """
    try:
        action = context.get("action", "read")
        scb_client = context.get("scb_client")
        
        # Check if SCB is available
        if not scb_client:
            return {
                "success": False,
                "error": "SCB client not available in context",
                "suggestion": "Ensure AGENTNET_ENABLED=true and SCB client is initialized"
            }
        
        if not scb_client.is_enabled():
            return {
                "success": False,
                "error": "SCB is in standalone mode",
                "suggestion": "Enable AgentNet for multi-agent coordination"
            }
        
        # Route to appropriate SCB operation
        if action == "read":
            return await _read_state(scb_client, context)
        
        elif action == "write" or action == "publish":
            return await _write_state(scb_client, context)
        
        elif action == "query":
            return await _query_states(scb_client, context)
        
        elif action == "list":
            return await _list_agents(scb_client, context)
        
        elif action == "broadcast":
            return await _broadcast_message(scb_client, context)
        
        elif action == "get_system_state":
            return await _get_system_state(scb_client, context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["read", "write", "query", "list", "broadcast", "get_system_state"]
            }
            
    except Exception as e:
        logger.error(f"❌ [SCB_OPERATIONS] Error in SCB operation: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _read_state(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """Read state from a specific agent or key"""
    agent_name = context.get("agent", "system")
    key = context.get("key", f"{agent_name}_state")
    
    try:
        state = scb_client.get_state(key)
        
        if state:
            # Parse JSON if it's a string
            if isinstance(state, (str, bytes)):
                try:
                    state = json.loads(state)
                except:
                    pass
            
            return {
                "success": True,
                "agent": agent_name,
                "key": key,
                "state": state,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": True,
                "agent": agent_name,
                "key": key,
                "state": None,
                "message": "No state found for this agent/key"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read state: {str(e)}"
        }


async def _write_state(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """Write/publish state to SCB"""
    agent_name = context.get("agent", "autonomous_team")
    state_data = context.get("state", {})
    channel = context.get("channel", "agent_state")
    ttl = context.get("ttl", 3600)  # Default 1 hour TTL
    
    try:
        # Prepare state with metadata
        full_state = {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "data": state_data,
            "metadata": {
                "source": "scb_operations_tool",
                "ttl": ttl
            }
        }
        
        # Publish to SCB
        scb_client.publish_state(full_state, channel)
        
        # Also store with a key for direct access
        key = f"{agent_name}_state"
        scb_client.set_state(key, full_state, ttl)
        
        logger.info(f"✅ [SCB_OPERATIONS] Published state for agent: {agent_name}")
        
        return {
            "success": True,
            "agent": agent_name,
            "channel": channel,
            "key": key,
            "state_published": full_state,
            "ttl": ttl
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to write state: {str(e)}"
        }


async def _query_states(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """Query multiple agent states with filters"""
    pattern = context.get("pattern", "*_state")
    filter_active = context.get("active_only", True)
    max_age_minutes = context.get("max_age_minutes", 60)
    
    try:
        # Get all matching keys
        keys = scb_client.get_keys(pattern)
        
        states = {}
        active_agents = []
        inactive_agents = []
        
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        for key in keys:
            state = scb_client.get_state(key)
            if state:
                try:
                    if isinstance(state, (str, bytes)):
                        state = json.loads(state)
                    
                    # Check if state is recent
                    state_time = datetime.fromisoformat(state.get("timestamp", "2000-01-01"))
                    is_active = state_time > cutoff_time
                    
                    if not filter_active or is_active:
                        agent_name = state.get("agent", key.replace("_state", ""))
                        states[agent_name] = state
                        
                        if is_active:
                            active_agents.append(agent_name)
                        else:
                            inactive_agents.append(agent_name)
                            
                except Exception as e:
                    logger.warning(f"Failed to parse state for {key}: {e}")
        
        return {
            "success": True,
            "total_agents": len(states),
            "active_agents": active_agents,
            "inactive_agents": inactive_agents,
            "states": states,
            "query_pattern": pattern,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to query states: {str(e)}"
        }


async def _list_agents(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """List all known agents in the system"""
    try:
        # Get all agent state keys
        keys = scb_client.get_keys("*_state")
        
        agents = []
        for key in keys:
            agent_name = key.replace("_state", "")
            state = scb_client.get_state(key)
            
            agent_info = {
                "name": agent_name,
                "has_state": state is not None
            }
            
            if state:
                try:
                    if isinstance(state, (str, bytes)):
                        state = json.loads(state)
                    agent_info["last_update"] = state.get("timestamp", "unknown")
                    agent_info["status"] = state.get("data", {}).get("status", "unknown")
                except:
                    pass
            
            agents.append(agent_info)
        
        # Sort by name
        agents.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "total_agents": len(agents),
            "agents": agents,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list agents: {str(e)}"
        }


async def _broadcast_message(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """Broadcast a message to all agents"""
    message = context.get("message", "")
    priority = context.get("priority", "normal")
    sender = context.get("sender", "autonomous_team")
    
    if not message:
        return {
            "success": False,
            "error": "Message cannot be empty"
        }
    
    try:
        broadcast_data = {
            "type": "broadcast",
            "sender": sender,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "metadata": context.get("metadata", {})
        }
        
        # Publish to multiple channels
        channels = ["system_broadcast", "agent_messages", "team_coordination"]
        
        for channel in channels:
            scb_client.publish_state(broadcast_data, channel)
        
        logger.info(f"📢 [SCB_OPERATIONS] Broadcast sent from {sender}: {message[:50]}...")
        
        return {
            "success": True,
            "broadcast": broadcast_data,
            "channels": channels,
            "message_length": len(message)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to broadcast: {str(e)}"
        }


async def _get_system_state(scb_client, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get comprehensive system state overview"""
    try:
        # Gather various system states
        system_state = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "active_objectives": [],
            "recent_decisions": [],
            "system_metrics": {}
        }
        
        # Get all agent states
        agent_keys = scb_client.get_keys("*_state")
        for key in agent_keys[:10]:  # Limit to prevent overload
            state = scb_client.get_state(key)
            if state:
                try:
                    if isinstance(state, (str, bytes)):
                        state = json.loads(state)
                    agent_name = state.get("agent", key.replace("_state", ""))
                    system_state["agents"][agent_name] = {
                        "last_update": state.get("timestamp"),
                        "status": state.get("data", {}).get("status", "unknown")
                    }
                except:
                    pass
        
        # Get active objectives
        objectives = scb_client.get_state("system_objectives")
        if objectives:
            try:
                if isinstance(objectives, (str, bytes)):
                    objectives = json.loads(objectives)
                system_state["active_objectives"] = objectives.get("objectives", [])
            except:
                pass
        
        # Get recent decisions
        decisions = scb_client.get_state("recent_decisions")
        if decisions:
            try:
                if isinstance(decisions, (str, bytes)):
                    decisions = json.loads(decisions)
                system_state["recent_decisions"] = decisions.get("decisions", [])[:5]
            except:
                pass
        
        # Get system metrics
        metrics = scb_client.get_state("system_metrics")
        if metrics:
            try:
                if isinstance(metrics, (str, bytes)):
                    metrics = json.loads(metrics)
                system_state["system_metrics"] = metrics
            except:
                pass
        
        return {
            "success": True,
            "system_state": system_state,
            "total_agents": len(system_state["agents"]),
            "total_objectives": len(system_state["active_objectives"])
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get system state: {str(e)}"
        }


# Tool metadata for registration
TOOL_METADATA = {
    "name": "scb_operations_tool",
    "description": "Direct access to Shared Context Blackboard for multi-agent coordination",
    "version": "1.0.0",
    "author": "Autonomous Team Enhancement",
    "capabilities": [
        "read_agent_states",
        "publish_state_updates",
        "query_multiple_agents",
        "broadcast_messages",
        "system_state_overview"
    ],
    "required_context": ["scb_client"],
    "example_usage": {
        "read": {
            "action": "read",
            "agent": "weather_service"
        },
        "write": {
            "action": "write",
            "state": {"status": "analyzing", "confidence": 0.85}
        },
        "broadcast": {
            "action": "broadcast",
            "message": "Requesting weather update for planning",
            "priority": "high"
        }
    }
}