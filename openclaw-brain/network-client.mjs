/**
 * network-client.mjs — Background daemon connecting the openclaw-brain to the
 * central agent-network server.
 *
 * Handles: registration, heartbeat, message polling, schedule sync,
 * knowledge sharing, governance participation, and the evolution loop.
 */

import { MemoryDB } from "./long-term-memory.mjs";

const NETWORK_URL = process.env.AGENT_NETWORK_URL || "";
const NETWORK_TOKEN = process.env.AGENT_NETWORK_TOKEN || "";
const AGENT_NAME = process.env.AGENT_NAME || "agent";
const AGENT_PERSONA = process.env.AGENT_PERSONA || "";
const AVATAR_SLUG = process.env.AVATAR_SLUG || "default";
const CHAT_SHIM_URL = process.env.CHAT_SHIM_URL || "http://localhost:18801";

if (!NETWORK_URL) {
  console.log("[network] AGENT_NETWORK_URL not set — exiting");
  process.exit(0);
}

const memory = new MemoryDB();
let agentToken = NETWORK_TOKEN;
let agentId = `${AVATAR_SLUG}-${AGENT_NAME}`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${agentToken}`,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${NETWORK_URL}/api/v1${path}`, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${method} ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 1. Registration
// ---------------------------------------------------------------------------
async function register() {
  try {
    const data = await api("POST", "/agents/register", {
      agent_id: agentId,
      name: AGENT_NAME,
      persona: AGENT_PERSONA,
      avatar_slug: AVATAR_SLUG,
      capabilities: ["streaming", "scheduling", "governance"],
    });
    if (data.token) agentToken = data.token;
    if (data.agent_id) agentId = data.agent_id;
    console.log(`[network] Registered as ${agentId}`);
  } catch (err) {
    console.error("[network] Registration failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 2. Heartbeat (every 60 s)
// ---------------------------------------------------------------------------
async function heartbeat() {
  try {
    // Gather metrics from chat-shim
    let shimMetrics = {};
    try {
      const res = await fetch(`${CHAT_SHIM_URL}/health`);
      shimMetrics = await res.json();
    } catch { /* chat-shim may not be ready */ }

    // Gather container health from infra-manager
    let containerHealth = [];
    try {
      const res = await fetch("http://localhost:18802/status");
      const data = await res.json();
      containerHealth = data.containers || [];
    } catch { /* infra-manager may not be ready */ }

    await api("POST", "/agents/heartbeat", {
      agent_id: agentId,
      status: "online",
      metrics: {
        chat_count: shimMetrics.metrics?.chatCount || 0,
        uptime_s: shimMetrics.uptime_s || 0,
        memory: shimMetrics.memory || {},
        container_health: containerHealth,
      },
    });
  } catch (err) {
    console.error("[network] Heartbeat failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 3. Message polling (every 60 s)
// ---------------------------------------------------------------------------
let lastMessageTs = null;

async function pollMessages() {
  try {
    const params = lastMessageTs ? `?since=${lastMessageTs}` : "";
    const data = await api("GET", `/messages/${agentId}${params}`);
    const messages = data.messages || [];
    for (const msg of messages) {
      console.log(`[network] Message from ${msg.from_agent}: ${msg.type}`);
      // Inject into chat-shim context (log as experience)
      memory.logExperience(
        msg.type === "coaching" ? "coaching" : "chat",
        `Peer message from ${msg.from_agent}: ${JSON.stringify(msg.payload)}`,
        [msg.from_agent]
      );
      lastMessageTs = msg.ts;
    }
  } catch (err) {
    console.error("[network] Message poll failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 4. Schedule sync (every 5 min)
// ---------------------------------------------------------------------------
async function syncSchedule() {
  try {
    const data = await api(
      "GET",
      `/calendar/events?participant=${agentId}&status=confirmed`
    );
    const events = data.events || [];
    memory.syncEvents(events);
    console.log(`[network] Synced ${events.length} calendar events`);
  } catch (err) {
    console.error("[network] Schedule sync failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 5. Knowledge sharing (daily)
// ---------------------------------------------------------------------------
async function shareKnowledge() {
  try {
    const experiences = memory.recentExperiences(50);
    // Select top learnings with non-null learnings field
    const learnings = experiences
      .filter((e) => e.learnings)
      .slice(0, 5);

    for (const exp of learnings) {
      await api("POST", "/knowledge/contribute", {
        contributor_id: agentId,
        category: exp.type === "coaching" ? "strategy" : "audience",
        content: `${exp.summary} — Learning: ${exp.learnings}`,
      });
    }
    console.log(`[network] Shared ${learnings.length} knowledge entries`);
  } catch (err) {
    console.error("[network] Knowledge sharing failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 6. Governance check (daily)
// ---------------------------------------------------------------------------
async function checkGovernance() {
  try {
    const data = await api("GET", "/governance/proposals?status=open");
    const proposals = data.proposals || [];
    for (const p of proposals) {
      console.log(`[network] Open proposal: ${p.title} (${p.proposal_id})`);
      // Agents can view but only orchestrators vote
    }
  } catch (err) {
    console.error("[network] Governance check failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 7. Evolution review (weekly)
// ---------------------------------------------------------------------------
async function evolutionReview() {
  try {
    // Query network for peer strategies
    const data = await api("POST", "/knowledge/query", {
      query: "engagement improvement strategies",
    });
    const entries = data.results || [];
    if (entries.length) {
      console.log(
        `[network] Evolution: found ${entries.length} peer strategies`
      );
      memory.logExperience(
        "coaching",
        `Weekly evolution review: ${entries.length} peer strategies reviewed`,
        [],
        "reviewed",
        entries
          .slice(0, 3)
          .map((e) => e.content)
          .join("; ")
      );
    }
  } catch (err) {
    console.error("[network] Evolution review failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 8. Hourly metrics logging
// ---------------------------------------------------------------------------
async function logMetrics() {
  try {
    const res = await fetch(`${CHAT_SHIM_URL}/health`);
    const data = await res.json();
    memory.logExperience(
      "maintenance",
      `Hourly metrics: chats=${data.metrics?.chatCount || 0}, uptime=${data.uptime_s || 0}s`,
      [],
      "logged"
    );
  } catch { /* skip if chat-shim not ready */ }
}

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------
async function main() {
  console.log(`[network] Connecting to ${NETWORK_URL} as ${agentId} …`);

  await register();
  await syncSchedule();

  // Heartbeat + message polling every 60 s
  setInterval(heartbeat, 60_000);
  setInterval(pollMessages, 60_000);

  // Schedule sync every 5 min
  setInterval(syncSchedule, 5 * 60_000);

  // Hourly metrics logging
  setInterval(logMetrics, 60 * 60_000);

  // Daily knowledge sharing + governance check
  setInterval(shareKnowledge, 24 * 60 * 60_000);
  setInterval(checkGovernance, 24 * 60 * 60_000);

  // Weekly evolution review
  setInterval(evolutionReview, 7 * 24 * 60 * 60_000);

  // Initial heartbeat
  await heartbeat();
  console.log("[network] Client running");
}

main().catch((err) => {
  console.error("[network] Fatal:", err);
  process.exit(1);
});
