"""
Base Tool Framework for S2 AutoGen Agent Tools

Provides the foundational classes and interfaces for all tools in the system.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Tool execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None


@dataclass
class ToolExecutionContext:
    """Context for tool execution"""
    request_id: str
    user_id: Optional[str] = None
    team_type: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass 
class ToolResult:
    """Result from tool execution"""
    success: bool
    status: ToolStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None


class BaseTool(ABC):
    """
    Base class for all tools in the S2 system.
    
    Provides common functionality for parameter validation, execution context,
    error handling, and result formatting.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        timeout: float = 30.0
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.timeout = timeout
        self._parameter_map = {p.name: p for p in parameters}
    
    @abstractmethod
    async def execute(
        self,
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            context: Execution context with request metadata
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate input parameters against tool definition.
        
        Returns:
            Dict of validation errors (empty if valid)
        """
        errors = {}
        
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in parameters:
                errors[param.name] = f"Required parameter '{param.name}' is missing"
        
        # Validate parameter types and constraints
        for param_name, value in parameters.items():
            if param_name not in self._parameter_map:
                errors[param_name] = f"Unknown parameter '{param_name}'"
                continue
                
            param = self._parameter_map[param_name]
            error = self._validate_parameter_value(param, value)
            if error:
                errors[param_name] = error
        
        return errors
    
    def _validate_parameter_value(self, param: ToolParameter, value: Any) -> Optional[str]:
        """Validate a single parameter value"""
        if value is None:
            return None
            
        # Type validation
        if param.type == "string" and not isinstance(value, str):
            return f"Expected string, got {type(value).__name__}"
        elif param.type == "integer" and not isinstance(value, int):
            return f"Expected integer, got {type(value).__name__}"
        elif param.type == "number" and not isinstance(value, (int, float)):
            return f"Expected number, got {type(value).__name__}"
        elif param.type == "boolean" and not isinstance(value, bool):
            return f"Expected boolean, got {type(value).__name__}"
        elif param.type == "array" and not isinstance(value, list):
            return f"Expected array, got {type(value).__name__}"
        elif param.type == "object" and not isinstance(value, dict):
            return f"Expected object, got {type(value).__name__}"
        
        # Enum validation
        if param.enum and value not in param.enum:
            return f"Value must be one of: {param.enum}"
        
        # Range validation for numbers
        if param.type in ["integer", "number"]:
            if param.minimum is not None and value < param.minimum:
                return f"Value must be >= {param.minimum}"
            if param.maximum is not None and value > param.maximum:
                return f"Value must be <= {param.maximum}"
        
        return None
    
    async def execute_with_timeout(
        self,
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """
        Execute tool with timeout and error handling.
        """
        start_time = time.time()
        
        # Extract stimuli_id from context if available
        stimuli_id = getattr(context, 'stimuli_id', 'unknown')
        if hasattr(context, 'metadata') and context.metadata:
            stimuli_id = context.metadata.get('stimuli_id', stimuli_id)
        
        # S2_TOOL_INVOKED timestamp
        tool_start_time = time.time()
        logger.info(f"S2_TOOL_INVOKED {stimuli_id} {self.name} {datetime.fromtimestamp(tool_start_time).isoformat()}")
        
        try:
            # Validate parameters
            validation_errors = self.validate_parameters(kwargs)
            if validation_errors:
                return ToolResult(
                    success=False,
                    status=ToolStatus.FAILED,
                    error_message=f"Parameter validation failed: {validation_errors}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Apply defaults for missing parameters
            for param in self.parameters:
                if param.name not in kwargs and param.default is not None:
                    kwargs[param.name] = param.default
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(context, **kwargs),
                timeout=self.timeout
            )
            
            # Add execution time
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            # S2_TOOL_COMPLETED timestamp
            tool_complete_time = time.time()
            logger.info(f"S2_TOOL_COMPLETED {stimuli_id} {self.name} {datetime.fromtimestamp(tool_complete_time).isoformat()}")
            
            return result
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                status=ToolStatus.TIMEOUT,
                error_message=f"Tool execution timed out after {self.timeout}s",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except asyncio.CancelledError:
            return ToolResult(
                success=False,
                status=ToolStatus.CANCELLED,
                error_message="Tool execution was cancelled",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.exception(f"Tool {self.name} execution failed")
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAPI-style schema for this tool"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
            if param.minimum is not None:
                prop["minimum"] = param.minimum
            if param.maximum is not None:
                prop["maximum"] = param.maximum
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class AsyncFunctionTool(BaseTool):
    """
    Wrapper to convert async functions into tools.
    
    Useful for simple functions that don't need full tool class implementation.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter],
        func,
        timeout: float = 30.0
    ):
        super().__init__(name, description, parameters, timeout)
        self.func = func
    
    async def execute(
        self,
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """Execute the wrapped function"""
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(context, **kwargs)
            else:
                result = self.func(context, **kwargs)
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result if isinstance(result, dict) else {"result": result}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=str(e)
            )


def create_simple_tool(
    name: str,
    description: str,
    parameters: List[ToolParameter],
    func,
    timeout: float = 30.0
) -> AsyncFunctionTool:
    """Helper function to create simple tools from functions"""
    return AsyncFunctionTool(name, description, parameters, func, timeout)


# Export all public classes and functions
__all__ = [
    "ToolStatus",
    "ToolParameter", 
    "ToolExecutionContext",
    "ToolResult",
    "BaseTool",
    "AsyncFunctionTool",
    "create_simple_tool"
]