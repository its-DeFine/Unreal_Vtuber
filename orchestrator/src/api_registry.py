"""
API Registry - Manages available APIs and their capabilities
"""
import yaml
import httpx
from typing import Dict, Any, List, Optional
import structlog
from pathlib import Path

logger = structlog.get_logger()


class APIRegistry:
    """
    Manages the registry of available APIs and their capabilities
    """
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.apis: Dict[str, Any] = {}
        self.routing_rules: Dict[str, Any] = {}
        
    async def load(self):
        """Load API registry from YAML configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.apis = config.get('apis', {})
            self.routing_rules = config.get('routing_rules', {})
            
            logger.info("API registry loaded",
                       api_count=len(self.apis),
                       rules_count=len(self.routing_rules))
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            logger.error("Failed to load API registry", error=str(e))
            raise
    
    def _validate_config(self):
        """Validate the loaded configuration"""
        required_api_fields = ['endpoint', 'capabilities']
        
        for api_name, api_config in self.apis.items():
            for field in required_api_fields:
                if field not in api_config:
                    raise ValueError(f"API {api_name} missing required field: {field}")
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities summary for all APIs"""
        capabilities = {}
        
        for api_name, api_config in self.apis.items():
            capabilities[api_name] = {
                'capabilities': api_config.get('capabilities', []),
                'personas': [p['name'] for p in api_config.get('personas', [])],
                'teams': list(api_config.get('teams', {}).keys())
            }
        
        return capabilities
    
    def find_api_for_capability(self, capability: str) -> Optional[str]:
        """Find which API provides a specific capability"""
        for api_name, api_config in self.apis.items():
            if capability in api_config.get('capabilities', []):
                return api_name
        return None
    
    def get_triggers(self, api_name: str, entity_type: str) -> List[str]:
        """Get trigger words for personas or teams"""
        api_config = self.apis.get(api_name, {})
        triggers = []
        
        if entity_type == 'persona':
            for persona in api_config.get('personas', []):
                triggers.extend(persona.get('triggers', []))
        elif entity_type == 'team':
            for team_config in api_config.get('teams', {}).values():
                triggers.extend(team_config.get('triggers', []))
        
        return triggers
    
    async def check_health(self, api_name: str) -> bool:
        """Check if an API is healthy"""
        api_config = self.apis.get(api_name)
        if not api_config:
            return False
        
        endpoint = api_config['endpoint']
        health_path = api_config.get('health_check', '/health')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{endpoint}{health_path}",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Health check failed", 
                         api=api_name, 
                         error=str(e))
            return False
    
    def get_api_endpoint(self, api_name: str, operation: str) -> Dict[str, Any]:
        """Get endpoint details for a specific API operation"""
        api_config = self.apis.get(api_name, {})
        endpoints = api_config.get('api_endpoints', {})
        return endpoints.get(operation, {})
    
    def match_routing_pattern(self, text: str) -> Optional[Dict[str, Any]]:
        """Check if text matches any hybrid routing patterns"""
        hybrid_patterns = self.routing_rules.get('hybrid_patterns', [])
        
        import re
        for pattern_config in hybrid_patterns:
            pattern = pattern_config.get('pattern')
            if pattern and re.search(pattern, text, re.IGNORECASE):
                return pattern_config
        
        return None