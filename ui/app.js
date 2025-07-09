// Unreal Agents - Main Application with Real API Integration
class UnrealAgentsApp {
    constructor() {
        this.currentView = 'dashboard';
        this.api = new APIClient();
        this.agents = [];
        this.websockets = {};
        this.charts = {};
        this.knowledgeGraph = null;
        this.systemHealth = null;
        this.updateInterval = null;
        
        this.init();
    }
    
    async init() {
        this.setupNavigation();
        this.setupEmergencyStop();
        this.initializeCharts();
        this.setupInteractions();
        
        // Load real data
        await this.loadSystemData();
        
        // Start real-time updates
        this.initializeWebSockets();
        this.startLiveUpdates();
        
        // Update connection status
        this.updateConnectionStatus();
    }
    
    async loadSystemData() {
        try {
            // Load real system data
            const [health, performance, learning, persona, stimuli] = await Promise.allSettled([
                this.api.getSystemHealth(),
                this.api.getPerformanceAnalytics(),
                this.api.getAgentLearning(),
                this.api.getPersonaStatus(),
                this.api.getStimuliStatus()
            ]);

            this.systemHealth = health.status === 'fulfilled' ? health.value : null;
            
            // Transform real data into agent format
            this.agents = this.transformToAgentFormat(
                performance.status === 'fulfilled' ? performance.value : null,
                learning.status === 'fulfilled' ? learning.value : null,
                persona.status === 'fulfilled' ? persona.value : null,
                stimuli.status === 'fulfilled' ? stimuli.value : null
            );
            
            this.updateAgentCards();
            this.updateSystemMetrics();
            
        } catch (error) {
            console.error('Failed to load system data:', error);
            this.showConnectionError();
        }
    }

    transformToAgentFormat(performance, learning, persona, stimuli) {
        const baseAgents = [
            {
                id: 'cognitive',
                name: 'Cognitive AI',
                type: 'cognitive',
                icon: '🧠',
                color: '#00ffff'
            },
            {
                id: 'programmer',
                name: 'Programmer',
                type: 'programmer',
                icon: '💻',
                color: '#ff00ff'
            },
            {
                id: 'observer',
                name: 'Observer',
                type: 'observer',
                icon: '👁',
                color: '#ffff00'
            },
            {
                id: 'executor',
                name: 'Code Executor',
                type: 'executor',
                icon: '⚡',
                color: '#00ff88'
            }
        ];

        return baseAgents.map(agent => ({
            ...agent,
            status: this.systemHealth?.autogen?.status === 'healthy' ? 'active' : 'error',
            metrics: {
                success: performance?.success_rate || 0,
                response: performance?.average_response_time || 0,
                tasks: learning?.memory_entries || 0
            },
            currentTask: this.generateTaskFromStatus(agent.type, persona, stimuli)
        }));
    }

