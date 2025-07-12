"""
Unified CORE System - Main Entry Point
=====================================

Clean, maintainable entry point for the unified CORE architecture.
Replaces both autogen-agent/simplified_main.py and graphflow main.py.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.bootstrap import initialize_core_system, get_bootstrap
from shared.config import SystemMode, get_config
from shared.processing import StimuliProcessor, ProcessingMode, TeamType
from shared.character import CharacterManager
from shared.queue import QueueService
from shared.errors import ErrorHandler, handle_errors, error_context


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedCoreAPI:
    """
    Unified API that consolidates all CORE system endpoints.
    
    Features:
    - Stimuli processing (replaces GraphFlow + AutoGen APIs)
    - Character management
    - Queue monitoring
    - Health checks and metrics
    - Error handling
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="Unified CORE System",
            description="Clean, maintainable CORE architecture with 10/10 maintainability",
            version="2.0.0"
        )
        self.bootstrap = None
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        config = get_config()
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup all API routes"""
        
        @self.app.on_event("startup")
        async def startup():
            """Initialize system on startup"""
            try:
                logger.info("🚀 Starting Unified CORE System...")
                self.bootstrap = get_bootstrap()
                
                if not self.bootstrap._startup_complete:
                    await self.bootstrap.initialize()
                
                logger.info("✅ Unified CORE System ready!")
                
            except Exception as e:
                logger.error(f"❌ Startup failed: {e}")
                raise
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """Graceful shutdown"""
            if self.bootstrap:
                await self.bootstrap.shutdown()
            logger.info("👋 Unified CORE System shutdown complete")
        
        # Health and status endpoints
        @self.app.get("/health")
        async def health_check():
            """Comprehensive system health check"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not initialized")
            
            health = await self.bootstrap.health_check()
            
            if health.get("healthy", False):
                return health
            else:
                raise HTTPException(status_code=503, detail=health)
        
        @self.app.get("/status")
        async def system_status():
            """Detailed system status"""
            if not self.bootstrap:
                return {"status": "initializing"}
            
            return await self.bootstrap.health_check()
        
        # Stimuli processing endpoints (GraphFlow + AutoGen compatibility)
        @self.app.post("/api/stimuli/receive")
        @handle_errors(operation="receive_stimuli", component="unified_api")
        async def receive_stimuli(
            stimuli_id: str,
            content: str,
            source: str,
            priority: str = "medium",
            processing_mode: str = "auto",
            team_preference: Optional[str] = None,
            character_type: Optional[str] = None,
            metadata: dict = None
        ):
            """
            Unified stimuli processing endpoint.
            
            Replaces both:
            - GraphFlow external stimuli API
            - AutoGen simplified stimuli API
            """
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            async with error_context(
                operation="process_stimuli",
                component="api",
                metadata={"stimuli_id": stimuli_id, "source": source}
            ):
                processor = self.bootstrap.get_service(StimuliProcessor)
                
                # Convert string parameters to enums
                try:
                    mode = ProcessingMode(processing_mode) if processing_mode != "auto" else ProcessingMode.AUTO
                except ValueError:
                    mode = ProcessingMode.AUTO
                
                team = None
                if team_preference:
                    try:
                        team = TeamType(team_preference)
                    except ValueError:
                        pass
                
                # Add character type to metadata for backward compatibility
                if not metadata:
                    metadata = {}
                if character_type:
                    metadata["character_type"] = character_type
                
                # Process stimuli
                result = await processor.process_stimuli(
                    content=content,
                    source=source,
                    priority=priority,
                    processing_mode=mode,
                    team_preference=team,
                    metadata=metadata
                )
                
                # Handle both single and multiple results
                if isinstance(result, list):
                    return {
                        "stimuli_id": stimuli_id,
                        "status": "success",
                        "processing_mode": "multiple",
                        "results": [
                            {
                                "success": r.success,
                                "mode": r.processing_mode.value,
                                "team": r.team_type.value if r.team_type else None,
                                "processing_time": r.processing_time,
                                "error": r.error_message
                            }
                            for r in result
                        ]
                    }
                else:
                    return {
                        "stimuli_id": stimuli_id,
                        "status": "success" if result.success else "failed",
                        "processing_mode": result.processing_mode.value,
                        "team_type": result.team_type.value if result.team_type else None,
                        "processing_time": result.processing_time,
                        "queued": result.analysis.get("queued", False) if result.analysis else False,
                        "message_id": result.analysis.get("message_id") if result.analysis else None,
                        "error": result.error_message
                    }
        
        # Character management endpoints
        @self.app.get("/api/characters")
        async def list_characters():
            """List all registered characters"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            character_manager = self.bootstrap.get_service(CharacterManager)
            
            characters = []
            for char_id, profile in character_manager.profiles.items():
                state = character_manager.states.get(char_id)
                
                characters.append({
                    "id": profile.id,
                    "name": profile.name,
                    "template": profile.template_name,
                    "mission_type": profile.mission_type.value,
                    "system_assignment": profile.system_assignment,
                    "capabilities": profile.capabilities,
                    "current_state": state.current_state.value if state else "unknown",
                    "current_mission": state.current_mission if state else None,
                    "active_sessions": len(state.active_sessions) if state else 0,
                    "error_count": state.error_count if state else 0
                })
            
            return {"characters": characters}
        
        @self.app.get("/api/characters/available")
        async def get_available_characters(
            mission_type: Optional[str] = None,
            system: Optional[str] = None
        ):
            """Get available characters for assignment"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            character_manager = self.bootstrap.get_service(CharacterManager)
            
            mission_enum = None
            if mission_type:
                try:
                    from shared.character import MissionType
                    mission_enum = MissionType(mission_type)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid mission type: {mission_type}")
            
            available = await character_manager.get_available_characters(
                mission_type=mission_enum,
                system_assignment=system
            )
            
            return {
                "available_characters": [
                    {
                        "id": char.id,
                        "name": char.name,
                        "mission_type": char.mission_type.value,
                        "capabilities": char.capabilities
                    }
                    for char in available
                ]
            }
        
        # Queue management endpoints
        @self.app.get("/api/queues/stats")
        async def queue_statistics():
            """Get queue statistics"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            queue_service = self.bootstrap.get_service(QueueService)
            stats = await queue_service.get_stats()
            
            return {"queue_stats": stats}
        
        @self.app.post("/api/queues/{queue_name}/purge")
        async def purge_queue(queue_name: str):
            """Purge all messages from a queue"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            queue_service = self.bootstrap.get_service(QueueService)
            purged_count = await queue_service.purge(queue_name)
            
            return {"purged_messages": purged_count}
        
        # Processing statistics
        @self.app.get("/api/stats")
        async def processing_statistics():
            """Get comprehensive processing statistics"""
            if not self.bootstrap:
                raise HTTPException(status_code=503, detail="System not ready")
            
            stats = {}
            
            # Processing stats
            processor = self.bootstrap.get_service(StimuliProcessor)
            stats["processing"] = processor.get_stats()
            
            # Character stats
            character_manager = self.bootstrap.get_service(CharacterManager)
            stats["characters"] = character_manager.get_system_stats()
            
            # Queue stats
            queue_service = self.bootstrap.get_service(QueueService)
            stats["queues"] = await queue_service.get_stats()
            
            # Error stats
            error_handler = self.bootstrap.get_service(ErrorHandler)
            stats["errors"] = error_handler.get_error_stats()
            
            return stats
        
        # Legacy compatibility endpoints
        @self.app.post("/api/stimuli/s2")
        async def legacy_s2_processing(
            content: str,
            character_type: Optional[str] = None,
            priority: str = "medium"
        ):
            """Legacy S2 processing endpoint for backward compatibility"""
            return await receive_stimuli(
                stimuli_id=f"legacy_{hash(content)}",
                content=content,
                source="legacy_s2_api",
                priority=priority,
                processing_mode="s2_only",
                character_type=character_type
            )
        
        # Configuration endpoints
        @self.app.get("/api/config")
        async def get_configuration():
            """Get current system configuration"""
            config = get_config()
            
            return {
                "system_mode": config.system_mode.value,
                "environment": config.environment,
                "debug": config.debug,
                "queue_type": config.queue.type,
                "api_host": config.api_host,
                "api_port": config.api_port
            }
    
    async def start_server(
        self,
        host: str = None,
        port: int = None,
        workers: int = None
    ):
        """Start the unified server"""
        config = get_config()
        
        server_config = uvicorn.Config(
            app=self.app,
            host=host or config.api_host,
            port=port or config.api_port,
            workers=workers or config.api_workers,
            log_level="info"
        )
        
        server = uvicorn.Server(server_config)
        await server.serve()


async def main():
    """Main entry point for unified CORE system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified CORE System")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--env", default="development", help="Environment")
    parser.add_argument("--mode", help="System mode (simplified/full_autogen/hybrid)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    
    args = parser.parse_args()
    
    try:
        # Initialize configuration
        config_overrides = {}
        if args.mode:
            config_overrides["system_mode"] = args.mode
        
        # Initialize CORE system
        bootstrap = await initialize_core_system(
            config_file=args.config,
            environment=args.env,
            **config_overrides
        )
        
        # Create and start API server
        api = UnifiedCoreAPI()
        
        logger.info(f"🌟 Starting Unified CORE System on {args.host}:{args.port}")
        logger.info(f"📖 API Documentation: http://{args.host}:{args.port}/docs")
        logger.info(f"❤️ Health Check: http://{args.host}:{args.port}/health")
        
        await api.start_server(
            host=args.host,
            port=args.port,
            workers=args.workers
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # For development
    if len(sys.argv) == 1:
        sys.argv.extend(["--env", "development", "--mode", "simplified"])
    
    asyncio.run(main())