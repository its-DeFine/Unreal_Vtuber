import type { ObjectGenerationParams, Plugin, TextEmbeddingParams } from '@elizaos/core';
import { type GenerateTextParams, ModelType, logger } from '@elizaos/core';
import { generateObject, generateText } from 'ai';
import { createOllama } from 'ollama-ai-provider';

// Default Ollama API URL
const OLLAMA_API_URL = 'http://localhost:11434/api';

/**
 * Generate text using Ollama API
 */
async function generateOllamaText(
  ollama: ReturnType<typeof createOllama>,
  model: string,
  params: {
    prompt: string;
    system?: string;
    temperature: number;
    maxTokens: number;
    frequencyPenalty: number;
    presencePenalty: number;
    stopSequences: string[];
  }
) {
  try {
    const { text: ollamaResponse } = await generateText({
      model: ollama(model),
      prompt: params.prompt,
      system: params.system,
      temperature: params.temperature,
      maxTokens: params.maxTokens,
      frequencyPenalty: params.frequencyPenalty,
      presencePenalty: params.presencePenalty,
      stopSequences: params.stopSequences,
    });
    return ollamaResponse;
  } catch (error: unknown) {
    logger.error('Error in generateOllamaText:', error);
    return 'Error generating text. Please try again later.';
  }
}

/**
 * Generate object using Ollama API with consistent error handling
 */
async function generateOllamaObject(
  ollama: ReturnType<typeof createOllama>,
  model: string,
  params: ObjectGenerationParams
) {
  try {
    const { object } = await generateObject({
      model: ollama(model),
      output: 'no-schema',
      prompt: params.prompt,
      temperature: params.temperature,
    });
    return object;
  } catch (error: unknown) {
    logger.error('Error generating object:', error);
    return {};
  }
}

