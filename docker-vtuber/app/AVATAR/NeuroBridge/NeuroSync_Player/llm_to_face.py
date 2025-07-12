# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

# llm_to_face_orchestrated.py - NeuroSync Player with Autonomous Orchestration
import pygame
import time      
import sys
import os
import threading
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

from livelink.animations.default_animation import stop_default_animation
from utils.vector_db.vector_db import vector_db
from utils.llm.turn_processing import process_turn
from utils.llm.llm_initialiser import initialize_system
from utils.game_control.game_control_processor import GameControlProcessor
from utils.game_control.unreal_tcp_controller import UnrealTCPController, TCPConnectionConfig
from config import get_llm_config, setup_warnings

# S1 system - no orchestrator needed, stimuli-driven only

# --- Global Variables for Flask App ---
app = Flask(__name__)
CORS(app)

# Shared flag path with server_adapter.py
WINDOW_ACTIVE_FLAG_PATH = "/app/neurosync_window_active.flag"

# Read the environment variable to control payment requirement
VTUBER_PAYMENT_ENABLED = os.getenv("VTUBER_PAYMENT_ENABLED", "true").lower() == "true"
# Log the status of payment requirement at startup
app.logger.info(f"VTuber payment requirement is {'ENABLED' if VTUBER_PAYMENT_ENABLED else 'DISABLED'} in llm_to_face_orchestrated.")

# System objects - to be initialized once
system_objects = None
llm_config_global = None
chat_history_global = None
full_history_global = None

# Global character state for Flask app context
current_character_id = None
current_character_data = None

# Game control system objects
game_control_processor = None
tcp_controller = None

# S1 system - orchestrator functionality removed

# --- End Global Variables ---

setup_warnings()

# --- Class to Tee stdout to a file and original stdout ---
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

def setup_logging_and_tee():
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(logs_dir, f"orchestrated_player_log_{timestamp}.txt")
    original_stdout = sys.stdout
    log_file = open(log_file_path, 'w', encoding='utf-8')
    sys.stdout = Tee(original_stdout, log_file)
    print(f"--- NeuroSync Player Orchestrated Log Initialized: {timestamp} ---")
    print(f"Logging to: {os.path.abspath(log_file_path)}")
    return log_file, original_stdout


def main_setup():
    global system_objects, llm_config_global, chat_history_global, full_history_global
    global game_control_processor, tcp_controller

    print("🚀 Initializing NeuroSync Player with Autonomous Orchestration")
    print("=" * 70)
    
    # === LLM Configuration Setup ===
    # Get LLM configuration with character-aware system message (NOT hardcoded Livy)
    llm_config_global = get_llm_config()  # Now uses character-aware system message by default
    
    app.logger.info(f"🤖 LLM Configuration: Provider={llm_config_global.get('LLM_PROVIDER', 'unknown')}")
    app.logger.info(f"🎭 System Message Source: Character-aware (not hardcoded Livy)")
    app.logger.info(f"📝 System Message Preview: {llm_config_global.get('system_message', '')[:100]}...")
    
    streaming = llm_config_global.get("USE_STREAMING", True)
    print(f"⚡ Streaming: {'Enabled' if streaming else 'Disabled'}")
    print(f"🧠 Vector DB: {'Enabled' if llm_config_global.get('USE_VECTOR_DB') else 'Disabled'}")
    print("=" * 70)
    
    system_objects = initialize_system()
    chat_history_global = system_objects['chat_history']
    full_history_global = system_objects['full_history']
    
    # Initialize Game Control System
    print("🎮 Initializing Game Control System...")
    try:
        game_control_processor = GameControlProcessor()
        
        tcp_host = os.getenv("UNREAL_TCP_HOST", "host.docker.internal")
        tcp_port = int(os.getenv("UNREAL_TCP_PORT", "7777"))
        tcp_config = TCPConnectionConfig(host=tcp_host, port=tcp_port)
        tcp_controller = UnrealTCPController(tcp_config)
        
        print(f"🎯 Game Control ready - TCP: {tcp_host}:{tcp_port}")
    except Exception as e:
        print(f"⚠️ Game Control initialization failed: {e}")
        print("💡 Game control features will be disabled")
        game_control_processor = None
        tcp_controller = None
    
    print("✅ NeuroSync Player System Initialized for Orchestrated HTTP interaction.")
    print("💡 Ready to process autonomous VTuber interactions!")


