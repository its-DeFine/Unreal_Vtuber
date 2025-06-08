import {
  type Action,
  type ActionExample,
  type IAgentRuntime,
  type Memory,
  type State,
  type HandlerCallback,
  ModelType,
  composePromptFromState,
  logger,
  parseJSONObjectFromText,
} from '@elizaos/core';

// Prompt template for extracting API call details
const apiCallExtractionTemplate = `# Task: Extract API POST Request Details

## User Message:
{{recentMessages}}

## Instructions:
Analyze the user's message to extract the following information for making a POST API call:
1.  **endpointURL**: The full URL of the API endpoint to which the POST request should be made.
2.  **payload**: A JSON object representing the data to be sent in the request body. Infer the keys and values for this payload from the user's message.

Return the information in a single JSON object.

## Example:
User Message: "Hey, can you post a new user to https://api.example.com/users? Name is Alice, age 30, and email is alice@wonder.land."

Output:
\`\`\`json
{
  "endpointURL": "https://api.example.com/users",
  "payload": {
    "name": "Alice",
    "age": 30,
    "email": "alice@wonder.land"
  }
}
\`\`\`

User Message: "Please log a new event to our analytics at https://analytics.service.io/events. The event type is 'button_click' and the user ID is 'user123'."

Output:
\`\`\`json
{
  "endpointURL": "https://analytics.service.io/events",
  "payload": {
    "eventType": "button_click",
    "userId": "user123"
  }
}
\`\`\`

User Message: "I need to send some data to the /submit-form endpoint on our main site, myapp.com. It's for a survey, response ID survey999, and the answer to Q1 is 'Yes'."

Output:
\`\`\`json
{
  "endpointURL": "https://myapp.com/submit-form",
  "payload": {
    "responseId": "survey999",
    "Q1_answer": "Yes"
  }
}
\`\`\`

Ensure the output is a valid JSON object enclosed in \`\`\`json ... \`\`\` tags. If critical information (like the endpoint or any payload data) seems missing, output null for that field or an empty object for the payload.
If no clear intent to make a POST call is found, or if the message doesn't specify an endpoint, you can return:
\`\`\`json
{
  "endpointURL": null,
  "payload": {}
}
\`\`\`
`;

export const makeApiPostAction: Action = {
  name: 'MAKE_API_POST',
  description: 'Extracts information from the user message to prepare data for a POST request to a specified API endpoint. Does not actually send the request yet.',
  validate: async () => true, // Keep it simple for now
  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
    _options: any, // Not used for now
    callback: HandlerCallback,
    _responses?: Memory[]
  ) => {
    logger.info('[makeApiPostAction] Handler started.');

    try {
      const prompt = composePromptFromState({
        state, // Uses recentMessages from the state
        template: apiCallExtractionTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_LARGE, { // Using TEXT_LARGE for potentially complex extraction
        prompt,
      });

      logger.debug('[makeApiPostAction] LLM Response for extraction:', llmResponse);

      const extractedData = parseJSONObjectFromText(llmResponse);

      if (!extractedData || !extractedData.endpointURL || Object.keys(extractedData.payload || {}).length === 0) {
        logger.warn('[makeApiPostAction] Could not extract sufficient data from user message.', extractedData);
        await callback({
          text: "I couldn't fully understand the details for the API POST request. Please specify the full endpoint URL and the data you want to send.",
          actions: ['MAKE_API_POST_ERROR'],
          source: message.content.source,
        });
        return;
      }

      const { endpointURL, payload } = extractedData;

      const responseMessage = `Okay, I\'m ready to prepare a POST request:\nEndpoint: \`${endpointURL}\`\nPayload:\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\`\n(Note: This action currently only prepares the data and does not send the request yet.)`;

      logger.info(`[makeApiPostAction] Prepared data - Endpoint: ${endpointURL}, Payload: ${JSON.stringify(payload)}`);

      await callback({
        text: responseMessage,
        actions: ['REPLY'], // Just reply with the prepared data for now
        source: message.content.source,
      });

    } catch (error) {
      logger.error('[makeApiPostAction] Error in handler:', error);
      await callback({
        text: 'Sorry, I encountered an error while trying to prepare the API POST data.',
        actions: ['MAKE_API_POST_ERROR'],
        source: message.content.source,
      });
    }
  },
  examples: [
    [
      {
        name: 'user', // Simpler name for example
        content: {
          text: 'Post to https://example.com/api/data with item1=value1 and item2=value2.',
        },
      },
      {
        name: 'agent', // Simpler name for example
        content: {
          text: "Okay, I'm ready to prepare a POST request... (details follow)",
          actions: ['MAKE_API_POST'],
        },
      },
    ],
    [
      {
        name: 'user',
        content: {
          text: 'Send a new product to example.com/products. Name is "Super Widget", price is 29.99.',
        },
      },
      {
        name: 'agent',
        content: {
          text: "Okay, I'm ready to prepare a POST request... (details follow)",
          actions: ['MAKE_API_POST'],
        },
      },
    ],
  ] as ActionExample[][],
}; 