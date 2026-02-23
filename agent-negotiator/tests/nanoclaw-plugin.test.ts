import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

const stopMock = vi.fn(async () => {});
const startMock = vi.fn(async () => ({
  config: {
    host: "0.0.0.0",
    port: 9100,
    configFile: "",
    healthUrl: "",
    orchestratorId: "orch-test",
    dataDir: "",
    ethUsdRate: 2500,
    rateLimitPerMinute: 30,
    quoteCleanupIntervalMs: 60_000,
  },
  port: 9100,
  stop: stopMock,
}));

vi.mock("../src/service.js", async () => {
  const actual = await vi.importActual<typeof import("../src/service.js")>("../src/service.js");
  return {
    ...actual,
    startNegotiatorService: startMock,
  };
});

function fakeApi(pluginConfig: Record<string, unknown>) {
  const channels: unknown[] = [];
  const services: Array<{ id: string; start: Function; stop?: Function }> = [];
  const commands: Array<{ name: string; description: string; handler: Function }> = [];

  const api = {
    id: "agent-negotiator",
    name: "agent-negotiator",
    source: "test",
    config: {},
    pluginConfig,
    runtime: {
      state: {
        resolveStateDir: () => os.tmpdir(),
      },
    },
    logger: {
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    },
    registerTool: vi.fn(),
    registerHook: vi.fn(),
    registerHttpHandler: vi.fn(),
    registerHttpRoute: vi.fn(),
    registerChannel: vi.fn((registration: unknown) => {
      channels.push(registration);
    }),
    registerGatewayMethod: vi.fn(),
    registerCli: vi.fn(),
    registerService: vi.fn((service: { id: string; start: Function; stop?: Function }) => {
      services.push(service);
    }),
    registerProvider: vi.fn(),
    registerCommand: vi.fn((command: { name: string; description: string; handler: Function }) => {
      commands.push(command);
    }),
    resolvePath: (input: string) => input,
    on: vi.fn(),
  };

  return { api: api as any, channels, services, commands };
}

describe("NanoClaw agent-negotiator plugin", () => {
  beforeEach(() => {
    startMock.mockClear();
    stopMock.mockClear();
    vi.resetModules();
  });

  it("registers channel, service, and command", async () => {
    const { default: plugin } = await import("../src/nanoclaw/plugin.js");
    const { api, channels, services, commands } = fakeApi({ enabled: true, port: 19010 });

    plugin.register(api);

    expect(channels.length).toBe(1);
    expect(services.length).toBe(1);
    expect(services[0].id).toBe("agent-negotiator-mcp");
    expect(commands.some((c) => c.name === "negotiator")).toBe(true);
  });

  it("starts/stops embedded service when enabled", async () => {
    const { default: plugin } = await import("../src/nanoclaw/plugin.js");
    const { api, services } = fakeApi({ enabled: true, port: 19011 });

    plugin.register(api);
    const service = services[0];

    const tmpState = fs.mkdtempSync(path.join(os.tmpdir(), "plugin-service-test-"));
    await service.start({
      config: {},
      workspaceDir: tmpState,
      stateDir: tmpState,
      logger: api.logger,
    });

    expect(startMock).toHaveBeenCalledTimes(1);

    await service.stop?.({
      config: {},
      workspaceDir: tmpState,
      stateDir: tmpState,
      logger: api.logger,
    });
    expect(stopMock).toHaveBeenCalledTimes(1);
  });

  it("does not start service when plugin is disabled", async () => {
    const { default: plugin } = await import("../src/nanoclaw/plugin.js");
    const { api, services } = fakeApi({ enabled: false, port: 19012 });

    plugin.register(api);
    const service = services[0];

    const tmpState = fs.mkdtempSync(path.join(os.tmpdir(), "plugin-disabled-test-"));
    await service.start({
      config: {},
      workspaceDir: tmpState,
      stateDir: tmpState,
      logger: api.logger,
    });

    expect(startMock).toHaveBeenCalledTimes(0);
  });
});
