/**
 * chat-shim.mjs — Express server wrapping the OpenClaw gateway.
 *
 * Provides the /chat endpoint expected by the existing _openclaw_chat
 * contract, plus auxiliary endpoints for scheduling, infrastructure,
 * network, and governance.
 */

import express from "express";
import { spawn } from "node:child_process";
import { MemoryDB } from "./long-term-memory.mjs";

const PORT = parseInt(process.env.OPENCLAW_CHAT_PORT || "18801", 10);
const GATEWAY = process.env.OPENCLAW_GATEWAY_URL || "http://localhost:18789";
const NETWORK_URL = process.env.AGENT_NETWORK_URL || "";
const NETWORK_TOKEN = process.env.AGENT_NETWORK_TOKEN || "";
const AGENT_NAME = process.env.AGENT_NAME || "agent";

const app = express();
app.use(express.json());

const startedAt = Date.now();
const memory = new MemoryDB();

// Track basic metrics
let metrics = { chatCount: 0, lastChat: null };

// ---------------------------------------------------------------------------
// POST /chat — matches existing _openclaw_chat contract
// ---------------------------------------------------------------------------
app.post("/chat", async (req, res) => {
  try {
    const { message, author, conversation_id } = req.body;
    if (!message) {
      return res.status(400).json({ error: "message is required" });
    }

    // Build context from long-term memory
    const relationship = author
      ? memory.getRelationship(author)
      : null;
    const recentExperiences = memory.recentExperiences(5);
    const contextParts = [];

    if (relationship) {
      contextParts.push(
        `[Memory] You have spoken with ${relationship.name} ${relationship.interaction_count} times. Sentiment: ${relationship.sentiment}. Notes: ${relationship.notes || "none"}`
      );
    }
    if (recentExperiences.length) {
      contextParts.push(
        `[Recent experiences] ${recentExperiences.map((e) => e.summary).join("; ")}`
      );
    }

    const enrichedMessage = contextParts.length
      ? `${contextParts.join("\n")}\n\n${message}`
      : message;

    // Forward to OpenClaw gateway
    let responseText;
    try {
      const gwRes = await fetch(`${GATEWAY}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: enrichedMessage,
          author,
          conversation_id,
        }),
      });
      const data = await gwRes.json();
      responseText = data.response || data.message || JSON.stringify(data);
    } catch {
      // Gateway not available — echo stub
      responseText = `[${AGENT_NAME}] I'm still warming up. Please try again in a moment.`;
    }

    // Update relationship tracking
    if (author) {
      memory.upsertRelationship(author, "human", author);
    }

    metrics.chatCount++;
    metrics.lastChat = new Date().toISOString();

    res.json({ response: responseText });
  } catch (err) {
    console.error("[chat] error:", err);
    res.status(500).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// GET /health
// ---------------------------------------------------------------------------
app.get("/health", (_req, res) => {
  const memStats = memory.stats();
  res.json({
    status: "ok",
    agent: AGENT_NAME,
    uptime_s: Math.floor((Date.now() - startedAt) / 1000),
    metrics,
    memory: memStats,
    network_connected: !!NETWORK_URL,
  });
});

// ---------------------------------------------------------------------------
// POST /coaching — receive coaching directives
// ---------------------------------------------------------------------------
app.post("/coaching", (req, res) => {
  const { directive, priority } = req.body;
  if (!directive) {
    return res.status(400).json({ error: "directive is required" });
  }
  memory.logExperience("coaching", directive, [], priority || "medium");
  memory.updateBehavior("coaching", directive);
  res.json({ acknowledged: true });
});

// ---------------------------------------------------------------------------
// Schedule endpoints — proxy to network or return local cache
// ---------------------------------------------------------------------------
app.get("/schedule", async (_req, res) => {
  const events = memory.upcomingEvents();
  res.json({ events });
});

app.post("/schedule/book", async (req, res) => {
  if (!NETWORK_URL) {
    return res.status(503).json({ error: "Network not configured" });
  }
  try {
    const nRes = await fetch(`${NETWORK_URL}/api/v1/calendar/book`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${NETWORK_TOKEN}`,
      },
      body: JSON.stringify(req.body),
    });
    const data = await nRes.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// Infrastructure endpoints
// ---------------------------------------------------------------------------
app.get("/infra/status", async (_req, res) => {
  try {
    const infraRes = await fetch("http://localhost:18802/status");
    const data = await infraRes.json();
    res.json(data);
  } catch {
    res.json({ status: "infra-manager not available" });
  }
});

app.post("/infra/action", async (req, res) => {
  try {
    const infraRes = await fetch("http://localhost:18802/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await infraRes.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// Network proxy endpoints
// ---------------------------------------------------------------------------
app.get("/network/peers", async (_req, res) => {
  if (!NETWORK_URL) {
    return res.json({ peers: [] });
  }
  try {
    const nRes = await fetch(`${NETWORK_URL}/api/v1/agents`, {
      headers: { Authorization: `Bearer ${NETWORK_TOKEN}` },
    });
    const data = await nRes.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get("/network/knowledge", async (req, res) => {
  if (!NETWORK_URL) {
    return res.json({ results: [] });
  }
  try {
    const nRes = await fetch(`${NETWORK_URL}/api/v1/knowledge/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${NETWORK_TOKEN}`,
      },
      body: JSON.stringify({ query: req.query.q || "" }),
    });
    const data = await nRes.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// Governance proxy
// ---------------------------------------------------------------------------
app.post("/governance/propose", async (req, res) => {
  if (!NETWORK_URL) {
    return res.status(503).json({ error: "Network not configured" });
  }
  try {
    const nRes = await fetch(`${NETWORK_URL}/api/v1/governance/proposals`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${NETWORK_TOKEN}`,
      },
      body: JSON.stringify(req.body),
    });
    const data = await nRes.json();
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`[chat-shim] listening on :${PORT}  agent=${AGENT_NAME}`);
});
