"""
Base tool framework for AutoGen agents.

Provides the foundation for creating tools that agents can use to interact
with external systems and perform specialized tasks.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import json

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value"""
        if self.required and value is None:
            return False
        
        if self.enum and value not in self.enum:
            return False
            
        return True


@dataclass 
class ToolExecutionContext:
    """Context information for tool execution"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    team_type: Optional[str] = None
    character_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Tool execution result"""
    success: bool
    status: ToolStatus
    result: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "status": self.status.value,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Base class for all tools used by AutoGen agents.
    
    Tools provide specific capabilities to agents like market data access,
    educational content generation, or streaming analytics.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[ToolParameter] = None,
        timeout: float = 30.0
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.timeout = timeout
        self._execution_count = 0
        self._last_execution = None
    
    @abstractmethod
    async def execute(
        self,
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def get_function_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for this tool"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.enum:
                prop["enum"] = param.enum
            
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
    
    def validate_parameters(self, **kwargs) -> List[str]:
        """Validate provided parameters, return list of errors"""
        errors = []
        
        for param in self.parameters:
            value = kwargs.get(param.name)
            
            if not param.validate(value):
                if param.required and value is None:
                    errors.append(f"Missing required parameter: {param.name}")
                elif param.enum and value not in param.enum:
                    errors.append(f"Invalid value for {param.name}: {value}. Must be one of {param.enum}")
        
        return errors
    
    async def safe_execute(
        self,
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """Execute tool with error handling and timeout"""
        start_time = datetime.now()
        
        try:
            # Validate parameters
            validation_errors = self.validate_parameters(**kwargs)
            if validation_errors:
                return ToolResult(
                    success=False,
                    status=ToolStatus.FAILED,
                    error_message=f"Parameter validation failed: {'; '.join(validation_errors)}",
                    execution_time=0.0
                )
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(context, **kwargs),
                timeout=self.timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            self._execution_count += 1
            self._last_execution = datetime.now()
            
            logger.debug(f"Tool {self.name} executed successfully in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool {self.name} timed out after {execution_time:.2f}s")
            return ToolResult(
                success=False,
                status=ToolStatus.TIMEOUT,
                error_message=f"Tool execution timed out after {self.timeout}s",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool {self.name} failed: {e}")
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
            "timeout": self.timeout
        }


class AsyncFunctionTool(BaseTool):
    """
    Tool wrapper for async functions.
    
    Allows easy conversion of async functions into tools that can be used
    by AutoGen agents.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: List[ToolParameter] = None,
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
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result
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
    func: Callable,
    parameters: List[ToolParameter] = None,
    timeout: float = 30.0
) -> AsyncFunctionTool:
    """Create a simple tool from a function"""
    return AsyncFunctionTool(
        name=name,
        description=description,
        func=func,
        parameters=parameters,
        timeout=timeout
    )