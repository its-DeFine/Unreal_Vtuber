import { Service, type IAgentRuntime, type ServiceTypeName, ServiceType, type Plugin, logger, type Memory } from '@elizaos/core';
import { fetch } from 'undici';

export class CogneeService extends Service {
  static serviceType: ServiceTypeName = 'COGNEE' as ServiceTypeName;
  capabilityDescription = 'Long term memory storage using Cognee';

  private baseUrl: string;
  private apiKey: string | null;
  private datasetName: string;

  constructor(runtime: IAgentRuntime) {
    super(runtime);
    this.baseUrl = (runtime.getSetting('COGNEE_URL') as string) ?? 'http://localhost:8000';
    this.apiKey = runtime.getSetting('COGNEE_API_KEY') as string | null;
    this.datasetName = `agent_${runtime.agentId}`;
  }

  static async start(runtime: IAgentRuntime): Promise<CogneeService> {
    return new CogneeService(runtime);
  }

  private getHeaders() {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async addMemory(text: string): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/add`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ data: [text], dataset_name: this.datasetName }),
      });
      if (!res.ok) {
        throw new Error(`Cognee add failed: ${res.status}`);
      }
    } catch (err) {
      logger.error('Cognee addMemory error', err);
    }
  }

  async cognify(): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/cognify`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ dataset_names: [this.datasetName] }),
      });
      if (!res.ok) {
        throw new Error(`Cognee cognify failed: ${res.status}`);
      }
    } catch (err) {
      logger.error('Cognee cognify error', err);
    }
  }

  async search(query: string): Promise<string[]> {
    try {
      const res = await fetch(`${this.baseUrl}/api/v1/search`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ query_text: query, datasets: [this.datasetName] }),
      });
      if (!res.ok) {
        throw new Error(`Cognee search failed: ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((d) => (typeof d === 'string' ? d : JSON.stringify(d)));
      }
    } catch (err) {
      logger.error('Cognee search error', err);
    }
    return [];
  }

  async storeMemory(memory: Memory): Promise<void> {
    if (memory.content && typeof memory.content.text === 'string') {
      await this.addMemory(memory.content.text);
      await this.cognify();
    }
  }
}

const cogneePlugin: Plugin = {
  name: 'COGNEE',
  description: 'Cognee memory integration',
  services: [CogneeService],
  actions: [],
  providers: [],
  routes: [],
  events: {},
  tests: [],
};

export default cogneePlugin;
