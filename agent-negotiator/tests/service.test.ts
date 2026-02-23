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
      runtimeSource: "nanoclaw-plugin",
    });

    const response = await fetch(`http://127.0.0.1:${service.port}/health`);
    expect(response.status).toBe(200);

    const json = (await response.json()) as { status: string };
    expect(json.status).toBe("ok");

    await service.stop();

    await expect(fetch(`http://127.0.0.1:${service.port}/health`)).rejects.toBeTruthy();
  });
});
