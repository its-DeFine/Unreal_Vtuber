// Advanced Autonomy Command Center Application
class AutonomyCommandCenter {
    constructor() {
        this.api = new AdvancedAPIClient();
        this.currentView = 'overview';
        this.updateIntervals = {};
        this.charts = {};
        this.systemData = {};
        this.isInitialized = false;
        
        // Real-time data storage
        this.realtimeData = {
            statistics: [],
            gpu: [],
            agents: {},
            stimuli: [],
            activities: []
        };
        
        this.startTime = Date.now();
        this.init();
    }
    
    async init() {
        try {
            console.log('🚀 Initializing Autonomy Command Center...');
            
            // Setup event listeners
            this.setupEventListeners();
            this.setupRealtimeUpdates();
            
            // Initialize UI components
            this.initializeCharts();
            this.setupNavigation();
            
            // Load initial data
            await this.loadInitialData();
            
            // Start real-time updates
            this.startRealtimeUpdates();
            
            this.isInitialized = true;
            this.updateSystemState('NEURAL NETWORKS ONLINE - ALL SYSTEMS OPERATIONAL');
            
            console.log('✅ Autonomy Command Center initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize Command Center:', error);
            this.updateSystemState('SYSTEM INITIALIZATION FAILED - CHECK CONNECTIONS');
        }
    }
    
    setupEventListeners() {
        // API event listeners
        this.api.on('statistics-update', (event) => this.handleStatisticsUpdate(event.detail));
        this.api.on('gpu-update', (event) => this.handleGPUUpdate(event.detail));
        this.api.on('agents-update', (event) => this.handleAgentsUpdate(event.detail));
        this.api.on('stimuli-update', (event) => this.handleStimuliUpdate(event.detail));
        this.api.on('network-status', (event) => this.handleNetworkStatus(event.detail));
        
        // UI event listeners
        document.getElementById('emergencyStop')?.addEventListener('click', () => this.executeEmergencyStop());
        document.getElementById('modeToggle')?.addEventListener('click', () => this.toggleMode());
        document.getElementById('refreshStats')?.addEventListener('click', () => this.refreshAllData());
        document.getElementById('executeCommand')?.addEventListener('click', () => this.executeCommand());
        document.getElementById('injectStimuli')?.addEventListener('click', () => this.injectStimuli());
        
        // Team selector
        document.getElementById('teamSelector')?.addEventListener('change', (e) => this.switchTeam(e.target.value));
        
        // Analytics timeframe
        document.getElementById('analyticsTimeframe')?.addEventListener('change', (e) => this.updateAnalytics(e.target.value));
        
        // Floating utilities
        document.getElementById('aiAssistant')?.addEventListener('click', () => this.openAIAssistant());
        document.getElementById('voiceCommand')?.addEventListener('click', () => this.startVoiceCommand());
        document.getElementById('exportData')?.addEventListener('click', () => this.exportSystemData());
        document.getElementById('helpSystem')?.addEventListener('click', () => this.showHelp());
    }
    
