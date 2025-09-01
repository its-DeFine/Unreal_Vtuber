#!/usr/bin/env python3
"""
Cluster Management Agent for Remote Orchestrator Control
Provides full container lifecycle management and cluster operations
"""

import os
import json
import asyncio
import docker
import yaml
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
COMPOSE_FILE = os.environ.get("COMPOSE_FILE", "docker-compose.yml")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
MANAGER_URL = os.environ.get("MANAGER_URL", "http://central-manager:8000")
CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "vtuber-cluster")

# Pydantic models
class ContainerConfig(BaseModel):
    name: str
    image: str
    environment: Dict[str, str] = {}
    networks: List[str] = ["vtuber_network"]
    volumes: List[str] = []
    ports: List[str] = []
    restart_policy: str = "unless-stopped"
    command: Optional[List[str]] = None

class ResetConfig(BaseModel):
    mode: str = "soft"  # soft or hard
    backup: bool = True
    services: List[str] = ["all"]

class ConfigUpdate(BaseModel):
    environment: Dict[str, str] = {}
    compose_overrides: Dict[str, Any] = {}
    apply_mode: str = "restart"  # restart or hot-reload

class ClusterManagementAgent:
    """Main cluster management agent"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except:
            self.docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        
        self.compose_file = Path(COMPOSE_FILE)
        self.backup_dir = Path(BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status"""
        try:
            containers = self.docker_client.containers.list(all=True)
            
            status = {
                "cluster_name": CLUSTER_NAME,
                "total_containers": len(containers),
                "running": sum(1 for c in containers if c.status == "running"),
                "stopped": sum(1 for c in containers if c.status != "running"),
                "containers": []
            }
            
            for container in containers:
                try:
                    image_name = container.image.tags[0] if container.image.tags else container.attrs['Config']['Image']
                except:
                    image_name = "unknown"
                
                status["containers"].append({
                    "id": container.short_id,
                    "name": container.name,
                    "image": image_name,
                    "status": container.status,
                    "created": container.attrs['Created'],
                    "ports": container.ports
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            raise
    
    async def reset_cluster(self, config: ResetConfig) -> Dict[str, Any]:
        """Reset cluster to clean state"""
        try:
            result = {
                "mode": config.mode,
                "backup_created": False,
                "services_reset": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Create backup if requested
            if config.backup:
                backup_path = await self.create_backup()
                result["backup_created"] = True
                result["backup_path"] = str(backup_path)
            
            # Get containers to reset
            containers = self.docker_client.containers.list(all=True)
            
            if "all" not in config.services:
                containers = [c for c in containers if c.name in config.services]
            
            if config.mode == "hard":
                # Hard reset - remove containers and recreate
                logger.info("Performing hard reset - removing all containers")
                
                for container in containers:
                    logger.info(f"Removing container: {container.name}")
                    container.stop()
                    container.remove(v=True)  # Remove with volumes
                    result["services_reset"].append(container.name)
                
                # Recreate from docker-compose
                os.system(f"docker-compose -f {self.compose_file} up -d")
                
            else:
                # Soft reset - just restart containers
                logger.info("Performing soft reset - restarting containers")
                
                for container in containers:
                    logger.info(f"Restarting container: {container.name}")
                    container.restart()
                    result["services_reset"].append(container.name)
            
            return result
            
        except Exception as e:
            logger.error(f"Error resetting cluster: {e}")
            raise
    
    async def create_container(self, config: ContainerConfig) -> Dict[str, Any]:
        """Create new container"""
        try:
            logger.info(f"Creating container: {config.name}")
            
            # Prepare container configuration
            container_config = {
                "image": config.image,
                "name": config.name,
                "environment": config.environment,
                "network": config.networks[0] if config.networks else None,
                "volumes": config.volumes,
                "ports": {p.split(":")[1]: p.split(":")[0] for p in config.ports if ":" in p},  # Fixed: container_port: host_port
                "restart_policy": {"Name": config.restart_policy},
                "detach": True
            }
            
            if config.command:
                container_config["command"] = config.command
            
            # Create and start container
            container = self.docker_client.containers.run(**container_config)
            
            # Add to additional networks
            for network_name in config.networks[1:]:
                try:
                    network = self.docker_client.networks.get(network_name)
                    network.connect(container)
                except:
                    logger.warning(f"Could not connect to network: {network_name}")
            
            return {
                "success": True,
                "container_id": container.short_id,
                "container_name": container.name,
                "status": container.status,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_container(self, container_id: str, force: bool = False, remove_volumes: bool = True) -> Dict[str, Any]:
        """Delete container"""
        try:
            container = self.docker_client.containers.get(container_id)
            container_name = container.name
            
            logger.info(f"Deleting container: {container_name} (ID: {container_id})")
            
            # Stop if running
            if container.status == "running":
                if force:
                    container.kill()
                else:
                    container.stop(timeout=30)
            
            # Remove container
            container.remove(v=remove_volumes)
            
            return {
                "success": True,
                "container_id": container_id,
                "container_name": container_name,
                "removed_at": datetime.now().isoformat(),
                "volumes_removed": remove_volumes
            }
            
        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail=f"Container {container_id} not found")
        except Exception as e:
            logger.error(f"Error deleting container: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_configuration(self, updates: ConfigUpdate) -> Dict[str, Any]:
        """Update cluster configuration"""
        try:
            result = {
                "environment_updated": False,
                "compose_updated": False,
                "services_restarted": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Update environment variables
            if updates.environment:
                env_file = Path(".env")
                env_lines = []
                
                if env_file.exists():
                    with open(env_file, 'r') as f:
                        env_lines = f.readlines()
                
                # Update or add environment variables
                for key, value in updates.environment.items():
                    found = False
                    for i, line in enumerate(env_lines):
                        if line.startswith(f"{key}="):
                            env_lines[i] = f"{key}={value}\n"
                            found = True
                            break
                    
                    if not found:
                        env_lines.append(f"{key}={value}\n")
                
                with open(env_file, 'w') as f:
                    f.writelines(env_lines)
                
                result["environment_updated"] = True
            
            # Update docker-compose overrides
            if updates.compose_overrides:
                override_file = Path("docker-compose.override.yml")
                
                if override_file.exists():
                    with open(override_file, 'r') as f:
                        override_config = yaml.safe_load(f) or {}
                else:
                    override_config = {"version": "3.8", "services": {}}
                
                # Merge overrides
                for service, config in updates.compose_overrides.items():
                    if service not in override_config["services"]:
                        override_config["services"][service] = {}
                    override_config["services"][service].update(config)
                
                with open(override_file, 'w') as f:
                    yaml.dump(override_config, f)
                
                result["compose_updated"] = True
            
            # Apply changes
            if updates.apply_mode == "restart":
                # Restart affected services with timeout
                containers = self.docker_client.containers.list()
                for container in containers:
                    if updates.environment or container.name in updates.compose_overrides.get("services", {}):
                        try:
                            container.restart(timeout=10)  # Add 10 second timeout
                            result["services_restarted"].append(container.name)
                        except Exception as e:
                            logger.warning(f"Failed to restart {container.name}: {e}")
                            # Continue with other containers instead of failing completely
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            raise
    
    async def create_backup(self) -> Path:
        """Create cluster configuration backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"cluster_backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup docker-compose files
            if self.compose_file.exists():
                shutil.copy(self.compose_file, backup_path / "docker-compose.yml")
            
            # Backup environment files
            env_file = Path(".env")
            if env_file.exists():
                shutil.copy(env_file, backup_path / ".env")
            
            # Backup override files
            override_file = Path("docker-compose.override.yml")
            if override_file.exists():
                shutil.copy(override_file, backup_path / "docker-compose.override.yml")
            
            # Save container states
            containers = self.docker_client.containers.list(all=True)
            container_states = []
            
            for container in containers:
                container_states.append({
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "status": container.status,
                    "environment": container.attrs['Config'].get('Env', []),
                    "labels": container.labels
                })
            
            with open(backup_path / "container_states.json", 'w') as f:
                json.dump(container_states, f, indent=2)
            
            logger.info(f"Backup created at: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        """Restore from backup"""
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                raise HTTPException(status_code=404, detail=f"Backup {backup_name} not found")
            
            result = {
                "backup_restored": backup_name,
                "files_restored": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Restore docker-compose files
            compose_backup = backup_path / "docker-compose.yml"
            if compose_backup.exists():
                shutil.copy(compose_backup, self.compose_file)
                result["files_restored"].append("docker-compose.yml")
            
            # Restore environment files
            env_backup = backup_path / ".env"
            if env_backup.exists():
                shutil.copy(env_backup, Path(".env"))
                result["files_restored"].append(".env")
            
            # Restore override files
            override_backup = backup_path / "docker-compose.override.yml"
            if override_backup.exists():
                shutil.copy(override_backup, Path("docker-compose.override.yml"))
                result["files_restored"].append("docker-compose.override.yml")
            
            # Recreate containers
            os.system(f"docker-compose -f {self.compose_file} up -d")
            
            return result
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise

# FastAPI app
app = FastAPI(title="Cluster Management Agent", version="1.0.0")
agent = ClusterManagementAgent()

# Security middleware
async def verify_auth(authorization: str = Header(None)):
    """Verify authorization header"""
    # TODO: Implement proper JWT validation
    # For now, skip auth for testing
    return True

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "cluster": CLUSTER_NAME}

@app.get("/status")
async def get_status(auth: bool = Depends(verify_auth)):
    """Get cluster status"""
    return await agent.get_cluster_status()

@app.post("/reset")
async def reset_cluster(config: ResetConfig, auth: bool = Depends(verify_auth)):
    """Reset cluster"""
    return await agent.reset_cluster(config)

@app.post("/containers")
async def create_container(config: ContainerConfig, auth: bool = Depends(verify_auth)):
    """Create new container"""
    return await agent.create_container(config)

@app.delete("/containers/{container_id}")
async def delete_container(container_id: str, force: bool = False, remove_volumes: bool = True, auth: bool = Depends(verify_auth)):
    """Delete container"""
    return await agent.delete_container(container_id, force, remove_volumes)

@app.put("/config")
async def update_config(updates: ConfigUpdate, auth: bool = Depends(verify_auth)):
    """Update configuration"""
    return await agent.update_configuration(updates)

@app.post("/backup")
async def create_backup(auth: bool = Depends(verify_auth)):
    """Create backup"""
    backup_path = await agent.create_backup()
    return {"success": True, "backup_path": str(backup_path)}

@app.post("/restore/{backup_name}")
async def restore_backup(backup_name: str, auth: bool = Depends(verify_auth)):
    """Restore from backup"""
    return await agent.restore_backup(backup_name)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)