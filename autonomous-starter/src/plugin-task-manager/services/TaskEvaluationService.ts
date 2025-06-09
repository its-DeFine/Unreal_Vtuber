import { IAgentRuntime, Service, logger, ServiceTypeName } from '@elizaos/core';
import { 
    TaskEvaluation, 
    TaskArtifact, 
    EvaluationRequest, 
    PendingEvaluation,
    SuccessMetric,
    SubTask,
    CentralTask 
} from '../types/TaskStructure';
import { v4 as uuidv4 } from 'uuid';

export class TaskEvaluationService extends Service {
    static serviceType: ServiceTypeName = 'TASK_EVALUATION' as ServiceTypeName;
    
    private evaluationQueue: Map<string, PendingEvaluation> = new Map();
    private evaluationHistory: TaskEvaluation[] = [];
    private evaluationInProgress: Set<string> = new Set();
    
    constructor(runtime: IAgentRuntime) {
        super(runtime);
        logger.info('📊 [TASK-EVAL] Service initialized');
    }
    
    async initialize(): Promise<void> {
        logger.info('📊 [TASK-EVAL] Initializing task evaluation service');
        
        // Start evaluation queue processor
        this.startEvaluationProcessor();
        
        logger.info('📊 [TASK-EVAL] Task evaluation service ready');
    }
    
    async evaluateTask(taskId: string, workArtifacts: TaskArtifact[]): Promise<TaskEvaluation> {
        logger.info('🔍 [TASK-EVAL] Starting task evaluation', { 
            taskId: taskId.substring(0, 8),
            artifactsCount: workArtifacts.length 
        });
        
        if (this.evaluationInProgress.has(taskId)) {
            logger.warn('⚠️ [TASK-EVAL] Evaluation already in progress for task', { taskId });
            throw new Error(`Evaluation already in progress for task ${taskId}`);
        }
        
        this.evaluationInProgress.add(taskId);
        
        try {
            // Get evaluation criteria for this task
            const evaluationCriteria = await this.getEvaluationCriteria(taskId);
            
            // Multi-dimensional evaluation
            const evaluation = await this.performComprehensiveEvaluation({
                taskId,
                artifacts: workArtifacts,
                evaluationCriteria
            });
            
            // Store evaluation in knowledge graph via Cognee
            await this.storeEvaluationKnowledge(evaluation);
            
            // Update task status and trigger next actions
            await this.updateTaskBasedOnEvaluation(taskId, evaluation);
            
            // Add to history
            this.evaluationHistory.push(evaluation);
            
            // Keep history manageable (last 1000 evaluations)
            if (this.evaluationHistory.length > 1000) {
                this.evaluationHistory = this.evaluationHistory.slice(-1000);
            }
            
            logger.info('✅ [TASK-EVAL] Evaluation completed', {
                taskId: taskId.substring(0, 8),
                overallScore: evaluation.overallScore,
                confidence: evaluation.confidence,
                nextActions: evaluation.nextActions.length
            });
            
            return evaluation;
            
        } catch (error) {
            logger.error('❌ [TASK-EVAL] Evaluation failed', { 
                taskId: taskId.substring(0, 8), 
                error: error.message 
            });
            throw error;
        } finally {
            this.evaluationInProgress.delete(taskId);
        }
    }
    
    private async performComprehensiveEvaluation({
        taskId,
        artifacts,
        evaluationCriteria
    }: EvaluationRequest): Promise<TaskEvaluation> {
        logger.debug('🔬 [TASK-EVAL] Performing comprehensive evaluation', {
            taskId: taskId.substring(0, 8),
            criteriaCount: evaluationCriteria.length
        });
        
        // 1. Completeness Analysis
        const completeness = await this.evaluateCompleteness(artifacts, evaluationCriteria);
        
        // 2. Quality Assessment  
        const quality = await this.evaluateQuality(artifacts);
        
        // 3. Efficiency Analysis
        const efficiency = await this.evaluateEfficiency(taskId, artifacts);
        
        // 4. Innovation Scoring
        const innovation = await this.evaluateInnovation(artifacts);
        
        // 5. Calculate overall score
        const overallScore = this.calculateOverallScore({
            completeness, quality, efficiency, innovation
        });
        
        // 6. Generate feedback and improvements
        const feedback = await this.generateDetailedFeedback({
            completeness, quality, efficiency, innovation, artifacts
        });
        
        // 7. Create evaluation record
        const evaluation: TaskEvaluation = {
            id: uuidv4(),
            taskId,
            timestamp: new Date(),
            evaluator: 'ai',
            scoreBreakdown: { completeness, quality, efficiency, innovation },
            overallScore,
            feedback: feedback.summary,
            improvements: feedback.improvements,
            nextActions: feedback.nextActions,
            evaluationContext: {
                timeSpent: this.calculateTimeSpent(artifacts),
                resourcesUsed: this.extractResourcesUsed(artifacts),
                challenges: feedback.challenges,
                successes: feedback.successes
            },
            confidence: this.calculateConfidence({ completeness, quality, efficiency, innovation }),
            metadata: {
                artifactTypes: artifacts.map(a => a.type),
                evaluationMethod: 'automated_comprehensive',
                version: '1.0'
            }
        };
        
        return evaluation;
    }
    
