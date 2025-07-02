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
from ..core.orchestrator import ReactiveOrchestrator

logger = logging.getLogger(__name__)

# Create Blueprint
reactive_api = Blueprint('reactive_api', __name__, url_prefix='/api/v1/reactive')


def _send_to_tts_pipeline(text: str, character_id: str):
    """Send text through the TTS pipeline for audio output"""
    import requests
    
    logger.info(f"_send_to_tts_pipeline called with text: {text[:100]}...")
    
    try:
        payload = {
            'text': text,
            'autonomous_context': {
                'source': 'reactive_orchestrator',
                'character_id': character_id
            },
            'direct_speech': True  # Use direct speech for orchestrator output
        }
        
        logger.info(f"Sending HTTP POST to /process_text for TTS with payload: {payload}")
        
        # Call the process_text endpoint with our response
        response = requests.post(
            'http://localhost:5001/process_text',
            json=payload,
            timeout=10
        )
        
        logger.info(f"TTS HTTP response status: {response.status_code}")
        logger.info(f"TTS HTTP response body: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"Failed to send to TTS pipeline: {response.text}")
        else:
            logger.info(f"Successfully sent response to TTS pipeline")
            
    except Exception as e:
        logger.error(f"Error sending to TTS pipeline: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


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


# Event Processing Endpoints
# ==========================

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
        
        # Add event (high priority events are processed automatically)
        event_id = await orchestrator.add_external_event(event_data)
        
        # Get the event and check if it was already processed
        event = next((e for e in orchestrator.state.event_queue if e.id == event_id), None)
        if event:
            if event.processed:
                # Event was already processed automatically (high priority)
                # Get the response from the recent responses
                recent_responses = list(orchestrator.state.recent_responses)
                response = recent_responses[-1]['text'] if recent_responses else None
            else:
                # Process the event manually
                response = await orchestrator.process_event(event)
            
            # Send response to TTS pipeline for audio output
            if response:
                logger.info(f"Sending chat response to TTS pipeline: {response[:100]}...")
                _send_to_tts_pipeline(response, orchestrator.character_manager.current_character_id)
            
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