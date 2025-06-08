// Temporary mock for @elizaos/core module to resolve import issues during development

export interface IAgentRuntime {
  agentId: string;
  createMemory(memory: Memory, room: string): Promise<void>;
  emitEvent(eventType: EventType, data: any): void;
  getService(serviceType: string): any;
}

export interface Memory {
  id: string;
  entityId: string;
  agentId: string;
  roomId: string;
  content: Content;
  createdAt: number;
}

export interface Content {
  text: string;
  type?: string;
  source?: string;
  [key: string]: any;
}

export enum EventType {
  SERVICE_STARTED = 'service_started',
  MESSAGE_RECEIVED = 'message_received'
}

export abstract class Service {
  protected runtime: IAgentRuntime;
  
  constructor(runtime: IAgentRuntime) {
    this.runtime = runtime;
  }
  
  abstract start(): Promise<void>;
  abstract stop(): Promise<void>;
}

export const logger = {
  info: (message: string, meta?: any) => {
    console.log(`[INFO] ${message}`, meta ? JSON.stringify(meta, null, 2) : '');
  },
  debug: (message: string, meta?: any) => {
    console.log(`[DEBUG] ${message}`, meta ? JSON.stringify(meta, null, 2) : '');
  },
  warn: (message: string, meta?: any) => {
    console.warn(`[WARN] ${message}`, meta ? JSON.stringify(meta, null, 2) : '');
  },
  error: (message: string, error?: any, meta?: any) => {
    console.error(`[ERROR] ${message}`, error, meta ? JSON.stringify(meta, null, 2) : '');
  }
};

export function createUniqueUuid(runtime: IAgentRuntime, prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
} 