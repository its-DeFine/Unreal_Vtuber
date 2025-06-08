#!/usr/bin/env python3
"""
LLM Service with Ollama Integration
=================================

Large Language Model service for text generation and chat functionality.
Integrates with Ollama for model execution and management with comprehensive
features for real-time communication, model switching, and performance optimization.

Features:
- Ollama API integration with fallback models
- Streaming and non-streaming text generation
- Multi-turn conversation support
- Dynamic model loading and switching
- Context management and memory optimization
- Performance monitoring and metrics
- Token counting and cost tracking
"""

import logging
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator, Tuple
from datetime import datetime
import aiohttp
import requests
from pathlib import Path

from ..core.model_manager import BaseModel, ModelConfig, ModelState, track_inference_metrics
from ..utils.request_queue import QueuePriority


# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

@dataclass
class LLMConfig:
    """Configuration for LLM service"""
    ollama_host: str = "http://localhost:11434"
    primary_model: str = "llama3.2:7b"
    fallback_model: str = "llama3.2:3b"
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    context_window: int = 4096
    stream_chunk_size: int = 1024


@dataclass
class ChatMessage:
    """Individual chat message"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Chat session with conversation history"""
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    model_name: str = ""
    total_tokens: int = 0
    max_history: int = 50
    system_prompt: Optional[str] = None


@dataclass
class GenerationRequest:
    """Text generation request"""
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
    stop: Optional[List[str]] = None
    context: Optional[List[ChatMessage]] = None
    session_id: Optional[str] = None
    priority: QueuePriority = QueuePriority.NORMAL


# =============================================================================
# OLLAMA CLIENT
# =============================================================================