    private async evaluateCompleteness(artifacts: TaskArtifact[], criteria: SuccessMetric[]): Promise<number> {
        logger.debug('📋 [TASK-EVAL] Evaluating completeness');
        
        if (criteria.length === 0) {
            // Fallback: basic artifact-based completeness
            return Math.min(100, artifacts.length * 25); // Up to 4 artifacts = 100%
        }
        
        let totalWeight = 0;
        let achievedWeight = 0;
        
        for (const metric of criteria) {
            totalWeight += metric.weight;
            
            // Check if this metric is satisfied by the artifacts
            const satisfaction = await this.checkMetricSatisfaction(metric, artifacts);
            if (satisfaction >= 0.8) { // 80% threshold for completion
                achievedWeight += metric.weight;
            } else if (satisfaction >= 0.5) {
                achievedWeight += metric.weight * 0.6; // Partial credit
            }
        }
        
        const completenessScore = totalWeight > 0 ? (achievedWeight / totalWeight) * 100 : 50;
        
        logger.debug('📋 [TASK-EVAL] Completeness score calculated', { 
            score: completenessScore,
            criteriaChecked: criteria.length 
        });
        
        return Math.round(completenessScore);
    }
    
    private async evaluateQuality(artifacts: TaskArtifact[]): Promise<number> {
        logger.debug('💎 [TASK-EVAL] Evaluating quality');
        
        let totalScore = 0;
        let artifactCount = 0;
        
        for (const artifact of artifacts) {
            let artifactQuality = 0;
            
            // Quality assessment based on artifact type
            switch (artifact.type) {
                case 'code':
                    artifactQuality = await this.evaluateCodeQuality(artifact);
                    break;
                case 'research_report':
                    artifactQuality = await this.evaluateResearchQuality(artifact);
                    break;
                case 'analysis':
                    artifactQuality = await this.evaluateAnalysisQuality(artifact);
                    break;
                case 'document':
                    artifactQuality = await this.evaluateDocumentQuality(artifact);
                    break;
                case 'decision':
                    artifactQuality = await this.evaluateDecisionQuality(artifact);
                    break;
                case 'communication':
                    artifactQuality = await this.evaluateCommunicationQuality(artifact);
                    break;
                default:
                    artifactQuality = await this.evaluateGenericQuality(artifact);
            }
            
            totalScore += artifactQuality;
            artifactCount++;
        }
        
        const qualityScore = artifactCount > 0 ? totalScore / artifactCount : 0;
        
        logger.debug('💎 [TASK-EVAL] Quality score calculated', { 
            score: qualityScore,
            artifactsEvaluated: artifactCount 
        });
        
        return Math.round(qualityScore);
    }
    
    private async evaluateEfficiency(taskId: string, artifacts: TaskArtifact[]): Promise<number> {
        logger.debug('⚡ [TASK-EVAL] Evaluating efficiency');
        
        // Get task timing information
        const task = await this.getTaskById(taskId);
        if (!task) {
            logger.warn('⚠️ [TASK-EVAL] Could not find task for efficiency evaluation');
            return 70; // Default efficiency score
        }
        
        const actualTime = this.calculateTimeSpent(artifacts);
        const estimatedTime = this.getEstimatedTime(task);
        
        let efficiencyScore = 70; // Base score
        
        // Time efficiency
        if (estimatedTime > 0) {
            const timeRatio = actualTime / estimatedTime;
            if (timeRatio <= 0.8) {
                efficiencyScore += 20; // Completed faster than expected
            } else if (timeRatio <= 1.2) {
                efficiencyScore += 10; // Completed within reasonable timeframe
            } else if (timeRatio <= 2.0) {
                efficiencyScore -= 10; // Took longer than expected
            } else {
                efficiencyScore -= 20; // Significantly over time
            }
        }
        
        // Resource efficiency
        const resourceEfficiency = await this.evaluateResourceEfficiency(artifacts);
        efficiencyScore = (efficiencyScore + resourceEfficiency) / 2;
        
        logger.debug('⚡ [TASK-EVAL] Efficiency score calculated', { 
            score: efficiencyScore,
            timeRatio: estimatedTime > 0 ? actualTime / estimatedTime : 'N/A'
        });
        
        return Math.round(Math.max(0, Math.min(100, efficiencyScore)));
    }
    
