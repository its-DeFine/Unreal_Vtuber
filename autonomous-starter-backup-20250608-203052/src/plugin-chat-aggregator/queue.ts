import { logger } from '@elizaos/core';
import { ChatMessage } from './types';

/**
 * Priority-based Message Queue for Chat Aggregator
 * 
 * Manages incoming chat messages with priority-based processing.
 * Higher salience messages get processed first while maintaining
 * fairness and preventing starvation.
 */
export class MessageQueue {
  private queue: Array<{ message: ChatMessage; priority: number; timestamp: number }> = [];
  private maxSize: number;
  private processed: number = 0;
  private dropped: number = 0;

  constructor(runtime: any) {
    this.maxSize = parseInt(process.env.CHAT_QUEUE_MAX_SIZE || '10000');
    
    logger.info('[MessageQueue] 📥 Initializing priority message queue', {
      maxSize: this.maxSize,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Add a message to the queue with priority
   */
  async enqueue(message: ChatMessage, priority: number): Promise<void> {
    const timestamp = Date.now();
    
    // Check if queue is full
    if (this.queue.length >= this.maxSize) {
      // Drop the lowest priority message
      this.queue.sort((a, b) => b.priority - a.priority);
      const dropped = this.queue.pop();
      this.dropped++;
      
      logger.warn('[MessageQueue] ⚠️ Queue full, dropped message', {
        droppedMessage: dropped?.message.id,
        droppedPriority: dropped?.priority,
        queueSize: this.queue.length,
        totalDropped: this.dropped
      });
    }

    // Add new message
    this.queue.push({ message, priority, timestamp });
    
    logger.debug('[MessageQueue] ➕ Message enqueued', {
      messageId: message.id,
      priority,
      platform: message.platform,
      author: message.author.username,
      queueSize: this.queue.length
    });
  }

  /**
   * Get the highest priority message from the queue
   */
  async dequeue(): Promise<ChatMessage | null> {
    if (this.queue.length === 0) {
      return null;
    }

    // Sort by priority (highest first), then by timestamp (oldest first)
    this.queue.sort((a, b) => {
      if (Math.abs(a.priority - b.priority) < 0.01) {
        return a.timestamp - b.timestamp; // FIFO for same priority
      }
      return b.priority - a.priority; // Higher priority first
    });

    const item = this.queue.shift();
    if (!item) return null;

    this.processed++;
    
    logger.debug('[MessageQueue] ➖ Message dequeued', {
      messageId: item.message.id,
      priority: item.priority,
      platform: item.message.platform,
      waitTime: Date.now() - item.timestamp,
      queueSize: this.queue.length,
      totalProcessed: this.processed
    });

    return item.message;
  }

  /**
   * Peek at the highest priority message without removing it
   */
  async peek(): Promise<ChatMessage | null> {
    if (this.queue.length === 0) {
      return null;
    }

    // Sort without modifying original queue
    const sorted = [...this.queue].sort((a, b) => {
      if (Math.abs(a.priority - b.priority) < 0.01) {
        return a.timestamp - b.timestamp;
      }
      return b.priority - a.priority;
    });

    return sorted[0]?.message || null;
  }

  /**
   * Get current queue size
   */
  size(): number {
    return this.queue.length;
  }

  /**
   * Clear all messages from the queue
   */
  async clear(): Promise<void> {
    const size = this.queue.length;
    this.queue = [];
    
    logger.info('[MessageQueue] 🧹 Queue cleared', {
      messagesCleared: size,
      totalProcessed: this.processed,
      totalDropped: this.dropped
    });
  }

  /**
   * Get queue statistics
   */
  getStats() {
    const now = Date.now();
    const priorities = this.queue.map(item => item.priority);
    const waitTimes = this.queue.map(item => now - item.timestamp);
    
    return {
      size: this.queue.length,
      maxSize: this.maxSize,
      processed: this.processed,
      dropped: this.dropped,
      utilization: this.queue.length / this.maxSize,
      averagePriority: priorities.length > 0 ? 
        priorities.reduce((sum, p) => sum + p, 0) / priorities.length : 0,
      averageWaitTime: waitTimes.length > 0 ? 
        waitTimes.reduce((sum, t) => sum + t, 0) / waitTimes.length : 0,
      oldestMessageAge: waitTimes.length > 0 ? Math.max(...waitTimes) : 0,
      platformDistribution: this.getPlatformDistribution()
    };
  }

  /**
   * Get distribution of messages by platform
   */
  private getPlatformDistribution(): Record<string, number> {
    const distribution: Record<string, number> = {};
    
    for (const item of this.queue) {
      const platform = item.message.platform;
      distribution[platform] = (distribution[platform] || 0) + 1;
    }
    
    return distribution;
  }

  /**
   * Get messages by priority level for monitoring
   */
  getPriorityDistribution() {
    const distribution = {
      critical: 0,  // >= 0.8
      high: 0,      // >= 0.6
      medium: 0,    // >= 0.4
      low: 0,       // >= 0.2
      minimal: 0    // < 0.2
    };

    for (const item of this.queue) {
      const priority = item.priority;
      if (priority >= 0.8) distribution.critical++;
      else if (priority >= 0.6) distribution.high++;
      else if (priority >= 0.4) distribution.medium++;
      else if (priority >= 0.2) distribution.low++;
      else distribution.minimal++;
    }

    return distribution;
  }

  /**
   * Remove messages older than specified age (cleanup)
   */
  async cleanup(maxAge: number = 10 * 60 * 1000): Promise<number> {
    const now = Date.now();
    const initialSize = this.queue.length;
    
    this.queue = this.queue.filter(item => now - item.timestamp < maxAge);
    
    const removed = initialSize - this.queue.length;
    
    if (removed > 0) {
      logger.info('[MessageQueue] 🧽 Queue cleanup completed', {
        messagesRemoved: removed,
        maxAge: `${maxAge / 1000}s`,
        remainingMessages: this.queue.length
      });
    }

    return removed;
  }

  /**
   * Get health status of the queue
   */
  getHealth() {
    const stats = this.getStats();
    const utilizationThreshold = 0.8;
    const avgWaitTimeThreshold = 30000; // 30 seconds
    
    const isHealthy = 
      stats.utilization < utilizationThreshold && 
      stats.averageWaitTime < avgWaitTimeThreshold;

    return {
      isHealthy,
      status: isHealthy ? 'healthy' : 'degraded',
      warnings: [
        ...(stats.utilization >= utilizationThreshold ? ['High queue utilization'] : []),
        ...(stats.averageWaitTime >= avgWaitTimeThreshold ? ['High average wait time'] : []),
        ...(stats.oldestMessageAge > 60000 ? ['Messages waiting over 1 minute'] : [])
      ],
      recommendations: [
        ...(stats.utilization >= 0.9 ? ['Consider increasing processing rate'] : []),
        ...(stats.dropped > 0 ? ['Monitor for message drops'] : []),
        ...(stats.averageWaitTime > 60000 ? ['Consider optimizing message processing'] : [])
      ]
    };
  }

  /**
   * Force process all messages of a specific priority or higher
   */
  async drainByPriority(minPriority: number): Promise<ChatMessage[]> {
    const matches: ChatMessage[] = [];
    
    this.queue = this.queue.filter(item => {
      if (item.priority >= minPriority) {
        matches.push(item.message);
        return false; // Remove from queue
      }
      return true; // Keep in queue
    });

    logger.info('[MessageQueue] 🚰 Drained messages by priority', {
      minPriority,
      messagesDrained: matches.length,
      remainingInQueue: this.queue.length
    });

    return matches;
  }
} 