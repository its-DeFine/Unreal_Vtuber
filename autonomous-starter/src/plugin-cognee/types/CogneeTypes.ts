export interface CogneeConfig {
    url: string;
    apiKey: string;
    timeout: number;
    retryAttempts: number;
}

export interface CogneeMemoryEntry {
    id: string;
    content: string;
    type: 'conversation' | 'knowledge' | 'experience' | 'insight';
    timestamp: Date;
    metadata: {
        source: string;
        confidence: number;
        entities: string[];
        relationships: string[];
        context: Record<string, any>;
    };
}

export interface CogneeSearchResult {
    id: string;
    content: string;
    relevanceScore: number;
    entities: CogneeEntity[];
    relationships: CogneeRelationship[];
    metadata: Record<string, any>;
}

export interface CogneeEntity {
    id: string;
    type: string;
    name: string;
    properties: Record<string, any>;
    confidence: number;
}

export interface CogneeRelationship {
    id: string;
    fromEntity: string;
    toEntity: string;
    type: string;
    strength: number;
    properties: Record<string, any>;
}

export interface CogneeGraphNode {
    id: string;
    type: string;
    label: string;
    properties: Record<string, any>;
    connections: number;
}

export interface CogneeGraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    weight: number;
    properties: Record<string, any>;
}

export interface CogneeKnowledgeGraph {
    nodes: CogneeGraphNode[];
    edges: CogneeGraphEdge[];
    metadata: {
        totalNodes: number;
        totalEdges: number;
        lastUpdated: Date;
        version: string;
    };
}

export interface CogneeSearchQuery {
    query: string;
    limit?: number;
    filters?: {
        type?: string[];
        entities?: string[];
        timeRange?: {
            start: Date;
            end: Date;
        };
        confidence?: {
            min: number;
            max: number;
        };
    };
    includeEntities?: boolean;
    includeRelationships?: boolean;
}

export interface CogneeAddMemoryRequest {
    data: string | string[];
    dataset_name?: string;
    metadata?: Record<string, any>;
}

export interface CogneeAddMemoryResponse {
    success: boolean;
    message: string;
    data_points_added: number;
    errors: string[];
}

export interface CogneeCognifyRequest {
    dataset_name?: string;
    force?: boolean;
}

export interface CogneeCognifyResponse {
    success: boolean;
    message: string;
    entities_created: number;
    relationships_created: number;
    processing_time: number;
}

export interface CogneeSearchRequest {
    query: string;
    dataset_name?: string;
    limit?: number;
    include_entities?: boolean;
    include_relationships?: boolean;
}

export interface CogneeSearchResponse {
    success: boolean;
    results: CogneeSearchResult[];
    total_results: number;
    processing_time: number;
}

export interface CogneeServiceStats {
    isHealthy: boolean;
    isConnected: boolean;
    lastActivity: Date | null;
    totalMemories: number;
    totalEntities: number;
    totalRelationships: number;
    apiCallsToday: number;
    averageResponseTime: number;
}

export interface CogneeOperationResult {
    success: boolean;
    operation: string;
    message: string;
    data?: any;
    error?: string;
    timestamp: Date;
} 