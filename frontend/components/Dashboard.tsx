"use client";

import React from "react";
import type { DecisionTrace, Decision } from "@/lib/api";
import { CheckCircle2, XCircle, AlertTriangle, Shield } from "lucide-react";

const DECISION_CONFIG: Record<Decision, { label: string; class: string; Icon: React.FC<{ size?: number }> }> = {
  PROCEED:     { label: "PROCEED", class: "badge-proceed",   Icon: CheckCircle2 },
  "HIGH-RISK": { label: "HIGH-RISK", class: "badge-highrisk", Icon: XCircle      },
  REVIEW:      { label: "REVIEW",  class: "badge-review",    Icon: AlertTriangle },
};

// ── Top Decision Hero ─────────────────────────────────────────

export function DecisionHero({ trace }: { trace: DecisionTrace }) {
  const cfg = DECISION_CONFIG[trace.decision];
  const Icon = cfg.Icon;
  const score = trace.final_score ?? 0;
  const confidence = Math.round((trace.final_confidence ?? 0) * 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <div>
          <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "var(--space-1)" }}>
            Startup Evaluation
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <span className={`badge ${cfg.class}`} style={{ fontSize: "0.95rem", padding: "6px 14px" }}>
              <Icon size={16} /> {cfg.label}
            </span>
            <span style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
              {score.toFixed(0)} <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}>/ 100</span>
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-6)" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span className="kv-label">Confidence</span>
            <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)" }}>
              {confidence}%
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span className="kv-label">Uncertainty</span>
            <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-secondary)" }}>
              ±{(trace.final_score_uncertainty ?? 0).toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      {trace.red_team_flag && (
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-md)",
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          color: "var(--danger-text)", fontSize: "0.88rem"
        }}>
          <Shield size={16} />
          <span>Red Team flagged <strong>{trace.red_team_severity?.toUpperCase()}</strong> risk: {trace.red_team_reasoning}</span>
        </div>
      )}
    </div>
  );
}

// ── Domain Analysis Bars ──────────────────────────────────────

