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
    parseJSONObjectFromText
} from '@elizaos/core';
import { TaskExecutionService } from '../services/TaskExecutionService';
import { SubTask, TaskArtifact } from '../types/TaskStructure';
import { v4 as uuidv4 } from 'uuid';

const workExecutionTemplate = `# Task: Execute Autonomous Work

## User Message/Context:
{{recentMessages}}

## Current Context:
{{content}}

## Instructions:
Based on the context and conversation, determine what type of work should be executed autonomously.

Work types available:
- **research**: Conduct research on specific topics, gather information, analyze sources
- **code**: Write, modify, or analyze code and technical implementations  
- **analysis**: Analyze data, situations, or information to draw insights
- **communication**: Create messages, reports, or communications for stakeholders
- **decision**: Make decisions based on available information and criteria

Extract the work specification that should be executed.

Return a JSON object with:
\`\`\`json
{
  "workType": "research|code|analysis|communication|decision",
  "title": "Brief title for the work",
  "description": "Detailed description of what needs to be done",
  "requirements": ["requirement 1", "requirement 2", "requirement 3"],
  "estimatedEffort": 2.5,
  "priority": "high|medium|low"
}
\`\`\`

Example:
\`\`\`json
{
  "workType": "research",
  "title": "Research VTuber content optimization strategies", 
  "description": "Research current trends and best practices for VTuber content creation and audience engagement",
  "requirements": ["Current trend analysis", "Best practices identification", "Actionable recommendations"],
  "estimatedEffort": 1.5,
  "priority": "high"
}
\`\`\`

Make sure to include the \`\`\`json\`\`\` tags around the JSON object.`;

