export interface CentralTask {
    id: string;
    title: string;
    description: string;
    objective: string; // Open-ended goal
    status: 'active' | 'paused' | 'completed' | 'failed';
    priority: 1 | 2 | 3 | 4 | 5;
    
    // Evaluation criteria
    successMetrics: SuccessMetric[];
    evaluationFrequency: 'realtime' | 'hourly' | 'daily';
    
    // Task hierarchy  
    subtasks: SubTask[];
    dependencies: string[];
    
    // Progress tracking
    startTime: Date;
    lastEvaluation: Date;
    progressScore: number; // 0-100
    
    // Context and constraints
    context: TaskContext;
    constraints: TaskConstraint[];
    
    // Metadata
    createdBy: string;
    assignedAgent: string;
    tags: string[];
    metadata: Record<string, any>;
}

export interface SubTask {
    id: string;
    parentId: string;
    title: string;
    description: string;
    
    // Work specification
    workType: 'research' | 'code' | 'analysis' | 'communication' | 'decision';
    estimatedEffort: number; // hours
    actualEffort?: number;
    
    // Evaluation
    status: 'pending' | 'in_progress' | 'completed' | 'blocked' | 'failed';
    qualityScore?: number; // 0-100
    evaluationHistory: TaskEvaluation[];
    
    // Execution details
    assignedAgent?: string;
    startTime?: Date;
    completionTime?: Date;
    artifacts: TaskArtifact[]; // Code, documents, decisions
    
    // Dependencies and requirements
    dependencies: string[];
    requirements: TaskRequirement[];
    
    // Context
    context: Record<string, any>;
}

export interface TaskEvaluation {
    id: string;
    taskId: string;
    timestamp: Date;
    evaluator: 'ai' | 'human' | 'automated';
    
    scoreBreakdown: {
        completeness: number;    // 0-100
        quality: number;         // 0-100  
        efficiency: number;      // 0-100
        innovation: number;      // 0-100
    };
    
    overallScore: number; // 0-100
    feedback: string;
    improvements: string[];
    nextActions: string[];
    
    // Context
    evaluationContext: {
        timeSpent: number;
        resourcesUsed: string[];
        challenges: string[];
        successes: string[];
    };
    
    // Metadata
    confidence: number; // 0-100
    metadata: Record<string, any>;
}

export interface TaskArtifact {
    id: string;
    taskId: string;
    type: 'code' | 'document' | 'research_report' | 'analysis' | 'decision' | 'communication';
    
    content: string;
    metadata: {
        language?: string;
        format?: string;
        size?: number;
        complexity?: number;
        testCoverage?: number;
        confidence?: number;
        sources?: number;
        gaps?: string[];
        evolutionHistory?: string[];
        [key: string]: any;
    };
    
    // Quality metrics
    qualityMetrics: {
        accuracy: number;
        completeness: number;
        clarity: number;
        usefulness: number;
    };
    
    // Lifecycle
    createdAt: Date;
    updatedAt: Date;
    version: string;
    
    // Relationships
    relatedArtifacts: string[];
    derivedFrom?: string[];
}

export interface SuccessMetric {
    id: string;
    name: string;
    description: string;
    type: 'numeric' | 'boolean' | 'qualitative';
    
    target: {
        value: any;
        operator: 'equals' | 'greater_than' | 'less_than' | 'contains' | 'matches';
        tolerance?: number;
    };
    
    current?: {
        value: any;
        measuredAt: Date;
        confidence: number;
    };
    
    measurement: {
        method: 'automated' | 'manual' | 'hybrid';
        frequency: string;
        source: string;
    };
    
    weight: number; // Importance weight 0-1
    status: 'not_started' | 'in_progress' | 'achieved' | 'failed';
}

export interface TaskContext {
    // Environment
    environment: 'development' | 'staging' | 'production';
    timeframe: {
        start: Date;
        deadline?: Date;
        milestones: Array<{
            name: string;
            date: Date;
            description: string;
        }>;
    };
    
    // Resources
    resources: {
        budgetLimit?: number;
        timeLimit?: number;
        computeLimit?: number;
        humanResourcesNeeded?: string[];
        toolsRequired?: string[];
    };
    
    // Stakeholders
    stakeholders: Array<{
        id: string;
        role: string;
        involvement: 'decision_maker' | 'contributor' | 'observer';
        contactInfo?: string;
    }>;
    
    // Domain context
    domain: string;
    relatedProjects: string[];
    businessValue: string;
    riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

export interface TaskConstraint {
    id: string;
    type: 'resource' | 'time' | 'quality' | 'scope' | 'regulatory' | 'technical';
    description: string;
    
    constraint: {
        field: string;
        operator: 'max' | 'min' | 'equals' | 'excludes' | 'requires';
        value: any;
        unit?: string;
    };
    
    severity: 'hard' | 'soft'; // Hard = must comply, Soft = should comply
    priority: number; // 1-10
    
    validation: {
        method: string;
        checkFrequency: string;
        lastChecked?: Date;
        status: 'compliant' | 'violation' | 'unknown';
    };
}

export interface TaskRequirement {
    id: string;
    type: 'functional' | 'non_functional' | 'technical' | 'business';
    description: string;
    acceptance_criteria: string[];
    
    priority: 'must_have' | 'should_have' | 'could_have' | 'wont_have';
    status: 'defined' | 'in_progress' | 'completed' | 'blocked';
    
    verification: {
        method: 'test' | 'review' | 'demo' | 'analysis';
        criteria: string;
        assignee?: string;
    };
    
    traceability: {
        source: string;
        relatedRequirements: string[];
        testCases: string[];
    };
}

// Execution types
export interface SubtaskResult {
    subtask: SubTask;
    artifacts: TaskArtifact[];
    evaluation: TaskEvaluation | null;
    actualEffort: number;
    status: 'completed' | 'failed' | 'partial';
    error?: string;
    
    // Performance metrics
    startTime: Date;
    endTime: Date;
    resourcesUsed: {
        cpuTime?: number;
        memoryUsed?: number;
        apiCalls?: number;
        humanHours?: number;
    };
}

export interface EvaluationRequest {
    taskId: string;
    artifacts: TaskArtifact[];
    evaluationCriteria: SuccessMetric[];
    context?: Record<string, any>;
}

export interface PendingEvaluation {
    taskId: string;
    requestTime: Date;
    priority: number;
    artifacts: TaskArtifact[];
    context: Record<string, any>;
}

// Response types for task operations
export interface TaskOperationResult {
    success: boolean;
    taskId: string;
    operation: string;
    message: string;
    data?: any;
    error?: string;
    timestamp: Date;
}

export interface TaskQueryResult {
    tasks: CentralTask[];
    totalCount: number;
    filteredCount: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
}

// Event types for task lifecycle
export interface TaskEvent {
    id: string;
    taskId: string;
    eventType: 'created' | 'updated' | 'completed' | 'failed' | 'paused' | 'resumed' | 'evaluated';
    timestamp: Date;
    actor: string; // Agent or user who triggered the event
    data: Record<string, any>;
    description: string;
} 