class OllamaClient:
    """Async client for Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("ollama_client")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if Ollama server is responsive"""
        try:
            if not self.session:
                return False
                
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            if not self.session:
                raise RuntimeError("Client session not initialized")
                
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("models", [])
                else:
                    self.logger.error(f"Failed to list models: {response.status}")
                    return []
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return []
    
    async def generate(
        self, 
        model: str, 
        prompt: str, 
        stream: bool = False,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate text with streaming or non-streaming"""
        if not self.session:
            raise RuntimeError("Client session not initialized")
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error {response.status}: {error_text}")
                
                if stream:
                    # Handle streaming response
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                else:
                    # Handle non-streaming response
                    result = await response.json()
                    yield result
                    
        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            raise
    
    async def chat(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Chat completion with conversation context"""
        if not self.session:
            raise RuntimeError("Client session not initialized")
            
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama chat API error {response.status}: {error_text}")
                
                if stream:
                    # Handle streaming response
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                else:
                    # Handle non-streaming response
                    result = await response.json()
                    yield result
                    
        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            raise


# =============================================================================
# LLM MODEL IMPLEMENTATION
# =============================================================================

class LLMModel(BaseModel):
    """LLM model implementation using Ollama"""
    
    def __init__(self, config: ModelConfig, llm_config: LLMConfig):
        super().__init__(config)
        self.llm_config = llm_config
        self.client: Optional[OllamaClient] = None
        self.current_model = llm_config.primary_model
        self.fallback_model = llm_config.fallback_model
        
        # Chat session management
        self.chat_sessions: Dict[str, ChatSession] = {}
        self.session_timeout = 3600  # 1 hour
        
        # Performance tracking
        self.token_count = 0
        self.generation_count = 0
        self.average_tokens_per_second = 0.0
        
    async def load(self) -> bool:
        """Load the LLM model"""
        try:
            self.logger.info(f"Loading LLM model: {self.current_model}")
            
            # Initialize Ollama client
            self.client = OllamaClient(self.llm_config.ollama_host)
            await self.client.__aenter__()
            
            # Health check
            if not await self.client.health_check():
                self.logger.error("Ollama server not responding")
                return False
            
            # Verify model availability
            models = await self.client.list_models()
            model_names = [model.get("name", "") for model in models]
            
            if self.current_model not in model_names:
                self.logger.warning(f"Primary model {self.current_model} not found")
                if self.fallback_model in model_names:
                    self.logger.info(f"Switching to fallback model: {self.fallback_model}")
                    self.current_model = self.fallback_model
                else:
                    self.logger.error("No suitable models available")
                    return False
            
            self.logger.info(f"LLM model loaded successfully: {self.current_model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load LLM model: {e}")
            return False
    
    async def unload(self) -> bool:
        """Unload the LLM model"""
        try:
            self.logger.info("Unloading LLM model")
            
            if self.client:
                await self.client.__aexit__(None, None, None)
                self.client = None
            
            # Clear chat sessions
            self.chat_sessions.clear()
            
            self.logger.info("LLM model unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload LLM model: {e}")
            return False
    
    @track_inference_metrics
    async def inference(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform LLM inference"""
        try:
            if not self.client:
                raise RuntimeError("LLM model not loaded")
            
            # Parse request
            request = GenerationRequest(**request_data)
            
            # Route to appropriate method
            if request.session_id:
                return await self._chat_completion(request)
            else:
                return await self._text_generation(request)
                
        except Exception as e:
            self.logger.error(f"LLM inference error: {e}")
            return {"error": str(e)}
    
    async def _text_generation(self, request: GenerationRequest) -> Dict[str, Any]:
        """Handle text generation requests"""
        start_time = time.time()
        
        # Prepare parameters
        params = {
            "temperature": request.temperature or self.llm_config.temperature,
            "top_p": request.top_p or self.llm_config.top_p,
            "max_tokens": request.max_tokens or self.llm_config.max_tokens,
            "stop": request.stop or self.llm_config.stop_sequences
        }
        
        try:
            if request.stream:
                # Streaming generation
                response_chunks = []
                async for chunk in self.client.generate(
                    model=request.model or self.current_model,
                    prompt=request.prompt,
                    stream=True,
                    **params
                ):
                    response_chunks.append(chunk)
                    if chunk.get("done", False):
                        break
                
                # Combine chunks
                full_response = ""
                for chunk in response_chunks:
                    if "response" in chunk:
                        full_response += chunk["response"]
                
                result = {
                    "text": full_response,
                    "model": request.model or self.current_model,
                    "stream": True,
                    "chunks": len(response_chunks)
                }
            else:
                # Non-streaming generation
                async for response in self.client.generate(
                    model=request.model or self.current_model,
                    prompt=request.prompt,
                    stream=False,
                    **params
                ):
                    result = {
                        "text": response.get("response", ""),
                        "model": request.model or self.current_model,
                        "stream": False,
                        "context": response.get("context", [])
                    }
                    break
            
            # Update metrics
            generation_time = (time.time() - start_time) * 1000
            result["generation_time_ms"] = generation_time
            result["timestamp"] = datetime.now().isoformat()
            
            # Estimate token count (rough approximation)
            estimated_tokens = len(result["text"].split()) * 1.3
            self.token_count += estimated_tokens
            self.generation_count += 1
            
            # Update tokens per second
            if generation_time > 0:
                tokens_per_second = (estimated_tokens / generation_time) * 1000
                self.average_tokens_per_second = (
                    (self.average_tokens_per_second * (self.generation_count - 1) + tokens_per_second) /
                    self.generation_count
                )
            
            result["estimated_tokens"] = int(estimated_tokens)
            result["tokens_per_second"] = round(tokens_per_second, 2) if generation_time > 0 else 0
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text generation error: {e}")
            return {"error": str(e)}
    
    async def _chat_completion(self, request: GenerationRequest) -> Dict[str, Any]:
        """Handle chat completion requests"""
        start_time = time.time()
        
        try:
            # Get or create chat session
            session = self._get_or_create_session(request.session_id)
            
            # Add user message
            user_message = ChatMessage(
                role="user",
                content=request.prompt,
                timestamp=datetime.now()
            )
            session.messages.append(user_message)
            
            # Prepare messages for Ollama
            messages = []
            
            # Add system prompt if available
            if session.system_prompt:
                messages.append({"role": "system", "content": session.system_prompt})
            
            # Add conversation history (limited by context window)
            message_count = min(len(session.messages), session.max_history)
            for message in session.messages[-message_count:]:
                messages.append({
                    "role": message.role,
                    "content": message.content
                })
            
            # Generate response
            if request.stream:
                # Streaming chat
                response_chunks = []
                async for chunk in self.client.chat(
                    model=request.model or self.current_model,
                    messages=messages,
                    stream=True,
                    temperature=request.temperature or self.llm_config.temperature,
                    top_p=request.top_p or self.llm_config.top_p
                ):
                    response_chunks.append(chunk)
                    if chunk.get("done", False):
                        break
                
                # Combine chunks
                assistant_content = ""
                for chunk in response_chunks:
                    if "message" in chunk and "content" in chunk["message"]:
                        assistant_content += chunk["message"]["content"]
                
                result = {
                    "text": assistant_content,
                    "model": request.model or self.current_model,
                    "stream": True,
                    "chunks": len(response_chunks),
                    "session_id": request.session_id
                }
            else:
                # Non-streaming chat
                async for response in self.client.chat(
                    model=request.model or self.current_model,
                    messages=messages,
                    stream=False,
                    temperature=request.temperature or self.llm_config.temperature,
                    top_p=request.top_p or self.llm_config.top_p
                ):
                    assistant_content = response.get("message", {}).get("content", "")
                    result = {
                        "text": assistant_content,
                        "model": request.model or self.current_model,
                        "stream": False,
                        "session_id": request.session_id
                    }
                    break
            
            # Add assistant message to session
            assistant_message = ChatMessage(
                role="assistant",
                content=result["text"],
                timestamp=datetime.now()
            )
            session.messages.append(assistant_message)
            session.last_activity = datetime.now()
            
            # Update metrics
            generation_time = (time.time() - start_time) * 1000
            result["generation_time_ms"] = generation_time
            result["timestamp"] = datetime.now().isoformat()
            result["message_count"] = len(session.messages)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Chat completion error: {e}")
            return {"error": str(e)}
    
    def _get_or_create_session(self, session_id: str) -> ChatSession:
        """Get existing or create new chat session"""
        if session_id in self.chat_sessions:
            session = self.chat_sessions[session_id]
            session.last_activity = datetime.now()
            return session
        
        # Create new session
        session = ChatSession(
            session_id=session_id,
            model_name=self.current_model
        )
        self.chat_sessions[session_id] = session
        
        self.logger.info(f"Created new chat session: {session_id}")
        return session
    
    async def health_check(self) -> bool:
        """Check LLM model health"""
        try:
            if not self.client:
                return False
            
            # Test with simple generation
            test_request = {
                "prompt": "Hello",
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            response = await self._text_generation(GenerationRequest(**test_request))
            return "error" not in response
            
        except Exception as e:
            self.logger.error(f"LLM health check failed: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a chat session"""
        if session_id not in self.chat_sessions:
            return None
        
        session = self.chat_sessions[session_id]
        return {
            "session_id": session_id,
            "message_count": len(session.messages),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "model_name": session.model_name,
            "total_tokens": session.total_tokens
        }
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a chat session"""
        if session_id in self.chat_sessions:
            del self.chat_sessions[session_id]
            self.logger.info(f"Cleared chat session: {session_id}")
            return True
        return False
    
    def cleanup_old_sessions(self):
        """Remove old inactive sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.chat_sessions.items():
            time_since_activity = (current_time - session.last_activity).total_seconds()
            if time_since_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.chat_sessions[session_id]
            self.logger.info(f"Removed expired session: {session_id}")
        
        return len(expired_sessions)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get LLM performance statistics"""
        return {
            "total_generations": self.generation_count,
            "total_tokens": self.token_count,
            "average_tokens_per_second": self.average_tokens_per_second,
            "active_sessions": len(self.chat_sessions),
            "current_model": self.current_model,
            "fallback_model": self.fallback_model
        }


# =============================================================================
# LLM SERVICE
# =============================================================================

class LLMService:
    """High-level LLM service with model management"""
    
    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        self.logger = logging.getLogger("llm_service")
        
        # Create model configuration
        model_config = ModelConfig(
            name="llm_service",
            model_type="llm",
            memory_requirement_mb=4096,  # 4GB for LLM
            load_time_estimate_ms=5000,
            priority=1,
            max_concurrent_requests=8,
            idle_timeout_seconds=600  # 10 minutes
        )
        
        # Initialize LLM model
        self.model = LLMModel(model_config, llm_config)
        
        self.logger.info("LLM Service initialized")
    
    async def start(self) -> bool:
        """Start the LLM service"""
        self.logger.info("Starting LLM Service...")
        return await self.model.load()
    
    async def stop(self) -> bool:
        """Stop the LLM service"""
        self.logger.info("Stopping LLM Service...")
        return await self.model.unload()
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text from prompt"""
        request_data = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        return await self.model.inference(request_data)
    
    async def chat_completion(
        self,
        message: str,
        session_id: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Complete chat conversation"""
        # Set system prompt if provided
        if system_prompt and session_id in self.model.chat_sessions:
            self.model.chat_sessions[session_id].system_prompt = system_prompt
        
        request_data = {
            "prompt": message,
            "session_id": session_id,
            "model": model,
            "stream": stream,
            **kwargs
        }
        
        return await self.model.inference(request_data)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        health_ok = await self.model.health_check()
        stats = self.model.get_performance_stats()
        
        return {
            "status": "healthy" if health_ok else "unhealthy",
            "model_loaded": self.model.state == ModelState.LOADED,
            "performance": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session information"""
        return self.model.get_session_info(session_id)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear chat session"""
        return self.model.clear_session(session_id)
    
    def cleanup_sessions(self) -> int:
        """Clean up old sessions"""
        return self.model.cleanup_old_sessions()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def main():
    """Example usage of LLM service"""
    # Configure LLM
    config = LLMConfig(
        ollama_host="http://localhost:11434",
        primary_model="llama3.2:7b",
        fallback_model="llama3.2:3b"
    )
    
    # Create service
    service = LLMService(config)
    
    try:
        # Start service
        if await service.start():
            print("LLM Service started successfully")
            
            # Test text generation
            response = await service.generate_text(
                prompt="Explain quantum computing in one sentence.",
                max_tokens=50
            )
            print("Text Generation:", response)
            
            # Test chat
            chat_response = await service.chat_completion(
                message="Hello! What's your name?",
                session_id="test_session"
            )
            print("Chat Response:", chat_response)
            
            # Health check
            health = await service.health_check()
            print("Health Check:", health)
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main()) 