def setup_s1_system():
    """Initialize S1 avatar system - stimuli-driven only"""
    print("🎯 S1 Avatar System Initialized")
    print("=" * 70)
    print("✅ Pure Stimuli-Driven Architecture Active")
    print("💡 S1 Avatar responds to external stimuli from S2 system")
    print("🎯 All intelligence and decision-making handled by S2")
    print("=" * 70)
    return True


# Routes are now handled by the version manager and registered automatically

@app.route("/health", methods=['GET'])
def health():
    """Health check endpoint for GraphFlow integration"""
    global system_objects, llm_config_global
    
    try:
        # Check if system is initialized
        is_initialized = system_objects is not None and llm_config_global is not None
        
        # S1 system status - always stimuli_triggered
        s1_status = "stimuli_triggered"
        
        # Check if payment window is active (if payment is enabled)
        payment_status = "disabled"
        if VTUBER_PAYMENT_ENABLED:
            payment_status = "active" if os.path.exists(WINDOW_ACTIVE_FLAG_PATH) else "inactive"
        
        status = {
            "status": "healthy" if is_initialized else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "system_initialized": is_initialized,
            "s1_status": s1_status,
            "stimuli_triggered": True,
            "payment_status": payment_status,
            "llm_provider": llm_config_global.get('provider', 'unknown') if llm_config_global else 'unknown'
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.route("/process_text", methods=['POST'])
def handle_process_text():
    global chat_history_global, full_history_global

    # Check payment window if enabled
    if VTUBER_PAYMENT_ENABLED:
        if not os.path.exists(WINDOW_ACTIVE_FLAG_PATH):
            app.logger.warning(f"Request to /process_text denied (Payment Enabled): Rolling window not active")
            return jsonify({"error": "Worker is idle – no active job window"}), 403
        else:
            app.logger.info(f"Payment Enabled: Window active, proceeding with /process_text.")
    else:
        app.logger.info(f"Payment DISABLED: Bypassing window active check for /process_text")

    if not request.json or 'text' not in request.json:
        app.logger.warning("/process_text: Missing 'text' in JSON payload")
        return jsonify({"error": "Missing 'text' in JSON payload"}), 400
    
    user_input = request.json['text']
    if not user_input:
        app.logger.warning("/process_text: Input text cannot be empty")
        return jsonify({"error": "Input text cannot be empty"}), 400

    autonomous_context = request.json.get('autonomous_context', None)
    direct_speech = request.json.get('direct_speech', False)
    
    provider = llm_config_global.get("LLM_PROVIDER", "openai")
    app.logger.info(f"📝 Processing text with {provider.upper()}: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
    
    if autonomous_context:
        app.logger.info(f"🤖 Autonomous context detected: {autonomous_context}")
    
    if direct_speech:
        app.logger.info(f"🎯 Direct speech mode - bypassing LLM")

    def clean_speech_text(text: str) -> str:
        """Clean text for speech by removing unwanted characters and extracting content"""
        if not text:
            return text
        
        # Extract content after "CONTENT:" if present (orchestrator output format)
        if "CONTENT:" in text:
            # Split by "CONTENT:" and take the part after it
            content_part = text.split("CONTENT:", 1)[1]
            
            # Remove "TYPE:" section if present (orchestrator also includes TYPE: info)
            if "TYPE:" in content_part:
                content_part = content_part.split("TYPE:")[0]
            
            text = content_part.strip()
        
        # Remove asterisks and other stage directions
        cleaned = text.replace('*', '')
        
        # Remove other common unwanted characters
        cleaned = cleaned.replace('[', '').replace(']', '')
        cleaned = cleaned.replace('(', '').replace(')', '')
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()

    # Check if this is a request FROM the orchestrator to prevent infinite loops
    is_from_orchestrator = autonomous_context and (
        "orchestrator_speech" in str(autonomous_context) or 
        "orchestrator_environment" in str(autonomous_context) or
        "autogen_orchestrator_v3" in str(autonomous_context) or
        (isinstance(autonomous_context, dict) and 
         autonomous_context.get("source") in ["autogen_orchestrator_v3", "autonomous_content", "reactive_orchestrator"])
    )
    
    # Check if this is direct speech that should bypass LLM
    should_use_direct_speech = (
        direct_speech or 
        (autonomous_context and isinstance(autonomous_context, dict) and 
         autonomous_context.get("direct_speech", False))
    )
    

    
    # Direct speech processing - highest priority
    if should_use_direct_speech and is_from_orchestrator:
        # Direct speech - skip LLM and send directly to TTS
        app.logger.info(f"🗣️ Direct speech: {user_input[:100]}...")
        
        # Clean the text for speech
        cleaned_text = clean_speech_text(user_input)
        app.logger.info(f"🧹 Cleaned speech: {cleaned_text[:100]}...")
        
        # Get necessary objects
        chunk_queue = system_objects['chunk_queue']
        audio_queue = system_objects['audio_queue']
        
        # Flush queues first
        from utils.llm.turn_processing import flush_queue
        flush_queue(chunk_queue)
        flush_queue(audio_queue)
        
        # Stop any playing audio
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        
        # Process direct speech through existing TTS pipeline
        # Simply put the cleaned text directly into the chunk queue for the TTS worker
        app.logger.info(f"🎯 Processing direct speech through TTS pipeline")
        
        # Put the complete cleaned text as a single chunk for TTS processing
        chunk_queue.put(cleaned_text)
        app.logger.info(f"✅ Direct speech chunk queued for TTS processing: {cleaned_text[:50]}...")
        
        # Log to SCB
        from utils.scb import scb_store
        scb_store.append_chat(cleaned_text, actor="orchestrator")
        
        response_data = {
            "status": "direct_speech",
            "message": "Direct speech processed through TTS pipeline",
            "llm_provider": "none",
            "s1_system": True
        }
        
    # Orchestrator processing - DISABLED to prevent duplicate processing
    # Our simplified API route handles character-aware responses directly
    elif False:  # Temporarily disabled to eliminate duplicate processing
        pass
    else:
        # Standard LLM processing
        chunk_queue = system_objects['chunk_queue']
        audio_queue = system_objects['audio_queue']
        
        # S1 system - no orchestrator state management needed
        
        # Normal LLM processing with dynamic character-aware system message
        from config import get_character_aware_system_message
        current_system_message = get_character_aware_system_message()
        
        # Fallback: Use Flask app global character state if character manager fails
        global current_character_data
        if current_system_message == llm_config_global.get('system_message', '') and current_character_data:
            app.logger.info(f"🔄 Using Flask app character state fallback: {current_character_data.name}")
            current_system_message = current_character_data.to_prompt_context()
        
        updated_chat_history = process_turn(
            user_input, 
            chat_history_global, 
            full_history_global, 
            llm_config_global, 
            chunk_queue, 
            audio_queue, 
            vector_db, 
            base_system_message=current_system_message,
            autonomous_context=autonomous_context
        )
        chat_history_global = updated_chat_history

        response_data = {
            "status": "processing", 
            "message": "Input processed.",
            "llm_provider": provider,
            "s1_system": True
        }
    
    app.logger.info(f"✅ Text processing completed with {provider}")
    return jsonify(response_data), 200


@app.route("/game_control", methods=['POST'])
def handle_game_control():
    """Handle game control requests to modify Unreal Engine avatar/environment"""
    global game_control_processor, tcp_controller
    
    if not game_control_processor or not tcp_controller:
        app.logger.warning("🚫 Game control system not initialized")
        return jsonify({"error": "Game control system unavailable"}), 503
    
    # Check payment/window guard if enabled
    if VTUBER_PAYMENT_ENABLED:
        if not os.path.exists(WINDOW_ACTIVE_FLAG_PATH):
            app.logger.warning(f"Request to /game_control denied (Payment Enabled): Rolling window not active")
            return jsonify({"error": "Worker is idle – no active job window"}), 403
        else:
            app.logger.info(f"Payment Enabled: Window active, proceeding with /game_control.")
    else:
        app.logger.info(f"Payment DISABLED: Bypassing window active check for /game_control")
    
    if not request.json or 'prompt' not in request.json:
        app.logger.warning("/game_control: Missing 'prompt' in JSON payload")
        return jsonify({"error": "Missing 'prompt' in JSON payload"}), 400
    
    game_prompt = request.json['prompt']
    if not game_prompt:
        app.logger.warning("/game_control: Game prompt cannot be empty")
        return jsonify({"error": "Game prompt cannot be empty"}), 400
    
    autonomous_context = request.json.get('autonomous_context', None)
    
    app.logger.info(f"🎮 Processing game control prompt: {game_prompt}")
    
    if autonomous_context:
        app.logger.info(f"🤖 Autonomous context for game control: {autonomous_context}")

    # S1 system - no orchestrator processing needed
    
    # Process the game control prompt asynchronously
    async def process_game_control():
        try:
            commands = await game_control_processor.process_game_control_prompt(game_prompt)
            
            if not commands:
                app.logger.info("📝 No game commands generated")
                return {"commands": [], "results": {"success": 0, "failed": 0, "total": 0}}
            
            results = await tcp_controller.send_commands_batch(commands)
            
            app.logger.info(f"🎯 Game control complete: {results['success']}/{results['total']} commands successful")
            
            # S1 system - no orchestrator notification needed
            
            return {"commands": commands, "results": results}
            
        except Exception as e:
            app.logger.error(f"❌ Game control processing error: {e}")
            # S1 system - no orchestrator error handling needed
            return {"error": str(e), "commands": [], "results": {"success": 0, "failed": 0, "total": 0}}
    
    # Run the async processing
    try:
        if hasattr(asyncio, 'run'):
            result = asyncio.run(process_game_control())
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(process_game_control())
            finally:
                loop.close()
    except Exception as e:
        app.logger.error(f"❌ Async execution error: {e}")
        return jsonify({"error": "Processing failed", "details": str(e)}), 500
    
    # Return results
    response_data = {
        "status": "completed",
        "prompt": game_prompt,
        "commands_generated": len(result.get("commands", [])),
        "commands_successful": result.get("results", {}).get("success", 0),
        "commands_failed": result.get("results", {}).get("failed", 0),
        "tcp_host": tcp_controller.config.host,
        "tcp_port": tcp_controller.config.port,
        "s1_system": True
    }
    
    if "results" in result and "commands" in result["results"]:
        response_data["command_details"] = result["results"]["commands"]
    
    if "error" in result:
        response_data["error"] = result["error"]
        return jsonify(response_data), 500
    
    app.logger.info(f"✅ Game control completed: {response_data['commands_successful']} successful commands")
    return jsonify(response_data), 200


@app.route("/game_control/health", methods=['GET'])
def handle_game_control_health():
    """Health check endpoint for game control system"""
    global game_control_processor, tcp_controller
    
    if not game_control_processor or not tcp_controller:
        return jsonify({
            "status": "unavailable",
            "message": "Game control system not initialized",
            "features": None
        }), 503
    
    app.logger.info("🔍 Performing game control health check")
    
    async def check_health():
        try:
            tcp_health = await tcp_controller.health_check()
            features = game_control_processor.get_supported_features()
            
            return {
                "status": "healthy" if tcp_health["overall"] == "healthy" else "degraded",
                "tcp_connection": tcp_health,
                "features": features,
                "processor_available": True,
                "controller_available": True
            }
        except Exception as e:
            app.logger.error(f"❌ Health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "tcp_connection": None,
                "features": None,
                "processor_available": game_control_processor is not None,
                "controller_available": tcp_controller is not None
            }
    
    try:
        if hasattr(asyncio, 'run'):
            result = asyncio.run(check_health())
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(check_health())
            finally:
                loop.close()
    except Exception as e:
        app.logger.error(f"❌ Health check execution error: {e}")
        return jsonify({
            "status": "error",
            "message": "Health check failed to execute",
            "error": str(e)
        }), 500
    
    status_code = 200
    if result["status"] == "unhealthy":
        status_code = 503
    elif result["status"] == "degraded":
        status_code = 200
    
    app.logger.info(f"📊 Game control health: {result['status']}")
    return jsonify(result), status_code


@app.route("/game_control/features", methods=['GET'])
def handle_game_control_features():
    """Get supported game control features and commands"""
    global game_control_processor
    
    if not game_control_processor:
        return jsonify({"error": "Game control system not available"}), 503
    
    try:
        features = game_control_processor.get_supported_features()
        return jsonify({
            "status": "available",
            "features": features,
            "example_commands": {
                "hair_color_red": ["HCR.0.9", "HCG.0.1", "HCB.0.1"],
                "hair_color_blue": ["HCR.0.1", "HCG.0.3", "HCB.0.9"],
                "medieval_scene": ["LVL.Medieval"],
                "feminine_maid": ["PRS.Fem", "OF.Maid Dress"],
                "night_atmosphere": ["SNH.0.1", "STRB.0.9"]
            },
            "usage": {
                "endpoint": "/game_control",
                "method": "POST",
                "payload": {"prompt": "yellow hair, medieval scene"},
                "example_prompts": [
                    "yellow hair, medieval scene",
                    "blue hair, bigger eyes, DJ scene", 
                    "feminine character, maid dress, red hair",
                    "night time, bright stars",
                    "dance animation"
                ]
            }
        }), 200
    except Exception as e:
        app.logger.error(f"❌ Error getting features: {e}")
        return jsonify({"error": "Failed to get features", "details": str(e)}), 500


@app.route("/character/list", methods=['GET'])
def handle_character_list():
    """Get list of available characters"""
    try:
        from character_config import get_character_manager
        character_manager = get_character_manager()
        characters = character_manager.list_characters()
        
        response_data = {
            "status": "success",
            "characters": characters,
            "current_character": character_manager.current_character_id,
            "total_characters": len(characters)
        }
        
        app.logger.info(f"📋 Character list retrieved: {len(characters)} characters")
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.error(f"❌ Error getting character list: {e}")
        return jsonify({"error": "Failed to get character list", "details": str(e)}), 500


@app.route("/character/current", methods=['GET'])
def handle_current_character():
    """Get current character information"""
    try:
        from character_config import get_character_manager
        character_manager = get_character_manager()
        current_character = character_manager.get_current_character()
        
        if not current_character:
            return jsonify({"error": "No character currently active"}), 404
        
        response_data = {
            "status": "success",
            "character": {
                "id": current_character.id,
                "name": current_character.name,
                "role": current_character.role,
                "personality_traits": current_character.personality_traits,
                "communication_style": current_character.communication_style,
                "domain_expertise": current_character.domain_expertise,
                "formality_level": current_character.formality_level
            }
        }
        
        app.logger.info(f"🎭 Current character retrieved: {current_character.name}")
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.error(f"❌ Error getting current character: {e}")
        return jsonify({"error": "Failed to get current character", "details": str(e)}), 500


@app.route("/character/switch", methods=['POST'])
def handle_character_switch():
    """Switch to a different character"""
    global current_character_id, current_character_data
    
    try:
        if not request.json or 'character_id' not in request.json:
            app.logger.warning("/character/switch: Missing 'character_id' in JSON payload")
            return jsonify({"error": "Missing 'character_id' in JSON payload"}), 400
        
        character_id = request.json['character_id']
        
        from character_config import get_character_manager
        character_manager = get_character_manager()
        
        # Attempt to switch character
        success = character_manager.switch_character(character_id)
        
        if success:
            current_character = character_manager.get_current_character()
            
            # Update global Flask app state
            current_character_id = character_id
            current_character_data = current_character
            
            response_data = {
                "status": "success",
                "message": f"Successfully switched to character: {current_character.name}",
                "previous_character": request.json.get('previous_character_id'),
                "current_character": {
                    "id": current_character.id,
                    "name": current_character.name,
                    "role": current_character.role
                }
            }
            app.logger.info(f"🎭 Character switched to: {current_character.name}")
            return jsonify(response_data), 200
        else:
            return jsonify({"error": f"Failed to switch to character: {character_id}"}), 400
            
    except Exception as e:
        app.logger.error(f"❌ Error switching character: {e}")
        return jsonify({"error": "Failed to switch character", "details": str(e)}), 500


@app.route("/character/create", methods=['POST'])
def handle_character_create():
    """Create a new character from template or custom data"""
    try:
        if not request.json:
            return jsonify({"error": "Missing character data"}), 400
        
        from character_config import get_character_manager
        character_manager = get_character_manager()
        
        # Create character from provided data
        character = character_manager.create_character(request.json)
        
        # Save the character
        character_manager.save_character(character)
        
        response_data = {
            "status": "success",
            "message": f"Character created successfully: {character.name}",
            "character": {
                "id": character.id,
                "name": character.name,
                "role": character.role
            }
        }
        
        app.logger.info(f"🎭 Character created: {character.name}")
        return jsonify(response_data), 201
        
    except Exception as e:
        app.logger.error(f"❌ Error creating character: {e}")
        return jsonify({"error": "Failed to create character", "details": str(e)}), 500


def s1_keepalive():
    """Simple keepalive for S1 system - no background processing needed"""
    app.logger.info("✅ S1 system keepalive started")
    app.logger.info("📌 S1 avatar ready for stimuli from S2 system")
    
    # Simple keepalive loop
    import time
    while True:
        time.sleep(30)  # S1 system keepalive


def cleanup_resources():
    global system_objects
    
    print("Cleaning up S1 system resources...")
    
    # Clean up system objects
    if system_objects:
        system_objects['chunk_queue'].join()
        system_objects['chunk_queue'].put(None)
        system_objects['tts_worker_thread'].join()
        system_objects['audio_queue'].join()
        system_objects['audio_queue'].put(None)
        system_objects['audio_worker_thread'].join()
        stop_default_animation.set()
        system_objects['default_animation_thread'].join()
        pygame.quit()
        if system_objects.get('socket_connection'):
            system_objects['socket_connection'].close()
    
    print("S1 system resources cleaned up.")


if __name__ == "__main__":
    log_file, original_stdout = setup_logging_and_tee()
    
    try:
        # Initialize core system
        main_setup()
        
        # Initialize S1 system
        s1_initialized = setup_s1_system()
        
        # Start S1 keepalive thread
        if s1_initialized:
            s1_thread = threading.Thread(
                target=s1_keepalive, 
                daemon=True,
                name="S1Keepalive"
            )
            s1_thread.start()
            print("🚀 S1 system keepalive thread started!")
        
        # Configure Flask logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(module)s : %(message)s',
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        ))
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

        flask_port = int(os.getenv("PLAYER_PORT", "5001"))
        app.logger.info(f"🌐 Starting NeuroSync Player Orchestrated HTTP server on port {flask_port}...")
        
        print("🎭 S1 AVATAR SYSTEM READY!")
        print("=" * 70)
        print("📡 HTTP API Endpoints:")
        print("   /process_text - Process text input (stimuli-driven)")
        print("   /game_control - Control game environment (stimuli-driven)")
        print("   /health - System health status")
        print("   /character/* - Character management endpoints")
        print("=" * 70)
        
        app.run(host='0.0.0.0', port=flask_port, debug=False)
        
    except KeyboardInterrupt:
        print("Flask server shutting down...")
    finally:
        cleanup_resources()
        if log_file:
            print(f"\n--- NeuroSync Player Orchestrated Log Ended: {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')} ---")
            log_file.close()
        sys.stdout = original_stdout
        app.logger.info("NeuroSync Player Orchestrated server stopped.")
        print("NeuroSync Player Orchestrated server stopped.")
