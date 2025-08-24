"""
Manager Client for Orchestrator
Handles registration, heartbeat, and communication with central manager
"""
import os
import asyncio
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ManagerClient:
    """Client for communication with central manager"""
    
    def __init__(self):
        self.manager_url = os.getenv("CENTRAL_MANAGER_URL")
        self.manager_token = os.getenv("CENTRAL_MANAGER_TOKEN", "")
        self.orchestrator_name = os.getenv("ORCHESTRATOR_NAME", "vtuber_orchestrator")
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://vtuber_orchestrator:8080")
        self.orchestrator_id: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.connected = False
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def initialize(self):
        """Initialize manager connection"""
        if not self.manager_url:
            logger.info("No CENTRAL_MANAGER_URL configured, running in standalone mode")
            return False
            
        try:
            # Try to register with manager
            await self.register()
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            self.connected = True
            logger.info("Connected to central manager", 
                       manager_url=self.manager_url,
                       orchestrator_id=self.orchestrator_id)
            return True
            
        except Exception as e:
            logger.warning("Failed to connect to central manager, running standalone", 
                          error=str(e))
            return False
    
    async def register(self) -> str:
        """Register with central manager"""
        try:
            # Get orchestrator_id from env or generate one
            orchestrator_id = os.getenv("ORCHESTRATOR_ID", f"{self.orchestrator_name}_{os.getpid()}")
            
            registration_data = {
                "orchestrator_id": orchestrator_id,  # Added required field
                "name": self.orchestrator_name,
                "url": self.orchestrator_url,
                "address": self.orchestrator_url,  # Some managers expect 'address'
                "capabilities": [
                    "routing",
                    "agent_control",
                    "metrics_collection",
                    "s1_integration",
                    "s2_integration"
                ],
                "version": "2.1.0",
                "metadata": {
                    "environment": os.getenv("ENVIRONMENT", "production"),
                    "region": os.getenv("REGION", "default"),
                    "max_agents": 50,
                    "ollama_enabled": True
                }
            }
            
            response = await self.client.post(
                f"{self.manager_url}/api/orchestrators/register",
                json=registration_data,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                self.orchestrator_id = data.get("orchestrator_id")
                logger.info("Registered with manager", orchestrator_id=self.orchestrator_id)
                return self.orchestrator_id
            else:
                raise Exception(f"Registration failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error("Failed to register with manager", error=str(e))
            raise
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to manager"""
        if not self.orchestrator_id:
            return False
            
        try:
            # Collect current metrics
            metrics = await self._collect_metrics()
            
            heartbeat_data = {
                "status": "healthy",
                "metrics": metrics,
                "active_agents": await self._get_active_agents(),
                "load": await self._calculate_load()
            }
            
            response = await self.client.post(
                f"{self.manager_url}/api/orchestrators/{self.orchestrator_id}/heartbeat",
                json=heartbeat_data,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                logger.debug("Heartbeat sent successfully")
                return True
            elif response.status_code == 404:
                # Orchestrator not found, try to re-register
                logger.warning("Orchestrator not found in manager, re-registering")
                await self.register()
                return True
            else:
                logger.warning("Heartbeat failed", 
                             status_code=response.status_code,
                             response=response.text)
                return False
                
        except Exception as e:
            logger.error("Failed to send heartbeat", error=str(e))
            return False
    
    async def _heartbeat_loop(self):
        """Background task for sending heartbeats"""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                success = await self.send_heartbeat()
                if not success:
                    logger.warning("Heartbeat failed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in heartbeat loop", error=str(e))
    
    async def report_metrics(self, metrics: Dict[str, Any]):
        """Report metrics to manager"""
        if not self.connected or not self.orchestrator_id:
            return
            
        try:
            # Metrics are sent with heartbeat, store for next heartbeat
            self._latest_metrics = metrics
        except Exception as e:
            logger.error("Failed to report metrics", error=str(e))
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics"""
        try:
            # TODO: Implement actual metrics collection
            return {
                "requests_per_minute": 0,
                "average_response_time": 0,
                "error_rate": 0,
                "active_connections": 0,
                "memory_usage_mb": 0,
                "cpu_usage_percent": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Failed to collect metrics", error=str(e))
            return {}
    
    async def _get_active_agents(self) -> List[str]:
        """Get list of active agents"""
        try:
            # TODO: Implement actual agent discovery
            return ["s1", "s2", "autogen_agent", "neurosync_s1"]
        except Exception as e:
            logger.error("Failed to get active agents", error=str(e))
            return []
    
    async def _calculate_load(self) -> float:
        """Calculate current system load (0.0 - 1.0)"""
        try:
            # TODO: Implement actual load calculation
            return 0.3  # 30% load
        except Exception as e:
            logger.error("Failed to calculate load", error=str(e))
            return 0.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for manager requests"""
        headers = {"Content-Type": "application/json"}
        if self.manager_token:
            headers["Authorization"] = f"Bearer {self.manager_token}"
        return headers
    
    async def shutdown(self):
        """Shutdown manager client"""
        try:
            # Cancel heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Close HTTP client
            await self.client.aclose()
            
            logger.info("Manager client shutdown complete")
        except Exception as e:
            logger.error("Error during manager client shutdown", error=str(e))