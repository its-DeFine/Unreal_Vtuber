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

## User Message/Context:
{{recentMessages}}

## Current Context:
{{content}}

## Instructions:
Based on the context and conversation, extract information that should be stored for future autonomous decision-making.

Context updates might include:
- Strategic insights about VTuber management
- Successful interaction patterns
- Research findings and facts
- User preferences and feedback
- Performance metrics and observations
- Goals and objectives

Extract the specific information that should be stored and categorize it appropriately.

Return a JSON object with:
\`\`\`json
{
  "updateType": "goal|strategy|pattern|fact|insight|preference",
  "content": "the information to store",
  "category": "vtuber_management|research|user_interaction|performance|general",
  "importance": "high|medium|low",
  "context": "additional context about when/why this is relevant"
}
\`\`\`

Example:
\`\`\`json
{
  "updateType": "pattern",
  "content": "Emotional prompts generate 40% more viewer engagement than factual statements",
  "category": "vtuber_management", 
  "importance": "high",
  "context": "Discovered during VR discussion streams"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const updateContextAction: Action = {
  name: 'UPDATE_CONTEXT',
  similes: [
    'store context',
    'save insight',
    'remember this',
    'update knowledge',
    'store information',
    'save strategy',
    'record pattern',
    'store fact'
  ],
  description: 'Stores strategic knowledge, insights, patterns, or facts in the agent\'s context for future autonomous decision-making. Used to build up the agent\'s knowledge base over time.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Allow context updates when the autonomous agent decides it's needed
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
      // Generate context update using LLM
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
        contextData = parseJSONObjectFromText(llmResponse);
        logger.info('[updateContextAction] Successfully extracted context update from LLM response');
      } catch (parseError) {
        logger.error('[updateContextAction] Failed to parse context update:', parseError);
        
        // Create a fallback context update based on recent context
        contextData = {
          updateType: "insight",
          content: "General autonomous agent learning update",
          category: "general",
          importance: "medium",
          context: "Autonomous learning cycle"
        };
        logger.info('[updateContextAction] Using fallback context update');
      }

      if (!contextData || !contextData.content) {
        logger.error('[updateContextAction] Could not determine context update');
        await callback({
          text: "I couldn't determine what context information to store from the current situation.",
          actions: ['UPDATE_CONTEXT_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info('[updateContextAction] ✅ CONTEXT UPDATE EXTRACTED:', JSON.stringify(contextData, null, 2));

      // Store the context update as a fact in ElizaOS
      const factMemory = {
        content: {
          text: contextData.content,
          type: contextData.updateType,
          category: contextData.category,
          importance: contextData.importance,
          context: contextData.context,
          source: 'autonomous_context_update',
          timestamp: Date.now()
        },
        entityId: runtime.agentId,
        roomId: message.roomId,
        worldId: message.worldId,
      };

      // Store as a fact in ElizaOS
      await runtime.createMemory(factMemory, 'facts');

      logger.info(`[updateContextAction] ✅ CONTEXT STORED: "${contextData.content}" (${contextData.category})`);

      // Also log to tool_usage analytics table if available
      try {
        await runtime.databaseAdapter.db.query(`
          INSERT INTO tool_usage (
            agent_id, tool_name, input_context, output_result, 
            execution_time_ms, success, impact_score
          ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        `, [
          runtime.agentId,
          'context_manager',
          JSON.stringify({ action: 'store', type: contextData.updateType }),
          JSON.stringify({ stored: true, category: contextData.category, importance: contextData.importance }),
          100, // execution time
          true,
          contextData.importance === 'high' ? 0.8 : contextData.importance === 'medium' ? 0.6 : 0.4
        ]);
      } catch (analyticsError) {
        logger.debug('[updateContextAction] Analytics logging failed (table may not exist):', analyticsError);
      }

      const responseContent: Content = {
        text: `Context updated: Stored "${contextData.content}" in ${contextData.category} category with ${contextData.importance} importance. Context: ${contextData.context}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { 
          contextUpdate: contextData,
          stored: true,
          memoryType: 'facts'
        },
      };

      logger.info(`[updateContextAction] 📤 CALLBACK RESPONSE:`, JSON.stringify({
        text: responseContent.text,
        actions: responseContent.actions,
        category: contextData.category
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
          text: 'I should store the insight that emotional prompts work better than factual ones',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated: Stored "Emotional prompts generate better engagement than factual statements" in vtuber_management category with high importance.',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'Need to remember that VR topics generate high viewer interest',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Context updated: Stored "VR topics generate high viewer interest and engagement" in research category with high importance.',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 