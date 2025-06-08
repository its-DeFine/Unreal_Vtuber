import { logger } from './core-mock';
import { 
  ChatMessage, 
  ChatContextUpdate, 
  VTuberResponse,
  SalienceLevel 
} from './types';

/**
 * VTuber Response Generation Pipeline
 * 
 * Orchestrates response generation by consulting Autoliza autonomous agent,
 * applying personality context, and generating contextually appropriate responses.
 */
export class ResponsePipeline {
  private runtime: any;
  private responseTemplates: Map<string, string[]>;
  private neurosyncEndpoint: string;

  constructor(runtime: any) {
    this.runtime = runtime;
    this.neurosyncEndpoint = process.env.NEUROSYNC_ENDPOINT || 'http://localhost:5001/process_text';
    
    logger.info('[ResponsePipeline] 🤖 Initializing VTuber response generation system');
    
    this.initializeResponseTemplates();
    
    logger.info('[ResponsePipeline] ✅ Response pipeline initialized', {
      endpoint: this.neurosyncEndpoint,
      templates: this.responseTemplates.size
    });
  }

  /**
   * Initialize response templates for different scenarios
   */
  private initializeResponseTemplates(): void {
    this.responseTemplates = new Map([
      ['greeting', [
        'Hello! 👋 Welcome to the stream!',
        'Hey there! Thanks for joining us! 😊',
        'Welcome! Great to have you here! ✨'
      ]],
      ['question_response', [
        'That\'s a great question! Let me think about that...',
        'Interesting point! Here\'s what I think...',
        'Oh, I love questions like this! 🤔'
      ]],
      ['technical_discussion', [
        'That\'s fascinating from a technical perspective!',
        'I find that aspect of AI research really intriguing...',
        'The neural network implications of that are quite interesting!'
      ]],
      ['emotional_support', [
        'I understand how you feel about that 💜',
        'That sounds really challenging, thank you for sharing',
        'Your feelings are completely valid! ✨'
      ]],
      ['creative_collaboration', [
        'What an amazing creative idea! 🎨',
        'I\'d love to explore that concept further!',
        'That could lead to something really interesting!'
      ]],
      ['casual_chat', [
        'Haha, that\'s so true! 😄',
        'I totally get what you mean!',
        'That\'s actually really cool! ✨'
      ]],
      ['appreciation', [
        'Thank you so much! That means a lot! 💜',
        'Aww, you\'re so sweet! Thank you! 😊',
        'I really appreciate your support! ✨'
      ]]
    ]);
  }

  /**
   * Generate response for a chat message
   */
  async generateResponse(
    message: ChatMessage, 
    context: ChatContextUpdate
  ): Promise<VTuberResponse | null> {
    const startTime = Date.now();
    
    try {
      logger.debug('[ResponsePipeline] 🔄 Generating response', {
        messageId: message.id,
        platform: message.platform,
        salienceLevel: message.salience.level,
        author: message.author.username
      });

      // Step 1: Determine response category
      const responseCategory = this.categorizeMessage(message);
      
      // Step 2: Get Autoliza guidance
      const autonomousContext = await this.getAutolizaGuidance(message, context);
      
      // Step 3: Generate base response
      const baseResponse = await this.generateBaseResponse(message, responseCategory, autonomousContext);
      
      // Step 4: Enhance with NeuroSync if available
      const enhancedResponse = await this.enhanceWithNeuroSync(baseResponse, message, context);
      
      // Step 5: Apply personality and emotion
      const finalResponse = this.applyPersonalityContext(enhancedResponse, message, autonomousContext);

      const processingTime = Date.now() - startTime;
      
      logger.info('[ResponsePipeline] ✅ Response generated', {
        messageId: message.id,
        platform: message.platform,
        responseLength: finalResponse.text.length,
        category: responseCategory,
        processingTime: `${processingTime}ms`,
        confidence: finalResponse.metadata.confidence
      });

      return finalResponse;

    } catch (error) {
      logger.error('[ResponsePipeline] ❌ Error generating response:', error, {
        messageId: message.id,
        platform: message.platform
      });
      
      // Return fallback response
      return this.generateFallbackResponse(message);
    }
  }

