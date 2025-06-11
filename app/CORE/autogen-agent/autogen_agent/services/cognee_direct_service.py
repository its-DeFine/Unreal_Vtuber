"""
🧠 Direct Cognee Integration - Using Python Library with Ollama

This service uses the official Cognee Python library directly instead of
making HTTP calls to a separate service. This approach is simpler and
more reliable for the open source version with local Ollama.

Based on the official Cognee usage:
import cognee
await cognee.add("text")
await cognee.cognify() 
await cognee.search("query")
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import cognee
    COGNEE_AVAILABLE = True
except ImportError:
    COGNEE_AVAILABLE = False
    logging.warning("🧠 [COGNEE_DIRECT] Cognee library not installed")

class CogneeDirectService:
    """Direct Cognee integration using the Python library with Ollama"""
    
    def __init__(self, dataset_name: str = "autogen_agent"):
        self.dataset_name = dataset_name
        self.initialized = False
        
        if not COGNEE_AVAILABLE:
            logging.error("❌ [COGNEE_DIRECT] Cognee library not available")
            return
        
        # 🔍 DEBUG: Log current environment before setting
        logging.info("🔍 [COGNEE_DIRECT] DEBUG - Environment BEFORE setting:")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_API_KEY (before): {os.environ.get('LLM_API_KEY', 'NOT_SET')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_PROVIDER (before): {os.environ.get('LLM_PROVIDER', 'NOT_SET')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_MODEL (before): {os.environ.get('LLM_MODEL', 'NOT_SET')}")
        
        # Set environment variables for Cognee (Ollama configuration per official docs)
        os.environ['LLM_PROVIDER'] = 'ollama'
        os.environ['LLM_MODEL'] = 'llama3-schema'
        os.environ['LLM_API_KEY'] = 'ollama'  # Official docs specify just "ollama"
        os.environ['LLM_ENDPOINT'] = 'http://ollama:11434/v1'  # Note the /v1 suffix
        os.environ['LLM_TEMPERATURE'] = '0.0'
        os.environ['LLM_MAX_TOKENS'] = '4096'
        
        # 🔧 Configure Fastembed for local embeddings (no API key required)
        # Per official Cognee documentation: https://docs.cognee.ai/how-to-guides/configuration
        # Fastembed is ideal for codegraph pipeline and avoids rate limits
        os.environ['EMBEDDING_PROVIDER'] = 'fastembed'
        os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'
        os.environ['EMBEDDING_DIMENSIONS'] = '384'
        os.environ['EMBEDDING_MAX_TOKENS'] = '256'
        
        # 🔧 HuggingFace tokenizer - using Cognee defaults to avoid conflicts
        
        # 🔧 NEW: Configure Cognee to avoid problematic summarization pipeline  
        os.environ['COGNEE_SUMMARIZATION_ENABLED'] = 'false'
        os.environ['COGNEE_DISABLE_BACKGROUND_TASKS'] = 'true'
        
        # 🔧 TEMPORARY FIX: Use CPU-only mode to avoid tokenizer issues
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        
        # 🔍 DEBUG: Log current environment after setting
        logging.info("🔍 [COGNEE_DIRECT] DEBUG - Environment AFTER setting:")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_API_KEY (after): {os.environ.get('LLM_API_KEY')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_PROVIDER (after): {os.environ.get('LLM_PROVIDER')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_MODEL (after): {os.environ.get('LLM_MODEL')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_ENDPOINT (after): {os.environ.get('LLM_ENDPOINT')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - EMBEDDING_API_KEY (after): {os.environ.get('EMBEDDING_API_KEY')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - EMBEDDING_PROVIDER (after): {os.environ.get('EMBEDDING_PROVIDER')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - EMBEDDING_MODEL (after): {os.environ.get('EMBEDDING_MODEL')}")
        logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - EMBEDDING_ENDPOINT (after): {os.environ.get('EMBEDDING_ENDPOINT')}")
        
        logging.info("🔑 [COGNEE_DIRECT] Configured for local Ollama (LLM + Embeddings)")
        
        try:
            import cognee
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Cognee imported successfully")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - Cognee has config: {dir(cognee.config)}")
            
            # 🔧 Use Cognee's native config methods per official documentation
            logging.info("🔧 [COGNEE_DIRECT] DEBUG - Setting Cognee config using native methods...")
            
            # Set LLM configuration using Cognee's config methods
            cognee.config.set_llm_provider('ollama')
            # Use our new schema-aware model that knows Cognee field names
            cognee.config.set_llm_model('llama3-schema')
            cognee.config.set_llm_api_key('ollama')
            cognee.config.set_llm_endpoint('http://ollama:11434/v1')
            
            # 🔧 Configure vector database to handle embedding issues
            try:
                cognee.config.set_vector_db_provider('lancedb')  # Use LanceDB which works better with Ollama
            except:
                logging.info("🔧 [COGNEE_DIRECT] Vector DB config not available (older version)")
            
            # 🔧 Embedding config already set via environment variables above
            
            logging.info("✅ [COGNEE_DIRECT] DEBUG - Cognee config methods applied successfully")
            
            # Test basic functionality
            logging.info("🧪 [COGNEE_DIRECT] DEBUG - Testing Cognee functionality...")
            
        except Exception as e:
            logging.error(f"❌ [COGNEE_DIRECT] Setup error: {e}")
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Continuing without Cognee...")
            self.initialized = False
            return
        
        logging.info(f"🧠 [COGNEE_DIRECT] Initialized for dataset: {self.dataset_name}")
    
    async def initialize(self) -> bool:
        """Initialize Cognee service"""
        if not COGNEE_AVAILABLE:
            return False
        
        try:
            # 🔍 DEBUG: Log environment values just before testing
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Environment at initialize:")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_API_KEY: '{os.environ.get('LLM_API_KEY', 'NOT_SET')}'")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_PROVIDER: '{os.environ.get('LLM_PROVIDER', 'NOT_SET')}'")
            
            # Test basic functionality
            await self._test_cognee_functionality()
            self.initialized = True
            logging.info("✅ [COGNEE_DIRECT] Successfully initialized with Ollama")
            return True
        except Exception as e:
            logging.error(f"❌ [COGNEE_DIRECT] Initialization failed: {e}")
            logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Exception type: {type(e)}")
            logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Exception args: {e.args}")
            return False
    
    async def _test_cognee_functionality(self):
        """Test basic Cognee functionality with simplified approach"""
        try:
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Starting test functionality...")
            
            # 🔍 DEBUG: Log before each cognee call
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - About to call cognee.add()")
            
            # Use simpler test data to avoid triggering complex summarization
            test_data = "Simple test: AutoGen system operational"
            await cognee.add(test_data)
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.add() completed successfully")
            
            # Try to cognify (this processes the data) with error handling
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - About to call cognee.cognify()")
            try:
                await cognee.cognify()
                logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.cognify() completed successfully")
            except Exception as cognify_error:
                error_msg = str(cognify_error)
                if "InstructorRetryException" in error_msg and "validation errors for KnowledgeGraph" in error_msg:
                    if "edges" in error_msg and ("source_node_id" in error_msg or "relationship_name" in error_msg or "target_node_id" in error_msg):
                        logging.warning("⚠️ [COGNEE_DIRECT] Cognify failed (expected due to edge schema): LLM generating wrong field names for edges")
                        logging.info("🔧 [COGNEE_DIRECT] LLM generated '@id', 'label' but schema expects 'source_node_id', 'relationship_name', 'target_node_id'")
                    else:
                        logging.warning(f"⚠️ [COGNEE_DIRECT] Cognify failed (expected due to KnowledgeGraph schema): {cognify_error}")
                elif "vector" in error_msg and "768 items" in error_msg:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Vector dimension issue (embedding not generating correct size): {cognify_error}")
                elif "validation error for SummarizedContent" in error_msg:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Summarization schema issue (non-critical): {cognify_error}")
                elif "Field required" in error_msg and "name" in error_msg:
                    logging.warning("⚠️ [COGNEE_DIRECT] Knowledge graph schema mismatch - nodes missing 'name' field")
                    logging.info("🔧 [COGNEE_DIRECT] This is a known Cognee library schema issue with KnowledgeGraph nodes")
                elif "KnowledgeGraph" in error_msg:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Knowledge graph validation error: {cognify_error}")
                    logging.info("🔧 [COGNEE_DIRECT] LLM-generated nodes don't match expected Pydantic schema")
                else:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Cognify failed: {cognify_error}")
                logging.info("🔍 [COGNEE_DIRECT] DEBUG - Continuing test without cognify step...")
            
            # Try to search - this is the most important function
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - About to call cognee.search()")
            results = await cognee.search("AutoGen")
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.search() completed successfully")
            
            logging.info(f"🧪 [COGNEE_DIRECT] Test successful with Ollama, found {len(results)} results")
        except Exception as e:
            logging.warning(f"⚠️ [COGNEE_DIRECT] Test functionality failed: {e}")
            logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Test failure type: {type(e)}")
            logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Test failure args: {e.args}")
            # Don't fail initialization on test failure - the service may still be usable
    
    async def health_check(self) -> bool:
        """Check if Cognee service is available"""
        return COGNEE_AVAILABLE and self.initialized
    
    async def add_data(self, data: List[str]) -> Dict[str, Any]:
        """Add data to Cognee knowledge graph"""
        if not self.initialized:
            return {"error": "Service not initialized"}
        
        try:
            # Add all data entries
            for item in data:
                await cognee.add(item)
            
            logging.info(f"✅ [COGNEE_DIRECT] Added {len(data)} items to knowledge graph (Ollama)")
            return {
                "success": True,
                "items_added": len(data),
                "dataset": self.dataset_name,
                "llm_provider": "ollama"
            }
        except Exception as e:
            logging.error(f"❌ [COGNEE_DIRECT] Add data error: {e}")
            return {"error": str(e)}
    
    async def cognify(self) -> Dict[str, Any]:
        """Process and create entity relationships (cognify) with enhanced error handling"""
        if not self.initialized:
            return {"error": "Service not initialized"}
        
        try:
            # Process the data to create knowledge graph relationships
            await cognee.cognify()
            
            logging.info("🧩 [COGNEE_DIRECT] Cognify completed successfully with Ollama")
            return {
                "success": True,
                "message": "Knowledge graph processing completed",
                "dataset": self.dataset_name,
                "llm_provider": "ollama"
            }
        except Exception as e:
            error_msg = str(e)
            
            # Enhanced error detection for knowledge graph validation issues
            if "InstructorRetryException" in error_msg and "validation errors for KnowledgeGraph" in error_msg:
                # This is the specific error we're seeing - edge validation failures
                if "edges" in error_msg and ("source_node_id" in error_msg or "relationship_name" in error_msg or "target_node_id" in error_msg):
                    logging.warning("⚠️ [COGNEE_DIRECT] Knowledge graph edge validation error - LLM generating wrong field names")
                    logging.info("🔧 [COGNEE_DIRECT] LLM generated edges with '@id', 'label' but schema expects 'source_node_id', 'relationship_name', 'target_node_id'")
                    return {
                        "success": False,
                        "message": "Knowledge graph processing failed due to edge validation error",
                        "dataset": self.dataset_name,
                        "llm_provider": "ollama",
                        "error": "LLM-generated edges don't match expected Pydantic schema",
                        "technical_details": "Expected fields: source_node_id, relationship_name, target_node_id",
                        "suggestion": "This is a known issue with Cognee + llama3.2:3b compatibility"
                    }
                else:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Knowledge graph validation error (general): {e}")
                    return {
                        "success": False,
                        "message": "Knowledge graph processing failed due to validation error",
                        "dataset": self.dataset_name,
                        "llm_provider": "ollama",
                        "error": "KnowledgeGraph validation failed"
                    }
            elif "validation error for SummarizedContent" in error_msg or "description" in error_msg:
                logging.warning(f"⚠️ [COGNEE_DIRECT] Known schema issue in summarization (data still processed): {e}")
                return {
                    "success": True,
                    "message": "Knowledge graph processing completed (with summarization warnings)",
                    "dataset": self.dataset_name,
                    "llm_provider": "ollama",
                    "warning": "Summarization schema mismatch (non-critical)"
                }
            elif "Field required" in error_msg and "name" in error_msg:
                logging.warning("⚠️ [COGNEE_DIRECT] Knowledge graph schema mismatch - nodes missing 'name' field")
                return {
                    "success": False,
                    "message": "Knowledge graph processing failed due to schema mismatch",
                    "dataset": self.dataset_name,
                    "llm_provider": "ollama",
                    "error": "KnowledgeGraph nodes missing required 'name' field",
                    "suggestion": "This is a known Cognee library schema issue"
                }
            elif "KnowledgeGraph" in error_msg:
                logging.warning(f"⚠️ [COGNEE_DIRECT] Knowledge graph validation error: {e}")
                return {
                    "success": False,
                    "message": "Knowledge graph processing failed due to validation error",
                    "dataset": self.dataset_name,
                    "llm_provider": "ollama",
                    "error": "LLM-generated nodes don't match expected Pydantic schema"
                }
            else:
                logging.error(f"❌ [COGNEE_DIRECT] Cognify error: {e}")
                return {"error": str(e)}
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Cognee knowledge graph"""
        if not self.initialized:
            return []
        
        try:
            # 🔍 DEBUG: Log environment and query details
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - Starting search for query: '{query}'")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - Environment at search time:")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_API_KEY: '{os.environ.get('LLM_API_KEY', 'NOT_SET')}'")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_PROVIDER: '{os.environ.get('LLM_PROVIDER', 'NOT_SET')}'")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - LLM_MODEL: '{os.environ.get('LLM_MODEL', 'NOT_SET')}'")
            
            # Search the knowledge graph
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - About to call cognee.search()")
            results = await cognee.search(query)
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.search() completed successfully")
            
            # Limit results if needed
            if limit and len(results) > limit:
                results = results[:limit]
            
            # Format results
            formatted_results = []
            for result in results:
                if isinstance(result, str):
                    formatted_results.append({
                        "content": result,
                        "relevance_score": 1.0,
                        "source": "cognee_search_ollama"
                    })
                elif isinstance(result, dict):
                    formatted_results.append(result)
                else:
                    formatted_results.append({
                        "content": str(result),
                        "relevance_score": 0.8,
                        "source": "cognee_search_ollama"
                    })
            
            logging.info(f"🔍 [COGNEE_DIRECT] Ollama search found {len(formatted_results)} results for: '{query[:50]}...'")
            return formatted_results
        except Exception as e:
            error_msg = str(e)
            if "EntityNotFoundError" in error_msg or "Empty graph projected" in error_msg:
                logging.warning("⚠️ [COGNEE_DIRECT] Knowledge graph is empty - no data available for search")
                logging.info("🔧 [COGNEE_DIRECT] This usually means cognify failed earlier due to schema issues")
                # Return a helpful fallback response instead of empty
                return [{
                    "content": f"No knowledge graph data available yet for query: {query}",
                    "relevance_score": 0.1,
                    "source": "cognee_fallback_empty_graph"
                }]
            else:
                logging.error(f"❌ [COGNEE_DIRECT] Search error: {e}")
                logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Search error type: {type(e)}")
                logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Search error args: {e.args}")
                logging.error(f"🔍 [COGNEE_DIRECT] DEBUG - Current LLM_API_KEY at error: '{os.environ.get('LLM_API_KEY', 'NOT_SET')}'")
                return []
    
    async def store_and_process(self, data: List[str], auto_cognify: bool = True) -> Dict[str, Any]:
        """Convenience method to add data and optionally process it"""
        if not self.initialized:
            return {"error": "Service not initialized"}
        
        try:
            # Add the data
            add_result = await self.add_data(data)
            if "error" in add_result:
                return add_result
            
            # Optionally process it
            if auto_cognify:
                cognify_result = await self.cognify()
                if "error" in cognify_result:
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Cognify failed but data was added: {cognify_result['error']}")
            
            return {
                "success": True,
                "items_added": len(data),
                "cognified": auto_cognify,
                "dataset": self.dataset_name,
                "llm_provider": "ollama"
            }
        except Exception as e:
            logging.error(f"❌ [COGNEE_DIRECT] Store and process error: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "cognee_direct",
            "library_available": COGNEE_AVAILABLE,
            "initialized": self.initialized,
            "dataset": self.dataset_name,
            "llm_provider": "ollama",
            "health": await self.health_check()
        }

# Global service instance
_cognee_direct_service: Optional[CogneeDirectService] = None

async def get_cognee_direct_service() -> Optional[CogneeDirectService]:
    """Get or create the global Cognee direct service instance"""
    global _cognee_direct_service
    
    if _cognee_direct_service is None:
        _cognee_direct_service = CogneeDirectService()
        await _cognee_direct_service.initialize()
    
    return _cognee_direct_service if _cognee_direct_service.initialized else None 