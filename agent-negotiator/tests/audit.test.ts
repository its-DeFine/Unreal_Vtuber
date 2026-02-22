import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { AuditLogger } from "../src/negotiation/audit.js";

let logger: AuditLogger;
let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "audit-test-"));
  logger = new AuditLogger(tmpDir);
});

afterEach(() => {
  logger.close();
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

describe("AuditLogger", () => {
  it("writes JSONL entries", () => {
    logger.log("quote_created", { quote_id: "q_test1", price: 5.0 });
    logger.log("booking_created", { booking_id: "b_test1" }, "192.168.1.1");

    const content = fs.readFileSync(logger.getPath(), "utf-8");
    const lines = content.trim().split("\n");

    expect(lines).toHaveLength(2);

    const entry1 = JSON.parse(lines[0]);
    expect(entry1.event).toBe("quote_created");
    expect(entry1.data.quote_id).toBe("q_test1");
    expect(entry1.timestamp).toBeDefined();
    expect(entry1.source_ip).toBeUndefined();

    const entry2 = JSON.parse(lines[1]);
    expect(entry2.event).toBe("booking_created");
    expect(entry2.source_ip).toBe("192.168.1.1");
  });

  it("appends to existing file", () => {
    logger.log("quote_created", { id: 1 });
    logger.close();

    // Reopen same file
    const logger2 = new AuditLogger(tmpDir);
    logger2.log("quote_created", { id: 2 });
    logger2.close();

    const content = fs.readFileSync(path.join(tmpDir, "audit.jsonl"), "utf-8");
    const lines = content.trim().split("\n");
    expect(lines).toHaveLength(2);
  });

  it("creates directory if it doesn't exist", () => {
    const nested = path.join(tmpDir, "sub", "dir");
    const nestedLogger = new AuditLogger(nested);
    nestedLogger.log("error", { message: "test" });
    nestedLogger.close();

    expect(fs.existsSync(path.join(nested, "audit.jsonl"))).toBe(true);
  });
});
