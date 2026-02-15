/**
 * long-term-memory.mjs — SQLite-backed persistent memory for agent identity,
 * relationships, experiences, behaviors, and schedule cache.
 */

import Database from "better-sqlite3";
import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DB_PATH = process.env.MEMORY_DB_PATH || "/data/memory/agent-memory.db";

export class MemoryDB {
  constructor(path = DB_PATH) {
    const dir = dirname(path);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

    this.db = new Database(path);
    this.db.pragma("journal_mode = WAL");
    this._migrate();
  }

  // -------------------------------------------------------------------------
  // Schema
  // -------------------------------------------------------------------------
  _migrate() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS identity (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS relationships (
        entity_id         TEXT PRIMARY KEY,
        entity_type       TEXT NOT NULL DEFAULT 'human',  -- human | agent
        name              TEXT NOT NULL,
        last_interaction  TEXT DEFAULT (datetime('now')),
        interaction_count INTEGER DEFAULT 1,
        sentiment         TEXT DEFAULT 'neutral',
        notes             TEXT
      );

      CREATE TABLE IF NOT EXISTS experiences (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp         TEXT DEFAULT (datetime('now')),
        type              TEXT NOT NULL,  -- chat | meeting | coaching | maintenance
        summary           TEXT NOT NULL,
        entities_involved TEXT,           -- JSON array
        outcome           TEXT,
        learnings         TEXT
      );

      CREATE TABLE IF NOT EXISTS behaviors (
        skill_area        TEXT PRIMARY KEY,
        current_strategy  TEXT NOT NULL,
        confidence        REAL DEFAULT 0.5,
        last_updated      TEXT DEFAULT (datetime('now')),
        change_history    TEXT DEFAULT '[]'  -- JSON array
      );

      CREATE TABLE IF NOT EXISTS scheduled_events (
        event_id          TEXT PRIMARY KEY,
        title             TEXT NOT NULL,
        event_type        TEXT NOT NULL,
        participants      TEXT,           -- JSON array
        scheduled_at      TEXT NOT NULL,
        duration_minutes  INTEGER DEFAULT 30,
        status            TEXT DEFAULT 'confirmed',
        notes             TEXT
      );
    `);
  }

  // -------------------------------------------------------------------------
  // Identity
  // -------------------------------------------------------------------------
  getIdentity(key) {
    const row = this.db
      .prepare("SELECT value FROM identity WHERE key = ?")
      .get(key);
    return row ? row.value : null;
  }

  setIdentity(key, value) {
    this.db
      .prepare(
        `INSERT INTO identity (key, value, updated_at)
         VALUES (?, ?, datetime('now'))
         ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at`
      )
      .run(key, value);
  }

  // -------------------------------------------------------------------------
  // Relationships
  // -------------------------------------------------------------------------
  getRelationship(entityId) {
    return this.db
      .prepare("SELECT * FROM relationships WHERE entity_id = ?")
      .get(entityId);
  }

  upsertRelationship(entityId, entityType, name) {
    this.db
      .prepare(
        `INSERT INTO relationships (entity_id, entity_type, name, last_interaction, interaction_count)
         VALUES (?, ?, ?, datetime('now'), 1)
         ON CONFLICT(entity_id) DO UPDATE SET
           last_interaction = datetime('now'),
           interaction_count = interaction_count + 1`
      )
      .run(entityId, entityType, name);
  }

  updateSentiment(entityId, sentiment, notes) {
    this.db
      .prepare(
        "UPDATE relationships SET sentiment = ?, notes = ? WHERE entity_id = ?"
      )
      .run(sentiment, notes, entityId);
  }

  allRelationships() {
    return this.db.prepare("SELECT * FROM relationships ORDER BY last_interaction DESC").all();
  }

  // -------------------------------------------------------------------------
  // Experiences
  // -------------------------------------------------------------------------
  logExperience(type, summary, entitiesInvolved = [], outcome = null, learnings = null) {
    this.db
      .prepare(
        `INSERT INTO experiences (type, summary, entities_involved, outcome, learnings)
         VALUES (?, ?, ?, ?, ?)`
      )
      .run(
        type,
        summary,
        JSON.stringify(entitiesInvolved),
        outcome,
        learnings
      );
  }

  recentExperiences(limit = 10) {
    return this.db
      .prepare("SELECT * FROM experiences ORDER BY timestamp DESC LIMIT ?")
      .all(limit);
  }

  experiencesByType(type, limit = 20) {
    return this.db
      .prepare(
        "SELECT * FROM experiences WHERE type = ? ORDER BY timestamp DESC LIMIT ?"
      )
      .all(type, limit);
  }

  // -------------------------------------------------------------------------
  // Behaviors
  // -------------------------------------------------------------------------
  getBehavior(skillArea) {
    return this.db
      .prepare("SELECT * FROM behaviors WHERE skill_area = ?")
      .get(skillArea);
  }

  updateBehavior(skillArea, strategy) {
    const existing = this.getBehavior(skillArea);
    let history = [];
    if (existing) {
      try {
        history = JSON.parse(existing.change_history || "[]");
      } catch { /* ignore */ }
      history.push({
        previous: existing.current_strategy,
        changed_at: new Date().toISOString(),
      });
    }
    this.db
      .prepare(
        `INSERT INTO behaviors (skill_area, current_strategy, last_updated, change_history)
         VALUES (?, ?, datetime('now'), ?)
         ON CONFLICT(skill_area) DO UPDATE SET
           current_strategy = excluded.current_strategy,
           last_updated = excluded.last_updated,
           change_history = excluded.change_history`
      )
      .run(skillArea, strategy, JSON.stringify(history));
  }

  // -------------------------------------------------------------------------
  // Scheduled events (local cache from central calendar)
  // -------------------------------------------------------------------------
  syncEvents(events) {
    const del = this.db.prepare("DELETE FROM scheduled_events WHERE event_id = ?");
    const ins = this.db.prepare(
      `INSERT OR REPLACE INTO scheduled_events
       (event_id, title, event_type, participants, scheduled_at, duration_minutes, status, notes)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    );
    const tx = this.db.transaction((evts) => {
      for (const e of evts) {
        ins.run(
          e.event_id,
          e.title,
          e.event_type,
          JSON.stringify(e.participants || []),
          e.scheduled_at,
          e.duration_minutes || 30,
          e.status || "confirmed",
          e.notes || null
        );
      }
    });
    tx(events);
  }

  upcomingEvents() {
    return this.db
      .prepare(
        "SELECT * FROM scheduled_events WHERE scheduled_at >= datetime('now') ORDER BY scheduled_at ASC LIMIT 20"
      )
      .all();
  }

  // -------------------------------------------------------------------------
  // Stats
  // -------------------------------------------------------------------------
  stats() {
    const counts = {};
    for (const table of [
      "relationships",
      "experiences",
      "behaviors",
      "scheduled_events",
    ]) {
      const row = this.db
        .prepare(`SELECT COUNT(*) as c FROM ${table}`)
        .get();
      counts[table] = row.c;
    }
    return counts;
  }

  close() {
    this.db.close();
  }
}