    private async evaluateInnovation(artifacts: TaskArtifact[]): Promise<number> {
        logger.debug('💡 [TASK-EVAL] Evaluating innovation');
        
        let innovationScore = 0;
        let artifactCount = 0;
        
        for (const artifact of artifacts) {
            let artifactInnovation = 50; // Base innovation score
            
            // Check for innovative elements
            const content = artifact.content.toLowerCase();
            
            // Novel approaches indicators
            const noveltyIndicators = [
                'new approach', 'innovative', 'novel', 'creative', 'breakthrough',
                'unique', 'original', 'pioneering', 'cutting-edge', 'revolutionary'
            ];
            
            let noveltyCount = 0;
            for (const indicator of noveltyIndicators) {
                if (content.includes(indicator)) {
                    noveltyCount++;
                }
            }
            
            artifactInnovation += noveltyCount * 5;
            
            // Technical innovation indicators
            if (artifact.type === 'code') {
                if (artifact.metadata.evolutionHistory && artifact.metadata.evolutionHistory.length > 0) {
                    artifactInnovation += 15; // Self-improving code
                }
                if (artifact.metadata.complexity && artifact.metadata.complexity > 7) {
                    artifactInnovation += 10; // Complex solution
                }
            }
            
            // Cross-domain connections
            if (artifact.relatedArtifacts.length > 2) {
                artifactInnovation += 10; // Connects multiple concepts
            }
            
            innovationScore += artifactInnovation;
            artifactCount++;
        }
        
        const finalInnovationScore = artifactCount > 0 ? innovationScore / artifactCount : 50;
        
        logger.debug('💡 [TASK-EVAL] Innovation score calculated', { 
            score: finalInnovationScore,
            artifactsEvaluated: artifactCount 
        });
        
        return Math.round(Math.max(0, Math.min(100, finalInnovationScore)));
    }
    
    private calculateOverallScore(scores: {
        completeness: number;
        quality: number;
        efficiency: number;
        innovation: number;
    }): number {
        // Weighted average - completeness and quality are most important
        const weights = {
            completeness: 0.35,
            quality: 0.35,
            efficiency: 0.20,
            innovation: 0.10
        };
        
        const overall = (
            scores.completeness * weights.completeness +
            scores.quality * weights.quality +
            scores.efficiency * weights.efficiency +
            scores.innovation * weights.innovation
        );
        
        return Math.round(overall);
    }
    
