"""
Unit tests for the StimuliCategorizerNode.

Tests the categorization functionality including LLM integration,
fallback mechanisms, and avatar state notification handling.
"""

import asyncio
import pytest
from datetime import datetime

from src.models.stimuli import (
    ExternalStimuli,
    StimuliCategory,
    Priority
)
from src.gateway.nodes import (
    StimuliCategorizerNode,
    CategorizerConfig
)
from src.utils import MockLLMClient


class TestStimuliCategorizerNode:
    """Test suite for StimuliCategorizerNode."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client for testing."""
        return MockLLMClient()
    
    @pytest.fixture
    def categorizer_config(self):
        """Create a test configuration."""
        return CategorizerConfig(
            confidence_threshold=0.7,
            fallback_category=StimuliCategory.CONTEXTUAL_UPDATE,
            llm_timeout=5.0,
            enable_fallback=True
        )
    
    @pytest.fixture
    def categorizer_node(self, mock_llm_client, categorizer_config):
        """Create a categorizer node for testing."""
        return StimuliCategorizerNode(mock_llm_client, categorizer_config)
    
    @pytest.mark.asyncio
    async def test_categorize_direct_admin(self, categorizer_node):
        """Test categorization of direct admin requests."""
        stimuli = ExternalStimuli(
            content="Set avatar hair color to blue",
            source="admin_console",
            priority=Priority.HIGH
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.DIRECT_ADMIN
        assert result.confidence >= 0.8
        assert result.classification_metadata["classification_method"] == "llm"
    
    @pytest.mark.asyncio
    async def test_categorize_user_interaction(self, categorizer_node):
        """Test categorization of user interactions."""
        stimuli = ExternalStimuli(
            content="Hello, how are you today?",
            source="user_chat"
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.USER_INTERACTION
        assert result.confidence >= 0.9
        assert "greeting" in result.classification_metadata["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_categorize_system_notification(self, categorizer_node):
        """Test categorization of avatar state notifications."""
        stimuli = ExternalStimuli(
            content="Avatar state changed to speaking",
            source="system",
            priority=Priority.HIGH
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.SYSTEM_NOTIFICATION
        assert result.confidence >= 0.95
        assert "avatar state" in result.classification_metadata["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_categorize_emergency(self, categorizer_node):
        """Test categorization of emergency stimuli."""
        stimuli = ExternalStimuli(
            content="URGENT: System overload detected! Immediate action required!",
            source="monitoring",
            priority=Priority.CRITICAL
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.EMERGENCY
        assert result.confidence >= 0.9
        assert result.priority == Priority.CRITICAL
    
    @pytest.mark.asyncio
    async def test_categorize_social_media(self, categorizer_node):
        """Test categorization of social media mentions."""
        stimuli = ExternalStimuli(
            content="@vtuber_ai just posted a new tweet!",
            source="twitter",
            metadata={"platform": "twitter", "type": "mention"}
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.SOCIAL_MEDIA
        assert result.confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self, categorizer_node):
        """Test fallback mechanism when LLM fails."""
        # Make LLM unhealthy
        categorizer_node.llm_client.set_healthy(False)
        
        stimuli = ExternalStimuli(
            content="Update system configuration",
            source="admin_console"
        )
        
        # Should still work with fallback
        result = await categorizer_node.process(stimuli)
        
        assert result.category in [
            StimuliCategory.DIRECT_ADMIN,
            StimuliCategory.CONTEXTUAL_UPDATE
        ]
        assert result.classification_metadata["classification_method"] == "keyword_fallback"
    
    @pytest.mark.asyncio
    async def test_invalid_stimuli_handling(self, categorizer_node):
        """Test handling of invalid stimuli."""
        stimuli = ExternalStimuli(
            content="",  # Empty content
            source="unknown"
        )
        
        result = await categorizer_node.process(stimuli)
        
        assert result.category == StimuliCategory.CONTEXTUAL_UPDATE
        assert result.confidence == 0.0
        assert "error" in result.classification_metadata
    
    @pytest.mark.asyncio
    async def test_confidence_adjustment(self, categorizer_node):
        """Test confidence score adjustment based on features."""
        stimuli = ExternalStimuli(
            content="The avatar is currently idle",
            source="system"
        )
        
        result = await categorizer_node.process(stimuli)
        
        # Should boost confidence for avatar state keywords
        assert result.category == StimuliCategory.SYSTEM_NOTIFICATION
        original_conf = result.classification_metadata["original_confidence"]
        adjusted_conf = result.classification_metadata["adjusted_confidence"]
        assert adjusted_conf > original_conf
    
    @pytest.mark.asyncio
    async def test_health_check(self, categorizer_node):
        """Test health check functionality."""
        # Process some stimuli first
        stimuli = ExternalStimuli(
            content="Test message",
            source="test"
        )
        await categorizer_node.process(stimuli)
        
        health = await categorizer_node.health_check()
        
        assert health["healthy"] is True
        assert health["total_processed"] == 1
        assert "llm_success_rate" in health
        assert health["config"]["confidence_threshold"] == 0.7
    
    @pytest.mark.asyncio
    async def test_high_confidence_required(self, categorizer_node):
        """Test that low confidence results in fallback category."""
        # Create a stimuli that will get low confidence
        stimuli = ExternalStimuli(
            content="random text with no clear category",
            source="unknown"
        )
        
        result = await categorizer_node.process(stimuli)
        
        # Should use fallback due to low confidence
        assert result.category == StimuliCategory.CONTEXTUAL_UPDATE
        assert result.confidence <= 0.7


class TestCategoryClassifier:
    """Test suite for CategoryClassifier helper."""
    
    @pytest.fixture
    def classifier(self):
        """Create a category classifier."""
        from src.gateway.nodes.category_classifier import CategoryClassifier
        return CategoryClassifier()
    
    def test_extract_features_basic(self, classifier):
        """Test basic feature extraction."""
        stimuli = ExternalStimuli(
            content="Hello, how are you?",
            source="user_chat"
        )
        
        features = classifier.extract_features(stimuli)
        
        assert features.content_length == 19
        assert features.word_count == 4
        assert features.has_question is True
        assert features.has_greeting is True
        assert features.has_urgency is False
    
    def test_extract_avatar_state_keywords(self, classifier):
        """Test extraction of avatar state keywords."""
        stimuli = ExternalStimuli(
            content="Avatar started speaking and is now busy",
            source="system"
        )
        
        features = classifier.extract_features(stimuli)
        
        assert "speaking" in features.avatar_state_keywords
        assert "busy" in features.avatar_state_keywords
    
    def test_extract_admin_keywords(self, classifier):
        """Test extraction of admin keywords."""
        stimuli = ExternalStimuli(
            content="Set the avatar configuration and update settings",
            source="admin_console"
        )
        
        features = classifier.extract_features(stimuli)
        
        assert "set" in features.admin_keywords
        assert "update" in features.admin_keywords
        assert features.has_command is True
    
    def test_keyword_fallback_emergency(self, classifier):
        """Test keyword-based fallback for emergency."""
        stimuli = ExternalStimuli(
            content="URGENT: System failure detected!",
            source="monitoring"
        )
        
        features = classifier.extract_features(stimuli)
        result = classifier.keyword_based_fallback(stimuli, features)
        
        assert result.category == StimuliCategory.EMERGENCY
        assert result.confidence >= 0.8
        assert result.method == "keyword_fallback"
    
    def test_keyword_fallback_avatar_state(self, classifier):
        """Test keyword-based fallback for avatar state."""
        stimuli = ExternalStimuli(
            content="Character loaded and avatar is idle",
            source="system"
        )
        
        features = classifier.extract_features(stimuli)
        result = classifier.keyword_based_fallback(stimuli, features)
        
        assert result.category == StimuliCategory.SYSTEM_NOTIFICATION
        assert result.confidence >= 0.9


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])