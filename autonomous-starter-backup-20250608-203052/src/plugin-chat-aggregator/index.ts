import { Plugin } from '@elizaos/core';
import { ChatAggregatorService } from './service';
import { chatActions } from './actions';
import { chatProviders } from './providers';
import { chatEvaluators } from './evaluators';

export const chatAggregatorPlugin: Plugin = {
  name: 'chat-aggregator',
  description: 'Multi-platform chat aggregation and intelligent response system for VTuber interactions',
  actions: chatActions,
  evaluators: chatEvaluators,
  providers: chatProviders,
  services: [ChatAggregatorService],
};

export * from './types';
export * from './service';
export * from './adapters';
export * from './salience'; 