    generateTaskFromStatus(agentType, persona, stimuli) {
        const tasks = {
            cognitive: persona?.current_persona ? `Operating as ${persona.current_persona}` : 'Processing cognitive tasks...',
            programmer: 'Optimizing code execution...',
            observer: stimuli?.orchestrator_status === 'active' ? 'Monitoring stimuli processing...' : 'Observing system state...',
            executor: 'Executing validation checks...'
        };
        
        return tasks[agentType] || 'Active...';
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
        // Update nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.view === view);
        });
        
        // Update view sections
        document.querySelectorAll('.view-section').forEach(section => {
            section.classList.toggle('active', section.id === `${view}-view`);
        });
        
        this.currentView = view;
        
        // Initialize view-specific features
        if (view === 'knowledge' && !this.knowledgeGraph) {
            this.initializeKnowledgeGraph();
        }
    }
    
    setupEmergencyStop() {
        const emergencyBtn = document.querySelector('.emergency-stop');
        const modal = document.getElementById('emergency-modal');
        
        emergencyBtn.addEventListener('click', () => {
            modal.classList.add('active');
        });
        
        modal.querySelector('.modal-btn.danger').addEventListener('click', () => {
            this.executeEmergencyStop();
            modal.classList.remove('active');
        });
        
        modal.querySelector('.modal-btn.secondary').addEventListener('click', () => {
            modal.classList.remove('active');
        });
    }
    
    async executeEmergencyStop() {
        try {
            // Pause stimuli processing
            await this.api.pauseStimuliProcessing();
            
            // Update UI
            this.agents.forEach(agent => {
                agent.status = 'error';
                agent.currentTask = 'EMERGENCY STOP - All operations halted';
            });
            
            this.updateAgentCards();
            this.addActivityItem('SYSTEM', 'Emergency stop executed - All agents halted', 'error');
            
            // Update connection status
            this.updateConnectionStatus('emergency_stop');
            
        } catch (error) {
            console.error('Emergency stop failed:', error);
            this.addActivityItem('SYSTEM', 'Emergency stop failed - Check system status', 'error');
        }
    }
    
    initializeCharts() {
        // CPU Chart
        const cpuCanvas = document.getElementById('cpu-chart');
        if (cpuCanvas) {
            const ctx = cpuCanvas.getContext('2d');
            this.drawLineChart(ctx, this.generateChartData(30, 20, 60), '#00ffff');
        }
        
        // Memory Chart
        const memCanvas = document.getElementById('memory-chart');
        if (memCanvas) {
            const ctx = memCanvas.getContext('2d');
            this.drawLineChart(ctx, this.generateChartData(30, 60, 80), '#ff00ff');
        }
        
        // Throughput Chart
        const throughputCanvas = document.getElementById('throughput-chart');
        if (throughputCanvas) {
            const ctx = throughputCanvas.getContext('2d');
            this.drawLineChart(ctx, this.generateChartData(30, 800, 1500), '#ffff00');
        }
        
        // Initialize sparklines
        this.initializeSparklines();
    }
    
    drawLineChart(ctx, data, color) {
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;
        
        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const stepX = width / (data.length - 1);
        const maxValue = Math.max(...data);
        const minValue = Math.min(...data);
        const range = maxValue - minValue;
        
        data.forEach((value, index) => {
            const x = index * stepX;
            const y = height - ((value - minValue) / range) * height;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Add glow effect
        ctx.shadowBlur = 10;
        ctx.shadowColor = color;
        ctx.stroke();
    }
    
    generateChartData(points, min, max) {
        const data = [];
        for (let i = 0; i < points; i++) {
            data.push(min + Math.random() * (max - min));
        }
        return data;
    }
    
    initializeSparklines() {
        const sparklines = [
            { id: 'performance-sparkline', color: '#00ff88' },
            { id: 'memory-sparkline', color: '#00ffff' },
            { id: 'latency-sparkline', color: '#ff00ff' },
            { id: 'error-sparkline', color: '#ff0044' }
        ];
        
        sparklines.forEach(sparkline => {
            const canvas = document.getElementById(sparkline.id);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                this.drawSparkline(ctx, this.generateChartData(20, 0, 100), sparkline.color);
            }
        });
    }
    
    drawSparkline(ctx, data, color) {
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;
        
        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        
        const stepX = width / (data.length - 1);
        
        data.forEach((value, index) => {
            const x = index * stepX;
            const y = height - (value / 100) * height;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
    }
    
    initializeWebSockets() {
        // Connect to dashboard WebSocket
        this.api.connectWebSocket('dashboard', 
            (data) => this.handleDashboardUpdate(data),
            (error) => this.handleWebSocketError('dashboard', error)
        );
        
        // Connect to stimuli WebSocket
        this.api.connectWebSocket('stimuli',
            (data) => this.handleStimuliUpdate(data),
            (error) => this.handleWebSocketError('stimuli', error)
        );
    }

    handleDashboardUpdate(data) {
        if (data.type === 'system_update') {
            this.updateSystemMetrics(data.data);
        } else if (data.type === 'agent_update') {
            this.updateAgentStatus(data.data);
        } else if (data.type === 'activity') {
            this.addActivityItem(data.agent, data.message, data.level || 'info');
        }
    }

    handleStimuliUpdate(data) {
        if (data.type === 'stimuli_update') {
            this.addActivityItem('Stimuli Processor', `Processing: ${data.data.content}`, 'info');
        } else if (data.type === 'stimuli_completed') {
            this.addActivityItem('Stimuli Processor', `Completed: ${data.data.result}`, 'success');
        }
    }

    handleWebSocketError(type, error) {
        console.error(`WebSocket ${type} error:`, error);
        this.addActivityItem('SYSTEM', `WebSocket ${type} connection lost`, 'warning');
        this.updateConnectionStatus('error');
    }
    
    startLiveUpdates() {
        // Update system data every 5 seconds
        this.updateInterval = setInterval(async () => {
            try {
                await this.refreshSystemData();
            } catch (error) {
                console.error('Failed to refresh system data:', error);
            }
        }, 5000);
        
        // Update charts every 2 seconds
        setInterval(() => {
            this.updateCharts();
        }, 2000);
    }

    async refreshSystemData() {
        try {
            const [health, performance, gpu] = await Promise.allSettled([
                this.api.getSystemHealth(),
                this.api.getPerformanceAnalytics(),
                this.api.getGPUStatus()
            ]);

            if (health.status === 'fulfilled') {
                this.systemHealth = health.value;
                this.updateConnectionStatus();
            }

            if (performance.status === 'fulfilled') {
                this.updateAgentMetrics(performance.value);
            }

            if (gpu.status === 'fulfilled') {
                this.updateGPUMetrics(gpu.value);
            }

        } catch (error) {
            console.error('Failed to refresh system data:', error);
            this.updateConnectionStatus('error');
        }
    }

    updateAgentMetrics(performance) {
        this.agents.forEach(agent => {
            agent.metrics.success = performance.success_rate || agent.metrics.success;
            agent.metrics.response = performance.average_response_time || agent.metrics.response;
            agent.status = this.systemHealth?.autogen?.status === 'healthy' ? 'active' : 'error';
        });
        
        this.updateAgentCards();
    }

    updateGPUMetrics(gpu) {
        // Update GPU chart data
        const gpuCanvas = document.getElementById('cpu-chart');
        if (gpuCanvas) {
            const ctx = gpuCanvas.getContext('2d');
            const utilization = gpu.gpu_utilization || 0;
            // Generate chart data based on real GPU utilization
            const chartData = Array.from({length: 30}, (_, i) => 
                utilization + (Math.random() - 0.5) * 10
            );
            this.drawLineChart(ctx, chartData, '#00ffff');
        }
    }

    updateConnectionStatus(status = null) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (!statusDot || !statusText) return;
        
        let connectionStatus = 'offline';
        let statusMessage = 'OFFLINE';
        
        if (status === 'emergency_stop') {
            connectionStatus = 'warning';
            statusMessage = 'EMERGENCY STOP';
        } else if (status === 'error') {
            connectionStatus = 'offline';
            statusMessage = 'CONNECTION ERROR';
        } else if (this.systemHealth?.autogen?.status === 'healthy') {
            connectionStatus = 'online';
            statusMessage = 'CONNECTED';
        }
        
        statusDot.className = `status-dot ${connectionStatus}`;
        statusText.textContent = statusMessage;
    }

    showConnectionError() {
        this.addActivityItem('SYSTEM', 'Failed to connect to backend services', 'error');
        this.updateConnectionStatus('error');
    }
    
    updateAgentCards() {
        const agentsGrid = document.querySelector('.agents-grid');
        if (!agentsGrid) return;
        
        // Clear existing cards
        agentsGrid.innerHTML = '';
        
        // Create cards for each agent
        this.agents.forEach(agent => {
            const card = this.createAgentCard(agent);
            agentsGrid.appendChild(card);
        });
    }
    
    createAgentCard(agent) {
        const card = document.createElement('div');
        card.className = `agent-card ${agent.status}`;
        card.innerHTML = `
            <div class="agent-avatar">
                <div class="avatar-ring ${agent.type}"></div>
                <span class="agent-icon">${agent.icon}</span>
            </div>
            <h3 class="agent-name">${agent.name}</h3>
            <div class="agent-status">
                <span class="status-indicator ${agent.status}"></span>
                <span class="status-label">${agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}</span>
            </div>
            <div class="agent-metrics">
                <div class="metric">
                    <span class="metric-value">${agent.metrics.success}%</span>
                    <span class="metric-label">Success</span>
                </div>
                <div class="metric">
                    <span class="metric-value">${agent.metrics.response.toFixed(0)}ms</span>
                    <span class="metric-label">Response</span>
                </div>
            </div>
            <div class="agent-task">${agent.currentTask}</div>
        `;
        
        return card;
    }
    
    addActivityItem(agent, message, type = 'info') {
        const feed = document.querySelector('.activity-feed');
        if (!feed) return;
        
        const item = document.createElement('div');
        item.className = `activity-item ${type}`;
        item.innerHTML = `
            <span class="activity-time">${new Date().toLocaleTimeString()}</span>
            <span class="activity-agent">[${agent}]</span>
            <span class="activity-message">${message}</span>
        `;
        
        feed.insertBefore(item, feed.firstChild);
        
        // Limit to 20 items
        while (feed.children.length > 20) {
            feed.removeChild(feed.lastChild);
        }
    }
    
    updateCharts() {
        // Update main charts
        const cpuCanvas = document.getElementById('cpu-chart');
        if (cpuCanvas) {
            const ctx = cpuCanvas.getContext('2d');
            this.drawLineChart(ctx, this.generateChartData(30, 20, 60), '#00ffff');
        }
        
        // Update metric values
        document.querySelector('.metrics-grid .metric-value').textContent = 
            (20 + Math.random() * 40).toFixed(0) + '%';
    }
    
    setupInteractions() {
        // Character customization
        this.setupCharacterCustomization();
        
        // Command center
        this.setupCommandCenter();
        
        // Conversation input
        this.setupConversation();
    }
    
    setupCharacterCustomization() {
        // Trait sliders
        document.querySelectorAll('.trait-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const value = e.target.value;
                e.target.parentElement.querySelector('.trait-value').textContent = value + '%';
            });
        });
        
        // Custom tabs
        document.querySelectorAll('.custom-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const custom = e.target.dataset.custom;
                
                // Update tabs
                document.querySelectorAll('.custom-tab').forEach(t => {
                    t.classList.toggle('active', t.dataset.custom === custom);
                });
                
                // Update panels
                document.querySelectorAll('.custom-panel').forEach(panel => {
                    panel.classList.toggle('active', panel.id === `${custom}-panel`);
                });
            });
        });
    }
    
    setupCommandCenter() {
        // Template buttons
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.currentTarget.dataset.command;
                const commandInput = document.querySelector('.command-input');
                
                const templates = {
                    analyze: 'Analyze the current context and provide insights on optimization opportunities',
                    optimize: 'Optimize system performance and resource allocation',
                    report: 'Generate comprehensive report on agent activities and performance metrics',
                    sync: 'Synchronize knowledge base across all agents'
                };
                
                commandInput.value = templates[command] || '';
            });
        });
        
        // Execute button
        document.querySelector('.execute-btn').addEventListener('click', () => {
            this.executeCommand();
        });
    }
    
    async executeCommand() {
        const commandInput = document.querySelector('.command-input');
        const targetSelect = document.querySelector('.target-select');
        const prioritySelect = document.querySelector('.priority-select');
        
        const command = commandInput.value.trim();
        if (!command) return;
        
        const target = targetSelect.value;
        const priority = prioritySelect.value;
        
        // Add to history
        this.addCommandHistory(command, target, priority);
        
        try {
            // Submit command as stimuli
            const result = await this.api.submitStimuli(command, 'command', priority);
            
            if (result) {
                this.addActivityItem(
                    target === 'all' ? 'All Agents' : this.agents.find(a => a.id === target)?.name || target,
                    `Command submitted: ${command.substring(0, 50)}...`,
                    'info'
                );
            } else {
                this.addActivityItem(
                    'SYSTEM',
                    'Failed to submit command',
                    'error'
                );
            }
            
        } catch (error) {
            console.error('Command execution failed:', error);
            this.addActivityItem(
                'SYSTEM',
                'Command execution failed - Check connection',
                'error'
            );
        }
        
        // Clear input
        commandInput.value = '';
    }
    
    addCommandHistory(command, target, priority) {
        const historyList = document.querySelector('.history-list');
        if (!historyList) return;
        
        const item = document.createElement('div');
        item.className = 'history-item pending';
        item.innerHTML = `
            <div class="history-header">
                <span class="history-time">${new Date().toLocaleTimeString()}</span>
                <span class="history-target">[${target === 'all' ? 'All Agents' : target}]</span>
                <span class="history-status pending">Pending</span>
            </div>
            <div class="history-command">${command}</div>
        `;
        
        historyList.insertBefore(item, historyList.firstChild);
        
        // Simulate command completion
        setTimeout(() => {
            item.classList.remove('pending');
            item.classList.add('success');
            item.querySelector('.history-status').classList.remove('pending');
            item.querySelector('.history-status').classList.add('success');
            item.querySelector('.history-status').textContent = 'Success';
        }, 2000 + Math.random() * 3000);
    }
    
    setupConversation() {
        const input = document.querySelector('.message-input');
        const sendBtn = document.querySelector('.send-btn');
        
        const sendMessage = () => {
            const message = input.value.trim();
            if (!message) return;
            
            // Add user message
            this.addConversationMessage('User', message, 'user');
            
            // Simulate agent response
            setTimeout(() => {
                const agent = this.agents[Math.floor(Math.random() * this.agents.length)];
                const responses = [
                    'Acknowledged. Processing your request...',
                    'I understand. Let me analyze this further.',
                    'Executing the requested operation now.',
                    'Interesting query. I have some insights to share.',
                    'Task initiated. Expected completion in 2.3 seconds.'
                ];
                
                this.addConversationMessage(
                    agent.name,
                    responses[Math.floor(Math.random() * responses.length)],
                    agent.type
                );
            }, 1000 + Math.random() * 1000);
            
            input.value = '';
        };
        
        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
    
    addConversationMessage(agent, content, type) {
        const conversationView = document.querySelector('.conversation-view');
        if (!conversationView) return;
        
        const message = document.createElement('div');
        message.className = `message ${type}`;
        message.innerHTML = `
            <div class="message-header">
                <span class="message-agent">${agent}</span>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="message-content">${content}</div>
        `;
        
        conversationView.appendChild(message);
        conversationView.scrollTop = conversationView.scrollHeight;
    }
    
    async initializeKnowledgeGraph() {
        const canvas = document.getElementById('knowledge-graph');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        
        try {
            // Load real semantic map data
            const semanticData = await this.api.exportSemanticMap();
            
            if (semanticData) {
                this.drawRealKnowledgeGraph(ctx, semanticData);
            } else {
                // Fallback to basic visualization
                this.drawKnowledgeGraph(ctx);
            }
        } catch (error) {
            console.error('Failed to load semantic map:', error);
            this.drawKnowledgeGraph(ctx);
        }
    }
    
    drawRealKnowledgeGraph(ctx, data) {
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;
        
        // Clear canvas
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, width, height);
        
        if (!data || !data.nodes || !data.links) {
            this.drawKnowledgeGraph(ctx);
            return;
        }
        
        // Position nodes using force-directed layout
        const nodes = data.nodes.map((node, i) => ({
            ...node,
            x: (Math.random() * 0.8 + 0.1) * width,
            y: (Math.random() * 0.8 + 0.1) * height,
            radius: Math.max(8, Math.min(25, (node.weight || 1) * 5)),
            color: this.getNodeColor(node.type || 'default')
        }));
        
        // Draw connections based on real semantic relationships
        ctx.strokeStyle = 'rgba(0, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        
        data.links.forEach(link => {
            const sourceNode = nodes[link.source];
            const targetNode = nodes[link.target];
            
            if (sourceNode && targetNode) {
                const strength = link.weight || 1;
                ctx.globalAlpha = Math.min(1, strength * 0.5);
                ctx.lineWidth = Math.max(1, strength * 2);
                
                ctx.beginPath();
                ctx.moveTo(sourceNode.x, sourceNode.y);
                ctx.lineTo(targetNode.x, targetNode.y);
                ctx.stroke();
            }
        });
        
        // Draw nodes with labels
        ctx.globalAlpha = 1;
        nodes.forEach(node => {
            // Node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
            ctx.fillStyle = node.color;
            ctx.globalAlpha = 0.8;
            ctx.fill();
            
            // Node border
            ctx.strokeStyle = node.color;
            ctx.lineWidth = 2;
            ctx.globalAlpha = 1;
            ctx.stroke();
            
            // Node label
            if (node.label && node.radius > 12) {
                ctx.fillStyle = '#ffffff';
                ctx.font = '10px Orbitron';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(
                    node.label.substring(0, 8),
                    node.x,
                    node.y
                );
            }
        });
        
        // Add legend
        this.drawGraphLegend(ctx, width, height);
    }
    
    getNodeColor(type) {
        const colors = {
            'concept': '#00ffff',
            'entity': '#ff00ff',
            'relation': '#ffff00',
            'memory': '#00ff88',
            'goal': '#ff8800',
            'tool': '#8800ff',
            'default': '#ffffff'
        };
        return colors[type] || colors.default;
    }
    
    drawGraphLegend(ctx, width, height) {
        const legend = [
            { label: 'Concept', color: '#00ffff' },
            { label: 'Entity', color: '#ff00ff' },
            { label: 'Relation', color: '#ffff00' },
            { label: 'Memory', color: '#00ff88' }
        ];
        
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        ctx.fillRect(width - 150, 10, 140, 90);
        
        legend.forEach((item, i) => {
            const y = 30 + i * 20;
            
            // Color dot
            ctx.fillStyle = item.color;
            ctx.beginPath();
            ctx.arc(width - 135, y, 5, 0, Math.PI * 2);
            ctx.fill();
            
            // Label
            ctx.fillStyle = '#ffffff';
            ctx.font = '12px Rajdhani';
            ctx.textAlign = 'left';
            ctx.fillText(item.label, width - 125, y + 4);
        });
    }
    
    drawKnowledgeGraph(ctx) {
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;
        
        // Clear canvas
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, width, height);
        
        // Generate random nodes
        const nodes = [];
        const nodeCount = 20;
        
        for (let i = 0; i < nodeCount; i++) {
            nodes.push({
                x: Math.random() * width,
                y: Math.random() * height,
                radius: 10 + Math.random() * 20,
                color: ['#00ffff', '#ff00ff', '#ffff00'][Math.floor(Math.random() * 3)]
            });
        }
        
        // Draw connections
        ctx.strokeStyle = 'rgba(0, 255, 255, 0.2)';
        ctx.lineWidth = 1;
        
        nodes.forEach((node, i) => {
            // Connect to 2-3 random nodes
            const connections = Math.floor(Math.random() * 2) + 2;
            for (let j = 0; j < connections; j++) {
                const target = nodes[Math.floor(Math.random() * nodes.length)];
                if (target !== node) {
                    ctx.beginPath();
                    ctx.moveTo(node.x, node.y);
                    ctx.lineTo(target.x, target.y);
                    ctx.stroke();
                }
            }
        });
        
        // Draw nodes
        nodes.forEach(node => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
            ctx.fillStyle = node.color;
            ctx.globalAlpha = 0.8;
            ctx.fill();
            ctx.strokeStyle = node.color;
            ctx.lineWidth = 2;
            ctx.stroke();
        });
        
        ctx.globalAlpha = 1;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.unrealAgents = new UnrealAgentsApp();
});

