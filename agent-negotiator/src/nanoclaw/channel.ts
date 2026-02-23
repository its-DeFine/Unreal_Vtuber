import type { ChannelPlugin } from "nanoclaw/plugin-sdk";

export const MCP_NEGOTIATION_CHANNEL_ID = "mcp-negotiation";
const DEFAULT_ACCOUNT_ID = "default";

interface ResolvedMcpNegotiationAccount {
  accountId: string;
  enabled: boolean;
  configured: boolean;
  host: string;
  port: number;
  publicUrl?: string;
}

function asChannelNode(cfg: unknown): Record<string, unknown> {
  if (!cfg || typeof cfg !== "object" || Array.isArray(cfg)) {
    return {};
  }

  const channels = (cfg as Record<string, unknown>).channels;
  if (!channels || typeof channels !== "object" || Array.isArray(channels)) {
    return {};
  }

  const node = (channels as Record<string, unknown>)[MCP_NEGOTIATION_CHANNEL_ID];
  if (!node || typeof node !== "object" || Array.isArray(node)) {
    return {};
  }

  return node as Record<string, unknown>;
}

function resolveAccount(cfg: unknown): ResolvedMcpNegotiationAccount {
  const node = asChannelNode(cfg);
  const host =
    typeof node.host === "string" && node.host.trim().length > 0
      ? node.host.trim()
      : "localhost";
  const portRaw = node.port;
  const port =
    typeof portRaw === "number"
      ? portRaw
      : typeof portRaw === "string"
        ? Number(portRaw)
        : 9100;

  return {
    accountId: DEFAULT_ACCOUNT_ID,
    enabled: typeof node.enabled === "boolean" ? node.enabled : true,
    configured: Number.isFinite(port) && port > 0,
    host,
    port: Number.isFinite(port) && port > 0 ? port : 9100,
    publicUrl:
      typeof node.publicUrl === "string" && node.publicUrl.trim().length > 0
        ? node.publicUrl.trim()
        : undefined,
  };
}

export const mcpNegotiationChannelPlugin: ChannelPlugin<ResolvedMcpNegotiationAccount> = {
  id: MCP_NEGOTIATION_CHANNEL_ID,
  meta: {
    id: MCP_NEGOTIATION_CHANNEL_ID,
    label: "MCP Negotiation",
    selectionLabel: "MCP Negotiation",
    docsPath: "/docs/agent-negotiator.md",
    blurb: "Customer-facing MCP quote + booking channel for orchestrator workloads.",
    order: 950,
    aliases: ["negotiator", "mcp-negotiator"],
    detailLabel: "Customer MCP API",
  },
  capabilities: {
    chatTypes: ["direct"],
    nativeCommands: false,
    media: false,
    blockStreaming: false,
    reactions: false,
    edit: false,
    unsend: false,
    reply: false,
  },
  reload: {
    configPrefixes: [
      `channels.${MCP_NEGOTIATION_CHANNEL_ID}`,
      "plugins.entries.agent-negotiator",
    ],
  },
  config: {
    listAccountIds: () => [DEFAULT_ACCOUNT_ID],
    resolveAccount: (cfg) => resolveAccount(cfg),
    defaultAccountId: () => DEFAULT_ACCOUNT_ID,
    isEnabled: (account) => account.enabled,
    isConfigured: (account) => account.configured,
    describeAccount: (account) => ({
      accountId: account.accountId,
      enabled: account.enabled,
      configured: account.configured,
      baseUrl: account.publicUrl ?? `http://${account.host}:${account.port}`,
    }),
  },
  status: {
    buildChannelSummary: ({ snapshot }) => ({
      baseUrl: snapshot.baseUrl ?? null,
      configured: snapshot.configured ?? false,
      enabled: snapshot.enabled ?? false,
    }),
  },
};
