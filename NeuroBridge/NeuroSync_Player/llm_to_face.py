# This software is licensed under a **dual-license model**
# For individuals and businesses earning **under $1M per year**, this software is licensed under the **MIT License**
# Businesses or organizations with **annual revenue of $1,000,000 or more** must obtain permission to use this software commercially.

# llm_to_face.py
import pygame
# import keyboard # No longer needed for main text interaction
import time      
import sys
import os
from datetime import datetime
from flask import Flask, request, jsonify # Added Flask imports
from flask_cors import CORS # Added CORS for broader compatibility if accessed from different origins
import logging

from livelink.animations.default_animation import  stop_default_animation
# from utils.stt.transcribe_whisper import transcribe_audio # Part of push-to-talk, will be addressed if that mode is reimplemented
# from utils.audio.record_audio import record_audio_until_release # Part of push-to-talk
from utils.vector_db.vector_db import vector_db
from utils.llm.turn_processing import process_turn
from utils.llm.llm_initialiser import initialize_system
from config import BASE_SYSTEM_MESSAGE, get_llm_config, setup_warnings

# --- Global Variables for Flask App ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Shared flag path with server_adapter.py
WINDOW_ACTIVE_FLAG_PATH = "/app/neurosync_window_active.flag"

# Read the environment variable to control payment requirement
VTUBER_PAYMENT_ENABLED = os.getenv("VTUBER_PAYMENT_ENABLED", "true").lower() == "true"
# Log the status of payment requirement at startup
app.logger.info(f"VTuber payment requirement is {'ENABLED' if VTUBER_PAYMENT_ENABLED else 'DISABLED'} in llm_to_face.")

# System objects - to be initialized once
system_objects = None
llm_config_global = None
chat_history_global = None # Manage chat history globally for the session
full_history_global = None   # Manage full history globally

# --- End Global Variables ---

setup_warnings()
# llm_config = get_llm_config(system_message=BASE_SYSTEM_MESSAGE) # Moved to main_setup

# --- Class to Tee stdout to a file and original stdout ---
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()  # If you want the output to be visible immediately
    def flush(self):
        for f in self.files:
            f.flush()

def setup_logging_and_tee():
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(logs_dir, f"player_log_{timestamp}.txt")
    original_stdout = sys.stdout
    log_file = open(log_file_path, 'w', encoding='utf-8')
    sys.stdout = Tee(original_stdout, log_file)
    print(f"--- NeuroSync Player Log Initialized: {timestamp} ---")
    print(f"Logging to: {os.path.abspath(log_file_path)}\\n")
    return log_file, original_stdout


def main_setup():
    global system_objects, llm_config_global, chat_history_global, full_history_global

    print("🚀 Initializing NeuroSync Player with Local LLM Support")
    print("=" * 60)
    
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
                model_names = [m.get('name', 'unknown') for m in models[:3]]  # Show first 3
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
    print("=" * 60)
    
    system_objects = initialize_system()
    # Initialize global histories from system_objects
    chat_history_global = system_objects['chat_history']
    full_history_global = system_objects['full_history']
    
    print("✅ NeuroSync Player System Initialized for HTTP interaction with Local LLM support.")
    print("💡 Ready to process VTuber interactions!")


@app.route("/process_text", methods=['POST'])
def handle_process_text():
    global chat_history_global, full_history_global # Use global histories

    # Check if the global rolling window is active, ONLY if payment is enabled
    if VTUBER_PAYMENT_ENABLED:
        if not os.path.exists(WINDOW_ACTIVE_FLAG_PATH):
            app.logger.warning(f"Request to /process_text denied (Payment Enabled): Rolling window not active (flag not found: {WINDOW_ACTIVE_FLAG_PATH})")
            return jsonify({"error": "Worker is idle – no active job window"}), 403
        else:
            app.logger.info(f"Payment Enabled: Window active, proceeding with /process_text.")
    else:
        app.logger.info(f"Payment DISABLED: Bypassing window active check for /process_text. Flag status: {'exists' if os.path.exists(WINDOW_ACTIVE_FLAG_PATH) else 'not found'}")

    if not request.json or 'text' not in request.json:
        app.logger.warning("/process_text: Missing 'text' in JSON payload")
        return jsonify({"error": "Missing 'text' in JSON payload"}), 400
    
    user_input = request.json['text']
    if not user_input:
        app.logger.warning("/process_text: Input text cannot be empty")
        return jsonify({"error": "Input text cannot be empty"}), 400

    # Extract autonomous context if provided
    autonomous_context = request.json.get('autonomous_context', None)
    
    # Enhanced logging with LLM provider information
    provider = llm_config_global.get("LLM_PROVIDER", "openai")
    app.logger.info(f"📝 Processing text with {provider.upper()}: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
    
    if autonomous_context:
        app.logger.info(f"🤖 Autonomous context detected: {autonomous_context}")

    # Access necessary components from system_objects
    chunk_queue = system_objects['chunk_queue']
    audio_queue = system_objects['audio_queue']
    
    # process_turn updates chat_history internally, but we should ensure it uses the global one
    # and that its return value (the updated history) is reassigned globally if necessary.
    # For simplicity, let's assume process_turn modifies chat_history_global in place or we reassign.
    updated_chat_history = process_turn(
        user_input, 
        chat_history_global, 
        full_history_global, 
        llm_config_global, 
        chunk_queue, 
        audio_queue, 
        vector_db, 
        base_system_message=BASE_SYSTEM_MESSAGE,
        autonomous_context=autonomous_context  # Pass autonomous context
    )
    chat_history_global = updated_chat_history # Ensure global history is updated

    # The actual response from process_turn isn't directly sent back here.
    # The function queues data for TTS and animation.
    # We can return a simple success message.
    response_data = {
        "status": "processing", 
        "message": "Input processed.",
        "llm_provider": provider,
        "model": llm_config_global.get(f"{provider.upper()}_MODEL") if provider != "custom_local" else "custom"
    }
    
    app.logger.info(f"✅ Text processing completed with {provider}")
    return jsonify(response_data), 200

def cleanup_resources():
    global system_objects
    if system_objects:
        print("Cleaning up resources...")
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

# Original main() is effectively replaced by Flask server startup
# if __name__ == "__main__":
#    main()

if __name__ == "__main__":
    log_file, original_stdout = setup_logging_and_tee()
    main_setup()
    
    # Configure Flask logging to be somewhat consistent
    handler = logging.StreamHandler(sys.stdout) # Log to the same place as Tee
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(module)s : %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO) # Or DEBUG if needed

    flask_port = int(os.getenv("PLAYER_PORT", "5001")) # Make port configurable
    app.logger.info(f"🌐 Starting NeuroSync Player HTTP server on port {flask_port}...")
    
    try:
        app.run(host='0.0.0.0', port=flask_port, debug=False) # debug=False for production/container
    except KeyboardInterrupt:
        print("Flask server shutting down...")
    finally:
        cleanup_resources()
        if log_file:
            print(f"\n--- NeuroSync Player Log Ended: {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')} ---")
            log_file.close()
        sys.stdout = original_stdout
        app.logger.info("NeuroSync Player server stopped.")
        print("NeuroSync Player server stopped.")

# Removed old main function and its try/finally block for interactive input.
# The cleanup logic is now in cleanup_resources() and called in the new __main__ block.
