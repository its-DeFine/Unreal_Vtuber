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
        "scb_operations_tool",
        "goal_management_tools"
    ],
    
    CharacterType.STREAMER: [
        "social_media_tool",
        "streaming_tool",
        "analytics_tool",
        "community_tool",
        "scb_operations_tool",
        "goal_management_tools"
    ],
    
    CharacterType.TEACHER: [
        "educational_content_tool",
        "assessment_tool",
        "learning_tool",
        "curriculum_tool",
        "scb_operations_tool", 
        "goal_management_tools"
    ],
    
    CharacterType.DEFAULT: [
        "core_evolution_tool",
        "goal_management_tools",
        "scb_operations_tool",
        "tool_management",
        "stimuli_action_executor"
    ]
}

def get_tools_for_character_type(character_type: CharacterType) -> List[str]:
    """Get the list of tools for a specific character type"""
    return TEAM_TOOL_MAPPING.get(character_type, TEAM_TOOL_MAPPING[CharacterType.DEFAULT])