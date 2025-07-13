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
                    autogen_func = self._create_simple_wrapper(tool_instance)
                    
                    # Store registered function
                    self.registered_functions[tool_instance.name] = autogen_func
                    
                    logger.info(f"✅ [TOOL_BRIDGE] Registered tool: {tool_instance.name} with schema")
                    
                except Exception as e:
                    logger.error(f"❌ [TOOL_BRIDGE] Failed to register tool {tool_class.__name__}: {e}")
                    
            logger.info(f"🔧 [TOOL_BRIDGE] Successfully registered {len(self.registered_functions)} tools")
            return self.registered_functions
            
        except Exception as e:
            logger.error(f"❌ [TOOL_BRIDGE] Failed to register tools: {e}")
            return {}
    
    def register_tools_with_agents(self, user_proxy, assistant_agents: List):
        """
        Register tools with AutoGen agents using proper decorators and schemas.
        
        Args:
            user_proxy: UserProxyAgent that will execute the tools
            assistant_agents: List of AssistantAgent instances that can call the tools
        """
        logger.info(f"🔧 [TOOL_BRIDGE] Registering {len(self.registered_functions)} tools with agents")
        
        for tool_name, tool_func in self.registered_functions.items():
            try:
                tool_instance = self.tool_instances[tool_name]
                schema = self.tool_schemas[tool_name]
                
                # Register for execution with user proxy
                user_proxy.register_for_execution(name=tool_name)(tool_func)
                
                # Register for LLM with all assistant agents with full schema
                for agent in assistant_agents:
                    # Create a description that includes parameter details
                    param_descriptions = []
                    for param_name, param_schema in schema["parameters"]["properties"].items():
                        param_type = param_schema.get("type", "any")
                        param_desc = param_schema.get("description", "")
                        is_required = param_name in schema["parameters"].get("required", [])
                        req_str = " (required)" if is_required else " (optional)"
                        param_descriptions.append(f"  - {param_name} ({param_type}): {param_desc}{req_str}")
                    
                    full_description = f"{tool_instance.description}\n\nParameters:\n" + "\n".join(param_descriptions)
                    
                    # Register with LLM with full description
                    agent.register_for_llm(
                        name=tool_name,
                        description=full_description
                    )(tool_func)
                
                logger.info(f"✅ [TOOL_BRIDGE] Registered tool '{tool_name}' with all agents")
                
            except Exception as e:
                logger.error(f"❌ [TOOL_BRIDGE] Failed to register tool {tool_name}: {e}")
    
    def _create_simple_wrapper(self, tool_instance: BaseTool) -> Callable:
        """
        Create a simple wrapper function for the tool that AutoGen can call.
        """
        async def tool_wrapper(**kwargs) -> str:
            """AutoGen tool wrapper"""
            
            # Generate unique stimuli ID for logging
            stimuli_id = kwargs.pop('stimuli_id', f"tool_{uuid.uuid4().hex[:8]}")
            
            # Log tool invocation
            logger.info(f"🔧 [TOOL_BRIDGE] S2_TOOL_INVOKED: {tool_instance.name} ({stimuli_id})")
            logger.debug(f"🔧 [TOOL_BRIDGE] Tool parameters: {kwargs}")
            
            try:
                # Create execution context
                context = ToolExecutionContext(
                    request_id=stimuli_id,
                    team_type=self.team_type,
                    metadata={"autogen_call": True, "stimuli_id": stimuli_id}
                )
                
                # Filter kwargs to only include tool parameters
                tool_params = {}
                for param in tool_instance.parameters:
                    if param.name in kwargs:
                        tool_params[param.name] = kwargs[param.name]
                    elif param.required:
                        # Provide default value for required parameters
                        if param.type == "string":
                            tool_params[param.name] = ""
                        elif param.type == "number":
                            tool_params[param.name] = 0
                        elif param.type == "boolean":
                            tool_params[param.name] = False
                        else:
                            tool_params[param.name] = None
                
                # Execute tool with timeout
                result = await tool_instance.execute_with_timeout(context, **tool_params)
                
                # Log completion
                logger.info(f"✅ [TOOL_BRIDGE] S2_TOOL_COMPLETED: {tool_instance.name} ({stimuli_id})")
                
                # Format result for AutoGen
                if isinstance(result, ToolResult):
                    if result.success:
                        # Return structured result as readable string
                        if result.result:
                            return f"✅ Tool '{tool_instance.name}' completed successfully:\n{self._format_result(result.result)}"
                        else:
                            return f"✅ Tool '{tool_instance.name}' completed successfully"
                    else:
                        return f"❌ Tool '{tool_instance.name}' failed: {result.error_message}"
                else:
                    return str(result)
                    
            except Exception as e:
                logger.error(f"❌ [TOOL_BRIDGE] Tool {tool_instance.name} failed: {e}")
                return f"Tool execution failed: {str(e)}"
        
        # Set function metadata for AutoGen
        tool_wrapper.__name__ = tool_instance.name
        tool_wrapper.__doc__ = f"""
{tool_instance.description}

Example usage:
#assistant to={tool_instance.name}
{self._generate_example_params(tool_instance)}
"""
        
        # Add parameter annotations for AutoGen
        import inspect
        sig_params = []
        
        for param in tool_instance.parameters:
            # Map our parameter types to Python types
            if param.type == "string":
                param_type = str
            elif param.type == "number":
                param_type = float
            elif param.type == "boolean":
                param_type = bool
            else:
                param_type = str
            
            # Create parameter with annotation
            sig_params.append(
                inspect.Parameter(
                    param.name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=param_type,
                    default=param.default if not param.required else inspect.Parameter.empty
                )
            )
        
        # Create new signature
        tool_wrapper.__signature__ = inspect.Signature(
            parameters=sig_params,
            return_annotation=str
        )
        
        return tool_wrapper
    
    def _generate_example_params(self, tool_instance: BaseTool) -> str:
        """Generate example parameters for tool usage"""
        examples = {}
        
        for param in tool_instance.parameters:
            if param.name == "symbol":
                examples[param.name] = "BTCUSDT"
            elif param.name == "topic":
                examples[param.name] = "Introduction to Machine Learning"
            elif param.name == "content_type":
                examples[param.name] = param.default or "general"
            elif param.name == "timeframe":
                examples[param.name] = "1d"
            elif param.type == "string":
                examples[param.name] = param.default or f"example_{param.name}"
            elif param.type == "number":
                examples[param.name] = param.default or 100
            elif param.type == "boolean":
                examples[param.name] = param.default or True
            else:
                examples[param.name] = param.default
        
        # Format as JSON for clarity
        import json
        return json.dumps(examples, indent=2)
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for AutoGen consumption."""
        if isinstance(result, dict):
            # Create a readable summary of the result
            formatted = []
            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    formatted.append(f"{key}: {len(value)} items")
                elif isinstance(value, str) and len(value) > 100:
                    formatted.append(f"{key}: {value[:100]}...")
                else:
                    formatted.append(f"{key}: {value}")
            return "\n".join(formatted)
        else:
            return str(result)
    
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