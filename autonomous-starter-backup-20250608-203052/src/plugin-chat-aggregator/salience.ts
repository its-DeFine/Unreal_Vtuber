import { logger } from './core-mock';
import { ChatMessage, SalienceScore, SalienceLevel, ChatContextUpdate } from './types';

/**
 * Intelligent message salience scoring engine for VTuber chat interactions.
 * Implements multi-dimensional scoring to prioritize messages based on:
 * - Content analysis (40%): mentions, emotions, technical topics
 * - Author authority (25%): subscriber status, follower age, moderator status
 * - Contextual relevance (20%): topic matching, conversation building
 * - Temporal factors (15%): recency, urgency, chat velocity
 */
export class SalienceEngine {
  private vtuberKeywords: Set<string>;
  private emotionalKeywords: Map<string, number>;
  private technicalTopics: Set<string>;
  private contextHistory: string[] = [];
  private recentTopics: Map<string, number> = new Map();

  constructor() {
    logger.info('[SalienceEngine] Initializing intelligent message scoring system');
    
    // Initialize VTuber-specific keywords (should be configurable)
    this.vtuberKeywords = new Set([
      'autoliza', 'vtuber', 'ai', 'neural', 'sync', 'research', 'autonomous',
      'question', 'help', 'explain', 'what', 'how', 'why', 'when', 'where'
    ]);

    // Emotional keywords with impact scores
    this.emotionalKeywords = new Map([
      // Positive emotions
      ['excited', 0.3], ['amazing', 0.25], ['love', 0.2], ['awesome', 0.2],
      ['fantastic', 0.25], ['wow', 0.15], ['incredible', 0.3], ['brilliant', 0.25],
      
      // Negative emotions (still valuable for engagement)
      ['sad', 0.2], ['confused', 0.25], ['worried', 0.2], ['frustrated', 0.15],
      ['disappointed', 0.2], ['concerned', 0.25],
      
      // High engagement indicators
      ['emergency', 0.4], ['urgent', 0.35], ['important', 0.3], ['please', 0.15],
      ['help', 0.3], ['question', 0.25]
    ]);

    // Technical/research topics of interest
    this.technicalTopics = new Set([
      'machine learning', 'neural networks', 'ai research', 'programming',
      'algorithm', 'data science', 'computer vision', 'nlp', 'language model',
      'artificial intelligence', 'deep learning', 'automation', 'robotics'
    ]);

    logger.info('[SalienceEngine] Loaded scoring parameters', {
      vtuberKeywords: this.vtuberKeywords.size,
      emotionalKeywords: this.emotionalKeywords.size,
      technicalTopics: this.technicalTopics.size
    });
  }

  /**
   * Calculate comprehensive salience score for a chat message
   */
  async calculateSalience(
    message: ChatMessage,
    context: ChatContextUpdate
  ): Promise<SalienceScore> {
    const startTime = Date.now();
    
    logger.debug('[SalienceEngine] Calculating salience for message', {
      platform: message.platform,
      author: message.author.username,
      textLength: message.content.text.length,
      timestamp: message.metadata.timestamp
    });

    // Calculate individual score components
    const contentScore = this.analyzeContent(message);
    const authorityScore = this.analyzeAuthority(message);
    const relevanceScore = this.analyzeRelevance(message, context);
    const temporalScore = this.analyzeTemporalFactors(message, context);

    // Weighted total score
    const totalScore = Math.min(1.0, Math.max(0.0, 
      contentScore * 0.4 + 
      authorityScore * 0.25 + 
      relevanceScore * 0.2 + 
      temporalScore * 0.15
    ));

    // Determine salience level
    const level = this.getSalienceLevel(totalScore);
    
    // Generate reasoning for score
    const reasoning = this.generateReasoning(message, {
      content: contentScore,
      authority: authorityScore,
      relevance: relevanceScore,
      temporal: temporalScore
    });

    const salienceScore: SalienceScore = {
      total: Math.round(totalScore * 1000) / 1000, // Round to 3 decimal places
      breakdown: {
        content: Math.round(contentScore * 1000) / 1000,
        authority: Math.round(authorityScore * 1000) / 1000,
        relevance: Math.round(relevanceScore * 1000) / 1000,
        temporal: Math.round(temporalScore * 1000) / 1000
      },
      level,
      reasoning
    };

    // Update context history for future relevance calculations
    this.updateContextHistory(message.content.text);

    const processingTime = Date.now() - startTime;
    logger.debug('[SalienceEngine] Salience calculation complete', {
      totalScore: salienceScore.total,
      level: salienceScore.level,
      processingTime: `${processingTime}ms`,
      reasoning: reasoning.join(', ')
    });

    return salienceScore;
  }

