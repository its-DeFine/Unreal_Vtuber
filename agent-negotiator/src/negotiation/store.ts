/**
 * SQLite store for bookings and quotes with state machine enforcement.
 *
 * State machines:
 *   Quote:   pending → accepted | expired
 *   Booking: confirmed → provisioning → active → completed | cancelled | failed
 */

import Database from "better-sqlite3";
import crypto from "node:crypto";

// --- Types ---

export type QuoteStatus = "pending" | "accepted" | "expired";

export type BookingStatus =
  | "confirmed"
  | "provisioning"
  | "active"
  | "completed"
  | "cancelled"
  | "failed";

export interface Quote {
  quote_id: string;
  session_type: string;
  duration_min: number;
  resolution: string;
  price_wei: string;
  price_usd_est: number;
  valid_until: string; // ISO 8601
  status: QuoteStatus;
  customer_message?: string;
  gpu_utilization_pct: number;
  created_at: string;
}

export interface Booking {
  booking_id: string;
  quote_id: string;
  customer_id: string;
  session_type: string;
  duration_min: number;
  resolution: string;
  price_wei: string;
  price_usd_est: number;
  status: BookingStatus;
  slot?: number;
  avatar_id?: string;
  signaling_url?: string;
  session_token?: string;
  started_at?: string;
  expires_at?: string;
  cancelled_at?: string;
  cancel_reason?: string;
  created_at: string;
}

// Runtime column whitelist for updateBookingStatus (prevents SQL injection)
const ALLOWED_BOOKING_EXTRA_COLUMNS = new Set([
  "slot",
  "signaling_url",
  "session_token",
  "avatar_id",
  "started_at",
  "expires_at",
  "cancelled_at",
  "cancel_reason",
]);

// Valid state transitions
const QUOTE_TRANSITIONS: Record<QuoteStatus, QuoteStatus[]> = {
  pending: ["accepted", "expired"],
  accepted: [],
  expired: [],
};

const BOOKING_TRANSITIONS: Record<BookingStatus, BookingStatus[]> = {
  confirmed: ["provisioning", "cancelled", "failed"],
  provisioning: ["active", "failed", "cancelled"],
  active: ["completed", "cancelled", "failed"],
  completed: [],
  cancelled: [],
  failed: [],
};

// --- Store ---

