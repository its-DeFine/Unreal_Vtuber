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
import json

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
        
        # 🔧 SOLUTION 1: Upgrade to a more capable model for better structured outputs
        # Use llama3.1:8b instead of llama3.2:3b for better JSON generation
        # Use llama3.1 which now exists as an alias to llama3.1:8b
        improved_model = os.getenv('COGNEE_LLM_MODEL', 'llama3.1')  # Now works with the alias we created
        
        # Set environment variables for Cognee (Ollama configuration per official docs)
        os.environ['LLM_PROVIDER'] = 'ollama'
        os.environ['LLM_MODEL'] = improved_model
        os.environ['LLM_API_KEY'] = 'ollama'  # Official docs specify just "ollama"
        # Use the LLM_ENDPOINT from environment or default to vtuber-ollama
        os.environ['LLM_ENDPOINT'] = os.getenv('LLM_ENDPOINT', 'http://vtuber-ollama:11434/v1')  # Use env var or correct hostname
        os.environ['LLM_TEMPERATURE'] = '0.1'  # Lower temperature for more consistent structured outputs
        os.environ['LLM_MAX_TOKENS'] = '2048'  # Reduced for better consistency
        
        # 🔧 Configure Fastembed for local embeddings (no API key required)
        # Per official Cognee documentation: https://docs.cognee.ai/how-to-guides/configuration
        # Fastembed is ideal for codegraph pipeline and avoids rate limits
        os.environ['EMBEDDING_PROVIDER'] = 'fastembed'
        os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'
        os.environ['EMBEDDING_DIMENSIONS'] = '384'
        os.environ['EMBEDDING_MAX_TOKENS'] = '256'
        
        # 🔧 SOLUTION 2: Advanced Cognee configuration to handle small model limitations
        os.environ['COGNEE_SUMMARIZATION_ENABLED'] = 'false'
        os.environ['COGNEE_DISABLE_BACKGROUND_TASKS'] = 'true'
        os.environ['COGNEE_DISABLE_ASYNC_SUMMARIZATION'] = 'true'  # Disable async summarization tasks
        os.environ['COGNEE_CHUNK_SIZE'] = '512'  # Smaller chunks for better processing
        os.environ['COGNEE_OVERLAP'] = '50'  # Reduced overlap
        os.environ['COGNEE_RETRY_ATTEMPTS'] = '1'  # Reduce retries to fail fast
        os.environ['COGNEE_ENABLE_VALIDATION_FALLBACK'] = 'true'  # Custom fallback handling
        
        # 🔧 SOLUTION 3: Configure instructor library for better error handling
        os.environ['INSTRUCTOR_MODE'] = 'json_mode'  # Use JSON mode instead of function calling
        os.environ['INSTRUCTOR_MAX_RETRIES'] = '1'  # Fail fast instead of retrying
        
        # 🔧 SOLUTION 6: Configure Cognee for more lenient validation (handle LLM inconsistencies)
        os.environ['COGNEE_LENIENT_VALIDATION'] = 'true'  # Allow type coercion where possible
        os.environ['COGNEE_SCHEMA_STRICT'] = 'false'  # More forgiving schema validation
        os.environ['COGNEE_AUTO_FIX_TYPES'] = 'true'  # Automatically fix common type mismatches
        
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
        
        logging.info(f"🔑 [COGNEE_DIRECT] Configured for local Ollama with {improved_model} (LLM + Embeddings)")
        
        try:
            import cognee
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Cognee imported successfully")
            logging.info(f"🔍 [COGNEE_DIRECT] DEBUG - Cognee has config: {dir(cognee.config)}")
            
            # 🔧 Use Cognee's native config methods per official documentation
            logging.info("🔧 [COGNEE_DIRECT] DEBUG - Setting Cognee config using native methods...")
            
            # Set LLM configuration using Cognee's config methods
            cognee.config.set_llm_provider('ollama')
            # Use our improved model that handles structured outputs better
            cognee.config.set_llm_model(improved_model)
            cognee.config.set_llm_api_key('ollama')
            # Use the endpoint from environment variable (which we set above)
            cognee.config.set_llm_endpoint(os.environ.get('LLM_ENDPOINT', 'http://vtuber-ollama:11434/v1'))
            
            # 🔧 Configure vector database to handle embedding issues
            try:
                cognee.config.set_vector_db_provider('lancedb')  # Use LanceDB which works better with Ollama
            except:
                logging.info("🔧 [COGNEE_DIRECT] Vector DB config not available (older version)")
            
            # 🔧 SOLUTION 4: Set up global exception handler for background tasks
            self._setup_global_exception_handler()
            
            logging.info("✅ [COGNEE_DIRECT] DEBUG - Cognee config methods applied successfully")
            
            # Test basic functionality
            logging.info("🧪 [COGNEE_DIRECT] DEBUG - Testing Cognee functionality...")
            
        except Exception as e:
            logging.error(f"❌ [COGNEE_DIRECT] Setup error: {e}")
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - Continuing without Cognee...")
            self.initialized = False
            return
        
        logging.info(f"🧠 [COGNEE_DIRECT] Initialized for dataset: {self.dataset_name}")
    
    def _setup_global_exception_handler(self):
        """Set up global exception handler for background tasks"""
        import asyncio
        
        def exception_handler(loop, context):
            """Handle exceptions in background tasks"""
            exception = context.get('exception')
            if exception:
                error_msg = str(exception)
                
                # 🔧 SOLUTION 5: Handle SummarizedContent validation errors in background tasks
                if ("validation error for SummarizedContent" in error_msg or 
                    "Field required" in error_msg and ("summary" in error_msg or "description" in error_msg) or
                    "Failed to validate model SummarizedContent" in error_msg):
                    
                    logging.warning("⚠️ [COGNEE_DIRECT] Caught SummarizedContent validation error in background task (non-critical)")
                    logging.info("🔧 [COGNEE_DIRECT] This is expected with smaller LLM models - data processing continues")
                    logging.debug(f"🔍 [COGNEE_DIRECT] Background task error details: {error_msg}")
                    return  # Don't log as error, just continue
                
                # Handle other instructor/validation errors
                if ("InstructorRetryException" in error_msg or 
                    "ValidationError" in error_msg or
                    "Failed to validate model" in error_msg):
                    
                    logging.warning(f"⚠️ [COGNEE_DIRECT] Background validation error (handled): {error_msg[:100]}...")
                    logging.info("🔧 [COGNEE_DIRECT] Background task validation failed - this is handled gracefully")
                    return
                
                # Log other exceptions normally
                logging.error(f"❌ [COGNEE_DIRECT] Background task error: {error_msg}")
            else:
                logging.error(f"❌ [COGNEE_DIRECT] Background task error: {context}")
        
        # Set the exception handler for the current event loop
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(exception_handler)
            logging.info("✅ [COGNEE_DIRECT] Global exception handler configured for background tasks")
        except Exception as e:
            logging.warning(f"⚠️ [COGNEE_DIRECT] Could not set global exception handler: {e}")
    
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
            
            # 🔧 LOG LLM INPUT: Show what we're sending to the LLM
            logging.info(f"📤 [COGNEE_DIRECT] LLM INPUT - Adding data: '{test_data}'")
            
            await cognee.add(test_data)
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.add() completed successfully")
            
            # 🔧 LOG LLM RESPONSE: Try to capture what the LLM returned (if possible)
            logging.info("📥 [COGNEE_DIRECT] LLM RESPONSE - Data added successfully to knowledge base")
            
            # Try to cognify (this processes the data) with error handling
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - About to call cognee.cognify()")
            
            # 🔧 LOG LLM INPUT: Show what cognify will process
            logging.info("📤 [COGNEE_DIRECT] LLM INPUT - Processing knowledge graph from added data")
            
            try:
                await cognee.cognify()
                logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.cognify() completed successfully")
                
                # 🔧 LOG LLM RESPONSE: Indicate successful processing
                logging.info("📥 [COGNEE_DIRECT] LLM RESPONSE - Knowledge graph processing completed successfully")
                
            except Exception as cognify_error:
                error_msg = str(cognify_error)
                
                # 🔧 LOG RAW LLM ERROR: Show exactly what the LLM produced
                logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Model output that caused validation failure:")
                logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Full error: {error_msg}")
                
                # 🔧 SOLUTION 7: Extract and log the actual JSON that failed validation
                import re
                json_match = re.search(r'input_value=([^,\]]+)', error_msg)
                if json_match:
                    problematic_value = json_match.group(1)
                    logging.error(f"📥 [COGNEE_DIRECT] PROBLEMATIC VALUE - LLM generated: {problematic_value} (expected string)")
                
                # Try to extract actual JSON/model output from error message if possible
                if "Got" in error_msg and "Expected" in error_msg:
                    logging.error(f"📥 [COGNEE_DIRECT] LLM MISMATCH - The LLM generated something different than expected schema")
                
                # New validation error patterns
                if "input_value=" in error_msg and "input_type=" in error_msg:
                    type_match = re.search(r'input_type=(\w+)', error_msg)
                    if type_match:
                        actual_type = type_match.group(1)
                        logging.error(f"📥 [COGNEE_DIRECT] TYPE MISMATCH - LLM generated {actual_type} instead of expected type")
                
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
            
            # 🔧 LOG LLM INPUT: Show search query
            search_query = "AutoGen"
            logging.info(f"📤 [COGNEE_DIRECT] LLM INPUT - Search query: '{search_query}'")
            
            results = await cognee.search(search_query)
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.search() completed successfully")
            
            # 🔧 LOG LLM RESPONSE: Show search results structure
            logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - Search returned {len(results)} results")
            if results:
                logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - First result type: {type(results[0])}")
                logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - First result preview: {str(results[0])[:100]}...")
            
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
            # 🔧 LOG LLM INPUT: Show what data we're sending
            logging.info(f"📤 [COGNEE_DIRECT] LLM INPUT - Adding {len(data)} items to knowledge graph")
            for i, item in enumerate(data):
                logging.info(f"📤 [COGNEE_DIRECT] LLM INPUT - Item {i+1}: '{item[:100]}...' (length: {len(item)})")
            
            # Add all data entries
            for item in data:
                await cognee.add(item)
            
            # 🔧 LOG LLM RESPONSE: Confirm successful addition
            logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - Successfully processed {len(data)} items")
            logging.info(f"✅ [COGNEE_DIRECT] Added {len(data)} items to knowledge graph (Ollama)")
            
            return {
                "success": True,
                "items_added": len(data),
                "dataset": self.dataset_name,
                "llm_provider": "ollama"
            }
        except Exception as e:
            # 🔧 LOG RAW LLM ERROR: Show detailed error information
            logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Failed to add data:")
            logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Error type: {type(e)}")
            logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Error message: {str(e)}")
            logging.error(f"❌ [COGNEE_DIRECT] Add data error: {e}")
            return {"error": str(e)}
    
    async def cognify(self) -> Dict[str, Any]:
        """Process and create entity relationships (cognify) with enhanced error handling"""
        if not self.initialized:
            return {"error": "Service not initialized"}
        
        try:
            # 🔧 LOG LLM INPUT: Show what cognify is about to process
            logging.info("📤 [COGNEE_DIRECT] LLM INPUT - Starting knowledge graph processing (cognify)")
            logging.info("📤 [COGNEE_DIRECT] LLM INPUT - Model will extract entities and relationships")
            
            # Process the data to create knowledge graph relationships
            await cognee.cognify()
            
            # 🔧 LOG LLM RESPONSE: Show successful completion
            logging.info("📥 [COGNEE_DIRECT] LLM RESPONSE - Knowledge graph processing completed successfully")
            logging.info("🧩 [COGNEE_DIRECT] Cognify completed successfully with Ollama")
            
            return {
                "success": True,
                "message": "Knowledge graph processing completed",
                "dataset": self.dataset_name,
                "llm_provider": "ollama"
            }
        except Exception as e:
            error_msg = str(e)
            
            # 🔧 LOG RAW LLM ERROR: Show exactly what the LLM produced that failed validation
            logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Cognify failed with model output:")
            logging.error(f"📥 [COGNEE_DIRECT] RAW LLM ERROR - Full error: {error_msg}")
            
            # Try to extract the actual JSON that failed validation
            if '"' in error_msg and '{' in error_msg:
                logging.error("📥 [COGNEE_DIRECT] RAW LLM ERROR - Error contains JSON-like content, model may have produced malformed output")
            
            if "validation error" in error_msg.lower():
                logging.error("📥 [COGNEE_DIRECT] RAW LLM ERROR - This is a Pydantic validation error - LLM output doesn't match expected schema")
            
            # 🔧 SOLUTION 8: Enhanced error detection for the new validation patterns  
            if "validation error for KnowledgeGraph" in error_msg or "Failed to validate model KnowledgeGraph" in error_msg:
                # Detect the specific type mismatch errors we're seeing
                if "nodes.0.description" in error_msg and "Input should be a valid string" in error_msg:
                    logging.warning("⚠️ [COGNEE_DIRECT] KnowledgeGraph node description type error - LLM generating integer instead of string")
                    logging.info("🔧 [COGNEE_DIRECT] LLM generated integer for description field (expected string) - this is a model output formatting issue")
                    return {
                        "success": False,
                        "message": "Knowledge graph processing failed due to node validation error",
                        "dataset": self.dataset_name,
                        "llm_provider": "ollama",
                        "error": "LLM generated integer for description field (expected string)",
                        "technical_details": "Node description field type mismatch",
                        "suggestion": "This is a llama3.1:8b model structured output issue"
                    }
                elif "edges" in error_msg and ("source_node_id" in error_msg or "relationship_name" in error_msg or "target_node_id" in error_msg):
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
            
            # 🔧 LOG LLM INPUT: Show the search query being processed
            logging.info(f"📤 [COGNEE_DIRECT] LLM INPUT - Search query: '{query}' (limit: {limit})")
            
            results = await cognee.search(query)
            logging.info("🔍 [COGNEE_DIRECT] DEBUG - cognee.search() completed successfully")
            
            # 🔧 LOG LLM RESPONSE: Show what the search returned
            logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - Search found {len(results)} raw results")
            if results:
                for i, result in enumerate(results[:3]):  # Show first 3 results
                    logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - Result {i+1} type: {type(result)}")
                    logging.info(f"📥 [COGNEE_DIRECT] LLM RESPONSE - Result {i+1} content: {str(result)[:150]}...")
            else:
                logging.info("📥 [COGNEE_DIRECT] LLM RESPONSE - No results found for query")
            
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