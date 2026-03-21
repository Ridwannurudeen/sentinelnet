interface SentinelNetOptions {
  baseUrl?: string;
  timeout?: number;
}

interface TrustScore {
  agent_id: number;
  wallet: string;
  trust_score: number;
  trust_score_raw?: number;
  longevity: number;
  activity: number;
  counterparty: number;
  contract_risk: number;
  agent_identity: number;
  verdict: "TRUST" | "CAUTION" | "REJECT";
  sybil_flagged: boolean;
  contagion_adjustment: number;
  explanation?: {
    summary: string;
    factors: string[];
  };
  [key: string]: any;
}

interface StatsResponse {
  agents_scored: number;
  avg_trust_score: number;
  min_trust_score: number;
  max_trust_score: number;
  verdicts: Record<string, number>;
  distribution: Record<string, number>;
  sybil_flagged: number;
  stale_scores: number;
  contagion_affected: number;
}

interface BatchResponse {
  results: Record<string, TrustScore | null>;
  queried: number;
  found: number;
}

interface ThreatEvent {
  id: number;
  threat_type: string;
  severity: string;
  agent_id: number;
  details: string;
  created_at: string;
}

declare class SentinelNet {
  constructor(options?: SentinelNetOptions);
  health(): Promise<{ status: string; service: string; version: string }>;
  getTrust(agentId: number): Promise<TrustScore>;
  getScores(applyDecay?: boolean): Promise<{ scores: TrustScore[]; total: number; verdicts: Record<string, number>; sybil_flagged: number }>;
  getStats(): Promise<StatsResponse>;
  getHistory(agentId: number, limit?: number): Promise<{ agent_id: number; history: TrustScore[]; entries: number }>;
  getGraph(agentId: number): Promise<{ agent_id: number; neighbors: any[]; total_neighbors: number }>;
  batchTrust(agentIds: number[]): Promise<BatchResponse>;
  getThreats(limit?: number): Promise<{ threats: ThreatEvent[]; count: number }>;
  getGraphData(): Promise<{ nodes: any[]; links: any[] }>;
  badgeUrl(agentId: number): string;
  isTrusted(agentId: number): Promise<boolean>;
  trustGate(agentId: number, minScore?: number): Promise<boolean>;
}

export default SentinelNet;
export { SentinelNet, SentinelNetOptions, TrustScore, StatsResponse, BatchResponse, ThreatEvent };
