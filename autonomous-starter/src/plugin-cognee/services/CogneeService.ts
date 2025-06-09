import { IAgentRuntime, Service, logger, ServiceTypeName } from '@elizaos/core';
import {
    CogneeConfig,
    CogneeMemoryEntry,
    CogneeSearchResult,
    CogneeAddMemoryRequest,
    CogneeAddMemoryResponse,
    CogneeCognifyRequest,
    CogneeCognifyResponse,
    CogneeSearchRequest,
    CogneeSearchResponse,
    CogneeServiceStats,
    CogneeOperationResult
} from '../types/CogneeTypes';

export class CogneeService extends Service {
    static serviceType: ServiceTypeName = 'COGNEE_MEMORY' as ServiceTypeName;
    
    private config: CogneeConfig;
    private isHealthy: boolean = false;
    private isConnected: boolean = false;
    private lastActivity: Date | null = null;
    private stats: CogneeServiceStats;
    private apiCallsToday: number = 0;
    private responseTimes: number[] = [];
    
    constructor(runtime: IAgentRuntime) {
        super(runtime);
        
        // Initialize configuration
        this.config = {
            url: runtime.getSetting('COGNEE_URL') as string || 'http://cognee:8000',
            apiKey: runtime.getSetting('COGNEE_API_KEY') as string || '',
            timeout: 30000,
            retryAttempts: 3
        };
        
        // Initialize stats
        this.stats = {
            isHealthy: false,
            isConnected: false,
            lastActivity: null,
            totalMemories: 0,
            totalEntities: 0,
            totalRelationships: 0,
            apiCallsToday: 0,
            averageResponseTime: 0
        };
        
        logger.info('🧠 [COGNEE] Service initialized', {
            url: this.config.url,
            hasApiKey: !!this.config.apiKey
        });
    }
    
    async initialize(): Promise<void> {
        logger.info('🧠 [COGNEE] Initializing knowledge graph service');
        
        try {
            // Test connection
            await this.checkHealth();
            
            if (this.isHealthy) {
                // Start health monitoring
                this.startHealthMonitoring();
                logger.info('🧠 [COGNEE] ✅ Knowledge graph service ready');
            } else {
                logger.warn('🧠 [COGNEE] ⚠️ Service initialized but health check failed');
            }
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Failed to initialize service', { error });
            // Continue without throwing - allow graceful degradation
        }
    }
    
    async addMemory(data: string | string[], datasetName?: string): Promise<CogneeOperationResult> {
        const startTime = Date.now();
        
        logger.info('🧠 [COGNEE] Adding memory to knowledge graph', {
            dataLength: Array.isArray(data) ? data.length : 1,
            dataset: datasetName || 'default'
        });
        
        try {
            const request: CogneeAddMemoryRequest = {
                data,
                dataset_name: datasetName
            };
            
            const response = await this.makeApiCall<CogneeAddMemoryResponse>(
                '/api/v1/add',
                'POST',
                request
            );
            
            this.recordApiCall(Date.now() - startTime);
            this.lastActivity = new Date();
            
            logger.info('🧠 [COGNEE] ✅ Memory added successfully', {
                dataPointsAdded: response.data_points_added,
                errors: response.errors.length
            });
            
            return {
                success: true,
                operation: 'add_memory',
                message: `Successfully added ${response.data_points_added} data points`,
                data: response,
                timestamp: new Date()
            };
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Failed to add memory', { error });
            return {
                success: false,
                operation: 'add_memory',
                message: 'Failed to add memory to knowledge graph',
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date()
            };
        }
    }
    
    async cognify(datasetName?: string, force?: boolean): Promise<CogneeOperationResult> {
        const startTime = Date.now();
        
        logger.info('🧠 [COGNEE] Starting cognify process (knowledge graph generation)', {
            dataset: datasetName || 'default',
            force
        });
        
        try {
            const request: CogneeCognifyRequest = {
                dataset_name: datasetName,
                force
            };
            
            const response = await this.makeApiCall<CogneeCognifyResponse>(
                '/cognify',
                'POST',
                request
            );
            
            this.recordApiCall(Date.now() - startTime);
            this.lastActivity = new Date();
            
            logger.info('🧠 [COGNEE] ✅ Cognify process completed', {
                entitiesCreated: response.entities_created,
                relationshipsCreated: response.relationships_created,
                processingTime: response.processing_time
            });
            
            // Update internal stats
            this.stats.totalEntities += response.entities_created;
            this.stats.totalRelationships += response.relationships_created;
            
            return {
                success: true,
                operation: 'cognify',
                message: `Cognify completed: ${response.entities_created} entities, ${response.relationships_created} relationships created`,
                data: response,
                timestamp: new Date()
            };
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Cognify process failed', { error });
            return {
                success: false,
                operation: 'cognify',
                message: 'Failed to complete cognify process',
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date()
            };
        }
    }
    
    async search(query: string, options?: {
        datasetName?: string;
        limit?: number;
        includeEntities?: boolean;
        includeRelationships?: boolean;
    }): Promise<CogneeOperationResult> {
        const startTime = Date.now();
        
        logger.info('🧠 [COGNEE] Searching knowledge graph', {
            query: query.substring(0, 100),
            dataset: options?.datasetName || 'default',
            limit: options?.limit || 10
        });
        
        try {
            const request: CogneeSearchRequest = {
                query,
                dataset_name: options?.datasetName,
                limit: options?.limit || 10,
                include_entities: options?.includeEntities ?? true,
                include_relationships: options?.includeRelationships ?? true
            };
            
            const response = await this.makeApiCall<CogneeSearchResponse>(
                '/search',
                'POST',
                request
            );
            
            this.recordApiCall(Date.now() - startTime);
            this.lastActivity = new Date();
            
            logger.info('🧠 [COGNEE] ✅ Search completed', {
                resultsFound: response.total_results,
                processingTime: response.processing_time
            });
            
            return {
                success: true,
                operation: 'search',
                message: `Found ${response.total_results} results`,
                data: response,
                timestamp: new Date()
            };
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Search failed', { error });
            return {
                success: false,
                operation: 'search',
                message: 'Failed to search knowledge graph',
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date()
            };
        }
    }
    
