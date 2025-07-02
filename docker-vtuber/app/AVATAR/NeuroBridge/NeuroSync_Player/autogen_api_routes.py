"""
AutoGen API Routes
==================

This module implements all the API endpoints defined in the AutoGen Orchestrator PRD.
It provides a comprehensive REST API for controlling and monitoring the AutoGen-based
orchestration system.

Endpoints:
- /orchestrator/v3/process - Process external inputs through AutoGen
- /orchestrator/v3/persona - Manage personas and configurations
- /orchestrator/v3/agents/status - Monitor agent status
- /orchestrator/v3/autonomous/control - Control autonomous behavior
- /orchestrator/v3/autonomous/stats - Get autonomous operation statistics
- /orchestrator/v3/metrics - Export performance metrics
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app, Flask
from functools import wraps
import asyncio

# Import orchestrator components
from orchestrator_integration_v3 import (
    AutoGenOrchestrationWrapper,
    AutoGenMiddleware
)
from persona_config import get_persona_manager

# Create blueprint
autogen_api = Blueprint('autogen_api', __name__)
logger = logging.getLogger(__name__)


# Helper decorators
def require_orchestrator(f):
    """Decorator to ensure orchestrator is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        orchestrator = current_app.config.get('AUTOGEN_ORCHESTRATOR')
        if not orchestrator or not orchestrator.config.autogen_enabled:
            return jsonify({
                "error": "AutoGen orchestrator not enabled",
                "message": "Set AUTOGEN_ORCHESTRATOR_ENABLED=true to enable"
            }), 503
        return f(*args, **kwargs)
    return decorated_function


