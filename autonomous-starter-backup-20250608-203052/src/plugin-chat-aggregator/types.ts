import { UUID } from '@elizaos/core';

export interface ChatMessage {
  id: string;
  platform: 'twitch' | 'youtube' | 'discord' | string;
  channel: string;
  author: {
    id: string;
    username: string;
    displayName: string;
    badges: string[];
    isSubscriber: boolean;
    isModerator: boolean;
    followAge?: number;
  };
  content: {
    text: string;
    emotes?: Emote[];
    mentions?: string[];
    links?: string[];
  };
  metadata: {
    timestamp: number;
    messageId: string;
    threadId?: string;
    replyTo?: string;
  };
  salience: SalienceScore;
}

export interface Emote {
  id: string;
  name: string;
  url?: string;
  positions?: Array<[number, number]>;
}

export interface SalienceScore {
  total: number; // 0.0 - 1.0
  breakdown: {
    content: number;      // Content analysis score
    authority: number;    // Author authority score
    relevance: number;    // Contextual relevance score
    temporal: number;     // Temporal factors score
  };
  level: SalienceLevel;
  reasoning: string[];
}

export enum SalienceLevel {
  CRITICAL = 0.8,    // Immediate response required
  HIGH = 0.6,        // Priority response within 30s
  MEDIUM = 0.4,      // Standard response queue
  LOW = 0.2,         // Background consideration
  IGNORE = 0.0       // Spam/filtered content
}

export interface AttentionInterrupt {
  type: 'message_spike' | 'high_salience' | 'platform_event' | 'autonomous_trigger';
  priority: number;
  context: {
    platform: string;
    messageCount?: number;
    averageSalience?: number;
    eventType?: string;
  };
  suggested_action: 'immediate_response' | 'queue_priority' | 'attention_shift';
}

export interface ChatContextUpdate {
  platforms: {
    [platform: string]: {
      activeUsers: number;
      averageSalience: number;
      topTopics: string[];
      sentiment: 'positive' | 'neutral' | 'negative';
      lastInteraction: number;
    };
  };
  globalContext: {
    totalMessages: number;
    responseRate: number;
    engagementTrend: 'increasing' | 'stable' | 'decreasing';
    recommendedAction: string;
  };
}

export interface PlatformAdapter {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  sendMessage(message: string, channel: string): Promise<void>;
  onMessage(callback: (message: ChatMessage) => void): void;
  getChannelInfo(): Promise<ChannelInfo>;
  isConnected(): boolean;
  getPlatformName(): string;
}

export interface ChannelInfo {
  id: string;
  name: string;
  userCount?: number;
  isLive?: boolean;
  moderators?: string[];
}

export interface VTuberResponse {
  text: string;
  emotion?: string;
  priority: number;
  targetPlatform?: string;
  metadata: {
    responseTime: number;
    confidence: number;
    originalMessage: string;
    autonomousContext?: any;
  };
}

export interface PlatformMessage {
  platform: string;
  channel: string;
  content: string;
  formattedContent: string;
  metadata: {
    messageType: 'text' | 'emote' | 'action';
    priority: number;
    timestamp: number;
  };
}

export enum AttentionState {
  FOCUSED_INTERACTION = 'focused_interaction',
  CASUAL_MONITORING = 'casual_monitoring', 
  DEEP_FOCUS = 'deep_focus',
  BREAK_TRANSITION = 'break_transition'
}

export interface AttentionCycle {
  currentState: AttentionState;
  stateStartTime: number;
  stateDuration: number;
  responseRate: number;
  interruptThreshold: number;
  nextTransition: number;
}

// Logging and analytics interfaces
export interface ChatMetrics {
  platform: string;
  messagesProcessed: number;
  averageResponseTime: number;
  salienceDistribution: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    ignored: number;
  };
  engagementRate: number;
  timestamp: number;
}

export interface PlatformConfig {
  name: string;
  enabled: boolean;
  credentials: {
    [key: string]: string;
  };
  settings: {
    maxMessagesPerMinute: number;
    responseCooldown: number;
    enableModeration: boolean;
    allowedChannels?: string[];
    bannedUsers?: string[];
  };
} 