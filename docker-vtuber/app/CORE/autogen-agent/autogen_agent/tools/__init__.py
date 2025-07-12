"""Tools module - organized by category

Available tool categories:
- system: Core system tools (SCB, stimuli action executor, management)
- analysis: Data analysis and semantic graph query tools

Team-specific tools:
- trader: Trading and financial analysis tools  
- streamer: Streaming and community management tools
- teacher: Educational and assessment tools
"""

# Keep backward compatibility for semantic graph tool
from .analysis.semantic_graph_query_tool import (
    get_semantic_query_tool,
    query_semantic_graph,
    SemanticGraphQueryTool
)

# Import tool catalog for discovery
from .tool_catalog import (
    get_tool_catalog,
    discover_team_tools,
    find_tool,
    list_tools_by_category
)

# Import base tool framework
from .base_tool import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolExecutionContext,
    ToolStatus,
    AsyncFunctionTool
)

__all__ = [
    # Semantic graph tools (backward compatibility)
    "get_semantic_query_tool",
    "query_semantic_graph", 
    "SemanticGraphQueryTool",
    
    # Tool catalog
    "get_tool_catalog",
    "discover_team_tools",
    "find_tool",
    "list_tools_by_category",
    
    # Base tool framework
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolExecutionContext",
    "ToolStatus",
    "AsyncFunctionTool"
]