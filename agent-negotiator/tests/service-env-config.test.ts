import { afterEach, describe, expect, it } from "vitest";
import { loadNegotiatorEnvConfig } from "../src/service.js";

const BASE_ENV = { ...process.env };

afterEach(() => {
  for (const key of Object.keys(process.env)) {
    if (!(key in BASE_ENV)) {
      delete process.env[key];
    }
  }
  Object.assign(process.env, BASE_ENV);
});

describe("loadNegotiatorEnvConfig", () => {
  it("returns defaults when env vars are unset", () => {
    delete process.env.NEGOTIATOR_HOST;
    delete process.env.NEGOTIATOR_PORT;
    delete process.env.NEGOTIATOR_CONFIG_FILE;
    delete process.env.ORCHESTRATOR_HEALTH_URL;
    delete process.env.NEGOTIATOR_API_TOKEN;
    delete process.env.NEGOTIATOR_SKILL_POLICY_FILE;
    delete process.env.NEGOTIATOR_SIGNALING_PUBLIC_BASE_URL;
    delete process.env.NEGOTIATOR_SIGNALING_CHECK_BASE_URL;
    delete process.env.ORCHESTRATOR_ID;
    delete process.env.NEGOTIATOR_DATA_DIR;
    delete process.env.ETH_USD_RATE;
    delete process.env.NEGOTIATOR_RATE_LIMIT;
    delete process.env.NEGOTIATOR_CLEANUP_INTERVAL_MS;
    delete process.env.NEGOTIATOR_FLEET_REGISTRY_FILE;

    const config = loadNegotiatorEnvConfig();

    expect(config.host).toBe("0.0.0.0");
    expect(config.port).toBe(9100);
    expect(config.configFile).toBe("/config/negotiator.yaml");
    expect(config.skillPolicyFile).toBeUndefined();
    expect(config.healthUrl).toBe("http://vtuber-orchestrator-health:9090");
    expect(config.apiToken).toBeUndefined();
    expect(config.orchestratorId).toBe("unknown");
    expect(config.dataDir).toBe("/data");
    expect(config.ethUsdRate).toBe(2500);
    expect(config.rateLimitPerMinute).toBe(30);
    expect(config.quoteCleanupIntervalMs).toBe(60_000);
    expect(config.fleetRegistryFile).toBeUndefined();
  });

  it("parses supported env vars and falls back on invalid numeric values", () => {
    process.env.NEGOTIATOR_HOST = "127.0.0.1";
    process.env.NEGOTIATOR_PORT = "9201";
    process.env.NEGOTIATOR_CONFIG_FILE = "/tmp/negotiator.yaml";
    process.env.NEGOTIATOR_SKILL_POLICY_FILE = "/tmp/client-skill.md";
    process.env.ORCHESTRATOR_HEALTH_URL = "http://localhost:9090";
    process.env.NEGOTIATOR_API_TOKEN = "api-token";
    process.env.NEGOTIATOR_SIGNALING_PUBLIC_BASE_URL = "https://signal.public";
    process.env.NEGOTIATOR_SIGNALING_CHECK_BASE_URL = "https://signal.check";
    process.env.ORCHESTRATOR_ID = "orch-1";
    process.env.NEGOTIATOR_DATA_DIR = "/tmp/data";
    process.env.ETH_USD_RATE = "0";
    process.env.NEGOTIATOR_RATE_LIMIT = "-5";
    process.env.NEGOTIATOR_CLEANUP_INTERVAL_MS = "15000";
    process.env.NEGOTIATOR_FLEET_REGISTRY_FILE = "/tmp/fleet.yaml";

    const config = loadNegotiatorEnvConfig();

    expect(config.host).toBe("127.0.0.1");
    expect(config.port).toBe(9201);
    expect(config.configFile).toBe("/tmp/negotiator.yaml");
    expect(config.skillPolicyFile).toBe("/tmp/client-skill.md");
    expect(config.healthUrl).toBe("http://localhost:9090");
    expect(config.apiToken).toBe("api-token");
    expect(config.signalingPublicBaseUrl).toBe("https://signal.public");
    expect(config.signalingCheckBaseUrl).toBe("https://signal.check");
    expect(config.orchestratorId).toBe("orch-1");
    expect(config.dataDir).toBe("/tmp/data");
    expect(config.ethUsdRate).toBe(2500);
    expect(config.rateLimitPerMinute).toBe(30);
    expect(config.quoteCleanupIntervalMs).toBe(15000);
    expect(config.fleetRegistryFile).toBe("/tmp/fleet.yaml");
  });

  it("treats a blank API token env as unset", () => {
    process.env.NEGOTIATOR_API_TOKEN = "   ";

    const config = loadNegotiatorEnvConfig();

    expect(config.apiToken).toBeUndefined();
  });

  it("lets explicit overrides win over env values", () => {
    process.env.NEGOTIATOR_PORT = "9202";
    process.env.NEGOTIATOR_API_TOKEN = "env-token";
    process.env.NEGOTIATOR_SKILL_POLICY_FILE = "/tmp/from-env.md";

    const config = loadNegotiatorEnvConfig({
      port: 9300,
      apiToken: "override-token",
      skillPolicyFile: "/tmp/from-override.md",
      quoteCleanupIntervalMs: 5000,
    });

    expect(config.port).toBe(9300);
    expect(config.apiToken).toBe("override-token");
    expect(config.skillPolicyFile).toBe("/tmp/from-override.md");
    expect(config.quoteCleanupIntervalMs).toBe(5000);
  });
});