    async getKnowledgeGraphStats(): Promise<CogneeServiceStats> {
        // Update real-time stats
        this.stats.isHealthy = this.isHealthy;
        this.stats.isConnected = this.isConnected;
        this.stats.lastActivity = this.lastActivity;
        this.stats.apiCallsToday = this.apiCallsToday;
        this.stats.averageResponseTime = this.calculateAverageResponseTime();
        
        return { ...this.stats };
    }
    
    private async checkHealth(): Promise<boolean> {
        try {
            const startTime = Date.now();
            
            // Simple health check - try to make a minimal API call
            const response = await fetch(`${this.config.url}/health`, {
                method: 'GET',
                headers: this.getHeaders(),
                signal: AbortSignal.timeout(this.config.timeout)
            });
            
            this.isHealthy = response.ok;
            this.isConnected = response.ok;
            
            if (this.isHealthy) {
                this.recordApiCall(Date.now() - startTime);
                logger.debug('🧠 [COGNEE] ✅ Health check passed');
            } else {
                logger.warn('🧠 [COGNEE] ⚠️ Health check failed', { 
                    status: response.status,
                    statusText: response.statusText 
                });
            }
            
            return this.isHealthy;
            
        } catch (error) {
            this.isHealthy = false;
            this.isConnected = false;
            logger.error('🧠 [COGNEE] ❌ Health check error', { error });
            return false;
        }
    }
    
    private async makeApiCall<T>(
        endpoint: string,
        method: 'GET' | 'POST' | 'PUT' | 'DELETE',
        body?: any
    ): Promise<T> {
        const url = `${this.config.url}${endpoint}`;
        const headers = this.getHeaders();
        
        let attempt = 0;
        while (attempt < this.config.retryAttempts) {
            try {
                const response = await fetch(url, {
                    method,
                    headers,
                    body: body ? JSON.stringify(body) : undefined,
                    signal: AbortSignal.timeout(this.config.timeout)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                return data as T;
                
            } catch (error) {
                attempt++;
                logger.warn(`🧠 [COGNEE] API call attempt ${attempt} failed`, {
                    endpoint,
                    error: error instanceof Error ? error.message : String(error)
                });
                
                if (attempt >= this.config.retryAttempts) {
                    throw error;
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
        
        throw new Error('All API call attempts failed');
    }
    
    private getHeaders(): Record<string, string> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };
        
        if (this.config.apiKey) {
            headers['Authorization'] = `Bearer ${this.config.apiKey}`;
        }
        
        return headers;
    }
    
    private startHealthMonitoring(): void {
        // Check health every 30 seconds
        setInterval(async () => {
            await this.checkHealth();
        }, 30000);
        
        logger.debug('🧠 [COGNEE] Health monitoring started');
    }
    
    private recordApiCall(responseTime: number): void {
        this.apiCallsToday++;
        this.responseTimes.push(responseTime);
        
        // Keep only last 100 response times for average calculation
        if (this.responseTimes.length > 100) {
            this.responseTimes = this.responseTimes.slice(-100);
        }
    }
    
    private calculateAverageResponseTime(): number {
        if (this.responseTimes.length === 0) return 0;
        
        const sum = this.responseTimes.reduce((a, b) => a + b, 0);
        return Math.round(sum / this.responseTimes.length);
    }
    
    // Public interface for external integrations
    async enhanceMemoryWithGraph(content: string, context?: Record<string, any>): Promise<CogneeOperationResult> {
        logger.info('🧠 [COGNEE] Enhancing memory with knowledge graph integration');
        
        try {
            // Add to knowledge graph
            const addResult = await this.addMemory([content], 'autonomous_agent');
            
            if (!addResult.success) {
                return addResult;
            }
            
            // Process through cognify to create entities/relationships
            const cognifyResult = await this.cognify('autonomous_agent');
            
            return {
                success: true,
                operation: 'enhance_memory',
                message: 'Memory enhanced with knowledge graph processing',
                data: {
                    addResult,
                    cognifyResult
                },
                timestamp: new Date()
            };
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Memory enhancement failed', { error });
            return {
                success: false,
                operation: 'enhance_memory',
                message: 'Failed to enhance memory with knowledge graph',
                error: error instanceof Error ? error.message : String(error),
                timestamp: new Date()
            };
        }
    }
    
    async semanticSearch(query: string, context?: Record<string, any>): Promise<CogneeSearchResult[]> {
        logger.info('🧠 [COGNEE] Performing semantic search', {
            query: query.substring(0, 50)
        });
        
        try {
            const searchResult = await this.search(query, {
                datasetName: 'autonomous_agent',
                limit: 10,
                includeEntities: true,
                includeRelationships: true
            });
            
            if (searchResult.success && searchResult.data) {
                const response = searchResult.data as CogneeSearchResponse;
                return response.results;
            }
            
            return [];
            
        } catch (error) {
            logger.error('🧠 [COGNEE] ❌ Semantic search failed', { error });
            return [];
        }
    }
} 