// Advanced API Client for Autonomy System
class AdvancedAPIClient {
    constructor() {
        this.baseUrls = {
            // Proxy endpoints through our Bottle server
            health: '/api/proxy/health',
            autogen: '/api/proxy/autogen',
            semantic: '/api/proxy/semantic',
            neurosync: '/api/proxy/neurosync',
            scb: '/api/proxy/scb',
            system: '/api/system'
        };
        
        this.websockets = {};
        this.requestTimeout = 15000;
        this.retryCount = 3;
        this.cache = new Map();
        this.cacheTimeout = 30000; // 30 seconds
        
        // Real-time data streams
        this.dataStreams = {
            statistics: null,
            agents: null,
            stimuli: null,
            gpu: null
        };
        
        this.init();
    }
    
    init() {
        // Start periodic data refresh
        this.startDataStreams();
        
        // Handle network status changes
        window.addEventListener('online', () => this.handleNetworkChange(true));
        window.addEventListener('offline', () => this.handleNetworkChange(false));
    }
    
    // Enhanced request method with retry and caching
    async makeRequest(url, options = {}) {
        const cacheKey = `${url}:${JSON.stringify(options)}`;
        
        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cached = this.cache.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            timeout: this.requestTimeout,
            ...options
        };
        
        let lastError;
        
        // Retry logic
        for (let attempt = 0; attempt < this.retryCount; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);
                
                const response = await fetch(url, {
                    ...defaultOptions,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                // Cache successful GET requests
                if (!options.method || options.method === 'GET') {
                    this.cache.set(cacheKey, {
                        data,
                        timestamp: Date.now()
                    });
                }
                
                return data;
                
            } catch (error) {
                lastError = error;
                
                // Don't retry on client errors (4xx)
                if (error.message.includes('4')) {
                    break;
                }
                
                // Wait before retry
                if (attempt < this.retryCount - 1) {
                    await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
                }
            }
        }
        
