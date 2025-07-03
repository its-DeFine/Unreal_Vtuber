"""
Configuration module for GraphFlow External Stimuli System.

This module provides configuration management and decision matrix functionality.
"""

from .settings import (
    GraphFlowConfig,
    System1Config,
    System2Config,
    ExternalAPIConfig,
    CategorizerConfig,
    AnalyzerConfig,
    RouterConfig,
    ExecutorConfig,
    SecurityConfig,
    ErrorHandlingConfig,
    ContextAnalysisDepth,
    Priority,
    StimuliCategory,
    ProcessingDecision,
    load_config,
    save_config
)

from .decision_matrix import (
    DecisionRule,
    RuleCategory,
    DecisionRulesConfig,
    DECISION_RULES
)

__all__ = [
    # Configuration classes
    'GraphFlowConfig',
    'System1Config',
    'System2Config',
    'ExternalAPIConfig',
    'CategorizerConfig',
    'AnalyzerConfig',
    'RouterConfig',
    'ExecutorConfig',
    'SecurityConfig',
    'ErrorHandlingConfig',
    
    # Enums
    'ContextAnalysisDepth',
    'Priority',
    'StimuliCategory',
    'ProcessingDecision',
    
    # Functions
    'load_config',
    'save_config',
    
    # Decision matrix
    'DecisionRule',
    'RuleCategory',
    'DecisionRulesConfig',
    'DECISION_RULES'
]