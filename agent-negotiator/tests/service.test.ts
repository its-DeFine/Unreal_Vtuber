import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, it, expect } from "vitest";
import { startNegotiatorService } from "../src/service.js";
import { DEFAULT_NEGOTIATOR_CONFIG_YAML } from "../src/nanoclaw/default-config.js";

describe("startNegotiatorService", () => {
  it("starts health endpoint and shuts down cleanly", async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "negotiator-service-test-"));
    const configFile = path.join(tmpDir, "negotiator.yaml");
    fs.writeFileSync(configFile, DEFAULT_NEGOTIATOR_CONFIG_YAML, "utf8");

    const service = await startNegotiatorService({
      host: "127.0.0.1",
      port: 0,
      configFile,
      healthUrl: "http://localhost:65534",
      orchestratorId: "svc-test",
      dataDir: path.join(tmpDir, "data"),
      ethUsdRate: 2500,
      rateLimitPerMinute: 100,
      quoteCleanupIntervalMs: 30_000,
    }, {
      runtimeSource: "openclaw-plugin",
    });

    const response = await fetch(`http://127.0.0.1:${service.port}/health`);
    expect(response.status).toBe(200);

    const json = (await response.json()) as { status: string };
    expect(json.status).toBe("ok");

    await service.stop();

    await expect(fetch(`http://127.0.0.1:${service.port}/health`)).rejects.toBeTruthy();
  });

  it("enforces OpenClaw token auth on MCP endpoints when configured", async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "negotiator-service-auth-test-"));
    const configFile = path.join(tmpDir, "negotiator.yaml");
    fs.writeFileSync(configFile, DEFAULT_NEGOTIATOR_CONFIG_YAML, "utf8");

    const service = await startNegotiatorService({
      host: "127.0.0.1",
      port: 0,
      configFile,
      healthUrl: "http://localhost:65534",
      orchestratorId: "svc-auth-test",
      dataDir: path.join(tmpDir, "data"),
      ethUsdRate: 2500,
      rateLimitPerMinute: 100,
      quoteCleanupIntervalMs: 30_000,
      openclawGatewayToken: "test-openclaw-token",
    }, {
      runtimeSource: "openclaw-plugin",
    });

    const base = `http://127.0.0.1:${service.port}`;

    const health = await fetch(`${base}/health`);
    expect(health.status).toBe(200);

    const noToken = await fetch(`${base}/sse`);
    expect(noToken.status).toBe(401);

    const badToken = await fetch(`${base}/sse`, {
      headers: { "x-openclaw-token": "wrong-token" },
    });
    expect(badToken.status).toBe(401);

    const ok = await fetch(`${base}/sse`, {
      headers: { Authorization: "Bearer test-openclaw-token" },
    });
    expect(ok.status).toBe(200);
    await ok.body?.cancel();

    await service.stop();
  });
});