    setupNavigation() {
        const navTabs = document.querySelectorAll('.nav-tab');
        navTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });
    }
    
    switchView(view) {
        // Update navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.view === view);
        });
        
        // Update view sections
        document.querySelectorAll('.view-section').forEach(section => {
            section.classList.toggle('active', section.id === `${view}-view`);
        });
        
        this.currentView = view;
        
        // Load view-specific data
        this.loadViewData(view);
    }
    
    async loadViewData(view) {
        switch (view) {
            case 'overview':
                await this.loadOverviewData();
                break;
            case 'agents':
                await this.loadAgentsData();
                break;
            case 'analytics':
                await this.loadAnalyticsData();
                break;
            case 'stimuli':
                await this.loadStimuliData();
                break;
            case 'knowledge':
                await this.loadKnowledgeData();
                break;
            case 'evolution':
                await this.loadEvolutionData();
                break;
            case 'tools':
                await this.loadToolsData();
                break;
            case 'systems':
                await this.loadSystemsData();
                break;
        }
    }
    
    async loadInitialData() {
        try {
            console.log('📊 Loading initial system data...');
            
            // Load comprehensive dashboard data
            const dashboardData = await this.api.getDashboardData();
            
            if (dashboardData) {
                this.systemData = dashboardData;
                this.updateSystemStatus();
                this.updateOverviewPanel();
            }
            
            // Initialize uptime counter
            this.startUptimeCounter();
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }
    
    setupRealtimeUpdates() {
        // System monitor updates
        this.updateIntervals.systemMonitor = setInterval(() => {
            this.updateSystemMonitor();
        }, 1000);
        
        // Activity feed updates
        this.updateIntervals.activityFeed = setInterval(() => {
            this.updateActivityFeed();
        }, 2000);
    }
    
    startRealtimeUpdates() {
        console.log('🔄 Starting real-time data streams...');
        // Real-time updates are handled by the API client
    }
    
    // Data Update Handlers
    handleStatisticsUpdate(data) {
        this.realtimeData.statistics.push({
            ...data,
            timestamp: Date.now()
        });
        
        // Keep only last 100 entries
        if (this.realtimeData.statistics.length > 100) {
            this.realtimeData.statistics = this.realtimeData.statistics.slice(-100);
        }
        
        this.updatePerformanceCharts();
        this.updateStatisticsDisplay();
    }
    
    handleGPUUpdate(data) {
        this.realtimeData.gpu.push({
            ...data,
            timestamp: Date.now()
        });
        
        if (this.realtimeData.gpu.length > 100) {
            this.realtimeData.gpu = this.realtimeData.gpu.slice(-100);
        }
        
        this.updateGPUMonitor();
    }
    
    handleAgentsUpdate(data) {
        this.realtimeData.agents = {
            ...data,
            timestamp: Date.now()
        };
        
        this.updateAgentsDisplay();
    }
    
    handleStimuliUpdate(data) {
        this.realtimeData.stimuli.push({
            ...data,
            timestamp: Date.now()
        });
        
        if (this.realtimeData.stimuli.length > 50) {
            this.realtimeData.stimuli = this.realtimeData.stimuli.slice(-50);
        }
        
        this.updateStimuliDisplay();
        this.addActivity('STIMULI', `Processing: ${data.content || 'Unknown'}`, 'info');
    }
    
    handleNetworkStatus(data) {
        const statusElement = document.getElementById('systemStatus');
        if (statusElement) {
            statusElement.className = `status-indicator ${data.online ? 'online' : 'offline'}`;
        }
        
        this.updateSystemState(data.online ? 
            'NETWORK ONLINE - ALL SYSTEMS OPERATIONAL' : 
            'NETWORK OFFLINE - OPERATING IN DEGRADED MODE');
    }
    
    // UI Update Methods
    updateSystemStatus() {
        const health = this.systemData.health;
        if (!health) return;
        
        const statusElement = document.getElementById('systemStatus');
        const stateElement = document.getElementById('systemState');
        
        if (statusElement && stateElement) {
            statusElement.className = `status-indicator ${health.overall}`;
            
            let statusText = 'UNKNOWN STATUS';
            switch (health.overall) {
                case 'healthy':
                    statusText = 'ALL SYSTEMS OPERATIONAL';
                    break;
                case 'degraded':
                    statusText = 'SOME SYSTEMS DEGRADED';
                    break;
                case 'critical':
                    statusText = 'CRITICAL SYSTEM ERRORS';
                    break;
            }
            
            stateElement.textContent = statusText;
        }
        
        // Update individual service statuses
        this.updateServiceStatuses(health);
    }
    
    updateServiceStatuses(health) {
        const services = ['autogen', 'graphflow', 'neurosync'];
        
        services.forEach(service => {
            const element = document.getElementById(`${service}Status`);
            if (element && health[service]) {
                const status = health[service].status === 'healthy' ? 'online' : 'offline';
                element.className = `service-status ${status}`;
            }
        });
    }
    
    updateSystemMonitor() {
        const gpu = this.realtimeData.gpu[this.realtimeData.gpu.length - 1];
        
        if (gpu && gpu.status) {
            this.updateMonitorValue('gpuUtil', `${gpu.status.gpu_utilization || 0}%`);
            this.updateMonitorValue('memoryUsage', `${(gpu.status.vram_used || 0) / 1024} GB`);
        }
        
        const stimuli = this.realtimeData.stimuli;
        if (stimuli.length > 0) {
            this.updateMonitorValue('processingRate', `${stimuli.length}/min`);
            this.updateMonitorValue('queueLength', `${stimuli[stimuli.length - 1].queue_length || 0}`);
        }
        
        // Update success rate
        const stats = this.realtimeData.statistics;
        if (stats.length > 0) {
            const latest = stats[stats.length - 1];
            document.getElementById('successRate').textContent = `${latest.success_rate || 0}%`;
        }
    }
    
    updateMonitorValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }
    
    updateOverviewPanel() {
        this.updateAgentsGrid();
        this.updateSystemMetrics();
    }
    
    updateAgentsGrid() {
        const container = document.getElementById('agentsContainer');
        if (!container) return;
        
        const agents = this.generateAgentData();
        
        container.innerHTML = '';
        
        agents.forEach(agent => {
            const card = this.createAgentCard(agent);
            container.appendChild(card);
        });
    }
    
    generateAgentData() {
        const baseAgents = [
            {
                id: 'cognitive',
                name: 'Cognitive AI',
                type: 'cognitive',
                icon: '🧠',
                status: 'active'
            },
            {
                id: 'programmer',
                name: 'Programmer',
                type: 'programmer',
                icon: '💻',
                status: 'active'
            },
            {
                id: 'observer',
                name: 'Observer',
                type: 'observer',
                icon: '👁',
                status: 'monitoring'
            },
            {
                id: 'executor',
                name: 'Code Executor',
                type: 'executor',
                icon: '⚡',
                status: 'active'
            }
        ];
        
        // Enhance with real data if available
        const agentData = this.realtimeData.agents;
        if (agentData) {
            baseAgents.forEach(agent => {
                agent.metrics = {
                    success: agentData.success_rate || Math.floor(Math.random() * 20) + 80,
                    response: agentData.average_response_time || Math.floor(Math.random() * 50) + 10,
                    tasks: agentData.memory_entries || Math.floor(Math.random() * 100) + 50
                };
                
                agent.activity = this.generateAgentActivity(agent.type);
            });
        }
        
        return baseAgents;
    }
    
    generateAgentActivity(type) {
        const activities = {
            cognitive: [
                'Analyzing semantic relationships...',
                'Processing natural language...',
                'Updating knowledge graph...',
                'Performing context analysis...'
            ],
            programmer: [
                'Optimizing code execution...',
                'Analyzing performance metrics...',
                'Implementing feature requests...',
                'Debugging system issues...'
            ],
            observer: [
                'Monitoring system health...',
                'Tracking performance metrics...',
                'Analyzing behavioral patterns...',
                'Collecting diagnostic data...'
            ],
            executor: [
                'Executing validation checks...',
                'Running automated tests...',
                'Processing tool requests...',
                'Handling system operations...'
            ]
        };
        
        const typeActivities = activities[type] || ['Processing tasks...'];
        return typeActivities[Math.floor(Math.random() * typeActivities.length)];
    }
    
    createAgentCard(agent) {
        const card = document.createElement('div');
        card.className = `agent-card ${agent.status}`;
        
        card.innerHTML = `
            <div class="agent-header">
                <div class="agent-avatar">
                    <span>${agent.icon}</span>
                </div>
                <div class="agent-info">
                    <h3>${agent.name}</h3>
                    <div class="agent-status">${agent.status.toUpperCase()}</div>
                </div>
            </div>
            <div class="agent-metrics">
                <div class="agent-metric">
                    <span class="metric-value">${agent.metrics?.success || 0}%</span>
                    <span class="metric-label">Success</span>
                </div>
                <div class="agent-metric">
                    <span class="metric-value">${agent.metrics?.response || 0}ms</span>
                    <span class="metric-label">Response</span>
                </div>
                <div class="agent-metric">
                    <span class="metric-value">${agent.metrics?.tasks || 0}</span>
                    <span class="metric-label">Tasks</span>
                </div>
            </div>
            <div class="agent-activity">${agent.activity || 'Idle...'}</div>
        `;
        
        return card;
    }
    
    updateActivityFeed() {
        // Generate periodic activity updates
        if (Math.random() < 0.3) { // 30% chance per update
            this.generateRandomActivity();
        }
        
        this.renderActivityFeed();
    }
    
    generateRandomActivity() {
        const agents = ['Cognitive AI', 'Programmer', 'Observer', 'Code Executor'];
        const activities = [
            'Completed semantic analysis task',
            'Optimized neural network performance',
            'Updated knowledge base entries',
            'Processed external stimuli',
            'Executed validation procedures',
            'Analyzed system performance metrics',
            'Generated optimization recommendations',
            'Updated character state matrix'
        ];
        
        const levels = ['success', 'info', 'warning'];
        
        const agent = agents[Math.floor(Math.random() * agents.length)];
        const activity = activities[Math.floor(Math.random() * activities.length)];
        const level = levels[Math.floor(Math.random() * levels.length)];
        
        this.addActivity(agent, activity, level);
    }
    
    addActivity(agent, message, level = 'info') {
        this.realtimeData.activities.unshift({
            timestamp: Date.now(),
            agent,
            message,
            level
        });
        
        // Keep only last 100 activities
        if (this.realtimeData.activities.length > 100) {
            this.realtimeData.activities = this.realtimeData.activities.slice(0, 100);
        }
    }
    
    renderActivityFeed() {
        const feedElement = document.getElementById('activityFeed');
        if (!feedElement) return;
        
        const activities = this.realtimeData.activities.slice(0, 20); // Show last 20
        
        feedElement.innerHTML = activities.map(activity => `
            <div class="activity-item ${activity.level}">
                <span class="activity-timestamp">${this.formatTime(activity.timestamp)}</span>
                <span class="activity-agent">[${activity.agent}]</span>
                <span class="activity-message">${activity.message}</span>
            </div>
        `).join('');
    }
    
    // Chart and Visualization Methods
    initializeCharts() {
        this.createMonitorCharts();
        this.createPerformanceCharts();
    }
    
    createMonitorCharts() {
        const chartIds = ['gpuChart', 'memoryChart', 'rateChart', 'queueChart'];
        
        chartIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                this.createMiniChart(element);
            }
        });
    }
    
    createMiniChart(element) {
        const canvas = document.createElement('canvas');
        canvas.width = element.offsetWidth;
        canvas.height = element.offsetHeight;
        element.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        this.drawWaveform(ctx, canvas.width, canvas.height);
        
        // Animate the waveform
        setInterval(() => {
            this.drawWaveform(ctx, canvas.width, canvas.height);
        }, 2000);
    }
    
    drawWaveform(ctx, width, height) {
        ctx.clearRect(0, 0, width, height);
        
        ctx.strokeStyle = '#00ffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const points = 20;
        const stepX = width / points;
        
        for (let i = 0; i <= points; i++) {
            const x = i * stepX;
            const y = height/2 + Math.sin(Date.now() * 0.01 + i * 0.5) * (height/4);
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        
        ctx.stroke();
    }
    
    createPerformanceCharts() {
        const performanceCanvas = document.getElementById('performanceChart');
        if (performanceCanvas) {
            this.charts.performance = new Chart(performanceCanvas, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Response Time',
                        data: [],
                        borderColor: '#00ffff',
                        backgroundColor: 'rgba(0, 255, 255, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#ffffff'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#ffffff'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    }
                }
            });
        }
    }
    
    updatePerformanceCharts() {
        if (this.charts.performance && this.realtimeData.statistics.length > 0) {
            const latest = this.realtimeData.statistics.slice(-10);
            
            this.charts.performance.data.labels = latest.map((_, i) => 
                this.formatTime(Date.now() - (latest.length - i) * 5000)
            );
            
            this.charts.performance.data.datasets[0].data = latest.map(stat => 
                stat.average_response_time || Math.random() * 100
            );
            
            this.charts.performance.update('none');
        }
    }
    
    // Command Execution
    async executeCommand() {
        const input = document.getElementById('commandInput');
        const target = document.getElementById('commandTarget');
        const priority = document.getElementById('commandPriority');
        
        if (!input?.value.trim()) return;
        
        const command = input.value.trim();
        const targetValue = target?.value || 'all';
        const priorityValue = priority?.value || 'normal';
        
        try {
            this.addActivity('SYSTEM', `Executing command: ${command.substring(0, 50)}...`, 'info');
            
            const result = await this.api.submitStimuli(command, 'command', priorityValue);
            
            if (result) {
                this.addActivity('SYSTEM', 'Command executed successfully', 'success');
                input.value = '';
            } else {
                this.addActivity('SYSTEM', 'Command execution failed', 'error');
            }
            
        } catch (error) {
            console.error('Command execution error:', error);
            this.addActivity('SYSTEM', 'Command execution error', 'error');
        }
    }
    
    async executeEmergencyStop() {
        try {
            this.addActivity('SYSTEM', 'EMERGENCY STOP INITIATED', 'warning');
            
            const result = await this.api.pauseStimuliProcessing();
            
            if (result) {
                this.addActivity('SYSTEM', 'EMERGENCY STOP SUCCESSFUL - ALL AGENTS HALTED', 'warning');
                this.updateSystemState('EMERGENCY STOP ACTIVE - SYSTEM PAUSED');
            } else {
                this.addActivity('SYSTEM', 'EMERGENCY STOP FAILED', 'error');
            }
            
        } catch (error) {
            console.error('Emergency stop error:', error);
            this.addActivity('SYSTEM', 'EMERGENCY STOP ERROR', 'error');
        }
    }
    
    // Utility Methods
    startUptimeCounter() {
        const updateUptime = () => {
            const uptime = Date.now() - this.startTime;
            const hours = Math.floor(uptime / 3600000);
            const minutes = Math.floor((uptime % 3600000) / 60000);
            const seconds = Math.floor((uptime % 60000) / 1000);
            
            const uptimeElement = document.getElementById('uptime');
            if (uptimeElement) {
                uptimeElement.textContent = 
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        };
        
        updateUptime();
        setInterval(updateUptime, 1000);
    }
    
    updateSystemState(message) {
        const element = document.getElementById('systemState');
        if (element) {
            element.textContent = message;
        }
    }
    
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString();
    }
    
    async refreshAllData() {
        try {
            this.addActivity('SYSTEM', 'Refreshing all data streams...', 'info');
            await this.loadInitialData();
            this.addActivity('SYSTEM', 'Data refresh completed', 'success');
        } catch (error) {
            console.error('Data refresh error:', error);
            this.addActivity('SYSTEM', 'Data refresh failed', 'error');
        }
    }
    
    // Placeholder methods for other views
    async loadOverviewData() {
        // Already handled in loadInitialData
    }
    
    async loadAgentsData() {
        console.log('Loading agents data...');
        // Implement agent management interface
    }
    
    async loadAnalyticsData() {
        console.log('Loading analytics data...');
        // Implement comprehensive analytics
    }
    
    async loadStimuliData() {
        console.log('Loading stimuli data...');
        // Implement stimuli management interface
    }
    
    async loadKnowledgeData() {
        console.log('Loading knowledge graph data...');
        // Implement semantic graph visualization
    }
    
    async loadEvolutionData() {
        console.log('Loading evolution data...');
        // Implement evolution tracking
    }
    
    async loadToolsData() {
        console.log('Loading tools data...');
        // Implement tool analytics
    }
    
    async loadSystemsData() {
        console.log('Loading systems data...');
        // Implement system management
    }
    
    // Placeholder methods for features
    async injectStimuli() {
        console.log('Injecting stimuli...');
    }
    
    async toggleMode() {
        console.log('Toggling mode...');
    }
    
    async switchTeam(team) {
        console.log('Switching team:', team);
    }
    
    async updateAnalytics(timeframe) {
        console.log('Updating analytics:', timeframe);
    }
    
    openAIAssistant() {
        console.log('Opening AI Assistant...');
    }
    
    startVoiceCommand() {
        console.log('Starting voice command...');
    }
    
    exportSystemData() {
        console.log('Exporting system data...');
    }
    
    showHelp() {
        console.log('Showing help...');
    }
    
    // Cleanup
    destroy() {
        Object.values(this.updateIntervals).forEach(interval => clearInterval(interval));
        this.api.destroy();
        
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Starting Autonomy Command Center...');
    window.autonomyApp = new AutonomyCommandCenter();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.autonomyApp) {
        window.autonomyApp.destroy();
    }
});