"""
EMERGENCY OVERRIDE: Simplified GraphFlow Decision Matrix

This module provides a drastically simplified decision matrix that bypasses 
the complex rule system and provides reliable, keyword-based routing.

CRITICAL FIXES:
1. Force speech-related requests to AVATAR_AND_ANALYSIS (S1)
2. Force analysis requests to ANALYSIS_ONLY (S2) 
3. Force admin requests to AVATAR_AND_ANALYSIS (S1+S2)
4. Remove all complex rule evaluation that causes false negatives
"""

import os
import re
import logging
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

# Import models we need
try:
    from ..src.models.decisions import ProcessingDecision
    from ..src.models.stimuli import AnalyzedStimuli
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.models.decisions import ProcessingDecision
    from src.models.stimuli import AnalyzedStimuli


class EmergencyDecisionOverride:
    """
    Emergency override that bypasses all complex decision matrix logic.
    
    This provides simple, reliable routing based on content keywords
    to ensure the system actually works.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("emergency_override")
        
        # Simple keyword mappings for reliable routing
        self.speech_keywords = [
            "speak", "speech", "say", "voice", "audio", "sound", "tell", "announce",
            "read", "tts", "avatar", "hello", "hi", "respond", "test_message"
        ]
        
        self.analysis_keywords = [
            "analyze", "analysis", "think", "process", "examine", "evaluate", 
            "cognitive", "reasoning", "understand", "interpret"
        ]
        
        self.admin_keywords = [
            "admin", "create", "character", "system", "config", "setup", "manage",
            "control", "override", "test_user", "emergency"
        ]
        
        # S2-specific character types that MUST go to S2 only
        self.s2_only_characters = [
            "trader", "trader_character", "financial_expert", "market_analyst"
        ]
        
        # S2 team types
        self.s2_team_types = [
            "trader", "streamer", "teacher", "researcher", "analyst"
        ]
        
        # Environment variable overrides for forced routing
        self.force_speech_routing = os.getenv("FORCE_SPEECH_ROUTING", "true").lower() == "true"
        self.force_s1_for_interaction = os.getenv("FORCE_S1_INTERACTION", "true").lower() == "true"
        self.fallback_decision = os.getenv("FALLBACK_DECISION", "AVATAR_AND_ANALYSIS")
        
        self.logger.info("Emergency decision override initialized")
        self.logger.info(f"Force speech routing: {self.force_speech_routing}")
        self.logger.info(f"Force S1 for interactions: {self.force_s1_for_interaction}")
        self.logger.info(f"Fallback decision: {self.fallback_decision}")
    
    def evaluate(self, context: Dict[str, Any]) -> ProcessingDecision:
        """
        Simple, reliable decision evaluation bypassing complex rules.
        
        ROUTING LOGIC:
        1. S2-specific characters (trader) → S2 ONLY (ANALYSIS_ONLY)
        2. Explicit S2 routing metadata → S2 ONLY (ANALYSIS_ONLY)
        3. Speech keywords → S1 (AVATAR_AND_ANALYSIS)
        4. Analysis keywords → S2 (ANALYSIS_ONLY)  
        5. Admin keywords → S1+S2 (AVATAR_AND_ANALYSIS)
        6. USER_INTERACTION → S1 (AVATAR_AND_ANALYSIS)
        7. Fallback → S1 (AVATAR_AND_ANALYSIS) for reliability
        """
        try:
            # Extract content for keyword matching
            content = ""
            metadata = {}
            if isinstance(context, dict):
                content = context.get('content', '')
                metadata = context.get('metadata', {})
                if metadata:
                    metadata_content = metadata.get('content', '')
                    content = f"{content} {metadata_content}".strip()
                category = context.get('category', '').upper()
                priority = context.get('priority', '').lower()
                source = context.get('source', '').lower()
            else:
                # Handle AnalyzedStimuli object
                content = getattr(context, 'content', '')
                if hasattr(context, 'metadata') and context.metadata:
                    metadata = context.metadata
                    metadata_content = metadata.get('content', '')
                    content = f"{content} {metadata_content}".strip()
                category = getattr(context, 'category', '').upper() if hasattr(context, 'category') else ''
                if hasattr(context.category, 'value'):
                    category = context.category.value.upper()
                priority = getattr(context, 'priority', '').lower() if hasattr(context, 'priority') else ''
                if hasattr(context.priority, 'value'):
                    priority = context.priority.value.lower()
                source = getattr(context, 'source', '').lower()
            
            content_lower = content.lower()
            
            self.logger.info(f"Emergency override evaluating: category={category}, content='{content[:100]}...', priority={priority}, source={source}, metadata={metadata}")
            
            # S2-ONLY ROUTING - HIGHEST PRIORITY
            # Check for S2-specific characters (trader, etc.)
            character_id = metadata.get('character_id', '').lower()
            character_type = metadata.get('character_type', '').lower()
            team_type = metadata.get('team_type', '').lower()
            processing_mode = metadata.get('processing_mode', '').lower()
            
            # Force S2-only routing for specific characters
            if any(s2_char in character_id for s2_char in self.s2_only_characters):
                self.logger.info(f"S2-only character detected: {character_id} → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            if any(s2_char in character_type for s2_char in self.s2_only_characters):
                self.logger.info(f"S2-only character type detected: {character_type} → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            # Check team type
            if team_type in self.s2_team_types and team_type == "trader":
                self.logger.info(f"S2 trader team detected: {team_type} → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            # Check explicit S2 routing metadata
            if processing_mode == "s2_only":
                self.logger.info("Explicit s2_only processing mode → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            if metadata.get('s2_only') == True or metadata.get('force_s2') == True:
                self.logger.info("S2-only flag detected → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            if metadata.get('target_systems') == ["s2"]:
                self.logger.info("Target systems = [s2] → ANALYSIS_ONLY")
                return ProcessingDecision.ANALYSIS_ONLY
            
            # EMERGENCY RULES - high priority
            if priority in ['emergency', 'critical', 'high']:
                # Check if it's from a trader or S2-specific source
                if "trader" in source or "s2_" in source:
                    self.logger.info("Emergency from S2 source → ANALYSIS_ONLY")
                    return ProcessingDecision.ANALYSIS_ONLY
                self.logger.info("Emergency/high priority detected → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # ADMIN OVERRIDE RULES
            if (category == "DIRECT_ADMIN" or 
                "test_user" in source or 
                "admin" in source or
                any(keyword in content_lower for keyword in self.admin_keywords)):
                self.logger.info("Admin request detected → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # ANALYSIS-ONLY ROUTING - Check this before speech routing
            if any(keyword in content_lower for keyword in self.analysis_keywords):
                # Check if it also has speech keywords (hybrid request)
                # Use word boundary matching for short words like "hi"
                has_speech_keyword = False
                for keyword in self.speech_keywords:
                    if len(keyword) <= 2:  # Short words like "hi" need word boundaries
                        if re.search(rf'\b{keyword}\b', content_lower):
                            has_speech_keyword = True
                            break
                    else:
                        if keyword in content_lower:
                            has_speech_keyword = True
                            break
                
                if has_speech_keyword:
                    self.logger.info("Hybrid analysis+speech request → AVATAR_AND_ANALYSIS")
                    return ProcessingDecision.AVATAR_AND_ANALYSIS
                # Check if it's a user interaction (usually needs avatar)
                elif category == "USER_INTERACTION":
                    self.logger.info("Analysis keywords in user interaction → AVATAR_AND_ANALYSIS")
                    return ProcessingDecision.AVATAR_AND_ANALYSIS
                else:
                    self.logger.info(f"Analysis keywords detected: {[k for k in self.analysis_keywords if k in content_lower]} → ANALYSIS_ONLY")
                    return ProcessingDecision.ANALYSIS_ONLY
            
            # SPEECH ROUTING - Force S1 for any speech-related content
            if (self.force_speech_routing and 
                any(keyword in content_lower for keyword in self.speech_keywords)):
                self.logger.info(f"Speech keywords detected: {[k for k in self.speech_keywords if k in content_lower]} → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # USER INTERACTION OVERRIDE - Force S1 for better UX
            if (category == "USER_INTERACTION" and self.force_s1_for_interaction):
                self.logger.info("User interaction detected with S1 override → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # CONTEXTUAL UPDATES with speech triggers
            if (category == "CONTEXTUAL_UPDATE" and 
                any(keyword in content_lower for keyword in ["hello", "hi", "speak", "respond", "test", "avatar"])):
                self.logger.info("Contextual update with speech trigger → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # FALLBACK DECISION - Default to enabling avatar for reliability
            fallback = getattr(ProcessingDecision, self.fallback_decision, ProcessingDecision.AVATAR_AND_ANALYSIS)
            self.logger.info(f"No specific rules matched, using fallback → {fallback.value}")
            return fallback
            
        except Exception as e:
            self.logger.error(f"Emergency override evaluation failed: {e}")
            # Safe fallback
            return ProcessingDecision.AVATAR_AND_ANALYSIS
    
    def get_target_systems(self, decision: ProcessingDecision) -> list:
        """Get target systems based on decision."""
        if decision == ProcessingDecision.AVATAR_AND_ANALYSIS:
            return ["system1", "system2"]
        elif decision == ProcessingDecision.ANALYSIS_ONLY:
            return ["system2"]
        elif decision == ProcessingDecision.LOG_ONLY:
            return ["log"]
        elif decision == ProcessingDecision.EMERGENCY_OVERRIDE:
            return ["system1", "system2"]
        else:
            return ["system1", "system2"]  # Safe fallback


# Global instance for easy access
EMERGENCY_OVERRIDE = EmergencyDecisionOverride()


def emergency_evaluate(context: Any) -> ProcessingDecision:
    """Simple function interface for emergency evaluation."""
    return EMERGENCY_OVERRIDE.evaluate(context)


# Example usage and testing
if __name__ == "__main__":
    override = EmergencyDecisionOverride()
    
    test_cases = [
        {"content": "hello speak to me", "category": "USER_INTERACTION"},
        {"content": "analyze this data", "category": "CONTEXTUAL_UPDATE"},
        {"content": "admin create character", "category": "DIRECT_ADMIN"},
        {"content": "test message with speech", "source": "test_user"},
        {"content": "emergency help needed", "priority": "emergency"},
        {"content": "market analysis", "metadata": {"character_id": "trader"}},
        {"content": "portfolio update", "metadata": {"character_type": "trader"}},
        {"content": "analyze Bitcoin", "metadata": {"processing_mode": "s2_only"}},
        {"content": "teach me Python", "metadata": {"team_type": "teacher"}},
        {"content": "stream content", "metadata": {"target_systems": ["s2"]}}
    ]
    
    for test in test_cases:
        decision = override.evaluate(test)
        print(f"Test: {test} → {decision.value}")