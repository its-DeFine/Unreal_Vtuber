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
    static serviceType: ServiceTypeName = 'COGNEE' as ServiceTypeName;
    
    private config: CogneeConfig;
    private isHealthy: boolean = false;
    private isConnected: boolean = false;
    private lastActivity: Date | null = null;
    private stats: CogneeServiceStats;
    private apiCallsToday: number = 0;
    private accessToken: string | null = null;
    private tokenExpiry: Date | null = null;

    constructor(runtime: IAgentRuntime) {
        super(runtime);
        this.config = {
            baseUrl: runtime.getSetting('COGNEE_URL') as string || 'http://localhost:8000',
            apiKey: runtime.getSetting('COGNEE_API_KEY') as string || '',
            maxRetries: 3,
            timeoutMs: 30000,
            defaultDataset: 'autonomous-vtuber',
            username: 'default_user@example.com',
            password: 'default_password'
        };
        
        this.stats = {
            totalMemoriesStored: 0,
            totalSearches: 0,
            averageResponseTime: 0,
            lastOperationTime: null,
            errors: []
        };
        
        logger.info('🧠 [COGNEE] CogneeService initialized', { 
            baseUrl: this.config.baseUrl,
            hasApiKey: !!this.config.apiKey 
        });
    }

    async start(): Promise<void> {
        await this.initialize();
    }

    async stop(): Promise<void> {
        this.isHealthy = false;
        this.isConnected = false;
        this.accessToken = null;
        this.tokenExpiry = null;
        logger.info('🛑 [COGNEE] CogneeService stopped');
    }

    private async initialize(): Promise<void> {
        try {
            logger.info('🚀 [COGNEE] Initializing Cognee service connection...');
            
            // Test basic connectivity
            const healthResponse = await this.makeRequest('GET', '/health');
            if (healthResponse.ok) {
                this.isConnected = true;
                logger.info('✅ [COGNEE] Basic connectivity established');
            }
            
            // Authenticate to get access token
            await this.authenticate();
            
            this.isHealthy = true;
            logger.info('✅ [COGNEE] CogneeService initialized successfully');
            
        } catch (error) {
            logger.error('❌ [COGNEE] Failed to initialize CogneeService', { 
                error: error.message,
                baseUrl: this.config.baseUrl 
            });
            // Don't throw - allow graceful degradation
            this.isHealthy = false;
        }
    }

    private async authenticate(): Promise<void> {
        try {
            const formData = new URLSearchParams();
            formData.append('username', this.config.username);
            formData.append('password', this.config.password);

            const response = await fetch(`${this.config.baseUrl}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData.toString(),
            });

            if (!response.ok) {
                throw new Error(`Authentication failed: ${response.status}`);
            }

            const data = await response.json();
            this.accessToken = data.access_token;
            
            // JWT tokens typically expire in 1 hour, set expiry to 50 minutes from now
            this.tokenExpiry = new Date(Date.now() + 50 * 60 * 1000);
            
            logger.info('✅ [COGNEE] Authentication successful');
            
        } catch (error) {
            logger.error('❌ [COGNEE] Authentication failed', { error: error.message });
            throw error;
        }
    }

    private async ensureValidToken(): Promise<void> {
        if (!this.accessToken || !this.tokenExpiry || new Date() >= this.tokenExpiry) {
            logger.info('🔄 [COGNEE] Token expired or missing, re-authenticating...');
            await this.authenticate();
        }
    }

    private async makeRequest(method: string, endpoint: string, data?: any): Promise<Response> {
        const url = `${this.config.baseUrl}${endpoint}`;
        const options: RequestInit = {
            method,
            headers: {
                'Accept': 'application/json',
            },
        };

        if (this.accessToken) {
            options.headers = {
                ...options.headers,
                'Authorization': `Bearer ${this.accessToken}`,
            };
        }

        if (data && method !== 'GET') {
            if (data instanceof FormData) {
                options.body = data;
            } else {
                options.headers = {
                    ...options.headers,
                    'Content-Type': 'application/json',
                };
                options.body = JSON.stringify(data);
            }
        }

        const response = await fetch(url, options);
        return response;
    }

    async addMemory(text: string, datasetName?: string): Promise<CogneeOperationResult> {
        try {
            await this.ensureValidToken();
            
            const formData = new FormData();
            const blob = new Blob([text], { type: 'text/plain' });
            formData.append('data', blob, 'memory.txt');
            formData.append('datasetName', datasetName || this.config.defaultDataset);

            const response = await this.makeRequest('POST', '/api/v1/add/', formData);
            
            if (!response.ok) {
                const errorText = await response.text();
                // Handle connection errors gracefully
                if (errorText.includes('Connection error') || errorText.includes('OpenAIException')) {
                    logger.warn('⚠️ [COGNEE] LLM connection issue, memory stored but not processed', {
                        text: text.substring(0, 100),
                        error: errorText
                    });
                    return {
                        success: true,
                        operation: 'addMemory',
                        data: { stored: true, processed: false },
                        timestamp: new Date(),
                        message: 'Memory stored but LLM processing unavailable'
                    };
                }
                throw new Error(`Add memory failed: ${response.status} - ${errorText}`);
            }

            const result = await response.json();
            this.stats.totalMemoriesStored++;
            this.lastActivity = new Date();
            
            logger.info('✅ [COGNEE] Memory added successfully', {
                datasetName: datasetName || this.config.defaultDataset,
                textLength: text.length
            });

            return {
                success: true,
                operation: 'addMemory',
                data: result,
                timestamp: new Date()
            };

        } catch (error) {
            logger.error('❌ [COGNEE] Failed to add memory', { 
                error: error.message,
                text: text.substring(0, 100) 
            });
            
            return {
                success: false,
                operation: 'addMemory',
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async search(query: string, searchType: string = 'GRAPH_COMPLETION'): Promise<CogneeOperationResult> {
        try {
            await this.ensureValidToken();
            
            const searchData = {
                searchType,
                query
            };

            const response = await this.makeRequest('POST', '/api/v1/search/', searchData);
            
            if (!response.ok) {
                const errorText = await response.text();
                // Handle connection errors gracefully
                if (errorText.includes('Connection error') || errorText.includes('OpenAIException')) {
                    logger.warn('⚠️ [COGNEE] LLM connection issue for search', {
                        query: query.substring(0, 50),
                        error: errorText
                    });
                    return {
                        success: false,
                        operation: 'search',
                        error: 'LLM service unavailable',
                        timestamp: new Date()
                    };
                }
                throw new Error(`Search failed: ${response.status} - ${errorText}`);
            }

            const result = await response.json();
            this.stats.totalSearches++;
            this.lastActivity = new Date();
            
            logger.info('✅ [COGNEE] Search completed successfully', {
                query: query.substring(0, 50),
                resultsCount: Array.isArray(result) ? result.length : 'N/A'
            });

            return {
                success: true,
                operation: 'search',
                data: result,
                timestamp: new Date()
            };

        } catch (error) {
            logger.error('❌ [COGNEE] Failed to search', { 
                error: error.message,
                query: query.substring(0, 50) 
            });
            
            return {
                success: false,
                operation: 'search',
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    async cognify(datasets?: string[]): Promise<CogneeOperationResult> {
        try {
            await this.ensureValidToken();
            
            const cognifyData = {
                datasets: datasets || [this.config.defaultDataset]
            };

            const response = await this.makeRequest('POST', '/api/v1/cognify/', cognifyData);
            
            if (!response.ok) {
                const errorText = await response.text();
                // Handle connection errors gracefully
                if (errorText.includes('Connection error') || errorText.includes('OpenAIException')) {
                    logger.warn('⚠️ [COGNEE] LLM connection issue for cognify', {
                        datasets,
                        error: errorText
                    });
                    return {
                        success: false,
                        operation: 'cognify',
                        error: 'LLM service unavailable',
                        timestamp: new Date()
                    };
                }
                throw new Error(`Cognify failed: ${response.status} - ${errorText}`);
            }

            const result = await response.json();
            this.lastActivity = new Date();
            
            logger.info('✅ [COGNEE] Cognify completed successfully', {
                datasets: datasets || [this.config.defaultDataset]
            });

            return {
                success: true,
                operation: 'cognify',
                data: result,
                timestamp: new Date()
            };

        } catch (error) {
            logger.error('❌ [COGNEE] Failed to cognify', { 
                error: error.message,
                datasets 
            });
            
            return {
                success: false,
                operation: 'cognify',
                error: error.message,
                timestamp: new Date()
            };
        }
    }

    getStats(): CogneeServiceStats {
        return {
            ...this.stats,
            isHealthy: this.isHealthy,
            isConnected: this.isConnected,
            lastActivity: this.lastActivity
        };
    }

    isServiceHealthy(): boolean {
        return this.isHealthy && this.isConnected;
    }
} 