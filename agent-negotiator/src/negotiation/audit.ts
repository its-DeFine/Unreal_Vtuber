/**
 * Append-only JSONL audit logger.
 * Every interaction — quotes, bookings, provisions, cancellations, errors —
 * gets a timestamped entry. The file is never truncated or rewritten.
 */

import fs from "node:fs";
import path from "node:path";

export type AuditEvent =
  | "quote_created"
  | "quote_expired"
  | "booking_created"
  | "booking_provisioning"
  | "booking_active"
  | "booking_completed"
  | "booking_cancelled"
  | "booking_connection_updated"
  | "booking_failed"
  | "session_provisioned"
  | "session_control_validated"
  | "session_teardown"
  | "killswitch_activated"
  | "killswitch_deactivated"
  | "config_reloaded"
  | "rate_limited"
  | "validation_error"
  | "error";

export interface AuditEntry {
  timestamp: string;
  event: AuditEvent;
  data: Record<string, unknown>;
  source_ip?: string;
}

export class AuditLogger {
  private fd: number | null;
  private filePath: string;

  constructor(logDir: string) {
    fs.mkdirSync(logDir, { recursive: true });
    this.filePath = path.join(logDir, "audit.jsonl");
    this.fd = fs.openSync(this.filePath, "a");
  }

  log(event: AuditEvent, data: Record<string, unknown>, sourceIp?: string): void {
    const entry: AuditEntry = {
      timestamp: new Date().toISOString(),
      event,
      data,
      ...(sourceIp && { source_ip: sourceIp }),
    };

    const line = JSON.stringify(entry) + "\n";
    if (this.fd !== null) fs.writeSync(this.fd, line);
  }

  getPath(): string {
    return this.filePath;
  }

  close(): void {
    if (this.fd !== null) {
      fs.closeSync(this.fd);
      this.fd = null;
    }
  }
}
