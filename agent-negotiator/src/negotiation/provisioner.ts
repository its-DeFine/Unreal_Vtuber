/**
 * Session provisioner — manages deploy/teardown lifecycle via orchestrator-health.
 *
 * Flow:
 *   1. allocate slot (SQLite + cluster ports scheme)
 *   2. POST /cluster/deploy → starts avatar containers
 *   3. poll signaling healthcheck (up to 120s)
 *   4. return signaling_url + session_token
 *   5. schedule teardown timer at expiry
 */

import crypto from "node:crypto";
import type { NegotiatorStore } from "./store.js";
import type { AuditLogger } from "./audit.js";

export interface ProvisionResult {
  slot: number;
  signaling_url: string;
  session_token: string;
  expires_at: string;
}

interface ClusterDeployPayload {
  avatar_id: string;
  slot: number;
  gpu?: string;
  recreate?: boolean;
}

// Mirrors _cluster_ports from remote_health_service.py
function clusterPorts(slot: number) {
  return {
    signaling: 8080 + slot,
    runner: 9877 + slot,
    recorder: 8889 + slot,
    game_tcp: 7777 + slot,
  };
}

export class SessionProvisioner {
  private healthBaseUrl: string;
  private store: NegotiatorStore;
  private audit: AuditLogger;
  private teardownTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private signalingWaitMs: number;

  constructor(
    healthBaseUrl: string,
    store: NegotiatorStore,
    audit: AuditLogger,
    options?: { signalingWaitMs?: number }
  ) {
    // Strip trailing slash
    this.healthBaseUrl = healthBaseUrl.replace(/\/+$/, "");
    this.store = store;
    this.audit = audit;
    this.signalingWaitMs = options?.signalingWaitMs ?? 120_000;
  }

  async provision(
    bookingId: string,
    slot: number,
    durationMin: number
  ): Promise<ProvisionResult> {
    const sessionToken = crypto.randomUUID();
    const avatarId = `negotiator-${bookingId.slice(2, 10)}`;

    // Update booking to provisioning — persist avatar_id for reliable teardown
    this.store.updateBookingStatus(bookingId, "provisioning", { slot, avatar_id: avatarId });

    this.audit.log("booking_provisioning", { bookingId, slot, avatarId });

    // Deploy via orchestrator-health
    const deployPayload: ClusterDeployPayload = {
      avatar_id: avatarId,
      slot,
    };

    const deployRes = await fetch(`${this.healthBaseUrl}/cluster/deploy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(deployPayload),
    });

    if (!deployRes.ok) {
      const errText = await deployRes.text().catch(() => "unknown error");
      this.store.updateBookingStatus(bookingId, "failed");
      this.audit.log("error", {
        bookingId,
        error: `Deploy failed: ${deployRes.status} ${errText}`,
      });
      throw new Error(`Provisioning failed: ${deployRes.status} ${errText}`);
    }

    this.audit.log("session_provisioned", { bookingId, slot, avatarId });

    // Wait for signaling to come up
    const ports = clusterPorts(slot);
    const signalingUrl = `http://localhost:${ports.signaling}`;
    await this.waitForSignaling(signalingUrl, this.signalingWaitMs);

    const now = new Date();
    const expiresAt = new Date(now.getTime() + durationMin * 60_000);

    // Activate booking
    this.store.updateBookingStatus(bookingId, "active", {
      signaling_url: signalingUrl,
      session_token: sessionToken,
      started_at: now.toISOString(),
      expires_at: expiresAt.toISOString(),
    });

    this.audit.log("booking_active", {
      bookingId,
      slot,
      signaling_url: signalingUrl,
      expires_at: expiresAt.toISOString(),
    });

    // Schedule auto-teardown
    this.scheduleTeardown(bookingId, avatarId, durationMin);

    return {
      slot,
      signaling_url: signalingUrl,
      session_token: sessionToken,
      expires_at: expiresAt.toISOString(),
    };
  }

  async teardown(bookingId: string): Promise<void> {
    const booking = this.store.getBooking(bookingId);
    if (!booking?.slot) return;

    // Use persisted avatar_id, fall back to derivation for backwards compat
    const avatarId = booking.avatar_id ?? `negotiator-${bookingId.slice(2, 10)}`;

    try {
      const res = await fetch(`${this.healthBaseUrl}/cluster/down`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_id: avatarId }),
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => "unknown");
        this.audit.log("error", {
          bookingId,
          error: `Teardown failed: ${res.status} ${errText}`,
        });
      }
    } catch (err) {
      this.audit.log("error", {
        bookingId,
        error: `Teardown request failed: ${err}`,
      });
    }

    // Clear timer if exists
    const timer = this.teardownTimers.get(bookingId);
    if (timer) {
      clearTimeout(timer);
      this.teardownTimers.delete(bookingId);
    }

    this.audit.log("session_teardown", { bookingId, avatarId });
  }

  private scheduleTeardown(
    bookingId: string,
    avatarId: string,
    durationMin: number
  ): void {
    const timer = setTimeout(async () => {
      this.teardownTimers.delete(bookingId);
      const booking = this.store.getBooking(bookingId);
      if (booking?.status === "active") {
        this.store.updateBookingStatus(bookingId, "completed");
        this.audit.log("booking_completed", { bookingId, avatarId });
        await this.teardown(bookingId);
      }
    }, durationMin * 60_000);

    // Unref so it doesn't keep the process alive
    timer.unref();
    this.teardownTimers.set(bookingId, timer);
  }

  private async waitForSignaling(
    url: string,
    timeoutMs: number
  ): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const res = await fetch(url, {
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) return;
      } catch {
        // Not ready yet
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    // Don't fail — signaling might come up slightly later
    // The booking is already marked active; worst case, client retries connection
  }

  cancelAllTimers(): void {
    for (const timer of this.teardownTimers.values()) {
      clearTimeout(timer);
    }
    this.teardownTimers.clear();
  }
}