  /**
   * Categorize message to determine response approach
   */
  private categorizeMessage(message: ChatMessage): string {
    const text = message.content.text.toLowerCase();
    
    // Check for greetings
    if (text.includes('hello') || text.includes('hi ') || text.includes('hey') || 
        text.includes('welcome') || text.includes('first time')) {
      return 'greeting';
    }
    
    // Check for questions
    if (text.includes('?') || text.startsWith('what') || text.startsWith('how') || 
        text.startsWith('why') || text.startsWith('when') || text.startsWith('where')) {
      return 'question_response';
    }
    
    // Check for technical topics
    if (text.includes('ai') || text.includes('neural') || text.includes('machine learning') || 
        text.includes('algorithm') || text.includes('code') || text.includes('programming')) {
      return 'technical_discussion';
    }
    
    // Check for emotional content
    if (text.includes('sad') || text.includes('worried') || text.includes('anxious') || 
        text.includes('stressed') || text.includes('difficult')) {
      return 'emotional_support';
    }
    
    // Check for creative content
    if (text.includes('idea') || text.includes('create') || text.includes('build') || 
        text.includes('project') || text.includes('collaborate')) {
      return 'creative_collaboration';
    }
    
    // Check for appreciation
    if (text.includes('thank') || text.includes('awesome') || text.includes('amazing') || 
        text.includes('love') || text.includes('great')) {
      return 'appreciation';
    }
    
    // Default to casual chat
    return 'casual_chat';
  }

  /**
   * Get strategic guidance from Autoliza autonomous agent
   */
  private async getAutolizaGuidance(
    message: ChatMessage, 
    context: ChatContextUpdate
  ): Promise<any> {
    try {
      // Create a consultation request for Autoliza
      const consultationRequest = {
        type: 'chat_response_consultation',
        message: {
          text: message.content.text,
          author: message.author.username,
          platform: message.platform,
          salience: message.salience
        },
        context: {
          platformActivity: context.platforms[message.platform],
          globalEngagement: context.globalContext,
          recentTopics: [] // TODO: Extract from context
        },
        requestedGuidance: [
          'response_tone',
          'conversation_direction',
          'personality_adjustment',
          'topic_suggestions'
        ]
      };

      // TODO: Integrate with actual Autoliza system
      // For now, return mock guidance based on context
      return {
        tone: this.inferToneFromContext(message, context),
        direction: this.inferConversationDirection(message, context),
        personality: 'curious_researcher',
        topicSuggestions: [],
        confidence: 0.8
      };

    } catch (error) {
      logger.error('[ResponsePipeline] ❌ Error getting Autoliza guidance:', error);
      return {
        tone: 'friendly',
        direction: 'maintain',
        personality: 'default',
        confidence: 0.5
      };
    }
  }

  /**
   * Generate base response using templates and context
   */
  private async generateBaseResponse(
    message: ChatMessage, 
    category: string, 
    autonomousContext: any
  ): Promise<string> {
    const templates = this.responseTemplates.get(category) || this.responseTemplates.get('casual_chat')!;
    let baseResponse = templates[Math.floor(Math.random() * templates.length)];
    
    // Customize based on message content
    if (category === 'question_response') {
      baseResponse += ` ${this.generateQuestionResponse(message)}`;
    } else if (category === 'technical_discussion') {
      baseResponse += ` ${this.generateTechnicalResponse(message)}`;
    } else if (category === 'greeting') {
      baseResponse = this.personalizeGreeting(message, baseResponse);
    }
    
    return baseResponse;
  }

