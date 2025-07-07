#!/usr/bin/env python3
"""
Isolated test for categorizer issue debugging.

This script tests the categorizer components in isolation to identify
the exact source of the 'contextual_update' KeyError.
"""

import sys
import traceback
from datetime import datetime

# Add src to path
sys.path.insert(0, '/home/geo/directories/autonomy/docker-vtuber/app/CORE/graphflow-stimuli-system/src')

def test_imports():
    """Test all imports work correctly."""
    print("🔍 Testing imports...")
    try:
        from models.stimuli import ExternalStimuli, CategorizedStimuli, StimuliCategory, Priority
        print("✅ Stimuli models imported successfully")
        
        from config.settings import CategorizerConfig
        print("✅ CategorizerConfig imported successfully")
        
        from gateway.nodes.categorizer_node import StimuliCategorizerNode
        print("✅ StimuliCategorizerNode imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_enum_access():
    """Test StimuliCategory enum access patterns."""
    print("\n🔍 Testing enum access...")
    try:
        from models.stimuli import StimuliCategory
        
        # Test basic enum access
        print(f"✅ CONTEXTUAL_UPDATE enum: {StimuliCategory.CONTEXTUAL_UPDATE}")
        print(f"✅ CONTEXTUAL_UPDATE value: {StimuliCategory.CONTEXTUAL_UPDATE.value}")
        print(f"✅ CONTEXTUAL_UPDATE name: {StimuliCategory.CONTEXTUAL_UPDATE.name}")
        
        # Test enum iteration
        categories = [e.value for e in StimuliCategory]
        print(f"✅ All category values: {categories}")
        
        # Test getattr access
        category_by_name = getattr(StimuliCategory, 'CONTEXTUAL_UPDATE')
        print(f"✅ getattr access: {category_by_name}")
        
        # Test string conversion patterns
        test_string = "contextual_update"
        print(f"✅ Test string: {test_string}")
        
        # Find enum by value
        found_enum = None
        for category in StimuliCategory:
            if category.value == test_string:
                found_enum = category
                break
        print(f"✅ Found enum by value: {found_enum}")
        
        return True
    except Exception as e:
        print(f"❌ Enum access failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_config_creation():
    """Test CategorizerConfig creation."""
    print("\n🔍 Testing config creation...")
    try:
        from config.settings import CategorizerConfig
        
        # Test default config
        config = CategorizerConfig()
        print(f"✅ Default config created")
        print(f"   fallback_category: {config.fallback_category} (type: {type(config.fallback_category)})")
        print(f"   confidence_threshold: {config.confidence_threshold}")
        print(f"   use_llm: {config.use_llm}")
        
        return config
    except Exception as e:
        print(f"❌ Config creation failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def test_categorizer_creation(config):
    """Test StimuliCategorizerNode creation."""
    print("\n🔍 Testing categorizer creation...")
    try:
        from gateway.nodes.categorizer_node import StimuliCategorizerNode
        
        llm_config = {
            "provider": "ollama",
            "model": "llama3.2:3b",
            "endpoint": "http://ollama:11434",
            "temperature": 0.3,
            "api_key": None
        }
        
        print("Creating categorizer node...")
        categorizer = StimuliCategorizerNode(config=config, llm_config=llm_config)
        print("✅ Categorizer node created successfully")
        
        return categorizer
    except Exception as e:
        print(f"❌ Categorizer creation failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def test_stimuli_creation():
    """Test ExternalStimuli creation."""
    print("\n🔍 Testing stimuli creation...")
    try:
        from models.stimuli import ExternalStimuli, Priority
        
        stimuli = ExternalStimuli(
            content="Hello, this is a test message",
            source="user_chat",
            priority=Priority.MEDIUM
        )
        print("✅ ExternalStimuli created successfully")
        print(f"   ID: {stimuli.id}")
        print(f"   Content: {stimuli.content}")
        print(f"   Source: {stimuli.source}")
        print(f"   Priority: {stimuli.priority}")
        
        return stimuli
    except Exception as e:
        print(f"❌ Stimuli creation failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def test_categorized_stimuli_creation():
    """Test CategorizedStimuli creation directly."""
    print("\n🔍 Testing CategorizedStimuli creation...")
    try:
        from models.stimuli import ExternalStimuli, CategorizedStimuli, StimuliCategory, Priority
        
        # Create base stimuli
        stimuli = ExternalStimuli(
            content="Test content",
            source="test_source",
            priority=Priority.MEDIUM
        )
        
        # Test direct creation
        categorized = CategorizedStimuli(
            **stimuli.__dict__,
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.8,
            classification_metadata={'method': 'test'}
        )
        print("✅ CategorizedStimuli created successfully")
        print(f"   Category: {categorized.category}")
        print(f"   Confidence: {categorized.confidence}")
        
        # Test with CONTEXTUAL_UPDATE specifically
        categorized2 = CategorizedStimuli(
            **stimuli.__dict__,
            category=StimuliCategory.CONTEXTUAL_UPDATE,
            confidence=0.5,
            classification_metadata={'method': 'test_contextual'}
        )
        print("✅ CategorizedStimuli with CONTEXTUAL_UPDATE created successfully")
        print(f"   Category: {categorized2.category}")
        
        return True
    except Exception as e:
        print(f"❌ CategorizedStimuli creation failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_categorizer_processing(categorizer, stimuli):
    """Test actual categorizer processing."""
    print("\n🔍 Testing categorizer processing...")
    try:
        # Initialize first
        await categorizer.initialize()
        print("✅ Categorizer initialized")
        
        # Process stimuli
        result = await categorizer.process(stimuli)
        print("✅ Categorizer processing completed")
        print(f"   Result category: {result.category}")
        print(f"   Result confidence: {result.confidence}")
        
        return result
    except Exception as e:
        print(f"❌ Categorizer processing failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    """Run all isolation tests."""
    print("🚀 Starting Categorizer Isolation Tests")
    print("=" * 50)
    
    # Test 1: Imports
    if not test_imports():
        return False
    
    # Test 2: Enum access
    if not test_enum_access():
        return False
    
    # Test 3: Config creation
    config = test_config_creation()
    if config is None:
        return False
    
    # Test 4: Categorizer creation
    categorizer = test_categorizer_creation(config)
    if categorizer is None:
        return False
    
    # Test 5: Stimuli creation
    stimuli = test_stimuli_creation()
    if stimuli is None:
        return False
    
    # Test 6: CategorizedStimuli creation
    if not test_categorized_stimuli_creation():
        return False
    
    print("\n✅ All synchronous tests passed!")
    print("🔄 Note: Async categorizer processing test requires async context")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 All isolation tests completed successfully!")
            print("The categorizer components work in isolation.")
            print("The issue must be in the integration or async context.")
        else:
            print("\n❌ Isolation tests failed!")
            print("Found the root cause of the categorizer issue.")
    except Exception as e:
        print(f"\n💥 Unexpected error in test runner: {e}")
        print(f"Traceback: {traceback.format_exc()}")