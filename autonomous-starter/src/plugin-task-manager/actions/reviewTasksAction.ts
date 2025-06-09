import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const reviewTasksAction: Action = {
    name: 'REVIEW_TASKS',
    similes: [
        'CHECK_TASKS',
        'TASK_STATUS',
        'WORK_REVIEW',
        'PROGRESS_CHECK'
    ],
    description: 'Review current tasks and their status',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "What tasks are you currently working on?"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "Let me review my current tasks and provide a status update.",
                    action: "REVIEW_TASKS"
                }
            }
        ]
    ] as ActionExample[][],
    
    validate: async (runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
        const content = message.content?.text;
        if (!content) {
            return false;
        }
        
        // Trigger task review for status requests
        const isReviewRequest = content.toLowerCase().includes('tasks') ||
                               content.toLowerCase().includes('working on') ||
                               content.toLowerCase().includes('status') ||
                               content.toLowerCase().includes('progress') ||
                               content.toLowerCase().includes('what are you') ||
                               content.toLowerCase().includes('current work');
                               
        return isReviewRequest;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const taskExecutionService = runtime.getService('TaskExecutionService');
            const taskEvaluationService = runtime.getService('TaskEvaluationService');
            
            if (!taskExecutionService || !taskEvaluationService) {
                console.log('📋❌ [REVIEW_TASKS] Task services not available');
                return false;
            }
            
            console.log('📋📊 [REVIEW_TASKS] Reviewing current tasks and status...');
            
            // Get active tasks (this would require implementing a task storage system)
            // For now, we'll get evaluation history as a proxy for task activity
            const evaluationHistory = await taskEvaluationService.getTaskEvaluationHistory();
            const averageScore = await taskEvaluationService.getAverageTaskScore();
            
            if (evaluationHistory.length > 0) {
                console.log(`📋✅ [REVIEW_TASKS] Found ${evaluationHistory.length} completed tasks`);
                console.log(`📋⭐ [REVIEW_TASKS] Average quality score: ${averageScore}/10`);
                
                // Store task review results in state
                if (state) {
                    state.taskReview = {
                        completedTasks: evaluationHistory.length,
                        averageScore: averageScore,
                        recentEvaluations: evaluationHistory.slice(0, 3) // Last 3 evaluations
                    };
                    state.hasTaskReview = true;
                }
                
                return true;
            } else {
                console.log('📋💡 [REVIEW_TASKS] No task history found');
                if (state) {
                    state.hasTaskReview = false;
                }
                return false;
            }
            
        } catch (error) {
            console.log('📋❌ [REVIEW_TASKS] Exception:', error.message);
            return false;
        }
    }
}; 