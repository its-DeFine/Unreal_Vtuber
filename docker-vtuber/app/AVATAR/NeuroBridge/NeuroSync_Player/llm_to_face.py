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
from config import BASE_SYSTEM_MESSAGE, get_llm_config, setup_warnings

# Import orchestrator components
from orchestrator_integration import OrchestrationWrapper, OrchestrationConfig
from autonomous_orchestrator import Priority, ActionType

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

# Game control system objects
game_control_processor = None
tcp_controller = None

# Orchestrator objects
orchestrator_wrapper = None
orchestrator_config = None

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
    
    llm_config_global = get_llm_config(system_message=BASE_SYSTEM_MESSAGE)
    
    # Enhanced LLM configuration logging
    provider = llm_config_global.get("LLM_PROVIDER", "openai")
    print(f"🤖 LLM Provider: {provider.upper()}")
    
    if provider == "ollama":
        endpoint = llm_config_global.get("OLLAMA_API_ENDPOINT", "http://vtuber-ollama:11434")
        model = llm_config_global.get("OLLAMA_MODEL", "llama3.2:3b")
        streaming = llm_config_global.get("OLLAMA_STREAMING", True)
        print(f"🦙 Ollama Configuration:")
        print(f"   📡 Endpoint: {endpoint}")
        print(f"   🤖 Model: {model}")
        print(f"   ⚡ Streaming: {'Enabled' if streaming else 'Disabled'}")
        
        # Test Ollama connection
        try:
            import requests
            response = requests.get(f"{endpoint}/api/tags", timeout=3)
            if response.ok:
                models = response.json().get('models', [])
                print(f"   ✅ Connection successful ({len(models)} models available)")
                model_names = [m.get('name', 'unknown') for m in models[:3]]
                if model_names:
                    print(f"   📋 Available models: {', '.join(model_names)}")
            else:
                print(f"   ⚠️ Connection warning: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Connection test failed: {e}")
            print("   💡 Make sure Ollama is running: docker-compose -f docker-compose.ollama.yml up -d")
            
    elif provider == "openai":
        model = llm_config_global.get("OPENAI_MODEL", "gpt-4o")
        api_key = llm_config_global.get("OPENAI_API_KEY", "")
        print(f"🎯 OpenAI Configuration:")
        print(f"   🤖 Model: {model}")
        print(f"   🔑 API Key: {'✅ Set' if api_key else '❌ Missing'}")
        
    elif provider == "custom_local":
        api_url = llm_config_global.get("LLM_API_URL", "")
        stream_url = llm_config_global.get("LLM_STREAM_URL", "")
        print(f"🔧 Custom Local LLM Configuration:")
        print(f"   📡 API URL: {api_url}")
        print(f"   🌊 Stream URL: {stream_url}")
    
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


def setup_orchestration():
    """Initialize the autonomous orchestrator"""
    global orchestrator_wrapper, orchestrator_config, system_objects
    
    print("🤖 Initializing Autonomous Orchestration System...")
    print("=" * 70)
    
    orchestrator_config = OrchestrationConfig()
    
    if orchestrator_config.enabled:
        print("✅ Autonomous Orchestration: ENABLED")
        print(f"🎯 Configuration:")
        for line in str(orchestrator_config).split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Create orchestration wrapper with system objects
        orchestrator_wrapper = OrchestrationWrapper(app, orchestrator_config, system_objects)
        
        # Add custom routes for orchestrator
        add_orchestrator_routes()
        
        print("✅ Autonomous Orchestrator ready!")
        print("🚀 System will now make autonomous decisions about speech and environment!")
        
    else:
        print("⚠️ Autonomous Orchestration: DISABLED")
        print("💡 Set AUTONOMOUS_ORCHESTRATION_ENABLED=true to enable")
        orchestrator_wrapper = None
    
    print("=" * 70)
    return orchestrator_wrapper


