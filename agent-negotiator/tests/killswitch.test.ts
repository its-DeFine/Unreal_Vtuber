import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { ConfigLoader } from "../src/negotiation/config.js";
import { Killswitch } from "../src/negotiation/killswitch.js";

let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "ks-test-"));
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  delete process.env.NEGOTIATOR_KILLSWITCH;
});

describe("Killswitch", () => {
  it("is inactive by default", () => {
    const loader = new ConfigLoader(path.join(tmpDir, "missing.yaml"));
    const ks = new Killswitch(loader);
    expect(ks.isActive()).toBe(false);
  });

  it("activates from config", () => {
    const configPath = path.join(tmpDir, "test.yaml");
    fs.writeFileSync(configPath, "killswitch:\n  enabled: true\n");

    const loader = new ConfigLoader(configPath);
    const ks = new Killswitch(loader);
    expect(ks.isActive()).toBe(true);
  });

  it("activates from env var", () => {
    process.env.NEGOTIATOR_KILLSWITCH = "1";
    const loader = new ConfigLoader(path.join(tmpDir, "missing.yaml"));
    const ks = new Killswitch(loader);
    expect(ks.isActive()).toBe(true);
  });

  it("can be toggled programmatically", () => {
    const loader = new ConfigLoader(path.join(tmpDir, "missing.yaml"));
    const ks = new Killswitch(loader);

    expect(ks.isActive()).toBe(false);
    ks.activate();
    expect(ks.isActive()).toBe(true);
    ks.deactivate();
    expect(ks.isActive()).toBe(false);
  });
});
