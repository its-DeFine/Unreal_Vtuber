"""
Tool catalog and discovery system.

Manages available tools for different team types and provides discovery
mechanisms for agents to find appropriate tools.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass

from .base_tool import BaseTool, ToolParameter

logger = logging.getLogger(__name__)


@dataclass
class ToolCatalogEntry:
    """Entry in the tool catalog"""
    tool_class: Type[BaseTool]
    category: str
    team_types: List[str]
    priority: int = 0
    enabled: bool = True


class ToolCatalog:
    """
    Central registry for all available tools.
    
    Provides discovery and instantiation of tools based on team type,
    category, and other criteria.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolCatalogEntry] = {}
        self._initialize_default_tools()
    
    def register_tool(
        self,
        tool_class: Type[BaseTool],
        category: str,
        team_types: List[str],
        priority: int = 0,
        enabled: bool = True
    ):
        """Register a tool in the catalog"""
        tool_name = tool_class.__name__
        
        self._tools[tool_name] = ToolCatalogEntry(
            tool_class=tool_class,
            category=category,
            team_types=team_types,
            priority=priority,
            enabled=enabled
        )
        
        logger.debug(f"Registered tool: {tool_name} for teams: {team_types}")
    
    def get_tools_for_team(self, team_type: str) -> List[Type[BaseTool]]:
        """Get all tools available for a specific team type"""
        tools = []
        
        for entry in self._tools.values():
            if entry.enabled and team_type in entry.team_types:
                tools.append(entry.tool_class)
        
        # Sort by priority (higher priority first)
        tools.sort(key=lambda t: self._tools[t.__name__].priority, reverse=True)
        
        return tools
    
    def get_tools_by_category(self, category: str) -> List[Type[BaseTool]]:
        """Get all tools in a specific category"""
        tools = []
        
        for entry in self._tools.values():
            if entry.enabled and entry.category == category:
                tools.append(entry.tool_class)
        
        return tools
    
    def find_tool(self, tool_name: str) -> Optional[Type[BaseTool]]:
        """Find a specific tool by name"""
        entry = self._tools.get(tool_name)
        return entry.tool_class if entry and entry.enabled else None
    
    def list_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tools with their metadata"""
        result = {}
        
        for tool_name, entry in self._tools.items():
            if entry.enabled:
                result[tool_name] = {
                    "category": entry.category,
                    "team_types": entry.team_types,
                    "priority": entry.priority,
                    "description": getattr(entry.tool_class, "description", "No description")
                }
        
        return result
    
    def _initialize_default_tools(self):
        """Initialize default tools that are always available"""
        # We'll add default tools as we create them
        pass


# Global tool catalog instance
_tool_catalog = ToolCatalog()


def get_tool_catalog() -> ToolCatalog:
    """Get the global tool catalog instance"""
    return _tool_catalog


def discover_team_tools(team_type: str) -> List[Type[BaseTool]]:
    """Discover all tools available for a team type"""
    return _tool_catalog.get_tools_for_team(team_type)


def find_tool(tool_name: str) -> Optional[Type[BaseTool]]:
    """Find a specific tool by name"""
    return _tool_catalog.find_tool(tool_name)


def list_tools_by_category(category: str) -> List[Type[BaseTool]]:
    """List all tools in a category"""
    return _tool_catalog.get_tools_by_category(category)


def register_tool(
    tool_class: Type[BaseTool],
    category: str,
    team_types: List[str],
    priority: int = 0
):
    """Register a tool in the global catalog"""
    _tool_catalog.register_tool(tool_class, category, team_types, priority)


# Auto-register any imported tools
def auto_register_tools():
    """Auto-register tools that have been imported"""
    # This would scan for available tool classes and register them
    # For now, we'll do manual registration as tools are created
    pass