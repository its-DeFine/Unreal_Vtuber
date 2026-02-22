import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { NegotiatorStore } from "../src/negotiation/store.js";

let store: NegotiatorStore;
let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "negotiator-test-"));
  store = new NegotiatorStore(path.join(tmpDir, "test.db"));
});

afterEach(() => {
  store.close();
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

describe("NegotiatorStore — Quotes", () => {
  it("creates and retrieves a quote", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 42,
    });

    expect(quote.quote_id).toMatch(/^q_/);
    expect(quote.status).toBe("pending");
    expect(quote.session_type).toBe("avatar_stream");

    const retrieved = store.getQuote(quote.quote_id);
    expect(retrieved).toBeDefined();
    expect(retrieved!.quote_id).toBe(quote.quote_id);
  });

  it("transitions quote from pending to accepted", () => {
    const quote = store.createQuote({
      session_type: "avatar_interactive",
      duration_min: 30,
      resolution: "720p",
      price_wei: "500000000000000000",
      price_usd_est: 2.5,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 20,
    });

    store.updateQuoteStatus(quote.quote_id, "accepted");
    const updated = store.getQuote(quote.quote_id);
    expect(updated!.status).toBe("accepted");
  });

  it("rejects invalid quote transitions", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    store.updateQuoteStatus(quote.quote_id, "accepted");
    expect(() => store.updateQuoteStatus(quote.quote_id, "pending")).toThrow(
      "Invalid quote transition"
    );
  });

  it("expires stale quotes", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() - 1000).toISOString(), // already expired
      gpu_utilization_pct: 10,
    });

    const expired = store.expireStaleQuotes();
    expect(expired).toBe(1);

    const updated = store.getQuote(quote.quote_id);
    expect(updated!.status).toBe("expired");
  });
});

describe("NegotiatorStore — Bookings", () => {
  it("creates a booking from a pending quote", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 42,
    });

    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-123",
    });

    expect(booking.booking_id).toMatch(/^b_/);
    expect(booking.status).toBe("confirmed");
    expect(booking.customer_id).toBe("customer-123");
    expect(booking.session_type).toBe("avatar_stream");

    // Quote should now be accepted
    const updatedQuote = store.getQuote(quote.quote_id);
    expect(updatedQuote!.status).toBe("accepted");
  });

  it("rejects booking for non-pending quote", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    store.updateQuoteStatus(quote.quote_id, "expired");

    expect(() =>
      store.createBooking({
        quote_id: quote.quote_id,
        customer_id: "customer-123",
      })
    ).toThrow("not pending");
  });

  it("rejects booking for expired quote", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() - 1000).toISOString(),
      gpu_utilization_pct: 30,
    });

    expect(() =>
      store.createBooking({
        quote_id: quote.quote_id,
        customer_id: "customer-123",
      })
    ).toThrow("expired");
  });

  it("enforces booking state machine transitions", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-123",
    });

    // confirmed → provisioning → active → completed
    store.updateBookingStatus(booking.booking_id, "provisioning", { slot: 1 });
    store.updateBookingStatus(booking.booking_id, "active", {
      signaling_url: "http://localhost:8081",
      session_token: "tok-123",
      started_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600000).toISOString(),
    });
    store.updateBookingStatus(booking.booking_id, "completed");

    const final = store.getBooking(booking.booking_id);
    expect(final!.status).toBe("completed");
  });

  it("rejects invalid booking transitions", () => {
    const quote = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    const booking = store.createBooking({
      quote_id: quote.quote_id,
      customer_id: "customer-123",
    });

    // confirmed → completed is not valid (must go through provisioning/active)
    expect(() =>
      store.updateBookingStatus(booking.booking_id, "completed")
    ).toThrow("Invalid booking transition");
  });

  it("counts active bookings", () => {
    // Create two bookings
    for (let i = 0; i < 2; i++) {
      const q = store.createQuote({
        session_type: "avatar_stream",
        duration_min: 60,
        resolution: "1080p",
        price_wei: "1000000000000000000",
        price_usd_est: 5.0,
        valid_until: new Date(Date.now() + 300_000).toISOString(),
        gpu_utilization_pct: 30,
      });
      store.createBooking({
        quote_id: q.quote_id,
        customer_id: `customer-${i}`,
      });
    }

    expect(store.getActiveBookingCount()).toBe(2);
  });

  it("finds next available slot", () => {
    const q1 = store.createQuote({
      session_type: "avatar_stream",
      duration_min: 60,
      resolution: "1080p",
      price_wei: "1000000000000000000",
      price_usd_est: 5.0,
      valid_until: new Date(Date.now() + 300_000).toISOString(),
      gpu_utilization_pct: 30,
    });

    const b1 = store.createBooking({
      quote_id: q1.quote_id,
      customer_id: "c1",
    });

    store.updateBookingStatus(b1.booking_id, "provisioning", { slot: 1 });

    // Slot 1 is taken, so next should be 2
    expect(store.getNextAvailableSlot(3)).toBe(2);
  });

  it("returns null when all slots taken", () => {
    for (let i = 1; i <= 2; i++) {
      const q = store.createQuote({
        session_type: "avatar_stream",
        duration_min: 60,
        resolution: "1080p",
        price_wei: "1000000000000000000",
        price_usd_est: 5.0,
        valid_until: new Date(Date.now() + 300_000).toISOString(),
        gpu_utilization_pct: 30,
      });
      const b = store.createBooking({
        quote_id: q.quote_id,
        customer_id: `c${i}`,
      });
      store.updateBookingStatus(b.booking_id, "provisioning", { slot: i });
    }

    expect(store.getNextAvailableSlot(2)).toBeNull();
  });
});
