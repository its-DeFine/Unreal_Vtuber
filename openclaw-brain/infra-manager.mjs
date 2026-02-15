/**
 * infra-manager.mjs — Monitors sibling containers via the Docker socket and
 * takes safe auto-actions (restart crashed containers) while escalating risky
 * changes through the governance proposal flow.
 */

import Dockerode from "dockerode";
import express from "express";

const AVATAR_SLUG = process.env.AVATAR_SLUG || "default";
const NETWORK_URL = process.env.AGENT_NETWORK_URL || "";
const NETWORK_TOKEN = process.env.AGENT_NETWORK_TOKEN || "";
const INFRA_PORT = parseInt(process.env.INFRA_PORT || "18802", 10);
const CHECK_INTERVAL_MS = 30_000;

// Container name prefixes we manage for this instance
const SIBLING_PREFIX = `vtuber-${AVATAR_SLUG}-`;

// Actions classified by risk level
const SAFE_ACTIONS = new Set(["restart", "clear_logs", "report_metrics"]);
const RISKY_ACTIONS = new Set([
  "update_env",
  "update_image",
  "modify_ports",
  "scale_resources",
]);

let docker;
try {
  docker = new Dockerode({ socketPath: "/var/run/docker.sock" });
} catch (err) {
  console.warn("[infra] Docker socket not available:", err.message);
}

const app = express();
app.use(express.json());

// ---------------------------------------------------------------------------
// Container inspection
// ---------------------------------------------------------------------------
async function listSiblings() {
  if (!docker) return [];
  const containers = await docker.listContainers({ all: true });
  return containers.filter((c) =>
    c.Names.some((n) => n.replace(/^\//, "").startsWith(SIBLING_PREFIX))
  );
}

async function containerHealth() {
  const siblings = await listSiblings();
  return siblings.map((c) => ({
    name: c.Names[0]?.replace(/^\//, ""),
    state: c.State,
    status: c.Status,
    image: c.Image,
  }));
}

// ---------------------------------------------------------------------------
// Safe auto-actions
// ---------------------------------------------------------------------------
async function restartContainer(name) {
  if (!docker) throw new Error("Docker socket not available");
  const container = docker.getContainer(name);
  await container.restart({ t: 10 });
  console.log(`[infra] Auto-restarted ${name}`);
  return { action: "restart", target: name, result: "ok" };
}

// ---------------------------------------------------------------------------
// Periodic health check — auto-restart exited containers
// ---------------------------------------------------------------------------
async function healthCheckLoop() {
  while (true) {
    try {
      const siblings = await listSiblings();
      for (const c of siblings) {
        const name = c.Names[0]?.replace(/^\//, "");
        if (c.State === "exited" || c.State === "dead") {
          console.log(`[infra] Container ${name} is ${c.State}; auto-restarting …`);
          try {
            await restartContainer(name);
          } catch (err) {
            console.error(`[infra] Failed to restart ${name}:`, err.message);
          }
        }
      }
    } catch (err) {
      console.error("[infra] Health check error:", err.message);
    }
    await new Promise((r) => setTimeout(r, CHECK_INTERVAL_MS));
  }
}

// ---------------------------------------------------------------------------
// Governance escalation for risky actions
// ---------------------------------------------------------------------------
async function submitGovernanceProposal(action, details) {
  if (!NETWORK_URL) {
    return { status: "no_network", message: "Cannot escalate — network not configured" };
  }
  try {
    const res = await fetch(`${NETWORK_URL}/api/v1/governance/proposals`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${NETWORK_TOKEN}`,
      },
      body: JSON.stringify({
        type: "infra_change",
        title: `Infra: ${action}`,
        description: details,
        payload: { action, avatar_slug: AVATAR_SLUG },
      }),
    });
    return await res.json();
  } catch (err) {
    return { status: "error", message: err.message };
  }
}

// ---------------------------------------------------------------------------
// HTTP API (used by chat-shim)
// ---------------------------------------------------------------------------
app.get("/status", async (_req, res) => {
  try {
    const health = await containerHealth();
    res.json({ avatar_slug: AVATAR_SLUG, containers: health });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/action", async (req, res) => {
  const { action, target, details } = req.body;
  if (!action) {
    return res.status(400).json({ error: "action is required" });
  }

  if (SAFE_ACTIONS.has(action)) {
    try {
      if (action === "restart" && target) {
        const result = await restartContainer(target);
        return res.json(result);
      }
      return res.json({ action, result: "ok" });
    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  if (RISKY_ACTIONS.has(action)) {
    const proposal = await submitGovernanceProposal(
      action,
      details || `Risky infra action: ${action} on ${target || AVATAR_SLUG}`
    );
    return res.json({
      action,
      status: "pending_approval",
      proposal,
    });
  }

  res.status(400).json({ error: `Unknown action: ${action}` });
});

// ---------------------------------------------------------------------------
app.listen(INFRA_PORT, () => {
  console.log(`[infra] listening on :${INFRA_PORT}  avatar=${AVATAR_SLUG}`);
});

// Start background health-check loop
healthCheckLoop();
