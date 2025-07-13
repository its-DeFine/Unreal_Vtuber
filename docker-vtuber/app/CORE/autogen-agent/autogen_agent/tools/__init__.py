"""
S2 AutoGen Agent Tools - Consolidated Structure.

Unified tool system with simplified file organization:
- One file per team (trader_tools.py, teacher_tools.py, streamer_tools.py)
- Common tools shared across teams (common_tools.py)
- Centralized registration and discovery

Available tool categories:
- system: Core system tools and common utilities
- trading: Financial analysis and trading tools
- education: Teaching and assessment tools  
- content: Streaming and community management tools
- analytics: Performance and data analysis tools
"""

import logging
from typing import Dict, List, Type

# Import base tool framework
from .base_tool import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolExecutionContext,
    ToolStatus,
    AsyncFunctionTool
)

# Import tool catalog for discovery
from .tool_catalog import (
    get_tool_catalog,
    discover_team_tools,
    find_tool,
    list_tools_by_category,
    register_tool
)

# Keep backward compatibility for semantic graph tool
try:
    from .analysis.semantic_graph_query_tool import (
        get_semantic_query_tool,
        query_semantic_graph,
        SemanticGraphQueryTool
    )
    SEMANTIC_TOOLS_AVAILABLE = True
except ImportError:
    SEMANTIC_TOOLS_AVAILABLE = False

# Import and register all tool modules
from .common_tools import register_common_tools
from .trader_tools import register_trader_tools
from .teacher_tools import register_teacher_tools
from .streamer_tools import register_streamer_tools

# Import SCB operations tool (self-registers on import)
from .scb_operations_tool import scb_operations_tool

logger = logging.getLogger(__name__)


def initialize_tools():
    """Initialize and register all available tools"""
    try:
        # Register all tool categories
        register_common_tools()
        register_trader_tools()
        register_teacher_tools()
        register_streamer_tools()
        
        logger.info("All tools registered successfully")
        
        # Log summary of registered tools
        catalog = get_tool_catalog()
        all_tools = catalog.list_all_tools()
        
        logger.info(f"Total tools registered: {len(all_tools)}")
        
        # Group by team type for summary
        team_counts = {}
        for tool_name, tool_info in all_tools.items():
            for team in tool_info['team_types']:
                team_counts[team] = team_counts.get(team, 0) + 1
        
        logger.info(f"Tools per team: {team_counts}")
        
    except Exception as e:
        logger.error(f"Failed to initialize tools: {e}")
        raise


def get_team_tools(team_type: str) -> List[Type[BaseTool]]:
    """Get all tools available for a specific team"""
    return discover_team_tools(team_type)


def create_tool_instance(tool_name: str) -> BaseTool:
    """Create an instance of a specific tool"""
    tool_class = find_tool(tool_name)
    if tool_class:
        return tool_class()
    else:
        raise ValueError(f"Tool '{tool_name}' not found")


def get_tools_summary() -> Dict[str, Dict]:
    """Get a summary of all available tools"""
    catalog = get_tool_catalog()
    return catalog.list_all_tools()


def validate_tool_system() -> Dict[str, any]:
    """Validate that the tool system is properly configured"""
    validation_results = {
        "status": "healthy",
        "issues": [],
        "tool_counts": {},
        "team_coverage": {}
    }
    
    try:
        catalog = get_tool_catalog()
        all_tools = catalog.list_all_tools()
        
        # Count tools by category
        category_counts = {}
        for tool_info in all_tools.values():
            category = tool_info['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        validation_results["tool_counts"] = category_counts
        
        # Check team coverage
        expected_teams = ["trader", "teacher", "streamer"]
        for team in expected_teams:
            team_tools = get_team_tools(team)
            validation_results["team_coverage"][team] = len(team_tools)
            
            if len(team_tools) == 0:
                validation_results["issues"].append(f"No tools available for {team} team")
        
        # Check for common tools
        common_tools = list_tools_by_category("system")
        if len(common_tools) == 0:
            validation_results["issues"].append("No common system tools available")
        
        if validation_results["issues"]:
            validation_results["status"] = "issues_found"
        
    except Exception as e:
        validation_results["status"] = "error"
        validation_results["issues"].append(f"Validation failed: {str(e)}")
    
    return validation_results


# Initialize tools when module is imported
initialize_tools()

# Export main interfaces
exports = [
    # Base classes
    "BaseTool",
    "ToolResult", 
    "ToolStatus",
    "ToolParameter",
    "ToolExecutionContext",
    "AsyncFunctionTool",
    
    # Main functions
    "get_team_tools",
    "create_tool_instance",
    "get_tools_summary",
    "validate_tool_system",
    
    # Catalog functions
    "get_tool_catalog",
    "discover_team_tools",
    "find_tool",
    "list_tools_by_category",
    "register_tool"
]

# Add semantic tools if available (backward compatibility)
if SEMANTIC_TOOLS_AVAILABLE:
    exports.extend([
        "get_semantic_query_tool",
        "query_semantic_graph", 
        "SemanticGraphQueryTool"
    ])

__all__ = exports