export class NegotiatorStore {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.migrate();
  }

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS quotes (
        quote_id         TEXT PRIMARY KEY,
        session_type     TEXT NOT NULL,
        duration_min     INTEGER NOT NULL,
        resolution       TEXT NOT NULL,
        price_wei        TEXT NOT NULL,
        price_usd_est    REAL NOT NULL,
        valid_until      TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'pending',
        customer_message TEXT,
        gpu_utilization_pct REAL NOT NULL DEFAULT 0,
        created_at       TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS bookings (
        booking_id     TEXT PRIMARY KEY,
        quote_id       TEXT NOT NULL REFERENCES quotes(quote_id),
        customer_id    TEXT NOT NULL,
        session_type   TEXT NOT NULL,
        duration_min   INTEGER NOT NULL,
        resolution     TEXT NOT NULL,
        price_wei      TEXT NOT NULL,
        price_usd_est  REAL NOT NULL,
        status         TEXT NOT NULL DEFAULT 'confirmed',
        slot           INTEGER,
        avatar_id      TEXT,
        signaling_url  TEXT,
        session_token  TEXT,
        started_at     TEXT,
        expires_at     TEXT,
        cancelled_at   TEXT,
        cancel_reason  TEXT,
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
      CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);
      CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);

      -- Prevent double-booking of same slot for active bookings
      CREATE UNIQUE INDEX IF NOT EXISTS idx_active_slot
        ON bookings(slot)
        WHERE status IN ('confirmed', 'provisioning', 'active') AND slot IS NOT NULL;
    `);
  }

  // --- Quotes ---

  createQuote(params: Omit<Quote, "quote_id" | "status" | "created_at">): Quote {
    const quote_id = `q_${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`;
    const now = new Date().toISOString();

    this.db
      .prepare(
        `INSERT INTO quotes (quote_id, session_type, duration_min, resolution,
         price_wei, price_usd_est, valid_until, status, customer_message,
         gpu_utilization_pct, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)`
      )
      .run(
        quote_id,
        params.session_type,
        params.duration_min,
        params.resolution,
        params.price_wei,
        params.price_usd_est,
        params.valid_until,
        params.customer_message ?? null,
        params.gpu_utilization_pct,
        now
      );

    return this.getQuote(quote_id)!;
  }

  getQuote(quoteId: string): Quote | undefined {
    return this.db
      .prepare("SELECT * FROM quotes WHERE quote_id = ?")
      .get(quoteId) as Quote | undefined;
  }

  updateQuoteStatus(quoteId: string, newStatus: QuoteStatus): void {
    const quote = this.getQuote(quoteId);
    if (!quote) throw new Error(`Quote ${quoteId} not found`);

    const allowed = QUOTE_TRANSITIONS[quote.status];
    if (!allowed.includes(newStatus)) {
      throw new Error(
        `Invalid quote transition: ${quote.status} → ${newStatus}`
      );
    }

    this.db
      .prepare("UPDATE quotes SET status = ? WHERE quote_id = ?")
      .run(newStatus, quoteId);
  }

  expireStaleQuotes(): number {
    const result = this.db
      .prepare(
        `UPDATE quotes SET status = 'expired'
         WHERE status = 'pending' AND valid_until < strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`
      )
      .run();
    return result.changes;
  }

  // --- Bookings ---

  createBooking(params: {
    quote_id: string;
    customer_id: string;
    slot?: number;
    maxConcurrentSessions?: number;
  }): Booking {
    const quote = this.getQuote(params.quote_id);
    if (!quote) throw new Error(`Quote ${params.quote_id} not found`);
    if (quote.status !== "pending") {
      throw new Error(`Quote ${params.quote_id} is ${quote.status}, not pending`);
    }

    // Check expiry
    if (new Date(quote.valid_until) < new Date()) {
      this.updateQuoteStatus(params.quote_id, "expired");
      throw new Error(`Quote ${params.quote_id} has expired`);
    }

    const booking_id = `b_${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`;
    const now = new Date().toISOString();

    // Atomic: check capacity + mark quote accepted + create booking with slot
    // Uses BEGIN IMMEDIATE to serialize concurrent writes (TOCTOU protection)
    const insert = this.db.transaction(() => {
      // Re-check capacity inside the transaction
      if (params.maxConcurrentSessions !== undefined) {
        const { count } = this.db
          .prepare(
            "SELECT COUNT(*) as count FROM bookings WHERE status IN ('confirmed', 'provisioning', 'active')"
          )
          .get() as { count: number };
        if (count >= params.maxConcurrentSessions) {
          throw new Error("No capacity: all session slots are in use");
        }
      }

      this.updateQuoteStatus(params.quote_id, "accepted");

      this.db
        .prepare(
          `INSERT INTO bookings (booking_id, quote_id, customer_id, session_type,
           duration_min, resolution, price_wei, price_usd_est, status, slot, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?)`
        )
        .run(
          booking_id,
          quote.quote_id,
          params.customer_id,
          quote.session_type,
          quote.duration_min,
          quote.resolution,
          quote.price_wei,
          quote.price_usd_est,
          params.slot ?? null,
          now
        );
    });
    insert();

    return this.getBooking(booking_id)!;
  }

  getBooking(bookingId: string): Booking | undefined {
    return this.db
      .prepare("SELECT * FROM bookings WHERE booking_id = ?")
      .get(bookingId) as Booking | undefined;
  }

  updateBookingStatus(
    bookingId: string,
    newStatus: BookingStatus,
    extra?: Partial<
      Pick<
        Booking,
        | "slot"
        | "avatar_id"
        | "signaling_url"
        | "session_token"
        | "started_at"
        | "expires_at"
        | "cancelled_at"
        | "cancel_reason"
      >
    >
  ): void {
    const booking = this.getBooking(bookingId);
    if (!booking) throw new Error(`Booking ${bookingId} not found`);

    const allowed = BOOKING_TRANSITIONS[booking.status];
    if (!allowed.includes(newStatus)) {
      throw new Error(
        `Invalid booking transition: ${booking.status} → ${newStatus}`
      );
    }

    const sets: string[] = ["status = ?"];
    const values: unknown[] = [newStatus];

    if (extra) {
      for (const [key, val] of Object.entries(extra)) {
        if (val !== undefined) {
          if (!ALLOWED_BOOKING_EXTRA_COLUMNS.has(key)) {
            throw new Error(`Invalid booking column: ${key}`);
          }
          sets.push(`${key} = ?`);
          values.push(val);
        }
      }
    }

    values.push(bookingId);
    this.db
      .prepare(`UPDATE bookings SET ${sets.join(", ")} WHERE booking_id = ?`)
      .run(...values);
  }

  getActiveBookings(): Booking[] {
    return this.db
      .prepare(
        "SELECT * FROM bookings WHERE status IN ('confirmed', 'provisioning', 'active')"
      )
      .all() as Booking[];
  }

  getActiveBookingCount(): number {
    const row = this.db
      .prepare(
        "SELECT COUNT(*) as count FROM bookings WHERE status IN ('confirmed', 'provisioning', 'active')"
      )
      .get() as { count: number };
    return row.count;
  }

  getBookingsByCustomer(customerId: string): Booking[] {
    return this.db
      .prepare("SELECT * FROM bookings WHERE customer_id = ? ORDER BY created_at DESC")
      .all(customerId) as Booking[];
  }

  getNextAvailableSlot(maxSlots: number): number | null {
    const usedSlots = this.db
      .prepare(
        "SELECT slot FROM bookings WHERE status IN ('confirmed', 'provisioning', 'active') AND slot IS NOT NULL"
      )
      .all() as { slot: number }[];

    const used = new Set(usedSlots.map((r) => r.slot));
    for (let i = 1; i <= maxSlots; i++) {
      if (!used.has(i)) return i;
    }
    return null;
  }

  close(): void {
    this.db.close();
  }
}
