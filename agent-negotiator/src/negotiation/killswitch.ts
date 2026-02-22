/**
 * Killswitch mechanism.
 * When active, halts all new bookings. Existing sessions continue to run.
 * Checked via: env var NEGOTIATOR_KILLSWITCH=1, or config killswitch.enabled=true.
 */

import type { ConfigLoader } from "./config.js";

export class Killswitch {
  private configLoader: ConfigLoader;
  private envOverride: boolean;

  constructor(configLoader: ConfigLoader) {
    this.configLoader = configLoader;
    this.envOverride = process.env.NEGOTIATOR_KILLSWITCH === "1";
  }

  isActive(): boolean {
    return this.envOverride || this.configLoader.get().killswitch.enabled;
  }

  /** Activate via environment (persists until process restart or explicit deactivation). */
  activate(): void {
    this.envOverride = true;
  }

  /** Deactivate the env override. Config file setting still applies. */
  deactivate(): void {
    this.envOverride = false;
  }
}
