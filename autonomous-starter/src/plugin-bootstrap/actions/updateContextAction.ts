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
} from '@elizaos/core';

const contextUpdateTemplate = `# Task: Extract Context Update Information

## User Message/Context:
{{recentMessages}}

## Current Context:
{{content}}

## Instructions:
Based on the conversation and recent activities, determine what important information should be stored in the agent's context for future reference.

Context updates can include:
- Strategic insights about VTuber management
- Successful interaction patterns
- User preferences and behaviors
- Technical discoveries or improvements
- Performance metrics and outcomes
- Learning from successful/failed actions

Extract the key information that should be preserved for future autonomous decisions.

Return a JSON object with:
\`\`\`json
{
  "type": "strategy|pattern|preference|technical|metric|learning",
  "key": "short descriptive key for this knowledge",
  "value": "the information to store", 
  "context": "why this is important for future decisions",
  "tags": ["tag1", "tag2", "tag3"]
}
\`\`\`

Examples:
1. Strategy insight:
\`\`\`json
{
  "type": "strategy",
  "key": "gaming_discussion_success",
  "value": "Gaming topic discussions generate 40% more VTuber engagement than general topics",
  "context": "Use gaming topics for higher viewer engagement in VTuber prompts",
  "tags": ["gaming", "engagement", "vtuber_strategy"]
}
\`\`\`

2. Technical learning:
\`\`\`json
{
  "type": "technical",
  "key": "scb_update_frequency",
  "value": "SCB updates work best when sent every 2-3 VTuber interactions",
  "context": "Optimal timing for maintaining coherent VTuber emotional state",
  "tags": ["scb", "timing", "optimization"]
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const updateContextAction: Action = {
  name: 'UPDATE_CONTEXT',
  similes: [
    'update context',
    'store knowledge',
    'remember insight',
    'save learning',
    'record pattern',
    'store strategy',
    'update memory'
  ],
  description: 'Updates the agent\'s own context by storing important facts, insights, strategies, or patterns for future reference. Used for continuous learning and improvement.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Allow context updates as part of autonomous learning
    logger.debug(`[updateContextAction] Validating context update request for message: "${message.content.text?.substring(0, 50)}..."`);
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
      // Generate context update data using LLM
      const prompt = composePromptFromState({
        state,
        template: contextUpdateTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_SMALL, {
        prompt,
      });

      logger.debug('[updateContextAction] LLM Response for context update:', llmResponse);

      // Parse context update data
      let contextData;
      try {
        // Try to extract JSON from LLM response
        const jsonMatch = llmResponse.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch && jsonMatch[1]) {
          contextData = JSON.parse(jsonMatch[1].trim());
          logger.info('[updateContextAction] Successfully extracted context data from LLM response');
        } else {
          // Fallback - try to parse the whole response
          const jsonRegex = /\{[\s\S]*?\}/;
          const possibleJson = llmResponse.match(jsonRegex);
          if (possibleJson) {
            contextData = JSON.parse(possibleJson[0]);
            logger.info('[updateContextAction] Successfully parsed context data from regex match');
          }
        }
      } catch (parseError) {
        logger.error('[updateContextAction] Failed to parse context data:', parseError);
        
        // Create a fallback context update
        contextData = {
          type: "learning",
          key: "autonomous_iteration",
          value: "Autonomous agent completed another iteration cycle",
          context: "General operational learning for system improvement",
          tags: ["autonomous", "iteration", "system"]
        };
        logger.info('[updateContextAction] Using fallback context update');
      }

      if (!contextData || !contextData.key || !contextData.value) {
        logger.error('[updateContextAction] Could not determine context update');
        await callback({
          text: "I couldn't determine what context information to store.",
          actions: ['UPDATE_CONTEXT_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info('[updateContextAction] ✅ CONTEXT UPDATE EXTRACTED:', JSON.stringify(contextData, null, 2));

      // Store the context update as a memory
      try {
        const contextMemory = {
          content: {
            text: `Context Update: ${contextData.key} - ${contextData.value}`,
            type: 'context_update',
            contextType: contextData.type,
            key: contextData.key,
            value: contextData.value,
            context: contextData.context,
            tags: contextData.tags || [],
            timestamp: Date.now(),
            source: 'autonomous_agent'
          },
          entityId: runtime.agentId,
          roomId: message.roomId || 'autonomous_context',
          worldId: message.worldId || 'autonomous_world',
        };

        // Store in both memories and facts for different retrieval patterns
        await runtime.createMemory(contextMemory, 'memories');
        await runtime.createMemory(contextMemory, 'facts');

        logger.info(`[updateContextAction] ✅ CONTEXT STORED: ${contextData.key}`);

        // Also update runtime settings if it's a strategic insight
        if (contextData.type === 'strategy' || contextData.type === 'technical') {
          try {
            const settingKey = `context_${contextData.key}`;
            runtime.setSetting(settingKey, JSON.stringify({
              value: contextData.value,
              context: contextData.context,
              timestamp: Date.now(),
              tags: contextData.tags
            }));
            logger.info(`[updateContextAction] Strategic context also stored in settings: ${settingKey}`);
          } catch (settingError) {
            logger.warn('[updateContextAction] Could not store in settings:', settingError);
          }
        }

      } catch (memoryError) {
        logger.error('[updateContextAction] Failed to store context memory:', memoryError);
        throw memoryError;
      }

      const responseContent: Content = {
        text: `Context updated: Stored "${contextData.key}" - ${contextData.value}. This knowledge will improve future autonomous decisions.`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { 
          contextUpdate: contextData,
          stored: true,
          memoryTable: 'memories_and_facts'
        },
      };

      logger.info(`[updateContextAction] 📤 CALLBACK RESPONSE:`, JSON.stringify({
        text: responseContent.text,
        actions: responseContent.actions,
        key: contextData.key,
        type: contextData.type
      }, null, 2));

      await callback(responseContent);

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
          text: 'I learned that gaming topics work well for VTuber engagement',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated: Stored "gaming_engagement_pattern" - Gaming topics generate higher VTuber engagement than general topics. This knowledge will improve future autonomous decisions.',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'SCB updates work better when timed with VTuber interactions',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated: Stored "scb_timing_optimization" - SCB updates are most effective when synchronized with VTuber interaction cycles. This knowledge will improve future autonomous decisions.',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 