export const ollamaPlugin: Plugin = {
  name: 'ollama',
  description: 'Ollama plugin',
  config: {
    OLLAMA_API_ENDPOINT: process.env.OLLAMA_API_ENDPOINT,
    OLLAMA_SMALL_MODEL: process.env.OLLAMA_SMALL_MODEL,
    OLLAMA_MEDIUM_MODEL: process.env.OLLAMA_MEDIUM_MODEL,
    OLLAMA_LARGE_MODEL: process.env.OLLAMA_LARGE_MODEL,
    OLLAMA_EMBEDDING_MODEL: process.env.OLLAMA_EMBEDDING_MODEL,
  },
  models: {
    [ModelType.TEXT_EMBEDDING]: async (
      runtime,
      params: TextEmbeddingParams | string | null
    ): Promise<number[]> => {
      try {
        const ollama = createOllama({
          fetch: runtime.fetch,
          baseURL: runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL,
        });

        const modelName = runtime.getSetting('OLLAMA_EMBEDDING_MODEL') || 'nomic-embed-text';
        logger.log(`[Ollama] Using TEXT_EMBEDDING model: ${modelName}`);
        const text =
          typeof params === 'string' ? params : (params as TextEmbeddingParams)?.text || '';

        if (!text) {
          logger.error('No text provided for embedding');
          return Array(1536).fill(0);
        }

        // Generate embeddings - note we're using a simpler approach since generateEmbedding
        // may not be available in the current version of the AI SDK
        try {
          // This is simplified and may need to be adjusted based on the actual API
          const response = await fetch(
            `${runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL}/embeddings`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                model: modelName,
                prompt: text,
              }),
            }
          );

          if (!response.ok) {
            throw new Error(`Embedding request failed: ${response.statusText}`);
          }

          const result = (await response.json()) as { embedding?: number[] };
          return result.embedding || Array(1536).fill(0);
        } catch (embeddingError) {
          logger.error('Error generating embedding:', embeddingError);
          return Array(1536).fill(0);
        }
      } catch (error) {
        logger.error('Error in TEXT_EMBEDDING model:', error);
        // Return a fallback vector rather than crashing
        return Array(1536).fill(0);
      }
    },
    [ModelType.TEXT_SMALL]: async (runtime, { prompt, stopSequences = [] }: GenerateTextParams) => {
      try {
        const temperature = 0.7;
        const frequency_penalty = 0.7;
        const presence_penalty = 0.7;
        const max_response_length = 8000;
        const ollama = createOllama({
          fetch: runtime.fetch,
          baseURL: runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL,
        });

        const model =
          runtime.getSetting('OLLAMA_SMALL_MODEL') ??
          runtime.getSetting('SMALL_MODEL') ??
          'gemma3:latest';

        logger.log(`[Ollama] Using TEXT_SMALL model: ${model}`);
        logger.log('generating text');
        logger.log(prompt);

        return await generateOllamaText(ollama, model, {
          prompt,
          system: runtime.character.system ?? undefined,
          temperature,
          maxTokens: max_response_length,
          frequencyPenalty: frequency_penalty,
          presencePenalty: presence_penalty,
          stopSequences,
        });
      } catch (error) {
        logger.error('Error in TEXT_SMALL model:', error);
        return 'Error generating text. Please try again later.';
      }
    },
    [ModelType.TEXT_LARGE]: async (
      runtime,
      {
        prompt,
        stopSequences = [],
        maxTokens = 8192,
        temperature = 0.7,
        frequencyPenalty = 0.7,
        presencePenalty = 0.7,
      }: GenerateTextParams
    ) => {
      try {
        const model =
          runtime.getSetting('OLLAMA_LARGE_MODEL') ??
          runtime.getSetting('LARGE_MODEL') ??
          'gemma3:latest';
        const ollama = createOllama({
          fetch: runtime.fetch,
          baseURL: runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL,
        });

        logger.log(`[Ollama] Using TEXT_LARGE model: ${model}`);
        return await generateOllamaText(ollama, model, {
          prompt,
          system: runtime.character.system ?? undefined,
          temperature,
          maxTokens,
          frequencyPenalty,
          presencePenalty,
          stopSequences,
        });
      } catch (error) {
        logger.error('Error in TEXT_LARGE model:', error);
        return 'Error generating text. Please try again later.';
      }
    },
    [ModelType.OBJECT_SMALL]: async (runtime, params: ObjectGenerationParams) => {
      try {
        const ollama = createOllama({
          fetch: runtime.fetch,
          baseURL: runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL,
        });
        const model =
          runtime.getSetting('OLLAMA_SMALL_MODEL') ??
          runtime.getSetting('SMALL_MODEL') ??
          'gemma3:latest';

        logger.log(`[Ollama] Using OBJECT_SMALL model: ${model}`);
        if (params.schema) {
          logger.info('Using OBJECT_SMALL without schema validation');
        }

        return await generateOllamaObject(ollama, model, params);
      } catch (error) {
        logger.error('Error in OBJECT_SMALL model:', error);
        // Return empty object instead of crashing
        return {};
      }
    },
    [ModelType.OBJECT_LARGE]: async (runtime, params: ObjectGenerationParams) => {
      try {
        const ollama = createOllama({
          fetch: runtime.fetch,
          baseURL: runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL,
        });
        const model =
          runtime.getSetting('OLLAMA_LARGE_MODEL') ??
          runtime.getSetting('LARGE_MODEL') ??
          'gemma3:latest';

        logger.log(`[Ollama] Using OBJECT_LARGE model: ${model}`);
        if (params.schema) {
          logger.info('Using OBJECT_LARGE without schema validation');
        }

        return await generateOllamaObject(ollama, model, params);
      } catch (error) {
        logger.error('Error in OBJECT_LARGE model:', error);
        // Return empty object instead of crashing
        return {};
      }
    },
  },
  tests: [
    {
      name: 'ollama_plugin_tests',
      tests: [
        {
          name: 'ollama_test_url_validation',
          fn: async (runtime) => {
            try {
              const baseURL = runtime.getSetting('OLLAMA_API_ENDPOINT') || OLLAMA_API_URL;
              const response = await fetch(`${baseURL}/tags`);
              const data = await response.json();
              logger.log('Models Available:', (data as { models: unknown[] })?.models?.length);
              if (!response.ok) {
                logger.error(`Failed to validate Ollama API: ${response.statusText}`);
                return;
              }
            } catch (error) {
              logger.error('Error in ollama_test_url_validation:', error);
            }
          },
        },
        {
          name: 'ollama_test_text_embedding',
          fn: async (runtime) => {
            try {
              const embedding = await runtime.useModel(ModelType.TEXT_EMBEDDING, {
                text: 'Hello, world!',
              });
              logger.log('embedding', embedding);
            } catch (error) {
              logger.error('Error in test_text_embedding:', error);
            }
          },
        },
        {
          name: 'ollama_test_text_large',
          fn: async (runtime) => {
            try {
              const text = await runtime.useModel(ModelType.TEXT_LARGE, {
                prompt: 'What is the nature of reality in 10 words?',
              });
              if (text.length === 0) {
                logger.error('Failed to generate text');
                return;
              }
              logger.log('generated with test_text_large:', text);
            } catch (error) {
              logger.error('Error in test_text_large:', error);
            }
          },
        },
        {
          name: 'ollama_test_text_small',
          fn: async (runtime) => {
            try {
              const text = await runtime.useModel(ModelType.TEXT_SMALL, {
                prompt: 'What is the nature of reality in 10 words?',
              });
              if (text.length === 0) {
                logger.error('Failed to generate text');
                return;
              }
              logger.log('generated with test_text_small:', text);
            } catch (error) {
              logger.error('Error in test_text_small:', error);
            }
          },
        },
        {
          name: 'ollama_test_object_small',
          fn: async (runtime) => {
            try {
              const object = await runtime.useModel(ModelType.OBJECT_SMALL, {
                prompt:
                  'Generate a JSON object representing a user profile with name, age, and hobbies',
                temperature: 0.7,
              });
              logger.log('Generated object:', object);
            } catch (error) {
              logger.error('Error in test_object_small:', error);
            }
          },
        },
        {
          name: 'ollama_test_object_large',
          fn: async (runtime) => {
            try {
              const object = await runtime.useModel(ModelType.OBJECT_LARGE, {
                prompt:
                  'Generate a detailed JSON object representing a restaurant with name, cuisine type, menu items with prices, and customer reviews',
                temperature: 0.7,
              });
              logger.log('Generated object:', object);
            } catch (error) {
              logger.error('Error in test_object_large:', error);
            }
          },
        },
      ],
    },
  ],
};
export default ollamaPlugin;
