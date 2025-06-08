#!/usr/bin/env node

import { 
  IAgentRuntime, 
  logger, 
  createUniqueUuid, 
  EventType 
} from './core-mock';
import { ChatAggregatorService } from './service';
import { 
  ChatMessage, 
  SalienceLevel,
  AttentionState 
} from './types';

/**
 * Demo Test Script for Multi-Platform Chat Aggregation System
 * 
 * This demonstrates the full chat system working with simulated messages
 * from multiple platforms, showing intelligent prioritization, human-like
 * attention patterns, and VTuber response generation.
 */

// Mock runtime implementation
class MockAgentRuntime implements IAgentRuntime {
  agentId = 'autoliza-vtuber-001';
  
  async createMemory(memory: any, room: string): Promise<void> {
    logger.debug('🧠 Memory created', { memoryId: memory.id, room, type: memory.content.type });
  }
  
  emitEvent(eventType: EventType, data: any): void {
    logger.debug('📡 Event emitted', { eventType, data });
  }
  
  getService(serviceType: string): any {
    logger.debug('🔍 Service requested', { serviceType });
    return null;
  }
}

// Demo messages from different platforms
const demoMessages: Partial<ChatMessage>[] = [
  {
    platform: 'twitch',
    channel: 'autoliza_channel',
    author: {
      id: 'user1',
      username: 'TechCurious',
      displayName: 'TechCurious',
      badges: ['subscriber'],
      isSubscriber: true,
      isModerator: false,
      followAge: 90
    },
    content: {
      text: 'Hey Autoliza! What do you think about the latest developments in neural network architecture?',
      mentions: ['autoliza'],
      emotes: [],
      links: []
    },
    metadata: {
      timestamp: Date.now(),
      messageId: 'twitch_msg_001'
    }
  },
  {
    platform: 'youtube',
    channel: 'autoliza_live',
    author: {
      id: 'user2',
      username: 'FirstTimeViewer',
      displayName: 'FirstTimeViewer',
      badges: [],
      isSubscriber: false,
      isModerator: false,
      followAge: 0
    },
    content: {
      text: 'Hello! This is my first time watching, what kind of research do you do?',
      mentions: [],
      emotes: [],
      links: []
    },
    metadata: {
      timestamp: Date.now() + 1000,
      messageId: 'youtube_msg_001'
    }
  },
  {
    platform: 'discord',
    channel: 'general',
    author: {
      id: 'user3',
      username: 'RegularChatter',
      displayName: 'RegularChatter',
      badges: ['member'],
      isSubscriber: true,
      isModerator: false,
      followAge: 180
    },
    content: {
      text: 'The stream quality looks amazing today! Love the new setup ✨',
      mentions: [],
      emotes: [],
      links: []
    },
    metadata: {
      timestamp: Date.now() + 2000,
      messageId: 'discord_msg_001'
    }
  },
  {
    platform: 'twitch',
    channel: 'autoliza_channel',
    author: {
      id: 'user4',
      username: 'ModeratorBot',
      displayName: 'ModeratorBot',
      badges: ['moderator', 'subscriber'],
      isSubscriber: true,
      isModerator: true,
      followAge: 365
    },
    content: {
      text: 'URGENT: We have a technical issue that needs your attention regarding the autonomous system',
      mentions: ['autoliza'],
      emotes: [],
      links: []
    },
    metadata: {
      timestamp: Date.now() + 3000,
      messageId: 'twitch_msg_002'
    }
  },
  {
    platform: 'youtube',
    channel: 'autoliza_live',
    author: {
      id: 'user5',
      username: 'CasualViewer',
      displayName: 'CasualViewer',
      badges: [],
      isSubscriber: false,
      isModerator: false,
      followAge: 30
    },
    content: {
      text: 'lol that was funny 😂',
      mentions: [],
      emotes: [],
      links: []
    },
    metadata: {
      timestamp: Date.now() + 4000,
      messageId: 'youtube_msg_002'
    }
  }
];

/**
 * Run the chat aggregator demo
 */
