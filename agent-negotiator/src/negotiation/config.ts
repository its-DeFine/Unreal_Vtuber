/**
 * Operator configuration loader with hot-reload via chokidar.
 * Reads negotiator.yaml, validates with defaults, emits on change.
 */

import fs from "node:fs";
import { parse as parseYaml } from "yaml";
import { watch } from "chokidar";
import { EventEmitter } from "node:events";

export interface PricingConfig {
  min_price_usd_per_hour: number;
  max_price_usd_per_hour: number;
  base_price_usd_per_hour: number;
  surge_multiplier: number;
  surge_threshold_pct: number;
}

export interface CapacityConfig {
  max_concurrent_sessions: number;
  capacity_threshold_pct: number;
}

export interface SessionTypeConfig {
  id: string;
  min_duration_minutes: number;
  max_duration_minutes: number;
  supported_resolutions: string[];
}

export interface KillswitchConfig {
  enabled: boolean;
}

export interface NegotiatorConfig {
  pricing: PricingConfig;
  capacity: CapacityConfig;
  session_types: SessionTypeConfig[];
  killswitch: KillswitchConfig;
}

const DEFAULTS: NegotiatorConfig = {
  pricing: {
    min_price_usd_per_hour: 2.5,
    max_price_usd_per_hour: 15.0,
    base_price_usd_per_hour: 5.0,
    surge_multiplier: 1.5,
    surge_threshold_pct: 70,
  },
  capacity: {
    max_concurrent_sessions: 2,
    capacity_threshold_pct: 85,
  },
  session_types: [
    {
      id: "avatar_stream",
      min_duration_minutes: 15,
      max_duration_minutes: 480,
      supported_resolutions: ["720p", "1080p"],
    },
    {
      id: "avatar_interactive",
      min_duration_minutes: 5,
      max_duration_minutes: 120,
      supported_resolutions: ["720p", "1080p"],
    },
  ],
  killswitch: { enabled: false },
};

export class ConfigLoader extends EventEmitter {
  private config: NegotiatorConfig;
  private configPath: string;
  private watcher?: ReturnType<typeof watch>;

  constructor(configPath: string) {
    super();
    this.configPath = configPath;
    this.config = this.load();
  }

  private load(): NegotiatorConfig {
    const parsed = fs.existsSync(this.configPath)
      ? (parseYaml(fs.readFileSync(this.configPath, "utf-8")) ?? {})
      : {};

    return {
      pricing: { ...DEFAULTS.pricing, ...parsed.pricing },
      capacity: { ...DEFAULTS.capacity, ...parsed.capacity },
      session_types:
        parsed.session_types?.length > 0
          ? parsed.session_types
          : DEFAULTS.session_types,
      killswitch: { ...DEFAULTS.killswitch, ...parsed.killswitch },
    };
  }

  get(): NegotiatorConfig {
    return this.config;
  }

  startWatching(): void {
    this.watcher = watch(this.configPath, {
      ignoreInitial: true,
      awaitWriteFinish: { stabilityThreshold: 500 },
    });

    this.watcher.on("change", () => {
      try {
        this.config = this.load();
        this.emit("reload", this.config);
      } catch (err) {
        this.emit("error", err);
      }
    });
  }

  stopWatching(): void {
    this.watcher?.close();
  }
}
