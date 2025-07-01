"""
Provider registry system for managing LLM, TTS, and Animation providers.
"""

from typing import Dict, Type, Any, Optional, List
import logging
from .base import (
    BaseProvider, LLMProvider, TTSProvider, AnimationProvider,
    ProviderStatus, ProviderInfo, ProviderError, ProviderNotReadyError
)


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Centralized provider registry for managing all system providers"""
    
    def __init__(self):
        self._llm_providers: Dict[str, LLMProvider] = {}
        self._tts_providers: Dict[str, TTSProvider] = {}
        self._animation_providers: Dict[str, AnimationProvider] = {}
        self._default_providers = {
            'llm': None,
            'tts': None,
            'animation': None
        }
        
    def register_llm_provider(self, 
                            name: str, 
                            provider_class: Type[LLMProvider],
                            config: Dict[str, Any],
                            set_as_default: bool = False) -> None:
        """Register an LLM provider"""
        try:
            provider = provider_class(config)
            self._llm_providers[name] = provider
            if set_as_default or self._default_providers['llm'] is None:
                self._default_providers['llm'] = name
            logger.info(f"Registered LLM provider: {name}")
        except Exception as e:
            logger.error(f"Failed to register LLM provider {name}: {e}")
            raise ProviderError(f"Failed to register LLM provider: {e}")
            
    def register_tts_provider(self,
                            name: str,
                            provider_class: Type[TTSProvider],
                            config: Dict[str, Any],
                            set_as_default: bool = False) -> None:
        """Register a TTS provider"""
        try:
            provider = provider_class(config)
            self._tts_providers[name] = provider
            if set_as_default or self._default_providers['tts'] is None:
                self._default_providers['tts'] = name
            logger.info(f"Registered TTS provider: {name}")
        except Exception as e:
            logger.error(f"Failed to register TTS provider {name}: {e}")
            raise ProviderError(f"Failed to register TTS provider: {e}")
            
    def register_animation_provider(self,
                                  name: str,
                                  provider_class: Type[AnimationProvider],
                                  config: Dict[str, Any],
                                  set_as_default: bool = False) -> None:
        """Register an animation provider"""
        try:
            provider = provider_class(config)
            self._animation_providers[name] = provider
            if set_as_default or self._default_providers['animation'] is None:
                self._default_providers['animation'] = name
            logger.info(f"Registered animation provider: {name}")
        except Exception as e:
            logger.error(f"Failed to register animation provider {name}: {e}")
            raise ProviderError(f"Failed to register animation provider: {e}")
            
    async def initialize_all(self) -> Dict[str, List[str]]:
        """
        Initialize all registered providers.
        Returns dict with 'success' and 'failed' provider lists.
        """
        success = []
        failed = []
        
        all_providers = [
            ('llm', self._llm_providers),
            ('tts', self._tts_providers),
            ('animation', self._animation_providers)
        ]
        
        for provider_type, providers in all_providers:
            for name, provider in providers.items():
                try:
                    logger.info(f"Initializing {provider_type} provider: {name}")
                    if await provider.initialize():
                        success.append(f"{provider_type}:{name}")
                        logger.info(f"Successfully initialized {provider_type} provider: {name}")
                    else:
                        failed.append(f"{provider_type}:{name}")
                        logger.error(f"Failed to initialize {provider_type} provider: {name}")
                except Exception as e:
                    failed.append(f"{provider_type}:{name}")
                    logger.error(f"Exception initializing {provider_type} provider {name}: {e}")
                    
        return {'success': success, 'failed': failed}
        
    async def shutdown_all(self) -> None:
        """Shutdown all registered providers"""
        all_providers = [
            *self._llm_providers.values(),
            *self._tts_providers.values(),
            *self._animation_providers.values()
        ]
        
        for provider in all_providers:
            try:
                await provider.shutdown()
                logger.info(f"Shut down provider: {provider.name}")
            except Exception as e:
                logger.error(f"Error shutting down provider {provider.name}: {e}")
                
    def get_llm_provider(self, name: Optional[str] = None) -> LLMProvider:
        """Get LLM provider by name or default"""
        if name is None:
            name = self._default_providers['llm']
            if name is None:
                raise ProviderError("No default LLM provider set")
                
        provider = self._llm_providers.get(name)
        if provider is None:
            raise ProviderError(f"LLM provider '{name}' not found")
            
        if provider.status != ProviderStatus.READY:
            raise ProviderNotReadyError(f"LLM provider '{name}' is not ready")
            
        return provider
        
    def get_tts_provider(self, name: Optional[str] = None) -> TTSProvider:
        """Get TTS provider by name or default"""
        if name is None:
            name = self._default_providers['tts']
            if name is None:
                raise ProviderError("No default TTS provider set")
                
        provider = self._tts_providers.get(name)
        if provider is None:
            raise ProviderError(f"TTS provider '{name}' not found")
            
        if provider.status != ProviderStatus.READY:
            raise ProviderNotReadyError(f"TTS provider '{name}' is not ready")
            
        return provider
        
    def get_animation_provider(self, name: Optional[str] = None) -> AnimationProvider:
        """Get animation provider by name or default"""
        if name is None:
            name = self._default_providers['animation']
            if name is None:
                raise ProviderError("No default animation provider set")
                
        provider = self._animation_providers.get(name)
        if provider is None:
            raise ProviderError(f"Animation provider '{name}' not found")
            
        if provider.status != ProviderStatus.READY:
            raise ProviderNotReadyError(f"Animation provider '{name}' is not ready")
            
        return provider
        
    def list_providers(self) -> Dict[str, List[str]]:
        """List all registered providers by type"""
        return {
            'llm': list(self._llm_providers.keys()),
            'tts': list(self._tts_providers.keys()),
            'animation': list(self._animation_providers.keys())
        }
        
    def get_provider_info(self, provider_type: str, name: str) -> ProviderInfo:
        """Get information about a specific provider"""
        providers_map = {
            'llm': self._llm_providers,
            'tts': self._tts_providers,
            'animation': self._animation_providers
        }
        
        providers = providers_map.get(provider_type)
        if providers is None:
            raise ProviderError(f"Invalid provider type: {provider_type}")
            
        provider = providers.get(name)
        if provider is None:
            raise ProviderError(f"{provider_type} provider '{name}' not found")
            
        return provider.get_info()
        
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health checks on all providers"""
        results = {}
        
        all_providers = [
            ('llm', self._llm_providers),
            ('tts', self._tts_providers),
            ('animation', self._animation_providers)
        ]
        
        for provider_type, providers in all_providers:
            for name, provider in providers.items():
                key = f"{provider_type}:{name}"
                try:
                    results[key] = await provider.health_check()
                except Exception as e:
                    results[key] = {
                        'healthy': False,
                        'message': f'Health check failed: {str(e)}',
                        'details': {'error': str(e)}
                    }
                    
        return results
        
    def set_default_provider(self, provider_type: str, name: str) -> None:
        """Set default provider for a type"""
        if provider_type not in self._default_providers:
            raise ProviderError(f"Invalid provider type: {provider_type}")
            
        providers_map = {
            'llm': self._llm_providers,
            'tts': self._tts_providers,
            'animation': self._animation_providers
        }
        
        providers = providers_map[provider_type]
        if name not in providers:
            raise ProviderError(f"{provider_type} provider '{name}' not found")
            
        self._default_providers[provider_type] = name
        logger.info(f"Set default {provider_type} provider to: {name}")
        
    def get_defaults(self) -> Dict[str, Optional[str]]:
        """Get current default providers"""
        return self._default_providers.copy()


# Singleton instance
_registry_instance = None


def get_registry() -> ProviderRegistry:
    """Get the singleton provider registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProviderRegistry()
    return _registry_instance


# Convenience exports
__all__ = [
    'ProviderRegistry',
    'get_registry',
    'BaseProvider',
    'LLMProvider',
    'TTSProvider',
    'AnimationProvider',
    'ProviderStatus',
    'ProviderInfo',
    'ProviderError',
    'ProviderNotReadyError'
] 