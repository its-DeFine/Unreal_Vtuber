/**
 * Agent internal tool definitions.
 *
 * These tools are available only to the container agent (reasoning boundary).
 * They are NOT exposed to MCP clients.
 *
 * Tools:
 *   _gpu_stats          — GET orchestrator-health GPU stats
 *   _read_operator_config — Read current operator config
 *   _check_capacity     — GPU stats + active bookings → available slots
 *   _provision_session   — Deploy avatar session via cluster API
 *   _teardown_session    — Tear down a session
 *   _store_booking       — Write booking state to SQLite
 */

import type { NegotiatorStore } from "./store.js";
import type { ConfigLoader } from "./config.js";
import type { SessionProvisioner } from "./provisioner.js";
import type { AuditLogger } from "./audit.js";

export interface GpuStats {
  index: number;
  uuid: string;
  utilization_gpu_pct: number;
  utilization_encoder_pct: number;
  utilization_decoder_pct: number;
  memory_used_mib: number;
  memory_total_mib: number;
  temperature_c: number;
  power_draw_w: number;
  power_limit_w: number;
}

export interface CapacityInfo {
  available: boolean;
  active_sessions: number;
  max_sessions: number;
  available_slots: number;
  gpu_utilization_pct: number;
  capacity_threshold_pct: number;
  next_slot: number | null;
}

export class InternalTools {
  private healthBaseUrl: string;
  private store: NegotiatorStore;
  private config: ConfigLoader;
  private provisioner: SessionProvisioner;
  private audit: AuditLogger;

  constructor(deps: {
    healthBaseUrl: string;
    store: NegotiatorStore;
    config: ConfigLoader;
    provisioner: SessionProvisioner;
    audit: AuditLogger;
  }) {
    this.healthBaseUrl = deps.healthBaseUrl.replace(/\/+$/, "");
    this.store = deps.store;
    this.config = deps.config;
    this.provisioner = deps.provisioner;
    this.audit = deps.audit;
  }

  async gpuStats(): Promise<GpuStats[]> {
    const res = await fetch(`${this.healthBaseUrl}/meta/gpu-stats`);
    if (!res.ok) {
      throw new Error(`GPU stats request failed: ${res.status}`);
    }
    const data = (await res.json()) as { gpus?: GpuStats[] };
    return data.gpus ?? [];
  }

  readOperatorConfig(): ReturnType<ConfigLoader["get"]> {
    return this.config.get();
  }

  async checkCapacity(): Promise<CapacityInfo> {
    const cfg = this.config.get();
    const activeCount = this.store.getActiveBookingCount();
    const maxSessions = cfg.capacity.max_concurrent_sessions;

    // Get GPU utilization
    let gpuPct = 0;
    let gpuTelemetryOk = true;
    try {
      const stats = await this.gpuStats();
      if (stats.length > 0) {
        gpuPct =
          stats.reduce((sum, g) => sum + g.utilization_gpu_pct, 0) /
          stats.length;
      }
    } catch {
      // Fail closed when telemetry is unavailable.
      gpuTelemetryOk = false;
      gpuPct = 100;
      this.audit.log("error", {
        action: "capacity_check",
        message: "GPU telemetry unavailable; failing capacity closed",
      });
    }

    const available =
      gpuTelemetryOk &&
      activeCount < maxSessions &&
      gpuPct < cfg.capacity.capacity_threshold_pct;

    const nextSlot = this.store.getNextAvailableSlot(maxSessions);

    return {
      available,
      active_sessions: activeCount,
      max_sessions: maxSessions,
      available_slots: Math.max(0, maxSessions - activeCount),
      gpu_utilization_pct: Math.round(gpuPct * 100) / 100,
      capacity_threshold_pct: cfg.capacity.capacity_threshold_pct,
      next_slot: nextSlot,
    };
  }

  async provisionSession(
    bookingId: string,
    slot: number,
    durationMin: number
  ) {
    return this.provisioner.provision(bookingId, slot, durationMin);
  }

  async teardownSession(bookingId: string) {
    return this.provisioner.teardown(bookingId);
  }

  storeBookingUpdate(
    bookingId: string,
    status: Parameters<NegotiatorStore["updateBookingStatus"]>[1],
    extra?: Parameters<NegotiatorStore["updateBookingStatus"]>[2]
  ) {
    this.store.updateBookingStatus(bookingId, status, extra);
    this.audit.log(`booking_${status}` as any, { bookingId, ...extra });
  }
}
