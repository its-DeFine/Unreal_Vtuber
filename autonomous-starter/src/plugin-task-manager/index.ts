import { Plugin } from '@elizaos/core';
import { TaskEvaluationService } from './services/TaskEvaluationService';
import { TaskExecutionService } from './services/TaskExecutionService';
import { assignTaskAction } from './actions/assignTaskAction';
import { evaluateTaskAction } from './actions/evaluateTaskAction';
import { executeWorkAction } from './actions/executeWorkAction';
import { reviewTasksAction } from './actions/reviewTasksAction';

export const taskManagerPlugin: Plugin = {
    name: 'TASK_MANAGER',
    description: 'Advanced task evaluation and execution framework for autonomous work completion',
    services: [TaskEvaluationService, TaskExecutionService],
    actions: [
        assignTaskAction,
        evaluateTaskAction, 
        executeWorkAction,
        reviewTasksAction
    ],
    providers: [],
    evaluators: [],
    routes: [],
    events: {},
    tests: []
};

export default taskManagerPlugin;

// Re-export types for external use
export * from './types/TaskStructure';
export * from './services/TaskEvaluationService';
export * from './services/TaskExecutionService'; 