import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { ConfigLoader } from "../src/negotiation/config.js";

let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "config-test-"));
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

describe("ConfigLoader", () => {
  it("returns defaults when config file is missing", () => {
    const loader = new ConfigLoader(path.join(tmpDir, "nonexistent.yaml"));
    const cfg = loader.get();

    expect(cfg.pricing.base_price_usd_per_hour).toBe(5.0);
    expect(cfg.capacity.max_concurrent_sessions).toBe(2);
    expect(cfg.killswitch.enabled).toBe(false);
    expect(cfg.session_types).toHaveLength(2);
  });

  it("loads and merges partial config", () => {
    const configPath = path.join(tmpDir, "test.yaml");
    fs.writeFileSync(
      configPath,
      `
pricing:
  base_price_usd_per_hour: 8.0
  surge_multiplier: 2.0

killswitch:
  enabled: true
`
    );

    const loader = new ConfigLoader(configPath);
    const cfg = loader.get();

    expect(cfg.pricing.base_price_usd_per_hour).toBe(8.0);
    expect(cfg.pricing.surge_multiplier).toBe(2.0);
    // Defaults preserved for unset fields
    expect(cfg.pricing.min_price_usd_per_hour).toBe(2.5);
    expect(cfg.capacity.max_concurrent_sessions).toBe(2);
    expect(cfg.killswitch.enabled).toBe(true);
  });

  it("uses custom session types when provided", () => {
    const configPath = path.join(tmpDir, "test.yaml");
    fs.writeFileSync(
      configPath,
      `
session_types:
  - id: "custom_type"
    min_duration_minutes: 10
    max_duration_minutes: 60
    supported_resolutions: ["720p"]
`
    );

    const loader = new ConfigLoader(configPath);
    const cfg = loader.get();

    expect(cfg.session_types).toHaveLength(1);
    expect(cfg.session_types[0].id).toBe("custom_type");
  });
});
