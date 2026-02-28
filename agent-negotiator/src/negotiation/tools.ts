/**
 * Customer-facing MCP tool definitions.
 *
 * These are the tools exposed to MCP clients (customers).
 * They run in the orchestrator process — the hard security boundary.
 *
 * Tools:
 *   orchestrator_info  — discovery (capabilities, GPU, pricing range)
 *   negotiate_quote    — get pricing for a session
 *   accept_quote       — book a session
 *   session_status     — check an active session
 *   cancel_session     — cancel/refund
 */

import { z } from "zod";

// --- Input schemas ---

export const NegotiateQuoteInput = z.object({
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
    .regex(/^\d+p$/)
    .describe("Video resolution (e.g. 720p, 1080p)"),
  message: z
    .string()
    .max(500)
    .optional()
    .describe("Optional message or requirements"),
});

export const AcceptQuoteInput = z.object({
  quote_id: z.string().min(1).describe("The quote ID to accept"),
  customer_id: z.string().min(1).max(128).describe("Your unique customer identifier"),
  start_time: z
    .string()
    .datetime()
    .optional()
    .describe("Desired start time (ISO 8601). If omitted, starts immediately."),
});

export const SessionStatusInput = z.object({
  booking_id: z.string().min(1).describe("The booking ID to check"),
});

export const CancelSessionInput = z.object({
  booking_id: z.string().min(1).describe("The booking ID to cancel"),
  customer_id: z.string().min(1).describe("Your customer identifier (must match booking)"),
  reason: z
    .string()
    .max(500)
    .optional()
    .describe("Optional cancellation reason"),
});

// Note: MCP tool registration uses inline zod schemas in src/channels/mcp.ts.
// These schemas above are the canonical input definitions — the MCP channel
// imports them for validation.
