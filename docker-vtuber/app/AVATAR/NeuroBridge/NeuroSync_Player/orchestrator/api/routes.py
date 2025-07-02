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


@reactive_api.route('/mode/status', methods=['GET'])
def get_mode_status():
    """Get current mode status"""
    try:
        character_manager = get_character_manager()
        character = character_manager.get_current_character()
        
        return jsonify({
            "current_mode": character_manager.get_current_mode(),
            "autonomous_active": character_manager.autonomous_active,
            "character_supports_autonomous": character.autonomous_enabled if character else False,
            "character_id": character_manager.current_character_id,
            "mode_history": character_manager.mode_history[-5:]  # Last 5 mode switches
        })
    except Exception as e:
        logger.error(f"Error getting mode status: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/mode/switch', methods=['POST'])
@require_orchestrator
def switch_mode():
    """Switch between reactive and autonomous modes"""
    try:
        data = request.get_json() if request.is_json else {}
        mode = data.get('mode', '').lower()
        
        if mode not in ['reactive', 'autonomous']:
            return jsonify({"error": "Mode must be 'reactive' or 'autonomous'"}), 400
        
        character_manager = get_character_manager()
        success = character_manager.switch_mode(mode)
        
        if success:
            return jsonify({
                "success": True,
                "mode": character_manager.get_current_mode(),
                "autonomous_active": character_manager.autonomous_active
            })
        else:
            return jsonify({"error": "Failed to switch mode"}), 400
            
    except Exception as e:
        logger.error(f"Error switching mode: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/mode/autonomous/start', methods=['POST'])
@require_orchestrator
@async_route
async def start_autonomous_mode():
    """Start autonomous content generation"""
    try:
        data = request.get_json() if request.is_json else {}
        topic = data.get('topic')
        
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        character_manager = get_character_manager()
        
        # Switch to autonomous mode if not already
        if not character_manager.is_autonomous_mode():
            character_manager.switch_mode('autonomous')
        
        # Start autonomous content generation
        success = await orchestrator.start_autonomous_mode(topic)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Autonomous mode started",
                "topic": topic,
                "character": character_manager.get_current_character().name
            })
        else:
            return jsonify({"error": "Failed to start autonomous mode"}), 400
            
    except Exception as e:
        logger.error(f"Error starting autonomous mode: {e}")
        return jsonify({"error": str(e)}), 500


@reactive_api.route('/mode/autonomous/stop', methods=['POST'])
@require_orchestrator
def stop_autonomous_mode():
    """Stop autonomous content generation - FIXED event loop handling"""
    try:
        orchestrator: ReactiveOrchestrator = current_app.config['REACTIVE_ORCHESTRATOR']
        character_manager = get_character_manager()
        
        # FIXED: Handle event loop mismatch by using thread-safe cancellation
        if orchestrator.autonomous_task:
            try:
                # Cancel the task directly without await (which causes loop mismatch)
                orchestrator.autonomous_task.cancel()
                logger.info("🛑 Autonomous task cancellation requested")
                
                # Clean up the task reference
                orchestrator.autonomous_task = None
                
            except Exception as e:
                logger.warning(f"⚠️ Error during task cancellation: {e}")
        
        # Stop character manager autonomous mode
        character_manager.stop_autonomous_mode()
        
        logger.info("✅ Autonomous mode stopped successfully")
        
        return jsonify({
            "success": True,
            "message": "Autonomous mode stopped"
        })
        
    except Exception as e:
        logger.error(f"Error stopping autonomous mode: {e}")
        return jsonify({"error": str(e)}), 500


# Event Processing Endpoints
# ==========================

@reactive_api.route('/event/chat', methods=['POST'])
def chat_event():
    """Submit a chat message - SIMPLIFIED to use proven /process_text endpoint"""
    try:
        import requests
        
        data = request.get_json() if request.is_json else {}
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        character_manager = get_character_manager()
        character = character_manager.get_current_character()
        
        # Get conversation history for better continuity
        conversation_context = ""
        try:
            # Try to get recent conversation from the system
            if hasattr(current_app.config, 'REACTIVE_ORCHESTRATOR'):
                orchestrator = current_app.config.get('REACTIVE_ORCHESTRATOR')
                if orchestrator and hasattr(orchestrator, 'conversation_history'):
                    recent_turns = orchestrator.conversation_history.get_recent_turns(limit=4)
                    if recent_turns:
                        conversation_context = "\nRecent Conversation:\n"
                        for turn in recent_turns[-4:]:  # Last 4 turns for context
                            conversation_context += f"{turn['speaker'].title()}: {turn['text'][:100]}...\n"
                        conversation_context += "\n"
        except Exception as e:
            logger.warning(f"Could not get conversation history: {e}")
        
        # Build character-aware prompt for the message
        character_context = ""
        if character:
            character_context = f"""Character Profile: {character.name}
Role: {character.role}

Personality Traits: {', '.join(character.personality_traits) if character.personality_traits else 'helpful, responsive'}
Communication Style: {character.communication_style or 'clear and friendly'}
Emotional Range: {character.emotional_range or 'balanced and positive'}

Behavioral Rules:
- Adapt explanations to student level
- Use examples and analogies  
- Encourage questions
- Provide positive reinforcement
- Continue naturally from recent conversation context
- Build upon previous topics when relevant

{conversation_context}Remember to stay in character and follow these guidelines.


"""
        
        # Create the full prompt with character and conversation context
        full_prompt = f"{character_context}User: {message}\n\nRespond naturally in character, building upon the conversation context if relevant:"
        
        # Call the proven /process_text endpoint directly with orchestrator bypass
        payload = {
            'text': full_prompt,
            'autonomous_context': {
                'source': 'reactive_orchestrator',  # This bypasses orchestrator processing
                'character_id': character.id if character else 'default'
            }
        }
        
        logger.info(f"📨 Sending to /process_text: {message}")
        
        # Call the working endpoint
        response = requests.post(
            'http://localhost:5001/process_text',
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "response": f"Message processed: {message}",
                "character": character.name if character else "default",
                "method": "simplified_process_text"
            })
        else:
            logger.error(f"Error calling /process_text: {response.status_code} - {response.text}")
            return jsonify({"error": "Failed to process message"}), 500
            
    except Exception as e:
        logger.error(f"Error in simplified chat: {e}")
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