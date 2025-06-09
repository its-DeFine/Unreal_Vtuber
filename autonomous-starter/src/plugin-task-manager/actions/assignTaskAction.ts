import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const assignTaskAction: Action = {
    name: 'ASSIGN_TASK',
    similes: [
        'CREATE_TASK',
        'ASSIGN_WORK',
        'DELEGATE_TASK',
        'TASK_ASSIGNMENT'
    ],
    description: 'Assign a new task or work item for autonomous execution',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "I need you to research VTuber content trends and prepare a report"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "I'll assign this research task and begin working on it autonomously.",
                    action: "ASSIGN_TASK"
                }
            }
        ]
    ] as ActionExample[][],
    
    validate: async (runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
        const content = message.content?.text;
        if (!content) {
            return false;
        }
        
        // Trigger task assignment for work requests
        const isTaskRequest = content.toLowerCase().includes('need you to') ||
                             content.toLowerCase().includes('can you') ||
                             content.toLowerCase().includes('please') ||
                             content.toLowerCase().includes('task') ||
                             content.toLowerCase().includes('work on') ||
                             content.toLowerCase().includes('research') ||
                             content.toLowerCase().includes('analyze');
                             
        return isTaskRequest;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const taskExecutionService = runtime.getService('TaskExecutionService');
            if (!taskExecutionService) {
                console.log('🔧❌ [ASSIGN_TASK] TaskExecutionService not available');
                return false;
            }
            
            const taskDescription = message.content?.text;
            if (!taskDescription) {
                return false;
            }
            
            console.log('🔧📋 [ASSIGN_TASK] Creating new task:', taskDescription.substring(0, 100) + '...');
            
            // Create a new central task
            const task = await taskExecutionService.createCentralTask(
                `Task from user: ${taskDescription}`,
                taskDescription,
                'research' // Default work type, will be determined by LLM
            );
            
            if (task) {
                console.log(`🔧✅ [ASSIGN_TASK] Task created with ID: ${task.id}`);
                
                // Store task info in state
                if (state) {
                    state.assignedTask = task;
                    state.hasActiveTask = true;
                }
                
                return true;
            } else {
                console.log('🔧❌ [ASSIGN_TASK] Failed to create task');
                return false;
            }
            
        } catch (error) {
            console.log('🔧❌ [ASSIGN_TASK] Exception:', error.message);
            return false;
        }
    }
}; 