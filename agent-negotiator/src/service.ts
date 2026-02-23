/**
 * Shared service lifecycle for agent-negotiator.
 *
 * The negotiator runtime is intended to run only via claw plugin services
 * (OpenClaw compatibility path today, NanoClaw hardening path later).
 */

import http from "node:http";
import path from "node:path";
import { mkdirSync } from "node:fs";
import type { AddressInfo } from "node:net";
import { NegotiatorStore } from "./negotiation/store.js";
import { AuditLogger } from "./negotiation/audit.js";
import { ConfigLoader } from "./negotiation/config.js";
import { Killswitch } from "./negotiation/killswitch.js";
import { SessionProvisioner } from "./negotiation/provisioner.js";
import { InternalTools } from "./negotiation/internal.js";
import { createMcpServer, createHttpServer, RateLimiter } from "./channels/mcp.js";

export interface NegotiatorServiceConfig {
  host: string;
  port: number;
  configFile: string;
  healthUrl: string;
  openclawGatewayToken?: string;
  signalingPublicBaseUrl?: string;
  signalingCheckBaseUrl?: string;
  orchestratorId: string;
  dataDir: string;
  ethUsdRate: number;
  rateLimitPerMinute: number;
  quoteCleanupIntervalMs: number;
}

export interface NegotiatorLogger {
  info: (message: string) => void;
  warn: (message: string) => void;
  error: (message: string) => void;
}

export interface NegotiatorServiceHandle {
  config: NegotiatorServiceConfig;
  port: number;
  stop: () => Promise<void>;
}

export type NegotiatorRuntimeSource = "openclaw-plugin" | "nanoclaw-plugin";

export interface StartNegotiatorServiceOptions {
  logger?: NegotiatorLogger;
  runtimeSource: NegotiatorRuntimeSource;
}

const defaultLogger: NegotiatorLogger = {
  info: (message: string) => console.log(message),
  warn: (message: string) => console.warn(message),
  error: (message: string) => console.error(message),
};

export function loadNegotiatorEnvConfig(
  overrides: Partial<NegotiatorServiceConfig> = {}
): NegotiatorServiceConfig {
  return {
    host: overrides.host ?? process.env.NEGOTIATOR_HOST ?? "0.0.0.0",
    port: overrides.port ?? parseInt(process.env.NEGOTIATOR_PORT ?? "9100", 10),
    configFile:
      overrides.configFile ?? process.env.NEGOTIATOR_CONFIG_FILE ?? "/config/negotiator.yaml",
    healthUrl:
      overrides.healthUrl ??
      process.env.ORCHESTRATOR_HEALTH_URL ??
      "http://vtuber-orchestrator-health:9090",
    openclawGatewayToken:
      overrides.openclawGatewayToken ??
      process.env.OPENCLAW_GATEWAY_TOKEN ??
      process.env.OPENCLAW_AUTH_TOKEN ??
      undefined,
    signalingPublicBaseUrl:
      overrides.signalingPublicBaseUrl ??
      process.env.NEGOTIATOR_SIGNALING_PUBLIC_BASE_URL ??
      undefined,
    signalingCheckBaseUrl:
      overrides.signalingCheckBaseUrl ??
      process.env.NEGOTIATOR_SIGNALING_CHECK_BASE_URL ??
      undefined,
    orchestratorId: overrides.orchestratorId ?? process.env.ORCHESTRATOR_ID ?? "unknown",
    dataDir: overrides.dataDir ?? process.env.NEGOTIATOR_DATA_DIR ?? "/data",
    ethUsdRate: overrides.ethUsdRate ?? parseFloat(process.env.ETH_USD_RATE ?? "2500"),
    rateLimitPerMinute:
      overrides.rateLimitPerMinute ?? parseInt(process.env.NEGOTIATOR_RATE_LIMIT ?? "30", 10),
    quoteCleanupIntervalMs:
      overrides.quoteCleanupIntervalMs ??
      parseInt(process.env.NEGOTIATOR_CLEANUP_INTERVAL_MS ?? "60000", 10),
  };
}

