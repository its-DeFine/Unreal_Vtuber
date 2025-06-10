import { logger } from '@elizaos/core';
import { 
  AttentionState, 
  AttentionCycle, 
  AttentionInterrupt, 
  ChatMessage, 
  ChatContextUpdate,
  SalienceLevel 
} from './types';

/**
 * Human-Like Attention Management System
 * 
 * Simulates natural streamer behavior patterns through attention cycles.
 * Manages state transitions, response rates, and interrupt handling
 * to create authentic human-like interaction patterns.
 */
export class AttentionManager {
  private currentCycle: AttentionCycle;
  private stateHistory: Array<{ state: AttentionState; timestamp: number; duration: number }> = [];
  private lastInteractionTime: number = Date.now();
  private consecutiveHighSalienceMessages: number = 0;
  private recentMessageVelocity: number[] = [];

  // Configuration for attention states
  private readonly stateConfig = {
    [AttentionState.FOCUSED_INTERACTION]: {
      responseRate: 0.8,
      averageDuration: 5 * 60 * 1000,  // 5 minutes
      probability: 0.4  // 40% of time
    },
    [AttentionState.CASUAL_MONITORING]: {
      responseRate: 0.4,
      averageDuration: 7 * 60 * 1000,  // 7 minutes  
      probability: 0.35  // 35% of time
    },
    [AttentionState.DEEP_FOCUS]: {
      responseRate: 0.1,
      averageDuration: 10 * 60 * 1000,  // 10 minutes
      probability: 0.2  // 20% of time
    },
    [AttentionState.BREAK_TRANSITION]: {
      responseRate: 0.6,
      averageDuration: 2 * 60 * 1000,  // 2 minutes
      probability: 0.05  // 5% of time
    }
  };

  constructor() {
    logger.info('[AttentionManager] 👁️ Initializing human-like attention management system');
    
    // Initialize with a random state weighted by probability
    const initialState = this.selectRandomState();
    this.currentCycle = this.createCycle(initialState);
    
    logger.info('[AttentionManager] ✅ Attention system initialized', {
      initialState: this.currentCycle.currentState,
      responseRate: this.currentCycle.responseRate,
      duration: this.currentCycle.stateDuration
    });
  }

  /**
   * Initialize the attention management system
   */
  initialize(): void {
    logger.info('[AttentionManager] 🔄 Starting attention management system');
    this.logStateTransition(this.currentCycle.currentState, 'System initialization');
  }

  /**
   * Update attention state and handle transitions
   */
  update(): void {
    const now = Date.now();
    const timeInCurrentState = now - this.currentCycle.stateStartTime;
    
    // Check if it's time to transition to a new state
    if (timeInCurrentState >= this.currentCycle.stateDuration) {
      this.transitionToNewState('Time-based transition');
    }
    
    // Update message velocity tracking
    this.updateMessageVelocity();
    
    // Log periodic status
    if (Math.random() < 0.1) { // 10% chance to log status
      logger.debug('[AttentionManager] 📊 Current attention status', {
        state: this.currentCycle.currentState,
        timeInState: timeInCurrentState,
        responseRate: this.currentCycle.responseRate,
        recentVelocity: this.getAverageMessageVelocity()
      });
    }
  }

  /**
   * Check for attention interrupts based on message content and context
   */
  checkForInterrupt(message: ChatMessage, context: ChatContextUpdate): AttentionInterrupt | null {
    // Always interrupt for critical messages
    if (message.salience.level === SalienceLevel.CRITICAL) {
      this.consecutiveHighSalienceMessages++;
      return {
        type: 'high_salience',
        priority: 1.0,
        context: {
          platform: message.platform,
          averageSalience: message.salience.total,
          eventType: 'critical_message'
        },
        suggested_action: 'immediate_response'
      };
    }

    // Check for message spikes
    const currentVelocity = this.getAverageMessageVelocity();
    if (currentVelocity > 10) { // More than 10 messages per minute
      return {
        type: 'message_spike',
        priority: 0.7,
        context: {
          platform: message.platform,
          messageCount: Math.round(currentVelocity),
          averageSalience: message.salience.total
        },
        suggested_action: 'attention_shift'
      };
    }

    // Check for consecutive high salience messages
    if (message.salience.level >= SalienceLevel.HIGH) {
      this.consecutiveHighSalienceMessages++;
      
      if (this.consecutiveHighSalienceMessages >= 3) {
        this.consecutiveHighSalienceMessages = 0; // Reset counter
        return {
          type: 'high_salience',
          priority: 0.8,
          context: {
            platform: message.platform,
            averageSalience: message.salience.total,
            eventType: 'consecutive_high_salience'
          },
          suggested_action: 'queue_priority'
        };
      }
    } else {
      this.consecutiveHighSalienceMessages = 0;
    }

    // Check for extended periods without interaction
    const timeSinceLastInteraction = Date.now() - this.lastInteractionTime;
    if (timeSinceLastInteraction > 5 * 60 * 1000) { // 5 minutes
      return {
        type: 'autonomous_trigger',
        priority: 0.6,
        context: {
          platform: message.platform,
          eventType: 'extended_silence'
        },
        suggested_action: 'attention_shift'
      };
    }

    return null;
  }

