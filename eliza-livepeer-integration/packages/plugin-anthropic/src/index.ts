import { anthropic } from '@ai-sdk/anthropic';
import { getProviderBaseURL } from '@elizaos/core';
import type {
  GenerateTextParams,
  IAgentRuntime,
  ObjectGenerationParams,
  Plugin,
} from '@elizaos/core';
import { ModelType, logger } from '@elizaos/core';
import { generateText } from 'ai';
import { ensureReflectionProperties, extractAndParseJSON } from './utils';

/**
 * Retrieves a configuration setting from the runtime, falling back to environment variables or a default value if not found.
 *
 * @param key - The name of the setting to retrieve.
 * @param defaultValue - The value to return if the setting is not found in the runtime or environment.
 * @returns The resolved setting value, or {@link defaultValue} if not found.
 */
function getSetting(
  runtime: IAgentRuntime,
  key: string,
  defaultValue?: string
): string | undefined {
  return runtime.getSetting(key) ?? process.env[key] ?? defaultValue;
}

/**
 * Helper function to get the API key for OpenAI
 *
 * @param runtime The runtime context
 * @returns The configured API key
 */
function getApiKey(runtime: IAgentRuntime): string | undefined {
  return getSetting(runtime, 'ANTHROPIC_API_KEY');
}

/**
 * Ensures that the Anthropic API key is available in the runtime or environment.
 * Throws an error if the API key is missing.
 *
 * @param runtime - The agent runtime environment to check for settings.
 */
function ensureAnthropicAPIKeyExists(runtime: IAgentRuntime) {
  const apiKey = getApiKey(runtime);
  if (!apiKey) {
    throw new Error(
      'ANTHROPIC_API_KEY is missing. Please set it in your environment or runtime settings.'
    );
  }
}

/**
 * Plugin for Anthropic.
 *
 * @type {Plugin}
 * @property {string} name - The name of the plugin.
 * @property {string} description - The description of the plugin.
 * @property {Object} config - The configuration object with API keys and model variables.
 * @property {Function} init - Initializes the plugin with the given configuration.
 * @property {Function} models - Contains functions for generating text using small and large models.
 * @property {Function[]} tests - An array of test functions for the plugin.
 */
