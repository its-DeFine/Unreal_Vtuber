import fs from "node:fs";
import { createHmac, timingSafeEqual } from "node:crypto";
import { parse as parseYaml } from "yaml";

export type AccessRail = "paid" | "zero_price";

export interface PaidAccessProof {
  http_status: number;
  standard: string;
  user_operation_hash: string;
}

export interface ZeroPriceAccessProof {
  nonce: string;
  timestamp: string;
  signature: string;
}

export interface AccessRequest {
  rail: AccessRail;
  paid?: PaidAccessProof;
  zero_price?: ZeroPriceAccessProof;
}

export interface LoadedSkillPolicy {
  configured: boolean;
  sourcePath?: string;
  parseError?: string;
  entitlementDefault: "allow" | "deny";
  consumers: Record<string, AccessRail[]>;
  paidRail: {
    requireHttpStatus: number;
    requireStandard: string;
  };
  zeroPriceRail: {
    secretEnv: string;
    secret?: string;
    maxSkewSeconds: number;
  };
}

export interface AccessEnforcementInput {
  customerId: string;
  quoteId: string;
  access?: AccessRequest;
  nowMs?: number;
}

export interface AccessDecision {
  allowed: boolean;
  code?: string;
  message?: string;
}

const DEFAULT_PAID_HTTP_STATUS = 402;
const DEFAULT_PAID_STANDARD = "ERC-4337";
const DEFAULT_ZERO_PRICE_SECRET_ENV = "NEGOTIATOR_SIGNED_MESSAGE_SECRET";
const DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS = 300;

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function asPositiveInt(value: unknown, fallback: number): number {
  const parsed =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number.parseInt(value, 10)
        : Number.NaN;
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return Math.floor(parsed);
}

function normalizeRail(value: string): AccessRail | null {
  const normalized = value.trim().toLowerCase().replace("-", "_");
  if (normalized === "paid") {
    return "paid";
  }
  if (normalized === "zero_price" || normalized === "zero" || normalized === "free") {
    return "zero_price";
  }
  return null;
}

