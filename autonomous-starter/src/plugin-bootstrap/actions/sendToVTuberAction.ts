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

const sendToVTuberInputSchema = z.object({ 
  text: z.string().min(1, 'Text prompt cannot be empty'),
}).partial().passthrough();

// Template for extracting VTuber message from complex content
const extractVTuberTextTemplate = `# Task: Extract VTuber Message

## Original Message:
{{content}}

## Instructions:
Extract the specific text that should be sent to the VTuber for speech/processing.

The message might contain:
- Direct VTuber prompts (e.g., "vtuber: Hello world")
- Instructions for the VTuber (e.g., "tell the vtuber to say good morning")
- Autonomous agent decisions to communicate with the VTuber
- Context or analysis that should be converted to VTuber speech

Rules:
1. If there's a direct "vtuber: [message]" format, extract just the message part
2. If it's an instruction like "tell vtuber to [action]", extract the action/message
3. If it's autonomous agent context, convert it to a natural VTuber message
4. Keep the extracted text concise and natural for speech
5. Return ONLY the text that should be spoken, nothing else

Examples:
- Input: "vtuber: Hello everyone!" → Output: "Hello everyone!"
- Input: "tell the vtuber to greet the viewers" → Output: "Hello viewers, great to see you!"
- Input: "Agent should update VTuber with excited state about Q&A" → Output: "I'm really excited to start our Q&A session! What questions do you have for me?"

Extract the VTuber message:`;

