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

Choose the appropriate SCB endpoint and update type:

**SCB EVENT (/scb/event)**: For emotional and environmental state changes
- Emotional state changes (happy, sad, excited, calm, curious, etc.)
- Environment updates (lighting, mood, setting, atmosphere)
- Scene context (time of day, location, activity)

**SCB DIRECTIVE (/scb/directive)**: For direct behavior commands and actions
- Avatar behavior modifications (gestures, expressions, posture)
- Specific actions (wave, nod, point, dance)
- Direct commands (look at camera, change pose, interact)

Return a JSON object with:
\`\`\`json
{
  "endpointType": "event|directive",
  "updateType": "emotion|environment|behavior|scene|action|command",
  "data": {
    // Specific data for the update type
    // For emotion: { "emotion": "happy", "intensity": 0.8 }
    // For environment: { "lighting": "dim", "mood": "cozy" }
    // For behavior: { "gesture": "wave", "expression": "smile" }
    // For action: { "action": "wave", "target": "audience" }
  },
  "description": "Human readable description of the update"
}
\`\`\`

Examples:

1. Emotional update (SCB EVENT):
\`\`\`json
{
  "endpointType": "event",
  "updateType": "emotion",
  "data": {
    "emotion": "excited",
    "intensity": 0.9
  },
  "description": "Agent is feeling excited about new discoveries"
}
\`\`\`

2. Behavior directive (SCB DIRECTIVE):
\`\`\`json
{
  "endpointType": "directive", 
  "updateType": "behavior",
  "data": {
    "gesture": "wave",
    "expression": "smile",
    "duration": 3
  },
  "description": "Wave and smile at the audience"
}
\`\`\`

3. Environment update (SCB EVENT):
\`\`\`json
{
  "endpointType": "event",
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
      
      // Method 1: Extract from ```json code blocks (most reliable)
      const jsonMatch = llmResponse.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch && jsonMatch[1]) {
        try {
          const cleanJson = jsonMatch[1].trim();
          updateData = JSON.parse(cleanJson);
          logger.info('[updateScbAction] ✅ SUCCESS: Extracted JSON from ```json``` code block');
        } catch (parseError) {
          logger.error('[updateScbAction] Failed to parse JSON from code block:', parseError);
        }
      }
      
      // Method 2: Try parseJSONObjectFromText as fallback
      if (!updateData) {
        try {
          updateData = parseJSONObjectFromText(llmResponse);
          if (updateData) {
            logger.info('[updateScbAction] ✅ SUCCESS: parseJSONObjectFromText worked');
          }
        } catch (error) {
          logger.debug('[updateScbAction] parseJSONObjectFromText failed:', error);
        }
      }
      
      // Method 3: Direct JSON parsing if response looks like pure JSON
      if (!updateData && llmResponse.trim().startsWith('{')) {
        try {
          updateData = JSON.parse(llmResponse.trim());
          logger.info('[updateScbAction] ✅ SUCCESS: Direct JSON parsing worked');
        } catch (error) {
          logger.debug('[updateScbAction] Direct JSON parsing failed:', error);
        }
      }

      // Validate the extracted data
      if (!updateData || !updateData.endpointType || !updateData.updateType || !updateData.data) {
        logger.error('[updateScbAction] ❌ JSON PARSING FAILED - Raw LLM response:', llmResponse);
        logger.error('[updateScbAction] Extracted data:', updateData);
        
        await callback({
          text: "I couldn't determine what SCB update to make from the current context. The LLM response format was invalid.",
          actions: ['UPDATE_SCB_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info('[updateScbAction] ✅ SUCCESSFULLY EXTRACTED SCB UPDATE DATA:', JSON.stringify(updateData, null, 2));

      // Determine the correct SCB endpoint based on agent selection
      const baseUrl = runtime.getSetting('NEUROSYNC_BASE_URL') || 'http://neurosync:5000';
      let scbUrl;
      
      if (updateData.endpointType === 'directive') {
        scbUrl = `${baseUrl}/scb/directive`;
      } else {
        scbUrl = `${baseUrl}/scb/event`; // default to event
      }
      
      const scbPayload = {
        type: updateData.endpointType === 'directive' ? 'scb_directive' : 'scb_event',
        actor: 'autonomous_agent',
        source: 'autoliza_controller',
        text: `Autonomous Agent SCB ${updateData.endpointType.toUpperCase()}: ${updateData.description}`,
        timestamp: Date.now(),
        metadata: {
          endpointType: updateData.endpointType,
          updateType: updateData.updateType,
          data: updateData.data,
          description: updateData.description,
          agent_iteration: 'auto',
          system_component: 'scb_manager'
        }
      };
      
      logger.info(`[updateScbAction] 🎯 SENDING SCB ${updateData.endpointType.toUpperCase()} to: ${scbUrl}`);
      logger.info(`[updateScbAction] SCB Payload:`, JSON.stringify(scbPayload, null, 2));

      // Send the update to SCB
      const response = await runtime.fetch(scbUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scbPayload),
      });

      logger.info(`[updateScbAction] SCB API Response Status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`[updateScbAction] ❌ SCB API FAILED - Status: ${response.status}, Error: ${errorText}`);
        throw new Error(`SCB API request failed: ${response.status} ${errorText}`);
      }

      const responseData = await response.json();
      logger.info(`[updateScbAction] ✅ SCB RESPONSE RECEIVED:`, JSON.stringify(responseData, null, 2));

      const responseContent: Content = {
        text: `Successfully updated SCB space: ${updateData.description}. SCB responded: ${JSON.stringify(responseData)}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { scbUpdate: updateData, scbResponse: responseData },
      };

      logger.info(`[updateScbAction] 📤 CALLBACK RESPONSE:`, JSON.stringify({
        text: responseContent.text,
        actions: responseContent.actions,
        values: responseContent.values
      }, null, 2));

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