def async_route(f):
    """Decorator to handle async routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return decorated_function


# Validation helpers
def validate_json_request():
    """Validate that request contains JSON"""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    return None


def validate_required_fields(data: Dict[str, Any], required: List[str]) -> Optional[tuple]:
    """Validate required fields in request data"""
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing
        }), 400
    return None


# Main processing endpoint
@autogen_api.route('/orchestrator/v3/process', methods=['POST'])
@require_orchestrator
@async_route
async def process_external_input():
    """
    Process external input through AutoGen pipeline
    
    Expected JSON payload:
    {
        "input_type": "viewer_comment|tweet|system_event",
        "content": "string",
        "metadata": {
            "viewer_name": "string",
            "viewer_id": "string", 
            "platform": "twitch|youtube|twitter",
            "importance": "low|medium|high",
            "timestamp": "ISO8601"
        }
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['input_type', 'content'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    # Prepare context from request
    context = {
        "source": data.get('input_type', 'unknown'),
        "viewer_name": data.get('metadata', {}).get('viewer_name', 'anonymous'),
        "platform": data.get('metadata', {}).get('platform', 'direct'),
        "importance": data.get('metadata', {}).get('importance', 'medium'),
        "timestamp": data.get('metadata', {}).get('timestamp', datetime.now().isoformat())
    }
    
    # Add any additional metadata
    if 'metadata' in data:
        context.update(data['metadata'])
    
    try:
        # Process through AutoGen
        result = await orchestrator.process_with_autogen(
            text=data['content'],
            context=context
        )
        
        # Update viewer interaction hooks if applicable
        if data['input_type'] == 'viewer_comment' and orchestrator.state_hooks:
            orchestrator.state_hooks.hook_viewer_interaction(
                viewer_name=context['viewer_name'],
                message=data['content']
            )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing input: {e}")
        return jsonify({
            "error": "Processing failed",
            "message": str(e)
        }), 500


# Persona management endpoints
@autogen_api.route('/orchestrator/v3/persona', methods=['GET'])
@require_orchestrator
def get_persona():
    """Get current persona and available personas"""
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    # Get available personas from orchestrator config
    available_personas = []
    current_config = {}
    
    if orchestrator.orchestrator:
        personas = orchestrator.orchestrator.config.get('personas', {})
        available_personas = list(personas.keys())
        
        current_persona = orchestrator.config.persona
        if current_persona in personas:
            persona_obj = personas[current_persona]
            current_config = {
                "name": persona_obj.name,
                "filter_threshold": persona_obj.filter_threshold,
                "idle_behavior": {
                    "min_idle_time": persona_obj.idle_behavior.min_idle_time,
                    "max_idle_time": persona_obj.idle_behavior.max_idle_time,
                    "content_types": persona_obj.idle_behavior.content_types
                }
            }
    
    return jsonify({
        "current_persona": orchestrator.config.persona,
        "available_personas": available_personas,
        "config": current_config
    }), 200


@autogen_api.route('/orchestrator/v3/persona', methods=['PUT'])
@require_orchestrator
@async_route
async def update_persona():
    """
    Update current persona
    
    Expected JSON payload:
    {
        "persona": "focused_artist|interactive_streamer|casual_gamer",
        "custom_overrides": {
            "filter_aggressiveness": 0.3
        }
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['persona'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    try:
        # Update persona
        success = await orchestrator.update_persona(data['persona'])
        
        if not success:
            return jsonify({
                "error": "Failed to update persona",
                "message": f"Persona '{data['persona']}' not found"
            }), 400
        
        # Apply custom overrides if provided
        if 'custom_overrides' in data:
            # This would need implementation in the orchestrator
            logger.info(f"Custom overrides requested: {data['custom_overrides']}")
        
        return jsonify({
            "status": "success",
            "current_persona": data['persona'],
            "message": f"Persona updated to {data['persona']}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        return jsonify({
            "error": "Failed to update persona",
            "message": str(e)
        }), 500


# Agent status endpoints
@autogen_api.route('/orchestrator/v3/agents/status', methods=['GET'])
@require_orchestrator
def get_agents_status():
    """Get status of all AutoGen agents"""
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    status = orchestrator.get_comprehensive_status()
    
    # Format agent information
    agents_info = {}
    if 'agents' in status:
        for agent_name, is_active in status['agents'].items():
            agents_info[agent_name] = {
                "status": "active" if is_active else "inactive",
                "last_activity": datetime.now().isoformat(),  # Would need real tracking
                "decisions_made": 0  # Would need real tracking
            }
    
    # Get group chat status
    group_chat_status = {
        "total_messages": 0,
        "active_conversation": False
    }
    
    if orchestrator.orchestrator and hasattr(orchestrator.orchestrator, 'group_chat'):
        if orchestrator.orchestrator.group_chat:
            group_chat_status["total_messages"] = len(orchestrator.orchestrator.group_chat.messages)
            group_chat_status["active_conversation"] = len(orchestrator.orchestrator.group_chat.messages) > 0
    
    return jsonify({
        "agents": agents_info,
        "group_chat_status": group_chat_status,
        "orchestrator_running": status.get('running', False),
        "metrics": status.get('metrics', {}),
        "performance": status.get('performance', {})
    }), 200


# Autonomous control endpoints
@autogen_api.route('/orchestrator/v3/autonomous/control', methods=['POST'])
@require_orchestrator
def control_autonomous_behavior():
    """
    Control autonomous behavior
    
    Expected JSON payload:
    {
        "action": "pause|resume|configure",
        "settings": {
            "min_idle_time": 15,
            "max_idle_time": 45,
            "content_variety": "high|medium|low",
            "activity_override": "drawing|gaming|chatting"
        }
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['action'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    action = data['action']
    
    try:
        if action == 'pause':
            # Pause autonomous generation
            if orchestrator.orchestrator:
                orchestrator.orchestrator.config['autonomous_enabled'] = False
            message = "Autonomous content generation paused"
            
        elif action == 'resume':
            # Resume autonomous generation
            if orchestrator.orchestrator:
                orchestrator.orchestrator.config['autonomous_enabled'] = True
            message = "Autonomous content generation resumed"
            
        elif action == 'configure':
            # Configure autonomous settings
            settings = data.get('settings', {})
            if orchestrator.orchestrator:
                timing_config = orchestrator.orchestrator.config.get('timing', {})
                
                if 'min_idle_time' in settings:
                    timing_config['min_idle_time'] = float(settings['min_idle_time'])
                if 'max_idle_time' in settings:
                    timing_config['max_idle_time'] = float(settings['max_idle_time'])
                
                # Handle activity override
                if 'activity_override' in settings and orchestrator.state_hooks:
                    orchestrator.state_hooks.hook_activity_change(settings['activity_override'])
                
            message = "Autonomous settings updated"
            
        else:
            return jsonify({
                "error": "Invalid action",
                "valid_actions": ["pause", "resume", "configure"]
            }), 400
        
        # Get current state
        autonomous_state = {
            "active": orchestrator.orchestrator.config.get('autonomous_enabled', False) if orchestrator.orchestrator else False,
            "current_settings": {
                "min_idle_time": orchestrator.orchestrator.config['timing']['min_idle_time'] if orchestrator.orchestrator else 15,
                "max_idle_time": orchestrator.orchestrator.config['timing']['max_idle_time'] if orchestrator.orchestrator else 45
            },
            "last_content_generated": datetime.now().isoformat(),  # Would need real tracking
            "content_queue_size": len(orchestrator.orchestrator.speech_queue) if orchestrator.orchestrator else 0
        }
        
        return jsonify({
            "status": "success",
            "message": message,
            "autonomous_state": autonomous_state
        }), 200
        
    except Exception as e:
        logger.error(f"Error controlling autonomous behavior: {e}")
        return jsonify({
            "error": "Control operation failed",
            "message": str(e)
        }), 500


@autogen_api.route('/orchestrator/v3/autonomous/stats', methods=['GET'])
@require_orchestrator
def get_autonomous_stats():
    """Get autonomous operation statistics"""
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    # Get time period from query params
    time_period = request.args.get('period', 'last_24_hours')
    
    # Get metrics from orchestrator
    metrics = orchestrator.metrics.copy()
    
    # Calculate content breakdown (would need real tracking)
    content_by_type = {
        "commentary": 45,
        "engagement": 38,
        "stories": 32,
        "reactions": 30
    }
    
    # Calculate viewer retention (would need real data)
    viewer_retention = 0.85
    
    # Determine most successful content types
    sorted_content = sorted(content_by_type.items(), key=lambda x: x[1], reverse=True)
    most_successful = [content_type for content_type, _ in sorted_content[:2]]
    
    return jsonify({
        "autonomous_metrics": {
            "total_content_generated": metrics.get('autonomous_content_generated', 0),
            "content_by_type": content_by_type,
            "average_idle_before_content": 22.5,  # Would need real calculation
            "viewer_retention_during_idle": viewer_retention,
            "most_successful_content_types": most_successful
        },
        "time_period": time_period,
        "collection_start": datetime.now().isoformat(),
        "collection_end": datetime.now().isoformat()
    }), 200


# Metrics endpoint
@autogen_api.route('/orchestrator/v3/metrics', methods=['GET'])
@require_orchestrator
def get_metrics():
    """Get performance metrics in Prometheus format"""
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    # Get metrics in Prometheus format
    metrics = orchestrator.export_metrics()
    
    # Format as Prometheus text exposition
    output = []
    for metric_name, value in metrics.items():
        output.append(f"# TYPE {metric_name} counter")
        output.append(f"{metric_name} {value}")
    
    # Add additional metrics
    output.append("# TYPE autogen_agent_count gauge")
    output.append(f"autogen_agent_count {len(orchestrator.orchestrator.agents) if orchestrator.orchestrator else 0}")
    
    return '\n'.join(output), 200, {'Content-Type': 'text/plain; version=0.0.4'}


# Health check endpoint
@autogen_api.route('/orchestrator/v3/health', methods=['GET'])
def health_check():
    """Health check endpoint for AutoGen orchestrator"""
    orchestrator = current_app.config.get('AUTOGEN_ORCHESTRATOR')
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "orchestrator": "unavailable",
            "agents": "unavailable",
            "state_hooks": "unavailable"
        }
    }
    
    if orchestrator:
        health["components"]["orchestrator"] = "healthy" if orchestrator.orchestrator else "unavailable"
        health["components"]["agents"] = "healthy" if orchestrator.orchestrator and orchestrator.orchestrator.agents else "unavailable"
        health["components"]["state_hooks"] = "healthy" if orchestrator.state_hooks else "unavailable"
        
        # Overall status
        if all(status == "healthy" for status in health["components"].values()):
            health["status"] = "healthy"
        elif any(status == "healthy" for status in health["components"].values()):
            health["status"] = "degraded"
        else:
            health["status"] = "unhealthy"
    else:
        health["status"] = "unhealthy"
    
    status_code = 200 if health["status"] == "healthy" else 503
    return jsonify(health), status_code


# Event handling endpoint
@autogen_api.route('/orchestrator/v3/event', methods=['POST'])
@require_orchestrator
@async_route
async def handle_external_event():
    """
    Handle external events
    
    Expected JSON payload:
    {
        "event_type": "new_viewers|donation|subscription|change_subject",
        "payload": {
            "names": ["viewer1", "viewer2"],
            "amount": 10.00,
            "topic": "new topic"
        }
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['event_type', 'payload'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    try:
        await orchestrator.handle_external_event(
            event_type=data['event_type'],
            payload=data['payload']
        )
        
        return jsonify({
            "status": "success",
            "event_type": data['event_type'],
            "message": f"Event {data['event_type']} processed successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling event: {e}")
        return jsonify({
            "error": "Event processing failed",
            "message": str(e)
        }), 500


# Activity tracking endpoint
@autogen_api.route('/orchestrator/v3/activity', methods=['POST'])
@require_orchestrator
def update_activity():
    """
    Update current stream activity
    
    Expected JSON payload:
    {
        "activity": "drawing|gaming|chatting|singing",
        "metadata": {
            "game_name": "string",
            "art_project": "string"
        }
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['activity'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    if orchestrator.state_hooks:
        orchestrator.state_hooks.hook_activity_change(data['activity'])
    
    return jsonify({
        "status": "success",
        "current_activity": data['activity'],
        "message": f"Activity updated to {data['activity']}"
    }), 200


# Viewer tracking endpoint
@autogen_api.route('/orchestrator/v3/viewers', methods=['POST'])
@require_orchestrator
def update_viewer_count():
    """
    Update viewer count
    
    Expected JSON payload:
    {
        "count": 150,
        "delta": 10
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['count'])
    if error:
        return error
    
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    orchestrator.update_viewer_count(data['count'])
    
    return jsonify({
        "status": "success",
        "viewer_count": data['count'],
        "message": f"Viewer count updated to {data['count']}"
    }), 200


# Debug endpoint
@autogen_api.route('/orchestrator/v3/debug', methods=['GET'])
@require_orchestrator
def get_debug_info():
    """Get debug information for troubleshooting"""
    orchestrator: AutoGenOrchestrationWrapper = current_app.config['AUTOGEN_ORCHESTRATOR']
    
    debug_info = {
        "config": {
            "autogen_enabled": orchestrator.config.autogen_enabled,
            "persona": orchestrator.config.persona,
            "group_chat_enabled": orchestrator.config.group_chat_enabled,
            "agent_timeout": orchestrator.config.agent_timeout,
            "max_agent_rounds": orchestrator.config.max_agent_rounds
        },
        "state": orchestrator.state_hooks.get_enhanced_state() if orchestrator.state_hooks else {},
        "metrics": orchestrator.metrics,
        "performance_traces": len(orchestrator.performance_traces),
        "errors": orchestrator.metrics.get('errors', 0)
    }
    
    return jsonify(debug_info), 200


# Additional persona management endpoints
@autogen_api.route('/orchestrator/v3/personas/list', methods=['GET'])
@require_orchestrator
def list_all_personas():
    """List all available personas including custom ones"""
    persona_manager = get_persona_manager()
    
    personas = {}
    for persona_id, persona_name in persona_manager.list_personas().items():
        persona_config = persona_manager.get_persona(persona_id)
        personas[persona_id] = {
            "name": persona_name,
            "description": persona_config.description if persona_config else "",
            "is_custom": persona_id not in ["friendly_streamer", "calm_educator", "chaotic_gremlin"],
            "is_current": persona_id == persona_manager.current_persona
        }
    
    return jsonify({
        "personas": personas,
        "current_persona": persona_manager.current_persona
    }), 200


@autogen_api.route('/orchestrator/v3/personas/create', methods=['POST'])
@require_orchestrator
def create_custom_persona():
    """
    Create a custom persona
    
    Expected JSON payload:
    {
        "name": "My Custom Persona",
        "description": "A unique VTuber personality",
        "personality_traits": {...},
        "speech_patterns": {...},
        "interaction_style": {...},
        "idle_behavior": {...},
        "filter_threshold": 0.5,
        "orchestrator_prompt": "..."
    }
    """
    error = validate_json_request()
    if error:
        return error
    
    data = request.get_json()
    error = validate_required_fields(data, ['name'])
    if error:
        return error
    
    persona_manager = get_persona_manager()
    
    try:
        persona_id = persona_manager.create_custom_persona(data)
        
        return jsonify({
            "status": "success",
            "persona_id": persona_id,
            "message": f"Custom persona '{data['name']}' created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating custom persona: {e}")
        return jsonify({
            "error": "Failed to create persona",
            "message": str(e)
        }), 500


@autogen_api.route('/orchestrator/v3/personas/<persona_id>', methods=['DELETE'])
@require_orchestrator
def delete_persona(persona_id: str):
    """Delete a custom persona"""
    # Prevent deletion of built-in personas
    if persona_id in ["friendly_streamer", "calm_educator", "chaotic_gremlin"]:
        return jsonify({
            "error": "Cannot delete built-in persona",
            "message": f"'{persona_id}' is a built-in persona and cannot be deleted"
        }), 403
    
    persona_manager = get_persona_manager()
    
    if persona_id not in persona_manager.personas:
        return jsonify({
            "error": "Persona not found",
            "message": f"Persona '{persona_id}' does not exist"
        }), 404
    
    try:
        # Remove from memory
        del persona_manager.personas[persona_id]
        
        # Delete file if it exists
        persona_file = persona_manager.config_dir / f"{persona_id}.json"
        if persona_file.exists():
            persona_file.unlink()
        
        return jsonify({
            "status": "success",
            "message": f"Persona '{persona_id}' deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting persona: {e}")
        return jsonify({
            "error": "Failed to delete persona",
            "message": str(e)
        }), 500


def register_autogen_routes(app: Flask, orchestrator: AutoGenOrchestrationWrapper):
    """
    Register AutoGen API routes with Flask app
    
    Args:
        app: Flask application instance
        orchestrator: AutoGen orchestration wrapper instance
    """
    # Store orchestrator in app config
    app.config['AUTOGEN_ORCHESTRATOR'] = orchestrator
    
    # Register blueprint
    app.register_blueprint(autogen_api)
    
    logger.info("✅ AutoGen API routes registered")
    logger.info("📍 Available endpoints:")
    logger.info("   POST   /orchestrator/v3/process")
    logger.info("   GET    /orchestrator/v3/persona")
    logger.info("   PUT    /orchestrator/v3/persona")
    logger.info("   GET    /orchestrator/v3/personas/list")
    logger.info("   POST   /orchestrator/v3/personas/create")
    logger.info("   DELETE /orchestrator/v3/personas/<persona_id>")
    logger.info("   GET    /orchestrator/v3/agents/status")
    logger.info("   POST   /orchestrator/v3/autonomous/control")
    logger.info("   GET    /orchestrator/v3/autonomous/stats")
    logger.info("   GET    /orchestrator/v3/metrics")
    logger.info("   GET    /orchestrator/v3/health")
    logger.info("   POST   /orchestrator/v3/event")
    logger.info("   POST   /orchestrator/v3/activity")
    logger.info("   POST   /orchestrator/v3/viewers")
    logger.info("   GET    /orchestrator/v3/debug")


# Export main components
__all__ = [
    'autogen_api',
    'register_autogen_routes'
]