// Voice command placeholder
document.getElementById('voice-command')?.addEventListener('click', () => {
    alert('Voice command feature coming soon!');
});

// Quick help
document.getElementById('quick-help')?.addEventListener('click', () => {
    alert('Unreal Agents Help:\n\n• Dashboard: Monitor agent status and activity\n• Character: Customize agent personality\n• Commands: Send instructions to agents\n• Health: View system performance\n• Knowledge: Explore semantic graph');
});

// Backend Connection Testing
class BackendTester {
    constructor() {
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.testBtn = document.getElementById('testConnectionBtn');
        this.autogenStatus = document.getElementById('autogenStatus');
        this.graphflowStatus = document.getElementById('graphflowStatus'); 
        this.neurosyncStatus = document.getElementById('neurosyncStatus');
        
        this.setupEventListeners();
        this.startConnectionTesting();
    }
    
    setupEventListeners() {
        this.testBtn?.addEventListener('click', () => this.testAllConnections());
    }
    
    async startConnectionTesting() {
        this.updateStatus('testing', 'TESTING BACKEND...');
        await this.testAllConnections();
        
        // Set up periodic testing every 30 seconds
        setInterval(() => this.testAllConnections(), 30000);
    }
    
    async testAllConnections() {
        this.testBtn.disabled = true;
        this.testBtn.textContent = 'TESTING...';
        
        const results = {
            autogen: await this.testService('http://autogen-agent:8000/health', 'AutoGen'),
            graphflow: await this.testService('http://graphflow-gateway:8080/health', 'GraphFlow'),
            neurosync: await this.testService('http://neurosync:5001/health', 'NeuroSync')
        };
        
        this.updateServiceStatus('autogenStatus', results.autogen);
        this.updateServiceStatus('graphflowStatus', results.graphflow);
        this.updateServiceStatus('neurosyncStatus', results.neurosync);
        
        const allOnline = Object.values(results).every(r => r.status === 'online');
        const anyOnline = Object.values(results).some(r => r.status === 'online');
        
        if (allOnline) {
            this.updateStatus('online', 'ALL SYSTEMS ONLINE');
        } else if (anyOnline) {
            this.updateStatus('warning', 'PARTIAL CONNECTION');
        } else {
            this.updateStatus('offline', 'BACKEND OFFLINE');
        }
        
        this.testBtn.disabled = false;
        this.testBtn.textContent = 'TEST APIs';
        
        // Add activity log entry
        this.addConnectionLog(results);
    }
    