export const executeWorkAction: Action = {
    name: 'EXECUTE_WORK',
    similes: [
        'do work',
        'perform task',
        'execute task',
        'complete work',
        'carry out work',
        'autonomous work',
        'work on task'
    ],
    description: 'Executes autonomous work including research, coding, analysis, communication, and decision-making tasks. Creates artifacts and evaluates work quality.',
    
    validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
        // Allow work execution when the autonomous agent determines it's needed
        logger.debug(`[executeWorkAction] Validating work execution request for message: "${message.content.text?.substring(0, 50)}..."`);
        return true;
    },

    handler: async (
        runtime: IAgentRuntime,
        message: Memory,
        state: State,
        _options: any,
        callback: HandlerCallback
    ) => {
        logger.info(`[executeWorkAction] Processing autonomous work execution request`);

        try {
            // Get task execution service
            const taskExecutionService = runtime.getService('TASK_EXECUTION') as TaskExecutionService;
            if (!taskExecutionService) {
                logger.error('[executeWorkAction] Task execution service not available');
                await callback({
                    text: "Task execution service is not available. Cannot execute autonomous work.",
                    actions: ['EXECUTE_WORK_ERROR'],
                    source: message.content.source,
                });
                return;
            }

            // Generate work specification using LLM
            const prompt = composePromptFromState({
                state,
                template: workExecutionTemplate,
            });

            const llmResponse = await runtime.useModel(ModelType.TEXT_SMALL, {
                prompt,
            });

            logger.debug('[executeWorkAction] LLM Response for work specification:', llmResponse);

            // Parse work specification
            let workSpec;
            try {
                const jsonMatch = llmResponse.match(/```json\s*([\s\S]*?)\s*```/);
                if (jsonMatch && jsonMatch[1]) {
                    workSpec = JSON.parse(jsonMatch[1].trim());
                    logger.info('[executeWorkAction] Successfully extracted work specification from LLM response');
                } else {
                    const jsonRegex = /\{[\s\S]*?\}/;
                    const possibleJson = llmResponse.match(jsonRegex);
                    if (possibleJson) {
                        workSpec = JSON.parse(possibleJson[0]);
                        logger.info('[executeWorkAction] Successfully parsed work specification from regex match');
                    }
                }
            } catch (parseError) {
                logger.error('[executeWorkAction] Failed to parse work specification:', parseError);
                
                // Create a fallback work specification
                workSpec = {
                    workType: "analysis",
                    title: "General autonomous work task",
                    description: "Perform general analysis and work based on current context",
                    requirements: ["Complete analysis", "Generate insights", "Provide recommendations"],
                    estimatedEffort: 1.0,
                    priority: "medium"
                };
                logger.info('[executeWorkAction] Using fallback work specification');
            }

            if (!workSpec || !workSpec.workType) {
                logger.error('[executeWorkAction] Could not determine work specification');
                await callback({
                    text: "I couldn't determine what work to execute from the current context.",
                    actions: ['EXECUTE_WORK_ERROR'],
                    source: message.content.source,
                });
                return;
            }

            logger.info('[executeWorkAction] ✅ WORK SPECIFICATION EXTRACTED:', JSON.stringify(workSpec, null, 2));

            // Create subtask for execution
            const subtask: SubTask = {
                id: uuidv4(),
                parentId: 'autonomous-work',
                title: workSpec.title,
                description: workSpec.description,
                workType: workSpec.workType,
                estimatedEffort: workSpec.estimatedEffort || 1.0,
                status: 'pending',
                evaluationHistory: [],
                artifacts: [],
                dependencies: [],
                requirements: (workSpec.requirements || []).map((req: string, index: number) => ({
                    id: `req-${index}`,
                    type: 'functional' as const,
                    description: req,
                    acceptance_criteria: [req],
                    priority: 'must_have' as const,
                    status: 'defined' as const,
                    verification: {
                        method: 'review' as const,
                        criteria: req,
                    },
                    traceability: {
                        source: 'autonomous_work_request',
                        relatedRequirements: [],
                        testCases: []
                    }
                })),
                context: {
                    autonomousRequest: true,
                    originalMessage: message.content.text,
                    priority: workSpec.priority || 'medium'
                }
            };

            logger.info(`[executeWorkAction] 🚀 EXECUTING AUTONOMOUS WORK: "${workSpec.title}" (${workSpec.workType})`);

            // Execute the work
            const result = await taskExecutionService.executeSubtask(subtask);

            // Prepare response based on execution result
            let responseText = '';
            if (result.status === 'completed') {
                responseText = `✅ Autonomous work completed successfully: "${workSpec.title}"

**Work Type:** ${workSpec.workType}
**Quality Score:** ${result.evaluation?.overallScore || 'N/A'}/100
**Time Taken:** ${result.actualEffort.toFixed(2)} hours
**Artifacts Created:** ${result.artifacts.length}

**Summary:**
${result.evaluation?.feedback || 'Work completed as specified.'}`;

                if (result.evaluation && result.evaluation.nextActions.length > 0) {
                    responseText += `\n\n**Recommended Next Actions:**\n${result.evaluation.nextActions.map(action => `• ${action}`).join('\n')}`;
                }
            } else if (result.status === 'partial') {
                responseText = `⚠️ Autonomous work partially completed: "${workSpec.title}"

**Work Type:** ${workSpec.workType}
**Quality Score:** ${result.evaluation?.overallScore || 'N/A'}/100
**Status:** Partial completion - may need additional work
**Time Taken:** ${result.actualEffort.toFixed(2)} hours
**Artifacts Created:** ${result.artifacts.length}

**Feedback:**
${result.evaluation?.feedback || 'Work partially completed but may need refinement.'}`;
            } else {
                responseText = `❌ Autonomous work failed: "${workSpec.title}"

**Work Type:** ${workSpec.workType}
**Status:** Failed
**Error:** ${result.error || 'Unknown error occurred'}
**Time Taken:** ${result.actualEffort.toFixed(2)} hours`;
            }

            const responseContent: Content = {
                text: responseText,
                actions: ['REPLY'],
                source: message.content.source,
                values: {
                    workSpec,
                    executionResult: result,
                    artifacts: result.artifacts.map(a => ({
                        type: a.type,
                        qualityScore: (a.qualityMetrics.accuracy + a.qualityMetrics.completeness + a.qualityMetrics.clarity + a.qualityMetrics.usefulness) / 4
                    }))
                },
            };

            logger.info(`[executeWorkAction] 📤 WORK EXECUTION RESPONSE:`, JSON.stringify({
                title: workSpec.title,
                workType: workSpec.workType,
                status: result.status,
                qualityScore: result.evaluation?.overallScore,
                artifactsCount: result.artifacts.length
            }, null, 2));

            await callback(responseContent);

        } catch (error) {
            logger.error('[executeWorkAction] Error during work execution:', error);
            const errorContent: Content = {
                text: `Failed to execute autonomous work. Error: ${error instanceof Error ? error.message : String(error)}`,
                source: message.content.source,
                actions: ['EXECUTE_WORK_ERROR']
            };
            await callback(errorContent);
        }
    },

    examples: [
        [
            {
                name: 'agent',
                content: {
                    text: 'I need to research current VTuber content trends for better engagement',
                }
            },
            {
                name: 'agent',
                content: {
                    text: '✅ Autonomous work completed successfully: "Research VTuber content optimization strategies"\n\n**Work Type:** research\n**Quality Score:** 85/100\n**Time Taken:** 1.2 hours\n**Artifacts Created:** 1',
                    actions: ['REPLY'],
                }
            },
        ],
        [
            {
                name: 'agent',
                content: {
                    text: 'I should analyze the current system performance to identify optimization opportunities',
                }
            },
            {
                name: 'agent',
                content: {
                    text: '✅ Autonomous work completed successfully: "System performance analysis"\n\n**Work Type:** analysis\n**Quality Score:** 82/100\n**Time Taken:** 0.8 hours\n**Artifacts Created:** 1',
                    actions: ['REPLY'],
                }
            }
        ],
        [
            {
                name: 'agent',
                content: {
                    text: 'Need to implement a new feature for better user interaction',
                }
            },
            {
                name: 'agent',
                content: {
                    text: '✅ Autonomous work completed successfully: "Implement user interaction feature"\n\n**Work Type:** code\n**Quality Score:** 78/100\n**Time Taken:** 2.1 hours\n**Artifacts Created:** 2',
                    actions: ['REPLY'],
                }
            }
        ]
    ] as ActionExample[][],
}; 