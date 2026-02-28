import path from "node:path";
import type {
  NanoClawPluginApi,
  NanoClawPluginService,
  NanoClawPluginServiceContext,
} from "openclaw/plugin-sdk";
import { mcpNegotiationChannelPlugin } from "./channel.js";
import {
  agentNegotiatorPluginConfigSchema,
  parseAgentNegotiatorPluginConfig,
} from "./plugin-config.js";
import {
  loadNegotiatorEnvConfig,
  startNegotiatorService,
  type NegotiatorLogger,
  type NegotiatorServiceHandle,
} from "../service.js";
import { ensureNegotiatorConfigFile } from "./default-config.js";

function serviceLogger(api: NanoClawPluginApi): NegotiatorLogger {
  return {
    info: (message) => api.logger.info(message),
    warn: (message) => api.logger.warn(message),
    error: (message) => api.logger.error(message),
  };
}

function resolveServiceConfig(
  api: NanoClawPluginApi,
  ctx: NanoClawPluginServiceContext
) {
  const pluginConfig = parseAgentNegotiatorPluginConfig(api.pluginConfig);
  const dataDir = pluginConfig.dataDir ?? path.join(ctx.stateDir, "agent-negotiator");
  const configFile =
    pluginConfig.configFile ?? path.join(dataDir, "config", "negotiator.yaml");

  const logger = serviceLogger(api);
  ensureNegotiatorConfigFile(configFile, logger);

  const resolved = loadNegotiatorEnvConfig({
    host: pluginConfig.host,
    port: pluginConfig.port,
    configFile,
    skillPolicyFile: pluginConfig.skillPolicyFile,
    healthUrl: pluginConfig.healthUrl,
    signalingPublicBaseUrl: pluginConfig.signalingPublicBaseUrl,
    signalingCheckBaseUrl: pluginConfig.signalingCheckBaseUrl,
    orchestratorId: pluginConfig.orchestratorId,
    dataDir,
    ethUsdRate: pluginConfig.ethUsdRate,
    rateLimitPerMinute: pluginConfig.rateLimitPerMinute,
    quoteCleanupIntervalMs: pluginConfig.quoteCleanupIntervalMs,
  });

  return { pluginConfig, resolved, logger };
}

const plugin = {
  id: "agent-negotiator",
  name: "Agent Negotiator",
  description: "Embedded MCP negotiation service for orchestrator workload quoting and booking",
  configSchema: agentNegotiatorPluginConfigSchema,
  register(api: NanoClawPluginApi) {
    let running: NegotiatorServiceHandle | null = null;

    api.registerChannel({
      plugin: mcpNegotiationChannelPlugin,
    });

    const service: NanoClawPluginService = {
      id: "agent-negotiator-mcp",
      start: async (ctx) => {
        if (running) {
          api.logger.info("[negotiator][nanoclaw] Service already running; skipping start");
          return;
        }

        const { pluginConfig, resolved, logger } = resolveServiceConfig(api, ctx);
        if (!pluginConfig.enabled) {
          api.logger.info("[negotiator][nanoclaw] Service disabled by plugin config");
          return;
        }

        running = await startNegotiatorService(resolved, {
          logger,
          runtimeSource: "claw-plugin",
        });
      },
      stop: async () => {
        if (!running) {
          return;
        }
        await running.stop();
        running = null;
      },
    };

    api.registerService(service);

    api.registerCommand({
      name: "negotiator",
      description: "Show whether the embedded agent-negotiator service is running.",
      handler: async () => {
        if (!running) {
          return { text: "Agent negotiator: stopped" };
        }
        return {
          text: `Agent negotiator: running on port ${running.port} (orchestrator ${running.config.orchestratorId})`,
        };
      },
    });
  },
};

export default plugin;