        console.error(`Request failed after ${this.retryCount} attempts:`, lastError);
        throw lastError;
    }
    
    // System Health and Status
    async getSystemHealth() {
        try {
            const [autogen, graphflow, neurosync] = await Promise.allSettled([
                this.makeRequest(`${this.baseUrls.health}/autogen`),
                this.makeRequest(`${this.baseUrls.health}/graphflow`),
                this.makeRequest(`${this.baseUrls.health}/neurosync`)
            ]);
            
            return {
                autogen: this.extractResult(autogen),
                graphflow: this.extractResult(graphflow),
                neurosync: this.extractResult(neurosync),
                overall: this.calculateOverallHealth([autogen, graphflow, neurosync])
            };
        } catch (error) {
            console.error('Failed to get system health:', error);
            return null;
        }
    }
    
    // Comprehensive Statistics
    async getDetailedStatistics(timeframe = '1h', agentFilter = '') {
        try {
            const params = new URLSearchParams({ timeframe });
            if (agentFilter) params.append('agent_filter', agentFilter);
            
            return await this.makeRequest(`${this.baseUrls.autogen}/statistics?${params}`);
        } catch (error) {
            console.error('Failed to get detailed statistics:', error);
            return null;
        }
    }
    
    // Performance Analytics
    async getPerformanceAnalytics() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/performance`);
        } catch (error) {
            console.error('Failed to get performance analytics:', error);
            return null;
        }
    }
    
    // GPU Monitoring
    async getGPUStatus() {
        try {
            const [status, summary] = await Promise.allSettled([
                this.makeRequest(`${this.baseUrls.autogen}/gpu-status`),
                this.makeRequest(`${this.baseUrls.autogen}/gpu-summary`)
            ]);
            
            return {
                status: this.extractResult(status),
                summary: this.extractResult(summary)
            };
        } catch (error) {
            console.error('Failed to get GPU status:', error);
            return null;
        }
    }
    
    // Agent Learning and Teaching
    async getAgentLearning() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/agents`);
        } catch (error) {
            console.error('Failed to get agent learning status:', error);
            return null;
        }
    }
    
    // Persona Management
    async getPersonaStatus() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/persona`);
        } catch (error) {
            console.error('Failed to get persona status:', error);
            return null;
        }
    }
    
    // Tool Usage Analytics
    async getToolUsage() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/tools/usage`);
        } catch (error) {
            console.error('Failed to get tool usage:', error);
            return null;
        }
    }
    
    // Stimuli Processing
    async getStimuliStatus() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/stimuli/status`);
        } catch (error) {
            console.error('Failed to get stimuli status:', error);
            return null;
        }
    }
    
    async submitStimuli(content, type = 'user_message', priority = 'normal') {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/stimuli/submit`, {
                method: 'POST',
                body: JSON.stringify({ content, type, priority })
            });
        } catch (error) {
            console.error('Failed to submit stimuli:', error);
            return null;
        }
    }
    
    async pauseStimuliProcessing() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/emergency-stop`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Failed to pause stimuli processing:', error);
            return null;
        }
    }
    
    async resumeStimuliProcessing() {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/stimuli/resume`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Failed to resume stimuli processing:', error);
            return null;
        }
    }
    
    // Semantic Graph Operations
    async getSemanticMapMetrics() {
        try {
            return await this.makeRequest(`${this.baseUrls.semantic}/metrics`);
        } catch (error) {
            console.error('Failed to get semantic map metrics:', error);
            return null;
        }
    }
    
    async exportSemanticMap(format = 'd3js') {
        try {
            return await this.makeRequest(`${this.baseUrls.semantic}/export?format=${format}`);
        } catch (error) {
            console.error('Failed to export semantic map:', error);
            return null;
        }
    }
    
    async searchSemanticMap(query, limit = 10) {
        try {
            return await this.makeRequest(`${this.baseUrls.semantic}/search`, {
                method: 'POST',
                body: JSON.stringify({ query, limit })
            });
        } catch (error) {
            console.error('Failed to search semantic map:', error);
            return null;
        }
    }
    
    // Goal Management
    async createGoal(title, description, targetDate) {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/goals/create`, {
                method: 'POST',
                body: JSON.stringify({ title, description, target_date: targetDate })
            });
        } catch (error) {
            console.error('Failed to create goal:', error);
            return null;
        }
    }
    
    async updateGoalProgress(goalId, progress, notes) {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/goals/progress`, {
                method: 'POST',
                body: JSON.stringify({ goal_id: goalId, progress, notes })
            });
        } catch (error) {
            console.error('Failed to update goal progress:', error);
            return null;
        }
    }
    
    // Evolution Tracking
    async getEvolutionHistory(limit = 50) {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/evolution/history?limit=${limit}`);
        } catch (error) {
            console.error('Failed to get evolution history:', error);
            return null;
        }
    }
    
    async analyzeEvolution(codeSnippet, analysisType = 'performance') {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/evolution/analyze`, {
                method: 'POST',
                body: JSON.stringify({ code_snippet: codeSnippet, analysis_type: analysisType })
            });
        } catch (error) {
            console.error('Failed to analyze evolution:', error);
            return null;
        }
    }
    
    // Character Management
    async getCurrentCharacter() {
        try {
            return await this.makeRequest(`${this.baseUrls.neurosync}/character/current`);
        } catch (error) {
            console.error('Failed to get current character:', error);
            return null;
        }
    }
    
    async getCharacterList() {
        try {
            return await this.makeRequest(`${this.baseUrls.neurosync}/character/list`);
        } catch (error) {
            console.error('Failed to get character list:', error);
            return null;
        }
    }
    
    async switchCharacter(characterId) {
        try {
            return await this.makeRequest(`${this.baseUrls.neurosync}/character/switch`, {
                method: 'POST',
                body: JSON.stringify({ character_id: characterId })
            });
        } catch (error) {
            console.error('Failed to switch character:', error);
            return null;
        }
    }
    
    // SCB (Shared Cognitive Blackboard)
    async getSCBStatus() {
        try {
            return await this.makeRequest(`${this.baseUrls.scb}/status`);
        } catch (error) {
            console.error('Failed to get SCB status:', error);
            return null;
        }
    }
    
    // Memory Management
    async storeMemory(content, category = 'user_preference') {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/memory/store`, {
                method: 'POST',
                body: JSON.stringify({ content, category })
            });
        } catch (error) {
            console.error('Failed to store memory:', error);
            return null;
        }
    }
    
    async searchMemory(query, limit = 10) {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/memory/search`, {
                method: 'POST',
                body: JSON.stringify({ query, limit })
            });
        } catch (error) {
            console.error('Failed to search memory:', error);
            return null;
        }
    }
    
    // Report Generation
    async generateReport(type, timeframe, includeCharts = true) {
        try {
            return await this.makeRequest(`${this.baseUrls.autogen}/reports/generate`, {
                method: 'POST',
                body: JSON.stringify({ type, timeframe, include_charts: includeCharts })
            });
        } catch (error) {
            console.error('Failed to generate report:', error);
            return null;
        }
    }
    
    // Comprehensive Dashboard Data
    async getDashboardData() {
        try {
            const [health, gpu, performance, agents, stimuli, semantic, tools] = await Promise.allSettled([
                this.getSystemHealth(),
                this.getGPUStatus(),
                this.getPerformanceAnalytics(),
                this.getAgentLearning(),
                this.getStimuliStatus(),
                this.getSemanticMapMetrics(),
                this.getToolUsage()
            ]);
            
            return {
                health: this.extractResult(health),
                gpu: this.extractResult(gpu),
                performance: this.extractResult(performance),
                agents: this.extractResult(agents),
                stimuli: this.extractResult(stimuli),
                semantic: this.extractResult(semantic),
                tools: this.extractResult(tools),
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Failed to get dashboard data:', error);
            return null;
        }
    }
    
    // Real-time Data Streams
    startDataStreams() {
        // Start periodic updates for critical data
        this.dataStreams.statistics = setInterval(async () => {
            try {
                const data = await this.getDetailedStatistics();
                if (data) {
                    this.emit('statistics-update', data);
                }
            } catch (error) {
                console.error('Statistics stream error:', error);
            }
        }, 5000); // Update every 5 seconds
        
        this.dataStreams.gpu = setInterval(async () => {
            try {
                const data = await this.getGPUStatus();
                if (data) {
                    this.emit('gpu-update', data);
                }
            } catch (error) {
                console.error('GPU stream error:', error);
            }
        }, 2000); // Update every 2 seconds
        
        this.dataStreams.agents = setInterval(async () => {
            try {
                const data = await this.getAgentLearning();
                if (data) {
                    this.emit('agents-update', data);
                }
            } catch (error) {
                console.error('Agents stream error:', error);
            }
        }, 3000); // Update every 3 seconds
        
        this.dataStreams.stimuli = setInterval(async () => {
            try {
                const data = await this.getStimuliStatus();
                if (data) {
                    this.emit('stimuli-update', data);
                }
            } catch (error) {
                console.error('Stimuli stream error:', error);
            }
        }, 1000); // Update every second
    }
    
    stopDataStreams() {
        Object.values(this.dataStreams).forEach(stream => {
            if (stream) clearInterval(stream);
        });
    }
    
    // Event System
    emit(event, data) {
        window.dispatchEvent(new CustomEvent(`autonomy:${event}`, { detail: data }));
    }
    
    on(event, callback) {
        window.addEventListener(`autonomy:${event}`, callback);
    }
    
    off(event, callback) {
        window.removeEventListener(`autonomy:${event}`, callback);
    }
    
    // Utility Methods
    extractResult(settledPromise) {
        return settledPromise.status === 'fulfilled' ? settledPromise.value : null;
    }
    
    calculateOverallHealth(healthChecks) {
        const successful = healthChecks.filter(check => check.status === 'fulfilled').length;
        const total = healthChecks.length;
        const percentage = (successful / total) * 100;
        
        if (percentage >= 80) return 'healthy';
        if (percentage >= 50) return 'degraded';
        return 'critical';
    }
    
    handleNetworkChange(online) {
        if (online) {
            console.log('Network restored, resuming data streams');
            this.startDataStreams();
        } else {
            console.log('Network lost, pausing data streams');
            this.stopDataStreams();
        }
        
        this.emit('network-status', { online });
    }
    
    // Cache Management
    clearCache() {
        this.cache.clear();
    }
    
    getCacheStats() {
        return {
            size: this.cache.size,
            entries: Array.from(this.cache.keys())
        };
    }
    
    // Error Recovery
    async testConnectivity() {
        try {
            const response = await fetch('/health', { 
                method: 'HEAD',
                timeout: 5000 
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
    
    // Cleanup
    destroy() {
        this.stopDataStreams();
        this.clearCache();
        
        // Remove all event listeners
        ['online', 'offline'].forEach(event => {
            window.removeEventListener(event, this.handleNetworkChange);
        });
    }
}

// Export the advanced API client
window.AdvancedAPIClient = AdvancedAPIClient;