def add_orchestrator_routes():
    """Add orchestrator-specific routes"""
    
    @app.route("/orchestrator/status", methods=['GET'])
    def orchestrator_status():
        if not orchestrator_wrapper:
            return jsonify({"error": "Orchestrator not enabled"}), 503
        
        status = orchestrator_wrapper.get_orchestrator_status()
        return jsonify(status), 200
    
    @app.route("/orchestrator/control", methods=['POST'])
    def orchestrator_control():
        if not orchestrator_wrapper:
            return jsonify({"error": "Orchestrator not enabled"}), 503
        
        if not request.json:
            return jsonify({"error": "Missing JSON payload"}), 400
        
        action = request.json.get('action')
        
        if action == "interrupt":
            orchestrator_wrapper.interrupt_current_activities()
            return jsonify({"status": "interrupted"}), 200
            
        elif action == "queue_speech":
            text = request.json.get('text', '')
            priority = request.json.get('priority', 'medium')
            interrupt = request.json.get('interrupt', False)
            
            if not text:
                return jsonify({"error": "Missing text for speech"}), 400
            
            orchestrator_wrapper.queue_speech_action(text, priority, interrupt)
            return jsonify({"status": "queued", "action": "speech", "text": text}), 200
            
        elif action == "queue_environment":
            prompt = request.json.get('prompt', '')
            priority = request.json.get('priority', 'medium')
            interrupt = request.json.get('interrupt', False)
            
            if not prompt:
                return jsonify({"error": "Missing prompt for environment"}), 400
            
            orchestrator_wrapper.queue_environment_action(prompt, priority, interrupt)
            return jsonify({"status": "queued", "action": "environment", "prompt": prompt}), 200
            
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400


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

    # Check if this is a request FROM the orchestrator to prevent infinite loops
    is_from_orchestrator = autonomous_context and (
        "orchestrator_speech" in str(autonomous_context) or 
        "orchestrator_environment" in str(autonomous_context)
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
        
        # Send directly to TTS as a single chunk
        chunk_queue.put(user_input)
        chunk_queue.put(None)  # End marker
        
        # Log to SCB
        from utils.scb import scb_store
        scb_store.append_chat(user_input, actor="orchestrator")
        
        response_data = {
            "status": "direct_speech",
            "message": "Direct speech sent to TTS",
            "llm_provider": "none",
            "orchestrator_enabled": orchestrator_wrapper is not None
        }
        
    # Orchestrator processing - only if enabled AND not from orchestrator itself AND not direct speech
    elif (orchestrator_wrapper and 
        not is_from_orchestrator and
        orchestrator_wrapper.should_orchestrate_request(user_input, autonomous_context)):
        app.logger.info("🎭 Orchestrator handling request")
        orchestrator_wrapper.process_orchestrated_input(user_input, autonomous_context)
        
        response_data = {
            "status": "orchestrated",
            "message": "Input processed by autonomous orchestrator",
            "llm_provider": provider,
            "orchestrator_enabled": True
        }
    else:
        # Standard LLM processing
        chunk_queue = system_objects['chunk_queue']
        audio_queue = system_objects['audio_queue']
        
        # Update orchestrator state even for non-orchestrated requests
        if orchestrator_wrapper and orchestrator_wrapper.state_hooks:
            orchestrator_wrapper.state_hooks.hook_conversation_input(user_input, autonomous_context)
        
        # Normal LLM processing
        updated_chat_history = process_turn(
            user_input, 
            chat_history_global, 
            full_history_global, 
            llm_config_global, 
            chunk_queue, 
            audio_queue, 
            vector_db, 
            base_system_message=BASE_SYSTEM_MESSAGE,
            autonomous_context=autonomous_context
        )
        chat_history_global = updated_chat_history

        response_data = {
            "status": "processing", 
            "message": "Input processed.",
            "llm_provider": provider,
            "orchestrator_enabled": orchestrator_wrapper is not None
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

    # Orchestrator processing for game control
    if orchestrator_wrapper and orchestrator_wrapper.state_hooks:
        orchestrator_wrapper.state_hooks.hook_environment_change_start(game_prompt)
    
    # Process the game control prompt asynchronously
    async def process_game_control():
        try:
            commands = await game_control_processor.process_game_control_prompt(game_prompt)
            
            if not commands:
                app.logger.info("📝 No game commands generated")
                return {"commands": [], "results": {"success": 0, "failed": 0, "total": 0}}
            
            results = await tcp_controller.send_commands_batch(commands)
            
            app.logger.info(f"🎯 Game control complete: {results['success']}/{results['total']} commands successful")
            
            # Notify orchestrator of completion
            if orchestrator_wrapper and orchestrator_wrapper.state_hooks:
                success = results['success'] > 0
                orchestrator_wrapper.state_hooks.hook_environment_change_end(game_prompt, success)
            
            return {"commands": commands, "results": results}
            
        except Exception as e:
            app.logger.error(f"❌ Game control processing error: {e}")
            if orchestrator_wrapper and orchestrator_wrapper.state_hooks:
                orchestrator_wrapper.state_hooks.hook_environment_change_end("error", False)
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
        "orchestrator_enabled": orchestrator_wrapper is not None
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


def start_orchestrator_async():
    """Start the orchestrator in a separate thread with persistent event loop"""
    if orchestrator_wrapper:
        # Create and set a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Start orchestrator and keep loop running
            loop.run_until_complete(orchestrator_wrapper.start_orchestrator())
            
            # Keep the loop running to maintain background tasks
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            else:
                # If no background tasks, run forever until stopped
                loop.run_forever()
                
        except Exception as e:
            print(f"❌ Orchestrator thread error: {e}")
        finally:
            # Clean shutdown
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()


def cleanup_resources():
    global system_objects, orchestrator_wrapper
    
    print("Cleaning up resources...")
    
    # Stop orchestrator first
    if orchestrator_wrapper:
        print("Stopping autonomous orchestrator...")
        try:
            asyncio.run(orchestrator_wrapper.stop_orchestrator())
        except Exception as e:
            print(f"Warning: Error stopping orchestrator: {e}")
    
    # Clean up original system objects
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
    
    print("Resources cleaned up.")


if __name__ == "__main__":
    log_file, original_stdout = setup_logging_and_tee()
    
    try:
        # Initialize core system
        main_setup()
        
        # Initialize orchestration
        orchestrator_wrapper = setup_orchestration()
        
        # Start orchestrator in background thread if enabled
        if orchestrator_wrapper:
            orchestrator_thread = threading.Thread(
                target=start_orchestrator_async, 
                daemon=True,
                name="AutonomousOrchestrator"
            )
            orchestrator_thread.start()
            print("🚀 Autonomous orchestrator thread started!")
        
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
        
        print("🎭 AUTONOMOUS VTUBER SYSTEM READY!")
        print("=" * 70)
        print("📡 HTTP API Endpoints:")
        print("   /process_text - Process text input (with autonomous decisions)")
        print("   /game_control - Control game environment (with autonomous decisions)")
        print("   /orchestrator/status - Get orchestrator status")
        print("   /orchestrator/control - Manual orchestrator control")
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
