import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  buildZeroPriceSignatureHex,
  enforceAccessPolicy,
  loadSkillPolicyFromFile,
} from "../src/access/policy.js";

function writeSkillPolicyFile(contents: string): string {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "skill-policy-test-"));
  const filePath = path.join(tmpDir, "SKILL.md");
  fs.writeFileSync(filePath, contents, "utf8");
  return filePath;
}

const SKILL_WITH_POLICY = `
# Skill: client-embodied-control

## Negotiator Policy
\`\`\`yaml
negotiator_policy:
  entitlement:
    default: deny
    consumers:
      paid-buyer:
        rails: [paid]
      free-buyer:
        rails: [zero_price]
  paid_rail:
    require_http_status: 402
    require_standard: ERC-4337
  zero_price_rail:
    signed_message:
      secret_env: NEGOTIATOR_TEST_SIGNED_SECRET
      max_skew_seconds: 300
\`\`\`
`;

describe("skill.md access policy", () => {
  it("allows requests when no skill policy file is configured", () => {
    const policy = loadSkillPolicyFromFile(undefined, {});
    const decision = enforceAccessPolicy(policy, {
      customerId: "anyone",
      quoteId: "q_1",
    });

    expect(policy.configured).toBe(false);
    expect(decision.allowed).toBe(true);
  });

  it("denies consumers not entitled by skill policy", () => {
    const policyFile = writeSkillPolicyFile(SKILL_WITH_POLICY);
    const policy = loadSkillPolicyFromFile(policyFile, {
      NEGOTIATOR_TEST_SIGNED_SECRET: "test-secret",
    });

    const decision = enforceAccessPolicy(policy, {
      customerId: "unknown-buyer",
      quoteId: "q_unauthorized",
    });

    expect(policy.configured).toBe(true);
    expect(policy.parseError).toBeUndefined();
    expect(decision.allowed).toBe(false);
    expect(decision.code).toBe("unauthorized_consumer");
  });

  it("enforces paid rail requirements (402 + ERC-4337 + user op hash)", () => {
    const policyFile = writeSkillPolicyFile(SKILL_WITH_POLICY);
    const policy = loadSkillPolicyFromFile(policyFile, {
      NEGOTIATOR_TEST_SIGNED_SECRET: "test-secret",
    });

    const allowed = enforceAccessPolicy(policy, {
      customerId: "paid-buyer",
      quoteId: "q_paid",
      access: {
        rail: "paid",
        paid: {
          http_status: 402,
          standard: "ERC-4337",
          user_operation_hash: `0x${"a".repeat(64)}`,
        },
      },
    });
    expect(allowed.allowed).toBe(true);

    const denied = enforceAccessPolicy(policy, {
      customerId: "paid-buyer",
      quoteId: "q_paid",
      access: {
        rail: "paid",
        paid: {
          http_status: 401,
          standard: "ERC-4337",
          user_operation_hash: `0x${"a".repeat(64)}`,
        },
      },
    });
    expect(denied.allowed).toBe(false);
    expect(denied.code).toBe("paid_http_status_invalid");
  });

  it("verifies zero-price signed-message rail deterministically", () => {
    const policyFile = writeSkillPolicyFile(SKILL_WITH_POLICY);
    const secret = "test-secret";
    const nowMs = Date.UTC(2026, 1, 28, 15, 0, 0);
    const timestamp = new Date(nowMs).toISOString();

    const policy = loadSkillPolicyFromFile(policyFile, {
      NEGOTIATOR_TEST_SIGNED_SECRET: secret,
    });

    const signature = buildZeroPriceSignatureHex(
      secret,
      "free-buyer",
      "q_free",
      "nonce-1",
      timestamp
    );

    const allowed = enforceAccessPolicy(policy, {
      customerId: "free-buyer",
      quoteId: "q_free",
      nowMs,
      access: {
        rail: "zero_price",
        zero_price: {
          nonce: "nonce-1",
          timestamp,
          signature,
        },
      },
    });
    expect(allowed.allowed).toBe(true);

    const denied = enforceAccessPolicy(policy, {
      customerId: "free-buyer",
      quoteId: "q_free",
      nowMs,
      access: {
        rail: "zero_price",
        zero_price: {
          nonce: "nonce-1",
          timestamp,
          signature: `0x${"f".repeat(64)}`,
        },
      },
    });
    expect(denied.allowed).toBe(false);
    expect(denied.code).toBe("zero_price_signature_invalid");
  });
});
