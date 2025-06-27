#!/bin/bash

echo "🏥 [HEALTH_CHECK] Checking Ollama service health..."

# Check if Ollama service is running
if ! curl -s http://localhost:11434 > /dev/null; then
    echo "❌ [HEALTH_CHECK] Ollama service not accessible"
    exit 1
fi

# Check if required models are available
echo "📋 [HEALTH_CHECK] Checking available models..."
MODELS=$(ollama list)

# Check for embedding model
if echo "$MODELS" | grep -q "nomic-embed-text:latest"; then
    echo "✅ [HEALTH_CHECK] Embedding model (nomic-embed-text:latest) available"
else
    echo "❌ [HEALTH_CHECK] Embedding model (nomic-embed-text:latest) missing"
    exit 1
fi

# Check for LLM model (any of the preferred options)
if echo "$MODELS" | grep -q "llama3.1:8b"; then
    echo "✅ [HEALTH_CHECK] LLM model (llama3.1:8b) available"
elif echo "$MODELS" | grep -q "llama3:8b"; then
    echo "✅ [HEALTH_CHECK] LLM model (llama3:8b) available"
elif echo "$MODELS" | grep -q "llama3:latest"; then
    echo "✅ [HEALTH_CHECK] LLM model (llama3:latest) available"
elif echo "$MODELS" | grep -q "llama3.2:3b"; then
    echo "⚠️ [HEALTH_CHECK] LLM model (llama3.2:3b) available but not optimal"
else
    echo "❌ [HEALTH_CHECK] No suitable LLM model found"
    echo "📋 [HEALTH_CHECK] Available models:"
    echo "$MODELS"
    exit 1
fi

echo "🎉 [HEALTH_CHECK] Ollama service is healthy and ready!"
exit 0 