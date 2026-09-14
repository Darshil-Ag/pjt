/**
 * AIRB API Client
 * Wraps all backend endpoints. All functions are type-safe and handle errors gracefully.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Types ────────────────────────────────────────────────────

export type Decision = "PROCEED" | "HIGH-RISK" | "REVIEW";

export interface EvaluateResponse {
  evaluation_id: string;
  status: "running" | "hitl_pending" | "complete" | "error";
  message: string;
}

export interface AgentBreakdown {
  score: number;
  confidence: number;
  weight: number;
  claim: string;
  cited_case_ids: string[];
}

export interface SweepPoint {
  variable_value: number | string;
  final_score: number;
  decision: Decision;
}

export interface DecisionTrace {
  evaluation_id: string;
  startup_pitch: string;
  digital_twin: Record<string, unknown>;
  retrieved_case_ids: string[];
  agent_scores: Record<string, number>;
  agent_confidences: Record<string, number>;
  agent_weights: Record<string, number>;
  agent_claims: Record<string, string>;
  agent_citations: Record<string, string[]>;
  conflict_index: number;
  hitl_triggered: boolean;
  hitl_question?: string;
  hitl_answer?: string;
  hitl_ci_before?: number;
  hitl_ci_after?: number;
  hitl_effectiveness?: number;
  final_score: number;
  final_confidence: number;
  final_score_uncertainty: number;
  decision: Decision;
  sensitivity_sweep?: SweepPoint[];
  red_team_flag: boolean;
  red_team_severity?: "low" | "medium" | "high";
  red_team_reasoning?: string;
  version_info: Record<string, unknown>;
}

// ── Helpers ──────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── API Functions ────────────────────────────────────────────

export async function submitPitch(pitch: string): Promise<EvaluateResponse> {
  return request<EvaluateResponse>("/evaluate", {
    method: "POST",
    body: JSON.stringify({ startup_pitch: pitch }),
  });
}

export async function respondToHITL(
  evaluationId: string,
  answer: string
): Promise<{ evaluation_id: string; status: string; message: string }> {
  return request("/hitl-respond", {
    method: "POST",
    body: JSON.stringify({ evaluation_id: evaluationId, answer }),
  });
}

export async function getDecision(evaluationId: string): Promise<DecisionTrace> {
  return request<DecisionTrace>(`/decision/${evaluationId}`);
}

export async function replayEvaluation(evaluationId: string): Promise<DecisionTrace> {
  return request<DecisionTrace>(`/replay/${evaluationId}`);
}

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const baseUrl = API_BASE.replace(/\/api\/v1\/?$/, "");
  const res = await fetch(`${baseUrl}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

