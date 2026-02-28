import fs from "node:fs";
import { parse as parseYaml } from "yaml";

export interface FleetOrchestratorConfig {
  id: string;
  health_url: string;
  signaling_public_base_url?: string;
  signaling_check_base_url?: string;
  max_concurrent_sessions?: number;
  capacity_threshold_pct?: number;
  enabled?: boolean;
}

export interface FleetRegistryFile {
  orchestrators?: FleetOrchestratorConfig[];
}

function normalizeUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim().replace(/\/+$/, "");
  return trimmed.length > 0 ? trimmed : undefined;
}

export function loadFleetRegistryFromFile(
  filePath: string | undefined
): FleetOrchestratorConfig[] {
  if (!filePath) {
    return [];
  }

  try {
    if (!fs.existsSync(filePath)) {
      return [];
    }

    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = (parseYaml(raw) ?? {}) as FleetRegistryFile;
    const items = Array.isArray(parsed.orchestrators) ? parsed.orchestrators : [];
    return items
      .map((item) => ({
        id: (item.id ?? "").trim(),
        health_url: normalizeUrl(item.health_url) ?? "",
        signaling_public_base_url: normalizeUrl(item.signaling_public_base_url),
        signaling_check_base_url: normalizeUrl(item.signaling_check_base_url),
        max_concurrent_sessions: item.max_concurrent_sessions,
        capacity_threshold_pct: item.capacity_threshold_pct,
        enabled: item.enabled ?? true,
      }))
      .filter((item) => item.id.length > 0 && item.health_url.length > 0 && item.enabled !== false);
  } catch {
    return [];
  }
}
