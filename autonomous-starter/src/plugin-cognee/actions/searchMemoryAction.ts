import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const searchMemoryAction: Action = {
    name: 'SEARCH_MEMORY',
    similes: [
        'FIND_KNOWLEDGE',
        'RECALL_INFORMATION',
        'QUERY_MEMORY',
        'KNOWLEDGE_SEARCH'
    ],
    description: 'Search the Cognee knowledge graph for relevant information',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "What do you know about VTuber streaming optimization?"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "Let me search my knowledge graph for information about VTuber streaming optimization.",
                    action: "SEARCH_MEMORY"
                }
            }
        ]
    ] as ActionExample[][],
    
    validate: async (runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
        const cogneeUrl = runtime.getSetting('COGNEE_URL');
        if (!cogneeUrl) {
            return false;
        }
        
        const content = message.content?.text;
        if (!content) {
            return false;
        }
        
        // Trigger search for questions or information requests
        const isQuery = content.includes('?') ||
                       content.toLowerCase().includes('what') ||
                       content.toLowerCase().includes('how') ||
                       content.toLowerCase().includes('why') ||
                       content.toLowerCase().includes('tell me') ||
                       content.toLowerCase().includes('know about');
                       
        return isQuery;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const cogneeService = runtime.getService('COGNEE');
            if (!cogneeService) {
                console.log('🧠❌ [SEARCH_MEMORY] CogneeService not available');
                return false;
            }
            
            const query = message.content?.text;
            if (!query) {
                return false;
            }
            
            console.log('🧠🔍 [SEARCH_MEMORY] Searching knowledge graph for:', query);
            
            const searchResults = await cogneeService.search(query, 5);
            
            if (searchResults.success && searchResults.results.length > 0) {
                console.log(`🧠✅ [SEARCH_MEMORY] Found ${searchResults.results.length} relevant results`);
                
                // Store search results in state for use by other actions
                if (state) {
                    state.cogneeSearchResults = searchResults.results;
                    state.hasRelevantMemories = true;
                }
                
                return true;
            } else {
                console.log('🧠💡 [SEARCH_MEMORY] No relevant memories found');
                if (state) {
                    state.hasRelevantMemories = false;
                }
                return false;
            }
            
        } catch (error) {
            console.log('🧠❌ [SEARCH_MEMORY] Exception:', error.message);
            return false;
        }
    }
}; 