    async testService(url, serviceName) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                const data = await response.json();
                return {
                    status: 'online',
                    message: `${serviceName} responding`,
                    data: data
                };
            } else {
                return {
                    status: 'error',
                    message: `${serviceName} error: ${response.status}`,
                    data: null
                };
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                return {
                    status: 'timeout',
                    message: `${serviceName} timeout`,
                    data: null
                };
            }
            return {
                status: 'offline',
                message: `${serviceName} unreachable: ${error.message}`,
                data: null
            };
        }
    }
    
    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
    }
    
    updateServiceStatus(elementId, result) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const stateElement = element.querySelector('.service-state');
        
        switch (result.status) {
            case 'online':
                stateElement.textContent = '✓';
                stateElement.style.color = 'var(--success)';
                break;
            case 'error':
                stateElement.textContent = '⚠';
                stateElement.style.color = 'var(--warning)';
                break;
            case 'timeout':
                stateElement.textContent = '⧗';
                stateElement.style.color = 'var(--warning)';
                break;
            case 'offline':
            default:
                stateElement.textContent = '✗';
                stateElement.style.color = 'var(--danger)';
                break;
        }
        
        element.title = result.message;
    }
    
    addConnectionLog(results) {
        // Add to activity feed if it exists
        const app = window.unrealAgentsApp;
        if (app && app.addActivityItem) {
            const onlineServices = Object.entries(results)
                .filter(([_, result]) => result.status === 'online')
                .map(([service, _]) => service);
            
            if (onlineServices.length > 0) {
                app.addActivityItem(
                    'Connection Test',
                    `Services online: ${onlineServices.join(', ')}`,
                    'info'
                );
            } else {
                app.addActivityItem(
                    'Connection Test',
                    'All backend services offline - using mock data',
                    'warning'
                );
            }
        }
    }
}

