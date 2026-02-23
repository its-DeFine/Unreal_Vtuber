/**
 * NanoClaw plugin config parser + schema hints for agent-negotiator.
 */

const DEFAULT_PORT = 9100;

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asString(
  value: unknown,
  fallback: string,
  options: { trim?: boolean } = { trim: true }
): string {
  if (typeof value !== "string") {
    return fallback;
  }

  const out = options.trim ? value.trim() : value;
  return out.length > 0 ? out : fallback;
}

function asNumber(
  value: unknown,
  fallback: number,
  min: number,
  max: number
): number {
  const parsed =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number(value)
        : Number.NaN;

  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.min(max, Math.max(min, parsed));
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export interface AgentNegotiatorPluginConfig {
  enabled: boolean;
  host: string;
  port: number;
  configFile?: string;
  healthUrl?: string;
  signalingPublicBaseUrl?: string;
  signalingCheckBaseUrl?: string;
  orchestratorId?: string;
  dataDir?: string;
  ethUsdRate?: number;
  rateLimitPerMinute?: number;
  quoteCleanupIntervalMs?: number;
}

export function parseAgentNegotiatorPluginConfig(
  value: unknown
): AgentNegotiatorPluginConfig {
  const raw = asRecord(value);

  const configFile =
    typeof raw.configFile === "string" && raw.configFile.trim().length > 0
      ? raw.configFile.trim()
      : undefined;

  const healthUrl =
    typeof raw.healthUrl === "string" && raw.healthUrl.trim().length > 0
      ? raw.healthUrl.trim()
      : undefined;

  const signalingPublicBaseUrl =
    typeof raw.signalingPublicBaseUrl === "string" &&
    raw.signalingPublicBaseUrl.trim().length > 0
      ? raw.signalingPublicBaseUrl.trim()
      : undefined;

  const signalingCheckBaseUrl =
    typeof raw.signalingCheckBaseUrl === "string" &&
    raw.signalingCheckBaseUrl.trim().length > 0
      ? raw.signalingCheckBaseUrl.trim()
      : undefined;

  const orchestratorId =
    typeof raw.orchestratorId === "string" && raw.orchestratorId.trim().length > 0
      ? raw.orchestratorId.trim()
      : undefined;

  const dataDir =
    typeof raw.dataDir === "string" && raw.dataDir.trim().length > 0
      ? raw.dataDir.trim()
      : undefined;

  const ethUsdRate =
    raw.ethUsdRate === undefined
      ? undefined
      : asNumber(raw.ethUsdRate, 2500, 1, 1_000_000);

  const rateLimitPerMinute =
    raw.rateLimitPerMinute === undefined
      ? undefined
      : asNumber(raw.rateLimitPerMinute, 30, 1, 10_000);

  const quoteCleanupIntervalMs =
    raw.quoteCleanupIntervalMs === undefined
      ? undefined
      : asNumber(raw.quoteCleanupIntervalMs, 60_000, 1_000, 3_600_000);

  return {
    enabled: asBoolean(raw.enabled, true),
    host: asString(raw.host, "0.0.0.0"),
    port: asNumber(raw.port, DEFAULT_PORT, 1, 65_535),
    configFile,
    healthUrl,
    signalingPublicBaseUrl,
    signalingCheckBaseUrl,
    orchestratorId,
    dataDir,
    ethUsdRate,
    rateLimitPerMinute,
    quoteCleanupIntervalMs,
  };
}

export const agentNegotiatorPluginConfigSchema = {
  parse: parseAgentNegotiatorPluginConfig,
  uiHints: {
    enabled: {
      label: "Enabled",
      help: "Start or skip the MCP negotiation service.",
    },
    host: {
      label: "Bind Host",
      help: "Network interface for the MCP HTTP+SSE endpoint.",
      advanced: true,
      placeholder: "0.0.0.0",
    },
    port: {
      label: "MCP Port",
      help: "Port exposed for customer-facing MCP calls.",
      placeholder: "9100",
    },
    configFile: {
      label: "Config File",
      help: "Path to negotiator YAML config. If omitted, plugin writes a default under stateDir.",
      advanced: true,
    },
    healthUrl: {
      label: "Orchestrator Health URL",
      help: "Base URL for /meta/gpu-stats and /cluster deploy/down endpoints.",
      placeholder: "http://vtuber-orchestrator-health:9090",
    },
    signalingPublicBaseUrl: {
      label: "Signaling Public Base URL",
      help: "Routable base URL handed to customers in signaling_url responses.",
      placeholder: "https://orchestrator.example.com",
    },
    signalingCheckBaseUrl: {
      label: "Signaling Check Base URL",
      help: "Base URL used internally to poll signaling health after deploy.",
      advanced: true,
      placeholder: "http://127.0.0.1",
    },
    orchestratorId: {
      label: "Orchestrator ID",
      help: "Identifier returned by orchestrator_info tool.",
    },
    dataDir: {
      label: "Data Directory",
      help: "Path for SQLite and JSONL audit data.",
      advanced: true,
    },
    ethUsdRate: {
      label: "ETH/USD Rate",
      help: "Fallback conversion rate when quoting wei.",
      advanced: true,
    },
    rateLimitPerMinute: {
      label: "Rate Limit / Minute",
      help: "Max requests per IP each minute.",
      advanced: true,
    },
    quoteCleanupIntervalMs: {
      label: "Quote Cleanup Interval (ms)",
      help: "How often stale quotes/rate-limit entries are cleaned.",
      advanced: true,
    },
  },
  jsonSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      enabled: { type: "boolean" },
      host: { type: "string" },
      port: { type: "number", minimum: 1, maximum: 65535 },
      configFile: { type: "string" },
      healthUrl: { type: "string" },
      signalingPublicBaseUrl: { type: "string" },
      signalingCheckBaseUrl: { type: "string" },
      orchestratorId: { type: "string" },
      dataDir: { type: "string" },
      ethUsdRate: { type: "number", minimum: 1 },
      rateLimitPerMinute: { type: "number", minimum: 1 },
      quoteCleanupIntervalMs: { type: "number", minimum: 1000 },
    },
  },
};
