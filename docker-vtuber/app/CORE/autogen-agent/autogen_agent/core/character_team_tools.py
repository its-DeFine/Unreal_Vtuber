"""
Character Team Tool Configuration
=================================

Maps character types to their specialized tools without complex team inheritance.
"""

from typing import Dict, List
from .character_team_registry import CharacterType

# Define tool sets for each character type
TEAM_TOOL_MAPPING: Dict[CharacterType, List[str]] = {
    CharacterType.TRADER: [
        "market_data_tool",
        "portfolio_tool", 
        "risk_calculator_tool",
        "technical_analysis_tool",
        "trading_tool",
        "internet_market_tool",  # NEW: Real-time market data from internet
        "financial_news_tool",   # NEW: Financial news from internet
        "scb_operations_tool",
        "semantic_graph_query_tool"  # For Neo4j queries
    ],
    
    CharacterType.STREAMER: [
        "social_media_tool",
        "streaming_tool",
        "analytics_tool",
        "community_tool",
        "trending_topics_tool",     # NEW: Real-time trending topics from internet
        "social_analytics_tool",    # NEW: Social media analytics from internet
        "scb_operations_tool",
        "semantic_graph_query_tool"  # For Neo4j queries
    ],
    
    CharacterType.TEACHER: [
        "educational_content_tool",
        "assessment_tool",
        "learning_tool",
        "curriculum_tool",
        "research_access_tool",     # NEW: Research papers and educational resources from internet
        "educational_search_tool",  # NEW: Educational content search from internet
        "scb_operations_tool", 
        "semantic_graph_query_tool"  # For Neo4j queries
    ],
    
    CharacterType.DEFAULT: [
        # Removed - we don't use default team anymore
        "scb_operations_tool",
        "stimuli_action_executor"
    ]
}

def get_tools_for_character_type(character_type: CharacterType) -> List[str]:
    """Get the list of tools for a specific character type"""
    return TEAM_TOOL_MAPPING.get(character_type, TEAM_TOOL_MAPPING[CharacterType.DEFAULT])