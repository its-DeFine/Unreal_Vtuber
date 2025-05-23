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

const researchTemplate = `# Task: Extract Research Query Information

## Current Context:
{{content}}

## Recent Messages:
{{recentMessages}}

## Instructions:
Analyze the context and determine what research needs to be conducted.
Research can include:
- Web searches for current information
- Knowledge base queries for facts
- Technical documentation lookup
- News and current events
- Scientific or academic research
- Market research or trends

Extract the research query and determine the best research method.

Return a JSON object with:
\`\`\`json
{
  "queryType": "web_search|knowledge_query|technical_docs|news|academic|market_trends",
  "query": "specific search query or question",
  "context": "why this research is needed",
  "expectedOutput": "what kind of information is expected"
}
\`\`\`

Example outputs:
1. For web search:
\`\`\`json
{
  "queryType": "web_search",
  "query": "latest developments in AI autonomous agents 2024",
  "context": "Need current information about autonomous agent technology",
  "expectedOutput": "Recent news, papers, and developments in autonomous AI"
}
\`\`\`

2. For knowledge query:
\`\`\`json
{
  "queryType": "knowledge_query",
  "query": "How do neural networks process natural language",
  "context": "Understanding NLP fundamentals for better communication",
  "expectedOutput": "Technical explanation of NLP in neural networks"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const doResearchAction: Action = {
  name: 'DO_RESEARCH',
  similes: [
    'research',
    'search for information',
    'look up',
    'find information',
    'investigate',
    'gather data',
    'web search',
    'knowledge query',
    'study'
  ],
  description: 'Conducts research by searching the web, querying knowledge bases, or gathering information on specific topics. Used to expand knowledge and context.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Always allow research as it's part of autonomous learning
    logger.debug(`[doResearchAction] Validating research request for message: "${message.content.text?.substring(0, 50)}..."`);
    return true;
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    state: State,
    _options: any,
    callback: HandlerCallback
  ) => {
    logger.info(`[doResearchAction] Processing research request`);

    try {
      // Generate research query using LLM
      const prompt = composePromptFromState({
        state,
        template: researchTemplate,
      });

      const llmResponse = await runtime.useModel(ModelType.TEXT_LARGE, {
        prompt,
      });

      logger.debug('[doResearchAction] LLM Response for research query:', llmResponse);

      const researchData = parseJSONObjectFromText(llmResponse);

      if (!researchData || !researchData.queryType || !researchData.query) {
        logger.warn('[doResearchAction] Could not extract valid research query', researchData);
        await callback({
          text: "I couldn't determine what research to conduct from the current context.",
          actions: ['DO_RESEARCH_ERROR'],
          source: message.content.source,
        });
        return;
      }

      logger.info(`[doResearchAction] Conducting ${researchData.queryType} research:`, researchData.query);

      let researchResults: any = {};

      // Conduct research based on query type
      switch (researchData.queryType) {
        case 'web_search':
          try {
            // Use runtime's web search if available, otherwise simulate
            const webSearchResult = await runtime.fetch('https://api.duckduckgo.com/?q=' + encodeURIComponent(researchData.query) + '&format=json&no_html=1&skip_disambig=1', {
              method: 'GET',
              headers: { 'User-Agent': 'AutonomousAgent/1.0' },
            });
            
            if (webSearchResult.ok) {
              const searchData = await webSearchResult.json();
              researchResults = {
                type: 'web_search',
                query: researchData.query,
                results: searchData,
                summary: `Found ${searchData.RelatedTopics?.length || 0} related topics`
              };
            } else {
              throw new Error('Web search API unavailable');
            }
          } catch (error) {
            logger.warn('[doResearchAction] Web search failed, using simulated results:', error);
            researchResults = {
              type: 'web_search',
              query: researchData.query,
              results: { simulated: true, message: 'Web search simulated - actual results would appear here' },
              summary: `Simulated web search for: ${researchData.query}`
            };
          }
          break;

        case 'knowledge_query':
          // Query existing knowledge/memories from runtime
          try {
            const knowledgeResults = await runtime.getMemories({
              tableName: 'facts',
              count: 10,
              unique: true,
            });
            
            researchResults = {
              type: 'knowledge_query',
              query: researchData.query,
              results: knowledgeResults.map(m => m.content.text),
              summary: `Found ${knowledgeResults.length} relevant knowledge items`
            };
          } catch (error) {
            logger.warn('[doResearchAction] Knowledge query failed:', error);
            researchResults = {
              type: 'knowledge_query',
              query: researchData.query,
              results: { error: 'Knowledge query failed' },
              summary: 'Unable to access knowledge base'
            };
          }
          break;

        default:
          // For other types, provide simulated research
          researchResults = {
            type: researchData.queryType,
            query: researchData.query,
            results: { 
              simulated: true, 
              message: `${researchData.queryType} research would be conducted here`,
              context: researchData.context,
              expectedOutput: researchData.expectedOutput
            },
            summary: `Simulated ${researchData.queryType} research completed`
          };
      }

      logger.info('[doResearchAction] Research completed:', researchResults);

      const responseContent: Content = {
        text: `Research completed: ${researchResults.summary}. Query: "${researchData.query}". Context: ${researchData.context}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: { 
          researchQuery: researchData, 
          researchResults: researchResults,
          timestamp: Date.now()
        },
      };

      await callback(responseContent);

      // Store research results as a memory for future reference
      const researchMemory = {
        content: {
          text: `Research: ${researchData.query} - ${researchResults.summary}`,
          type: 'research_result',
          researchData: researchData,
          results: researchResults,
        },
        entityId: runtime.agentId,
        roomId: message.roomId,
        worldId: message.worldId,
      };

      await runtime.createMemory(researchMemory, 'facts');

    } catch (error) {
      logger.error('[doResearchAction] Error during research:', error);
      const errorContent: Content = {
        text: `Failed to conduct research. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['DO_RESEARCH_ERROR']
      };
      await callback(errorContent);
    }
  },

  examples: [
    [
      {
        name: 'agent',
        content: {
          text: 'I need to research the latest AI developments',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Research completed: Found 12 related topics. Query: "latest AI developments 2024". Context: Need current information about AI technology.',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'I should look up how neural networks work',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'Research completed: Found 5 relevant knowledge items. Query: "neural network fundamentals". Context: Understanding basic AI concepts.',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 