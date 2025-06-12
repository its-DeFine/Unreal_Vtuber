"""
🎭 Advanced VTuber Control Tool - VTuber Activation Control

This tool provides VTuber control functionality:
- Explicit activation via control_vtuber_instance boolean
- Avatar activation and deactivation
- Status checking and monitoring
- Message sending control
- Duration specification
- Remote control capabilities
"""

import logging
import time
from typing import Dict, Any, Optional

def run(context: Dict) -> Dict[str, Any]:
    """
    Advanced VTuber Control Tool - VTuber Activation Control
    
    This tool controls VTuber activation based on:
    - control_vtuber_instance: boolean (explicit activation)
    - vtuber_action: str (activate, deactivate, status, send_message)
    - message: str (optional message to send when activated)
    - duration_minutes: int (optional duration for activation)
    """
    
    # Check if explicitly enabled
    control_vtuber = context.get("control_vtuber_instance", False)
    vtuber_action = context.get("vtuber_action", "activate")
    message = context.get("message", "")
    duration_minutes = context.get("duration_minutes", 0)
    
    if not control_vtuber:
        logging.info("🚫 [ADVANCED_VTUBER] Tool called but control_vtuber_instance=False, skipping...")
        return {
            "message": "VTuber control disabled - set control_vtuber_instance=True to activate",
            "tool": "advanced_vtuber_control",
            "success": False,
            "reason": "explicit_control_required",
            "status": "disabled",
            "vtuber_activated": False
        }
    
    # Get VTuber client from context (if available)
    vtuber_client = context.get("vtuber_client")
    
    if not vtuber_client:
        logging.warning("⚠️ [ADVANCED_VTUBER] VTuber client not available in context")
        return {
            "message": "VTuber client not available - check system configuration",
            "tool": "advanced_vtuber_control",
            "success": False,
            "reason": "client_not_available",
            "status": "error"
        }
    
    # Execute VTuber action
    result = _execute_vtuber_action(vtuber_client, vtuber_action, message, duration_minutes)
    
    logging.info(f"🎭 [ADVANCED_VTUBER] Action '{vtuber_action}' completed: {result['status']}")
    
    return result

def _execute_vtuber_action(vtuber_client, action: str, message: str = "", duration_minutes: int = 0) -> Dict[str, Any]:
    """Execute the specified VTuber action"""
    
    timestamp = time.time()
    
    if action == "activate":
        vtuber_client.activate_vtuber()
        
        # Send activation message if provided
        if message:
            vtuber_client.post_message(message, force_send=True)
            action_message = f"🎭 VTuber activated and message sent: {message[:50]}..."
        else:
            action_message = "🎭 VTuber activated - ready to receive messages"
        
        # Set deactivation timer if duration specified
        if duration_minutes > 0:
            # Note: In a real implementation, you'd want to set up a proper timer
            # For now, we'll just log the intended duration
            logging.info(f"🕐 [ADVANCED_VTUBER] VTuber activated for {duration_minutes} minutes")
            action_message += f" (Duration: {duration_minutes} minutes)"
        
        return {
            "message": action_message,
            "tool": "advanced_vtuber_control",
            "success": True,
            "status": "activated",
            "vtuber_activated": True,
            "action": "activate",
            "duration_minutes": duration_minutes,
            "timestamp": timestamp
        }
    
    elif action == "deactivate":
        vtuber_client.deactivate_vtuber()
        
        return {
            "message": "🎭 VTuber deactivated - messages will be logged only",
            "tool": "advanced_vtuber_control",
            "success": True,
            "status": "deactivated",
            "vtuber_activated": False,
            "action": "deactivate",
            "timestamp": timestamp
        }
    
    elif action == "status":
        status = vtuber_client.get_status()
        
        return {
            "message": f"🎭 VTuber Status: {'Activated' if status['activated'] else 'Deactivated'} | Endpoint: {status['endpoint']}",
            "tool": "advanced_vtuber_control",
            "success": True,
            "status": "checked",
            "vtuber_activated": status['activated'],
            "vtuber_status": status,
            "action": "status",
            "timestamp": timestamp
        }
    
    elif action == "send_message":
        if not message:
            return {
                "message": "🚫 Cannot send empty message to VTuber",
                "tool": "advanced_vtuber_control",
                "success": False,
                "status": "error",
                "reason": "empty_message",
                "timestamp": timestamp
            }
        
        # Send message with force_send=True to bypass activation check
        vtuber_client.post_message(message, force_send=True)
        
        return {
            "message": f"🎭 Message sent to VTuber: {message[:50]}{'...' if len(message) > 50 else ''}",
            "tool": "advanced_vtuber_control",
            "success": True,
            "status": "message_sent",
            "vtuber_activated": vtuber_client.is_vtuber_activated(),
            "action": "send_message",
            "message_sent": message,
            "timestamp": timestamp
        }
    
    else:
        return {
            "message": f"🚫 Unknown VTuber action: {action}",
            "tool": "advanced_vtuber_control",
            "success": False,
            "status": "error",
            "reason": "unknown_action",
            "available_actions": ["activate", "deactivate", "status", "send_message"],
            "timestamp": timestamp
        }

def get_vtuber_control_help() -> Dict[str, Any]:
    """Get help information for VTuber control"""
    return {
        "tool": "advanced_vtuber_control",
        "description": "Control VTuber activation and messaging",
        "required_parameters": {
            "control_vtuber_instance": "boolean - Must be True to enable control"
        },
        "optional_parameters": {
            "vtuber_action": "str - Action to perform (activate, deactivate, status, send_message)",
            "message": "str - Message to send to VTuber",
            "duration_minutes": "int - Duration for activation (0 = indefinite)"
        },
        "actions": {
            "activate": "Enable VTuber message sending",
            "deactivate": "Disable VTuber message sending",
            "status": "Check current VTuber status",
            "send_message": "Send specific message to VTuber (bypasses activation check)"
        },
        "examples": [
            {"control_vtuber_instance": True, "vtuber_action": "activate"},
            {"control_vtuber_instance": True, "vtuber_action": "send_message", "message": "Hello viewers!"},
            {"control_vtuber_instance": True, "vtuber_action": "deactivate"}
        ]
    }

def create_vtuber_instance(
    avatar_config: Dict[str, Any],
    projection_medium: str,
    duration_minutes: int,
    custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    FUTURE IMPLEMENTATION: Create and configure VTuber instance
    
    Args:
        avatar_config: Avatar selection and customization options
        projection_medium: Target platform (twitch, zoom, youtube, etc.)
        duration_minutes: How long to run the VTuber
        custom_prompt: Optional custom prompt for content generation
        
    Returns:
        VTuber instance configuration and status
    """
    # Future implementation
    pass

def control_vtuber_instance(
    instance_id: str,
    action: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    FUTURE IMPLEMENTATION: Control existing VTuber instance
    
    Args:
        instance_id: ID of the VTuber instance to control
        action: Action to perform (update_prompt, change_medium, shutdown, etc.)
        parameters: Action-specific parameters
        
    Returns:
        Control action result
    """
    # Future implementation
    pass

def shutdown_vtuber_instance(instance_id: str) -> Dict[str, Any]:
    """
    FUTURE IMPLEMENTATION: Shutdown VTuber instance
    
    Args:
        instance_id: ID of the VTuber instance to shutdown
        
    Returns:
        Shutdown status
    """
    # Future implementation
    pass 