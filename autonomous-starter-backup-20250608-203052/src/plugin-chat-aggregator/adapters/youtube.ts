import { logger } from '../core-mock';
import { PlatformAdapter, ChatMessage, ChannelInfo } from '../types';

/**
 * YouTube Platform Adapter
 * Mock implementation for development/testing
 */
export class YouTubeAdapter implements PlatformAdapter {
  private connected: boolean = false;
  private messageCallback?: (message: ChatMessage) => void;

  async connect(): Promise<void> {
    logger.info('[YouTubeAdapter] 🔌 Connecting to YouTube...');
    // Mock connection - implement actual YouTube API integration later
    this.connected = true;
    logger.info('[YouTubeAdapter] ✅ Connected to YouTube (mock)');
  }

  async disconnect(): Promise<void> {
    logger.info('[YouTubeAdapter] 🔌 Disconnecting from YouTube...');
    this.connected = false;
    logger.info('[YouTubeAdapter] ✅ Disconnected from YouTube');
  }

  async sendMessage(message: string, channel: string): Promise<void> {
    logger.info('[YouTubeAdapter] 📤 Sending message to YouTube', {
      channel,
      messageLength: message.length
    });
    // Mock send - implement actual YouTube API integration later
  }

  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallback = callback;
    logger.debug('[YouTubeAdapter] 📨 Message callback registered');
  }

  async getChannelInfo(): Promise<ChannelInfo> {
    return {
      id: 'mock_youtube_channel',
      name: 'autoliza_live',
      userCount: 75,
      isLive: true,
      moderators: ['ytmod1', 'ytmod2']
    };
  }

  isConnected(): boolean {
    return this.connected;
  }

  getPlatformName(): string {
    return 'youtube';
  }
} 