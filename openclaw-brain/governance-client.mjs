/**
 * governance-client.mjs — Governance participation module.
 *
 * Allows the agent to submit proposals to the network, monitor outcomes,
 * and auto-apply approved proposals that affect this agent.
 */

const NETWORK_URL = process.env.AGENT_NETWORK_URL || "";
const NETWORK_TOKEN = process.env.AGENT_NETWORK_TOKEN || "";
const AGENT_ID = `${process.env.AVATAR_SLUG || "default"}-${process.env.AGENT_NAME || "agent"}`;

export class GovernanceClient {
  /**
   * Submit a proposal to the network.
   */
  async submitProposal(type, title, description, payload = {}) {
    if (!NETWORK_URL) {
      return { error: "Network not configured" };
    }
    try {
      const res = await fetch(`${NETWORK_URL}/api/v1/governance/proposals`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${NETWORK_TOKEN}`,
        },
        body: JSON.stringify({
          proposer_id: AGENT_ID,
          type,
          title,
          description,
          payload,
        }),
      });
      return await res.json();
    } catch (err) {
      return { error: err.message };
    }
  }

  /**
   * List proposals, optionally filtered by status.
   */
  async listProposals(status = null) {
    if (!NETWORK_URL) return [];
    try {
      const params = status ? `?status=${status}` : "";
      const res = await fetch(
        `${NETWORK_URL}/api/v1/governance/proposals${params}`,
        { headers: { Authorization: `Bearer ${NETWORK_TOKEN}` } }
      );
      const data = await res.json();
      return data.proposals || [];
    } catch (err) {
      console.error("[governance] List failed:", err.message);
      return [];
    }
  }

  /**
   * Check for approved proposals that affect this agent and should be applied.
   */
  async checkApprovedProposals() {
    const proposals = await this.listProposals("approved");
    const applicable = [];

    for (const p of proposals) {
      // Check if this proposal targets this agent or is network-wide
      const payload = p.payload || {};
      const targetSlug = payload.avatar_slug;
      const avatarSlug = process.env.AVATAR_SLUG || "default";

      if (!targetSlug || targetSlug === avatarSlug || targetSlug === "all") {
        applicable.push(p);
      }
    }

    return applicable;
  }

  /**
   * Apply an approved proposal locally.
   * Returns a description of what was applied.
   */
  async applyProposal(proposal) {
    const type = proposal.type;
    const payload = proposal.payload || {};

    switch (type) {
      case "skill_addition":
        return this._applySkillAddition(payload);
      case "config_change":
        return this._applyConfigChange(payload);
      case "policy_update":
        return this._applyPolicyUpdate(payload);
      case "infra_change":
        // Infra changes are handled by infra-manager
        return { applied: false, reason: "infra changes handled by infra-manager" };
      default:
        return { applied: false, reason: `Unknown proposal type: ${type}` };
    }
  }

  _applySkillAddition(payload) {
    // Write skill file to workspace
    const { skill_name, skill_content } = payload;
    if (!skill_name || !skill_content) {
      return { applied: false, reason: "Missing skill_name or skill_content" };
    }
    try {
      const fs = await import("node:fs");
      const path = `/workspace/skills/${skill_name}.md`;
      fs.writeFileSync(path, skill_content);
      console.log(`[governance] Applied skill addition: ${skill_name}`);
      return { applied: true, action: `Added skill: ${skill_name}` };
    } catch (err) {
      return { applied: false, reason: err.message };
    }
  }

  _applyConfigChange(payload) {
    console.log(`[governance] Config change proposal noted:`, payload);
    return { applied: true, action: "Config change logged" };
  }

  _applyPolicyUpdate(payload) {
    console.log(`[governance] Policy update proposal noted:`, payload);
    return { applied: true, action: "Policy update logged" };
  }
}
