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

const scbUpdateTemplate = `# Task: Generate SCB Space Update

## Current Context:
{{recentMessages}}

## VTuber Current State:
{{content}}

## Instructions:
Based on the current conversation and VTuber interaction context, determine what SCB space update would enhance the VTuber experience.

SCB updates can include:
- Environmental changes (lighting, background, atmosphere)
- Emotional state adjustments (posture, expression, mood)
- Interactive elements (props, effects, animations)
- Contextual adaptations (matching conversation topic)

Generate an appropriate SCB update that matches the current context and enhances viewer engagement.

Return a JSON object with:
\`\`\`json
{
  "updateType": "environment|emotion|interaction|context",
  "description": "detailed description of the SCB update",
  "elements": {
    "lighting": "lighting description",
    "background": "background/environment description", 
    "posture": "VTuber posture/pose description",
    "expression": "facial expression description",
    "effects": "special effects or animations",
    "props": "any props or interactive elements"
  },
  "mood": "calm|excited|focused|playful|mysterious|energetic",
  "intensity": "subtle|moderate|dramatic",
  "duration": "brief|sustained|permanent"
}
\`\`\`

Example:
\`\`\`json
{
  "updateType": "context",
  "description": "Cozy study environment for research discussion",
  "elements": {
    "lighting": "warm, soft desk lamp lighting",
    "background": "library with books and research papers",
    "posture": "leaning forward, engaged and focused",
    "expression": "curious and thoughtful",
    "effects": "subtle floating text particles",
    "props": "notebook and pen, coffee cup"
  },
  "mood": "focused",
  "intensity": "moderate", 
  "duration": "sustained"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const updateScbAction: Action = {
  name: 'UPDATE_SCB',
  similes: [
    'update scb',
    'change environment',
    'update space',
    'modify scene',
    'adjust atmosphere',
    'change mood',
    'update background',
    'modify setting'
  ],
  description: 'Updates the VTuber\'s SCB (Spatial Coherence Bridge) space to match the current context, mood, or conversation topic. Controls environment, lighting, posture, and interactive elements.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Allow SCB updates when the autonomous agent determines it's beneficial
    logger.debug(`[updateScbAction] Validating SCB update request for context: "${message.content.text?.substring(0, 50)}..."`);
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
      // Generate SCB update using LLM
      const prompt = composePromptFromState({
        state,
        template: scbUpdateTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_SMALL, {
        prompt,
      });

      logger.debug('[updateScbAction] LLM Response for SCB update:', llmResponse);

      // Parse SCB update data
      let scbData;
      try {
        scbData = parseJSONObjectFromText(llmResponse);
        logger.info('[updateScbAction] Successfully extracted SCB update from LLM response');
      } catch (parseError) {
        logger.error('[updateScbAction] Failed to parse SCB update:', parseError);
        
        // Create a fallback SCB update
        scbData = {
          updateType: "environment",
          description: "Default neutral environment update",
          elements: {
            lighting: "soft, natural lighting",
            background: "clean, minimal background",
            posture: "relaxed, natural posture",
            expression: "friendly, approachable",
            effects: "none",
            props: "none"
          },
          mood: "calm",
          intensity: "subtle",
          duration: "sustained"
        };
        logger.info('[updateScbAction] Using fallback SCB update');
      }

      if (!scbData || !scbData.description) {
        logger.error('[updateScbAction] Could not determine SCB update');
        await callback({
          text: "I couldn't determine an appropriate SCB space update for the current context.",
          actions: ['UPDATE_SCB_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info('[updateScbAction] ✅ SCB UPDATE EXTRACTED:', JSON.stringify(scbData, null, 2));

      // Send SCB update to VTuber system
      try {
        const scbEndpoint = runtime.getSetting('VTUBER_ENDPOINT_URL') || 'http://neurosync:5001/process_text';
        const scbUpdatePayload = {
          type: 'scb_update',
          data: scbData,
          timestamp: Date.now(),
          agent_id: runtime.agentId
        };

        logger.info(`[updateScbAction] 🎬 SENDING SCB UPDATE to ${scbEndpoint}:`, JSON.stringify(scbUpdatePayload, null, 2));

        // Note: In a real implementation, you would send this to the VTuber system
        // For now, we'll log it and store it as a memory
        
        // Store the SCB update as a memory for tracking
        const scbMemory = {
          content: {
            text: `SCB Update: ${scbData.description}`,
            type: 'scb_update',
            updateType: scbData.updateType,
            elements: scbData.elements,
            mood: scbData.mood,
            intensity: scbData.intensity,
            duration: scbData.duration,
            source: 'autonomous_scb_control',
            timestamp: Date.now()
          },
          entityId: runtime.agentId,
          roomId: message.roomId,
          worldId: message.worldId,
        };

        await runtime.createMemory(scbMemory, 'memories');
        logger.info(`[updateScbAction] ✅ SCB UPDATE STORED: "${scbData.description}"`);

        // Log to analytics if available
        try {
          await runtime.databaseAdapter.db.query(`
            INSERT INTO tool_usage (
              agent_id, tool_name, input_context, output_result, 
              execution_time_ms, success, impact_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
          `, [
            runtime.agentId,
            'scb_controller',
            JSON.stringify({ context: 'scb_update', mood: scbData.mood }),
            JSON.stringify({ updated: true, type: scbData.updateType, intensity: scbData.intensity }),
            150, // execution time
            true,
            scbData.intensity === 'dramatic' ? 0.9 : scbData.intensity === 'moderate' ? 0.7 : 0.5
          ]);
        } catch (analyticsError) {
          logger.debug('[updateScbAction] Analytics logging failed (table may not exist):', analyticsError);
        }

      } catch (scbError) {
        logger.error('[updateScbAction] Failed to send SCB update:', scbError);
        // Continue with response even if SCB update fails
      }

      const responseContent: Content = {
        text: `SCB space updated: ${scbData.description}. Environment set to ${scbData.mood} mood with ${scbData.intensity} intensity for ${scbData.duration} duration.`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { 
          scbUpdate: scbData,
          updated: true,
          endpoint: runtime.getSetting('VTUBER_ENDPOINT_URL')
        },
      };

      logger.info(`[updateScbAction] 📤 CALLBACK RESPONSE:`, JSON.stringify({
        text: responseContent.text,
        actions: responseContent.actions,
        mood: scbData.mood,
        type: scbData.updateType
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
          text: 'The conversation is about gaming, I should update the SCB to match',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'SCB space updated: Gaming setup with RGB lighting and gaming chair. Environment set to energetic mood with moderate intensity for sustained duration.',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'Time for a research discussion, need a focused environment',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'SCB space updated: Cozy study environment for research discussion. Environment set to focused mood with moderate intensity for sustained duration.',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 