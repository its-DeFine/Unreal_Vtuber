import { createUniqueUuid, Entity, IAgentRuntime, Memory, Service, logger } from '@elizaos/core';
import { EventType } from './types';

export default class AutonomousService extends Service {
  static serviceType = 'autonomous';
  capabilityDescription = 'Autonomous agent service, maintains the autonomous agent loop with context awareness';
  private contextStore: Map<string, any> = new Map();
  private iterationCount: number = 0;

  async stop(): Promise<void> {
    logger.info('[AutonomousService] Service stopped');
    return;
  }

  static async start(runtime: IAgentRuntime): Promise<Service> {
    const autoService = new AutonomousService(runtime);
    return autoService;
  }

  static async stop(runtime: IAgentRuntime): Promise<void> {
    runtime.getService(AutonomousService.serviceType).stop();
    return;
  }

  constructor(runtime: IAgentRuntime) {
    super(runtime);
    this.runtime = runtime;

    this.setupWorld().then(() => {
      this.initializeContext().then(() => {
        this.loop();
      });
    });
  }

  async setupWorld() {
    const worldId = createUniqueUuid(this.runtime, 'auto');
    const world = await this.runtime.getWorld(worldId);

    const copilotEntityId = createUniqueUuid(this.runtime, 'copilot');

    const entityExists = await this.runtime.getEntityById(copilotEntityId);

    if (!entityExists) {
      const copilot: Entity = {
        id: copilotEntityId,
        names: ['Copilot'],
        agentId: this.runtime.agentId,
      };

      await this.runtime.createEntity(copilot);
    }

    if (!world) {
      await this.runtime.createWorld({
        id: worldId,
        name: 'Auto',
        agentId: this.runtime.agentId,
        serverId: createUniqueUuid(this.runtime, 'auto'),
      });
    }
  }

  async initializeContext() {
    logger.info('[AutonomousService] Initializing context store');
    
    // Load existing context from memory if it exists
    try {
      const contextMemories = await this.runtime.getMemories({
        tableName: 'facts',
        count: 20,
        unique: true,
      });

      // Load strategic context (goals, strategies, patterns)
      const strategicContext = contextMemories.filter(m => 
        m.content.type === 'goal' || 
        m.content.type === 'strategy' || 
        m.content.type === 'pattern' ||
        m.content.source === 'autonomous_context_update'
      );

      this.contextStore.set('strategic_knowledge', strategicContext);
      
      // Load recent research findings
      const researchContext = contextMemories.filter(m => 
        m.content.type === 'research_result'
      );
      
      this.contextStore.set('research_findings', researchContext);

      // Set initial goals if none exist
      if (strategicContext.length === 0) {
        const initialGoals = [
          {
            content: {
              text: 'Maintain engaging VTuber interactions through contextual prompts',
              type: 'goal',
              importance: 'high',
              category: 'vtuber_management'
            }
          },
          {
            content: {
              text: 'Continuously learn and adapt through research and context updates',
              type: 'goal', 
              importance: 'high',
              category: 'self_improvement'
            }
          },
          {
            content: {
              text: 'Keep SCB space coherent with current activities and emotional state',
              type: 'goal',
              importance: 'medium',
              category: 'scb_management'
            }
          }
        ];
        
        this.contextStore.set('strategic_knowledge', initialGoals);
      }

      logger.info(`[AutonomousService] Context initialized with ${strategicContext.length} strategic items and ${researchContext.length} research items`);
      
    } catch (error) {
      logger.error('[AutonomousService] Error initializing context:', error);
      // Set minimal default context
      this.contextStore.set('strategic_knowledge', []);
      this.contextStore.set('research_findings', []);
    }
  }

  async getContextSummary(): Promise<string> {
    const strategic = this.contextStore.get('strategic_knowledge') || [];
    const research = this.contextStore.get('research_findings') || [];
    
    let contextSummary = `## Agent Context (Iteration ${this.iterationCount})\n\n`;
    
    if (strategic.length > 0) {
      contextSummary += '### Strategic Knowledge & Goals:\n';
      strategic.slice(-5).forEach((item: any) => {
        const content = item.content || item;
        contextSummary += `- ${content.text} (${content.category || 'general'})\n`;
      });
      contextSummary += '\n';
    }
    
    if (research.length > 0) {
      contextSummary += '### Recent Research:\n';
      research.slice(-3).forEach((item: any) => {
        const content = item.content || item;
        contextSummary += `- ${content.text}\n`;
      });
      contextSummary += '\n';
    }

    // Add current state summary
    contextSummary += '### Current State:\n';
    contextSummary += `- Autonomous loop iteration: ${this.iterationCount}\n`;
    contextSummary += `- Available actions: SEND_TO_VTUBER, UPDATE_SCB_SPACE, DO_RESEARCH, UPDATE_CONTEXT\n`;
    contextSummary += `- Agent role: Autonomous VTuber management and learning system\n\n`;

    return contextSummary;
  }

  async updateContextStore(key: string, value: any) {
    this.contextStore.set(key, value);
    logger.debug(`[AutonomousService] Context updated: ${key}`);
  }

  async loop() {
    this.iterationCount++;
    logger.info(`[AutonomousService] Starting autonomous loop iteration ${this.iterationCount}`);

    const copilotEntityId = createUniqueUuid(this.runtime, this.runtime.agentId);
    const contextSummary = await this.getContextSummary();

    const enhancedPrompt = `${contextSummary}

## Current Situation Analysis
You are an autonomous agent managing a VTuber system. Based on your context above, analyze the current situation and decide what actions to take.

Available actions:
- SEND_TO_VTUBER: Send specific prompts to the VTuber for speech/interaction
- UPDATE_SCB_SPACE: Update the VTuber's emotional state, environment, or behavior 
- DO_RESEARCH: Conduct research on topics to expand knowledge
- UPDATE_CONTEXT: Store new insights, strategies, or facts for future reference

Consider:
1. What would improve the VTuber experience right now?
2. What knowledge gaps need to be filled through research?
3. What have you learned that should be stored for future use?
4. How can you maintain coherent and engaging VTuber behavior?

Think strategically about your goals and choose actions that will have the most impact. You can choose multiple actions if appropriate.

What will you do next? Please think, plan and act autonomously.`;

    const newMessage: Memory = {
      content: {
        text: enhancedPrompt,
        type: 'text',
        source: 'auto',
      },
      roomId: createUniqueUuid(this.runtime, 'auto'),
      worldId: createUniqueUuid(this.runtime, 'auto'),
      entityId: copilotEntityId,
    };

    await this.runtime.emitEvent(EventType.AUTO_MESSAGE_RECEIVED, {
      runtime: this.runtime,
      message: newMessage,
      callback: (content) => {
        logger.info('[AutonomousService] Loop iteration response:', content.text?.substring(0, 100) + '...');
        logger.debug('[AutonomousService] Full response:', content);
      },
      onComplete: () => {
        logger.info(`[AutonomousService] Loop iteration ${this.iterationCount} completed`);
        
        // Schedule next iteration
        const interval = this.runtime.getSetting('AUTONOMOUS_LOOP_INTERVAL') || 30000; // Default 30 seconds
        setTimeout(
          async () => {
            try {
              await this.loop();
            } catch (error) {
              logger.error('[AutonomousService] Error in autonomous loop:', error);
              // Continue loop even if one iteration fails
              setTimeout(() => this.loop(), interval);
            }
          },
          interval
        );
      },
    });
  }
}
