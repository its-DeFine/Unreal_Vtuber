import { describe, it, expect } from "vitest";
import { calculatePrice, usdToWei, weiToUsd } from "../src/negotiation/pricing.js";
import type { PricingConfig } from "../src/negotiation/config.js";

const defaultConfig: PricingConfig = {
  min_price_usd_per_hour: 2.5,
  max_price_usd_per_hour: 15.0,
  base_price_usd_per_hour: 5.0,
  surge_multiplier: 1.5,
  surge_threshold_pct: 70,
};

const ETH_USD = 2500;

describe("Pricing Engine", () => {
  it("calculates base price at low utilization", () => {
    const result = calculatePrice(
      { gpuUtilizationPct: 30, durationMin: 60, resolution: "720p" },
      defaultConfig,
      ETH_USD
    );

    expect(result.price_usd_per_hour).toBe(5.0);
    expect(result.price_usd_total).toBe(5.0);
    expect(result.surge_active).toBe(false);
  });

  it("applies surge pricing above threshold", () => {
    const result = calculatePrice(
      { gpuUtilizationPct: 85, durationMin: 60, resolution: "720p" },
      defaultConfig,
      ETH_USD
    );

    // utilization_factor = (85 - 70) / (100 - 70) = 0.5
    // surge_addon = 0.5 * 1.5 * 5.0 = 3.75
    // price = 5.0 + 3.75 = 8.75
    expect(result.price_usd_per_hour).toBe(8.75);
    expect(result.surge_active).toBe(true);
  });

  it("applies resolution multiplier", () => {
    const result = calculatePrice(
      { gpuUtilizationPct: 30, durationMin: 60, resolution: "1080p" },
      defaultConfig,
      ETH_USD
    );

    // 5.0 * 1.25 = 6.25
    expect(result.price_usd_per_hour).toBe(6.25);
  });

  it("clamps to min price", () => {
    const cheapConfig: PricingConfig = {
      ...defaultConfig,
      base_price_usd_per_hour: 1.0,
    };

    const result = calculatePrice(
      { gpuUtilizationPct: 10, durationMin: 60, resolution: "720p" },
      cheapConfig,
      ETH_USD
    );

    expect(result.price_usd_per_hour).toBe(2.5); // min
  });

  it("clamps to max price", () => {
    const result = calculatePrice(
      { gpuUtilizationPct: 99, durationMin: 60, resolution: "1080p" },
      defaultConfig,
      ETH_USD
    );

    // Would be: base(5) + surge(0.966 * 1.5 * 5 = 7.25) = 12.25, * 1.25 = 15.31
    // Clamped to 15.0
    expect(result.price_usd_per_hour).toBe(15.0);
  });

  it("calculates total for partial hours", () => {
    const result = calculatePrice(
      { gpuUtilizationPct: 30, durationMin: 30, resolution: "720p" },
      defaultConfig,
      ETH_USD
    );

    // 5.0/hr * 0.5hr = 2.5
    expect(result.price_usd_total).toBe(2.5);
  });

  it("converts USD to wei correctly", () => {
    const wei = usdToWei(5.0, 2500);
    // 5 / 2500 = 0.002 ETH = 2000000000000000 wei
    expect(wei).toBe("2000000000000000");
  });

  it("converts wei to USD correctly", () => {
    const usd = weiToUsd("2000000000000000", 2500);
    expect(usd).toBeCloseTo(5.0, 2);
  });

  it("handles zero ETH rate gracefully", () => {
    const wei = usdToWei(5.0, 0);
    expect(wei).toBe("0");
  });
});
