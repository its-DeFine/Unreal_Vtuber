"""
Ollama Integration for LiveKit Agent
Simple integration with local Ollama for LLM functionality
"""

import asyncio
import httpx
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class OllamaLLM:
    """
    Ollama LLM integration for LiveKit
    """
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        base_url: str = "http://vtuber-ollama:11434",
        system_prompt: str = "",
        temperature: float = 0.8
    ):
        self.model = model
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        stream: bool = False
    ) -> str:
        """Generate text from prompt"""
        
        # Build full prompt with system context
        full_prompt = f"{self.system_prompt}\n\n{prompt}" if self.system_prompt else prompt
        
        try:
            # Call Ollama API
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "temperature": self.temperature,
                    "stream": stream,
                    "options": {
                        "num_predict": max_tokens
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return "I'm having trouble thinking right now..."
                
        except Exception as e:
            logger.error(f"Failed to generate with Ollama: {e}")
            return "Let me think about that..."
    
    async def chat(
        self,
        messages: list,
        max_tokens: int = 150
    ) -> str:
        """Chat completion with conversation history"""
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            else:
                logger.error(f"Ollama chat error: {response.status_code}")
                return "I'm having trouble responding..."
                
        except Exception as e:
            logger.error(f"Failed to chat with Ollama: {e}")
            return "Let me think..."
    
    async def check_model(self) -> bool:
        """Check if model is available"""
        
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                # Check both with and without tag
                model_base = self.model.split(":")[0]
                if self.model in model_names or any(name.startswith(model_base) for name in model_names):
                    logger.info(f"Model {self.model} is available")
                    return True
                else:
                    logger.warning(f"Model {self.model} not found. Available: {model_names}")
                    return False
            else:
                logger.error(f"Failed to check models: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    async def pull_model(self) -> bool:
        """Pull model if not available"""
        
        try:
            logger.info(f"Pulling model {self.model}...")
            
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=600.0  # 10 minutes for model download
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully pulled model {self.model}")
                return True
            else:
                logger.error(f"Failed to pull model: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False
    
    async def ensure_model(self) -> bool:
        """Ensure model is available, pull if needed"""
        
        if await self.check_model():
            return True
        
        logger.info(f"Model {self.model} not found, attempting to pull...")
        return await self.pull_model()
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()


# Test function
async def test_ollama():
    """Test Ollama integration"""
    
    llm = OllamaLLM(
        model="llama3.2",
        base_url="http://localhost:11434",
        system_prompt="You are a friendly VTuber assistant."
    )
    
    # Check model
    if await llm.ensure_model():
        # Test generation
        response = await llm.generate("Hello! How are you today?")
        print(f"Response: {response}")
    
    await llm.close()


if __name__ == "__main__":
    asyncio.run(test_ollama())