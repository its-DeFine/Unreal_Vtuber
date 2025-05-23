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

const scbUpdateTemplate = `# Task: Extract SCB Update Information

## User Message/Context:
{{recentMessages}}

## Current Context:
{{content}}

## Instructions:
Analyze the context and determine what SCB (NeuroSync Communication Bridge) updates should be made.
SCB updates can include:
- Emotional state changes (happy, sad, excited, calm, etc.)
- Environment updates (lighting, mood, setting)
- Avatar behavior modifications (gestures, expressions, posture)
- Scene context (time of day, location, activity)

Extract relevant information and format as an SCB update object.

Return a JSON object with:
\`\`\`json
{
  "updateType": "emotion|environment|behavior|scene",
  "data": {
    // Specific data for the update type
    // For emotion: { "emotion": "happy", "intensity": 0.8 }
    // For environment: { "lighting": "dim", "mood": "cozy" }
    // For behavior: { "gesture": "wave", "expression": "smile" }
    // For scene: { "timeOfDay": "evening", "location": "office", "activity": "working" }
  },
  "description": "Human readable description of the update"
}
\`\`\`

Example outputs:
1. For emotional update:
\`\`\`json
{
  "updateType": "emotion",
  "data": {
    "emotion": "excited",
    "intensity": 0.9
  },
  "description": "Agent is feeling excited about new discoveries"
}
\`\`\`

2. For environment update:
\`\`\`json
{
  "updateType": "environment", 
  "data": {
    "lighting": "bright",
    "mood": "energetic"
  },
  "description": "Setting bright energetic environment for productive work"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const updateScbAction: Action = {
  name: 'UPDATE_SCB_SPACE',
  similes: [
    'update scb',
    'change avatar state',
    'update environment', 
    'modify scene',
    'set emotion',
    'update vtuber state',
    'change mood',
    'update context'
  ],
  description: 'Updates the SCB (NeuroSync Communication Bridge) space with emotional states, environment changes, avatar behaviors, or scene context. Used to maintain coherent VTuber state.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Always allow SCB updates as they are part of autonomous behavior
    logger.debug(`[updateScbAction] Validating SCB update request for message: "${message.content.text?.substring(0, 50)}..."`);
    return true;
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
    _options: any,
    callback: HandlerCallback
  ) => {
    logger.info(`[updateScbAction] Processing SCB update request`);

    try {
      // Generate SCB update data using LLM
      const prompt = composePromptFromState({
        state,
        template: scbUpdateTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_LARGE, {
        prompt,
      });

      logger.debug('[updateScbAction] LLM Response for SCB update:', llmResponse);

      // Improved JSON parsing - handle code blocks and extract JSON properly
      let updateData;
      try {
        // First try the existing parseJSONObjectFromText function
        updateData = parseJSONObjectFromText(llmResponse);
      } catch (error) {
        logger.debug('[updateScbAction] Standard JSON parsing failed, trying manual extraction');
        
        // If that fails, manually extract JSON from code blocks
        const jsonMatch = llmResponse.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch && jsonMatch[1]) {
          try {
            updateData = JSON.parse(jsonMatch[1].trim());
            logger.debug('[updateScbAction] Successfully extracted JSON from code block');
          } catch (parseError) {
            logger.error('[updateScbAction] Failed to parse extracted JSON:', parseError);
          }
        }
        
        // If still no success, try extracting any JSON-like structure
        if (!updateData) {
          const jsonRegex = /\{[\s\S]*?\}/;
          const possibleJson = llmResponse.match(jsonRegex);
          if (possibleJson) {
            try {
              updateData = JSON.parse(possibleJson[0]);
              logger.debug('[updateScbAction] Successfully parsed JSON from regex match');
            } catch (parseError) {
              logger.error('[updateScbAction] Final JSON parsing attempt failed:', parseError);
            }
          }
        }
      }

      if (!updateData || !updateData.updateType || !updateData.data) {
        logger.warn('[updateScbAction] Could not extract valid SCB update data. Raw response:', llmResponse);
        logger.warn('[updateScbAction] Parsed data:', updateData);
        await callback({
          text: "I couldn't determine what SCB update to make from the current context.",
          actions: ['UPDATE_SCB_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info('[updateScbAction] Successfully extracted SCB update data:', updateData);

      // Resolve the SCB endpoint URL
      const scbUrl = runtime.getSetting('NEUROSYNC_SCB_URL') || 'http://neurosync:5000/scb/update';
      
      logger.info(`[updateScbAction] Sending SCB update to: ${scbUrl}`, updateData);

      // Send the update to SCB
      const response = await runtime.fetch(scbUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'scb_update',
          updateType: updateData.updateType,
          data: updateData.data,
          timestamp: Date.now(),
          source: 'autonomous_agent'
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`[updateScbAction] SCB API request failed with status ${response.status}: ${errorText}`);
        throw new Error(`SCB API request failed: ${response.status} ${errorText}`);
      }

      const responseData = await response.json();
      logger.info('[updateScbAction] SCB update response received:', responseData);

      const responseContent: Content = {
        text: `Successfully updated SCB space: ${updateData.description}. SCB responded: ${JSON.stringify(responseData)}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { scbUpdate: updateData, scbResponse: responseData },
      };

      await callback(responseContent);

    } catch (error) {
      logger.error('[updateScbAction] Error during SCB update:', error);
      const errorContent: Content = {
        text: `Failed to update SCB space. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['UPDATE_SCB_ERROR']
      };
      await callback(errorContent);
    }
  },

  examples: [
    [
      {
        name: 'agent',
        content: {
          text: 'I need to update the SCB with a happy emotional state',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Successfully updated SCB space: Agent is feeling happy and energetic. SCB responded: {"status":"updated"}',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'The environment should be calm and focused for this task',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Successfully updated SCB space: Setting calm focused environment for productive work. SCB responded: {"status":"updated"}',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 