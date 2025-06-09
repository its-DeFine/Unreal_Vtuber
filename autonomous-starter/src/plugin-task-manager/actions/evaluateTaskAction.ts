import { Action, IAgentRuntime, Memory, HandlerCallback, type ActionExample } from '@elizaos/core';

export const evaluateTaskAction: Action = {
    name: 'EVALUATE_TASK',
    similes: [
        'ASSESS_WORK',
        'REVIEW_TASK',
        'QUALITY_CHECK',
        'TASK_EVALUATION'
    ],
    description: 'Evaluate completed work and provide quality assessment',
    examples: [
        [
            {
                user: "{{user1}}",
                content: {
                    text: "How did the research task turn out?"
                }
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "Let me evaluate the completed research task and provide a quality assessment.",
                    action: "EVALUATE_TASK"
                }
            }
        ]
    ] as ActionExample[][],
    
    validate: async (runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
        const content = message.content?.text;
        if (!content) {
            return false;
        }
        
        // Trigger evaluation for assessment requests
        const isEvaluationRequest = content.toLowerCase().includes('evaluate') ||
                                   content.toLowerCase().includes('assess') ||
                                   content.toLowerCase().includes('review') ||
                                   content.toLowerCase().includes('quality') ||
                                   content.toLowerCase().includes('how did') ||
                                   content.toLowerCase().includes('turn out');
                                   
        return isEvaluationRequest;
    },
    
    handler: async (runtime: IAgentRuntime, message: Memory, state: any, options: any, callback?: HandlerCallback): Promise<boolean> => {
        try {
            const taskEvaluationService = runtime.getService('TaskEvaluationService');
            if (!taskEvaluationService) {
                console.log('📊❌ [EVALUATE_TASK] TaskEvaluationService not available');
                return false;
            }
            
            console.log('📊⭐ [EVALUATE_TASK] Starting task evaluation...');
            
            // Check if there are recent completed tasks to evaluate
            const recentEvaluations = await taskEvaluationService.getTaskEvaluationHistory();
            
            if (recentEvaluations.length > 0) {
                const latestEvaluation = recentEvaluations[0];
                console.log(`📊✅ [EVALUATE_TASK] Latest evaluation - Overall Score: ${latestEvaluation.overallScore}/10`);
                console.log(`📊📋 [EVALUATE_TASK] Accuracy: ${latestEvaluation.accuracy}, Completeness: ${latestEvaluation.completeness}`);
                
                // Store evaluation results in state
                if (state) {
                    state.taskEvaluation = latestEvaluation;
                    state.hasEvaluationResults = true;
                }
                
                return true;
            } else {
                console.log('📊💡 [EVALUATE_TASK] No completed tasks found for evaluation');
                return false;
            }
            
        } catch (error) {
            console.log('📊❌ [EVALUATE_TASK] Exception:', error.message);
            return false;
        }
    }
}; 