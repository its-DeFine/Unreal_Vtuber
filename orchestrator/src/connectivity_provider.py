"""
Connectivity Proof Provider for Orchestrators
Replaces GPU info with connectivity proof to manager
"""

import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import httpx


class ConnectivityProofProvider:
    """Provides connectivity proof to the manager"""
    
    def __init__(
        self,
        orchestrator_id: str,
        manager_url: str,
        endpoint: str,
        capabilities: list = None
    ):
        self.orchestrator_id = orchestrator_id
        self.manager_url = manager_url
        self.endpoint = endpoint
        self.capabilities = capabilities or []
        self.connection_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.calls_processed = 0
        self.total_latency = 0
        self.proof_interval = 60  # seconds
        self.is_registered = False
        self.current_challenge = None
        
    async def register(self) -> bool:
        """Register with the manager and get initial challenge"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.manager_url}/api/v1/livepeer/orchestrators/register",
                    json={
                        "orchestrator_id": self.orchestrator_id,
                        "endpoint": self.endpoint,
                        "capabilities": self.capabilities
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.current_challenge = data.get("challenge")
                    self.is_registered = True
                    print(f"[connectivity] Registered with manager, challenge: {self.current_challenge}")
                    return True
                else:
                    print(f"[connectivity] Registration failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"[connectivity] Registration error: {e}")
                return False
    
    async def generate_proof(self, secret_key: str = None) -> Dict[str, Any]:
        """Generate a connectivity proof"""
        if not self.current_challenge:
            print("[connectivity] No challenge available")
            return None
            
        # Calculate metrics
        uptime = int(time.time() - self.start_time)
        avg_latency = self.total_latency / max(self.calls_processed, 1)
        
        # Generate response to challenge
        if not secret_key:
            # In production, this would be a shared secret or use proper crypto
            secret_key = os.getenv("ORCHESTRATOR_SECRET", "default_secret")
            
        response = hashlib.sha256(
            f"{self.current_challenge}:{self.orchestrator_id}:{secret_key}".encode()
        ).hexdigest()
        
        proof = {
            "orchestrator_id": self.orchestrator_id,
            "timestamp": datetime.utcnow().isoformat(),
            "connection_id": self.connection_id,
            "manager_challenge": self.current_challenge,
            "orchestrator_response": response,
            "metrics": {
                "latency_ms": int(avg_latency),
                "uptime_seconds": uptime,
                "processed_calls": self.calls_processed
            },
            "capabilities": self.capabilities
        }
        
        return proof
    
    async def submit_proof(self, proof: Dict[str, Any]) -> bool:
        """Submit connectivity proof to manager"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.manager_url}/api/v1/livepeer/orchestrators/{self.orchestrator_id}/proof",
                    json=proof
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Get new challenge for next proof
                    if "challenge" in data:
                        self.current_challenge = data["challenge"]
                    print(f"[connectivity] Proof accepted, next required in {data.get('next_proof_required', 60)}s")
                    return True
                else:
                    print(f"[connectivity] Proof rejected: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"[connectivity] Proof submission error: {e}")
                return False
    
    async def start_proof_loop(self):
        """Start the connectivity proof loop"""
        if not self.is_registered:
            success = await self.register()
            if not success:
                print("[connectivity] Failed to register, retrying in 30s...")
                await asyncio.sleep(30)
                return await self.start_proof_loop()
        
        while True:
            try:
                # Generate and submit proof
                proof = await self.generate_proof()
                if proof:
                    await self.submit_proof(proof)
                
                # Wait for next interval
                await asyncio.sleep(self.proof_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[connectivity] Proof loop error: {e}")
                await asyncio.sleep(10)
    
    def record_call(self, latency_ms: float):
        """Record a processed call for metrics"""
        self.calls_processed += 1
        self.total_latency += latency_ms
    
    async def handle_manager_request(self, request_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests from the manager"""
        if request_type == "health_check":
            return {
                "status": "healthy",
                "orchestrator_id": self.orchestrator_id,
                "uptime": int(time.time() - self.start_time),
                "calls_processed": self.calls_processed
            }
        
        elif request_type == "execute_call":
            # Simulate call execution
            start = time.time()
            
            # Process the call based on type
            call_type = payload.get("call_type")
            if call_type == "payment":
                # Simulate payment processing
                await asyncio.sleep(0.1)
                result = {"status": "completed", "transaction_id": str(uuid.uuid4())}
            elif call_type == "transcode":
                # Simulate transcoding
                await asyncio.sleep(0.5)
                result = {"status": "completed", "output_url": f"output_{uuid.uuid4()}.mp4"}
            else:
                result = {"status": "unknown_call_type"}
            
            # Record metrics
            latency = (time.time() - start) * 1000
            self.record_call(latency)
            
            return {
                "orchestrator_id": self.orchestrator_id,
                "call_type": call_type,
                "result": result,
                "latency_ms": latency
            }
        
        elif request_type == "get_capabilities":
            return {
                "orchestrator_id": self.orchestrator_id,
                "capabilities": self.capabilities,
                "connection_id": self.connection_id
            }
        
        else:
            return {"error": f"Unknown request type: {request_type}"}


class OrchestratorConnectivityService:
    """Service to manage orchestrator connectivity"""
    
    def __init__(self):
        self.provider: Optional[ConnectivityProofProvider] = None
        self.proof_task: Optional[asyncio.Task] = None
        
    async def initialize(
        self,
        orchestrator_id: str = None,
        manager_url: str = None,
        endpoint: str = None,
        capabilities: list = None
    ):
        """Initialize the connectivity service"""
        # Get from environment if not provided
        orchestrator_id = orchestrator_id or os.getenv("ORCHESTRATOR_ID", f"orch-{uuid.uuid4().hex[:8]}")
        manager_url = manager_url or os.getenv("MANAGER_URL", "http://localhost:8010")
        endpoint = endpoint or os.getenv("ORCHESTRATOR_ENDPOINT", f"http://{orchestrator_id}:8082")
        
        # Default capabilities
        if capabilities is None:
            capabilities = os.getenv("ORCHESTRATOR_CAPABILITIES", "payment_processing,video_transcoding").split(",")
        
        self.provider = ConnectivityProofProvider(
            orchestrator_id=orchestrator_id,
            manager_url=manager_url,
            endpoint=endpoint,
            capabilities=capabilities
        )
        
        # Start proof loop
        self.proof_task = asyncio.create_task(self.provider.start_proof_loop())
        
        print(f"[connectivity] Service initialized for {orchestrator_id}")
        print(f"[connectivity] Manager URL: {manager_url}")
        print(f"[connectivity] Capabilities: {capabilities}")
        
    async def shutdown(self):
        """Shutdown the connectivity service"""
        if self.proof_task:
            self.proof_task.cancel()
            try:
                await self.proof_task
            except asyncio.CancelledError:
                pass
        
        print("[connectivity] Service shutdown complete")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current connectivity status"""
        if not self.provider:
            return {"status": "not_initialized"}
        
        return {
            "orchestrator_id": self.provider.orchestrator_id,
            "is_registered": self.provider.is_registered,
            "connection_id": self.provider.connection_id,
            "uptime": int(time.time() - self.provider.start_time),
            "calls_processed": self.provider.calls_processed,
            "capabilities": self.provider.capabilities
        }


# Global service instance
connectivity_service = OrchestratorConnectivityService()


async def main():
    """Standalone connectivity provider for testing"""
    print("Starting Orchestrator Connectivity Provider")
    
    service = OrchestratorConnectivityService()
    await service.initialize()
    
    try:
        # Keep running
        while True:
            status = await service.get_status()
            print(f"Status: {json.dumps(status, indent=2)}")
            await asyncio.sleep(30)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())