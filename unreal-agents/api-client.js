// API Client for Unreal Agents - Real Backend Integration
class APIClient {
    constructor() {
        this.baseURLs = {
            autogen: 'http://autogen-agent:8000',
            graphflow: 'http://graphflow-gateway:8080',
            neurosync: 'http://neurosync:5001',
            neurosyncLocal: 'http://neurosync-local:5000'
        };
        this.apiKey = 'your-api-key'; // Replace with actual API key
        this.websockets = {};
    }

    // Helper method for API calls
    async makeRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            }
        };

        // Add API key for GraphFlow endpoints
        if (url.includes('graphflow-gateway')) {
            defaultOptions.headers['X-API-Key'] = this.apiKey;
        }

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    // System Health & Status
    async getSystemHealth() {
        try {
            const [autogenHealth, graphflowHealth, neurosyncHealth] = await Promise.allSettled([
                this.makeRequest(`${this.baseURLs.autogen}/health`),
                this.makeRequest(`${this.baseURLs.graphflow}/api/v1/health`),
                this.makeRequest(`${this.baseURLs.neurosync}/game_control/health`)
            ]);

            return {
                autogen: autogenHealth.status === 'fulfilled' ? autogenHealth.value : { status: 'offline' },
                graphflow: graphflowHealth.status === 'fulfilled' ? graphflowHealth.value : { status: 'offline' },
                neurosync: neurosyncHealth.status === 'fulfilled' ? neurosyncHealth.value : { status: 'offline' }
            };
        } catch (error) {
            console.error('Failed to get system health:', error);
            return null;
        }
    }

    // GPU Status
    async getGPUStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/gpu-status`);
        } catch (error) {
            console.error('Failed to get GPU status:', error);
            return null;
        }
    }

    // Performance Analytics
    async getPerformanceAnalytics() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/analytics/performance`);
        } catch (error) {
            console.error('Failed to get performance analytics:', error);
            return null;
        }
    }

    // Agent Learning Status
    async getAgentLearning() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/agent-learning`);
        } catch (error) {
            console.error('Failed to get agent learning status:', error);
            return null;
        }
    }

    // Persona Status
    async getPersonaStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/persona/status`);
        } catch (error) {
            console.error('Failed to get persona status:', error);
            return null;
        }
    }

    // Semantic Map Status
    async getSemanticMapStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/semantic-map/status`);
        } catch (error) {
            console.error('Failed to get semantic map status:', error);
            return null;
        }
    }

    // Semantic Map Metrics
    async getSemanticMapMetrics() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/semantic-map/metrics`);
        } catch (error) {
            console.error('Failed to get semantic map metrics:', error);
            return null;
        }
    }

    // Search Semantic Map
    async searchSemanticMap(query, limit = 10) {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/semantic-map/search`, {
                method: 'POST',
                body: JSON.stringify({ query, limit })
            });
        } catch (error) {
            console.error('Failed to search semantic map:', error);
            return null;
        }
    }

    // Export Semantic Map for D3.js
    async exportSemanticMap() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/semantic-map/export?format=d3js`);
        } catch (error) {
            console.error('Failed to export semantic map:', error);
            return null;
        }
    }

    // Tool Usage Statistics
    async getToolUsage() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/tools/usage`);
        } catch (error) {
            console.error('Failed to get tool usage:', error);
            return null;
        }
    }

    // Submit Stimuli
    async submitStimuli(content, type = 'user_message', priority = 'normal') {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/stimuli/receive`, {
                method: 'POST',
                body: JSON.stringify({ content, type, priority })
            });
        } catch (error) {
            console.error('Failed to submit stimuli:', error);
            return null;
        }
    }

    // Get Stimuli Status
    async getStimuliStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/stimuli/status`);
        } catch (error) {
            console.error('Failed to get stimuli status:', error);
            return null;
        }
    }

    // Control Stimuli Processing
    async pauseStimuliProcessing() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/stimuli/control/pause`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Failed to pause stimuli processing:', error);
            return null;
        }
    }

    async resumeStimuliProcessing() {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/stimuli/control/resume`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Failed to resume stimuli processing:', error);
            return null;
        }
    }

    // Memory Management
    async storeMemory(content, category = 'user_preference') {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/memory/store`, {
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
            return await this.makeRequest(`${this.baseURLs.autogen}/api/memory/search`, {
                method: 'POST',
                body: JSON.stringify({ query, limit })
            });
        } catch (error) {
            console.error('Failed to search memory:', error);
            return null;
        }
    }

    // Goal Management
    async createGoal(title, description, targetDate) {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/goals/create`, {
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
            return await this.makeRequest(`${this.baseURLs.autogen}/api/goals/progress`, {
                method: 'POST',
                body: JSON.stringify({ goal_id: goalId, progress, notes })
            });
        } catch (error) {
            console.error('Failed to update goal progress:', error);
            return null;
        }
    }

    // Evolution History
    async getEvolutionHistory(limit = 50) {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/evolution/history?limit=${limit}`);
        } catch (error) {
            console.error('Failed to get evolution history:', error);
            return null;
        }
    }

    // Generate Report
    async generateReport(type, timeframe, includeCharts = true) {
        try {
            return await this.makeRequest(`${this.baseURLs.autogen}/api/reports/generate`, {
                method: 'POST',
                body: JSON.stringify({ type, timeframe, include_charts: includeCharts })
            });
        } catch (error) {
            console.error('Failed to generate report:', error);
            return null;
        }
    }

    // Character Management (NeuroSync)
    async getCharacterList() {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/character/list`);
        } catch (error) {
            console.error('Failed to get character list:', error);
            return null;
        }
    }

    async getCurrentCharacter() {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/character/current`);
        } catch (error) {
            console.error('Failed to get current character:', error);
            return null;
        }
    }

    async switchCharacter(characterId) {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/character/switch`, {
                method: 'POST',
                body: JSON.stringify({ character_id: characterId })
            });
        } catch (error) {
            console.error('Failed to switch character:', error);
            return null;
        }
    }

    // Avatar Control
    async processText(text, voiceConfig = {}) {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/process_text`, {
                method: 'POST',
                body: JSON.stringify({ text, voice_config: voiceConfig })
            });
        } catch (error) {
            console.error('Failed to process text:', error);
            return null;
        }
    }

    async gameControl(action, parameters = {}) {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/game_control`, {
                method: 'POST',
                body: JSON.stringify({ action, parameters })
            });
        } catch (error) {
            console.error('Failed to execute game control:', error);
            return null;
        }
    }

    // Reactive API
    async getReactiveStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/api/v1/reactive/status`);
        } catch (error) {
            console.error('Failed to get reactive status:', error);
            return null;
        }
    }

    async switchReactiveMode(mode) {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosync}/api/v1/reactive/mode/switch`, {
                method: 'POST',
                body: JSON.stringify({ mode })
            });
        } catch (error) {
            console.error('Failed to switch reactive mode:', error);
            return null;
        }
    }

    // SCB (Shared Cognitive Blackboard)
    async getSCBStatus() {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosyncLocal}/scb/ping`);
        } catch (error) {
            console.error('Failed to get SCB status:', error);
            return null;
        }
    }

    async getSCBSlice() {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosyncLocal}/scb/slice`);
        } catch (error) {
            console.error('Failed to get SCB slice:', error);
            return null;
        }
    }

    async sendSCBEvent(eventType, data) {
        try {
            return await this.makeRequest(`${this.baseURLs.neurosyncLocal}/scb/event`, {
                method: 'POST',
                body: JSON.stringify({ event_type: eventType, data })
            });
        } catch (error) {
            console.error('Failed to send SCB event:', error);
            return null;
        }
    }

    // WebSocket Connections
    connectWebSocket(type, onMessage, onError) {
        let wsUrl;
        
        switch (type) {
            case 'dashboard':
                wsUrl = `ws://${this.baseURLs.autogen.replace('http://', '')}/ws/dashboard`;
                break;
            case 'stimuli':
                wsUrl = `ws://${this.baseURLs.graphflow.replace('http://', '')}/ws/stimuli`;
                break;
            default:
                console.error('Unknown WebSocket type:', type);
                return null;
        }

        try {
            const ws = new WebSocket(wsUrl);
            
            // Add API key for GraphFlow WebSocket
            if (type === 'stimuli') {
                ws.addEventListener('open', () => {
                    ws.send(JSON.stringify({ auth: this.apiKey }));
                });
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    onMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                if (onError) onError(error);
            };

            ws.onclose = () => {
                console.log(`WebSocket ${type} closed`);
                // Implement reconnection logic if needed
            };

            this.websockets[type] = ws;
            return ws;
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            if (onError) onError(error);
            return null;
        }
    }

    // Disconnect WebSocket
    disconnectWebSocket(type) {
        if (this.websockets[type]) {
            this.websockets[type].close();
            delete this.websockets[type];
        }
    }

    // Disconnect all WebSockets
    disconnectAll() {
        Object.keys(this.websockets).forEach(type => {
            this.disconnectWebSocket(type);
        });
    }

    // Dashboard Overview (combined data)
    async getDashboardOverview() {
        try {
            const [health, gpu, performance, stimuli, semantic] = await Promise.allSettled([
                this.getSystemHealth(),
                this.getGPUStatus(),
                this.getPerformanceAnalytics(),
                this.getStimuliStatus(),
                this.getSemanticMapStatus()
            ]);

            return {
                system_health: health.status === 'fulfilled' ? health.value : null,
                gpu_status: gpu.status === 'fulfilled' ? gpu.value : null,
                performance: performance.status === 'fulfilled' ? performance.value : null,
                stimuli: stimuli.status === 'fulfilled' ? stimuli.value : null,
                semantic: semantic.status === 'fulfilled' ? semantic.value : null,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Failed to get dashboard overview:', error);
            return null;
        }
    }
}

// Export the API client
window.APIClient = APIClient;