/**
 * SentinelNet JavaScript SDK
 * Trust scoring for ERC-8004 agents on Base.
 *
 * @example
 * const sn = new SentinelNet();
 * const score = await sn.getTrust(31253);
 * console.log(score.verdict); // "TRUST" | "CAUTION" | "REJECT"
 */

const DEFAULT_BASE_URL = "https://sentinelnet.gudman.xyz";

class SentinelNet {
  /**
   * @param {Object} [options]
   * @param {string} [options.baseUrl] - API base URL
   * @param {number} [options.timeout] - Request timeout in ms (default: 30000)
   */
  constructor({ baseUrl = DEFAULT_BASE_URL, timeout = 30000 } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.timeout = timeout;
  }

  async _fetch(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        signal: controller.signal,
        ...options,
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`SentinelNet API error ${res.status}: ${body}`);
      }
      return res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  /** Check API health. */
  async health() {
    return this._fetch("/api/health");
  }

  /**
   * Get trust score for an agent.
   * @param {number} agentId
   * @returns {Promise<Object>} Trust score with verdict, explanation, dimensions
   */
  async getTrust(agentId) {
    return this._fetch(`/trust/${agentId}`);
  }

  /**
   * Get all scored agents with verdict breakdown.
   * @param {boolean} [applyDecay=true]
   */
  async getScores(applyDecay = true) {
    return this._fetch(`/api/scores?apply_decay=${applyDecay}`);
  }

  /** Get aggregate trust statistics. */
  async getStats() {
    return this._fetch("/api/stats");
  }

  /**
   * Get scoring history for an agent.
   * @param {number} agentId
   * @param {number} [limit=50]
   */
  async getHistory(agentId, limit = 50) {
    return this._fetch(`/trust/${agentId}/history?limit=${limit}`);
  }

  /**
   * Get an agent's counterparty trust neighborhood.
   * @param {number} agentId
   */
  async getGraph(agentId) {
    return this._fetch(`/trust/graph/${agentId}`);
  }

  /**
   * Query trust scores for multiple agents at once (max 100).
   * @param {number[]} agentIds
   */
  async batchTrust(agentIds) {
    return this._fetch("/trust/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_ids: agentIds }),
    });
  }

  /**
   * Get real-time threat intelligence feed.
   * @param {number} [limit=50]
   */
  async getThreats(limit = 50) {
    return this._fetch(`/api/threats?limit=${limit}`);
  }

  /** Get full agent interaction graph (nodes + links). */
  async getGraphData() {
    return this._fetch("/api/graph-data");
  }

  /**
   * Get embeddable SVG badge URL for an agent.
   * @param {number} agentId
   * @returns {string}
   */
  badgeUrl(agentId) {
    return `${this.baseUrl}/badge/${agentId}.svg`;
  }

  /**
   * Quick check: is this agent trusted?
   * @param {number} agentId
   * @returns {Promise<boolean>}
   */
  async isTrusted(agentId) {
    try {
      const score = await this.getTrust(agentId);
      return score.verdict === "TRUST";
    } catch {
      return false;
    }
  }

  /**
   * Gate an interaction: only proceed if agent meets minimum trust score.
   * @param {number} agentId
   * @param {number} [minScore=55]
   * @returns {Promise<boolean>}
   */
  async trustGate(agentId, minScore = 55) {
    try {
      const score = await this.getTrust(agentId);
      return (score.trust_score || 0) >= minScore && !score.sybil_flagged;
    } catch {
      return false;
    }
  }
}

// Support both CommonJS and ESM
if (typeof module !== "undefined" && module.exports) {
  module.exports = SentinelNet;
  module.exports.SentinelNet = SentinelNet;
  module.exports.default = SentinelNet;
}

export default SentinelNet;
export { SentinelNet };
