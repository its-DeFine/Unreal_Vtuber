/**
 * scheduler-client.mjs — Schedule management module for the agent brain.
 *
 * Syncs with the central calendar, notifies the agent of upcoming
 * appointments, handles booking requests, and manages conflicts.
 */

import { MemoryDB } from "./long-term-memory.mjs";

const NETWORK_URL = process.env.AGENT_NETWORK_URL || "";
const NETWORK_TOKEN = process.env.AGENT_NETWORK_TOKEN || "";
const AGENT_ID = `${process.env.AVATAR_SLUG || "default"}-${process.env.AGENT_NAME || "agent"}`;

// Appointment type priorities (higher = more important)
const TYPE_PRIORITY = {
  coaching: 5,
  stream: 4,
  human_meeting: 3,
  agent_meeting: 2,
  maintenance: 1,
};

export class SchedulerClient {
  constructor(memory = null) {
    this.memory = memory || new MemoryDB();
  }

  /**
   * Sync events from central calendar into local memory cache.
   */
  async syncFromNetwork() {
    if (!NETWORK_URL) return [];
    try {
      const res = await fetch(
        `${NETWORK_URL}/api/v1/calendar/events?participant=${AGENT_ID}&status=confirmed`,
        { headers: { Authorization: `Bearer ${NETWORK_TOKEN}` } }
      );
      const data = await res.json();
      const events = data.events || [];
      this.memory.syncEvents(events);
      return events;
    } catch (err) {
      console.error("[scheduler] Sync failed:", err.message);
      return [];
    }
  }

  /**
   * Get upcoming events from local cache.
   */
  getUpcoming() {
    return this.memory.upcomingEvents();
  }

  /**
   * Check if a proposed time conflicts with existing events.
   */
  hasConflict(scheduledAt, durationMinutes = 30) {
    const proposed = new Date(scheduledAt);
    const proposedEnd = new Date(proposed.getTime() + durationMinutes * 60000);
    const events = this.memory.upcomingEvents();

    for (const evt of events) {
      const evtStart = new Date(evt.scheduled_at);
      const evtEnd = new Date(evtStart.getTime() + (evt.duration_minutes || 30) * 60000);
      // Overlap check
      if (proposed < evtEnd && proposedEnd > evtStart) {
        return evt;
      }
    }
    return null;
  }

  /**
   * Request booking via the network calendar.
   */
  async requestBooking(title, eventType, participants, scheduledAt, durationMinutes = 30, notes = null) {
    if (!NETWORK_URL) {
      return { error: "Network not configured" };
    }

    // Check for conflicts
    const conflict = this.hasConflict(scheduledAt, durationMinutes);
    if (conflict) {
      return {
        error: "conflict",
        conflicting_event: conflict,
        suggestion: this._suggestAlternative(scheduledAt, durationMinutes),
      };
    }

    try {
      const res = await fetch(`${NETWORK_URL}/api/v1/calendar/book`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${NETWORK_TOKEN}`,
        },
        body: JSON.stringify({
          title,
          event_type: eventType,
          participants: [AGENT_ID, ...participants],
          scheduled_at: scheduledAt,
          duration_minutes: durationMinutes,
          proposed_by: AGENT_ID,
          notes,
        }),
      });
      return await res.json();
    } catch (err) {
      return { error: err.message };
    }
  }

  /**
   * Handle an incoming appointment request from a peer.
   */
  async handleRequest(event) {
    const conflict = this.hasConflict(event.scheduled_at, event.duration_minutes);
    if (conflict) {
      // Compare priorities
      const incomingPriority = TYPE_PRIORITY[event.event_type] || 0;
      const conflictPriority = TYPE_PRIORITY[conflict.event_type] || 0;
      if (incomingPriority <= conflictPriority) {
        return {
          action: "declined",
          reason: "conflict",
          conflicting_event: conflict.event_id,
          suggestion: this._suggestAlternative(event.scheduled_at, event.duration_minutes),
        };
      }
      // Higher priority incoming — auto-accept, decline existing
      console.log(`[scheduler] Accepting higher-priority ${event.event_type} over ${conflict.event_type}`);
    }
    return { action: "accepted", event_id: event.event_id };
  }

  /**
   * Find the next available slot after a given time.
   */
  _suggestAlternative(scheduledAt, durationMinutes) {
    const events = this.memory.upcomingEvents();
    let candidate = new Date(scheduledAt);

    for (const evt of events) {
      const evtStart = new Date(evt.scheduled_at);
      const evtEnd = new Date(evtStart.getTime() + (evt.duration_minutes || 30) * 60000);
      const candidateEnd = new Date(candidate.getTime() + durationMinutes * 60000);

      if (candidate < evtEnd && candidateEnd > evtStart) {
        // Move candidate to after this event
        candidate = evtEnd;
      }
    }
    return candidate.toISOString();
  }

  /**
   * Check for events happening soon and prepare context.
   */
  async prepareForUpcoming(withinMinutes = 15) {
    const events = this.getUpcoming();
    const now = Date.now();
    const soon = [];

    for (const evt of events) {
      const start = new Date(evt.scheduled_at).getTime();
      if (start - now <= withinMinutes * 60000 && start > now) {
        soon.push(evt);
      }
    }

    if (soon.length === 0) return null;

    // Load relationship context for participants
    const contextParts = [];
    for (const evt of soon) {
      const participants = JSON.parse(evt.participants || "[]");
      for (const p of participants) {
        if (p === AGENT_ID) continue;
        const rel = this.memory.getRelationship(p);
        if (rel) {
          contextParts.push(
            `Upcoming ${evt.event_type} with ${rel.name} (${rel.interaction_count} previous interactions, sentiment: ${rel.sentiment})`
          );
        } else {
          contextParts.push(`Upcoming ${evt.event_type} with ${p} (first meeting)`);
        }
      }
    }

    return contextParts.join("\n");
  }
}