    private async generateDetailedFeedback(params: {
        completeness: number;
        quality: number;
        efficiency: number;
        innovation: number;
        artifacts: TaskArtifact[];
    }): Promise<{
        summary: string;
        improvements: string[];
        nextActions: string[];
        challenges: string[];
        successes: string[];
    }> {
        const { completeness, quality, efficiency, innovation, artifacts } = params;
        
        let summary = `Task evaluation completed. `;
        const improvements: string[] = [];
        const nextActions: string[] = [];
        const challenges: string[] = [];
        const successes: string[] = [];
        
        // Overall assessment
        const overall = this.calculateOverallScore({ completeness, quality, efficiency, innovation });
        
        if (overall >= 90) {
            summary += `Excellent work with outstanding results (${overall}/100).`;
            successes.push('Exceptional performance across all evaluation dimensions');
        } else if (overall >= 80) {
            summary += `Very good work with strong results (${overall}/100).`;
            successes.push('Strong performance with minor areas for enhancement');
        } else if (overall >= 70) {
            summary += `Good work with satisfactory results (${overall}/100).`;
            challenges.push('Some areas need improvement to reach higher performance');
        } else if (overall >= 60) {
            summary += `Acceptable work but with room for improvement (${overall}/100).`;
            challenges.push('Several areas require attention for better outcomes');
        } else {
            summary += `Work needs significant improvement (${overall}/100).`;
            challenges.push('Major improvements needed across multiple dimensions');
        }
        
        // Specific feedback for each dimension
        if (completeness < 80) {
            improvements.push(`Improve task completeness (${completeness}/100) - ensure all requirements are fully addressed`);
            nextActions.push('Review task requirements and complete missing elements');
        } else {
            successes.push(`Good task completeness (${completeness}/100)`);
        }
        
        if (quality < 80) {
            improvements.push(`Enhance work quality (${quality}/100) - focus on accuracy, clarity, and thoroughness`);
            nextActions.push('Review and refine work quality standards');
        } else {
            successes.push(`High work quality (${quality}/100)`);
        }
        
        if (efficiency < 70) {
            improvements.push(`Improve efficiency (${efficiency}/100) - optimize time and resource usage`);
            nextActions.push('Analyze workflow and identify optimization opportunities');
        } else {
            successes.push(`Good efficiency (${efficiency}/100)`);
        }
        
        if (innovation < 60) {
            improvements.push(`Increase innovation (${innovation}/100) - explore creative and novel approaches`);
            nextActions.push('Research alternative approaches and creative solutions');
        } else {
            successes.push(`Good innovation level (${innovation}/100)`);
        }
        
        // Artifact-specific feedback
        if (artifacts.length === 0) {
            challenges.push('No artifacts produced - unable to assess concrete deliverables');
            nextActions.push('Ensure work produces tangible artifacts and deliverables');
        }
        
        return {
            summary,
            improvements,
            nextActions,
            challenges,
            successes
        };
    }
    
    // Helper methods for specific quality evaluations
    private async evaluateCodeQuality(artifact: TaskArtifact): Promise<number> {
        let score = 70; // Base score
        
        const codeLength = artifact.content.length;
        const metadata = artifact.metadata;
        
        // Test coverage bonus
        if (metadata.testCoverage && metadata.testCoverage > 80) {
            score += 15;
        } else if (metadata.testCoverage && metadata.testCoverage > 60) {
            score += 10;
        }
        
        // Complexity assessment
        if (metadata.complexity) {
            if (metadata.complexity <= 5) {
                score += 5; // Appropriate complexity
            } else if (metadata.complexity > 8) {
                score -= 5; // Overly complex
            }
        }
        
        // Code length assessment
        if (codeLength > 100 && codeLength < 1000) {
            score += 5; // Good length
        } else if (codeLength > 5000) {
            score -= 5; // May be too long
        }
        
        return Math.max(0, Math.min(100, score));
    }
    
    private async evaluateResearchQuality(artifact: TaskArtifact): Promise<number> {
        let score = 70; // Base score
        
        const content = artifact.content;
        const metadata = artifact.metadata;
        
        // Source count bonus
        if (metadata.sources && metadata.sources > 5) {
            score += 15;
        } else if (metadata.sources && metadata.sources > 2) {
            score += 10;
        }
        
        // Confidence level
        if (metadata.confidence && metadata.confidence > 80) {
            score += 10;
        }
        
        // Content depth (length as proxy)
        if (content.length > 1000) {
            score += 10;
        }
        
        // Gap identification (shows thoroughness)
        if (metadata.gaps && metadata.gaps.length > 0) {
            score += 5; // Identified research gaps
        }
        
        return Math.max(0, Math.min(100, score));
    }
    
    private async evaluateAnalysisQuality(artifact: TaskArtifact): Promise<number> {
        let score = 70; // Base score
        
        const content = artifact.content.toLowerCase();
        
        // Look for analytical depth indicators
        const analyticalKeywords = [
            'analysis', 'conclusion', 'recommendation', 'insight', 'pattern',
            'trend', 'correlation', 'implication', 'significance', 'evidence'
        ];
        
        let keywordCount = 0;
        for (const keyword of analyticalKeywords) {
            if (content.includes(keyword)) {
                keywordCount++;
            }
        }
        
        score += Math.min(20, keywordCount * 2);
        
        // Content structure
        if (content.includes('summary') || content.includes('conclusion')) {
            score += 10;
        }
        
        return Math.max(0, Math.min(100, score));
    }
    
