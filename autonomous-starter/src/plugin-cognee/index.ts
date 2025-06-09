import { Plugin } from '@elizaos/core';
import { CogneeService } from './services/CogneeService';
import { addMemoryAction } from './actions/addMemoryAction';
import { searchMemoryAction } from './actions/searchMemoryAction';
import { cognifyAction } from './actions/cognifyAction';

export const cogneePlugin: Plugin = {
    name: 'COGNEE',
    description: 'Knowledge graph-driven AI memory system providing semantic understanding and multi-hop reasoning',
    services: [CogneeService],
    actions: [
        addMemoryAction,
        searchMemoryAction,
        cognifyAction
    ],
    providers: [],
    evaluators: [],
    routes: [],
    events: {},
    tests: []
};

export default cogneePlugin;

// Re-export for external use
export * from './services/CogneeService';
export * from './types/CogneeTypes'; 