async function runDemo(): Promise<void> {
  logger.info('🚀 Starting Multi-Platform Chat Aggregator Demo');
  logger.info('=' .repeat(60));
  
  try {
    // Initialize the system
    const runtime = new MockAgentRuntime();
    const chatService = new ChatAggregatorService(runtime);
    
    logger.info('🔧 Initializing chat aggregation service...');
    await chatService.start();
    
    logger.info('✅ Service started successfully!');
    logger.info('📊 Initial system status:', chatService.getStatus());
    
    // Simulate incoming messages with delays
    logger.info('\n🎭 Simulating incoming messages from multiple platforms...');
    
    for (let i = 0; i < demoMessages.length; i++) {
      const messageData = demoMessages[i];
      
      // Create complete message with salience
      const message: ChatMessage = {
        id: createUniqueUuid(runtime, 'msg'),
        platform: messageData.platform!,
        channel: messageData.channel!,
        author: messageData.author!,
        content: messageData.content!,
        metadata: messageData.metadata!,
        salience: {
          total: 0, // Will be calculated by salience engine
          breakdown: { content: 0, authority: 0, relevance: 0, temporal: 0 },
          level: SalienceLevel.MEDIUM,
          reasoning: []
        }
      };
      
      logger.info(`\n📨 Incoming message ${i + 1}/${demoMessages.length}:`);
      logger.info(`   Platform: ${message.platform}`);
      logger.info(`   Author: ${message.author.displayName} ${message.author.isSubscriber ? '(Subscriber)' : ''} ${message.author.isModerator ? '(Moderator)' : ''}`);
      logger.info(`   Content: "${message.content.text}"`);
      
      // Simulate the message being processed
      await (chatService as any).handleIncomingMessage(message);
      
      // Wait a bit to see processing
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Show current status
      const status = chatService.getStatus();
      logger.info(`   Queue size: ${status.queueSize}`);
      logger.info(`   Attention state: ${status.attentionState}`);
    }
    
    // Let the system process messages for a bit
    logger.info('\n⏳ Allowing system to process messages...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Show final statistics
    const finalStatus = chatService.getStatus();
    logger.info('\n📊 Final System Statistics:');
    logger.info('=' .repeat(40));
    logger.info(`Total messages processed: ${finalStatus.totalMessagesProcessed}`);
    logger.info(`Current attention state: ${finalStatus.attentionState}`);
    logger.info(`Queue size: ${finalStatus.queueSize}`);
    logger.info(`Uptime: ${Math.round(finalStatus.uptime / 1000)}s`);
    logger.info(`Connected platforms: ${finalStatus.platformsConnected.join(', ') || 'None (simulated)'}`);
    
    // Show platform metrics
    if (finalStatus.metrics && Object.keys(finalStatus.metrics).length > 0) {
      logger.info('\n📈 Platform Metrics:');
      Object.entries(finalStatus.metrics).forEach(([platform, metrics]: [string, any]) => {
        logger.info(`  ${platform}:`);
        logger.info(`    Messages processed: ${metrics.messagesProcessed}`);
        logger.info(`    Salience distribution: Critical(${metrics.salienceDistribution.critical}) High(${metrics.salienceDistribution.high}) Medium(${metrics.salienceDistribution.medium}) Low(${metrics.salienceDistribution.low})`);
      });
    }
    
    // Show salience engine statistics
    if (finalStatus.salienceStats) {
      logger.info('\n🧮 Salience Engine Statistics:');
      logger.info(`  Context history size: ${finalStatus.salienceStats.contextHistorySize}`);
      logger.info(`  Tracked topics: ${finalStatus.salienceStats.trackedTopics}`);
      if (finalStatus.salienceStats.topTopics && finalStatus.salienceStats.topTopics.length > 0) {
        logger.info('  Top topics:');
        finalStatus.salienceStats.topTopics.forEach((topic: any) => {
          logger.info(`    - ${topic.topic}: ${topic.count} mentions`);
        });
      }
    }
    
    // Demonstrate attention state changes
    logger.info('\n🎯 Demonstrating attention state management...');
    const attentionManager = (chatService as any).attentionManager;
    const attentionStats = attentionManager.getStats();
    
    logger.info(`Current state: ${attentionStats.currentState}`);
    logger.info(`Response rate: ${(attentionStats.responseRate * 100).toFixed(1)}%`);
    logger.info(`Time in current state: ${Math.round(attentionStats.timeInCurrentState / 1000)}s`);
    logger.info(`Message velocity: ${attentionStats.messageVelocity} messages/minute`);
    
    // Cleanup
    logger.info('\n🛑 Stopping service...');
    await chatService.stop();
    
    logger.info('\n✅ Demo completed successfully!');
    logger.info('🎉 Multi-Platform Chat Aggregation System is fully operational!');
    
  } catch (error) {
    logger.error('❌ Demo failed:', error);
    process.exit(1);
  }
}

/**
 * Display system capabilities summary
 */
function displayCapabilities(): void {
  logger.info('\n🌟 Multi-Platform Chat System Capabilities:');
  logger.info('=' .repeat(50));
  logger.info('✅ Intelligent Message Prioritization');
  logger.info('   • 4-dimensional salience scoring (Content, Authority, Relevance, Temporal)');
  logger.info('   • Real-time priority queue management');
  logger.info('   • Transparent reasoning for all decisions');
  
  logger.info('\n✅ Human-Like Attention Management');
  logger.info('   • 4 attention states with realistic transitions');
  logger.info('   • Dynamic response rates based on context');
  logger.info('   • Interrupt handling for critical messages');
  
  logger.info('\n✅ Platform Integration');
  logger.info('   • Unified message ingestion from Twitch, YouTube, Discord');
  logger.info('   • Platform-specific formatting and constraints');
  logger.info('   • Automatic reconnection and error handling');
  
  logger.info('\n✅ VTuber Response Generation');
  logger.info('   • Context-aware response categorization');
  logger.info('   • NeuroSync integration for enhanced responses');
  logger.info('   • Personality-consistent tone and emotion');
  
  logger.info('\n✅ Autoliza Coordination');
  logger.info('   • Bidirectional context sharing');
  logger.info('   • Strategic conversation guidance');
  logger.info('   • Autonomous behavior triggers');
  
  logger.info('\n✅ Comprehensive Monitoring');
  logger.info('   • Real-time metrics and analytics');
  logger.info('   • Performance monitoring and health checks');
  logger.info('   • Detailed logging for debugging and optimization');
}

// Main execution
if (require.main === module) {
  displayCapabilities();
  runDemo().catch(error => {
    logger.error('💥 Unhandled error in demo:', error);
    process.exit(1);
  });
}

export { runDemo, displayCapabilities }; 