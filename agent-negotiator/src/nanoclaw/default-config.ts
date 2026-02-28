import fs from "node:fs";
import path from "node:path";
import type { NegotiatorLogger } from "../service.js";

export const DEFAULT_NEGOTIATOR_CONFIG_YAML = `pricing:
  min_price_usd_per_hour: 2.50
  max_price_usd_per_hour: 15.00
  base_price_usd_per_hour: 5.00
  surge_multiplier: 1.5
  surge_threshold_pct: 70

capacity:
  max_concurrent_sessions: 2
  capacity_threshold_pct: 85

session_types:
  - id: "avatar_stream"
    min_duration_minutes: 15
    max_duration_minutes: 480
    supported_resolutions: ["720p", "1080p"]
  - id: "avatar_interactive"
    min_duration_minutes: 5
    max_duration_minutes: 120
    supported_resolutions: ["720p", "1080p"]

killswitch:
  enabled: false
`;

export function ensureNegotiatorConfigFile(
  configFile: string,
  logger: NegotiatorLogger
): void {
  const dir = path.dirname(configFile);
  fs.mkdirSync(dir, { recursive: true });

  if (!fs.existsSync(configFile)) {
    fs.writeFileSync(configFile, DEFAULT_NEGOTIATOR_CONFIG_YAML, "utf8");
    logger.info(`[negotiator][nanoclaw] Created default config at ${configFile}`);
  }
}
