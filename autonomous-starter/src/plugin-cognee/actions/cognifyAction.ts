import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const cognifyAction: Action = {
    name: 'COGNIFY',
    similes: [
        'BUILD_KNOWLEDGE_GRAPH',
        'PROCESS_MEMORIES',
        'ORGANIZE_KNOWLEDGE',
        'UPDATE_GRAPH'
    ],
    description: 'Process stored memories to build and update the knowledge graph structure',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "Process all the information I've shared with you"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "I'll process all the information to build a comprehensive knowledge graph.",
                    action: "COGNIFY"
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
        
        // Trigger cognify for processing requests
        const shouldCognify = content.toLowerCase().includes('process') ||
                             content.toLowerCase().includes('organize') ||
                             content.toLowerCase().includes('build graph') ||
                             content.toLowerCase().includes('update knowledge') ||
                             content.toLowerCase().includes('cognify');
                             
        return shouldCognify;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const cogneeService = runtime.getService('COGNEE');
            if (!cogneeService) {
                console.log('🧠❌ [COGNIFY] CogneeService not available');
                return false;
            }
            
            console.log('🧠🧩 [COGNIFY] Starting knowledge graph processing...');
            
            const result = await cogneeService.cognify();
            
            if (result.success) {
                console.log(`🧠✅ [COGNIFY] Knowledge graph updated: ${result.entitiesCreated} entities, ${result.relationshipsCreated} relationships`);
                
                // Store cognify results in state
                if (state) {
                    state.cognifyResults = {
                        entitiesCreated: result.entitiesCreated,
                        relationshipsCreated: result.relationshipsCreated,
                        processingTime: result.processingTime
                    };
                }
                
                return true;
            } else {
                console.log('🧠❌ [COGNIFY] Knowledge graph processing failed:', result.error);
                return false;
            }
            
        } catch (error) {
            console.log('🧠❌ [COGNIFY] Exception:', error.message);
            return false;
        }
    }
}; 