    private async evaluateDocumentQuality(artifact: TaskArtifact): Promise<number> {
        const qualityMetrics = artifact.qualityMetrics;
        
        if (qualityMetrics) {
            return Math.round((
                qualityMetrics.accuracy +
                qualityMetrics.completeness +
                qualityMetrics.clarity +
                qualityMetrics.usefulness
            ) / 4);
        }
        
        // Fallback assessment
        return 70;
    }
    
    private async evaluateDecisionQuality(artifact: TaskArtifact): Promise<number> {
        let score = 70;
        
        const content = artifact.content.toLowerCase();
        
        // Look for decision-making indicators
        if (content.includes('rationale') || content.includes('reasoning')) {
            score += 15;
        }
        
        if (content.includes('alternatives') || content.includes('options')) {
            score += 10;
        }
        
        if (content.includes('risk') || content.includes('consequence')) {
            score += 10;
        }
        
        return Math.max(0, Math.min(100, score));
    }
    
    private async evaluateCommunicationQuality(artifact: TaskArtifact): Promise<number> {
        let score = 70;
        
        const content = artifact.content;
        
        // Length appropriateness
        if (content.length > 100 && content.length < 2000) {
            score += 10;
        }
        
        // Professional language indicators
        const professionalIndicators = ['please', 'thank you', 'regards', 'sincerely'];
        for (const indicator of professionalIndicators) {
            if (content.toLowerCase().includes(indicator)) {
                score += 5;
                break;
            }
        }
        
        return Math.max(0, Math.min(100, score));
    }
    
    private async evaluateGenericQuality(artifact: TaskArtifact): Promise<number> {
        // Use quality metrics if available
        if (artifact.qualityMetrics) {
            return Math.round((
                artifact.qualityMetrics.accuracy +
                artifact.qualityMetrics.completeness +
                artifact.qualityMetrics.clarity +
                artifact.qualityMetrics.usefulness
            ) / 4);
        }
        
        // Basic assessment based on content length and structure
        let score = 70;
        
        if (artifact.content.length > 100) {
            score += 10;
        }
        
        if (artifact.content.length > 500) {
            score += 10;
        }
        
        return score;
    }
    
    // Utility methods
    private async getEvaluationCriteria(taskId: string): Promise<SuccessMetric[]> {
        try {
            const task = await this.getTaskById(taskId);
            return task?.successMetrics || [];
        } catch (error) {
            logger.warn('⚠️ [TASK-EVAL] Could not get evaluation criteria', { 
                taskId: taskId.substring(0, 8) 
            });
            return [];
        }
    }
    
    private async getTaskById(taskId: string): Promise<CentralTask | null> {
        // This would typically query the task storage system
        // For now, return null as placeholder
        return null;
    }
    
    private calculateTimeSpent(artifacts: TaskArtifact[]): number {
        // Calculate time based on artifact timestamps
        if (artifacts.length === 0) return 0;
        
        const timestamps = artifacts.map(a => a.createdAt.getTime());
        const earliest = Math.min(...timestamps);
        const latest = Math.max(...timestamps);
        
        return (latest - earliest) / (1000 * 60 * 60); // Hours
    }
    
    private getEstimatedTime(task: CentralTask): number {
        // Sum estimated effort from subtasks
        return task.subtasks.reduce((total, subtask) => total + subtask.estimatedEffort, 0);
    }
    
    private extractResourcesUsed(artifacts: TaskArtifact[]): string[] {
        const resources = new Set<string>();
        
        for (const artifact of artifacts) {
            if (artifact.metadata.language) {
                resources.add(`Language: ${artifact.metadata.language}`);
            }
            if (artifact.metadata.format) {
                resources.add(`Format: ${artifact.metadata.format}`);
            }
            // Add more resource extraction logic as needed
        }
        
        return Array.from(resources);
    }
    
    private async evaluateResourceEfficiency(artifacts: TaskArtifact[]): Promise<number> {
        // Placeholder implementation
        return 75;
    }
    
    private async checkMetricSatisfaction(metric: SuccessMetric, artifacts: TaskArtifact[]): Promise<number> {
        // Placeholder implementation - would analyze artifacts against metric criteria
        return 0.8; // 80% satisfaction
    }
    
    private calculateConfidence(scores: {
        completeness: number;
        quality: number;
        efficiency: number;
        innovation: number;
    }): number {
        // Higher scores generally indicate higher confidence
        const average = (scores.completeness + scores.quality + scores.efficiency + scores.innovation) / 4;
        
        // Convert to confidence scale
        if (average >= 90) return 95;
        if (average >= 80) return 85;
        if (average >= 70) return 75;
        if (average >= 60) return 65;
        return 50;
    }
    