  /**
   * Transition to a new attention state
   */
  private transitionToNewState(reason: string): void {
    const previousState = this.currentCycle.currentState;
    const previousDuration = Date.now() - this.currentCycle.stateStartTime;
    
    // Record state history
    this.stateHistory.push({
      state: previousState,
      timestamp: this.currentCycle.stateStartTime,
      duration: previousDuration
    });

    // Select new state based on context and probabilities
    const newState = this.selectNextState(previousState);
    this.currentCycle = this.createCycle(newState);

    logger.info('[AttentionManager] 🔄 Attention state transition', {
      from: previousState,
      to: newState,
      reason,
      previousDuration: `${Math.round(previousDuration / 1000)}s`,
      newResponseRate: this.currentCycle.responseRate,
      newDuration: `${Math.round(this.currentCycle.stateDuration / 1000)}s`
    });

    this.logStateTransition(newState, reason);
  }

  /**
   * Select next attention state based on current state and context
   */
  private selectNextState(currentState: AttentionState): AttentionState {
    // Define transition probabilities based on current state
    const transitionMatrix: Record<AttentionState, Record<AttentionState, number>> = {
      [AttentionState.FOCUSED_INTERACTION]: {
        [AttentionState.FOCUSED_INTERACTION]: 0.2,
        [AttentionState.CASUAL_MONITORING]: 0.5,
        [AttentionState.DEEP_FOCUS]: 0.25,
        [AttentionState.BREAK_TRANSITION]: 0.05
      },
      [AttentionState.CASUAL_MONITORING]: {
        [AttentionState.FOCUSED_INTERACTION]: 0.4,
        [AttentionState.CASUAL_MONITORING]: 0.3,
        [AttentionState.DEEP_FOCUS]: 0.2,
        [AttentionState.BREAK_TRANSITION]: 0.1
      },
      [AttentionState.DEEP_FOCUS]: {
        [AttentionState.FOCUSED_INTERACTION]: 0.15,
        [AttentionState.CASUAL_MONITORING]: 0.4,
        [AttentionState.DEEP_FOCUS]: 0.25,
        [AttentionState.BREAK_TRANSITION]: 0.2
      },
      [AttentionState.BREAK_TRANSITION]: {
        [AttentionState.FOCUSED_INTERACTION]: 0.6,
        [AttentionState.CASUAL_MONITORING]: 0.3,
        [AttentionState.DEEP_FOCUS]: 0.05,
        [AttentionState.BREAK_TRANSITION]: 0.05
      }
    };

    const probabilities = transitionMatrix[currentState];
    return this.selectRandomStateFromProbabilities(probabilities);
  }

  /**
   * Select random state based on probability distribution
   */
  private selectRandomStateFromProbabilities(probabilities: Record<AttentionState, number>): AttentionState {
    const random = Math.random();
    let cumulative = 0;

    for (const [state, probability] of Object.entries(probabilities)) {
      cumulative += probability;
      if (random <= cumulative) {
        return state as AttentionState;
      }
    }

    // Fallback to casual monitoring
    return AttentionState.CASUAL_MONITORING;
  }

  /**
   * Select random state weighted by overall probabilities
   */
  private selectRandomState(): AttentionState {
    const probabilities = {
      [AttentionState.FOCUSED_INTERACTION]: this.stateConfig[AttentionState.FOCUSED_INTERACTION].probability,
      [AttentionState.CASUAL_MONITORING]: this.stateConfig[AttentionState.CASUAL_MONITORING].probability,
      [AttentionState.DEEP_FOCUS]: this.stateConfig[AttentionState.DEEP_FOCUS].probability,
      [AttentionState.BREAK_TRANSITION]: this.stateConfig[AttentionState.BREAK_TRANSITION].probability
    };

    return this.selectRandomStateFromProbabilities(probabilities);
  }

