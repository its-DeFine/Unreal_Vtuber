/**
 * Integration tests — full negotiate → book → provision → teardown flow
 * with a mocked orchestrator-health server.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import { NegotiatorStore } from "../src/negotiation/store.js";
import { AuditLogger } from "../src/negotiation/audit.js";
import { ConfigLoader } from "../src/negotiation/config.js";
import { Killswitch } from "../src/negotiation/killswitch.js";
import { SessionProvisioner } from "../src/negotiation/provisioner.js";
import { InternalTools } from "../src/negotiation/internal.js";
import {
  createMcpServer,
  createHttpServer,
  RateLimiter,
} from "../src/channels/mcp.js";

// --- Mock orchestrator-health server ---

let mockServer: http.Server;
let mockPort: number;
let mockGpuUtilization = 40;
let mockGpuStatsFail = false;
let deployCallCount = 0;
let downCallCount = 0;
const mockRunnerServers = new Map<number, http.Server>();
const mockRunnerPortsBySlot = new Map<number, number>();

function ensureMockRunnerForSlot(slot: number): Promise<number> {
  const existing = mockRunnerPortsBySlot.get(slot);
  if (typeof existing === "number") {
    return Promise.resolve(existing);
  }

  return new Promise((resolve, reject) => {
    const sessions = new Map<string, { state: string; lastCommand: string | null }>();
    const server = http.createServer((req, res) => {
      const url = new URL(req.url ?? "/", "http://localhost");

      if (url.pathname === "/health" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "ok" }));
        return;
      }

      if (url.pathname === "/scripts/execute" && req.method === "POST") {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
          try {
            const parsed = JSON.parse(body || "{}");
            const sessionId = String(parsed.session_id || "");
            const first = Array.isArray(parsed.commands) && parsed.commands.length > 0
              ? parsed.commands[0]
              : null;
            const lastCommand = first && typeof first.value === "string" ? first.value : null;
            sessions.set(sessionId, { state: "completed", lastCommand });

            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(
              JSON.stringify({
                session_id: sessionId,
                state: "running",
              })
            );
          } catch {
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "invalid_payload" }));
          }
        });
        return;
      }

      if (url.pathname.startsWith("/scripts/") && req.method === "GET") {
        const sessionId = decodeURIComponent(url.pathname.replace("/scripts/", ""));
        const status = sessions.get(sessionId);
        if (!status) {
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ detail: "session not found" }));
          return;
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            session_id: sessionId,
            state: status.state,
            last_command: status.lastCommand,
          })
        );
        return;
      }

      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "not_found" }));
    });

    server.on("error", reject);
    server.listen(0, () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      if (!port) {
        reject(new Error("failed to allocate mock runner port"));
        return;
      }
      mockRunnerServers.set(port, server);
      mockRunnerPortsBySlot.set(slot, port);
      resolve(port);
    });
  });
}

async function stopMockRunners(): Promise<void> {
  await Promise.all(
    Array.from(mockRunnerServers.values()).map(
      (server) =>
        new Promise<void>((resolve) => {
          server.close(() => resolve());
        })
    )
  );
  mockRunnerServers.clear();
  mockRunnerPortsBySlot.clear();
}

function startMockHealth(): Promise<void> {
  return new Promise((resolve) => {
    mockServer = http.createServer((req, res) => {
      const url = new URL(req.url!, `http://localhost`);

      if (url.pathname === "/meta/gpu-stats" && req.method === "GET") {
        if (mockGpuStatsFail) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "gpu stats unavailable" }));
          return;
        }

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            gpus: [
              {
                index: 0,
                uuid: "GPU-mock-0",
                utilization_gpu_pct: mockGpuUtilization,
                utilization_encoder_pct: 10,
                utilization_decoder_pct: 5,
                memory_used_mib: 4096,
                memory_total_mib: 16384,
                temperature_c: 65,
                power_draw_w: 150,
                power_limit_w: 300,
              },
            ],
          })
        );
        return;
      }

      if (url.pathname === "/cluster/deploy" && req.method === "POST") {
        deployCallCount++;
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", async () => {
          try {
            const parsed = JSON.parse(body);
            const slot = Number(parsed.slot) || 0;
            const runnerPort = await ensureMockRunnerForSlot(slot);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(
              JSON.stringify({
                status: "ok",
                deployed: parsed,
                ports: {
                  signaling: 8080 + slot,
                  runner: runnerPort,
                  recorder: 8889 + slot,
                  game_tcp: 7777 + slot,
                },
              })
            );
          } catch {
            res.writeHead(500, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "mock_deploy_failed" }));
          }
        });
        return;
      }

      if (url.pathname === "/cluster/down" && req.method === "POST") {
        downCallCount++;
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ status: "ok" }));
        });
        return;
      }

      // Simulate signaling healthcheck (always ready)
      if (req.method === "GET") {
        res.writeHead(200);
        res.end("ok");
        return;
      }

      res.writeHead(404);
      res.end("not found");
    });

    mockServer.listen(0, () => {
      const addr = mockServer.address();
      mockPort = typeof addr === "object" ? addr!.port : 0;
      resolve();
    });
  });
}

// --- Test setup ---

let tmpDir: string;
let store: NegotiatorStore;
let audit: AuditLogger;
let configLoader: ConfigLoader;
let killswitch: Killswitch;
let provisioner: SessionProvisioner;
let internalTools: InternalTools;

beforeAll(async () => {
  await startMockHealth();
});

afterAll(async () => {
  mockServer?.close();
  await stopMockRunners();
});

beforeEach(() => {
  // Reset state
  mockGpuUtilization = 40;
  mockGpuStatsFail = false;
  deployCallCount = 0;
  downCallCount = 0;

  // Fresh temp dir and dependencies for each test
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "integ-test-"));
  const configPath = path.join(tmpDir, "negotiator.yaml");

  fs.writeFileSync(
    configPath,
    `
pricing:
  min_price_usd_per_hour: 2.50
  max_price_usd_per_hour: 15.00
  base_price_usd_per_hour: 5.00
  surge_multiplier: 1.5
  surge_threshold_pct: 70

capacity:
  max_concurrent_sessions: 2
  capacity_threshold_pct: 85

session_types:
  - id: "avatar_stream"
    min_duration_minutes: 15
    max_duration_minutes: 480
    supported_resolutions: ["720p", "1080p"]
  - id: "avatar_interactive"
    min_duration_minutes: 5
    max_duration_minutes: 120
    supported_resolutions: ["720p", "1080p"]

killswitch:
  enabled: false
`
  );

  configLoader = new ConfigLoader(configPath);
  store = new NegotiatorStore(path.join(tmpDir, "test.db"));
  audit = new AuditLogger(tmpDir);
  killswitch = new Killswitch(configLoader);

  const healthUrl = `http://localhost:${mockPort}`;
  // Skip signaling wait in tests (mock doesn't listen on cluster ports)
  provisioner = new SessionProvisioner(healthUrl, store, audit, {
    signalingWaitMs: 0,
    signalingPublicBaseUrl: "https://orchestrator.example.com",
  });
  internalTools = new InternalTools({
    healthBaseUrl: healthUrl,
    store,
    config: configLoader,
    provisioner,
    audit,
  });

  return () => {
    provisioner.cancelAllTimers();
    store.close();
    audit.close();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  };
});

// --- Integration tests ---

describe("Integration: GPU Stats", () => {
  it("fetches GPU stats from mock orchestrator-health", async () => {
    const stats = await internalTools.gpuStats();

    expect(stats).toHaveLength(1);
    expect(stats[0].utilization_gpu_pct).toBe(40);
    expect(stats[0].memory_total_mib).toBe(16384);
  });
});

describe("Integration: Capacity Check", () => {
  it("reports available when under threshold", async () => {
    const capacity = await internalTools.checkCapacity();

    expect(capacity.available).toBe(true);
    expect(capacity.active_sessions).toBe(0);
    expect(capacity.max_sessions).toBe(2);
    expect(capacity.available_slots).toBe(2);
    expect(capacity.gpu_utilization_pct).toBe(40);
  });

  it("reports unavailable when GPU is over threshold", async () => {
    mockGpuUtilization = 90;

    const capacity = await internalTools.checkCapacity();

    expect(capacity.available).toBe(false);
    expect(capacity.gpu_utilization_pct).toBe(90);
  });

  it("fails closed when GPU telemetry is unavailable", async () => {
    mockGpuStatsFail = true;

    const capacity = await internalTools.checkCapacity();

    expect(capacity.available).toBe(false);
    expect(capacity.gpu_utilization_pct).toBe(100);
  });

  it("reports unavailable when sessions are full", async () => {
    // Fill all slots
    for (let i = 0; i < 2; i++) {
      const q = store.createQuote({
        session_type: "avatar_stream",
        duration_min: 60,
        resolution: "1080p",
        price_wei: "1000000000000000000",
        price_usd_est: 5.0,
        valid_until: new Date(Date.now() + 300_000).toISOString(),
        gpu_utilization_pct: 40,
      });
      store.createBooking({ quote_id: q.quote_id, customer_id: `c${i}` });
    }

    const capacity = await internalTools.checkCapacity();
    expect(capacity.available).toBe(false);
    expect(capacity.active_sessions).toBe(2);
    expect(capacity.available_slots).toBe(0);
  });
});

describe("Integration: Full Booking Flow", () => {
  it("negotiate → book → provision → complete lifecycle", async () => {
    // 1. Create a quote
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "2500000000000000",
      price_usd_est: 6.25,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 40,
    });

    expect(quote.status).toBe("pending");

    // 2. Accept the quote → creates a booking
    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-alice",
    });

    expect(booking.status).toBe("confirmed");
    expect(booking.customer_id).toBe("customer-alice");

    // Quote should now be accepted
    const updatedQuote = store.getQuote(quote.quote_id);
    expect(updatedQuote!.status).toBe("accepted");

    // 3. Check capacity and provision
    const capacity = await internalTools.checkCapacity();
    expect(capacity.available).toBe(true); // booking is "confirmed", not yet using a slot

    // Provision the session
    const result = await provisioner.provision(
      booking.booking_id,
      capacity.next_slot!,
      booking.duration_min
    );

    expect(result.slot).toBe(1);
    expect(result.avatar_id).toMatch(/^negotiator-/);
    expect(result.session_token).toBeDefined();
    expect(result.expires_at).toBeDefined();
    expect(result.runner_url).toContain("https://orchestrator.example.com:");
    expect(result.runner_execute_url).toBe(`${result.runner_url}/scripts/execute`);
    expect(result.runner_status_url_template).toBe(
      `${result.runner_url}/scripts/{session_id}`
    );
    expect(result.game_tcp_port).toBeGreaterThan(0);
    expect(deployCallCount).toBe(1);
    const localRunnerPort = mockRunnerPortsBySlot.get(result.slot);
    expect(localRunnerPort).toBeDefined();

    // Booking should be active
    const activeBooking = store.getBooking(booking.booking_id);
    expect(activeBooking!.status).toBe("active");
    expect(activeBooking!.signaling_url).toBeDefined();
    expect(activeBooking!.signaling_url).toContain("https://orchestrator.example.com:");
    expect(activeBooking!.slot).toBe(1);

    // 4. Simulate a buyer control command via script-runner
    const clientSessionId = `client-skill-${Date.now()}`;
    const localRunnerUrl = `http://127.0.0.1:${localRunnerPort}`;
    const executeResp = await fetch(`${localRunnerUrl}/scripts/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: clientSessionId,
        commands: [
          {
            delay_ms: 0,
            type: "tcp",
            value: "TTS_BYOB_/opt/embody/sample-15s.mp3",
          },
        ],
        audio: [],
      }),
    });
    expect(executeResp.ok).toBe(true);

    const executeBody = (await executeResp.json()) as {
      session_id: string;
      state: string;
    };
    expect(executeBody.session_id).toBe(clientSessionId);

    const statusResp = await fetch(
      `${localRunnerUrl}/scripts/${encodeURIComponent(clientSessionId)}`
    );
    expect(statusResp.ok).toBe(true);
    const statusBody = (await statusResp.json()) as {
      state: string;
      last_command: string;
    };
    expect(statusBody.state).toBe("completed");
    expect(statusBody.last_command).toBe("TTS_BYOB_/opt/embody/sample-15s.mp3");

    // 5. Teardown
    await provisioner.teardown(booking.booking_id);
    expect(downCallCount).toBe(1);

    // Verify audit trail
    const auditContent = fs.readFileSync(audit.getPath(), "utf-8");
    const auditLines = auditContent.trim().split("\n").map(JSON.parse);

    const events = auditLines.map((e: any) => e.event);
    expect(events).toContain("booking_provisioning");
    expect(events).toContain("session_provisioned");
    expect(events).toContain("booking_active");
    expect(events).toContain("session_teardown");
  });
});

describe("Integration: Cancellation Flow", () => {
  it("cancels a confirmed booking (pre-provision)", () => {
    const quote = store.createQuote({
      session_type: "avatar_interactive",
      duration_min: 30,
      resolution: "720p",
      price_wei: "1000000000000000",
      price_usd_est: 2.5,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-bob",
    });

    store.updateBookingStatus(booking.booking_id, "cancelled", {
      cancelled_at: new Date().toISOString(),
      cancel_reason: "Changed my mind",
    });

    const cancelled = store.getBooking(booking.booking_id);
    expect(cancelled!.status).toBe("cancelled");
    expect(cancelled!.cancel_reason).toBe("Changed my mind");
  });

  it("cancels an active booking with teardown", async () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "2500000000000000",
      price_usd_est: 6.25,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 40,
    });

    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-carol",
    });

    // Provision and activate
    await provisioner.provision(booking.booking_id, 1, 60);
    expect(store.getBooking(booking.booking_id)!.status).toBe("active");

    // Cancel
    store.updateBookingStatus(booking.booking_id, "cancelled", {
      cancelled_at: new Date().toISOString(),
    });
    await provisioner.teardown(booking.booking_id);

    expect(store.getBooking(booking.booking_id)!.status).toBe("cancelled");
    expect(downCallCount).toBe(1);
  });
});

describe("Integration: Killswitch", () => {
  it("blocks new bookings when killswitch is active", async () => {
    killswitch.activate();
    expect(killswitch.isActive()).toBe(true);

    // Capacity still technically available
    const capacity = await internalTools.checkCapacity();
    expect(capacity.available).toBe(true);

    // But killswitch should block at the MCP tool level
    // (This is enforced in the MCP channel, not the store layer)
    // Here we just verify the killswitch flag works
    killswitch.deactivate();
    expect(killswitch.isActive()).toBe(false);
  });
});

describe("Integration: Price Boundary Enforcement", () => {
  it("pricing never goes below min", async () => {
    const { calculatePrice } = await import("../src/negotiation/pricing.js");
    const cfg = configLoader.get().pricing;

    // Very low utilization, cheapest resolution
    const result = calculatePrice(
      { gpuUtilizationPct: 0, durationMin: 60, resolution: "720p" },
      cfg,
      2500
    );

    expect(result.price_usd_per_hour).toBeGreaterThanOrEqual(
      cfg.min_price_usd_per_hour
    );
  });

  it("pricing never goes above max", async () => {
    const { calculatePrice } = await import("../src/negotiation/pricing.js");
    const cfg = configLoader.get().pricing;

    // Max utilization, highest resolution
    const result = calculatePrice(
      { gpuUtilizationPct: 99, durationMin: 60, resolution: "1080p" },
      cfg,
      2500
    );

    expect(result.price_usd_per_hour).toBeLessThanOrEqual(
      cfg.max_price_usd_per_hour
    );
  });
});

describe("Integration: Slot Allocation", () => {
  it("allocates sequential slots and respects limits", async () => {
    // Book slot 1
    const q1 = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "2500000000000000",
      price_usd_est: 6.25,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 40,
    });
    const b1 = store.createBooking({ quote_id: q1.quote_id, customer_id: "c1" });
    await provisioner.provision(b1.booking_id, 1, 60);

    expect(store.getNextAvailableSlot(2)).toBe(2);

    // Book slot 2
    const q2 = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "2500000000000000",
      price_usd_est: 6.25,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 40,
    });
    const b2 = store.createBooking({ quote_id: q2.quote_id, customer_id: "c2" });
    await provisioner.provision(b2.booking_id, 2, 60);

    // No more slots
    expect(store.getNextAvailableSlot(2)).toBeNull();

    // Complete one — slot opens up
    store.updateBookingStatus(b1.booking_id, "completed");
    expect(store.getNextAvailableSlot(2)).toBe(1);
  });
});

describe("Integration: MCP Server Creation", () => {
  it("creates MCP server and HTTP app without errors", () => {
    const mcpServer = createMcpServer({
      store,
      config: configLoader,
      audit,
      killswitch,
      provisioner,
      internalTools,
      orchestratorId: "test-orch",
      ethUsdRate: 2500,
    });

    const rateLimiter = new RateLimiter(30, 60_000);
    const app = createHttpServer(mcpServer, {
      port: 0,
      rateLimiter,
      audit,
    });

    expect(mcpServer).toBeDefined();
    expect(app).toBeDefined();
  });
});
