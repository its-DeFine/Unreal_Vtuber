"""
AutoGen Tool Bridge
==================

Converts our existing tool system to AutoGen-compatible functions.
Provides proper registration with AutoGen agents using decorators.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Type, Callable
from datetime import datetime
from functools import wraps
import inspect
import json

from ..tools.base_tool import BaseTool, ToolExecutionContext, ToolResult
from ..tools import get_team_tools, get_tool_catalog

logger = logging.getLogger(__name__)


class AutoGenToolBridge:
    """
    Bridge between our tool system and AutoGen agents.
    Converts our tools into AutoGen-compatible functions with proper registration.
    """
    
    def __init__(self, team_type: str):
        self.team_type = team_type
        self.registered_functions = {}
        self.tool_instances = {}
        self.tool_schemas = {}
        self.autogen_functions = {}
        logger.info(f"🔧 [TOOL_BRIDGE] Initializing bridge for team: {team_type}")
        
    def register_tools(self) -> Dict[str, Callable]:
        """
        Register all team tools with AutoGen.
        Returns dictionary of function name -> callable for AutoGen registration.
        """
        try:
            # Get tools for this team
            team_tools = get_team_tools(self.team_type)
            logger.info(f"🔧 [TOOL_BRIDGE] Found {len(team_tools)} tools for team {self.team_type}")
            
            for tool_class in team_tools:
                try:
                    # Instantiate tool
                    tool_instance = tool_class()
                    self.tool_instances[tool_instance.name] = tool_instance
                    
                    # Get OpenAPI schema from tool
                    schema = tool_instance.get_schema()
                    self.tool_schemas[tool_instance.name] = schema
                    
                    # Create AutoGen-compatible function
                    autogen_func = self._create_autogen_function(tool_instance)
                    
                    # Store registered function
                    self.registered_functions[tool_instance.name] = autogen_func
                    self.autogen_functions[tool_instance.name] = autogen_func
                    
                    logger.info(f"✅ [TOOL_BRIDGE] Registered tool: {tool_instance.name} with schema")
                    
                except Exception as e:
                    logger.error(f"❌ [TOOL_BRIDGE] Failed to register tool {tool_class.__name__}: {e}")
                    
            logger.info(f"🔧 [TOOL_BRIDGE] Successfully registered {len(self.registered_functions)} tools")
            return self.registered_functions
            
        except Exception as e:
            logger.error(f"❌ [TOOL_BRIDGE] Failed to register tools: {e}")
            return {}
    
    def _create_autogen_function(self, tool_instance: BaseTool) -> Callable:
        """
        Create a synchronous function that AutoGen can call directly.
        This follows the AutoGen pattern of using type annotations.
        """
        # Build parameter types (no Annotated, just plain types)
        params = {}
        param_docs = []
        
        for param in tool_instance.parameters:
            # Map tool parameter types to Python types
            if param.type == "string":
                param_type = str
            elif param.type == "number":
                param_type = float
            elif param.type == "integer":
                param_type = int
            elif param.type == "boolean":
                param_type = bool
            else:
                param_type = str  # Default to string for safety
            
            # Store plain type (no Annotated)
            params[param.name] = param_type
            
            # Build docstring
            param_docs.append(f"    {param.name} ({param.type}): {param.description}")
            if param.default is not None:
                param_docs[-1] += f" (default: {param.default})"
        
        # Create the function dynamically
        def autogen_tool_function(**kwargs) -> Dict[str, Any]:
            """Dynamic tool function for AutoGen"""
            # Log tool invocation
            stimuli_id = f"tool_{uuid.uuid4().hex[:8]}"
            logger.info(f"🔧 [TOOL_BRIDGE] S2_TOOL_INVOKED: {tool_instance.name} ({stimuli_id})")
            logger.debug(f"🔧 [TOOL_BRIDGE] Parameters: {kwargs}")
            
            try:
                # Create execution context
                context = ToolExecutionContext(
                    request_id=stimuli_id,
                    team_type=self.team_type,
                    metadata={"autogen_call": True, "stimuli_id": stimuli_id}
                )
                
                # Run async tool - handle existing event loop
                try:
                    # Check if we're already in an async context
                    loop = asyncio.get_running_loop()
                    # We're in an async context, need to use run_until_complete differently
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, tool_instance.execute_with_timeout(context, **kwargs))
                        result = future.result()
                except RuntimeError:
                    # No running loop, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            tool_instance.execute_with_timeout(context, **kwargs)
                        )
                    finally:
                        loop.close()
                
                # Log completion
                logger.info(f"✅ [TOOL_BRIDGE] S2_TOOL_COMPLETED: {tool_instance.name} ({stimuli_id})")
                
                # Return actual data, not formatted string
                if isinstance(result, ToolResult):
                    if result.success and result.result:
                        return result.result
                    else:
                        return {"error": result.error_message or "Tool execution failed"}
                else:
                    return {"result": str(result)}
                    
            except Exception as e:
                logger.error(f"❌ [TOOL_BRIDGE] Tool {tool_instance.name} failed: {e}")
                return {"error": str(e)}
        
        # Set function metadata
        autogen_tool_function.__name__ = tool_instance.name
        autogen_tool_function.__doc__ = f"{tool_instance.description}\n\nParameters:\n" + "\n".join(param_docs)
        
        # Create simple signature with basic type annotations
        sig_params = []
        for param_name, param_type in params.items():
            param_obj = inspect.Parameter(
                param_name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=param_type
            )
            sig_params.append(param_obj)
        
        # Add return annotation
        autogen_tool_function.__signature__ = inspect.Signature(
            parameters=sig_params,
            return_annotation=Dict[str, Any]
        )
        
        return autogen_tool_function
    
    def get_llm_config_tools(self) -> List[Dict[str, Any]]:
        """
        Get tool configurations for LLM config in OpenAI function format.
        This is what gets passed to the LLM to tell it about available functions.
        """
        tools = []
        
        for tool_name, tool_instance in self.tool_instances.items():
            schema = self.tool_schemas[tool_name]
            
            # Convert to OpenAI function format
            tool_config = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_instance.description,
                    "parameters": schema["parameters"]
                }
            }
            tools.append(tool_config)
        
        return tools
    
    def get_function_map(self) -> Dict[str, Callable]:
        """
        Get a mapping of function names to callables for UserProxyAgent execution.
        """
        return self.autogen_functions
    
    def get_tool_count(self) -> int:
        """Get number of registered tools"""
        return len(self.registered_functions)
    
    def get_tool_names(self) -> List[str]:
        """Get list of registered tool names"""
        return list(self.registered_functions.keys())
    
    def get_tool_summary(self) -> Dict[str, Any]:
        """Get summary of registered tools with schemas"""
        return {
            "team_type": self.team_type,
            "tools_count": len(self.tool_instances),
            "tools": {
                name: {
                    "description": tool.description,
                    "parameters": len(tool.parameters),
                    "required_params": [p.name for p in tool.parameters if p.required],
                    "schema": self.tool_schemas.get(name, {})
                }
                for name, tool in self.tool_instances.items()
            }
        } 