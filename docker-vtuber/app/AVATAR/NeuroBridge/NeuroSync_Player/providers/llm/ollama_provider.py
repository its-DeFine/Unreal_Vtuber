"""
Ollama LLM provider implementation.
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from ..base import LLMProvider, ProviderStatus, ProviderInfo, ProviderInitializationError


logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint = config.get('endpoint', 'http://localhost:11434')
        self.model = config.get('model', 'llama2')
        self.streaming = config.get('streaming', True)
        self.max_tokens = config.get('max_tokens', 2048)
        self.temperature = config.get('temperature', 0.7)
        self.timeout = config.get('timeout', 30)
        self.session = None
        
    async def initialize(self) -> bool:
        """Initialize the Ollama provider"""
        try:
            self.status = ProviderStatus.INITIALIZING
            
            # Create aiohttp session
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection
            health_check = await self.health_check()
            if health_check['healthy']:
                self.status = ProviderStatus.READY
                logger.info(f"Ollama provider initialized successfully with model: {self.model}")
                return True
            else:
                self.status = ProviderStatus.ERROR
                logger.error(f"Ollama health check failed: {health_check['message']}")
                return False
                
        except Exception as e:
            self.status = ProviderStatus.ERROR
            logger.error(f"Failed to initialize Ollama provider: {e}")
            raise ProviderInitializationError(f"Failed to initialize Ollama: {e}")
            
    async def shutdown(self) -> None:
        """Shutdown the provider"""
        if self.session:
            await self.session.close()
        self.status = ProviderStatus.SHUTDOWN
        logger.info("Ollama provider shut down")
        
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health"""
        try:
            if not self.session:
                return {
                    'healthy': False,
                    'message': 'Session not initialized',
                    'details': {}
                }
                
            # Check if Ollama is running
            async with self.session.get(f"{self.endpoint}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model['name'] for model in data.get('models', [])]
                    model_available = self.model in models
                    
                    return {
                        'healthy': model_available,
                        'message': 'Ollama is running' if model_available else f'Model {self.model} not found',
                        'details': {
                            'endpoint': self.endpoint,
                            'available_models': models,
                            'requested_model': self.model
                        }
                    }
                else:
                    return {
                        'healthy': False,
                        'message': f'Ollama returned status {response.status}',
                        'details': {'status_code': response.status}
                    }
                    
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Health check failed: {str(e)}',
                'details': {'error': str(e)}
            }
            
    def get_info(self) -> ProviderInfo:
        """Get provider information"""
        return ProviderInfo(
            name=self.name,
            type='llm',
            status=self.status,
            capabilities=self.get_capabilities(),
            health_info=None  # Will be populated by health_check
        )
        
    async def generate(self, 
                      prompt: str,
                      context: Optional[Dict[str, Any]] = None,
                      **kwargs) -> str:
        """Generate text response from prompt"""
        if self.status != ProviderStatus.READY:
            raise RuntimeError(f"Provider not ready: {self.status}")
            
        # Build request payload
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }
        
        # Add context if provided
        if context and 'system' in context:
            payload['system'] = context['system']
            
        try:
            async with self.session.post(
                f"{self.endpoint}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', '')
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error: {response.status} - {error_text}")
                    
        except asyncio.TimeoutError:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
            
    async def generate_stream(self,
                            prompt: str,
                            context: Optional[Dict[str, Any]] = None,
                            **kwargs) -> asyncio.Queue:
        """Generate streaming text response"""
        if self.status != ProviderStatus.READY:
            raise RuntimeError(f"Provider not ready: {self.status}")
            
        # Create queue for streaming responses
        queue = asyncio.Queue()
        
        # Build request payload
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': True,
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }
        
        # Add context if provided
        if context and 'system' in context:
            payload['system'] = context['system']
            
        # Start streaming task
        asyncio.create_task(self._stream_response(payload, queue))
        
        return queue
        
    async def _stream_response(self, payload: Dict[str, Any], queue: asyncio.Queue) -> None:
        """Internal method to handle streaming response"""
        try:
            async with self.session.post(
                f"{self.endpoint}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if 'response' in data:
                                    await queue.put(data['response'])
                                if data.get('done', False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming response: {line}")
                else:
                    error_text = await response.text()
                    await queue.put(Exception(f"Ollama API error: {response.status} - {error_text}"))
                    
        except Exception as e:
            await queue.put(e)
        finally:
            # Signal end of stream
            await queue.put(None)
            
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities"""
        return {
            'streaming': True,
            'max_tokens': self.max_tokens,
            'models': [self.model],  # Could be expanded to list all available models
            'supports_functions': False,
            'supports_images': False,  # Depends on model
            'supports_system_prompt': True,
            'endpoint': self.endpoint
        }
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation - can be improved with proper tokenizer
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4 