export const anthropicPlugin: Plugin = {
  name: 'anthropic',
  description: 'Anthropic plugin (supports text generation only)',
  config: {
    ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY,
    ANTHROPIC_SMALL_MODEL: process.env.ANTHROPIC_SMALL_MODEL,
    ANTHROPIC_LARGE_MODEL: process.env.ANTHROPIC_LARGE_MODEL,
  },
  async init(config: Record<string, string>, runtime: IAgentRuntime) {
    try {
      const apiKey = getApiKey(runtime);
      // If API key is not set, we'll show a warning but continue
      if (!apiKey) {
        logger.warn(
          'ANTHROPIC_API_KEY is not set in environment - Anthropic functionality will be limited'
        );
        // Return early without throwing an error
        return;
      }
    } catch (error) {
      // Convert to warning instead of error
      logger.warn(
        `Anthropic plugin configuration issue: ${error} - You need to configure the ANTHROPIC_API_KEY in your environment variables`
      );
    }
  },
  models: {
    [ModelType.TEXT_SMALL]: async (runtime, { prompt, stopSequences = [] }: GenerateTextParams) => {
      ensureAnthropicAPIKeyExists(runtime);

      const temperature = 0.7;
      const smallModel = runtime.getSetting('ANTHROPIC_SMALL_MODEL') ?? 'claude-3-haiku-20240307';
      const maxTokens = smallModel.includes('-3-') ? 4096 : 8192;

      logger.log(`[Anthropic] Using TEXT_SMALL model: ${smallModel}`);

      const { text } = await generateText({
        model: anthropic(smallModel),
        prompt,
        // Pass along any system prompt if available.
        system: runtime.character.system ?? undefined,
        temperature,
        maxTokens,
        stopSequences,
      });
      return text;
    },

    // TEXT_LARGE generation using Anthropics (e.g. using a "claude-3" model).
    [ModelType.TEXT_LARGE]: async (
      runtime,
      {
        prompt,
        maxTokens = 8192,
        stopSequences = [],
        temperature = 0.7,
        frequencyPenalty = 0.7,
        presencePenalty = 0.7,
      }: GenerateTextParams
    ) => {
      ensureAnthropicAPIKeyExists(runtime);

      const largeModel = runtime.getSetting('ANTHROPIC_LARGE_MODEL') ?? 'claude-3-5-sonnet-latest';

      logger.log(`[Anthropic] Using TEXT_LARGE model: ${largeModel}`);

      const { text } = await generateText({
        model: anthropic(largeModel),
        prompt,
        system: runtime.character.system ?? undefined,
        temperature,
        maxTokens,
        stopSequences,
        frequencyPenalty,
        presencePenalty,
      });
      return text;
    },

    [ModelType.OBJECT_SMALL]: async (runtime, params: ObjectGenerationParams) => {
      ensureAnthropicAPIKeyExists(runtime);

      const smallModel = runtime.getSetting('ANTHROPIC_SMALL_MODEL') ?? 'claude-3-haiku-20240307';

      logger.log(`[Anthropic] Using OBJECT_SMALL model: ${smallModel}`);

      try {
        // Check if this is a reflection schema request (has specific format)
        const isReflection = params.schema?.facts && params.schema.relationships;

        // Build a prompt that asks for JSON output
        let jsonPrompt = params.prompt;

        // Don't modify the prompt if it already contains explicit JSON formatting instructions
        if (!jsonPrompt.includes('```json') && !jsonPrompt.includes('respond with valid JSON')) {
          jsonPrompt +=
            '\nPlease respond with valid JSON only, without any explanations, markdown formatting, or additional text.';
        }

        let systemPrompt = runtime.character.system
          ? `${runtime.character.system}\nYou must respond with valid JSON only.`
          : 'You must respond with valid JSON only.';

        // For reflection schemas, we need a more specific instruction
        if (isReflection) {
          systemPrompt +=
            " Ensure your response includes 'thought', 'facts', and 'relationships' properties exactly as specified in the prompt.";
        } else {
          systemPrompt += ' No markdown, no code blocks, no explanation text.';
        }

        // Generate text response that should contain JSON
        const { text } = await generateText({
          model: anthropic(smallModel),
          prompt: jsonPrompt,
          system: systemPrompt,
          temperature: params.temperature || 0.2, // Lower temperature for more predictable structured output
        });

        // Extract and parse JSON from the response with our improved function
        try {
          logger.debug('Attempting to parse response from Anthropic model');
          const jsonObject = extractAndParseJSON(text);

          // Ensure reflection schema has all required properties
          const processedObject = ensureReflectionProperties(jsonObject, isReflection);

          return processedObject;
        } catch (parseError) {
          logger.error('Failed to parse JSON from Anthropic response:', parseError);
          logger.error('Raw response:', text);
          throw new Error('Invalid JSON returned from Anthropic model');
        }
      } catch (error) {
        logger.error('Error generating object:', error);
        throw error;
      }
    },

    [ModelType.OBJECT_LARGE]: async (runtime, params: ObjectGenerationParams) => {
      ensureAnthropicAPIKeyExists(runtime);

      const largeModel = runtime.getSetting('ANTHROPIC_LARGE_MODEL') ?? 'claude-3-5-sonnet-latest';

      logger.log(`[Anthropic] Using OBJECT_LARGE model: ${largeModel}`);

      try {
        // Check if this is a reflection schema request (has specific format)
        const isReflection = params.schema?.facts && params.schema.relationships;

        // Build a prompt that asks for JSON output
        let jsonPrompt = params.prompt;

        // Don't modify the prompt if it already contains explicit JSON formatting instructions
        if (!jsonPrompt.includes('```json') && !jsonPrompt.includes('respond with valid JSON')) {
          jsonPrompt +=
            '\nPlease respond with valid JSON only, without any explanations, markdown formatting, or additional text.';
        }

        let systemPrompt = runtime.character.system
          ? `${runtime.character.system}\nYou must respond with valid JSON only.`
          : 'You must respond with valid JSON only.';

        // For reflection schemas, we need a more specific instruction
        if (isReflection) {
          systemPrompt +=
            " Ensure your response includes 'thought', 'facts', and 'relationships' properties exactly as specified in the prompt.";
        } else {
          systemPrompt += ' No markdown, no code blocks, no explanation text.';
        }

        // Generate text response that should contain JSON
        const { text } = await generateText({
          model: anthropic(largeModel),
          prompt: jsonPrompt,
          system: systemPrompt,
          temperature: params.temperature || 0.2, // Lower temperature for more predictable structured output
        });

        // Extract and parse JSON from the response with our improved function
        try {
          logger.debug('Attempting to parse response from Anthropic model');
          const jsonObject = extractAndParseJSON(text);

          // Ensure reflection schema has all required properties
          const processedObject = ensureReflectionProperties(jsonObject, isReflection);

          return processedObject;
        } catch (parseError) {
          logger.error('Failed to parse JSON from Anthropic response:', parseError);
          logger.error('Raw response:', text);
          throw new Error('Invalid JSON returned from Anthropic model');
        }
      } catch (error) {
        logger.error('Error generating object:', error);
        throw error;
      }
    },
  },
  tests: [
    {
      name: 'anthropic_plugin_tests',
      tests: [
        {
          name: 'anthropic_test_text_small',
          fn: async (runtime) => {
            try {
              const text = await runtime.useModel(ModelType.TEXT_SMALL, {
                prompt: 'What is the nature of reality in 10 words?',
              });
              if (text.length === 0) {
                throw new Error('Failed to generate text');
              }
              logger.log('generated with test_text_small:', text);
            } catch (error) {
              logger.error('Error in test_text_small:', error);
              throw error;
            }
          },
        },
        {
          name: 'anthropic_test_text_large',
          fn: async (runtime) => {
            try {
              const text = await runtime.useModel(ModelType.TEXT_LARGE, {
                prompt: 'What is the nature of reality in 10 words?',
              });
              if (text.length === 0) {
                throw new Error('Failed to generate text');
              }
              logger.log('generated with test_text_large:', text);
            } catch (error) {
              logger.error('Error in test_text_large:', error);
              throw error;
            }
          },
        },
        {
          name: 'anthropic_test_object_with_code_blocks',
          fn: async (runtime) => {
            try {
              const result = await runtime.useModel(ModelType.OBJECT_SMALL, {
                prompt: 'Give me instructions to install Node.js',
                schema: { type: 'object' },
              });
              logger.log('Generated object with code blocks:', result);
              if (!result || result.error) {
                throw new Error('Failed to generate object with code blocks');
              }
            } catch (error) {
              logger.error('Error in test_object_with_code_blocks:', error);
              throw error;
            }
          },
        },
      ],
    },
  ],
};

export default anthropicPlugin;