  /**
   * Analyze message content for VTuber mentions, emotional content, and technical topics
   */
  private analyzeContent(message: ChatMessage): number {
    const text = message.content.text.toLowerCase();
    let score = 0.0;

    // Direct mentions or questions to VTuber (+0.4)
    const hasMention = message.content.mentions?.length > 0 || 
                      Array.from(this.vtuberKeywords).some(keyword => text.includes(keyword));
    if (hasMention) {
      score += 0.4;
    }

    // Emotional content analysis (+0.2 max)
    let emotionalScore = 0.0;
    for (const [keyword, impact] of this.emotionalKeywords) {
      if (text.includes(keyword)) {
        emotionalScore = Math.max(emotionalScore, impact);
      }
    }
    score += Math.min(0.2, emotionalScore);

    // Technical/research topics (+0.3 max)
    let technicalScore = 0.0;
    for (const topic of this.technicalTopics) {
      if (text.includes(topic)) {
        technicalScore = Math.max(technicalScore, 0.3);
        break;
      }
    }
    score += technicalScore;

    // Creative suggestions or collaboration ideas (+0.25)
    const creativeKeywords = ['idea', 'suggest', 'collaborate', 'create', 'build', 'project'];
    if (creativeKeywords.some(keyword => text.includes(keyword))) {
      score += 0.25;
    }

    return Math.min(1.0, score);
  }

  /**
   * Analyze author authority based on platform status and history
   */
  private analyzeAuthority(message: ChatMessage): number {
    let score = 0.0;

    // Subscriber/member status (+0.15)
    if (message.author.isSubscriber) {
      score += 0.15;
    }

    // Moderator status (+0.2)
    if (message.author.isModerator) {
      score += 0.2;
    }

    // Long-term follower (+0.1)
    if (message.author.followAge && message.author.followAge > 30) { // 30+ days
      score += 0.1;
    }

    // First-time chatter welcome boost (+0.05)
    if (!message.author.followAge || message.author.followAge === 0) {
      score += 0.05;
    }

    // Badge analysis for platform-specific authority
    const authorityBadges = ['verified', 'partner', 'staff', 'admin', 'founder'];
    if (message.author.badges.some(badge => 
        authorityBadges.some(auth => badge.toLowerCase().includes(auth)))) {
      score += 0.1;
    }

    return Math.min(1.0, score);
  }

  /**
   * Analyze contextual relevance to ongoing conversation and stream topics
   */
  private analyzeRelevance(message: ChatMessage, context: ChatContextUpdate): number {
    const text = message.content.text.toLowerCase();
    let score = 0.0;

    // Match current stream topic from platform context (+0.2)
    const platformContext = context.platforms[message.platform];
    if (platformContext?.topTopics) {
      const matchesCurrentTopic = platformContext.topTopics.some(topic => 
        text.includes(topic.toLowerCase()));
      if (matchesCurrentTopic) {
        score += 0.2;
      }
    }

    // References recent VTuber statements (+0.15)
    const referencesRecentContext = this.contextHistory.slice(-3).some(recentText =>
      this.calculateTextSimilarity(text, recentText.toLowerCase()) > 0.3);
    if (referencesRecentContext) {
      score += 0.15;
    }

    // Builds on ongoing conversation (+0.1)
    if (message.metadata.replyTo || text.includes('yes') || text.includes('agree') || 
        text.includes('also') || text.includes('too')) {
      score += 0.1;
    }

    return Math.min(1.0, score);
  }

