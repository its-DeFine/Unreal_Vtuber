"""Base Tool Framework

Provides base classes and utilities for tool implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Tool execution status"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class ToolParameter:
    """Defines a tool parameter"""
    name: str
    type: str  # string, integer, boolean, object, array
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API usage"""
        result = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        return result


@dataclass
class ToolResult:
    """Standardized tool execution result"""
    status: ToolStatus
    data: Any
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            "status": self.status.value,
            "data": self.data
        }
        if self.message:
            result["message"] = self.message
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ToolExecutionContext:
    """Context passed to tool execution"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    character_name: Optional[str] = None
    team_name: Optional[str] = None
    agent_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: List[ToolParameter],
        version: str = "1.0.0"
    ):
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters
        self.version = version
        self._logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolResult:
        """Execute the tool with given parameters
        
        Args:
            params: Tool parameters
            context: Execution context
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters against tool definition
        
        Returns:
            Error message if validation fails, None if valid
        """
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"
            
            # Check enum values if specified
            if param.name in params and param.enum:
                if params[param.name] not in param.enum:
                    return f"Invalid value for {param.name}. Must be one of: {param.enum}"
        
        return None
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for registration"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        **({"default": param.default} if param.default is not None else {}),
                        **({"enum": param.enum} if param.enum else {})
                    }
                    for param in self.parameters
                },
                "required": [param.name for param in self.parameters if param.required]
            }
        }
    
    async def __call__(
        self,
        params: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolResult:
        """Make tool callable"""
        # Validate parameters
        error = self.validate_params(params)
        if error:
            return ToolResult(
                status=ToolStatus.ERROR,
                data=None,
                message=error
            )
        
        try:
            return await self.execute(params, context)
        except Exception as e:
            self._logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return ToolResult(
                status=ToolStatus.ERROR,
                data=None,
                message=f"Tool execution failed: {str(e)}"
            )


class AsyncFunctionTool(BaseTool):
    """Wrapper for async function-based tools"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        function,
        parameters: List[ToolParameter],
        version: str = "1.0.0"
    ):
        super().__init__(name, description, category, parameters, version)
        self.function = function
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolResult:
        """Execute the wrapped function"""
        try:
            # Add context to params if function expects it
            if context:
                params["_context"] = context
            
            result = await self.function(params)
            
            # Handle different return types
            if isinstance(result, ToolResult):
                return result
            elif isinstance(result, dict) and "status" in result:
                return ToolResult(
                    status=ToolStatus(result["status"]),
                    data=result.get("data"),
                    message=result.get("message"),
                    metadata=result.get("metadata")
                )
            else:
                # Assume success if function returns data
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=result
                )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                data=None,
                message=str(e)
            )