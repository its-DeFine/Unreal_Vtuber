"""
Docker Control Module for Orchestrator
Provides actual container management capabilities
"""
import asyncio
import docker
import httpx
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class DockerController:
    """Manages Docker containers for agent control"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.available = True
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
            self.available = False
    
    async def stop_container(self, container_name: str) -> Dict[str, Any]:
        """Stop a Docker container"""
        if not self.available:
            return {"status": "error", "message": "Docker not available"}
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=10)
            logger.info(f"Container {container_name} stopped")
            return {
                "status": "success",
                "message": f"Container {container_name} stopped",
                "container_id": container.id[:12]
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start_container(self, container_name: str) -> Dict[str, Any]:
        """Start a Docker container"""
        if not self.available:
            return {"status": "error", "message": "Docker not available"}
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.start()
            logger.info(f"Container {container_name} started")
            return {
                "status": "success",
                "message": f"Container {container_name} started",
                "container_id": container.id[:12]
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            logger.error(f"Failed to start container {container_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def restart_container(self, container_name: str) -> Dict[str, Any]:
        """Restart a Docker container"""
        if not self.available:
            return {"status": "error", "message": "Docker not available"}
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart(timeout=10)
            logger.info(f"Container {container_name} restarted")
            return {
                "status": "success",
                "message": f"Container {container_name} restarted",
                "container_id": container.id[:12]
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            logger.error(f"Failed to restart container {container_name}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Get status of a Docker container"""
        if not self.available:
            return {"status": "error", "message": "Docker not available"}
        
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            return {
                "status": "success",
                "container": container_name,
                "state": container.status,
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown"),
                "created": container.attrs.get("Created", "unknown"),
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                "memory_usage_mb": round(stats.get("memory_stats", {}).get("usage", 0) / 1024 / 1024, 2)
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            logger.error(f"Failed to get status for container {container_name}: {e}")
            return {"status": "error", "message": str(e)}


class VTuberController:
    """Controls VTuber-specific operations"""
    
    def __init__(self):
        self.s1_url = "http://neurosync_s1:5001"
        self.s2_url = "http://autogen_agent:8000"
        
    async def swap_character(self, character_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Swap VTuber character"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send character switch command to S1
                response = await client.post(
                    f"{self.s1_url}/character/switch",
                    json={
                        "character_id": character_name
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Character swapped to {character_name}")
                    return {
                        "status": "success",
                        "message": f"Character swapped to {character_name}",
                        "response": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to swap character: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to swap character: {e}")
            return {"status": "error", "message": str(e)}
    
    async def generate_speech(self, text: str, voice: Optional[str] = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate speech for VTuber"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send text to process for speech
                response = await client.post(
                    f"{self.s1_url}/process_text",
                    json={
                        "text": text,
                        "voice_settings": parameters or {}
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Speech generated: {text[:50]}...")
                    return {
                        "status": "success",
                        "message": "Speech generated successfully",
                        "response": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to generate speech: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return {"status": "error", "message": str(e)}
    
    async def trigger_animation(self, animation_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Trigger VTuber animation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send animation command to S1
                response = await client.post(
                    f"{self.s1_url}/api/animation/trigger",
                    json={
                        "animation": animation_name,
                        "parameters": parameters or {}
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Animation triggered: {animation_name}")
                    return {
                        "status": "success",
                        "message": f"Animation {animation_name} triggered",
                        "response": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to trigger animation: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to trigger animation: {e}")
            return {"status": "error", "message": str(e)}
    
    async def send_stimulus_to_s2(self, stimulus: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send stimulus to S2 (AutoGen agents)"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send stimulus to S2
                response = await client.post(
                    f"{self.s2_url}/api/stimulus",
                    json={
                        "stimulus": stimulus,
                        "parameters": parameters or {}
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Stimulus sent to S2: {stimulus[:50]}...")
                    return {
                        "status": "success",
                        "message": "Stimulus processed by S2",
                        "response": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to send stimulus: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to send stimulus to S2: {e}")
            return {"status": "error", "message": str(e)}


# Global instances
docker_controller = DockerController()
vtuber_controller = VTuberController()