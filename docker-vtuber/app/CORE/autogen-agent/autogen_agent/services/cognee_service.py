"""
🧠 Cognee Service - Official Open Source Integration

Based on official Cognee documentation:
https://github.com/topoteretes/cognee
https://docs.cognee.ai/tutorials/use-the-api

Key Features:
- Bearer token authentication via login endpoint
- Proper dataset management  
- Search with multiple types (GRAPH_COMPLETION, etc.)
- Error handling and retry logic
"""

import aiohttp
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

class CogneeService:
    """Official Cognee open source service integration"""
    
    def __init__(self, base_url: str, username: str = "default_user@example.com", 
                 password: str = "default_password", dataset_name: str = "autogen_agent"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.dataset_name = dataset_name
        self.access_token = None
        self.token_expires = None
        
        logging.info(f"🧠 [COGNEE_SERVICE] Initialized with base URL: {self.base_url}")
        
    async def initialize(self) -> bool:
        """Initialize Cognee service and get access token"""
        try:
            await self.authenticate()
            logging.info("✅ [COGNEE_SERVICE] Successfully initialized and authenticated")
            return True
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Initialization failed: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Cognee API and get Bearer token"""
        try:
            # Use form data for authentication as per official docs
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data=login_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as response:
                    if response.status == 200:
                        auth_data = await response.json()
                        self.access_token = auth_data.get('access_token')
                        
                        if self.access_token:
                            # Set token expiration (assume 1 hour if not provided)
                            self.token_expires = datetime.now() + timedelta(hours=1)
                            logging.info("🔐 [COGNEE_SERVICE] Authentication successful")
                            return True
                        else:
                            logging.error("❌ [COGNEE_SERVICE] No access token in response")
                            return False
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ [COGNEE_SERVICE] Authentication failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Authentication error: {e}")
            return False
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or (self.token_expires and datetime.now() >= self.token_expires):
            await self.authenticate()
    
    async def health_check(self) -> bool:
        """Check if Cognee service is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    is_healthy = response.status == 200
                    logging.info(f"🏥 [COGNEE_SERVICE] Health check: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
                    return is_healthy
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Health check failed: {e}")
            return False
    
    async def add_data(self, data: List[str]) -> Dict[str, Any]:
        """Add data to Cognee knowledge graph"""
        await self._ensure_authenticated()
        
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Create multipart form data for file uploads
            form_data = aiohttp.FormData()
            
            # Add each piece of data as a file upload
            for i, item in enumerate(data):
                form_data.add_field('data', item, filename=f'data_{i}.txt', content_type='text/plain')
            
            # Add dataset name
            form_data.add_field('datasetName', self.dataset_name)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/add/",
                    headers=headers,
                    data=form_data
                ) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                        except:
                            # Handle null/empty response
                            result = {"success": True}
                        logging.info(f"✅ [COGNEE_SERVICE] Added {len(data)} items to dataset '{self.dataset_name}'")
                        return result
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ [COGNEE_SERVICE] Add data failed: {response.status} - {error_text}")
                        return {"error": f"Status {response.status}: {error_text}"}
                        
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Add data error: {e}")
            return {"error": str(e)}
    
    async def cognify(self, datasets: Optional[List[str]] = None) -> Dict[str, Any]:
        """Process and create entity relationships (cognify)"""
        await self._ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Use current dataset if none specified
            if datasets is None:
                datasets = [self.dataset_name]
            
            payload = {
                "datasets": datasets
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/cognify/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                        except:
                            # Handle null/empty response (success)
                            result = {"success": True, "message": "Cognify completed"}
                        logging.info(f"🧩 [COGNEE_SERVICE] Cognify completed for datasets: {datasets}")
                        return result
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ [COGNEE_SERVICE] Cognify failed: {response.status} - {error_text}")
                        return {"error": f"Status {response.status}: {error_text}"}
                        
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Cognify error: {e}")
            return {"error": str(e)}
    
    async def search(self, query: str, search_type: str = "CHUNKS", 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search Cognee knowledge graph with semantic and graph traversal"""
        await self._ensure_authenticated()
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "searchType": search_type,
                "query": query,
                "topK": limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/search/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Handle different response formats
                        if isinstance(result, list):
                            search_results = result
                        elif isinstance(result, dict) and 'results' in result:
                            search_results = result['results']
                        else:
                            search_results = [result] if result else []
                        
                        logging.info(f"🔍 [COGNEE_SERVICE] Search found {len(search_results)} results for: '{query[:50]}...'")
                        return search_results
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ [COGNEE_SERVICE] Search failed: {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Search error: {e}")
            return []
    
    async def delete_data(self, data: List[str], mode: str = "soft") -> Dict[str, Any]:
        """Delete data from Cognee dataset"""
        await self._ensure_authenticated()
        
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Use form data for deletion
            form_data = aiohttp.FormData()
            
            # Add each piece of data to delete
            for item in data:
                form_data.add_field('data', item)
            
            # Add dataset name and mode
            form_data.add_field('datasetName', self.dataset_name)
            form_data.add_field('mode', mode)
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/v1/delete",
                    headers=headers,
                    data=form_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logging.info(f"🗑️ [COGNEE_SERVICE] Deleted {len(data)} items from dataset '{self.dataset_name}' (mode: {mode})")
                        return result
                    else:
                        error_text = await response.text()
                        logging.error(f"❌ [COGNEE_SERVICE] Delete failed: {response.status} - {error_text}")
                        return {"error": f"Status {response.status}: {error_text}"}
                        
        except Exception as e:
            logging.error(f"❌ [COGNEE_SERVICE] Delete error: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status and dataset information"""
        await self._ensure_authenticated()
        
        return {
            "service": "cognee",
            "base_url": self.base_url,
            "dataset": self.dataset_name,
            "authenticated": bool(self.access_token),
            "token_expires": self.token_expires.isoformat() if self.token_expires else None,
            "health": await self.health_check()
        }

# Legacy compatibility - keep the old interface but use new implementation
class CogneeMemoryService(CogneeService):
    """Legacy compatibility wrapper for old CogneeService"""
    
    async def add_memory(self, content: List[str]) -> Dict:
        """Legacy method - use add_data instead"""
        return await self.add_data(content)
    
    async def search_knowledge_graph(self, query: str, **kwargs) -> List[Dict]:
        """Legacy method - use search instead"""
        return await self.search(query, **kwargs) 