import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const addMemoryAction: Action = {
    name: 'ADD_MEMORY',
    similes: [
        'STORE_MEMORY',
        'SAVE_KNOWLEDGE',
        'REMEMBER_INFORMATION',
        'KNOWLEDGE_STORAGE'
    ],
    description: 'Add information to the Cognee knowledge graph for long-term memory storage',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "I learned something important about VTuber streaming optimization today"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "I'll store this important information in my knowledge graph for future reference.",
                    action: "ADD_MEMORY"
                }
            }
        ]
    ] as ActionExample[][],
    
    validate: async (runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
        const cogneeUrl = runtime.getSetting('COGNEE_URL');
        if (!cogneeUrl) {
            console.log('🧠❌ [COGNEE] COGNEE_URL not configured');
            return false;
        }
        
        // Check if message contains meaningful content to store
        const content = message.content?.text;
        if (!content || content.length < 10) {
            return false;
        }
        
        // Store memories for learning opportunities or important information
        const shouldStore = content.toLowerCase().includes('learn') ||
                          content.toLowerCase().includes('important') ||
                          content.toLowerCase().includes('remember') ||
                          content.toLowerCase().includes('knowledge') ||
                          content.toLowerCase().includes('insight');
                          
        return shouldStore;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const cogneeService = runtime.getService('COGNEE');
            if (!cogneeService) {
                console.log('🧠❌ [ADD_MEMORY] CogneeService not available');
                return false;
            }
            
            const content = message.content?.text;
            if (!content) {
                return false;
            }
            
            console.log('🧠💾 [ADD_MEMORY] Storing memory in knowledge graph:', content.substring(0, 100) + '...');
            
            const result = await cogneeService.addMemory(content);
            
            if (result.success) {
                console.log(`🧠✅ [ADD_MEMORY] Successfully stored memory with ${result.dataPointsAdded} data points`);
                
                // Optionally trigger cognify process for immediate knowledge graph update
                setTimeout(async () => {
                    try {
                        await cogneeService.cognify();
                        console.log('🧠🧩 [ADD_MEMORY] Knowledge graph updated automatically');
                    } catch (error) {
                        console.log('🧠⚠️ [ADD_MEMORY] Auto-cognify failed:', error.message);
                    }
                }, 2000);
                
                return true;
            } else {
                console.log('🧠❌ [ADD_MEMORY] Failed to store memory:', result.error);
                return false;
            }
            
        } catch (error) {
            console.log('🧠❌ [ADD_MEMORY] Exception:', error.message);
            return false;
        }
    }
}; 