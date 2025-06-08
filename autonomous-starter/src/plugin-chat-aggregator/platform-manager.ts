import { logger } from '@elizaos/core';
import { 
  PlatformAdapter, 
  ChatMessage, 
  ChatContextUpdate, 
  ChannelInfo,
  VTuberResponse,
  PlatformMessage 
} from './types';
import { TwitchAdapter } from './adapters/twitch';
import { YouTubeAdapter } from './adapters/youtube';
import { DiscordAdapter } from './adapters/discord';

/**
 * Multi-Platform Connection Manager
 * 
 * Orchestrates connections to multiple chat platforms and provides
 * unified message handling and response distribution.
 */
export class PlatformManager {
  private adapters: Map<string, PlatformAdapter> = new Map();
  private messageHandler: (message: ChatMessage) => Promise<void>;
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 5000; // 5 seconds

  constructor(runtime: any, messageHandler: (message: ChatMessage) => Promise<void>) {
    this.messageHandler = messageHandler;
    
    logger.info('[PlatformManager] 🌐 Initializing multi-platform manager', {
      timestamp: new Date().toISOString()
    });

    this.initializePlatforms();
  }

  /**
   * Initialize platform adapters based on configuration
   */
  private initializePlatforms(): void {
    const enabledPlatforms = (process.env.CHAT_ENABLED_PLATFORMS || 'twitch,youtube,discord').split(',');
    
    logger.info('[PlatformManager] 🔧 Initializing platform adapters', {
      enabledPlatforms
    });

    // Initialize Twitch adapter if enabled
    if (enabledPlatforms.includes('twitch')) {
      try {
        const twitchAdapter = new TwitchAdapter();
        this.adapters.set('twitch', twitchAdapter);
        this.setupAdapterHandlers('twitch', twitchAdapter);
        logger.info('[PlatformManager] ✅ Twitch adapter initialized');
      } catch (error) {
        logger.error('[PlatformManager] ❌ Failed to initialize Twitch adapter:', error);
      }
    }

    // Initialize YouTube adapter if enabled
    if (enabledPlatforms.includes('youtube')) {
      try {
        const youtubeAdapter = new YouTubeAdapter();
        this.adapters.set('youtube', youtubeAdapter);
        this.setupAdapterHandlers('youtube', youtubeAdapter);
        logger.info('[PlatformManager] ✅ YouTube adapter initialized');
      } catch (error) {
        logger.error('[PlatformManager] ❌ Failed to initialize YouTube adapter:', error);
      }
    }

    // Initialize Discord adapter if enabled
    if (enabledPlatforms.includes('discord')) {
      try {
        const discordAdapter = new DiscordAdapter();
        this.adapters.set('discord', discordAdapter);
        this.setupAdapterHandlers('discord', discordAdapter);
        logger.info('[PlatformManager] ✅ Discord adapter initialized');
      } catch (error) {
        logger.error('[PlatformManager] ❌ Failed to initialize Discord adapter:', error);
      }
    }

    logger.info('[PlatformManager] 🎯 Platform initialization complete', {
      totalAdapters: this.adapters.size,
      platforms: Array.from(this.adapters.keys())
    });
  }

  /**
   * Set up event handlers for a platform adapter
   */
  private setupAdapterHandlers(platformName: string, adapter: PlatformAdapter): void {
    // Handle incoming messages
    adapter.onMessage(async (message: ChatMessage) => {
      try {
        logger.debug('[PlatformManager] 📨 Message received from platform', {
          platform: platformName,
          author: message.author.username,
          textLength: message.content.text.length
        });

        await this.messageHandler(message);
      } catch (error) {
        logger.error('[PlatformManager] ❌ Error handling message from platform:', error, {
          platform: platformName,
          messageId: message.id
        });
      }
    });

    logger.debug('[PlatformManager] 🔗 Event handlers set up for platform', {
      platform: platformName
    });
  }

