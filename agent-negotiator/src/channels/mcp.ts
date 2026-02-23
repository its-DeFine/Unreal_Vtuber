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
import type { Request, Response } from "express";
import { z } from "zod";

import type { NegotiatorStore } from "../negotiation/store.js";
import type { ConfigLoader } from "../negotiation/config.js";
import type { AuditLogger } from "../negotiation/audit.js";
import type { Killswitch } from "../negotiation/killswitch.js";
import type { SessionProvisioner } from "../negotiation/provisioner.js";
import type { InternalTools } from "../negotiation/internal.js";
import { calculatePrice, type PricingResult } from "../negotiation/pricing.js";

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
    this.maxPerWindow = maxPerWindow;
    this.windowMs = windowMs;
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
}

export function createMcpServer(deps: McpChannelDeps): McpServer {
  const {
    store,
    config,
    audit,
    killswitch,
    internalTools,
    orchestratorId,
  } = deps;

  const ethUsdRate = deps.ethUsdRate ?? 2500;

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
      try {
        const stats = await internalTools.gpuStats();
        if (stats.length > 0) {
          gpuInfo = `${stats.length}x GPU, ${stats[0].memory_total_mib}MiB VRAM each`;
        }
      } catch {
        gpuInfo = "GPU stats unavailable";
      }

      const capacity = await internalTools.checkCapacity();

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
    },
    async (params) => {
      // MCP SDK already validates via inline zod schemas; use params directly
      const input = params as { session_type: string; duration_min: number; resolution: string; message?: string };
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

      // Check capacity
      const capacity = await internalTools.checkCapacity();

      // Calculate price
      const pricing: PricingResult = calculatePrice(
        {
          gpuUtilizationPct: capacity.gpu_utilization_pct,
          durationMin: input.duration_min,
          resolution: input.resolution,
        },
        cfg.pricing,
        ethUsdRate
      );

      // Quote valid for 5 minutes
      const validUntil = new Date(Date.now() + 5 * 60_000).toISOString();

      const quote = store.createQuote({
        session_type: input.session_type,
        duration_min: input.duration_min,
        resolution: input.resolution,
        price_wei: pricing.price_wei,
        price_usd_est: pricing.price_usd_total,
        valid_until: validUntil,
        customer_message: input.message,
        gpu_utilization_pct: capacity.gpu_utilization_pct,
      });

      audit.log("quote_created", {
        quote_id: quote.quote_id,
        session_type: input.session_type,
        duration_min: input.duration_min,
        resolution: input.resolution,
        price_usd: pricing.price_usd_total,
        price_per_hour: pricing.price_usd_per_hour,
        surge: pricing.surge_active,
      });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                quote_id: quote.quote_id,
                price_wei: quote.price_wei,
                price_usd_est: pricing.price_usd_total,
                price_usd_per_hour: pricing.price_usd_per_hour,
                surge_active: pricing.surge_active,
                valid_until: quote.valid_until,
                available: capacity.available,
                available_slots: capacity.available_slots,
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
    },
    async (params) => {
      const input = params as { quote_id: string; customer_id: string; start_time?: string };

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

      // Capacity check
      const capacity = await internalTools.checkCapacity();
      if (!capacity.available || capacity.next_slot === null) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: "no_capacity",
                message: `No available slots. ${capacity.active_sessions}/${capacity.max_sessions} sessions active, GPU at ${capacity.gpu_utilization_pct}%.`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Create booking — atomically checks capacity + reserves slot inside SQLite transaction
      const cfg = config.get();
      let booking;
      try {
        booking = store.createBooking({
          quote_id: input.quote_id,
          customer_id: input.customer_id,
          slot: capacity.next_slot,
          maxConcurrentSessions: cfg.capacity.max_concurrent_sessions,
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
        slot: capacity.next_slot,
      });

      // Provision session
      try {
        const result = await internalTools.provisionSession(
          booking.booking_id,
          capacity.next_slot,
          booking.duration_min
        );

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  booking_id: booking.booking_id,
                  status: "active",
                  session: {
                    signaling_url: result.signaling_url,
                    token: result.session_token,
                    expires_at: result.expires_at,
                    slot: result.slot,
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
        audit.log("booking_failed", { booking_id: booking.booking_id, error: message });
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

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                booking_id: booking.booking_id,
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
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // --- cancel_session ---
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
          await internalTools.teardownSession(input.booking_id);
        }

        audit.log("booking_cancelled", {
          booking_id: input.booking_id,
          customer_id: input.customer_id,
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
}

export function createHttpServer(
  mcpServer: McpServer,
  options: McpHttpServerOptions
) {
  const app = express();
  const { rateLimiter, audit } = options;

  // Track SSE transports for cleanup
  const transports = new Map<string, SSEServerTransport>();

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
