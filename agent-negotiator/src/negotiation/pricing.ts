/**
 * Pricing engine.
 *
 * Formula: price = base + (utilization_factor × surge_multiplier × base)
 * where utilization_factor = max(0, (gpu_pct - surge_threshold) / (100 - surge_threshold))
 *
 * Result is clamped to [min_price, max_price] from operator config.
 * Price is per-hour in USD, then converted to wei at the provided ETH/USD rate.
 */

import type { PricingConfig } from "./config.js";

export interface PricingInput {
  gpuUtilizationPct: number;
  durationMin: number;
  resolution: string;
}

export interface PricingResult {
  price_usd_per_hour: number;
  price_usd_total: number;
  price_wei: string;
  surge_active: boolean;
  gpu_utilization_pct: number;
}

// Resolution multipliers (higher res costs more)
const RESOLUTION_MULTIPLIERS: Record<string, number> = {
  "720p": 1.0,
  "1080p": 1.25,
  "1440p": 1.5,
  "4k": 2.0,
};

const WEI_PER_ETH = 10n ** 18n;

export function calculatePrice(
  input: PricingInput,
  config: PricingConfig,
  ethUsdRate: number
): PricingResult {
  const { gpuUtilizationPct, durationMin, resolution } = input;

  // Surge pricing based on GPU utilization
  const surgeActive = gpuUtilizationPct > config.surge_threshold_pct;
  let utilizationFactor = 0;
  if (surgeActive) {
    utilizationFactor =
      (gpuUtilizationPct - config.surge_threshold_pct) /
      (100 - config.surge_threshold_pct);
  }

  const surgeAddon =
    utilizationFactor * config.surge_multiplier * config.base_price_usd_per_hour;
  let pricePerHour = config.base_price_usd_per_hour + surgeAddon;

  // Resolution scaling
  const resMult = RESOLUTION_MULTIPLIERS[resolution] ?? 1.0;
  pricePerHour *= resMult;

  // Clamp to operator bounds
  pricePerHour = Math.max(config.min_price_usd_per_hour, pricePerHour);
  pricePerHour = Math.min(config.max_price_usd_per_hour, pricePerHour);

  // Round to 2 decimal places
  pricePerHour = Math.round(pricePerHour * 100) / 100;

  const hours = durationMin / 60;
  const totalUsd = Math.round(pricePerHour * hours * 100) / 100;

  // Convert to wei (bigint to avoid floating point issues)
  const priceWei = usdToWei(totalUsd, ethUsdRate);

  return {
    price_usd_per_hour: pricePerHour,
    price_usd_total: totalUsd,
    price_wei: priceWei,
    surge_active: surgeActive,
    gpu_utilization_pct: gpuUtilizationPct,
  };
}

export function usdToWei(usd: number, ethUsdRate: number): string {
  if (ethUsdRate <= 0) return "0";
  // (usd / ethUsdRate) * 10^18, done in bigint for precision
  const usdMicro = BigInt(Math.round(usd * 1_000_000));
  const rateMicro = BigInt(Math.round(ethUsdRate * 1_000_000));
  const wei = (usdMicro * WEI_PER_ETH) / rateMicro;
  return wei.toString();
}

export function weiToUsd(wei: string, ethUsdRate: number): number {
  const weiBig = BigInt(wei);
  const usdMicro = (weiBig * BigInt(Math.round(ethUsdRate * 1_000_000))) / WEI_PER_ETH;
  return Number(usdMicro) / 1_000_000;
}
