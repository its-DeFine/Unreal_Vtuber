import { logger } from '../core-mock';
import { PlatformAdapter, ChatMessage, ChannelInfo } from '../types';

/**
 * Twitch Platform Adapter
 * Mock implementation for development/testing
 */
export class TwitchAdapter implements PlatformAdapter {
  private connected: boolean = false;
  private messageCallback?: (message: ChatMessage) => void;

  async connect(): Promise<void> {
    logger.info('[TwitchAdapter] 🔌 Connecting to Twitch...');
    // Mock connection - implement actual Twitch API integration later
    this.connected = true;
    logger.info('[TwitchAdapter] ✅ Connected to Twitch (mock)');
  }

  async disconnect(): Promise<void> {
    logger.info('[TwitchAdapter] 🔌 Disconnecting from Twitch...');
    this.connected = false;
    logger.info('[TwitchAdapter] ✅ Disconnected from Twitch');
  }

  async sendMessage(message: string, channel: string): Promise<void> {
    logger.info('[TwitchAdapter] 📤 Sending message to Twitch', {
      channel,
      messageLength: message.length
    });
    // Mock send - implement actual Twitch API integration later
  }

  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallback = callback;
    logger.debug('[TwitchAdapter] 📨 Message callback registered');
  }

  async getChannelInfo(): Promise<ChannelInfo> {
    return {
      id: 'mock_twitch_channel',
      name: 'autoliza_channel',
      userCount: 50,
      isLive: true,
      moderators: ['mod1', 'mod2']
    };
  }

  isConnected(): boolean {
    return this.connected;
  }

  getPlatformName(): string {
    return 'twitch';
  }
} 