    private async storeEvaluationKnowledge(evaluation: TaskEvaluation): Promise<void> {
        try {
            // Store evaluation insights in Cognee knowledge graph
            const cogneeService = this.runtime.getService('COGNEE');
            if (cogneeService) {
                const knowledgeText = `Task evaluation: ${evaluation.taskId} scored ${evaluation.overallScore}/100. 
                                     Completeness: ${evaluation.scoreBreakdown.completeness}/100, 
                                     Quality: ${evaluation.scoreBreakdown.quality}/100, 
                                     Efficiency: ${evaluation.scoreBreakdown.efficiency}/100, 
                                     Innovation: ${evaluation.scoreBreakdown.innovation}/100. 
                                     Feedback: ${evaluation.feedback}`;
                
                await cogneeService.addMemory(knowledgeText, 'task_evaluations');
                
                logger.debug('📚 [TASK-EVAL] Evaluation stored in knowledge graph');
            }
        } catch (error) {
            logger.warn('⚠️ [TASK-EVAL] Failed to store evaluation in knowledge graph', { error });
        }
    }
    
    private async updateTaskBasedOnEvaluation(taskId: string, evaluation: TaskEvaluation): Promise<void> {
        try {
            // Update task status based on evaluation results
            if (evaluation.overallScore >= 80) {
                logger.info('✅ [TASK-EVAL] Task marked as successfully completed', { 
                    taskId: taskId.substring(0, 8),
                    score: evaluation.overallScore 
                });
            } else if (evaluation.overallScore >= 60) {
                logger.info('⚠️ [TASK-EVAL] Task completed with room for improvement', { 
                    taskId: taskId.substring(0, 8),
                    score: evaluation.overallScore 
                });
            } else {
                logger.warn('❌ [TASK-EVAL] Task requires significant improvement', { 
                    taskId: taskId.substring(0, 8),
                    score: evaluation.overallScore 
                });
            }
        } catch (error) {
            logger.error('❌ [TASK-EVAL] Failed to update task status', { error });
        }
    }
    
    private startEvaluationProcessor(): void {
        // Process evaluation queue every 30 seconds
        setInterval(async () => {
            if (this.evaluationQueue.size === 0) return;
            
            logger.debug('🔄 [TASK-EVAL] Processing evaluation queue', { 
                queueSize: this.evaluationQueue.size 
            });
            
            // Process one evaluation from queue
            const [taskId, pendingEval] = Array.from(this.evaluationQueue.entries())[0];
            this.evaluationQueue.delete(taskId);
            
            try {
                await this.evaluateTask(taskId, pendingEval.artifacts);
            } catch (error) {
                logger.error('❌ [TASK-EVAL] Queue processing failed', { 
                    taskId: taskId.substring(0, 8), 
                    error 
                });
            }
        }, 30000);
    }
    
    // Public interface methods
    async queueEvaluation(taskId: string, artifacts: TaskArtifact[], priority: number = 5): Promise<void> {
        const pendingEval: PendingEvaluation = {
            taskId,
            requestTime: new Date(),
            priority,
            artifacts,
            context: {}
        };
        
        this.evaluationQueue.set(taskId, pendingEval);
        
        logger.info('📋 [TASK-EVAL] Evaluation queued', { 
            taskId: taskId.substring(0, 8),
            priority,
            queueSize: this.evaluationQueue.size 
        });
    }
    
    async getEvaluationHistory(taskId?: string, limit: number = 10): Promise<TaskEvaluation[]> {
        let history = this.evaluationHistory;
        
        if (taskId) {
            history = history.filter(eval => eval.taskId === taskId);
        }
        
        return history.slice(-limit);
    }
    
    getEvaluationStats(): {
        totalEvaluations: number;
        averageScore: number;
        queueSize: number;
        evaluationsInProgress: number;
    } {
        const totalEvaluations = this.evaluationHistory.length;
        const averageScore = totalEvaluations > 0 
            ? this.evaluationHistory.reduce((sum, eval) => sum + eval.overallScore, 0) / totalEvaluations 
            : 0;
        
        return {
            totalEvaluations,
            averageScore: Math.round(averageScore),
            queueSize: this.evaluationQueue.size,
            evaluationsInProgress: this.evaluationInProgress.size
        };
    }
} 