  /**
   * Analyze temporal factors including recency, urgency, and chat velocity
   */
  private analyzeTemporalFactors(message: ChatMessage, context: ChatContextUpdate): number {
    const now = Date.now();
    const messageAge = now - message.metadata.timestamp;
    let score = 0.0;

    // Message recency - decay over 5 minutes
    const maxAge = 5 * 60 * 1000; // 5 minutes in milliseconds
    const recencyScore = Math.max(0, 0.15 * (1 - messageAge / maxAge));
    score += recencyScore;

    // Response urgency for questions (+0.1)
    const text = message.content.text.toLowerCase();
    const isQuestion = text.includes('?') || text.startsWith('what') || 
                      text.startsWith('how') || text.startsWith('why') ||
                      text.startsWith('when') || text.startsWith('where');
    if (isQuestion) {
      score += 0.1;
    }

    // Chat velocity adjustment - boost score in active chat
    const platformContext = context.platforms[message.platform];
    if (platformContext && platformContext.activeUsers > 10) {
      const velocityBoost = Math.min(0.1, platformContext.activeUsers / 100);
      score += velocityBoost;
    }

    return Math.min(1.0, score);
  }

  /**
   * Determine salience level based on total score
   */
  private getSalienceLevel(score: number): SalienceLevel {
    if (score >= SalienceLevel.CRITICAL) return SalienceLevel.CRITICAL;
    if (score >= SalienceLevel.HIGH) return SalienceLevel.HIGH;
    if (score >= SalienceLevel.MEDIUM) return SalienceLevel.MEDIUM;
    if (score >= SalienceLevel.LOW) return SalienceLevel.LOW;
    return SalienceLevel.IGNORE;
  }

  /**
   * Generate human-readable reasoning for the salience score
   */
  private generateReasoning(message: ChatMessage, breakdown: any): string[] {
    const reasoning: string[] = [];

    if (breakdown.content > 0.3) {
      reasoning.push('High content relevance (mentions VTuber or key topics)');
    }
    if (breakdown.authority > 0.15) {
      reasoning.push(`Author has platform authority (${message.author.isSubscriber ? 'subscriber' : ''}${message.author.isModerator ? ' moderator' : ''})`);
    }
    if (breakdown.relevance > 0.1) {
      reasoning.push('Contextually relevant to ongoing conversation');
    }
    if (breakdown.temporal > 0.1) {
      reasoning.push('Time-sensitive or recent message');
    }

    if (reasoning.length === 0) {
      reasoning.push('Standard message with basic engagement value');
    }

    return reasoning;
  }

  /**
   * Update context history for relevance calculations
   */
  private updateContextHistory(text: string): void {
    this.contextHistory.push(text);
    
    // Keep only last 10 messages for context
    if (this.contextHistory.length > 10) {
      this.contextHistory.shift();
    }

    // Update topic tracking
    const words = text.toLowerCase().split(/\s+/);
    words.forEach(word => {
      if (word.length > 3) { // Only track meaningful words
        const current = this.recentTopics.get(word) || 0;
        this.recentTopics.set(word, current + 1);
      }
    });

    // Decay topic scores over time
    if (this.recentTopics.size > 50) {
      const entries = Array.from(this.recentTopics.entries());
      entries.sort((a, b) => b[1] - a[1]);
      this.recentTopics = new Map(entries.slice(0, 30));
    }
  }

  /**
   * Calculate similarity between two text strings
   */
  private calculateTextSimilarity(text1: string, text2: string): number {
    const words1 = new Set(text1.split(/\s+/));
    const words2 = new Set(text2.split(/\s+/));
    
    const intersection = new Set([...words1].filter(word => words2.has(word)));
    const union = new Set([...words1, ...words2]);
    
    return intersection.size / union.size; // Jaccard similarity
  }

  /**
   * Get current context statistics for monitoring
   */
  getContextStats() {
    return {
      contextHistorySize: this.contextHistory.length,
      trackedTopics: this.recentTopics.size,
      topTopics: Array.from(this.recentTopics.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([topic, count]) => ({ topic, count }))
    };
  }
} 