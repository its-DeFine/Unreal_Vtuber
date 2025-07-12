#!/bin/bash
# Unified Ollama initialization script
# Usage: ./init-ollama.sh [--fast]

FAST_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast|-f)
            FAST_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--fast]"
            echo "  --fast   Use fast initialization with smaller models and shorter timeouts"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$FAST_MODE" = true ]; then
    echo "🚀 [OLLAMA_FAST_INIT] Starting Fast Ollama model initialization..."
    MODE_PREFIX="OLLAMA_FAST_INIT"
    INITIAL_SLEEP=5
    RETRY_SLEEP=3
else
    echo "🚀 [OLLAMA_INIT] Starting Ollama model initialization..."
    MODE_PREFIX="OLLAMA_INIT"
    INITIAL_SLEEP=10
    RETRY_SLEEP=5
fi

# Start Ollama server in background
echo "🔄 [$MODE_PREFIX] Starting Ollama server..."
ollama serve &

# Wait for Ollama service to be ready
echo "⏳ [$MODE_PREFIX] Waiting for Ollama service to start..."
sleep $INITIAL_SLEEP

# Test if Ollama is responding
echo "✅ [$MODE_PREFIX] Testing Ollama availability..."
while ! ollama list >/dev/null 2>&1; do
    echo "⏳ [$MODE_PREFIX] Ollama not ready yet, waiting..."
    sleep $RETRY_SLEEP
done

echo "✅ [$MODE_PREFIX] Ollama service is ready"

# Pull embedding model first (smaller, more reliable)
echo "📥 [$MODE_PREFIX] Pulling embedding model: nomic-embed-text:latest..."
if [ "$FAST_MODE" = true ]; then
    timeout 60 ollama pull nomic-embed-text:latest
else
    ollama pull nomic-embed-text:latest
fi

if [ $? -eq 0 ]; then
    echo "✅ [$MODE_PREFIX] Embedding model pulled successfully"
else
    echo "❌ [$MODE_PREFIX] Failed to pull embedding model"
fi

# Pull LLM models based on mode
echo "📥 [$MODE_PREFIX] Pulling LLM model..."

if [ "$FAST_MODE" = true ]; then
    # Fast mode: try small models with short timeouts
    echo "📥 [$MODE_PREFIX] Fast mode: Attempting small LLM models..."
    
    SMALL_MODELS=("phi3:mini" "gemma2:2b" "tinyllama" "qwen2:0.5b")
    LLM_MODEL=""
    
    for model in "${SMALL_MODELS[@]}"; do
        echo "📥 [$MODE_PREFIX] Trying $model..."
        if timeout 120 ollama pull "$model"; then
            echo "✅ [$MODE_PREFIX] Successfully pulled $model"
            LLM_MODEL="$model"
            break
        else
            echo "⚠️ [$MODE_PREFIX] $model failed or timed out, trying next..."
        fi
    done
    
    # Fallback for fast mode
    if [ -z "$LLM_MODEL" ]; then
        echo "⚠️ [$MODE_PREFIX] No new models downloaded, checking existing..."
        EXISTING_MODELS=$(ollama list | grep -v "NAME" | awk '{print $1}' | head -1)
        if [ ! -z "$EXISTING_MODELS" ]; then
            LLM_MODEL="$EXISTING_MODELS"
            echo "✅ [$MODE_PREFIX] Using existing model: $LLM_MODEL"
        else
            echo "❌ [$MODE_PREFIX] No models available, will use basic configuration"
            LLM_MODEL="llama3.2:3b"
        fi
    fi
    
else
    # Standard mode: try larger, more capable models
    echo "📥 [$MODE_PREFIX] Attempting to pull llama3.1:8b..."
    timeout 300 ollama pull llama3.1:8b
    if [ $? -eq 0 ]; then
        echo "✅ [$MODE_PREFIX] llama3.1:8b pulled successfully"
        LLM_MODEL="llama3.1:8b"
    else
        echo "⚠️ [$MODE_PREFIX] llama3.1:8b failed, trying llama3:8b..."
        
        # Fallback to llama3:8b
        timeout 300 ollama pull llama3:8b
        if [ $? -eq 0 ]; then
            echo "✅ [$MODE_PREFIX] llama3:8b pulled successfully"
            LLM_MODEL="llama3:8b"
        else
            echo "⚠️ [$MODE_PREFIX] llama3:8b failed, trying smaller but more reliable model..."
            
            # Final fallback to a more reliable smaller model
            timeout 180 ollama pull llama3:latest
            if [ $? -eq 0 ]; then
                echo "✅ [$MODE_PREFIX] llama3:latest pulled successfully"
                LLM_MODEL="llama3:latest"
            else
                echo "❌ [$MODE_PREFIX] All model pulls failed, keeping llama3.2:3b"
                LLM_MODEL="llama3.2:3b"
            fi
        fi
    fi
fi

# Save model configuration
echo "LLM_MODEL=$LLM_MODEL" > /tmp/ollama_model.env

# Show final status
echo "📋 [$MODE_PREFIX] Final model configuration:"
echo "   LLM Model: $LLM_MODEL"

# List available models
echo "📋 [$MODE_PREFIX] Available models:"
ollama list

echo "🎉 [$MODE_PREFIX] Initialization complete!"

# Keep the process running (wait for the background ollama serve process)
echo "🔄 [$MODE_PREFIX] Keeping Ollama server running..."
wait