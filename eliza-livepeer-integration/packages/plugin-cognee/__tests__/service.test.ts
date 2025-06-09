import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('undici', () => ({
  fetch: vi.fn(),
}));

import { CogneeService } from '../src/index';
import type { IAgentRuntime, Memory, UUID } from '@elizaos/core';
import { fetch } from 'undici';

const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;

function createRuntime(settings: Record<string, string | null> = {}): IAgentRuntime {
  return {
    agentId: 'agent1' as UUID,
    getSetting: (key: string) => settings[key] ?? null,
  } as unknown as IAgentRuntime;
}

describe('CogneeService', () => {
  let service: CogneeService;

  beforeEach(async () => {
    const runtime = createRuntime({ COGNEE_URL: 'http://cognee', COGNEE_API_KEY: 'key' });
    service = await CogneeService.start(runtime);
    mockFetch.mockReset();
  });

  it('calls addMemory endpoint', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) } as any);
    await service.addMemory('hello');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://cognee/api/v1/add',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ data: ['hello'], dataset_name: 'agent_agent1' }),
      })
    );
  });

  it('calls cognify endpoint', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) } as any);
    await service.cognify();
    expect(mockFetch).toHaveBeenCalledWith(
      'http://cognee/api/v1/cognify',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ dataset_names: ['agent_agent1'] }),
      })
    );
  });

  it('search returns results', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ['a', 'b'] } as any);
    const res = await service.search('q');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://cognee/api/v1/search',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ query_text: 'q', datasets: ['agent_agent1'] }),
      })
    );
    expect(res).toEqual(['a', 'b']);
  });

  it('storeMemory delegates to addMemory and cognify', async () => {
    const addSpy = vi.spyOn(service, 'addMemory').mockResolvedValue();
    const cognifySpy = vi.spyOn(service, 'cognify').mockResolvedValue();
    await service.storeMemory({ content: { text: 'hi' } } as Memory);
    expect(addSpy).toHaveBeenCalledWith('hi');
    expect(cognifySpy).toHaveBeenCalled();
  });
});