  /**
   * Connect to all configured platforms
   */
  async connectAll(): Promise<void> {
    logger.info('[PlatformManager] 🚀 Connecting to all platforms...');

    const connectionPromises = Array.from(this.adapters.entries()).map(
      async ([name, adapter]) => {
        try {
          await this.connectPlatform(name, adapter);
        } catch (error) {
          logger.error(`[PlatformManager] ❌ Failed to connect to ${name}:`, error);
          // Don't throw - continue with other platforms
        }
      }
    );

    await Promise.allSettled(connectionPromises);

    const connectedPlatforms = Array.from(this.adapters.entries())
      .filter(([_, adapter]) => adapter.isConnected())
      .map(([name, _]) => name);

    logger.info('[PlatformManager] ✅ Platform connections completed', {
      connectedPlatforms,
      totalRequested: this.adapters.size,
      totalConnected: connectedPlatforms.length
    });
  }

  /**
   * Connect to a specific platform with retry logic
   */
  private async connectPlatform(name: string, adapter: PlatformAdapter): Promise<void> {
    const maxAttempts = this.maxReconnectAttempts;
    let attempt = 0;

    while (attempt < maxAttempts) {
      try {
        logger.info(`[PlatformManager] 🔌 Connecting to ${name} (attempt ${attempt + 1}/${maxAttempts})`);
        
        await adapter.connect();
        
        logger.info(`[PlatformManager] ✅ Successfully connected to ${name}`);
        this.reconnectAttempts.set(name, 0); // Reset counter on success
        return;

      } catch (error) {
        attempt++;
        this.reconnectAttempts.set(name, attempt);
        
        logger.warn(`[PlatformManager] ⚠️ Connection attempt ${attempt} failed for ${name}:`, error);

        if (attempt < maxAttempts) {
          const delay = this.reconnectDelay * Math.pow(2, attempt - 1); // Exponential backoff
          logger.info(`[PlatformManager] ⏳ Retrying ${name} connection in ${delay}ms`);
          await new Promise(resolve => setTimeout(resolve, delay));
        } else {
          logger.error(`[PlatformManager] ❌ Max reconnection attempts reached for ${name}`);
          throw error;
        }
      }
    }
  }

  /**
   * Disconnect from all platforms
   */
  async disconnectAll(): Promise<void> {
    logger.info('[PlatformManager] 🔌 Disconnecting from all platforms...');

    const disconnectionPromises = Array.from(this.adapters.entries()).map(
      async ([name, adapter]) => {
        try {
          if (adapter.isConnected()) {
            await adapter.disconnect();
            logger.info(`[PlatformManager] ✅ Disconnected from ${name}`);
          }
        } catch (error) {
          logger.error(`[PlatformManager] ❌ Error disconnecting from ${name}:`, error);
        }
      }
    );

    await Promise.allSettled(disconnectionPromises);
    logger.info('[PlatformManager] ✅ All platform disconnections completed');
  }

  /**
   * Send a response to a specific platform
   */
  async sendResponse(response: VTuberResponse, platformName: string): Promise<void> {
    const adapter = this.adapters.get(platformName);
    
    if (!adapter) {
      logger.error('[PlatformManager] ❌ Platform adapter not found', {
        platform: platformName,
        availablePlatforms: Array.from(this.adapters.keys())
      });
      return;
    }

    if (!adapter.isConnected()) {
      logger.warn('[PlatformManager] ⚠️ Platform not connected, attempting reconnection', {
        platform: platformName
      });
      
      try {
        await this.connectPlatform(platformName, adapter);
      } catch (error) {
        logger.error('[PlatformManager] ❌ Failed to reconnect platform:', error);
        return;
      }
    }

    try {
      // Format response for the specific platform
      const platformMessage = await this.formatResponseForPlatform(response, platformName);
      
      // Send through the platform adapter
      await adapter.sendMessage(
        platformMessage.formattedContent, 
        response.targetPlatform || 'default'
      );

      logger.info('[PlatformManager] ✅ Response sent successfully', {
        platform: platformName,
        responseLength: response.text.length,
        formattedLength: platformMessage.formattedContent.length,
        priority: response.priority
      });

    } catch (error) {
      logger.error('[PlatformManager] ❌ Failed to send response:', error, {
        platform: platformName,
        responseText: response.text.substring(0, 100) + '...'
      });
    }
  }

