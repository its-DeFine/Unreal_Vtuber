"""
API Routes for Reactive VTuber System
Handles character management, external events, and response control
"""

from flask import Blueprint, jsonify, request, current_app
from functools import wraps
import asyncio
import logging
from typing import Dict, Any
import traceback

from character_config import get_character_manager
from reactive_orchestrator import ReactiveOrchestrator

logger = logging.getLogger(__name__)

# Create Blueprint
reactive_api = Blueprint('reactive_api', __name__, url_prefix='/api/v1/reactive')


def require_orchestrator(f):
    """Decorator to ensure orchestrator is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'REACTIVE_ORCHESTRATOR' not in current_app.config:
            return jsonify({"error": "Reactive orchestrator not initialized"}), 503
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


# Character Management Endpoints
# ==============================

@reactive_api.route('/character/list', methods=['GET'])
def list_characters():
    """List all available characters"""
    try:
        character_manager = get_character_manager()
        characters = character_manager.list_characters()
        
        return jsonify({
            "characters": characters,
            "current_character_id": character_manager.current_character_id
        })
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/character/current', methods=['GET'])
def get_current_character():
    """Get the currently active character"""
    try:
        character_manager = get_character_manager()
        character = character_manager.get_current_character()
        
        if not character:
            return jsonify({"error": "No character currently active"}), 404
        
        return jsonify({
            "id": character.id,
            "name": character.name,
            "role": character.role,
            "personality_traits": character.personality_traits,
            "communication_style": character.communication_style,
            "scb_context_lines": character.scb_context_lines,
            "conversation_history_size": character.conversation_history_size
        })
    except Exception as e:
        logger.error(f"Error getting current character: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/character/load', methods=['POST'])
def load_character():
    """Load/switch to a different character"""
    try:
        data = request.get_json() if request.is_json else {}
        character_id = data.get('character_id')
        
        if not character_id:
            return jsonify({"error": "character_id is required"}), 400
        
        character_manager = get_character_manager()
        success = character_manager.switch_character(character_id)
        
        if success:
            character = character_manager.get_current_character()
            return jsonify({
                "success": True,
                "character": {
                    "id": character.id,
                    "name": character.name,
                    "role": character.role
                }
            })
        else:
            return jsonify({"error": f"Character {character_id} not found"}), 404
            
    except Exception as e:
        logger.error(f"Error loading character: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/character/create', methods=['POST'])
def create_character():
    """Create a new character"""
    try:
        data = request.get_json() if request.is_json else {}
        
        # Validate required fields
        required_fields = ['id', 'name', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400
        
        character_manager = get_character_manager()
        character = character_manager.create_character(data)
        
        return jsonify({
            "success": True,
            "character": {
                "id": character.id,
                "name": character.name,
                "role": character.role
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating character: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/character/update', methods=['PUT'])
def update_character():
    """Update current character's configuration"""
    try:
        data = request.get_json() if request.is_json else {}
        character_manager = get_character_manager()
        character = character_manager.get_current_character()
        
        if not character:
            return jsonify({"error": "No character currently active"}), 404
        
        # Update allowed fields
        updatable_fields = [
            'personality_traits', 'communication_style', 'emotional_range',
            'response_patterns', 'behavioral_rules', 'scb_context_lines',
            'conversation_history_size', 'priority_topics'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(character, field, data[field])
        
        # Save updated character
        character_manager.save_character(character)
        
        return jsonify({
            "success": True,
            "character_id": character.id
        })
        
    except Exception as e:
        logger.error(f"Error updating character: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/character/delete/<character_id>', methods=['DELETE'])
def delete_character(character_id: str):
    """Delete a character"""
    try:
        character_manager = get_character_manager()
        success = character_manager.delete_character(character_id)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Cannot delete current character or character not found"}), 400
            
    except Exception as e:
        logger.error(f"Error deleting character: {e}")
        return jsonify({"error": str(e)}), 500


# External Event Endpoints
# ========================

@reactive_api.route('/event/submit', methods=['POST'])
@require_orchestrator
@async_route
async def submit_event():
    """Submit an external event for processing"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        data = request.get_json() if request.is_json else {}
        
        # Validate event data
        if 'type' not in data:
            return jsonify({"error": "Event type is required"}), 400
        
        # Add event to queue
        event_id = await orchestrator.add_external_event(data)
        
        # Process immediately if requested
        if data.get('process_immediately', False):
            await orchestrator.process_event_queue()
        
        return jsonify({
            "success": True,
            "event_id": event_id
        })
        
    except Exception as e:
        logger.error(f"Error submitting event: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/event/chat', methods=['POST'])
@require_orchestrator
@async_route
async def chat_event():
    """Submit a chat message and get immediate response"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        data = request.get_json() if request.is_json else {}
        
        message = data.get('message', '').strip()
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Create chat event
        event_data = {
            'type': 'chat',
            'source': data.get('source', 'api'),
            'priority': 'high',
            'data': {
                'message': message,
                'user_id': data.get('user_id', 'anonymous')
            }
        }
        
        # Add and process immediately
        event_id = await orchestrator.add_external_event(event_data)
        
        # Get the event and process it
        event = next((e for e in orchestrator.state.event_queue if e.id == event_id), None)
        if event:
            response = await orchestrator.process_event(event)
            
            return jsonify({
                "success": True,
                "response": response,
                "event_id": event_id,
                "character": orchestrator.character_manager.get_current_character().name
            })
        else:
            return jsonify({"error": "Event processing failed"}), 500
            
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/event/queue', methods=['GET'])
@require_orchestrator
def get_event_queue():
    """Get current event queue status"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        state = orchestrator.get_state()
        
        return jsonify({
            "event_queue": state['event_queue'],
            "pending_count": len([e for e in state['event_queue'] if not e.get('processed', False)]),
            "processed_count": len([e for e in state['event_queue'] if e.get('processed', False)])
        })
        
    except Exception as e:
        logger.error(f"Error getting event queue: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/event/process', methods=['POST'])
@require_orchestrator
@async_route
async def process_events():
    """Process all pending events in queue"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        await orchestrator.process_event_queue()
        
        state = orchestrator.get_state()
        processed_count = len([e for e in state['event_queue'] if e.get('processed', False)])
        
        return jsonify({
            "success": True,
            "processed_count": processed_count
        })
        
    except Exception as e:
        logger.error(f"Error processing events: {e}")
        return jsonify({"error": str(e)}), 500


# Response Control Endpoints
# ==========================

@reactive_api.route('/response/history', methods=['GET'])
@require_orchestrator
def get_response_history():
    """Get recent response history"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        state = orchestrator.get_state()
        
        return jsonify({
            "recent_responses": state['recent_responses'],
            "last_speech_time": state['last_speech_time']
        })
        
    except Exception as e:
        logger.error(f"Error getting response history: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/response/conversation', methods=['GET'])
@require_orchestrator
def get_conversation_history():
    """Get conversation history"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        limit = request.args.get('limit', 20, type=int)
        
        history = orchestrator.conversation_history.get_recent_turns(limit=limit)
        
        return jsonify({
            "conversation": history,
            "total_turns": len(orchestrator.conversation_history.turns)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/response/clear', methods=['POST'])
@require_orchestrator
def clear_conversation():
    """Clear conversation history"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        orchestrator.conversation_history.clear()
        orchestrator.state.recent_responses.clear()
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        return jsonify({"error": str(e)}), 500


# System Status Endpoints
# =======================

@reactive_api.route('/status', methods=['GET'])
@require_orchestrator
def get_system_status():
    """Get overall system status"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        character_manager = get_character_manager()
        
        state = orchestrator.get_state()
        
        return jsonify({
            "status": "operational",
            "character": state['character'],
            "event_queue_size": len(state['event_queue']),
            "pending_events": len([e for e in state['event_queue'] if not e.get('processed', False)]),
            "is_speaking": state['is_speaking'],
            "total_characters": len(character_manager.characters),
            "scb_connected": orchestrator.scb_client is not None
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@reactive_api.route('/config', methods=['GET'])
@require_orchestrator
def get_config():
    """Get current system configuration"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        
        return jsonify({
            "timing": {
                "min_speech_gap": orchestrator.min_speech_gap,
                "response_timeout": orchestrator.response_timeout
            },
            "anti_repetition": {
                "enabled": orchestrator.enable_anti_repetition,
                "similarity_threshold": orchestrator.similarity_threshold
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/config', methods=['PUT'])
@require_orchestrator
def update_config():
    """Update system configuration"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        data = request.get_json() if request.is_json else {}
        
        # Update timing settings
        if 'timing' in data:
            if 'min_speech_gap' in data['timing']:
                orchestrator.min_speech_gap = float(data['timing']['min_speech_gap'])
            if 'response_timeout' in data['timing']:
                orchestrator.response_timeout = float(data['timing']['response_timeout'])
        
        # Update anti-repetition settings
        if 'anti_repetition' in data:
            if 'enabled' in data['anti_repetition']:
                orchestrator.enable_anti_repetition = bool(data['anti_repetition']['enabled'])
            if 'similarity_threshold' in data['anti_repetition']:
                orchestrator.similarity_threshold = float(data['anti_repetition']['similarity_threshold'])
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500


# Example Event Endpoints
# =======================

@reactive_api.route('/example/email', methods=['POST'])
@require_orchestrator
@async_route
async def send_example_email():
    """Send an example email event"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        
        event_data = {
            'type': 'email',
            'source': 'gmail',
            'priority': 'high',
            'data': {
                'sender': 'boss@company.com',
                'subject': 'Quarterly Review Meeting',
                'preview': 'Please prepare the Q3 sales report for tomorrow\'s meeting...'
            }
        }
        
        event_id = await orchestrator.add_external_event(event_data)
        
        # Process immediately
        event = next((e for e in orchestrator.state.event_queue if e.id == event_id), None)
        if event:
            response = await orchestrator.process_event(event)
            
            return jsonify({
                "success": True,
                "event_id": event_id,
                "response": response
            })
        
        return jsonify({"error": "Failed to process event"}), 500
        
    except Exception as e:
        logger.error(f"Error sending example email: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/example/calendar', methods=['POST'])
@require_orchestrator
@async_route
async def send_example_calendar():
    """Send an example calendar event"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        
        event_data = {
            'type': 'calendar',
            'source': 'google_calendar',
            'priority': 'medium',
            'data': {
                'title': 'Team Standup',
                'type': 'meeting',
                'attendees': 'Development Team',
                'time': '10 minutes',
                'location': 'Conference Room A'
            }
        }
        
        event_id = await orchestrator.add_external_event(event_data)
        
        # Process immediately
        event = next((e for e in orchestrator.state.event_queue if e.id == event_id), None)
        if event:
            response = await orchestrator.process_event(event)
            
            return jsonify({
                "success": True,
                "event_id": event_id,
                "response": response
            })
        
        return jsonify({"error": "Failed to process event"}), 500
        
    except Exception as e:
        logger.error(f"Error sending example calendar: {e}")
        return jsonify({"error": str(e)}), 500 