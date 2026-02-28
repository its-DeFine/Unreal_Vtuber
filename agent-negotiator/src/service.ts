/**
 * Shared service lifecycle for agent-negotiator.
 *
 * The negotiator runtime is intended to run only via claw plugin services.
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
import { loadSkillPolicyFromFile } from "./access/policy.js";
import {
  type FleetOrchestratorConfig,
  loadFleetRegistryFromFile,
} from "./negotiation/fleet.js";

export interface NegotiatorServiceConfig {
  host: string;
  port: number;
  configFile: string;
  skillPolicyFile?: string;
  healthUrl: string;
  apiToken?: string;
  signalingPublicBaseUrl?: string;
  signalingCheckBaseUrl?: string;
  orchestratorId: string;
  dataDir: string;
  ethUsdRate: number;
  rateLimitPerMinute: number;
  quoteCleanupIntervalMs: number;
  fleetRegistryFile?: string;
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

export type NegotiatorRuntimeSource = "claw-plugin";

export interface StartNegotiatorServiceOptions {
  logger?: NegotiatorLogger;
  runtimeSource: NegotiatorRuntimeSource;
}

const defaultLogger: NegotiatorLogger = {
  info: (message: string) => console.log(message),
  warn: (message: string) => console.warn(message),
  error: (message: string) => console.error(message),
};

const DEFAULT_NEGOTIATOR_PORT = 9100;
const DEFAULT_ETH_USD_RATE = 2500;
const DEFAULT_RATE_LIMIT_PER_MINUTE = 30;
const DEFAULT_CLEANUP_INTERVAL_MS = 60_000;

function parseIntegerEnv(
  value: string | undefined,
  fallback: number,
  minValue: number
): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < minValue) {
    return fallback;
  }

  return parsed;
}

function parseFloatEnv(
  value: string | undefined,
  fallback: number,
  minValue: number
): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed) || parsed < minValue) {
    return fallback;
  }

  return parsed;
}

function parseOptionalTokenEnv(value: string | undefined): string | undefined {
  if (value === undefined) {
    return undefined;
  }

  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
}

export function loadNegotiatorEnvConfig(
  overrides: Partial<NegotiatorServiceConfig> = {}
): NegotiatorServiceConfig {
  return {
    host: overrides.host ?? process.env.NEGOTIATOR_HOST ?? "0.0.0.0",
    port:
      overrides.port ??
      parseIntegerEnv(process.env.NEGOTIATOR_PORT, DEFAULT_NEGOTIATOR_PORT, 1),
    configFile:
      overrides.configFile ?? process.env.NEGOTIATOR_CONFIG_FILE ?? "/config/negotiator.yaml",
    skillPolicyFile:
      overrides.skillPolicyFile ??
      parseOptionalTokenEnv(process.env.NEGOTIATOR_SKILL_POLICY_FILE),
    healthUrl:
      overrides.healthUrl ??
      process.env.ORCHESTRATOR_HEALTH_URL ??
      "http://vtuber-orchestrator-health:9090",
    apiToken:
      overrides.apiToken ??
      parseOptionalTokenEnv(process.env.NEGOTIATOR_API_TOKEN) ??
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
    ethUsdRate:
      overrides.ethUsdRate ??
      parseFloatEnv(process.env.ETH_USD_RATE, DEFAULT_ETH_USD_RATE, 0.000001),
    rateLimitPerMinute:
      overrides.rateLimitPerMinute ??
      parseIntegerEnv(
        process.env.NEGOTIATOR_RATE_LIMIT,
        DEFAULT_RATE_LIMIT_PER_MINUTE,
        1
      ),
    quoteCleanupIntervalMs:
      overrides.quoteCleanupIntervalMs ??
      parseIntegerEnv(
        process.env.NEGOTIATOR_CLEANUP_INTERVAL_MS,
        DEFAULT_CLEANUP_INTERVAL_MS,
        1
      ),
    fleetRegistryFile:
      overrides.fleetRegistryFile ??
      parseOptionalTokenEnv(process.env.NEGOTIATOR_FLEET_REGISTRY_FILE),
  };
}

export async function startNegotiatorService(
  config: NegotiatorServiceConfig,
  options: StartNegotiatorServiceOptions
): Promise<NegotiatorServiceHandle> {
  if (options.runtimeSource !== "claw-plugin") {
    throw new Error(
      "agent-negotiator runtime is restricted to claw plugin startup (runtimeSource=claw-plugin)"
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
  if (config.apiToken) {
    logger.info("[negotiator] API token auth is enabled");
  }
  const accessPolicy = loadSkillPolicyFromFile(config.skillPolicyFile);
  if (accessPolicy.configured && accessPolicy.sourcePath) {
    if (accessPolicy.parseError) {
      logger.warn(
        `[negotiator] Skill policy load error (${accessPolicy.sourcePath}): ${accessPolicy.parseError}`
      );
    } else {
      logger.info(`[negotiator] Skill policy loaded: ${accessPolicy.sourcePath}`);
    }
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
  const fleetFromFile = loadFleetRegistryFromFile(config.fleetRegistryFile);
  const orchestrators = new Map<string, FleetOrchestratorConfig>();
  const upsertOrchestrator = (entry: FleetOrchestratorConfig) => {
    if (!entry.id || !entry.health_url) return;
    orchestrators.set(entry.id, entry);
  };
  upsertOrchestrator({
    id: config.orchestratorId,
    health_url: config.healthUrl,
    signaling_public_base_url: config.signalingPublicBaseUrl,
    signaling_check_base_url: config.signalingCheckBaseUrl,
    enabled: true,
  });
  for (const entry of fleetFromFile) {
    upsertOrchestrator(entry);
  }
  logger.info(
    `[negotiator] Fleet orchestrators configured: ${Array.from(orchestrators.keys()).join(", ")}`
  );

  const provisioners = new Map<string, SessionProvisioner>();
  for (const [orchestratorId, entry] of orchestrators.entries()) {
    provisioners.set(
      orchestratorId,
      new SessionProvisioner(entry.health_url, store, audit, {
        signalingPublicBaseUrl: entry.signaling_public_base_url,
        signalingCheckBaseUrl: entry.signaling_check_base_url,
      })
    );
  }
  const provisioner = provisioners.get(config.orchestratorId)!;

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
    accessPolicy,
    fleetOrchestrators: Array.from(orchestrators.values()),
    fleetProvisioners: provisioners,
    defaultHealthUrl: config.healthUrl,
  });

  const app = createHttpServer(mcpServer, {
    port: config.port,
    rateLimiter,
    audit,
    authToken: config.apiToken,
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
      for (const p of provisioners.values()) {
        p.cancelAllTimers();
      }
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