  /**
   * Format response for platform-specific requirements
   */
  private async formatResponseForPlatform(
    response: VTuberResponse, 
    platformName: string
  ): Promise<PlatformMessage> {
    let formattedContent = response.text;

    // Platform-specific formatting
    switch (platformName) {
      case 'twitch':
        // Twitch: 500 character limit, emote support
        if (formattedContent.length > 500) {
          formattedContent = formattedContent.substring(0, 497) + '...';
        }
        break;

      case 'youtube':
        // YouTube: 200 character limit for live chat
        if (formattedContent.length > 200) {
          formattedContent = formattedContent.substring(0, 197) + '...';
        }
        break;

      case 'discord':
        // Discord: 2000 character limit, markdown support
        if (formattedContent.length > 2000) {
          formattedContent = formattedContent.substring(0, 1997) + '...';
        }
        break;

      default:
        // Generic formatting
        if (formattedContent.length > 500) {
          formattedContent = formattedContent.substring(0, 497) + '...';
        }
        break;
    }

    return {
      platform: platformName,
      channel: response.targetPlatform || 'default',
      content: response.text,
      formattedContent,
      metadata: {
        messageType: 'text',
        priority: response.priority,
        timestamp: Date.now()
      }
    };
  }

  /**
   * Get context from all connected platforms
   */
  async getAllPlatformContexts(): Promise<{ [platform: string]: any }> {
    const contexts: { [platform: string]: any } = {};

    for (const [name, adapter] of this.adapters.entries()) {
      if (adapter.isConnected()) {
        try {
          const channelInfo = await adapter.getChannelInfo();
          contexts[name] = {
            activeUsers: channelInfo.userCount || 0,
            averageSalience: 0.5, // TODO: Calculate from recent messages
            topTopics: [], // TODO: Extract from recent messages
            sentiment: 'neutral' as const,
            lastInteraction: Date.now(),
            isLive: channelInfo.isLive || false,
            channelName: channelInfo.name
          };
        } catch (error) {
          logger.error(`[PlatformManager] ❌ Error getting context for ${name}:`, error);
          contexts[name] = {
            activeUsers: 0,
            averageSalience: 0,
            topTopics: [],
            sentiment: 'neutral' as const,
            lastInteraction: 0,
            isLive: false,
            error: error.message
          };
        }
      }
    }

    return contexts;
  }

  /**
   * Get list of connected platforms
   */
  getConnectedPlatforms(): string[] {
    return Array.from(this.adapters.entries())
      .filter(([_, adapter]) => adapter.isConnected())
      .map(([name, _]) => name);
  }

  /**
   * Get platform adapter statistics
   */
  getStats() {
    const stats: any = {};

    for (const [name, adapter] of this.adapters.entries()) {
      stats[name] = {
        isConnected: adapter.isConnected(),
        reconnectAttempts: this.reconnectAttempts.get(name) || 0,
        platformName: adapter.getPlatformName()
      };
    }

    return {
      totalPlatforms: this.adapters.size,
      connectedPlatforms: this.getConnectedPlatforms().length,
      platforms: stats
    };
  }

  /**
   * Force reconnection to a specific platform
   */
  async reconnectPlatform(platformName: string): Promise<void> {
    const adapter = this.adapters.get(platformName);
    
    if (!adapter) {
      throw new Error(`Platform ${platformName} not found`);
    }

    logger.info(`[PlatformManager] 🔄 Force reconnecting to ${platformName}`);

    try {
      if (adapter.isConnected()) {
        await adapter.disconnect();
      }
      await this.connectPlatform(platformName, adapter);
    } catch (error) {
      logger.error(`[PlatformManager] ❌ Force reconnection failed for ${platformName}:`, error);
      throw error;
    }
  }

  /**
   * Health check for all platforms
   */
  async healthCheck(): Promise<{ [platform: string]: boolean }> {
    const health: { [platform: string]: boolean } = {};

    for (const [name, adapter] of this.adapters.entries()) {
      try {
        health[name] = adapter.isConnected();
        
        // Additional health checks could be added here
        // e.g., ping/heartbeat, recent message flow, etc.
        
      } catch (error) {
        logger.error(`[PlatformManager] ❌ Health check failed for ${name}:`, error);
        health[name] = false;
      }
    }

    return health;
  }
} 