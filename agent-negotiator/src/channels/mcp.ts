/**
 * MCP Server channel — HTTP+SSE transport on configurable port.
 *
 * This is the customer-facing entry point. It:
 *   1. Receives MCP tool calls over HTTP+SSE
 *   2. Validates input (JSON schema via zod)
 *   3. Checks rate limits (per-IP, 30 req/min default)
 *   4. Checks killswitch before booking operations
 *   5. Delegates to tool handlers
 *   6. Returns MCP-formatted responses
 *
 * Uses @modelcontextprotocol/sdk for protocol compliance.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express from "express";
import { timingSafeEqual } from "node:crypto";
import type { Request, Response } from "express";
import { z } from "zod";

import type { NegotiatorStore } from "../negotiation/store.js";
import type { ConfigLoader } from "../negotiation/config.js";
import type { AuditLogger } from "../negotiation/audit.js";
import type { Killswitch } from "../negotiation/killswitch.js";
import { clusterPorts, type SessionProvisioner } from "../negotiation/provisioner.js";
import type { GpuStats, InternalTools } from "../negotiation/internal.js";
import { calculatePrice, type PricingResult } from "../negotiation/pricing.js";
import type { AccessRequest, LoadedSkillPolicy } from "../access/policy.js";
import { enforceAccessPolicy } from "../access/policy.js";
import type { FleetOrchestratorConfig } from "../negotiation/fleet.js";

// --- Rate Limiter ---

interface RateLimitEntry {
  count: number;
  windowStart: number;
}

export class RateLimiter {
  private limits = new Map<string, RateLimitEntry>();
  private maxPerWindow: number;
  private windowMs: number;

  constructor(maxPerWindow = 30, windowMs = 60_000) {
    const safeMaxPerWindow = Number.isFinite(maxPerWindow) && maxPerWindow >= 1 ? maxPerWindow : 30;
    const safeWindowMs = Number.isFinite(windowMs) && windowMs >= 1 ? windowMs : 60_000;

    this.maxPerWindow = Math.floor(safeMaxPerWindow);
    this.windowMs = Math.floor(safeWindowMs);
  }

  check(ip: string): boolean {
    const now = Date.now();
    const entry = this.limits.get(ip);

    if (!entry || now - entry.windowStart > this.windowMs) {
      this.limits.set(ip, { count: 1, windowStart: now });
      return true;
    }

    if (entry.count >= this.maxPerWindow) {
      return false;
    }

    entry.count++;
    return true;
  }

  // Periodic cleanup to prevent memory leak
  cleanup(): void {
    const now = Date.now();
    for (const [ip, entry] of this.limits) {
      if (now - entry.windowStart > this.windowMs * 2) {
        this.limits.delete(ip);
      }
    }
  }
}

// --- MCP Channel ---

export interface McpChannelDeps {
  store: NegotiatorStore;
  config: ConfigLoader;
  audit: AuditLogger;
  killswitch: Killswitch;
  provisioner: SessionProvisioner;
  internalTools: InternalTools;
  orchestratorId: string;
  ethUsdRate?: number; // defaults to 2500 if not provided
  accessPolicy?: LoadedSkillPolicy;
  fleetOrchestrators?: FleetOrchestratorConfig[];
  fleetProvisioners?: Map<string, SessionProvisioner>;
  defaultHealthUrl?: string;
}

interface ConnectionTargetInput {
  direct_webrtc_base_url?: string;
  direct_webrtc_ip?: string;
  scheme?: "http" | "https";
}

interface ConnectionRouteResolution {
  baseUrl?: string;
  source?: "base_url" | "ip";
  error?: {
    code: string;
    message: string;
  };
}

const ConnectionTargetSchema = z.object({
  direct_webrtc_base_url: z
    .string()
    .min(1)
    .optional()
    .describe("Direct WebRTC route base URL (e.g. https://203.0.113.10 or https://stream.example.com)"),
  direct_webrtc_ip: z
    .string()
    .min(1)
    .optional()
    .describe("Direct WebRTC IP or hostname shortcut (without port)"),
  scheme: z
    .enum(["http", "https"])
    .optional()
    .describe("Scheme to use with direct_webrtc_ip when protocol is omitted"),
});

function withPort(baseUrl: string, port: number): string | null {
  try {
    const u = new URL(baseUrl);
    u.port = String(port);
    u.pathname = "/";
    u.search = "";
    u.hash = "";
    return u.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeRouteBaseUrl(
  candidate: string,
  source: "base_url" | "ip"
): ConnectionRouteResolution {
  try {
    const parsed = new URL(candidate);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return {
        error: {
          code: "invalid_connection_route_protocol",
          message: "connection route must use http or https",
        },
      };
    }
    if (!parsed.hostname) {
      return {
        error: {
          code: "invalid_connection_route_host",
          message: "connection route must include a host",
        },
      };
    }
    parsed.pathname = "/";
    parsed.search = "";
    parsed.hash = "";
    return {
      baseUrl: parsed.toString().replace(/\/$/, ""),
      source,
    };
  } catch {
    return {
      error: {
        code: "invalid_connection_route",
        message: "failed to parse connection route target",
      },
    };
  }
}

function resolveConnectionRouteBase(
  connection?: ConnectionTargetInput
): ConnectionRouteResolution {
  if (!connection) {
    return {};
  }

  const fromBase = connection.direct_webrtc_base_url?.trim() ?? "";
  const fromIp = connection.direct_webrtc_ip?.trim() ?? "";

  if (fromBase.length > 0 && fromIp.length > 0) {
    return {
      error: {
        code: "connection_route_ambiguous",
        message: "provide either direct_webrtc_base_url or direct_webrtc_ip, not both",
      },
    };
  }

  if (fromBase.length > 0) {
    return normalizeRouteBaseUrl(fromBase, "base_url");
  }

  if (fromIp.length > 0) {
    const scheme = connection.scheme === "https" ? "https" : "http";
    const candidate = fromIp.includes("://") ? fromIp : `${scheme}://${fromIp}`;
    return normalizeRouteBaseUrl(candidate, "ip");
  }

  return {
    error: {
      code: "connection_route_missing",
      message: "connection target is missing direct_webrtc_base_url/direct_webrtc_ip",
    },
  };
}

function buildControlFromSignaling(
  signalingUrl: string,
  slot: number,
  avatarId?: string | null
): Record<string, unknown> | null {
  const ports = clusterPorts(slot);
  const runnerUrl = withPort(signalingUrl, ports.runner);
  if (!runnerUrl) {
    return null;
  }

  return {
    avatar_id: avatarId ?? null,
    runner_url: runnerUrl,
    runner_execute_url: `${runnerUrl}/scripts/execute`,
    runner_status_url_template: `${runnerUrl}/scripts/{session_id}`,
    game_tcp_port: ports.game_tcp,
  };
}

interface FleetCapacityInfo {
  orchestrator_id: string;
  health_url: string;
  available: boolean;
  active_sessions: number;
  max_sessions: number;
  available_slots: number;
  gpu_utilization_pct: number;
  capacity_threshold_pct: number;
  next_slot: number | null;
  telemetry_ok: boolean;
}

interface ResolveOrchestratorResult {
  id: string;
  healthUrl: string;
  provisioner: SessionProvisioner;
}

async function fetchGpuStatsFromHealth(healthBaseUrl: string): Promise<GpuStats[]> {
  const base = healthBaseUrl.replace(/\/+$/, "");
  const paths = ["/meta/gpu/stats", "/meta/gpu-stats"];
  let lastError: Error | null = null;

  for (const p of paths) {
    try {
      const res = await fetch(`${base}${p}`);
      if (res.ok) {
        const data = (await res.json()) as { gpus?: GpuStats[] };
        return data.gpus ?? [];
      }
      if (res.status === 404) {
        continue;
      }
      lastError = new Error(`GPU stats request failed (${p}): ${res.status}`);
      break;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      lastError = new Error(`GPU stats request failed (${p}): ${message}`);
    }
  }

  throw lastError ?? new Error("GPU stats request failed");
}

export function createMcpServer(deps: McpChannelDeps): McpServer {
  const {
    store,
    config,
    audit,
    killswitch,
    internalTools,
    orchestratorId,
    accessPolicy,
  } = deps;
  const fleetOrchestratorsInput = deps.fleetOrchestrators ?? [];
  const fleetProvisionersInput = deps.fleetProvisioners ?? new Map<string, SessionProvisioner>();

  const ethUsdRate = deps.ethUsdRate ?? 2500;
  const provisionersByOrchestrator = new Map<string, SessionProvisioner>();
  provisionersByOrchestrator.set(orchestratorId, deps.provisioner);
  for (const [id, p] of fleetProvisionersInput.entries()) {
    provisionersByOrchestrator.set(id, p);
  }

  const orchestratorById = new Map<string, FleetOrchestratorConfig>();
  for (const item of fleetOrchestratorsInput) {
    if (item?.id && item?.health_url) {
      orchestratorById.set(item.id, item);
    }
  }
  if (!orchestratorById.has(orchestratorId)) {
    orchestratorById.set(orchestratorId, {
      id: orchestratorId,
      health_url: deps.defaultHealthUrl ?? "",
      enabled: true,
    });
  }

  const localOrchestratorIds = new Set(
    [orchestratorId, ...Array.from(orchestratorById.keys())].filter((v) => v.length > 0)
  );

  const resolveTargetOrchestrator = (
    requestedOrchestratorId: string | undefined
  ): ResolveOrchestratorResult | null => {
    const id = (requestedOrchestratorId ?? orchestratorId).trim();
    const record = orchestratorById.get(id);
    const provisioner = provisionersByOrchestrator.get(id);
    if (!record || !provisioner) {
      return null;
    }
    return { id, healthUrl: record.health_url, provisioner };
  };

  const checkCapacityForOrchestrator = async (
    requestedOrchestratorId: string | undefined
  ): Promise<FleetCapacityInfo | null> => {
    const target = resolveTargetOrchestrator(requestedOrchestratorId);
    if (!target) return null;

    const cfg = config.get();
    const orchestratorCfg = orchestratorById.get(target.id);
    const maxSessions =
      orchestratorCfg?.max_concurrent_sessions ?? cfg.capacity.max_concurrent_sessions;
    const thresholdPct =
      orchestratorCfg?.capacity_threshold_pct ?? cfg.capacity.capacity_threshold_pct;

    const activeCount = store.getActiveBookingCount(target.id);
    let gpuPct = 0;
    let telemetryOk = true;
    if (target.healthUrl.length === 0 && target.id === orchestratorId) {
      const fallback = await internalTools.checkCapacity();
      gpuPct = fallback.gpu_utilization_pct;
    } else {
      try {
        const stats = await fetchGpuStatsFromHealth(target.healthUrl);
        if (stats.length > 0) {
          gpuPct =
            stats.reduce((sum, g) => sum + g.utilization_gpu_pct, 0) /
            stats.length;
        }
      } catch {
        telemetryOk = false;
        gpuPct = 100;
      }
    }

    const available =
      telemetryOk &&
      activeCount < maxSessions &&
      gpuPct < thresholdPct;

    const nextSlot = store.getNextAvailableSlot(maxSessions, target.id);
    return {
      orchestrator_id: target.id,
      health_url: target.healthUrl,
      available,
      active_sessions: activeCount,
      max_sessions: maxSessions,
      available_slots: Math.max(0, maxSessions - activeCount),
      gpu_utilization_pct: Math.round(gpuPct * 100) / 100,
      capacity_threshold_pct: thresholdPct,
      next_slot: nextSlot,
      telemetry_ok: telemetryOk,
    };
  };

  const server = new McpServer({
    name: `embody-negotiator-${orchestratorId}`,
    version: "0.1.0",
  });

  // --- orchestrator_info ---
  server.tool(
    "orchestrator_info",
    "Get orchestrator capabilities, GPU type, available session slots, and pricing range",
    {},
    async () => {
      const cfg = config.get();
      let gpuInfo: string = "unknown";
      let capacity = await checkCapacityForOrchestrator(orchestratorId);
      try {
        const target = resolveTargetOrchestrator(orchestratorId);
        const stats = target
          ? await fetchGpuStatsFromHealth(target.healthUrl)
          : await internalTools.gpuStats();
        if (stats.length > 0) {
          gpuInfo = `${stats.length}x GPU, ${stats[0].memory_total_mib}MiB VRAM each`;
        }
      } catch {
        gpuInfo = "GPU stats unavailable";
      }

      if (!capacity) {
        const fallback = await internalTools.checkCapacity();
        capacity = {
          orchestrator_id: orchestratorId,
          health_url: "unknown",
          available: fallback.available,
          active_sessions: fallback.active_sessions,
          max_sessions: fallback.max_sessions,
          available_slots: fallback.available_slots,
          gpu_utilization_pct: fallback.gpu_utilization_pct,
          capacity_threshold_pct: fallback.capacity_threshold_pct,
          next_slot: fallback.next_slot,
          telemetry_ok: true,
        };
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                orchestrator_id: orchestratorId,
                gpu: gpuInfo,
                session_types: cfg.session_types,
                pricing_range: {
                  min_usd_per_hour: cfg.pricing.min_price_usd_per_hour,
                  max_usd_per_hour: cfg.pricing.max_price_usd_per_hour,
                  base_usd_per_hour: cfg.pricing.base_price_usd_per_hour,
                  surge_above_gpu_pct: cfg.pricing.surge_threshold_pct,
                },
                capacity: {
                  available_slots: capacity.available_slots,
                  max_concurrent: capacity.max_sessions,
                  gpu_utilization_pct: capacity.gpu_utilization_pct,
                },
                killswitch_active: killswitch.isActive(),
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- fleet_overview ---
  server.tool(
    "fleet_overview",
    "List available orchestrators with capacity snapshots for allocator decisions.",
    {},
    async () => {
      const rows: Array<Record<string, unknown>> = [];
      for (const orchestratorIdItem of localOrchestratorIds) {
        const cap = await checkCapacityForOrchestrator(orchestratorIdItem);
        if (!cap) {
          rows.push({
            orchestrator_id: orchestratorIdItem,
            available: false,
            error: "orchestrator_not_configured",
          });
          continue;
        }
        rows.push({
          orchestrator_id: cap.orchestrator_id,
          health_url: cap.health_url,
          available: cap.available,
          active_sessions: cap.active_sessions,
          max_sessions: cap.max_sessions,
          available_slots: cap.available_slots,
          gpu_utilization_pct: cap.gpu_utilization_pct,
          capacity_threshold_pct: cap.capacity_threshold_pct,
          telemetry_ok: cap.telemetry_ok,
        });
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                orchestrators: rows,
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- negotiate_quote ---
  server.tool(
    "negotiate_quote",
    "Request a price quote for a session. Returns quote_id, price, and validity window.",
    {
      session_type: z
        .string()
        .describe("Type of session (e.g. avatar_stream, avatar_interactive)"),
      duration_min: z
        .number()
        .int()
        .min(1)
        .max(1440)
        .describe("Desired session duration in minutes"),
      resolution: z
        .string()
        .describe("Video resolution (e.g. 720p, 1080p)"),
      message: z
        .string()
        .max(500)
        .optional()
        .describe("Optional message or requirements"),
      preferred_orchestrator_id: z
        .string()
        .min(1)
        .optional()
        .describe("Optional orchestrator preference. If omitted, allocator picks best available."),
    },
    async (params) => {
      // MCP SDK already validates via inline zod schemas; use params directly
      const input = params as {
        session_type: string;
        duration_min: number;
        resolution: string;
        message?: string;
        preferred_orchestrator_id?: string;
      };
      const cfg = config.get();

      // Validate session type
      const sessionType = cfg.session_types.find(
        (st) => st.id === input.session_type
      );
      if (!sessionType) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unknown_session_type",
                message: `Unknown session type: ${input.session_type}. Available: ${cfg.session_types.map((s) => s.id).join(", ")}`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Validate duration
      if (
        input.duration_min < sessionType.min_duration_minutes ||
        input.duration_min > sessionType.max_duration_minutes
      ) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "invalid_duration",
                message: `Duration must be ${sessionType.min_duration_minutes}-${sessionType.max_duration_minutes} minutes for ${input.session_type}`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Validate resolution
      if (!sessionType.supported_resolutions.includes(input.resolution)) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unsupported_resolution",
                message: `Resolution ${input.resolution} not supported. Available: ${sessionType.supported_resolutions.join(", ")}`,
              }),
            },
          ],
          isError: true,
        };
      }

      const requested = input.preferred_orchestrator_id?.trim();
      if (requested && !localOrchestratorIds.has(requested)) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unknown_orchestrator",
                message: `Unknown orchestrator: ${requested}`,
              }),
            },
          ],
          isError: true,
        };
      }

      const candidateIds = requested
        ? [requested]
        : Array.from(localOrchestratorIds);

      const evaluated: Array<{
        capacity: FleetCapacityInfo;
        pricing: PricingResult;
      }> = [];
      for (const id of candidateIds) {
        const capacity = await checkCapacityForOrchestrator(id);
        if (!capacity) {
          continue;
        }
        const pricing: PricingResult = calculatePrice(
          {
            gpuUtilizationPct: capacity.gpu_utilization_pct,
            durationMin: input.duration_min,
            resolution: input.resolution,
          },
          cfg.pricing,
          ethUsdRate
        );
        evaluated.push({ capacity, pricing });
      }

      const available = evaluated.filter((item) => item.capacity.available);
      if (available.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "no_capacity",
                message: "No orchestrator has available capacity right now.",
                candidates: evaluated.map((item) => ({
                  orchestrator_id: item.capacity.orchestrator_id,
                  available: item.capacity.available,
                  available_slots: item.capacity.available_slots,
                  max_sessions: item.capacity.max_sessions,
                  active_sessions: item.capacity.active_sessions,
                  gpu_utilization_pct: item.capacity.gpu_utilization_pct,
                  telemetry_ok: item.capacity.telemetry_ok,
                })),
              }),
            },
          ],
          isError: true,
        };
      }

      available.sort((a, b) => {
        const priceDiff = a.pricing.price_usd_total - b.pricing.price_usd_total;
        if (priceDiff !== 0) return priceDiff;
        if (a.capacity.available_slots !== b.capacity.available_slots) {
          return b.capacity.available_slots - a.capacity.available_slots;
        }
        return a.capacity.gpu_utilization_pct - b.capacity.gpu_utilization_pct;
      });

      const selected = available[0];

      // Quote valid for 5 minutes
      const validUntil = new Date(Date.now() + 5 * 60_000).toISOString();

      const quote = store.createQuote({
        session_type: input.session_type,
        duration_min: input.duration_min,
        resolution: input.resolution,
        price_wei: selected.pricing.price_wei,
        price_usd_est: selected.pricing.price_usd_total,
        valid_until: validUntil,
        customer_message: input.message,
        gpu_utilization_pct: selected.capacity.gpu_utilization_pct,
        orchestrator_id: selected.capacity.orchestrator_id,
      });

      audit.log("quote_created", {
        quote_id: quote.quote_id,
        orchestrator_id: selected.capacity.orchestrator_id,
        session_type: input.session_type,
        duration_min: input.duration_min,
        resolution: input.resolution,
        price_usd: selected.pricing.price_usd_total,
        price_per_hour: selected.pricing.price_usd_per_hour,
        surge: selected.pricing.surge_active,
      });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                quote_id: quote.quote_id,
                orchestrator_id: selected.capacity.orchestrator_id,
                price_wei: quote.price_wei,
                price_usd_est: selected.pricing.price_usd_total,
                price_usd_per_hour: selected.pricing.price_usd_per_hour,
                surge_active: selected.pricing.surge_active,
                valid_until: quote.valid_until,
                available: selected.capacity.available,
                available_slots: selected.capacity.available_slots,
                allocator: {
                  strategy: "lowest_price_then_capacity",
                  considered_orchestrators: candidateIds,
                },
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- accept_quote ---
  server.tool(
    "accept_quote",
    "Accept a quote and book a session. Returns booking_id, session details, and signaling URL.",
    {
      quote_id: z.string().min(1).describe("The quote ID to accept"),
      customer_id: z
        .string()
        .min(1)
        .max(128)
        .describe("Your unique customer identifier"),
      start_time: z
        .string()
        .optional()
        .describe("Desired start time (ISO 8601). If omitted, starts immediately."),
      access: z
        .object({
          rail: z.enum(["paid", "zero_price"]),
          paid: z
            .object({
              http_status: z.number().int().describe("Expected paid rail status code (402)"),
              standard: z.string().min(1).describe("Payment rail standard (ERC-4337)"),
              user_operation_hash: z
                .string()
                .min(1)
                .describe("ERC-4337 userOperation hash"),
            })
            .optional(),
          zero_price: z
            .object({
              nonce: z.string().min(1).max(256).describe("Signed-message nonce"),
              timestamp: z
                .string()
                .min(1)
                .describe("Signed-message timestamp (ISO-8601)"),
              signature: z
                .string()
                .min(1)
                .describe("Signed-message signature"),
            })
            .optional(),
        })
        .optional()
        .describe("Policy-driven access rail proof"),
      connection: ConnectionTargetSchema.optional().describe(
        "Optional direct WebRTC route preference for this booking"
      ),
    },
    async (params) => {
      const input = params as {
        quote_id: string;
        customer_id: string;
        start_time?: string;
        access?: AccessRequest;
        connection?: ConnectionTargetInput;
      };

      // Killswitch check
      if (killswitch.isActive()) {
        audit.log("killswitch_activated", { action: "accept_quote" });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "service_unavailable",
                message:
                  "The negotiator is temporarily not accepting new bookings. Please try again later.",
              }),
            },
          ],
          isError: true,
        };
      }

      // Delayed scheduling is not implemented in v1.
      // Reject future start times instead of silently provisioning immediately.
      if (input.start_time) {
        const requestedStart = new Date(input.start_time);
        if (Number.isNaN(requestedStart.getTime())) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify({
                  error: "invalid_start_time",
                  message: "start_time must be a valid ISO-8601 timestamp",
                }),
              },
            ],
            isError: true,
          };
        }

        if (requestedStart.getTime() > Date.now() + 30_000) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify({
                  error: "scheduled_start_not_supported",
                  message:
                    "Future start_time scheduling is not supported yet. Omit start_time to start now.",
                }),
              },
            ],
            isError: true,
          };
        }
      }

      const accessDecision = enforceAccessPolicy(accessPolicy, {
        customerId: input.customer_id,
        quoteId: input.quote_id,
        access: input.access,
      });
      if (!accessDecision.allowed) {
        audit.log("error", {
          action: "access_gate",
          customer_id: input.customer_id,
          quote_id: input.quote_id,
          code: accessDecision.code,
        });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: accessDecision.code ?? "access_denied",
                message:
                  accessDecision.message ??
                  "Access denied by negotiated customer entitlement policy",
              }),
            },
          ],
          isError: true,
        };
      }

      const routeResolution = resolveConnectionRouteBase(input.connection);
      if (routeResolution.error) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: routeResolution.error.code,
                message: routeResolution.error.message,
              }),
            },
          ],
          isError: true,
        };
      }

      const quote = store.getQuote(input.quote_id);
      if (!quote) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "quote_not_found",
                message: `Quote ${input.quote_id} not found`,
              }),
            },
          ],
          isError: true,
        };
      }
      const targetOrchestratorId =
        quote.orchestrator_id?.trim() || orchestratorId;
      const target = resolveTargetOrchestrator(targetOrchestratorId);
      if (!target) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "orchestrator_not_configured",
                message: `Orchestrator ${targetOrchestratorId} is not configured`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Capacity check (target orchestrator)
      const capacity = await checkCapacityForOrchestrator(targetOrchestratorId);
      if (!capacity || !capacity.available || capacity.next_slot === null) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "no_capacity",
                message: capacity
                  ? `No available slots on ${targetOrchestratorId}. ${capacity.active_sessions}/${capacity.max_sessions} sessions active, GPU at ${capacity.gpu_utilization_pct}%.`
                  : `No available slots on ${targetOrchestratorId}.`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Create booking — atomically checks capacity + reserves slot inside SQLite transaction
      let booking;
      try {
        booking = store.createBooking({
          quote_id: input.quote_id,
          customer_id: input.customer_id,
          slot: capacity.next_slot,
          maxConcurrentSessions: capacity.max_sessions,
          orchestrator_id: targetOrchestratorId,
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "booking_failed",
                message,
              }),
            },
          ],
          isError: true,
        };
      }

      audit.log("booking_created", {
        booking_id: booking.booking_id,
        quote_id: input.quote_id,
        customer_id: input.customer_id,
        orchestrator_id: targetOrchestratorId,
        slot: capacity.next_slot,
        connection_route_base: routeResolution.baseUrl ?? null,
        connection_route_source: routeResolution.source ?? "default",
      });

      // Provision session
      try {
        const result = await target.provisioner.provision(
          booking.booking_id,
          capacity.next_slot,
          booking.duration_min,
          routeResolution.baseUrl
            ? { signalingBaseUrlOverride: routeResolution.baseUrl }
            : undefined
        );

        const control =
          buildControlFromSignaling(result.signaling_url, result.slot, result.avatar_id) ??
          {
            avatar_id: result.avatar_id,
            runner_url: result.runner_url,
            runner_execute_url: result.runner_execute_url,
            runner_status_url_template: result.runner_status_url_template,
            game_tcp_port: result.game_tcp_port,
          };

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  booking_id: booking.booking_id,
                  orchestrator_id: targetOrchestratorId,
                  status: "active",
                  session: {
                    signaling_url: result.signaling_url,
                    token: result.session_token,
                    expires_at: result.expires_at,
                    slot: result.slot,
                    control,
                    connection_route: {
                      base_url: routeResolution.baseUrl ?? null,
                      source: routeResolution.source ?? "default",
                    },
                  },
                },
                null,
                2
              ),
            },
          ],
        };
      } catch (err: unknown) {
        // Mark booking as failed so it doesn't orphan capacity
        try {
          store.updateBookingStatus(booking.booking_id, "failed");
        } catch { /* best effort */ }
        const message = err instanceof Error ? err.message : String(err);
        audit.log("booking_failed", {
          booking_id: booking.booking_id,
          orchestrator_id: targetOrchestratorId,
          error: message,
        });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "provisioning_failed",
                message: "Session provisioning failed. Please try again.",
                booking_id: booking.booking_id,
                status: "failed",
              }),
            },
          ],
          isError: true,
        };
      }
    }
  );

  // --- session_status ---
  server.tool(
    "session_status",
    "Check the status of a booked session including time remaining",
    {
      booking_id: z.string().min(1).describe("The booking ID to check"),
      customer_id: z.string().min(1).describe("Your customer identifier (must match booking)"),
    },
    async (params) => {
      const booking = store.getBooking(params.booking_id as string);

      if (!booking) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "not_found",
                message: `Booking ${params.booking_id} not found`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (booking.customer_id !== params.customer_id) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unauthorized",
                message: "Customer ID does not match booking",
              }),
            },
          ],
          isError: true,
        };
      }

      let timeRemainingMin: number | null = null;
      if (booking.status === "active" && booking.expires_at) {
        const remaining =
          new Date(booking.expires_at).getTime() - Date.now();
        timeRemainingMin = Math.max(0, Math.round(remaining / 60_000));
      }

      let control: Record<string, unknown> | null = null;
      if (booking.status === "active" && typeof booking.slot === "number" && booking.signaling_url) {
        control = buildControlFromSignaling(
          booking.signaling_url,
          booking.slot,
          booking.avatar_id ?? null
        );
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                booking_id: booking.booking_id,
                orchestrator_id: booking.orchestrator_id ?? orchestratorId,
                status: booking.status,
                session_type: booking.session_type,
                duration_min: booking.duration_min,
                resolution: booking.resolution,
                price_usd_est: booking.price_usd_est,
                ...(booking.signaling_url && {
                  signaling_url: booking.signaling_url,
                }),
                ...(booking.started_at && { started_at: booking.started_at }),
                ...(booking.expires_at && { expires_at: booking.expires_at }),
                ...(timeRemainingMin !== null && {
                  time_remaining_min: timeRemainingMin,
                }),
                ...(control && { control }),
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- update_webrtc_connection ---
  server.tool(
    "update_webrtc_connection",
    "Update direct WebRTC route (IP/base URL) for an existing booking.",
    {
      booking_id: z.string().min(1).describe("The booking ID to update"),
      customer_id: z
        .string()
        .min(1)
        .describe("Customer identifier (must match booking)"),
      connection: ConnectionTargetSchema.describe(
        "New direct WebRTC route target"
      ),
    },
    async (params) => {
      const input = params as {
        booking_id: string;
        customer_id: string;
        connection: ConnectionTargetInput;
      };

      const booking = store.getBooking(input.booking_id);
      if (!booking) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "not_found",
                message: `Booking ${input.booking_id} not found`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (booking.customer_id !== input.customer_id) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unauthorized",
                message: "Customer ID does not match booking",
              }),
            },
          ],
          isError: true,
        };
      }

      if (
        booking.status !== "confirmed" &&
        booking.status !== "provisioning" &&
        booking.status !== "active"
      ) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "connection_update_not_allowed",
                message: `Booking ${input.booking_id} is ${booking.status}; only confirmed/provisioning/active can change route`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (typeof booking.slot !== "number") {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "slot_unavailable",
                message: "Booking has no assigned slot yet",
              }),
            },
          ],
          isError: true,
        };
      }

      const routeResolution = resolveConnectionRouteBase(input.connection);
      if (routeResolution.error || !routeResolution.baseUrl) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: routeResolution.error?.code ?? "invalid_connection_route",
                message:
                  routeResolution.error?.message ??
                  "failed to resolve connection route",
              }),
            },
          ],
          isError: true,
        };
      }

      const signalingUrl = withPort(
        routeResolution.baseUrl,
        clusterPorts(booking.slot).signaling
      );
      if (!signalingUrl) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "invalid_connection_route",
                message: "unable to build signaling URL from requested route",
              }),
            },
          ],
          isError: true,
        };
      }

      store.updateBookingFields(booking.booking_id, {
        signaling_url: signalingUrl,
      });

      const updated = store.getBooking(booking.booking_id) ?? booking;
      const control = buildControlFromSignaling(
        signalingUrl,
        booking.slot,
        updated.avatar_id ?? null
      );

      audit.log("booking_connection_updated", {
        booking_id: booking.booking_id,
        customer_id: input.customer_id,
        signaling_url: signalingUrl,
        route_source: routeResolution.source ?? "unknown",
      });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                booking_id: booking.booking_id,
                orchestrator_id: booking.orchestrator_id ?? orchestratorId,
                status: updated.status,
                signaling_url: signalingUrl,
                connection_route: {
                  base_url: routeResolution.baseUrl,
                  source: routeResolution.source ?? "unknown",
                },
                control,
                message:
                  "WebRTC route updated. Reconnect the client using the new signaling_url/control URLs.",
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- validate_renter_control ---
  server.tool(
    "validate_renter_control",
    "Execute a deterministic TCP command sequence through script-runner and verify completion.",
    {
      booking_id: z.string().min(1).describe("The active booking ID"),
      customer_id: z.string().min(1).describe("Customer identifier (must match booking)"),
      commands: z
        .array(z.string().min(1))
        .min(1)
        .max(32)
        .optional()
        .describe("TCP commands to execute in-order"),
      session_id: z
        .string()
        .min(1)
        .max(128)
        .optional()
        .describe("Optional runner session ID override"),
      timeout_ms: z
        .number()
        .int()
        .min(1_000)
        .max(120_000)
        .optional()
        .describe("Total timeout before validation fails"),
      poll_interval_ms: z
        .number()
        .int()
        .min(100)
        .max(10_000)
        .optional()
        .describe("Polling interval for runner status"),
    },
    async (params) => {
      const input = params as {
        booking_id: string;
        customer_id: string;
        commands?: string[];
        session_id?: string;
        timeout_ms?: number;
        poll_interval_ms?: number;
      };

      const booking = store.getBooking(input.booking_id);
      if (!booking) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "not_found",
                message: `Booking ${input.booking_id} not found`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (booking.customer_id !== input.customer_id) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unauthorized",
                message: "Customer ID does not match booking",
              }),
            },
          ],
          isError: true,
        };
      }

      if (booking.status !== "active") {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "inactive_session",
                message: `Booking ${input.booking_id} is ${booking.status}, not active`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (typeof booking.slot !== "number" || !booking.signaling_url) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "control_unavailable",
                message: "Booking does not expose active control metadata",
              }),
            },
          ],
          isError: true,
        };
      }

      const ports = clusterPorts(booking.slot);
      const runnerUrl = withPort(booking.signaling_url, ports.runner);
      if (!runnerUrl) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "runner_url_invalid",
                message: "Failed to resolve runner URL from booking signaling URL",
              }),
            },
          ],
          isError: true,
        };
      }

      const commands = input.commands ?? [
        "EMOTE_Wave",
        "CAMSHOT.ExtremeClose",
        "CAMSHOT.WideShot",
        "EMOTE_ThumbsUp",
        "CAMSHOT.Default",
      ];
      const sessionId =
        input.session_id ??
        `renter-control-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
      const timeoutMs = input.timeout_ms ?? 30_000;
      const pollIntervalMs = input.poll_interval_ms ?? 500;

      const commandPayload = {
        session_id: sessionId,
        commands: commands.map((value, index) => ({
          delay_ms: index === 0 ? 0 : 500,
          type: "tcp",
          value,
        })),
        audio: [],
      };

      let executeResponseStatus = 0;
      try {
        const executeResponse = await fetch(`${runnerUrl}/scripts/execute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(commandPayload),
        });
        executeResponseStatus = executeResponse.status;
        if (!executeResponse.ok) {
          const responseBody = await executeResponse.text();
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify({
                  error: "runner_execute_failed",
                  message: `script-runner execute returned ${executeResponse.status}`,
                  response: responseBody.slice(0, 1000),
                }),
              },
            ],
            isError: true,
          };
        }
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "runner_execute_unreachable",
                message,
              }),
            },
          ],
          isError: true,
        };
      }

      const deadline = Date.now() + timeoutMs;
      let lastState = "unknown";
      let lastStatusBody: Record<string, unknown> | undefined;
      let statusHttpCode = 0;

      while (Date.now() <= deadline) {
        try {
          const statusResponse = await fetch(
            `${runnerUrl}/scripts/${encodeURIComponent(sessionId)}`
          );
          statusHttpCode = statusResponse.status;
          if (statusResponse.ok) {
            const parsed = (await statusResponse.json()) as Record<string, unknown>;
            lastStatusBody = parsed;
            lastState =
              typeof parsed.state === "string" ? parsed.state.toLowerCase() : "unknown";

            if (
              lastState === "completed" ||
              lastState === "failed" ||
              lastState === "error" ||
              lastState === "cancelled"
            ) {
              const validated = lastState === "completed";
              if (!validated) {
                return {
                  content: [
                    {
                      type: "text" as const,
                      text: JSON.stringify({
                        error: "runner_terminal_failure",
                        message: `script-runner ended in terminal state ${lastState}`,
                        state: lastState,
                        session_id: sessionId,
                        execute_http_status: executeResponseStatus,
                        status_http_status: statusHttpCode,
                        status: parsed,
                      }),
                    },
                  ],
                  isError: true,
                };
              }

              audit.log("session_control_validated", {
                booking_id: input.booking_id,
                customer_id: input.customer_id,
                session_id: sessionId,
                command_count: commands.length,
              });

              return {
                content: [
                  {
                    type: "text" as const,
                    text: JSON.stringify(
                      {
                        validated: true,
                        booking_id: input.booking_id,
                        session_id: sessionId,
                        state: lastState,
                        runner_execute_url: `${runnerUrl}/scripts/execute`,
                        runner_status_url: `${runnerUrl}/scripts/${encodeURIComponent(sessionId)}`,
                        commands,
                        status: parsed,
                      },
                      null,
                      2
                    ),
                  },
                ],
              };
            }
          }
        } catch {
          // retry until deadline
        }

        await wait(pollIntervalMs);
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              error: "runner_status_timeout",
              message: `Timed out waiting for runner completion after ${timeoutMs}ms`,
              session_id: sessionId,
              last_state: lastState,
              execute_http_status: executeResponseStatus,
              status_http_status: statusHttpCode,
              status: lastStatusBody ?? null,
            }),
          },
        ],
        isError: true,
      };
    }
  );

  server.tool(
    "cancel_session",
    "Cancel an active or pending session. Returns cancellation confirmation and refund eligibility.",
    {
      booking_id: z.string().min(1).describe("The booking ID to cancel"),
      customer_id: z
        .string()
        .min(1)
        .describe("Your customer identifier (must match booking)"),
      reason: z
        .string()
        .max(500)
        .optional()
        .describe("Optional cancellation reason"),
    },
    async (params) => {
      const input = params as { booking_id: string; customer_id: string; reason?: string };
      const booking = store.getBooking(input.booking_id);

      if (!booking) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "not_found",
                message: `Booking ${input.booking_id} not found`,
              }),
            },
          ],
          isError: true,
        };
      }

      if (booking.customer_id !== input.customer_id) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "unauthorized",
                message: "Customer ID does not match booking",
              }),
            },
          ],
          isError: true,
        };
      }

      const cancellableStatuses = ["confirmed", "provisioning", "active"];
      if (!cancellableStatuses.includes(booking.status)) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "not_cancellable",
                message: `Booking is ${booking.status} and cannot be cancelled`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Determine refund eligibility (full refund if not yet active)
      const refundEligible = booking.status !== "active";

      try {
        store.updateBookingStatus(input.booking_id, "cancelled", {
          cancelled_at: new Date().toISOString(),
          cancel_reason: input.reason,
        });

        // Teardown if session was running
        if (booking.status === "active" || booking.status === "provisioning") {
          const targetOrchestratorId = booking.orchestrator_id ?? orchestratorId;
          const target = resolveTargetOrchestrator(targetOrchestratorId);
          if (target) {
            await target.provisioner.teardown(input.booking_id);
          } else {
            await internalTools.teardownSession(input.booking_id);
          }
        }

        audit.log("booking_cancelled", {
          booking_id: input.booking_id,
          customer_id: input.customer_id,
          orchestrator_id: booking.orchestrator_id ?? orchestratorId,
          reason: input.reason,
          refund_eligible: refundEligible,
          previous_status: booking.status,
        });

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                cancelled: true,
                booking_id: input.booking_id,
                orchestrator_id: booking.orchestrator_id ?? orchestratorId,
                refund_eligible: refundEligible,
                previous_status: booking.status,
              }),
            },
          ],
        };
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        audit.log("error", { action: "cancel_session", booking_id: input.booking_id, error: message });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "cancel_failed",
                message: "Cancellation failed. Please try again.",
              }),
            },
          ],
          isError: true,
        };
      }
    }
  );

  return server;
}