  /**
   * Enhance response using NeuroSync VTuber system
   */
  private async enhanceWithNeuroSync(
    baseResponse: string, 
    message: ChatMessage, 
    context: ChatContextUpdate
  ): Promise<string> {
    try {
      const neurosyncPayload = {
        text: baseResponse,
        context: {
          originalMessage: message.content.text,
          platform: message.platform,
          author: message.author.username,
          emotion: 'neutral',
          urgency: message.salience.level >= SalienceLevel.HIGH ? 'high' : 'normal'
        }
      };

      // Make request to NeuroSync endpoint
      const response = await fetch(this.neurosyncEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(neurosyncPayload)
      });

      if (response.ok) {
        const result = await response.json();
        logger.debug('[ResponsePipeline] ✅ NeuroSync enhancement applied', {
          originalLength: baseResponse.length,
          enhancedLength: result.enhanced_text?.length || baseResponse.length
        });
        
        return result.enhanced_text || baseResponse;
      } else {
        logger.warn('[ResponsePipeline] ⚠️ NeuroSync enhancement failed, using base response');
        return baseResponse;
      }

    } catch (error) {
      logger.debug('[ResponsePipeline] 💡 NeuroSync unavailable, using base response');
      return baseResponse;
    }
  }

  /**
   * Apply personality context and finalize response
   */
  private applyPersonalityContext(
    response: string, 
    message: ChatMessage, 
    autonomousContext: any
  ): VTuberResponse {
    // Apply tone adjustments based on autonomous guidance
    let finalText = response;
    
    if (autonomousContext.tone === 'excited') {
      finalText += ' ✨';
    } else if (autonomousContext.tone === 'thoughtful') {
      finalText = '🤔 ' + finalText;
    } else if (autonomousContext.tone === 'supportive') {
      finalText += ' 💜';
    }

    return {
      text: finalText,
      emotion: this.mapToneToEmotion(autonomousContext.tone),
      priority: message.salience.total,
      targetPlatform: message.platform,
      metadata: {
        responseTime: Date.now(),
        confidence: autonomousContext.confidence || 0.7,
        originalMessage: message.content.text,
        autonomousContext
      }
    };
  }

  /**
   * Generate fallback response for error cases
   */
  private generateFallbackResponse(message: ChatMessage): VTuberResponse {
    const fallbackResponses = [
      'Thanks for your message! 😊',
      'I appreciate you sharing that!',
      'That\'s really interesting! ✨',
      'Thanks for being part of the community! 💜'
    ];

    const text = fallbackResponses[Math.floor(Math.random() * fallbackResponses.length)];

    return {
      text,
      emotion: 'neutral',
      priority: 0.3,
      targetPlatform: message.platform,
      metadata: {
        responseTime: Date.now(),
        confidence: 0.4,
        originalMessage: message.content.text,
        isFallback: true
      }
    };
  }

  /**
   * Helper methods for response generation
   */
  private generateQuestionResponse(message: ChatMessage): string {
    const responses = [
      'From my understanding of AI and neural networks...',
      'Based on my research experience...',
      'That\'s something I\'ve been exploring in my work...',
      'Let me share what I\'ve learned about that...'
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  private generateTechnicalResponse(message: ChatMessage): string {
    const responses = [
      'The neural architecture for that is quite fascinating!',
      'I\'ve been researching similar concepts in my autonomous systems work.',
      'That touches on some interesting machine learning principles!',
      'The computational aspects of that are really compelling!'
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  private personalizeGreeting(message: ChatMessage, baseResponse: string): string {
    if (message.author.isSubscriber) {
      return `${baseResponse} Thank you for your continued support! 💜`;
    } else if (message.author.followAge === 0) {
      return `${baseResponse} Welcome to your first stream with us! 🎉`;
    }
    return baseResponse;
  }

  private inferToneFromContext(message: ChatMessage, context: ChatContextUpdate): string {
    if (message.salience.level === SalienceLevel.CRITICAL) return 'excited';
    if (message.content.text.toLowerCase().includes('sad')) return 'supportive';
    if (message.content.text.includes('?')) return 'thoughtful';
    return 'friendly';
  }

  private inferConversationDirection(message: ChatMessage, context: ChatContextUpdate): string {
    const globalTrend = context.globalContext.engagementTrend;
    if (globalTrend === 'decreasing') return 'energize';
    if (globalTrend === 'increasing') return 'maintain';
    return 'explore';
  }

  private mapToneToEmotion(tone: string): string {
    const mapping: Record<string, string> = {
      'excited': 'happy',
      'supportive': 'caring',
      'thoughtful': 'contemplative',
      'friendly': 'neutral'
    };
    return mapping[tone] || 'neutral';
  }

  /**
   * Get pipeline statistics
   */
  getStats() {
    return {
      templatesLoaded: this.responseTemplates.size,
      neurosyncEndpoint: this.neurosyncEndpoint,
      categoriesAvailable: Array.from(this.responseTemplates.keys())
    };
  }
} 