export const sendToVTuberAction: Action = {
  name: 'SEND_TO_VTUBER',
  similes: [
    'send message to vtuber',
    'tell vtuber',
    'vtuber say',
    'ask vtuber',
    'vtuber prompt',
    'process text for vtuber',
    'vtuber talk'
  ],
  description: 'Sends a specific text message or prompt to the VTuber for processing or speech. Example: "vtuber: Hello world" or "tell the vtuber to say good morning".',
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    if (message.content.text && message.content.text.trim().length > 0) {
      logger.debug(`[sendToVTuberAction] Validate: true (based on message.content.text: "${message.content.text.substring(0,50)}...")`);
      return true;
    }
    const vals = message.content.values as any;
    if (vals && typeof vals.text === 'string' && vals.text.trim().length > 0) {
      logger.debug('[sendToVTuberAction] Validate: true (based on message.content.values.text)');
      return true;
    }
    logger.debug('[sendToVTuberAction] Validate: false (no relevant text found)');
    return false;
  },
  handler: async (
    runtime: IAgentRuntime, 
    message: Memory,
    _state: State,
    _options: any,
    callback: HandlerCallback 
  ) => {
    logger.info(`[sendToVTuberAction] Handler attempting to process message: "${message.content.text}"`);
    const sourceValues = message.content.values ?? {};
    const parseResult = sendToVTuberInputSchema.safeParse(sourceValues); 
    
    let vtuberMessageText: string | undefined = undefined;

    // Prefer text from validated & parsed values if available
    if (parseResult.success && parseResult.data.text) {
      vtuberMessageText = parseResult.data.text.trim();
      logger.info(`[sendToVTuberAction] VTuber message extracted from message.content.values: "${vtuberMessageText}"`);
    } else if (message.content.text) { // Fallback to regex on raw text if not in values
      const fullInputText = message.content.text.trim();
      // More robust regex to capture text after variations of "tell the vtuber to say"
      const patterns = [
        /(?:vtuber|send to vtuber|tell vtuber|vtuber say|ask vtuber|vtuber prompt|vtuber talk)[:\s]+(?:that\s+)?(?:to\s+)?(?:say\s+)?['"]?(.+)['"]?$/i,
        /send (?:the message\s*)?['"](.+)['"] to(?: the)? vtuber/i,
      ];
      
      for (const pattern of patterns) {
        const match = fullInputText.match(pattern);
        if (match && match[1]) {
          vtuberMessageText = match[1].trim();
          logger.info(`[sendToVTuberAction] VTuber message extracted from message.content.text using regex: "${vtuberMessageText}"`);
          break;
        }
      }
      
      // If regex fails, use LLM to extract VTuber message from complex content
      if (!vtuberMessageText && fullInputText.length > 0) {
        logger.info('[sendToVTuberAction] Regex patterns failed, using LLM to extract VTuber message');
        try {
          const prompt = extractVTuberTextTemplate.replace('{{content}}', fullInputText);
          const llmResponse = await runtime.useModel(ModelType.TEXT_SMALL, {
            prompt,
          });
          
          if (llmResponse && llmResponse.trim().length > 0) {
            vtuberMessageText = llmResponse.trim();
            logger.info(`[sendToVTuberAction] VTuber message extracted using LLM: "${vtuberMessageText}"`);
          }
        } catch (error) {
          logger.error('[sendToVTuberAction] LLM extraction failed:', error);
        }
      }
    }

    if (!vtuberMessageText || vtuberMessageText.length === 0) {
      logger.error('[sendToVTuberAction] Handler: Could not determine/extract text for VTuber.');
      const errorContent: Content = { 
        text: 'I understood you want to talk to the VTuber, but I could not figure out what message to send. Please try saying: "vtuber: [your message]".',
        source: message.content.source,
        actions: ['SEND_TO_VTUBER_ERROR']
      };
      await callback(errorContent);
      return;
    }
    
    logger.info(`[sendToVTuberAction] Final VTuber message to send: "${vtuberMessageText}"`);
    
    // Resolve the VTuber endpoint URL. Use runtime settings/environment first, otherwise default
    // to the NeuroSync container hostname that is available on the shared Docker network.
    const vtuberUrl =
      runtime.getSetting('VTUBER_ENDPOINT_URL') ||
      'http://neurosync:5001/process_text';
    if (!vtuberUrl) {
        logger.error('[sendToVTuberAction] VTUBER_ENDPOINT_URL is not set in runtime settings.');
        await callback({
            text: 'The VTuber endpoint URL is not configured. I cannot send the message.',
            actions: ['SEND_TO_VTUBER_ERROR'],
            source: message.content.source
        });
        return;
    }

    try {
      logger.info(`[sendToVTuberAction] Sending text to VTuber: "${vtuberMessageText}" at ${vtuberUrl}`);
      const response = await runtime.fetch(vtuberUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: vtuberMessageText }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`[sendToVTuberAction] VTuber API request failed with status ${response.status}: ${errorText}`);
        throw new Error(`VTuber API request failed: ${response.status} ${errorText}`);
      }

      const responseData = await response.json();
      logger.info('[sendToVTuberAction] VTuber response received:', responseData);

      const responseContent: Content = {
        text: `Successfully sent to VTuber: "${vtuberMessageText}". VTuber responded: ${JSON.stringify(responseData)}`,
        actions: ['REPLY'], // Changed from ['SEND_TO_VTUBER'] to avoid loop if LLM just repeats the action
        source: message.content.source,
        values: responseData, // Pass through the response from VTuber endpoint
      };
      await callback(responseContent); 
    } catch (error) {
      logger.error('[sendToVTuberAction] Error during API call:', error);
      const errorContent: Content = {
        text: `Failed to send message to VTuber. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['SEND_TO_VTUBER_ERROR']
      };
      await callback(errorContent); 
    }
  },
  examples: [
    [
      {
        name: 'user',
        content: { 
            text: 'vtuber: Hello from the user!', 
        }
      },
      {
        name: 'agent',
        content: { 
            text: 'Successfully sent to VTuber: "Hello from the user!". VTuber responded: {"status":"received"}',
            actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'user',
        content: {
          text: "tell the vtuber that the weather is nice today",
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Successfully sent to VTuber: "the weather is nice today". VTuber responded: {"status":"received"}',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 