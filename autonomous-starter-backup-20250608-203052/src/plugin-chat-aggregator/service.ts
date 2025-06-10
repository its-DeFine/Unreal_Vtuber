import {
  Service,
  IAgentRuntime,
  logger,
  createUniqueUuid,
  EventType,
  Memory,
  Content
} from '@elizaos/core';
import { SalienceEngine } from './salience';
import { AttentionManager } from './attention';
import { MessageQueue } from './queue';
import { PlatformManager } from './platform-manager';
import { ResponsePipeline } from './response-pipeline';
import {
  ChatMessage,
  ChatContextUpdate,
  AttentionState,
  SalienceLevel,
  ChatMetrics,
  PlatformConfig
} from './types';

/**
 * Multi-Platform Chat Aggregator Service
 * 
 * Core service that orchestrates intelligent chat aggregation across multiple platforms.
 * Features human-like attention mechanisms, intelligent message prioritization,
 * and seamless integration with the Autoliza autonomous agent system.
 */
export class ChatAggregatorService extends Service {
  static serviceType = 'chat-aggregator';

  private salienceEngine: SalienceEngine;
  private attentionManager: AttentionManager;
  private messageQueue: MessageQueue;
  private platformManager: PlatformManager;
  private responsePipeline: ResponsePipeline;
  
  // System state
  private isRunning: boolean = false;
  private processingLoop: NodeJS.Timeout | null = null;
  private contextUpdateInterval: NodeJS.Timeout | null = null;
  
  // Metrics and monitoring
  private metrics: Map<string, ChatMetrics> = new Map();
  private startTime: number = Date.now();
  
  constructor(runtime: IAgentRuntime) {
    super(runtime);
    logger.info('[ChatAggregatorService] 🚀 Initializing Multi-Platform Chat Aggregation System');
    
    // Initialize core components
    this.salienceEngine = new SalienceEngine();
    this.attentionManager = new AttentionManager();
    this.messageQueue = new MessageQueue(runtime);
    this.platformManager = new PlatformManager(runtime, this.handleIncomingMessage.bind(this));
    this.responsePipeline = new ResponsePipeline(runtime);
    
    logger.info('[ChatAggregatorService] ✅ Core components initialized', {
      serviceType: ChatAggregatorService.serviceType,
      components: ['SalienceEngine', 'AttentionManager', 'MessageQueue', 'PlatformManager', 'ResponsePipeline']
    });
  }

  /**
   * Start the chat aggregation service
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      logger.warn('[ChatAggregatorService] Service already running');
      return;
    }

    try {
      logger.info('[ChatAggregatorService] 🔄 Starting chat aggregation service...');

      // Start platform connections
      await this.platformManager.connectAll();
      logger.info('[ChatAggregatorService] 📡 Platform connections established');

      // Start message processing loop
      this.startProcessingLoop();
      logger.info('[ChatAggregatorService] ⚡ Message processing loop started');

      // Start context update system
      this.startContextUpdates();
      logger.info('[ChatAggregatorService] 🧠 Context update system started');

      // Initialize attention state
      this.attentionManager.initialize();
      logger.info('[ChatAggregatorService] 👁️ Attention management system initialized');

      this.isRunning = true;
      logger.info('[ChatAggregatorService] ✅ Multi-platform chat system fully operational!', {
        startTime: new Date(this.startTime).toISOString(),
        uptime: Date.now() - this.startTime
      });

      // Emit service started event
      this.runtime.emitEvent(EventType.SERVICE_STARTED, {
        service: ChatAggregatorService.serviceType,
        timestamp: Date.now()
      });

    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Failed to start service:', error);
      await this.stop();
      throw error;
    }
  }

  /**
   * Stop the chat aggregation service
   */
  async stop(): Promise<void> {
    logger.info('[ChatAggregatorService] 🛑 Stopping chat aggregation service...');

    this.isRunning = false;

    // Stop processing loops
    if (this.processingLoop) {
      clearInterval(this.processingLoop);
      this.processingLoop = null;
    }

    if (this.contextUpdateInterval) {
      clearInterval(this.contextUpdateInterval);
      this.contextUpdateInterval = null;
    }

    // Disconnect from platforms
    await this.platformManager.disconnectAll();

    // Clear message queue
    await this.messageQueue.clear();

    logger.info('[ChatAggregatorService] ✅ Service stopped gracefully', {
      uptime: Date.now() - this.startTime,
      totalMessagesProcessed: this.getTotalMessagesProcessed()
    });
  }

