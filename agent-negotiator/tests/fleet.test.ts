import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadFleetRegistryFromFile } from "../src/negotiation/fleet.js";

describe("loadFleetRegistryFromFile", () => {
  it("returns empty when file does not exist", () => {
    const out = loadFleetRegistryFromFile("/tmp/does-not-exist-fleet-registry.yaml");
    expect(out).toEqual([]);
  });

  it("parses valid orchestrators and filters invalid rows", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "fleet-registry-test-"));
    const file = path.join(dir, "fleet.yaml");
    fs.writeFileSync(
      file,
      `orchestrators:
  - id: orch-a
    health_url: http://orch-a:9090/
    signaling_public_base_url: https://stream-a.example.com/
  - id: ""
    health_url: http://invalid:9090
  - id: orch-b
    health_url: http://orch-b:9090
    enabled: false
`,
      "utf8"
    );

    const out = loadFleetRegistryFromFile(file);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({
      id: "orch-a",
      health_url: "http://orch-a:9090",
      signaling_public_base_url: "https://stream-a.example.com",
      enabled: true,
    });
  });
});
