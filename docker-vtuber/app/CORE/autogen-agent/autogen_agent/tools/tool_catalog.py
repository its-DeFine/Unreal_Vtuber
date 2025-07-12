"""Tool Catalog

Central registry of all available tools organized by team and category.
This provides a unified interface for discovering and accessing tools.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ToolCatalog:
    """Central catalog of all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._initialize_catalog()
    
    def _initialize_catalog(self):
        """Initialize the tool catalog with all available tools"""
        
        # Trader Team Tools
        self._tools["trader"] = {
            "market_data_tool": {
                "module": "autogen_agent.tools.trader.market_data_tool",
                "class": "MarketDataTool",
                "description": "Real-time and historical market data access",
                "category": "data"
            },
            "portfolio_tool": {
                "module": "autogen_agent.tools.trader.portfolio_tool",
                "class": "PortfolioTool",
                "description": "Portfolio management and tracking",
                "category": "management"
            },
            "risk_calculator_tool": {
                "module": "autogen_agent.tools.trader.risk_calculator_tool",
                "class": "RiskCalculatorTool",
                "description": "Risk assessment and management",
                "category": "analysis"
            },
            "technical_analysis_tool": {
                "module": "autogen_agent.tools.trader.technical_analysis_tool",
                "class": "TechnicalAnalysisTool",
                "description": "Technical indicators and chart analysis",
                "category": "analysis"
            },
            "trading_tool": {
                "module": "autogen_agent.tools.trader.trading_tool",
                "class": "TradingTool",
                "description": "Trade execution and order management",
                "category": "execution"
            }
        }
        
        # Streamer Team Tools
        self._tools["streamer"] = {
            "analytics_tool": {
                "module": "autogen_agent.tools.streamer.analytics_tool",
                "function": "run",
                "description": "Stream performance analytics and insights",
                "category": "analysis"
            },
            "community_tool": {
                "module": "autogen_agent.tools.streamer.community_tool",
                "function": "run",
                "description": "Community engagement and management",
                "category": "social"
            },
            "social_media_tool": {
                "module": "autogen_agent.tools.streamer.social_media_tool",
                "function": "run",
                "description": "Social media integration and posting",
                "category": "social"
            },
            "streaming_tool": {
                "module": "autogen_agent.tools.streamer.streaming_tool",
                "function": "run",
                "description": "Stream control and management",
                "category": "control"
            }
        }
        
        # Teacher Team Tools
        self._tools["teacher"] = {
            "assessment_tool": {
                "module": "autogen_agent.tools.teacher.assessment_tool",
                "function": "run",
                "description": "Student assessment and grading",
                "category": "evaluation"
            },
            "curriculum_tool": {
                "module": "autogen_agent.tools.teacher.curriculum_tool",
                "function": "run",
                "description": "Course planning and curriculum management",
                "category": "planning"
            },
            "educational_content_tool": {
                "module": "autogen_agent.tools.teacher.educational_content_tool",
                "function": "run",
                "description": "Educational content creation and resources",
                "category": "content"
            },
            "learning_tool": {
                "module": "autogen_agent.tools.teacher.learning_tool",
                "function": "run",
                "description": "Personalized learning support and adaptation",
                "category": "support"
            }
        }
        
        # Common/Shared Tools
        self._tools["common"] = {
            # System Tools
            "scb_operations_tool": {
                "module": "autogen_agent.tools.system.scb_operations_tool",
                "description": "SCB (State Context Bridge) operations",
                "category": "system"
            },
            # Removed goal management tools - using simplified system
            "stimuli_action_executor": {
                "module": "autogen_agent.tools.system.stimuli_action_executor",
                "description": "Execute stimuli-based actions",
                "category": "system"
            },
            
            # Analysis Tools
            "semantic_graph_query_tool": {
                "module": "autogen_agent.tools.analysis.semantic_graph_query_tool",
                "description": "Query and analyze semantic knowledge graphs",
                "category": "analysis"
            },
            "weather_api_tool": {
                "module": "autogen_agent.tools.analysis.weather_api_tool",
                "description": "Weather data and forecasting",
                "category": "data"
            },
            
            # Control Tools
            "cognitive_vtuber_tool": {
                "module": "autogen_agent.tools.control.cognitive_vtuber_tool",
                "description": "Cognitive VTuber control and interaction",
                "category": "control"
            },
            "advanced_vtuber_control": {
                "module": "autogen_agent.tools.control.advanced_vtuber_control",
                "description": "Advanced VTuber animation and control",
                "category": "control"
            },
            
            # Character Tools
            "admin_character_tool": {
                "module": "autogen_agent.tools.character.admin_character_tool",
                "description": "Character administration and management",
                "category": "admin"
            }
        }
    
    def get_tools_for_team(self, team_name: str) -> Dict[str, Any]:
        """Get all tools available for a specific team
        
        Args:
            team_name: Name of the team (trader, streamer, teacher)
            
        Returns:
            Dictionary of team-specific tools plus common tools
        """
        team_tools = self._tools.get(team_name, {}).copy()
        common_tools = self._tools.get("common", {}).copy()
        
        # Merge team-specific and common tools
        all_tools = {**team_tools, **common_tools}
        return all_tools
    
    def get_tool_info(self, tool_name: str, team_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool
        
        Args:
            tool_name: Name of the tool
            team_name: Optional team name to search in
            
        Returns:
            Tool information or None if not found
        """
        if team_name:
            team_tools = self.get_tools_for_team(team_name)
            return team_tools.get(tool_name)
        
        # Search across all teams
        for team, tools in self._tools.items():
            if tool_name in tools:
                return tools[tool_name]
        
        return None
    
    def get_tools_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get all tools in a specific category across all teams
        
        Args:
            category: Tool category (e.g., 'analysis', 'control', 'data')
            
        Returns:
            Dictionary of tools organized by team
        """
        categorized_tools = {}
        
        for team, tools in self._tools.items():
            team_category_tools = {
                name: info for name, info in tools.items()
                if info.get("category") == category
            }
            if team_category_tools:
                categorized_tools[team] = team_category_tools
        
        return categorized_tools
    
    def list_all_tools(self) -> Dict[str, List[str]]:
        """List all available tools organized by team
        
        Returns:
            Dictionary with team names as keys and tool names as values
        """
        return {
            team: list(tools.keys())
            for team, tools in self._tools.items()
        }
    
    def get_tool_count(self) -> Dict[str, int]:
        """Get count of tools per team
        
        Returns:
            Dictionary with team names and tool counts
        """
        return {
            team: len(tools)
            for team, tools in self._tools.items()
        }


# Singleton instance
_catalog_instance = None


def get_tool_catalog() -> ToolCatalog:
    """Get the global tool catalog instance"""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = ToolCatalog()
    return _catalog_instance


# Convenience functions
def discover_team_tools(team_name: str) -> Dict[str, Any]:
    """Discover all tools available for a team"""
    catalog = get_tool_catalog()
    return catalog.get_tools_for_team(team_name)


def find_tool(tool_name: str, team_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find a specific tool by name"""
    catalog = get_tool_catalog()
    return catalog.get_tool_info(tool_name, team_name)


def list_tools_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """List all tools in a specific category"""
    catalog = get_tool_catalog()
    return catalog.get_tools_by_category(category)