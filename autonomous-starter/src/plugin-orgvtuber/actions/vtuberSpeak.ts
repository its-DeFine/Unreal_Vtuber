import {
  type Action,
  type IAgentRuntime,
  type Memory,
  type State,
  type HandlerCallback,
  logger,
} from "@elizaos/core";
import { z } from "zod";

// Schema for VTuber speak parameters
const VTuberSpeakSchema = z.object({
  text: z.string().min(1, "Text is required"),
  autonomous_context: z.string().optional().describe("Optional context about the autonomous agent's current state or activity"),
});

export const vtuberSpeakAction: Action = {
  name: "VTUBER_SPEAK",
  similes: [
    "SAY_OUT_LOUD", 
    "SPEAK_ALOUD", 
    "VTUBER_SAY", 
    "ANIMATE_SPEECH",
    "NEURAL_SPEAK",
    "LIVE_SPEAK"
  ],
  description: "Send text to the VTuber system for speech synthesis and facial animation. This will make the VTuber character speak the provided text with realistic facial animations.",
  validate: async (runtime: IAgentRuntime, message: Memory) => {
    try {
      const vtuberEndpoint = runtime.getSetting("VTUBER_ENDPOINT_URL") || process.env.VTUBER_ENDPOINT_URL;
      if (!vtuberEndpoint) {
        logger.warn("VTUBER_SPEAK action: No VTuber endpoint URL configured");
        return false;
      }

      // Extract text from message content
      const content = typeof message.content === 'string' 
        ? message.content 
        : message.content?.text || "";

      return content.length > 0;
    } catch (error) {
      logger.error("Error validating VTUBER_SPEAK action:", error);
      return false;
    }
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
    options: { [key: string]: unknown },
    callback: HandlerCallback
  ) => {
    try {
      logger.info("🎭 VTUBER_SPEAK action triggered");

      const vtuberEndpoint = runtime.getSetting("VTUBER_ENDPOINT_URL") || process.env.VTUBER_ENDPOINT_URL;
      
      if (!vtuberEndpoint) {
        const errorMsg = "VTuber endpoint URL not configured. Set VTUBER_ENDPOINT_URL environment variable.";
        logger.error(errorMsg);
        
        if (callback) {
          callback({
            text: errorMsg,
            success: false,
          });
        }
        return false;
      }

      // Extract text from message content
      const content = typeof message.content === 'string' 
        ? message.content 
        : message.content?.text || "";

      if (!content.trim()) {
        const errorMsg = "No text content found to speak";
        logger.warn(errorMsg);
        
        if (callback) {
          callback({
            text: errorMsg,
            success: false,
          });
        }
        return false;
      }

      // Prepare payload for VTuber system
      const payload = {
        text: content.trim(),
        autonomous_context: `Agent: ${runtime.character.name}, Activity: Processing user interaction`
      };

      logger.info(`🎭 Sending to VTuber system: "${content.substring(0, 100)}${content.length > 100 ? '...' : ''}"`);
      logger.debug(`🔗 VTuber endpoint: ${vtuberEndpoint}`);

      // Send to VTuber system
      const response = await runtime.fetch(vtuberEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        const errorMsg = `VTuber request failed (${response.status}): ${errorText}`;
        logger.error(errorMsg);
        
        if (callback) {
          callback({
            text: errorMsg,
            success: false,
          });
        }
        return false;
      }

      const result = await response.json();
      logger.info("✅ VTuber speech processing initiated successfully");
      logger.debug("🎭 VTuber response:", result);

      if (callback) {
        callback({
          text: `VTuber speech processing initiated for: "${content.substring(0, 50)}${content.length > 50 ? '...' : ''}"`,
          success: true,
          data: {
            vtuber_status: result.status || "processing",
            vtuber_message: result.message || "Speech processing started",
            llm_provider: result.llm_provider,
            model: result.model,
            text_length: content.length
          }
        });
      }

      return true;

    } catch (error) {
      const errorMsg = `Error in VTuber speak action: ${error.message}`;
      logger.error(errorMsg, error);
      
      if (callback) {
        callback({
          text: errorMsg,
          success: false,
        });
      }
      return false;
    }
  },

  examples: [
    [
      {
        user: "{{user1}}",
        content: {
          text: "Can you say hello to everyone watching the stream?",
        },
      },
      {
        user: "{{user2}}",
        content: {
          text: "I'll speak this message out loud for the viewers.",
          action: "VTUBER_SPEAK",
        },
      },
    ],
    [
      {
        user: "{{user1}}",
        content: {
          text: "Tell them about the new features we're working on",
        },
      },
      {
        user: "{{user2}}",
        content: {
          text: "Hello everyone! Let me tell you about the exciting new features we're developing. We've been working on some amazing AI-powered tools that will enhance your experience.",
          action: "VTUBER_SPEAK",
        },
      },
    ],
    [
      {
        user: "{{user1}}",
        content: {
          text: "Can you explain what you're doing right now?",
        },
      },
      {
        user: "{{user2}}",
        content: {
          text: "Right now I'm processing your request and preparing to speak this response through the VTuber system with realistic facial animations.",
          action: "VTUBER_SPEAK",
        },
      },
    ],
  ],
}; 