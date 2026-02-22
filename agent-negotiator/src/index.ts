/**
 * Agent Negotiator — MCP service for autonomous workload negotiation.
 *
 * Entry point: starts the MCP server, wires all dependencies, handles graceful shutdown.
 */

import path from "node:path";
import { NegotiatorStore } from "./negotiation/store.js";
import { AuditLogger } from "./negotiation/audit.js";
import { ConfigLoader } from "./negotiation/config.js";
import { Killswitch } from "./negotiation/killswitch.js";
import { SessionProvisioner } from "./negotiation/provisioner.js";
import { InternalTools } from "./negotiation/internal.js";
import {
  createMcpServer,
  createHttpServer,
  RateLimiter,
} from "./channels/mcp.js";

const PORT = parseInt(process.env.NEGOTIATOR_PORT ?? "9100", 10);
const CONFIG_FILE =
  process.env.NEGOTIATOR_CONFIG_FILE ?? "/config/negotiator.yaml";
const HEALTH_URL =
  process.env.ORCHESTRATOR_HEALTH_URL ?? "http://vtuber-orchestrator-health:9090";
const ORCHESTRATOR_ID = process.env.ORCHESTRATOR_ID ?? "unknown";
const DATA_DIR = process.env.NEGOTIATOR_DATA_DIR ?? "/data";
const ETH_USD_RATE = parseFloat(process.env.ETH_USD_RATE ?? "2500");

async function main() {
  console.log(`[negotiator] Starting agent-negotiator for ${ORCHESTRATOR_ID}`);
  console.log(`[negotiator] Config: ${CONFIG_FILE}`);
  console.log(`[negotiator] Health URL: ${HEALTH_URL}`);
  console.log(`[negotiator] Port: ${PORT}`);

  // Initialize dependencies
  const configLoader = new ConfigLoader(CONFIG_FILE);
  configLoader.startWatching();

  configLoader.on("reload", () => {
    console.log("[negotiator] Config reloaded");
    audit.log("config_reloaded", {});
  });
  configLoader.on("error", (err) => {
    console.error("[negotiator] Config reload error:", err);
  });

  const store = new NegotiatorStore(path.join(DATA_DIR, "negotiator.db"));
  const audit = new AuditLogger(DATA_DIR);
  const killswitch = new Killswitch(configLoader);
  const provisioner = new SessionProvisioner(HEALTH_URL, store, audit);

  const internalTools = new InternalTools({
    healthBaseUrl: HEALTH_URL,
    store,
    config: configLoader,
    provisioner,
    audit,
  });

  const rateLimiter = new RateLimiter(30, 60_000);

  // Clean up rate limiter periodically
  const cleanupInterval = setInterval(() => {
    rateLimiter.cleanup();
    store.expireStaleQuotes();
  }, 60_000);

  // Create MCP server
  const mcpServer = createMcpServer({
    store,
    config: configLoader,
    audit,
    killswitch,
    provisioner,
    internalTools,
    orchestratorId: ORCHESTRATOR_ID,
    ethUsdRate: ETH_USD_RATE,
  });

  // Create HTTP server
  const app = createHttpServer(mcpServer, {
    port: PORT,
    rateLimiter,
    audit,
  });

  const server = app.listen(PORT, () => {
    console.log(`[negotiator] MCP server listening on :${PORT}`);
    console.log(`[negotiator] SSE endpoint: http://localhost:${PORT}/sse`);
    console.log(`[negotiator] Health: http://localhost:${PORT}/health`);
  });

  // Graceful shutdown
  const shutdown = async () => {
    console.log("[negotiator] Shutting down...");
    clearInterval(cleanupInterval);
    provisioner.cancelAllTimers();
    configLoader.stopWatching();
    server.close();
    store.close();
    audit.close();
    process.exit(0);
  };

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

main().catch((err) => {
  console.error("[negotiator] Fatal:", err);
  process.exit(1);
});
