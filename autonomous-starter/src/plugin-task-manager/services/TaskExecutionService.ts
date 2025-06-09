import { IAgentRuntime, Service, logger, ServiceTypeName } from '@elizaos/core';
import { 
    CentralTask, 
    SubTask, 
    TaskArtifact, 
    SubtaskResult,
    TaskOperationResult 
} from '../types/TaskStructure';
import { TaskEvaluationService } from './TaskEvaluationService';
import { v4 as uuidv4 } from 'uuid';

export class TaskExecutionService extends Service {
    static serviceType: ServiceTypeName = 'TASK_EXECUTION' as ServiceTypeName;
    
    private executionQueue: Map<string, SubTask> = new Map();
    private activeExecutions: Map<string, { 
        subtask: SubTask; 
        startTime: Date; 
        progress: number; 
    }> = new Map();
    
    private taskEvaluationService: TaskEvaluationService;
    private maxConcurrentExecutions: number = 3;
    
    constructor(runtime: IAgentRuntime) {
        super(runtime);
        this.taskEvaluationService = new TaskEvaluationService(runtime);
        logger.info('🔧 [TASK-EXEC] Service initialized');
    }
    
    async initialize(): Promise<void> {
        logger.info('🔧 [TASK-EXEC] Initializing task execution service');
        
        // Initialize evaluation service
        await this.taskEvaluationService.initialize();
        
        // Start execution processor
        this.startExecutionProcessor();
        
        logger.info('🔧 [TASK-EXEC] Task execution service ready');
    }
    
    async executeSubtask(subtask: SubTask): Promise<SubtaskResult> {
        logger.info('🚀 [TASK-EXEC] Starting subtask execution', {
            subtaskId: subtask.id.substring(0, 8),
            workType: subtask.workType,
            estimatedEffort: subtask.estimatedEffort
        });
        
        const startTime = new Date();
        
        // Update subtask status
        subtask.status = 'in_progress';
        subtask.startTime = startTime;
        
        // Track active execution
        this.activeExecutions.set(subtask.id, {
            subtask,
            startTime,
            progress: 0
        });
        
        try {
            // Execute based on work type
            const artifacts = await this.performWork(subtask);
            
            // Calculate actual effort
            const endTime = new Date();
            const actualEffort = (endTime.getTime() - startTime.getTime()) / (1000 * 60 * 60); // Hours
            
            // Update subtask
            subtask.status = 'completed';
            subtask.completionTime = endTime;
            subtask.actualEffort = actualEffort;
            subtask.artifacts = artifacts;
            
            // Evaluate the work
            const evaluation = await this.taskEvaluationService.evaluateTask(subtask.id, artifacts);
            
            // Update quality score
            subtask.qualityScore = evaluation.overallScore;
            subtask.evaluationHistory.push(evaluation);
            
            // Create result
            const result: SubtaskResult = {
                subtask,
                artifacts,
                evaluation,
                actualEffort,
                status: evaluation.overallScore >= 70 ? 'completed' : 'partial',
                startTime,
                endTime,
                resourcesUsed: {
                    cpuTime: actualEffort * 3600, // Seconds
                    memoryUsed: this.estimateMemoryUsage(artifacts),
                    apiCalls: this.countApiCalls(artifacts),
                    humanHours: 0 // Autonomous execution
                }
            };
            
            logger.info('✅ [TASK-EXEC] Subtask execution completed', {
                subtaskId: subtask.id.substring(0, 8),
                status: result.status,
                qualityScore: evaluation.overallScore,
                actualEffort: actualEffort.toFixed(2)
            });
            
            return result;
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Subtask execution failed', {
                subtaskId: subtask.id.substring(0, 8),
                error: error.message
            });
            
            // Update subtask status
            subtask.status = 'failed';
            
            // Create failure result
            const result: SubtaskResult = {
                subtask,
                artifacts: [],
                evaluation: null,
                actualEffort: (new Date().getTime() - startTime.getTime()) / (1000 * 60 * 60),
                status: 'failed',
                error: error.message,
                startTime,
                endTime: new Date(),
                resourcesUsed: {
                    cpuTime: 0,
                    memoryUsed: 0,
                    apiCalls: 0,
                    humanHours: 0
                }
            };
            
