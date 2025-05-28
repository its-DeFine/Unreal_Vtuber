import {
  type Action, 
  type ActionExample, 
  type IAgentRuntime, 
  type Memory, 
  type State, 
  type HandlerCallback, 
  type Content,
  logger,
  ModelType
} from '@elizaos/core';
import { z } from 'zod';

const directVTuberSpeechInputSchema = z.object({ 
  text: z.string().min(1, 'Speech text cannot be empty'),
  emotion: z.string().optional(),
  priority: z.enum(['low', 'normal', 'high']).optional(),
}).partial().passthrough();

export const directVTuberSpeechAction: Action = {
  name: 'DIRECT_VTUBER_SPEECH',
  similes: [
    'speak directly to vtuber',
    'vtuber speak now',
    'direct vtuber speech',
    'immediate vtuber response',
    'vtuber say immediately'
  ],
  description: 'Sends text directly to VTuber for immediate speech generation, bypassing authority conflicts. Use for urgent or important VTuber communications.',
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    if (message.content.text && message.content.text.trim().length > 0) {
      logger.debug(`[directVTuberSpeechAction] Validate: true (based on message.content.text: "${message.content.text.substring(0,50)}...")`);
      return true;
    }
    const vals = message.content.values as any;
    if (vals && typeof vals.text === 'string' && vals.text.trim().length > 0) {
      logger.debug('[directVTuberSpeechAction] Validate: true (based on message.content.values.text)');
      return true;
    }
    logger.debug('[directVTuberSpeechAction] Validate: false (no relevant text found)');
    return false;
  },
  handler: async (
    runtime: IAgentRuntime, 
    message: Memory,
    _state: State,
    _options: any,
    callback: HandlerCallback 
  ) => {
    logger.info(`[directVTuberSpeechAction] Processing direct VTuber speech request: "${message.content.text}"`);
    const sourceValues = message.content.values ?? {};
    const parseResult = directVTuberSpeechInputSchema.safeParse(sourceValues); 
    
    let speechText: string | undefined = undefined;
    let emotion: string = 'neutral';
    let priority: string = 'high'; // Default to high priority for direct speech

    // Extract speech parameters
    if (parseResult.success && parseResult.data.text) {
      speechText = parseResult.data.text.trim();
      emotion = parseResult.data.emotion || 'neutral';
      priority = parseResult.data.priority || 'high';
      logger.info(`[directVTuberSpeechAction] Speech extracted from values: "${speechText}" (emotion: ${emotion}, priority: ${priority})`);
    } else if (message.content.text) {
      const fullInputText = message.content.text.trim();
      
      // Extract speech text using simple patterns
      const speechPatterns = [
        /(?:direct|immediate|urgent)\s+(?:vtuber\s+)?(?:speech|speak|say)[:\s]+['"]?(.+?)['"]?$/i,
        /vtuber\s+speak\s+now[:\s]+['"]?(.+?)['"]?$/i,
        /(?:speak|say)\s+directly[:\s]+['"]?(.+?)['"]?$/i,
      ];
      
      for (const pattern of speechPatterns) {
        const match = fullInputText.match(pattern);
        if (match && match[1]) {
          speechText = match[1].trim();
          logger.info(`[directVTuberSpeechAction] Speech extracted using pattern: "${speechText}"`);
          break;
        }
      }
      
      // If no pattern matches, use the full text as speech
      if (!speechText && fullInputText.length > 0) {
        speechText = fullInputText;
        logger.info(`[directVTuberSpeechAction] Using full text as speech: "${speechText}"`);
      }
      
      // Extract emotion if mentioned
      if (fullInputText.match(/\b(happy|excited|sad|angry|neutral|calm|energetic)\b/i)) {
        const emotionMatch = fullInputText.match(/\b(happy|excited|sad|angry|neutral|calm|energetic)\b/i);
        if (emotionMatch) {
          emotion = emotionMatch[1].toLowerCase();
        }
      }
    }

    if (!speechText || speechText.length === 0) {
      logger.error('[directVTuberSpeechAction] Could not extract speech text');
      const errorContent: Content = { 
        text: 'I could not determine what the VTuber should say. Please provide clear speech text.',
        source: message.content.source,
        actions: ['DIRECT_VTUBER_SPEECH_ERROR']
      };
      await callback(errorContent);
      return;
    }
    
    logger.info(`[directVTuberSpeechAction] Final speech parameters - Text: "${speechText}", Emotion: ${emotion}, Priority: ${priority}`);
    
    // Get VTuber endpoint URL
    const vtuberUrl = runtime.getSetting('VTUBER_ENDPOINT_URL') || 'http://neurosync:5001/process_text';
    
    if (!vtuberUrl) {
        logger.error('[directVTuberSpeechAction] VTUBER_ENDPOINT_URL is not configured');
        await callback({
            text: 'VTuber endpoint is not configured. Cannot send direct speech.',
            actions: ['DIRECT_VTUBER_SPEECH_ERROR'],
            source: message.content.source
        });
        return;
    }

    try {
      logger.info(`[directVTuberSpeechAction] 🎯 SENDING DIRECT SPEECH TO VTUBER: "${speechText}" at ${vtuberUrl}`);
      
      // Create direct speech payload with minimal context to avoid conflicts
      const requestPayload = { 
        text: speechText,
        direct_speech: true,  // Flag for direct speech processing
        emotion: emotion,
        priority: priority,
        source: "autonomous_direct",
        timestamp: Date.now(),
        // Minimal context to avoid authority conflicts
        context: {
          type: "direct_speech",
          agent: "Autoliza",
          bypass_queue: priority === 'high',
          force_generation: true  // Force speech generation
        }
      };
      
      logger.debug(`[directVTuberSpeechAction] Direct speech payload:`, JSON.stringify(requestPayload, null, 2));
      
      const response = await runtime.fetch(vtuberUrl, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Direct-Speech': 'true',  // Header to indicate direct speech
          'X-Priority': priority
        },
        body: JSON.stringify(requestPayload),
      });

      logger.info(`[directVTuberSpeechAction] VTuber Direct Speech Response Status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`[directVTuberSpeechAction] ❌ DIRECT SPEECH FAILED - Status: ${response.status}, Error: ${errorText}`);
        throw new Error(`Direct VTuber speech failed: ${response.status} ${errorText}`);
      }

      const responseData = await response.json();
      logger.info(`[directVTuberSpeechAction] ✅ DIRECT SPEECH RESPONSE:`, JSON.stringify(responseData, null, 2));

      const responseContent: Content = {
        text: `✅ Direct VTuber speech sent successfully: "${speechText}" (${emotion} emotion, ${priority} priority). Response: ${JSON.stringify(responseData)}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: {
          ...responseData,
          speech_text: speechText,
          emotion: emotion,
          priority: priority,
          direct_speech: true
        },
      };
      
      logger.info(`[directVTuberSpeechAction] 📤 SUCCESS CALLBACK:`, JSON.stringify({
        text: responseContent.text,
        actions: responseContent.actions,
        speech_sent: true
      }, null, 2));
      
      await callback(responseContent); 
    } catch (error) {
      logger.error(`[directVTuberSpeechAction] ❌ DIRECT SPEECH ERROR:`, error);
      const errorContent: Content = {
        text: `❌ Failed to send direct VTuber speech. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['DIRECT_VTUBER_SPEECH_ERROR']
      };
      
      logger.error(`[directVTuberSpeechAction] 📤 ERROR CALLBACK:`, JSON.stringify(errorContent, null, 2));
      await callback(errorContent); 
    }
  },
  examples: [
    [
      {
        name: 'user',
        content: { 
            text: 'direct vtuber speech: Hello everyone, welcome to my stream!', 
        }
      },
      {
        name: 'agent',
        content: { 
            text: '✅ Direct VTuber speech sent successfully: "Hello everyone, welcome to my stream!" (neutral emotion, high priority).',
            actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'user',
        content: {
          text: "vtuber speak now: I'm so excited to start today's adventure!",
        }
      },
      {
        name: 'agent',
        content: {
          text: '✅ Direct VTuber speech sent successfully: "I\'m so excited to start today\'s adventure!" (excited emotion, high priority).',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 