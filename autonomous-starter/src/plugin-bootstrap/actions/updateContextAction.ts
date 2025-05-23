import {
  type Action,
  type ActionExample,
  type IAgentRuntime,
  type Memory,
  type State,
  type HandlerCallback,
  type Content,
  logger,
  composePromptFromState,
  ModelType,
  parseJSONObjectFromText,
} from '@elizaos/core';

const contextUpdateTemplate = `# Task: Extract Context Update Information

## Current Context:
{{content}}

## Recent Messages:
{{recentMessages}}

## Instructions:
Analyze the current situation and determine what context updates the agent should make to improve future decision-making.
Context updates can include:
- Learning new facts or insights
- Updating goals or priorities
- Revising understanding of situations
- Remembering important patterns or relationships
- Storing preferences or successful strategies
- Recording outcomes of actions

Extract information that should be added to the agent's context for future reference.

Return a JSON object with:
\`\`\`json
{
  "updateType": "fact|goal|strategy|preference|pattern|outcome",
  "content": "the specific information to remember",
  "importance": "high|medium|low",
  "category": "descriptive category for organization",
  "reasoning": "why this information is important to remember"
}
\`\`\`

Example outputs:
1. For learning a fact:
\`\`\`json
{
  "updateType": "fact",
  "content": "VTuber responds better to specific emotional prompts rather than generic messages",
  "importance": "high",
  "category": "vtuber_interaction",
  "reasoning": "This pattern improves VTuber engagement and response quality"
}
\`\`\`

2. For updating a goal:
\`\`\`json
{
  "updateType": "goal",
  "content": "Maintain regular research on AI developments to stay current",
  "importance": "medium",
  "category": "self_improvement",
  "reasoning": "Staying informed helps make better autonomous decisions"
}
\`\`\`

3. For recording a strategy:
\`\`\`json
{
  "updateType": "strategy",
  "content": "When updating SCB, always include emotional context for better avatar coherence",
  "importance": "high",
  "category": "scb_management",
  "reasoning": "Emotional context makes VTuber behavior more natural and engaging"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const updateContextAction: Action = {
  name: 'UPDATE_CONTEXT',
  similes: [
    'update context',
    'remember this',
    'learn from this',
    'add to memory',
    'store information',
    'update knowledge',
    'record insight',
    'save strategy',
    'remember pattern'
  ],
  description: 'Updates the agent\'s own context by storing important facts, insights, strategies, or patterns for future reference. Used for continuous learning and improvement.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Always allow context updates as they are core to autonomous learning
    logger.debug(`[updateContextAction] Validating context update for message: "${message.content.text?.substring(0, 50)}..."`);
    return true;
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
    _options: any,
    callback: HandlerCallback
  ) => {
    logger.info(`[updateContextAction] Processing context update request`);

    try {
      // Generate context update using LLM
      const prompt = composePromptFromState({
        state,
        template: contextUpdateTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_LARGE, {
        prompt,
      });

      logger.debug('[updateContextAction] LLM Response for context update:', llmResponse);

      const contextData = parseJSONObjectFromText(llmResponse);

      if (!contextData || !contextData.updateType || !contextData.content) {
        logger.warn('[updateContextAction] Could not extract valid context update data', contextData);
        await callback({
          text: "I couldn't determine what context update to make from the current situation.",
          actions: ['UPDATE_CONTEXT_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info(`[updateContextAction] Updating context with ${contextData.updateType}:`, contextData.content);

      // Create different types of memories based on update type
      let memoryTable = 'facts';
      let memoryContent = contextData.content;

      switch (contextData.updateType) {
        case 'goal':
          memoryTable = 'goals';
          break;
        case 'strategy':
          memoryTable = 'strategies';
          break;
        case 'pattern':
          memoryTable = 'patterns';
          break;
        case 'outcome':
          memoryTable = 'outcomes';
          break;
        case 'preference':
          memoryTable = 'preferences';
          break;
        default:
          memoryTable = 'facts';
      }

      // Create the memory with full context
      const contextMemory = {
        content: {
          text: memoryContent,
          type: contextData.updateType,
          importance: contextData.importance,
          category: contextData.category,
          reasoning: contextData.reasoning,
          timestamp: Date.now(),
          source: 'autonomous_context_update'
        },
        entityId: runtime.agentId,
        roomId: message.roomId,
        worldId: message.worldId,
      };

      // Store in appropriate memory table
      try {
        await runtime.createMemory(contextMemory, memoryTable);
        logger.info(`[updateContextAction] Context stored in ${memoryTable} table`);
      } catch (error) {
        // If specialized table doesn't exist, fall back to facts
        logger.warn(`[updateContextAction] Failed to store in ${memoryTable}, using facts table:`, error);
        await runtime.createMemory(contextMemory, 'facts');
      }

      // Also store a summary in the agent's general memory for easy access
      const summaryMemory = {
        content: {
          text: `[CONTEXT UPDATE] ${contextData.updateType.toUpperCase()}: ${contextData.content}`,
          type: 'context_summary',
          category: contextData.category,
          importance: contextData.importance,
        },
        entityId: runtime.agentId,
        roomId: message.roomId,
        worldId: message.worldId,
      };

      await runtime.createMemory(summaryMemory, 'messages');

      const responseContent: Content = {
        text: `Context updated successfully: Added ${contextData.updateType} to ${contextData.category} category. Reasoning: ${contextData.reasoning}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { 
          contextUpdate: contextData,
          memoryTable: memoryTable,
          timestamp: Date.now()
        },
      };

      await callback(responseContent);

      logger.info('[updateContextAction] Context update completed successfully');

    } catch (error) {
      logger.error('[updateContextAction] Error during context update:', error);
      const errorContent: Content = {
        text: `Failed to update context. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['UPDATE_CONTEXT_ERROR']
      };
      await callback(errorContent);
    }
  },

  examples: [
    [
      {
        name: 'agent',
        content: {
          text: 'I need to remember that emotional prompts work better with the VTuber',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated successfully: Added strategy to vtuber_interaction category. Reasoning: This pattern improves VTuber engagement and response quality.',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'I should record this successful research approach for future use',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated successfully: Added strategy to research_methods category. Reasoning: Successful approaches should be remembered for consistent results.',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 