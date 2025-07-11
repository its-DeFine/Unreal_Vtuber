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
            "read", "tts", "avatar", "character", "hello", "hi", "respond", "test_message"
        ]
        
        self.analysis_keywords = [
            "analyze", "analysis", "think", "process", "examine", "evaluate", 
            "cognitive", "reasoning", "understand", "interpret"
        ]
        
        self.admin_keywords = [
            "admin", "create", "character", "system", "config", "setup", "manage",
            "control", "override", "test_user", "emergency"
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
        1. Speech keywords → S1 (AVATAR_AND_ANALYSIS)
        2. Analysis keywords → S2 (ANALYSIS_ONLY)  
        3. Admin keywords → S1+S2 (AVATAR_AND_ANALYSIS)
        4. USER_INTERACTION → S1 (AVATAR_AND_ANALYSIS)
        5. Fallback → S1 (AVATAR_AND_ANALYSIS) for reliability
        """
        try:
            # Extract content for keyword matching
            content = ""
            if isinstance(context, dict):
                content = context.get('content', '')
                if 'metadata' in context:
                    metadata_content = context['metadata'].get('content', '')
                    content = f"{content} {metadata_content}".strip()
                category = context.get('category', '').upper()
                priority = context.get('priority', '').lower()
                source = context.get('source', '').lower()
            else:
                # Handle AnalyzedStimuli object
                content = getattr(context, 'content', '')
                if hasattr(context, 'metadata') and context.metadata:
                    metadata_content = context.metadata.get('content', '')
                    content = f"{content} {metadata_content}".strip()
                category = getattr(context, 'category', '').upper() if hasattr(context, 'category') else ''
                if hasattr(context.category, 'value'):
                    category = context.category.value.upper()
                priority = getattr(context, 'priority', '').lower() if hasattr(context, 'priority') else ''
                if hasattr(context.priority, 'value'):
                    priority = context.priority.value.lower()
                source = getattr(context, 'source', '').lower()
            
            content_lower = content.lower()
            
            self.logger.info(f"Emergency override evaluating: category={category}, content='{content[:100]}...', priority={priority}, source={source}")
            
            # EMERGENCY RULES - highest priority
            if priority in ['emergency', 'critical', 'high']:
                self.logger.info("Emergency/high priority detected → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # ADMIN OVERRIDE RULES
            if (category == "DIRECT_ADMIN" or 
                "test_user" in source or 
                "admin" in source or
                any(keyword in content_lower for keyword in self.admin_keywords)):
                self.logger.info("Admin request detected → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # SPEECH ROUTING - Force S1 for any speech-related content
            if (self.force_speech_routing and 
                any(keyword in content_lower for keyword in self.speech_keywords)):
                self.logger.info(f"Speech keywords detected: {[k for k in self.speech_keywords if k in content_lower]} → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # USER INTERACTION OVERRIDE - Force S1 for better UX
            if (category == "USER_INTERACTION" and self.force_s1_for_interaction):
                self.logger.info("User interaction detected with S1 override → AVATAR_AND_ANALYSIS")
                return ProcessingDecision.AVATAR_AND_ANALYSIS
            
            # ANALYSIS-ONLY ROUTING
            if any(keyword in content_lower for keyword in self.analysis_keywords):
                # Check if it also has speech keywords (hybrid request)
                if any(keyword in content_lower for keyword in self.speech_keywords):
                    self.logger.info("Hybrid analysis+speech request → AVATAR_AND_ANALYSIS")
                    return ProcessingDecision.AVATAR_AND_ANALYSIS
                else:
                    self.logger.info(f"Analysis keywords detected: {[k for k in self.analysis_keywords if k in content_lower]} → ANALYSIS_ONLY")
                    return ProcessingDecision.ANALYSIS_ONLY
            
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
        {"content": "emergency help needed", "priority": "emergency"}
    ]
    
    for test in test_cases:
        decision = override.evaluate(test)
        print(f"Test: {test} → {decision.value}")