#!/usr/bin/env python3
"""Script to populate Cognee knowledge graph with initial data"""

import asyncio
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Add autogen_agent to path
sys.path.insert(0, '/app')

async def populate_cognee():
    try:
        import cognee
        
        # Configure Cognee for Ollama
        os.environ['LLM_PROVIDER'] = 'ollama'
        os.environ['LLM_MODEL'] = 'llama3.2:3b'
        os.environ['LLM_API_KEY'] = 'ollama'
        os.environ['LLM_ENDPOINT'] = 'http://ollama:11434/v1'
        
        # Configure embedding environment variables - CRITICAL for Cognee + Ollama
        os.environ['EMBEDDING_PROVIDER'] = 'ollama'
        os.environ['EMBEDDING_MODEL'] = 'nomic-embed-text:latest'
        os.environ['EMBEDDING_DIMENSIONS'] = '768'
        os.environ['HUGGINGFACE_TOKENIZER'] = 'nomic-ai/nomic-embed-text-v1'
        os.environ['EMBEDDING_API_KEY'] = 'ollama'
        os.environ['EMBEDDING_ENDPOINT'] = 'http://ollama:11434/api/embeddings'
        
        # Use Cognee's native config methods
        cognee.config.set_llm_provider('ollama')
        cognee.config.set_llm_model('llama3.2:3b')
        cognee.config.set_llm_api_key('ollama')
        cognee.config.set_llm_endpoint('http://ollama:11434/v1')
        
        # CRITICAL: Set embedding configuration to use Ollama too
        print('🔧 Setting embedding config for Ollama...')
        if hasattr(cognee.config, 'set_embedding_provider'):
            cognee.config.set_embedding_provider('ollama')
        if hasattr(cognee.config, 'set_embedding_model'):
            cognee.config.set_embedding_model('nomic-embed-text:latest')
        if hasattr(cognee.config, 'set_embedding_api_key'):
            cognee.config.set_embedding_api_key('ollama')
        if hasattr(cognee.config, 'set_embedding_endpoint'):
            cognee.config.set_embedding_endpoint('http://ollama:11434/api/embeddings')
        
        print('🔍 Adding initial data to Cognee...')
        
        # Add some meaningful data
        data_entries = [
            'AutoGen Cognitive Agent with Darwin-Gödel self-improvement engine successfully operational',
            'Iteration 20 completed with evolution analysis and code optimization strategies',
            'System successfully processes autonomous decision-making with memory consolidation capabilities',
            'Cognee knowledge graph integration with Ollama local LLM fully operational',
            'Evolution cycles trigger every 5 iterations for continuous improvement and learning',
            'Code performance analysis identifies optimization opportunities in main.py and tool_registry.py',
            'Memory consolidation processes show 15% increase in retrieval accuracy',
            'Pattern recognition algorithms evolved with 20% improvement in speed',
            'Adaptive learning algorithms enhance self-improvement and meta-cognition',
            'Strategic planning incorporates real-time feedback for dynamic adjustments'
        ]
        
        for entry in data_entries:
            await cognee.add(entry)
            print(f'✅ Added: {entry[:60]}...')
        
        print('🧩 Running cognify to build knowledge graph...')
        await cognee.cognify()
        print('✅ Cognify completed successfully!')
        
        print('🔍 Testing search...')
        results = await cognee.search('AutoGen evolution')
        print(f'✅ Search successful! Found {len(results)} results')
        
        # Test another search
        results2 = await cognee.search('optimization strategies')
        print(f'✅ Search 2 successful! Found {len(results2)} results')
        
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the async function
    success = asyncio.run(populate_cognee())
    print(f'🎯 Knowledge graph population {"successful" if success else "failed"}') 