// API Response Manager
class APIResponseManager {
    constructor() {
        this.responseLog = document.getElementById('responseLog');
        this.responseStatus = document.getElementById('responseStatus');
        this.clearBtn = document.getElementById('clearApiLog');
        this.testBtn = document.getElementById('testApiEndpoints');
        
        this.setupEventListeners();
        this.clearLog();
    }
    
    setupEventListeners() {
        // Endpoint test buttons
        document.querySelectorAll('.endpoint-test-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const endpoint = e.target.dataset.endpoint;
                this.testEndpoint(endpoint);
            });
        });
        
        // Clear log button
        this.clearBtn?.addEventListener('click', () => this.clearLog());
        
        // Test all endpoints button
        this.testBtn?.addEventListener('click', () => this.testAllEndpoints());
    }
    
    async testEndpoint(endpoint) {
        const timestamp = new Date().toLocaleTimeString();
        this.updateStatus('Testing...');
        
        let url, method = 'GET', body = null;
        
        // Define endpoint URLs and parameters
        switch (endpoint) {
            case 'autogen-health':
                url = 'http://autogen-agent:8000/health';
                break;
            case 'autogen-agents':
                url = 'http://autogen-agent:8000/agents';
                break;
            case 'autogen-stimuli':
                url = 'http://autogen-agent:8000/stimuli';
                method = 'POST';
                body = JSON.stringify({
                    content: 'Test stimuli from UI',
                    type: 'test',
                    priority: 'medium'
                });
                break;
            case 'graphflow-health':
                url = 'http://graphflow-gateway:8080/health';
                break;
            case 'graphflow-semantic':
                url = 'http://graphflow-gateway:8080/semantic/export';
                break;
            case 'graphflow-memory':
                url = 'http://graphflow-gateway:8080/memory/status';
                break;
            case 'neurosync-health':
                url = 'http://neurosync:5001/health';
                break;
            case 'neurosync-process':
                url = 'http://neurosync:5001/process';
                method = 'POST';
                body = JSON.stringify({
                    text: 'Hello from Unreal Agents UI',
                    enable_voice: false
                });
                break;
            case 'neurosync-character':
                url = 'http://neurosync:5001/character';
                break;
            default:
                this.addLogEntry('error', timestamp, `Unknown endpoint: ${endpoint}`, null);
                return;
        }
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: body,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            const responseData = await response.json();
            
            if (response.ok) {
                this.addLogEntry('success', timestamp, 
                    `${endpoint} → SUCCESS (${response.status})`, responseData);
                this.updateStatus('Success');
            } else {
                this.addLogEntry('error', timestamp, 
                    `${endpoint} → ERROR (${response.status})`, responseData);
                this.updateStatus('Error');
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                this.addLogEntry('warning', timestamp, 
                    `${endpoint} → TIMEOUT (10s exceeded)`, null);
                this.updateStatus('Timeout');
            } else {
                this.addLogEntry('error', timestamp, 
                    `${endpoint} → FAILED: ${error.message}`, null);
                this.updateStatus('Failed');
            }
        }
    }
    
    async testAllEndpoints() {
        this.clearLog();
        this.updateStatus('Testing all endpoints...');
        
        const endpoints = [
            'autogen-health', 'autogen-agents',
            'graphflow-health', 'graphflow-semantic', 
            'neurosync-health', 'neurosync-character'
        ];
        
        for (const endpoint of endpoints) {
            await this.testEndpoint(endpoint);
            await new Promise(resolve => setTimeout(resolve, 500)); // Small delay between tests
        }
        
        this.updateStatus('All tests completed');
    }
    
    addLogEntry(type, timestamp, message, data) {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        
        const timeElement = document.createElement('span');
        timeElement.className = 'log-time';
        timeElement.textContent = timestamp;
        
        const messageElement = document.createElement('span');
        messageElement.className = 'log-message';
        messageElement.textContent = message;
        
        entry.appendChild(timeElement);
        entry.appendChild(messageElement);
        
        if (data) {
            const dataElement = document.createElement('div');
            dataElement.style.marginTop = '0.5rem';
            dataElement.style.padding = '0.5rem';
            dataElement.style.background = 'rgba(0, 255, 255, 0.1)';
            dataElement.style.borderRadius = '4px';
            dataElement.style.fontSize = '0.75rem';
            dataElement.style.color = '#00ffff';
            dataElement.textContent = JSON.stringify(data, null, 2);
            entry.appendChild(dataElement);
        }
        
        this.responseLog.insertBefore(entry, this.responseLog.firstChild);
        
        // Limit to 50 entries
        while (this.responseLog.children.length > 50) {
            this.responseLog.removeChild(this.responseLog.lastChild);
        }
    }
    
    updateStatus(status) {
        if (this.responseStatus) {
            this.responseStatus.textContent = status;
        }
    }
    
    clearLog() {
        if (this.responseLog) {
            this.responseLog.innerHTML = `
                <div class="log-entry">
                    <span class="log-time">Ready</span>
                    <span class="log-message">Click any endpoint test button to see real API responses</span>
                </div>
            `;
        }
        this.updateStatus('Ready');
    }
}

// Initialize backend tester when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.backendTester = new BackendTester();
    window.apiResponseManager = new APIResponseManager();
});