export function DomainAnalysisBars({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {domains.map(d => {
        const score = trace.agent_scores?.[d] ?? 0;
        return (
          <div key={d} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.9rem" }}>
              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{d}</span>
              <span style={{ fontWeight: 700, color: "var(--text-primary)", fontFamily: "JetBrains Mono, monospace" }}>
                {score.toFixed(0)}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Digital Twin Component ───────────────────────────────────

export function DigitalTwinView({ dt }: { dt?: Record<string, unknown> | null }) {
  const fields = [
    { key: "industry", label: "Industry" },
    { key: "location", label: "Location" },
    { key: "budget", label: "Budget" },
    { key: "business_model_summary", label: "Business Model" },
    { key: "team_size", label: "Team Size" },
    { key: "revenue_model", label: "Revenue Model" },
    { key: "target_market", label: "Target Market" },
    { key: "competitive_advantage", label: "Competitive Advantage" },
    { key: "regulatory_environment", label: "Regulatory Environment" },
    { key: "tech_stack", label: "Technology Stack" },
    { key: "traction", label: "Traction" },
  ];

  function formatVal(val: unknown): string {
    if (val === null || val === undefined || val === "") return "Not provided";
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  }

  const twinObj = dt || {};

  return (
    <div className="kv-grid">
      {fields.map(f => {
        const rawVal = twinObj[f.key];
        const val = formatVal(rawVal);
        const isMissing = val === "Not provided";
        return (
          <div key={f.key} className="kv-item">
            <span className="kv-label">{f.label}</span>
            <span className="kv-value" style={{ color: isMissing ? "var(--text-muted)" : "var(--text-primary)", fontStyle: isMissing ? "italic" : "normal" }}>
              {val}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Compact Agent Cards ──────────────────────────────────────

export function CompactAgentCards({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
      {domains.map(d => {
        const score = trace.agent_scores?.[d];
        const weight = trace.agent_weights?.[d];
        const conf = trace.agent_confidences?.[d];
        const claim = trace.agent_claims?.[d];

        return (
          <div key={d} className="card" style={{ padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text-primary)" }}>{d}</span>
              <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "JetBrains Mono, monospace" }}>
                {score !== undefined ? score.toFixed(0) : "—"}
              </span>
            </div>

            <div style={{ display: "flex", gap: "var(--space-4)", fontSize: "0.8rem", color: "var(--text-muted)", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)", padding: "6px 0" }}>
              <span>Weight: <strong style={{ color: "var(--text-secondary)" }}>{weight !== undefined ? (weight * 100).toFixed(0) + "%" : "—"}</strong></span>
              <span>Confidence: <strong style={{ color: "var(--text-secondary)" }}>{conf !== undefined ? (conf * 100).toFixed(0) + "%" : "—"}</strong></span>
            </div>

            <div>
              <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 2 }}>
                Claim
              </span>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                {claim ? `"${claim}"` : "No claim recorded."}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Evidence Section ──────────────────────────────────────────

export function EvidenceSection({ trace }: { trace: DecisionTrace }) {
  const cases = trace.retrieved_cases;
  const ids = trace.retrieved_case_ids;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div>
        <h3 style={{ marginBottom: "var(--space-1)" }}>Historical Evidence</h3>
        <p style={{ fontSize: "0.88rem", color: "var(--text-muted)" }}>
          Relevant historical cases retrieved by AIRB.
        </p>
      </div>

      {cases && cases.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {cases.map((c, i) => {
            const cid = String(c.case_id ?? `CASE-${i + 1}`);
            const outcome = String(c.outcome ?? "UNKNOWN").toUpperCase();
            const risk = String(c.primary_risk_category ?? "General");
            const summary = String(c.root_cause_summary ?? "");
            const rawText = String(c.raw_text ?? "");
            const similarity = typeof c.similarity_score === "number"
              ? (c.similarity_score * 100).toFixed(0) + "%"
              : null;

            const isSuccess = outcome === "SUCCESS";
            const isFailed = outcome === "FAILED";

            return (
              <div key={cid} className="card" style={{ padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)", fontFamily: "JetBrains Mono, monospace" }}>
                      {cid}
                    </span>
                    {Boolean(c.industry) && (
                      <span className="domain-chip">
                        {String(c.industry)}
                      </span>
                    )}
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                      Risk: <strong style={{ color: "var(--text-secondary)" }}>{risk}</strong>
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    {similarity && (
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        Similarity: <strong style={{ color: "var(--text-primary)" }}>{similarity}</strong>
                      </span>
                    )}
                    <span className={`badge ${isSuccess ? "badge-proceed" : isFailed ? "badge-highrisk" : "badge-review"}`}>
                      {outcome}
                    </span>
                  </div>
                </div>

                {summary && (
                  <div style={{ marginTop: "var(--space-1)" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block" }}>
                      Root Cause
                    </span>
                    <p style={{ fontSize: "0.88rem", fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
                      {summary}
                    </p>
                  </div>
                )}

                {rawText && (
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5, margin: 0 }}>
                    {rawText}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      ) : ids && ids.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {ids.map(cid => (
            <div key={cid} className="card" style={{ padding: "var(--space-3) var(--space-4)" }}>
              <code style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>{cid}</code>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          No historical cases retrieved for this evaluation.
        </p>
      )}
    </div>
  );
}

// ── Clean Board Transcript ────────────────────────────────────

export function BoardTranscript({ trace }: { trace: DecisionTrace }) {
  const steps = [
    { label: "Pitch Received", done: !!trace.startup_pitch },
    { label: "Digital Twin", done: !!trace.digital_twin },
    { label: "Evidence Retrieved", done: (trace.retrieved_case_ids?.length ?? 0) > 0 || (trace.retrieved_cases?.length ?? 0) > 0 },
    { label: "Finance Agent", done: trace.agent_scores?.Finance !== undefined },
    { label: "Legal Agent", done: trace.agent_scores?.Legal !== undefined },
    { label: "Market Agent", done: trace.agent_scores?.Market !== undefined },
    { label: "Operations Agent", done: trace.agent_scores?.Operations !== undefined },
    { label: "Technology Agent", done: trace.agent_scores?.Technology !== undefined },
    { label: "Fusion", done: trace.final_score !== undefined },
    { label: "Red Team", done: true },
    { label: "Final Decision", done: !!trace.decision },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {steps.map((s, idx) => (
        <div key={idx} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", fontSize: "0.9rem" }}>
          <span style={{ color: s.done ? "var(--success)" : "var(--border-dark)", fontWeight: 700 }}>
            {s.done ? "✓" : "○"}
          </span>
          <span style={{ color: s.done ? "var(--text-primary)" : "var(--text-muted)", fontWeight: s.done ? 500 : 400 }}>
            {s.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Technical Reproducibility ─────────────────────────────────

export function VersionInfo({ trace }: { trace: DecisionTrace }) {
  const v = trace.version_info ?? {};

  const items = [
    { label: "Evaluation ID", val: trace.evaluation_id },
    { label: "Model", val: String(v.model_worker ?? "openai/gpt-oss-120b") },
    { label: "Dataset", val: String(v.dataset_version ?? "v1.0") },
    { label: "Prompt Version", val: String(v.prompt_template_version ?? "v1.0") },
    { label: "Embedding Model", val: "all-MiniLM-L6-v2" },
    { label: "Decision Threshold", val: "PROCEED ≥ 70, REVIEW 50-69, HIGH-RISK < 50" },
    { label: "Calibration Version", val: "Uncalibrated" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div className="kv-grid">
        {items.map(i => (
          <div key={i.label} className="kv-item">
            <span className="kv-label">{i.label}</span>
            <span className="kv-value" style={{ fontFamily: i.label === "Evaluation ID" ? "JetBrains Mono, monospace" : "inherit" }}>
              {i.val}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Sensitivity Sweep ────────────────────────────────────────

export function SensitivitySweep({ trace }: { trace: DecisionTrace }) {
  if (!trace.sensitivity_sweep?.length) return null;
  const originalDecision = trace.decision;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
      {trace.sensitivity_sweep.map((pt, i) => {
        const isFlip = pt.decision !== originalDecision;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-md)", background: "var(--bg-elevated)", border: `1px solid ${isFlip ? "var(--warning-border)" : "var(--border)"}` }}>
            <code style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>{String(pt.variable_value)}</code>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Score: {pt.final_score.toFixed(1)}</span>
            <span className={`badge ${DECISION_CONFIG[pt.decision as Decision]?.class ?? "badge-neutral"}`}>{pt.decision}</span>
          </div>
        );
      })}
    </div>
  );
}