// --- Express HTTP+SSE server ---

export interface McpHttpServerOptions {
  port: number;
  rateLimiter: RateLimiter;
  audit: AuditLogger;
  authToken?: string;
}

export function createHttpServer(
  mcpServer: McpServer,
  options: McpHttpServerOptions
) {
  const app = express();
  const { rateLimiter, audit } = options;
  const authToken = options.authToken?.trim();

  // Track SSE transports for cleanup
  const transports = new Map<string, SSEServerTransport>();

  // Optional bearer-token auth on MCP endpoints.
  // Health check stays open for orchestration probes.
  app.use((req: Request, res: Response, next) => {
    if (!authToken || req.path === "/health") {
      next();
      return;
    }

    const authHeader = (req.headers.authorization ?? "").toString();
    const presented = authHeader.startsWith("Bearer ")
      ? authHeader.slice("Bearer ".length).trim()
      : "";

    if (!presented) {
      audit.log("error", { action: "auth", path: req.path, reason: "missing_token" });
      res.status(401).json({ error: "unauthorized" });
      return;
    }

    const expected = Buffer.from(authToken, "utf8");
    const received = Buffer.from(presented, "utf8");
    const valid =
      expected.length === received.length && timingSafeEqual(expected, received);

    if (!valid) {
      audit.log("error", { action: "auth", path: req.path, reason: "invalid_token" });
      res.status(401).json({ error: "unauthorized" });
      return;
    }

    next();
  });

  // Rate limiting middleware
  app.use((req: Request, res: Response, next) => {
    const ip = req.ip ?? req.socket.remoteAddress ?? "unknown";
    if (!rateLimiter.check(ip)) {
      audit.log("rate_limited", { ip, path: req.path });
      res.status(429).json({ error: "rate_limited", message: "Too many requests" });
      return;
    }
    next();
  });

  // Health check
  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok", service: "agent-negotiator" });
  });

  // SSE endpoint for MCP clients
  app.get("/sse", async (req: Request, res: Response) => {
    const transport = new SSEServerTransport("/messages", res);
    transports.set(transport.sessionId, transport);

    res.on("close", () => {
      transports.delete(transport.sessionId);
    });

    await mcpServer.connect(transport);
  });

  // Message endpoint for MCP tool calls
  app.post("/messages", async (req: Request, res: Response) => {
    const sessionId = req.query.sessionId as string;
    const transport = transports.get(sessionId);

    if (!transport) {
      res.status(400).json({ error: "invalid_session", message: "Unknown session ID" });
      return;
    }

    await transport.handlePostMessage(req, res);
  });

  return app;
}
