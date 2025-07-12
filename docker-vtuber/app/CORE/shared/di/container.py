"""
Dependency Injection Container
=============================

Clean service management with proper lifecycle handling.
"""

import asyncio
import logging
from typing import Dict, Any, Type, TypeVar, Callable, Optional, Union
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
import inspect

from ..config import get_config, CoreConfig

T = TypeVar('T')
logger = logging.getLogger(__name__)


class ServiceLifecycle(ABC):
    """Base class for services that need lifecycle management"""
    
    @abstractmethod
    async def start(self):
        """Start the service"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the service"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        pass


class DIContainer:
    """
    Dependency Injection Container with lifecycle management.
    
    Features:
    - Singleton and transient services
    - Async lifecycle management
    - Dependency resolution
    - Health checking
    - Proper cleanup
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lifecycle_services: Dict[str, ServiceLifecycle] = {}
        self._started = False
    
    def register_singleton(
        self, 
        service_type: Type[T], 
        factory: Optional[Callable[..., T]] = None,
        name: Optional[str] = None
    ) -> 'DIContainer':
        """Register a singleton service"""
        service_name = name or service_type.__name__
        
        if factory is None:
            # Try to use the class constructor
            factory = service_type
        
        self._factories[service_name] = factory
        logger.debug(f"Registered singleton: {service_name}")
        return self
    
    def register_transient(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        name: Optional[str] = None
    ) -> 'DIContainer':
        """Register a transient service (new instance each time)"""
        service_name = name or service_type.__name__
        self._factories[service_name] = factory
        logger.debug(f"Registered transient: {service_name}")
        return self
    
    def register_instance(
        self,
        instance: T,
        service_type: Optional[Type[T]] = None,
        name: Optional[str] = None
    ) -> 'DIContainer':
        """Register an existing instance"""
        service_name = name or (service_type.__name__ if service_type else type(instance).__name__)
        self._singletons[service_name] = instance
        
        if isinstance(instance, ServiceLifecycle):
            self._lifecycle_services[service_name] = instance
        
        logger.debug(f"Registered instance: {service_name}")
        return self
    
    def get(self, service_type: Type[T], name: Optional[str] = None) -> T:
        """Get a service instance"""
        service_name = name or service_type.__name__
        
        # Check if we have a singleton instance
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Check if we have a factory
        if service_name not in self._factories:
            raise ValueError(f"Service not registered: {service_name}")
        
        factory = self._factories[service_name]
        
        # Resolve dependencies
        instance = self._create_instance(factory)
        
        # Cache singletons
        if service_name not in self._services or service_name.endswith("Singleton"):
            self._singletons[service_name] = instance
            
            if isinstance(instance, ServiceLifecycle):
                self._lifecycle_services[service_name] = instance
        
        return instance
    
    def _create_instance(self, factory: Callable) -> Any:
        """Create an instance using dependency injection"""
        sig = inspect.signature(factory)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'config':
                kwargs['config'] = get_config()
            elif param_name == 'container':
                kwargs['container'] = self
            elif param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.get(param.annotation)
                except ValueError:
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        logger.warning(f"Could not resolve dependency: {param_name}")
        
        return factory(**kwargs)
    
    async def start_all(self):
        """Start all lifecycle services"""
        if self._started:
            return
        
        logger.info("Starting all services...")
        
        for name, service in self._lifecycle_services.items():
            try:
                await service.start()
                logger.info(f"Started service: {name}")
            except Exception as e:
                logger.error(f"Failed to start service {name}: {e}")
                raise
        
        self._started = True
        logger.info("All services started successfully")
    
    async def stop_all(self):
        """Stop all lifecycle services"""
        if not self._started:
            return
        
        logger.info("Stopping all services...")
        
        # Stop in reverse order
        for name, service in reversed(list(self._lifecycle_services.items())):
            try:
                await service.stop()
                logger.info(f"Stopped service: {name}")
            except Exception as e:
                logger.error(f"Failed to stop service {name}: {e}")
        
        self._started = False
        logger.info("All services stopped")
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all lifecycle services"""
        results = {}
        
        for name, service in self._lifecycle_services.items():
            try:
                results[name] = await service.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        
        return results
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for service lifecycle"""
        try:
            await self.start_all()
            yield self
        finally:
            await self.stop_all()


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container"""
    global _container
    if _container is None:
        _container = DIContainer()
        _setup_core_services(_container)
    return _container


def _setup_core_services(container: DIContainer):
    """Setup core services in the container"""
    # Configuration is already available via get_config()
    
    # Register core services that will be implemented
    # These will be registered by their respective modules
    logger.debug("Core DI container initialized")


def reset_container():
    """Reset the global container (for testing)"""
    global _container
    _container = None


# Service registration decorators
def singleton(name: Optional[str] = None):
    """Decorator to auto-register a class as singleton"""
    def decorator(cls):
        container = get_container()
        container.register_singleton(cls, name=name)
        return cls
    return decorator


def transient(name: Optional[str] = None):
    """Decorator to auto-register a class as transient"""
    def decorator(cls):
        container = get_container()
        container.register_transient(cls, cls, name=name)
        return cls
    return decorator


# Example usage
if __name__ == "__main__":
    import asyncio
    from ..config import load_development_config
    
    # Initialize config
    load_development_config()
    
    # Example service
    class ExampleService(ServiceLifecycle):
        def __init__(self, config: CoreConfig):
            self.config = config
            self.running = False
        
        async def start(self):
            self.running = True
            print("ExampleService started")
        
        async def stop(self):
            self.running = False
            print("ExampleService stopped")
        
        async def health_check(self) -> bool:
            return self.running
    
    async def main():
        container = get_container()
        container.register_singleton(ExampleService)
        
        async with container.lifespan():
            service = container.get(ExampleService)
            health = await container.health_check_all()
            print(f"Health status: {health}")
    
    asyncio.run(main())