            return result;
            
        } finally {
            // Remove from active executions
            this.activeExecutions.delete(subtask.id);
        }
    }
    
    private async performWork(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('🔨 [TASK-EXEC] Performing work', {
            workType: subtask.workType,
            description: subtask.description.substring(0, 100)
        });
        
        const artifacts: TaskArtifact[] = [];
        
        switch (subtask.workType) {
            case 'research':
                artifacts.push(...(await this.performResearch(subtask)));
                break;
            case 'code':
                artifacts.push(...(await this.performCoding(subtask)));
                break;
            case 'analysis':
                artifacts.push(...(await this.performAnalysis(subtask)));
                break;
            case 'communication':
                artifacts.push(...(await this.performCommunication(subtask)));
                break;
            case 'decision':
                artifacts.push(...(await this.performDecision(subtask)));
                break;
            default:
                logger.warn('⚠️ [TASK-EXEC] Unknown work type, using generic approach', {
                    workType: subtask.workType
                });
                artifacts.push(...(await this.performGenericWork(subtask)));
        }
        
        // Add metadata to all artifacts
        for (const artifact of artifacts) {
            artifact.metadata.taskExecutionId = subtask.id;
            artifact.metadata.executionTimestamp = new Date().toISOString();
        }
        
        logger.debug('🔨 [TASK-EXEC] Work completed', {
            workType: subtask.workType,
            artifactsCreated: artifacts.length
        });
        
        return artifacts;
    }
    
    private async performResearch(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('🔍 [TASK-EXEC] Performing research work');
        
        // Use the research action from the autonomous system
        try {
            // Trigger research via the existing DO_RESEARCH action
            const researchPrompt = `Research topic: ${subtask.title}\nDescription: ${subtask.description}\nRequirements: ${subtask.requirements.map(r => r.description).join(', ')}`;
            
            // This would typically trigger the DO_RESEARCH action
            // For now, simulate research results
            const researchContent = await this.simulateResearchWork(subtask);
            
            const artifact: TaskArtifact = {
                id: uuidv4(),
                taskId: subtask.id,
                type: 'research_report',
                content: researchContent,
                metadata: {
                    sources: 5,
                    confidence: 85,
                    gaps: [],
                    format: 'markdown'
                },
                qualityMetrics: {
                    accuracy: 85,
                    completeness: 80,
                    clarity: 90,
                    usefulness: 85
                },
                createdAt: new Date(),
                updatedAt: new Date(),
                version: '1.0',
                relatedArtifacts: []
            };
            
            return [artifact];
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Research work failed', { error });
            throw error;
        }
    }
    
    private async performCoding(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('💻 [TASK-EXEC] Performing coding work');
        
        try {
            // Generate code based on subtask requirements
            const codeContent = await this.generateCode(subtask);
            
            const artifact: TaskArtifact = {
                id: uuidv4(),
                taskId: subtask.id,
                type: 'code',
                content: codeContent,
                metadata: {
                    language: this.detectLanguage(codeContent),
                    complexity: this.calculateCodeComplexity(codeContent),
                    testCoverage: 0, // Would be calculated by tests
                    format: 'typescript'
                },
                qualityMetrics: {
                    accuracy: 80,
                    completeness: 85,
                    clarity: 75,
                    usefulness: 90
                },
                createdAt: new Date(),
                updatedAt: new Date(),
                version: '1.0',
                relatedArtifacts: []
            };
            
            return [artifact];
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Coding work failed', { error });
            throw error;
        }
    }
    
    private async performAnalysis(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('📊 [TASK-EXEC] Performing analysis work');
        
        try {
            const analysisContent = await this.generateAnalysis(subtask);
            
            const artifact: TaskArtifact = {
                id: uuidv4(),
                taskId: subtask.id,
                type: 'analysis',
                content: analysisContent,
                metadata: {
                    format: 'structured_analysis',
                    confidence: 80
                },
                qualityMetrics: {
                    accuracy: 85,
                    completeness: 80,
                    clarity: 90,
                    usefulness: 85
                },
                createdAt: new Date(),
                updatedAt: new Date(),
                version: '1.0',
                relatedArtifacts: []
            };
            
            return [artifact];
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Analysis work failed', { error });
            throw error;
        }
    }
    
    private async performCommunication(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('💬 [TASK-EXEC] Performing communication work');
        
        try {
            // Use the VTuber communication capabilities
            const communicationContent = await this.generateCommunication(subtask);
            
            const artifact: TaskArtifact = {
                id: uuidv4(),
                taskId: subtask.id,
                type: 'communication',
                content: communicationContent,
                metadata: {
                    format: 'message',
                    audience: 'general'
                },
                qualityMetrics: {
                    accuracy: 90,
                    completeness: 85,
                    clarity: 95,
                    usefulness: 80
                },
                createdAt: new Date(),
                updatedAt: new Date(),
                version: '1.0',
                relatedArtifacts: []
            };
            
            return [artifact];
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Communication work failed', { error });
            throw error;
        }
    }
    
    private async performDecision(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('🎯 [TASK-EXEC] Performing decision work');
        
        try {
            const decisionContent = await this.generateDecision(subtask);
            
            const artifact: TaskArtifact = {
                id: uuidv4(),
                taskId: subtask.id,
                type: 'decision',
                content: decisionContent,
                metadata: {
                    format: 'structured_decision',
                    confidence: 75
                },
                qualityMetrics: {
                    accuracy: 80,
                    completeness: 85,
                    clarity: 90,
                    usefulness: 85
                },
                createdAt: new Date(),
                updatedAt: new Date(),
                version: '1.0',
                relatedArtifacts: []
            };
            
            return [artifact];
            
        } catch (error) {
            logger.error('❌ [TASK-EXEC] Decision work failed', { error });
            throw error;
        }
    }
    
    private async performGenericWork(subtask: SubTask): Promise<TaskArtifact[]> {
        logger.debug('📝 [TASK-EXEC] Performing generic work');
        
        const artifact: TaskArtifact = {
            id: uuidv4(),
            taskId: subtask.id,
            type: 'document',
            content: `Work completed for: ${subtask.title}\n\nDescription: ${subtask.description}\n\nThis work was completed autonomously as part of task execution.`,
            metadata: {
                format: 'markdown'
            },
            qualityMetrics: {
                accuracy: 70,
                completeness: 75,
                clarity: 80,
                usefulness: 70
            },
            createdAt: new Date(),
            updatedAt: new Date(),
            version: '1.0',
            relatedArtifacts: []
        };
        
        return [artifact];
    }
    
    // Simulation methods (would be replaced by actual AI-powered implementations)
    private async simulateResearchWork(subtask: SubTask): Promise<string> {
        return `# Research Report: ${subtask.title}

## Overview
This research was conducted to address: ${subtask.description}

## Key Findings
1. Research indicates positive potential for the proposed approach
2. Multiple implementation strategies are available
3. Best practices suggest following established patterns

## Methodology
- Literature review of relevant sources
- Analysis of current industry practices
- Evaluation of technical feasibility

## Recommendations
- Proceed with implementation following identified best practices
- Monitor progress and adjust approach as needed
- Consider alternative approaches if initial approach proves insufficient

## Confidence Level
This research has a confidence level of 85% based on available information and analysis depth.`;
    }
    
    private async generateCode(subtask: SubTask): Promise<string> {
        // This would use an AI code generator in practice
        return `// Generated code for: ${subtask.title}
// Description: ${subtask.description}

interface ${this.titleToInterfaceName(subtask.title)} {
    id: string;
    status: 'active' | 'completed' | 'failed';
    createdAt: Date;
}

export class ${this.titleToClassName(subtask.title)}Service {
    constructor() {
        console.log('Service initialized for: ${subtask.title}');
    }
    
    async execute(): Promise<boolean> {
        try {
            // Implementation would go here
            console.log('Executing: ${subtask.description}');
            return true;
        } catch (error) {
            console.error('Execution failed:', error);
            return false;
        }
    }
}`;
    }
    
    private async generateAnalysis(subtask: SubTask): Promise<string> {
        return `# Analysis: ${subtask.title}

## Objective
${subtask.description}

## Analysis Framework
- Current State Assessment
- Gap Analysis
- Risk Evaluation
- Opportunity Identification

## Key Insights
1. Current situation analysis reveals areas for improvement
2. Identified gaps provide clear targets for enhancement
3. Risk assessment indicates manageable challenges
4. Opportunities exist for significant value creation

## Recommendations
Based on the analysis, the following actions are recommended:
1. Address identified gaps through systematic approach
2. Implement risk mitigation strategies
3. Leverage identified opportunities for maximum impact

## Conclusion
The analysis indicates a positive outlook with clear action items for success.`;
    }
    
    private async generateCommunication(subtask: SubTask): Promise<string> {
        return `Subject: ${subtask.title}

Dear Team,

I wanted to update you on the progress of our current initiative: ${subtask.description}

Key points:
- Work is progressing according to plan
- All requirements are being addressed systematically
- Expected completion within estimated timeframe

Please let me know if you have any questions or need additional information.

Best regards,
Autonomous Task System`;
    }
    
    private async generateDecision(subtask: SubTask): Promise<string> {
        return `# Decision Record: ${subtask.title}

## Context
${subtask.description}

## Decision
Based on available information and analysis, the decision is to proceed with the planned approach.

## Rationale
- Aligns with project objectives
- Leverages available resources effectively
- Minimizes identified risks
- Maximizes potential for success

## Alternatives Considered
1. Alternative approach A - Rejected due to resource constraints
2. Alternative approach B - Rejected due to timeline limitations
3. Alternative approach C - Rejected due to complexity concerns

## Implementation Plan
1. Begin with preparation phase
2. Execute core activities
3. Monitor progress and adjust as needed
4. Complete with evaluation and documentation

## Decision Confidence
High confidence (80%) based on thorough analysis and consideration of alternatives.`;
    }
    
    // Utility methods
    private titleToInterfaceName(title: string): string {
        return title.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '') + 'Interface';
    }
    
    private titleToClassName(title: string): string {
        return title.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '');
    }
    
    private detectLanguage(code: string): string {
        if (code.includes('interface') || code.includes('export class')) {
            return 'typescript';
        }
        if (code.includes('def ') || code.includes('import ')) {
            return 'python';
        }
        return 'javascript';
    }
    
    private calculateCodeComplexity(code: string): number {
        // Simple complexity calculation based on keywords
        const complexityIndicators = ['if', 'for', 'while', 'switch', 'try', 'catch'];
        let complexity = 1; // Base complexity
        
        for (const indicator of complexityIndicators) {
            const matches = code.split(indicator).length - 1;
            complexity += matches;
        }
        
        return Math.min(10, complexity);
    }
    
    private estimateMemoryUsage(artifacts: TaskArtifact[]): number {
        // Estimate memory usage in MB
        const totalContent = artifacts.reduce((total, artifact) => total + artifact.content.length, 0);
        return Math.round(totalContent / 1024); // KB to MB approximation
    }
    
    private countApiCalls(artifacts: TaskArtifact[]): number {
        // Count estimated API calls based on artifact types
        let apiCalls = 0;
        
        for (const artifact of artifacts) {
            switch (artifact.type) {
                case 'research_report':
                    apiCalls += 5; // Research typically involves multiple API calls
                    break;
                case 'code':
                    apiCalls += 2; // Code generation
                    break;
                case 'analysis':
                    apiCalls += 3; // Analysis processing
                    break;
                default:
                    apiCalls += 1; // Default
            }
        }
        
        return apiCalls;
    }
    
    private startExecutionProcessor(): void {
        // Process execution queue every 10 seconds
        setInterval(async () => {
            if (this.executionQueue.size === 0) return;
            if (this.activeExecutions.size >= this.maxConcurrentExecutions) return;
            
            logger.debug('🔄 [TASK-EXEC] Processing execution queue', {
                queueSize: this.executionQueue.size,
                activeExecutions: this.activeExecutions.size
            });
            
            // Get next subtask from queue
            const [subtaskId, subtask] = Array.from(this.executionQueue.entries())[0];
            this.executionQueue.delete(subtaskId);
            
            // Execute in background
            this.executeSubtask(subtask).catch(error => {
                logger.error('❌ [TASK-EXEC] Background execution failed', {
                    subtaskId: subtaskId.substring(0, 8),
                    error
                });
            });
        }, 10000);
    }
    
    // Public interface methods
    async queueSubtask(subtask: SubTask): Promise<TaskOperationResult> {
        this.executionQueue.set(subtask.id, subtask);
        
        logger.info('📋 [TASK-EXEC] Subtask queued for execution', {
            subtaskId: subtask.id.substring(0, 8),
            workType: subtask.workType,
            queueSize: this.executionQueue.size
        });
        
        return {
            success: true,
            taskId: subtask.id,
            operation: 'queue_subtask',
            message: `Subtask queued for execution`,
            timestamp: new Date()
        };
    }
    
    async getExecutionStatus(subtaskId: string): Promise<{
        status: string;
        progress: number;
        startTime?: Date;
        estimatedCompletion?: Date;
    }> {
        if (this.activeExecutions.has(subtaskId)) {
            const execution = this.activeExecutions.get(subtaskId)!;
            const elapsed = Date.now() - execution.startTime.getTime();
            const estimatedTotal = execution.subtask.estimatedEffort * 60 * 60 * 1000; // Convert hours to ms
            const progress = Math.min(100, (elapsed / estimatedTotal) * 100);
            
            return {
                status: 'executing',
                progress: Math.round(progress),
                startTime: execution.startTime,
                estimatedCompletion: new Date(execution.startTime.getTime() + estimatedTotal)
            };
        }
        
        if (this.executionQueue.has(subtaskId)) {
            return {
                status: 'queued',
                progress: 0
            };
        }
        
        return {
            status: 'unknown',
            progress: 0
        };
    }
    
    getExecutionStats(): {
        queueSize: number;
        activeExecutions: number;
        maxConcurrentExecutions: number;
        totalCompleted: number;
    } {
        return {
            queueSize: this.executionQueue.size,
            activeExecutions: this.activeExecutions.size,
            maxConcurrentExecutions: this.maxConcurrentExecutions,
            totalCompleted: 0 // Would track this in practice
        };
    }
} 