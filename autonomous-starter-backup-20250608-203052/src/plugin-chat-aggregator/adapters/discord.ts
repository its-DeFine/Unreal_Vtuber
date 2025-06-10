import { logger } from '../core-mock';
import { PlatformAdapter, ChatMessage, ChannelInfo } from '../types';

/**
 * Discord Platform Adapter
 * Mock implementation for development/testing
 */
export class DiscordAdapter implements PlatformAdapter {
  private connected: boolean = false;
  private messageCallback?: (message: ChatMessage) => void;

  async connect(): Promise<void> {
    logger.info('[DiscordAdapter] 🔌 Connecting to Discord...');
    // Mock connection - implement actual Discord API integration later
    this.connected = true;
    logger.info('[DiscordAdapter] ✅ Connected to Discord (mock)');
  }

  async disconnect(): Promise<void> {
    logger.info('[DiscordAdapter] 🔌 Disconnecting from Discord...');
    this.connected = false;
    logger.info('[DiscordAdapter] ✅ Disconnected from Discord');
  }

  async sendMessage(message: string, channel: string): Promise<void> {
    logger.info('[DiscordAdapter] 📤 Sending message to Discord', {
      channel,
      messageLength: message.length
    });
    // Mock send - implement actual Discord API integration later
  }

  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallback = callback;
    logger.debug('[DiscordAdapter] 📨 Message callback registered');
  }

  async getChannelInfo(): Promise<ChannelInfo> {
    return {
      id: 'mock_discord_channel',
      name: 'general',
      userCount: 120,
      isLive: false,
      moderators: ['discordmod1', 'discordmod2']
    };
  }

  isConnected(): boolean {
    return this.connected;
  }

  getPlatformName(): string {
    return 'discord';
  }
} 