  /**
   * Create a new attention cycle for the given state
   */
  private createCycle(state: AttentionState): AttentionCycle {
    const config = this.stateConfig[state];
    const now = Date.now();
    
    // Add some randomness to duration (±25%)
    const randomFactor = 0.75 + Math.random() * 0.5;
    const duration = Math.round(config.averageDuration * randomFactor);
    
    // Add some randomness to response rate (±10%)
    const responseRandomFactor = 0.9 + Math.random() * 0.2;
    const responseRate = Math.min(1.0, Math.max(0.0, config.responseRate * responseRandomFactor));

    return {
      currentState: state,
      stateStartTime: now,
      stateDuration: duration,
      responseRate,
      interruptThreshold: this.calculateInterruptThreshold(state),
      nextTransition: now + duration
    };
  }

  /**
   * Calculate interrupt threshold based on attention state
   */
  private calculateInterruptThreshold(state: AttentionState): number {
    switch (state) {
      case AttentionState.FOCUSED_INTERACTION: return 0.6; // Easy to interrupt
      case AttentionState.CASUAL_MONITORING: return 0.7;   // Moderately interruptible
      case AttentionState.DEEP_FOCUS: return 0.9;          // Hard to interrupt
      case AttentionState.BREAK_TRANSITION: return 0.5;    // Very interruptible
      default: return 0.7;
    }
  }

  /**
   * Update message velocity tracking
   */
  private updateMessageVelocity(): void {
    const now = Date.now();
    
    // Remove entries older than 1 minute
    this.recentMessageVelocity = this.recentMessageVelocity.filter(
      timestamp => now - timestamp < 60 * 1000
    );
  }

  /**
   * Record a new message for velocity tracking
   */
  recordMessage(): void {
    this.recentMessageVelocity.push(Date.now());
    this.lastInteractionTime = Date.now();
  }

  /**
   * Get average message velocity (messages per minute)
   */
  private getAverageMessageVelocity(): number {
    return this.recentMessageVelocity.length; // Already filtered to last minute
  }

  /**
   * Log state transition for monitoring
   */
  private logStateTransition(newState: AttentionState, reason: string): void {
    logger.info('[AttentionManager] 📝 State transition logged', {
      state: newState,
      reason,
      responseRate: this.currentCycle.responseRate,
      duration: this.currentCycle.stateDuration,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Get current attention state
   */
  getCurrentState(): AttentionState {
    return this.currentCycle.currentState;
  }

  /**
   * Get current response rate
   */
  getResponseRate(): number {
    return this.currentCycle.responseRate;
  }

  /**
   * Get recommended action based on current context
   */
  getRecommendedAction(): string {
    const state = this.currentCycle.currentState;
    const velocity = this.getAverageMessageVelocity();
    const timeSinceLastInteraction = Date.now() - this.lastInteractionTime;

    if (timeSinceLastInteraction > 10 * 60 * 1000) {
      return 'initiate_conversation';
    }

    if (velocity > 15) {
      return 'increase_attention';
    }

    if (velocity < 2 && state === AttentionState.FOCUSED_INTERACTION) {
      return 'casual_topic_transition';
    }

    switch (state) {
      case AttentionState.FOCUSED_INTERACTION:
        return 'maintain_engagement';
      case AttentionState.CASUAL_MONITORING:
        return 'selective_responses';
      case AttentionState.DEEP_FOCUS:
        return 'minimal_interaction';
      case AttentionState.BREAK_TRANSITION:
        return 'catch_up_mode';
      default:
        return 'maintain_current_state';
    }
  }

  /**
   * Get attention statistics for monitoring
   */
  getStats() {
    const now = Date.now();
    const timeInCurrentState = now - this.currentCycle.stateStartTime;
    
    return {
      currentState: this.currentCycle.currentState,
      timeInCurrentState,
      responseRate: this.currentCycle.responseRate,
      interruptThreshold: this.currentCycle.interruptThreshold,
      messageVelocity: this.getAverageMessageVelocity(),
      timeSinceLastInteraction: now - this.lastInteractionTime,
      stateHistory: this.stateHistory.slice(-5), // Last 5 state changes
      nextTransition: this.currentCycle.nextTransition,
      consecutiveHighSalienceMessages: this.consecutiveHighSalienceMessages
    };
  }

  /**
   * Force a state transition (for testing or manual control)
   */
  forceStateTransition(newState: AttentionState, reason: string = 'Manual override'): void {
    logger.warn('[AttentionManager] ⚠️ Forcing state transition', {
      from: this.currentCycle.currentState,
      to: newState,
      reason
    });

    this.currentCycle = this.createCycle(newState);
    this.logStateTransition(newState, reason);
  }
} 