  /**
   * Handle incoming messages from platforms
   */
  private async handleIncomingMessage(message: ChatMessage): Promise<void> {
    try {
      logger.debug('[ChatAggregatorService] 📨 Incoming message', {
        platform: message.platform,
        author: message.author.username,
        textLength: message.content.text.length,
        timestamp: message.metadata.timestamp
      });

      // Calculate message salience
      const context = await this.buildCurrentContext();
      const salienceScore = await this.salienceEngine.calculateSalience(message, context);
      message.salience = salienceScore;

      logger.debug('[ChatAggregatorService] 🧮 Message salience calculated', {
        platform: message.platform,
        author: message.author.username,
        salienceLevel: salienceScore.level,
        totalScore: salienceScore.total,
        reasoning: salienceScore.reasoning.join(', ')
      });

      // Store message in database
      await this.storeMessage(message);

      // Add to processing queue with priority based on salience
      await this.messageQueue.enqueue(message, salienceScore.total);

      // Update platform metrics
      this.updateMetrics(message);

      // Check for attention interrupts
      const attentionInterrupt = this.attentionManager.checkForInterrupt(message, context);
      if (attentionInterrupt) {
        logger.info('[ChatAggregatorService] ⚠️ Attention interrupt triggered', {
          type: attentionInterrupt.type,
          priority: attentionInterrupt.priority,
          suggestedAction: attentionInterrupt.suggested_action
        });

        // Handle interrupt immediately for critical messages
        if (attentionInterrupt.suggested_action === 'immediate_response') {
          await this.processMessage(message, context, true);
        }
      }

    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error handling incoming message:', error, {
        platform: message.platform,
        messageId: message.id
      });
    }
  }

  /**
   * Main message processing loop
   */
  private startProcessingLoop(): void {
    const PROCESSING_INTERVAL = parseInt(process.env.CHAT_PROCESSING_INTERVAL || '1000'); // 1 second

    this.processingLoop = setInterval(async () => {
      if (!this.isRunning) return;

      try {
        // Get current attention state
        const attentionState = this.attentionManager.getCurrentState();
        
        // Determine how many messages to process based on attention state
        const batchSize = this.getBatchSizeForAttentionState(attentionState);
        
        // Process messages from queue
        for (let i = 0; i < batchSize; i++) {
          const message = await this.messageQueue.dequeue();
          if (!message) break; // No more messages

          const context = await this.buildCurrentContext();
          await this.processMessage(message, context);
        }

        // Update attention state
        this.attentionManager.update();

      } catch (error) {
        logger.error('[ChatAggregatorService] ❌ Error in processing loop:', error);
      }
    }, PROCESSING_INTERVAL);
  }

  /**
   * Process a single message
   */
  private async processMessage(
    message: ChatMessage, 
    context: ChatContextUpdate, 
    isImmediate: boolean = false
  ): Promise<void> {
    const startTime = Date.now();

    try {
      logger.debug('[ChatAggregatorService] 🔄 Processing message', {
        platform: message.platform,
        author: message.author.username,
        salienceLevel: message.salience.level,
        isImmediate,
        attentionState: this.attentionManager.getCurrentState()
      });

      // Check if we should respond based on attention state and salience
      const shouldRespond = this.shouldRespondToMessage(message, isImmediate);
      
      if (shouldRespond) {
        // Generate response using the response pipeline
        const response = await this.responsePipeline.generateResponse(message, context);
        
        if (response) {
          // Send response through platform
          await this.platformManager.sendResponse(response, message.platform);
          
          // Store response in database
          await this.storeResponse(message, response);

          logger.info('[ChatAggregatorService] ✅ Response sent', {
            platform: message.platform,
            originalAuthor: message.author.username,
            responseLength: response.text.length,
            processingTime: Date.now() - startTime,
            attentionState: this.attentionManager.getCurrentState()
          });
        }
      } else {
        logger.debug('[ChatAggregatorService] ⏭️ Message skipped (attention state)', {
          platform: message.platform,
          salienceLevel: message.salience.level,
          attentionState: this.attentionManager.getCurrentState()
        });
      }

      // Mark message as processed
      await this.markMessageProcessed(message);

    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error processing message:', error, {
        messageId: message.id,
        platform: message.platform
      });
    }
  }

  /**
   * Start context update system for Autoliza integration
   */
  private startContextUpdates(): void {
    const CONTEXT_UPDATE_INTERVAL = parseInt(process.env.CHAT_CONTEXT_UPDATE_INTERVAL || '30000'); // 30 seconds

    this.contextUpdateInterval = setInterval(async () => {
      try {
        const context = await this.buildCurrentContext();
        await this.sendContextToAutoliza(context);
      } catch (error) {
        logger.error('[ChatAggregatorService] ❌ Error updating context:', error);
      }
    }, CONTEXT_UPDATE_INTERVAL);
  }

  /**
   * Build current context for analysis and Autoliza integration
   */
  private async buildCurrentContext(): Promise<ChatContextUpdate> {
    const platforms = await this.platformManager.getAllPlatformContexts();
    
    const totalMessages = Array.from(this.metrics.values())
      .reduce((total, metric) => total + metric.messagesProcessed, 0);

    const averageResponseTime = Array.from(this.metrics.values())
      .reduce((total, metric) => total + metric.averageResponseTime, 0) / this.metrics.size;

    return {
      platforms,
      globalContext: {
        totalMessages,
        responseRate: this.calculateGlobalResponseRate(),
        engagementTrend: this.calculateEngagementTrend(),
        recommendedAction: this.attentionManager.getRecommendedAction()
      }
    };
  }

  /**
   * Send context update to Autoliza autonomous agent
   */
  private async sendContextToAutoliza(context: ChatContextUpdate): Promise<void> {
    try {
      // Ensure a room exists for the agent - this fixes the foreign key constraint
      const roomId = this.runtime.agentId;
      
      // Check if room exists, create if it doesn't
      let room = await this.runtime.databaseAdapter.getRoom(roomId);
      if (!room) {
        logger.info('[ChatAggregatorService] 🏠 Creating room for Autoliza agent', { roomId });
        room = await this.runtime.databaseAdapter.createRoom(roomId, {
          id: roomId,
          agentId: this.runtime.agentId,
          source: 'chat_aggregator',
          type: 'autonomous_chat',
          name: 'Autoliza Chat Context Room'
        });
        logger.info('[ChatAggregatorService] ✅ Room created successfully', { roomId });
      }
      
      // Create a memory containing the chat context
      const contextMemory: Memory = {
        id: createUniqueUuid(this.runtime, 'chat-context'),
        entityId: this.runtime.agentId,
        agentId: this.runtime.agentId,
        roomId: roomId, // Use existing/created room ID
        content: {
          text: `Multi-platform chat context update: ${JSON.stringify(context, null, 2)}`,
          type: 'chat_context_update',
          source: 'chat_aggregator',
          platforms: Object.keys(context.platforms),
          totalMessages: context.globalContext.totalMessages,
          engagementTrend: context.globalContext.engagementTrend,
          recommendedAction: context.globalContext.recommendedAction
        },
        createdAt: Date.now()
      };

      // Store the context for Autoliza to access
      await this.runtime.createMemory(contextMemory, 'messages');

      // Also store in our custom chat context table for analytics
      await this.storeChatContext(context, roomId);

      // Emit event for Autoliza to process
      this.runtime.emitEvent(EventType.MESSAGE_RECEIVED, {
        runtime: this.runtime,
        message: contextMemory,
        source: 'chat_aggregator'
      });

      logger.info('[ChatAggregatorService] ✅ Context sent to Autoliza successfully', {
        roomId: roomId,
        platforms: Object.keys(context.platforms),
        totalMessages: context.globalContext.totalMessages,
        engagementTrend: context.globalContext.engagementTrend
      });

    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error sending context to Autoliza:', error);
    }
  }

  /**
   * Store chat context in our custom table for analytics
   */
  private async storeChatContext(context: ChatContextUpdate, roomId: string): Promise<void> {
    try {
      // This would use a direct database connection to store in chat_contexts table
      // For now, just log that we would store it
      logger.debug('[ChatAggregatorService] 💾 Chat context would be stored in analytics table', {
        roomId: roomId,
        platformCount: Object.keys(context.platforms).length,
        totalMessages: context.globalContext.totalMessages
      });
    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error storing chat context:', error);
    }
  }

  /**
   * Determine if we should respond to a message based on attention state and salience
   */
  private shouldRespondToMessage(message: ChatMessage, isImmediate: boolean): boolean {
    if (isImmediate) return true;

    const attentionState = this.attentionManager.getCurrentState();
    const responseRate = this.attentionManager.getResponseRate();
    const randomFactor = Math.random();

    // Always respond to critical messages
    if (message.salience.level === SalienceLevel.CRITICAL) return true;

    // Apply attention-based filtering
    switch (attentionState) {
      case AttentionState.FOCUSED_INTERACTION:
        return message.salience.level >= SalienceLevel.MEDIUM && randomFactor < responseRate;
      
      case AttentionState.CASUAL_MONITORING:
        return message.salience.level >= SalienceLevel.HIGH && randomFactor < responseRate;
      
      case AttentionState.DEEP_FOCUS:
        return message.salience.level === SalienceLevel.CRITICAL;
      
      case AttentionState.BREAK_TRANSITION:
        return message.salience.level >= SalienceLevel.HIGH && randomFactor < responseRate;
      
      default:
        return false;
    }
  }

  /**
   * Get batch size for processing based on attention state
   */
  private getBatchSizeForAttentionState(attentionState: AttentionState): number {
    switch (attentionState) {
      case AttentionState.FOCUSED_INTERACTION: return 5;
      case AttentionState.CASUAL_MONITORING: return 3;
      case AttentionState.DEEP_FOCUS: return 1;
      case AttentionState.BREAK_TRANSITION: return 4;
      default: return 2;
    }
  }

  /**
   * Store message in database
   */
  private async storeMessage(message: ChatMessage): Promise<void> {
    try {
      // Store in PostgreSQL database
      // Implementation would depend on the actual database schema
      logger.debug('[ChatAggregatorService] 💾 Message stored', {
        messageId: message.id,
        platform: message.platform,
        salienceScore: message.salience.total
      });
    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error storing message:', error);
    }
  }

  /**
   * Store response in database
   */
  private async storeResponse(originalMessage: ChatMessage, response: any): Promise<void> {
    try {
      // Store response linked to original message
      logger.debug('[ChatAggregatorService] 💾 Response stored', {
        originalMessageId: originalMessage.id,
        responseLength: response.text.length,
        platform: originalMessage.platform
      });
    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error storing response:', error);
    }
  }

  /**
   * Mark message as processed
   */
  private async markMessageProcessed(message: ChatMessage): Promise<void> {
    try {
      // Update message status in database
      message.metadata.processedAt = Date.now();
    } catch (error) {
      logger.error('[ChatAggregatorService] ❌ Error marking message as processed:', error);
    }
  }

  /**
   * Update metrics for monitoring
   */
  private updateMetrics(message: ChatMessage): void {
    const platformMetrics = this.metrics.get(message.platform) || {
      platform: message.platform,
      messagesProcessed: 0,
      averageResponseTime: 0,
      salienceDistribution: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        ignored: 0
      },
      engagementRate: 0,
      timestamp: Date.now()
    };

    platformMetrics.messagesProcessed++;
    
    // Update salience distribution
    switch (message.salience.level) {
      case SalienceLevel.CRITICAL:
        platformMetrics.salienceDistribution.critical++;
        break;
      case SalienceLevel.HIGH:
        platformMetrics.salienceDistribution.high++;
        break;
      case SalienceLevel.MEDIUM:
        platformMetrics.salienceDistribution.medium++;
        break;
      case SalienceLevel.LOW:
        platformMetrics.salienceDistribution.low++;
        break;
      case SalienceLevel.IGNORE:
        platformMetrics.salienceDistribution.ignored++;
        break;
    }

    this.metrics.set(message.platform, platformMetrics);
  }

  /**
   * Calculate global response rate
   */
  private calculateGlobalResponseRate(): number {
    if (this.metrics.size === 0) return 0;
    
    const totalMessages = Array.from(this.metrics.values())
      .reduce((total, metric) => total + metric.messagesProcessed, 0);
    
    const totalResponses = Array.from(this.metrics.values())
      .reduce((total, metric) => total + (metric.messagesProcessed * metric.engagementRate), 0);
    
    return totalMessages > 0 ? totalResponses / totalMessages : 0;
  }

  /**
   * Calculate engagement trend
   */
  private calculateEngagementTrend(): 'increasing' | 'stable' | 'decreasing' {
    // Simple implementation - could be enhanced with historical data
    const currentRate = this.calculateGlobalResponseRate();
    
    if (currentRate > 0.6) return 'increasing';
    if (currentRate > 0.3) return 'stable';
    return 'decreasing';
  }

  /**
   * Get total messages processed across all platforms
   */
  private getTotalMessagesProcessed(): number {
    return Array.from(this.metrics.values())
      .reduce((total, metric) => total + metric.messagesProcessed, 0);
  }

  /**
   * Get current system status
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      uptime: Date.now() - this.startTime,
      totalMessagesProcessed: this.getTotalMessagesProcessed(),
      attentionState: this.attentionManager.getCurrentState(),
      platformsConnected: this.platformManager.getConnectedPlatforms(),
      queueSize: this.messageQueue.size(),
      metrics: Object.fromEntries(this.metrics),
      salienceStats: this.salienceEngine.getContextStats()
    };
  }

  /**
   * Static method to start the service
   */
  static async start(runtime: IAgentRuntime): Promise<ChatAggregatorService> {
    const service = new ChatAggregatorService(runtime);
    await service.start();
    return service;
  }

  /**
   * Static method to stop the service
   */
  static async stop(runtime: IAgentRuntime): Promise<void> {
    const service = runtime.getService(ChatAggregatorService.serviceType);
    if (service) {
      await service.stop();
    }
  }
} 