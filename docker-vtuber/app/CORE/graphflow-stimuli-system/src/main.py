"""
Main entry point for GraphFlow External Stimuli System.

This module provides the main application entry point that integrates
the API server, gateway agent, and background tasks into a cohesive
production-ready service.
"""

import asyncio
import signal
import sys
import os
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import asdict

import uvicorn

from .gateway.gateway_agent import GraphFlowGatewayAgent, create_gateway
from .config.settings import GraphFlowConfig, load_config
from .utils.logging import configure_logging, get_structured_logger
from .api_server import create_app
from .background_tasks import start_background_tasks, BackgroundTaskManager


# Global instances
gateway: Optional[GraphFlowGatewayAgent] = None
background_manager: Optional[BackgroundTaskManager] = None
logger = get_structured_logger("main")


class GraphFlowApplication:
    """Main application class that manages all components."""
    
    def __init__(self):
        self.gateway: Optional[GraphFlowGatewayAgent] = None
        self.background_manager: Optional[BackgroundTaskManager] = None
        self.app = None
        self.config = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all application components."""
        logger.info("Initializing GraphFlow External Stimuli System")
        
        # Load configuration
        self.config = load_config()
        
        # Configure logging
        configure_logging(
            log_level=self.config.log_level,
            enable_json=self.config.detailed_logging
        )
        
        # Create gateway
        logger.info("Creating GraphFlow Gateway Agent")
        self.gateway = await create_gateway(self.config)
        
        # Start background tasks
        logger.info("Starting background task manager")
        self.background_manager = await start_background_tasks(
            self.gateway,
            asdict(self.config)
        )
        
        # Create FastAPI app with enhanced features
        logger.info("Creating FastAPI application")
        self.app = create_app()
        
        # Inject gateway into app state
        self.app.state.gateway = self.gateway
        self.app.state.background_manager = self.background_manager
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("GraphFlow External Stimuli System initialized successfully")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating graceful shutdown")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Perform graceful shutdown of all components."""
        logger.info("Starting graceful shutdown sequence")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Stop background tasks
        if self.background_manager:
            logger.info("Stopping background tasks")
            await self.background_manager.stop()
        
        # Stop gateway
        if self.gateway:
            logger.info("Stopping gateway agent")
            await self.gateway.stop()
        
        logger.info("Graceful shutdown completed")
    
    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the application."""
        await self.initialize()
        
        # Configure uvicorn
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_config=None,  # Use our custom logging
            access_log=False,  # Disable default access logs
            loop="asyncio"
        )
        
        server = uvicorn.Server(config)
        
        # Run server with shutdown handling
        try:
            await server.serve()
        except asyncio.CancelledError:
            logger.info("Server cancelled")
        finally:
            await self.shutdown()


def main():
    """Main entry point for the GraphFlow External Stimuli System."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="GraphFlow External Stimuli System")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--env", default="production", choices=["development", "testing", "production"],
                       help="Environment to run in")
    args = parser.parse_args()
    
    # Set environment
    os.environ["ENVIRONMENT"] = args.env
    
    # Create and run application
    app = GraphFlowApplication()
    
    # Run the application
    try:
        asyncio.run(app.run(host=args.host, port=args.port))
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


# For uvicorn, create a simple app instance
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting GraphFlow Gateway")
    application = GraphFlowApplication()
    await application.initialize()
    app.state.application = application
    yield
    # Shutdown
    logger.info("Shutting down GraphFlow Gateway")
    if hasattr(app.state, 'application'):
        await app.state.application.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(
    title="GraphFlow External Stimuli Gateway",
    description="External Stimuli Processing Gateway for GraphFlow System",
    version="1.0.0",
    lifespan=lifespan
)

if __name__ == "__main__":
    main()