function normalizeStandard(value: string): string {
  return value.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function parseRails(value: unknown): AccessRail[] {
  const values = Array.isArray(value) ? value : [];
  const rails = values
    .map((entry) => (typeof entry === "string" ? normalizeRail(entry) : null))
    .filter((entry): entry is AccessRail => entry !== null);
  return Array.from(new Set(rails));
}

function extractYamlOrJsonBlock(markdown: string): Record<string, unknown> | null {
  const fencedBlockRegex = /```(yaml|yml|json)\s*([\s\S]*?)```/gi;
  let match: RegExpExecArray | null;

  while ((match = fencedBlockRegex.exec(markdown)) !== null) {
    const language = match[1].toLowerCase();
    const body = match[2];
    try {
      const parsed =
        language === "json"
          ? (JSON.parse(body) as unknown)
          : (parseYaml(body) as unknown);
      const parsedRecord = asRecord(parsed);
      if (
        "negotiator_policy" in parsedRecord ||
        "entitlement" in parsedRecord ||
        "paid_rail" in parsedRecord ||
        "zero_price_rail" in parsedRecord
      ) {
        return parsedRecord;
      }
    } catch {
      continue;
    }
  }

  return null;
}

function parsePolicyObject(
  rawRoot: Record<string, unknown>,
  env: NodeJS.ProcessEnv
): Omit<LoadedSkillPolicy, "configured" | "sourcePath" | "parseError"> {
  const root = asRecord(rawRoot.negotiator_policy ?? rawRoot);

  const entitlement = asRecord(root.entitlement);
  const defaultMode = asString(entitlement.default)?.toLowerCase() === "deny" ? "deny" : "allow";
  const consumersRaw = asRecord(entitlement.consumers);
  const consumers: Record<string, AccessRail[]> = {};

  for (const [consumerId, rawValue] of Object.entries(consumersRaw)) {
    const entry = asRecord(rawValue);
    const rails = parseRails(entry.rails ?? rawValue);
    if (rails.length > 0) {
      consumers[consumerId] = rails;
    }
  }

  const paidRail = asRecord(root.paid_rail);
  const paidHttpStatus = asPositiveInt(
    paidRail.require_http_status,
    DEFAULT_PAID_HTTP_STATUS
  );
  const paidStandard = asString(paidRail.require_standard) ?? DEFAULT_PAID_STANDARD;

  const zeroPriceRail = asRecord(root.zero_price_rail);
  const signedMessageConfig = asRecord(zeroPriceRail.signed_message ?? zeroPriceRail);
  const secretEnv = asString(signedMessageConfig.secret_env) ?? DEFAULT_ZERO_PRICE_SECRET_ENV;
  const configuredSecret = asString(env[secretEnv]);
  const maxSkewSeconds = asPositiveInt(
    signedMessageConfig.max_skew_seconds,
    DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS
  );

  return {
    entitlementDefault: defaultMode,
    consumers,
    paidRail: {
      requireHttpStatus: paidHttpStatus,
      requireStandard: paidStandard,
    },
    zeroPriceRail: {
      secretEnv,
      secret: configuredSecret,
      maxSkewSeconds,
    },
  };
}

export function loadSkillPolicyFromFile(
  skillPolicyFile: string | undefined,
  env: NodeJS.ProcessEnv = process.env
): LoadedSkillPolicy {
  if (!skillPolicyFile) {
    return {
      configured: false,
      entitlementDefault: "allow",
      consumers: {},
      paidRail: {
        requireHttpStatus: DEFAULT_PAID_HTTP_STATUS,
        requireStandard: DEFAULT_PAID_STANDARD,
      },
      zeroPriceRail: {
        secretEnv: DEFAULT_ZERO_PRICE_SECRET_ENV,
        secret: asString(env[DEFAULT_ZERO_PRICE_SECRET_ENV]),
        maxSkewSeconds: DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS,
      },
    };
  }

  if (!fs.existsSync(skillPolicyFile)) {
    return {
      configured: true,
      sourcePath: skillPolicyFile,
      parseError: `skill policy file not found: ${skillPolicyFile}`,
      entitlementDefault: "deny",
      consumers: {},
      paidRail: {
        requireHttpStatus: DEFAULT_PAID_HTTP_STATUS,
        requireStandard: DEFAULT_PAID_STANDARD,
      },
      zeroPriceRail: {
        secretEnv: DEFAULT_ZERO_PRICE_SECRET_ENV,
        secret: asString(env[DEFAULT_ZERO_PRICE_SECRET_ENV]),
        maxSkewSeconds: DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS,
      },
    };
  }

  try {
    const markdown = fs.readFileSync(skillPolicyFile, "utf8");
    const parsedBlock = extractYamlOrJsonBlock(markdown);
    if (!parsedBlock) {
      return {
        configured: true,
        sourcePath: skillPolicyFile,
        parseError:
          "skill policy block not found; expected fenced yaml/json with negotiator_policy settings",
        entitlementDefault: "deny",
        consumers: {},
        paidRail: {
          requireHttpStatus: DEFAULT_PAID_HTTP_STATUS,
          requireStandard: DEFAULT_PAID_STANDARD,
        },
        zeroPriceRail: {
          secretEnv: DEFAULT_ZERO_PRICE_SECRET_ENV,
          secret: asString(env[DEFAULT_ZERO_PRICE_SECRET_ENV]),
          maxSkewSeconds: DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS,
        },
      };
    }

    const normalized = parsePolicyObject(parsedBlock, env);
    return {
      configured: true,
      sourcePath: skillPolicyFile,
      ...normalized,
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      configured: true,
      sourcePath: skillPolicyFile,
      parseError: `failed to parse skill policy: ${message}`,
      entitlementDefault: "deny",
      consumers: {},
      paidRail: {
        requireHttpStatus: DEFAULT_PAID_HTTP_STATUS,
        requireStandard: DEFAULT_PAID_STANDARD,
      },
      zeroPriceRail: {
        secretEnv: DEFAULT_ZERO_PRICE_SECRET_ENV,
        secret: asString(env[DEFAULT_ZERO_PRICE_SECRET_ENV]),
        maxSkewSeconds: DEFAULT_ZERO_PRICE_MAX_SKEW_SECONDS,
      },
    };
  }
}

function signedMessagePayload(
  customerId: string,
  quoteId: string,
  nonce: string,
  timestamp: string
): string {
  return `${customerId}|${quoteId}|${nonce}|${timestamp}`;
}

export function buildZeroPriceSignatureHex(
  secret: string,
  customerId: string,
  quoteId: string,
  nonce: string,
  timestamp: string
): string {
  return createHmac("sha256", secret)
    .update(signedMessagePayload(customerId, quoteId, nonce, timestamp))
    .digest("hex");
}

export function enforceAccessPolicy(
  policy: LoadedSkillPolicy | undefined,
  input: AccessEnforcementInput
): AccessDecision {
  if (!policy || !policy.configured) {
    return { allowed: true };
  }

  if (policy.parseError) {
    return {
      allowed: false,
      code: "policy_unavailable",
      message: policy.parseError,
    };
  }

  const allowedRails = policy.consumers[input.customerId];
  if (!allowedRails || allowedRails.length === 0) {
    if (policy.entitlementDefault === "deny") {
      return {
        allowed: false,
        code: "unauthorized_consumer",
        message: `customer_id ${input.customerId} is not entitled by skill policy`,
      };
    }

    if (!input.access) {
      return { allowed: true };
    }
  }

  if (!input.access) {
    return {
      allowed: false,
      code: "access_rail_required",
      message: "access rail proof is required by policy",
    };
  }

  if (allowedRails && allowedRails.length > 0 && !allowedRails.includes(input.access.rail)) {
    return {
      allowed: false,
      code: "rail_not_allowed",
      message: `rail ${input.access.rail} is not allowed for customer_id ${input.customerId}`,
    };
  }

  if (input.access.rail === "paid") {
    const paid = input.access.paid;
    if (!paid) {
      return {
        allowed: false,
        code: "paid_proof_missing",
        message: "paid rail selected but paid proof payload is missing",
      };
    }

    if (paid.http_status !== policy.paidRail.requireHttpStatus) {
      return {
        allowed: false,
        code: "paid_http_status_invalid",
        message: `expected http_status=${policy.paidRail.requireHttpStatus} for paid rail`,
      };
    }

    if (
      normalizeStandard(paid.standard) !==
      normalizeStandard(policy.paidRail.requireStandard)
    ) {
      return {
        allowed: false,
        code: "paid_standard_invalid",
        message: `expected payment standard ${policy.paidRail.requireStandard}`,
      };
    }

    if (!/^0x[a-fA-F0-9]{64}$/.test(paid.user_operation_hash)) {
      return {
        allowed: false,
        code: "paid_user_operation_hash_invalid",
        message: "user_operation_hash must be a 32-byte hex string",
      };
    }

    return { allowed: true };
  }

  const zeroPrice = input.access.zero_price;
  if (!zeroPrice) {
    return {
      allowed: false,
      code: "zero_price_proof_missing",
      message: "zero_price rail selected but signed message proof is missing",
    };
  }

  const timestampMs = Date.parse(zeroPrice.timestamp);
  if (!Number.isFinite(timestampMs)) {
    return {
      allowed: false,
      code: "zero_price_timestamp_invalid",
      message: "zero_price.timestamp must be a valid ISO-8601 timestamp",
    };
  }

  const nowMs = input.nowMs ?? Date.now();
  const skewSeconds = Math.abs(nowMs - timestampMs) / 1000;
  if (skewSeconds > policy.zeroPriceRail.maxSkewSeconds) {
    return {
      allowed: false,
      code: "zero_price_timestamp_expired",
      message: `signed message timestamp outside allowed skew window (${policy.zeroPriceRail.maxSkewSeconds}s)`,
    };
  }

  const secret = policy.zeroPriceRail.secret;
  if (!secret) {
    return {
      allowed: false,
      code: "zero_price_secret_missing",
      message: `signed-message secret not configured in env ${policy.zeroPriceRail.secretEnv}`,
    };
  }

  const providedHex = zeroPrice.signature.trim().replace(/^0x/i, "");
  if (!/^[a-fA-F0-9]{64}$/.test(providedHex)) {
    return {
      allowed: false,
      code: "zero_price_signature_format_invalid",
      message: "signature must be a 32-byte hex string",
    };
  }

  const expectedHex = buildZeroPriceSignatureHex(
    secret,
    input.customerId,
    input.quoteId,
    zeroPrice.nonce,
    zeroPrice.timestamp
  );

  const expected = Buffer.from(expectedHex, "hex");
  const provided = Buffer.from(providedHex, "hex");
  const valid =
    expected.length === provided.length && timingSafeEqual(expected, provided);

  if (!valid) {
    return {
      allowed: false,
      code: "zero_price_signature_invalid",
      message: "signed message verification failed",
    };
  }

  return { allowed: true };
}