export async function startNegotiatorService(
  config: NegotiatorServiceConfig,
  options: StartNegotiatorServiceOptions
): Promise<NegotiatorServiceHandle> {
  if (
    options.runtimeSource !== "openclaw-plugin" &&
    options.runtimeSource !== "nanoclaw-plugin"
  ) {
    throw new Error(
      "agent-negotiator runtime is restricted to claw plugin startup (runtimeSource=openclaw-plugin|nanoclaw-plugin)"
    );
  }

  const logger = options.logger ?? defaultLogger;

  mkdirSync(config.dataDir, { recursive: true });

  logger.info(`[negotiator] Starting agent-negotiator for ${config.orchestratorId}`);
  logger.info(`[negotiator] Config: ${config.configFile}`);
  logger.info(`[negotiator] Health URL: ${config.healthUrl}`);
  if (config.signalingPublicBaseUrl) {
    logger.info(`[negotiator] Signaling public base: ${config.signalingPublicBaseUrl}`);
  }
  if (config.openclawGatewayToken) {
    logger.info("[negotiator] OpenClaw gateway token auth is enabled");
  }
  logger.info(`[negotiator] Bind: ${config.host}:${config.port}`);

  const store = new NegotiatorStore(path.join(config.dataDir, "negotiator.db"));
  const audit = new AuditLogger(config.dataDir);
  const configLoader = new ConfigLoader(config.configFile);

  configLoader.on("reload", () => {
    logger.info("[negotiator] Config reloaded");
    audit.log("config_reloaded", {});
  });

  configLoader.on("error", (err) => {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(`[negotiator] Config reload error: ${message}`);
    audit.log("error", { action: "config_reload", message });
  });

  configLoader.startWatching();

  const killswitch = new Killswitch(configLoader);
  const provisioner = new SessionProvisioner(config.healthUrl, store, audit, {
    signalingPublicBaseUrl: config.signalingPublicBaseUrl,
    signalingCheckBaseUrl: config.signalingCheckBaseUrl,
  });

  const internalTools = new InternalTools({
    healthBaseUrl: config.healthUrl,
    store,
    config: configLoader,
    provisioner,
    audit,
  });

  const rateLimiter = new RateLimiter(config.rateLimitPerMinute, 60_000);

  const cleanupInterval = setInterval(() => {
    rateLimiter.cleanup();
    store.expireStaleQuotes();
  }, config.quoteCleanupIntervalMs);

  const mcpServer = createMcpServer({
    store,
    config: configLoader,
    audit,
    killswitch,
    provisioner,
    internalTools,
    orchestratorId: config.orchestratorId,
    ethUsdRate: config.ethUsdRate,
  });

  const app = createHttpServer(mcpServer, {
    port: config.port,
    rateLimiter,
    audit,
    authToken: config.openclawGatewayToken,
  });

  const server = await new Promise<http.Server>((resolve, reject) => {
    const s = app.listen(config.port, config.host, () => resolve(s));
    s.on("error", reject);
  });

  const address = server.address();
  const resolvedPort =
    address && typeof address === "object" ? (address as AddressInfo).port : config.port;

  logger.info(`[negotiator] MCP server listening on :${resolvedPort}`);
  logger.info(`[negotiator] SSE endpoint: http://localhost:${resolvedPort}/sse`);
  logger.info(`[negotiator] Health: http://localhost:${resolvedPort}/health`);

  let stopped = false;

  return {
    config,
    port: resolvedPort,
    stop: async () => {
      if (stopped) {
        return;
      }
      stopped = true;

      clearInterval(cleanupInterval);
      provisioner.cancelAllTimers();
      configLoader.stopWatching();

      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });

      store.close();
      audit.close();
      logger.info("[negotiator] Stopped");
    },
  };
}
