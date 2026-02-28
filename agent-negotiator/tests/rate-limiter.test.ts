import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { RateLimiter } from "../src/channels/mcp.js";

describe("RateLimiter", () => {
  it("allows requests under the limit", () => {
    const limiter = new RateLimiter(5, 60_000);

    for (let i = 0; i < 5; i++) {
      expect(limiter.check("192.168.1.1")).toBe(true);
    }
  });

  it("blocks requests over the limit", () => {
    const limiter = new RateLimiter(3, 60_000);

    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(false);
  });

  it("tracks per-IP independently", () => {
    const limiter = new RateLimiter(2, 60_000);

    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(false); // blocked

    expect(limiter.check("10.0.0.2")).toBe(true); // different IP, allowed
  });

  it("resets after window expires", () => {
    vi.useFakeTimers();

    const limiter = new RateLimiter(2, 1000); // 1 second window

    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(true);
    expect(limiter.check("10.0.0.1")).toBe(false);

    vi.advanceTimersByTime(1500); // advance past window

    expect(limiter.check("10.0.0.1")).toBe(true); // reset

    vi.useRealTimers();
  });

  it("cleans up old entries", () => {
    vi.useFakeTimers();

    const limiter = new RateLimiter(10, 1000);
    limiter.check("10.0.0.1");
    limiter.check("10.0.0.2");

    vi.advanceTimersByTime(3000);
    limiter.cleanup();

    // After cleanup + window expiry, limits should be fresh
    expect(limiter.check("10.0.0.1")).toBe(true);

    vi.useRealTimers();
  });
});
