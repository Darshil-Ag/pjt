"use client";

import React from "react";
import type { DecisionTrace, Decision } from "@/lib/api";
import { CheckCircle, XCircle, AlertTriangle, Shield, Info } from "lucide-react";

const DOMAIN_COLORS: Record<string, string> = {
  Finance:    "#3fb950",
  Legal:      "#d29922",
  Market:     "#58a6ff",
  Operations: "#f0883e",
  Technology: "#bc8cff",
};

const DECISION_CONFIG: Record<Decision, { label: string; class: string; Icon: React.FC<{ size?: number }> }> = {
  PROCEED:    { label: "Proceed", class: "badge-proceed",   Icon: CheckCircle   },
  "HIGH-RISK":{ label: "High Risk", class: "badge-highrisk", Icon: XCircle      },
  REVIEW:     { label: "Review",  class: "badge-review",    Icon: AlertTriangle },
};

// ── Decision Hero ────────────────────────────────────────────

export function DecisionHero({ trace }: { trace: DecisionTrace }) {
  const cfg = DECISION_CONFIG[trace.decision];
  const Icon = cfg.Icon;
  const score = trace.final_score ?? 0;
  const band  = trace.final_score_uncertainty ?? 0;

  // SVG ring
  const R = 64, circumference = 2 * Math.PI * R;
  const dashOffset = circumference - (score / 100) * circumference;
  const ringColor =
    trace.decision === "PROCEED"    ? "var(--success)" :
    trace.decision === "HIGH-RISK"  ? "var(--danger)"  : "var(--warning)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-6)", padding: "var(--space-8) 0" }}>
      {/* Score ring */}
      <div style={{ position: "relative", width: 160, height: 160 }}>
        <svg width={160} height={160} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={80} cy={80} r={R} fill="none" stroke="var(--bg-elevated)" strokeWidth={10} />
          <circle
            cx={80} cy={80} r={R} fill="none"
            stroke={ringColor} strokeWidth={10}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease, stroke 0.4s ease", filter: `drop-shadow(0 0 8px ${ringColor})` }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"
        }}>
          <span style={{ fontSize: "2.4rem", fontWeight: 800, lineHeight: 1, color: "var(--text-primary)" }}>
            {score.toFixed(0)}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>± {band.toFixed(1)}</span>
        </div>
      </div>

      {/* Decision badge */}
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
        <span className={`badge ${cfg.class}`} style={{ fontSize: "0.9rem", padding: "6px 16px" }}>
          <Icon size={14} /> {cfg.label}
        </span>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Final Confidence: <strong style={{ color: "var(--text-secondary)" }}>{(trace.final_confidence * 100).toFixed(1)}%</strong>
          &ensp;·&ensp;
          Conflict Index: <strong style={{ color: "var(--text-secondary)" }}>{(trace.conflict_index ?? 0).toFixed(1)}</strong>
        </p>
        {trace.red_team_flag && (
          <div style={{
            display: "flex", alignItems: "center", gap: "var(--space-2)",
            padding: "var(--space-2) var(--space-4)",
            background: "rgba(248,81,73,0.10)", border: "1px solid var(--danger)",
            borderRadius: "var(--radius-sm)", fontSize: "0.82rem", color: "var(--danger)"
          }}>
            <Shield size={14} /> Red Team flagged <strong>{trace.red_team_severity}</strong> risk
          </div>
        )}
      </div>
    </div>
  );
}

// ── Agent Score Table ────────────────────────────────────────

export function AgentBreakdownTable({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["Agent", "Score (Sᵢ)", "Weight (Wᵢ)", "Confidence (Cᵢ)", "Claim"].map(h => (
              <th key={h} style={{ padding: "var(--space-3) var(--space-4)", textAlign: "left", color: "var(--text-muted)", fontWeight: 600, fontSize: "0.78rem", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {domains.map(d => {
            const score = trace.agent_scores?.[d];
            const weight = trace.agent_weights?.[d];
            const conf = trace.agent_confidences?.[d];
            const claim = trace.agent_claims?.[d];
            const color = DOMAIN_COLORS[d];

            return (
              <tr key={d} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "var(--space-3) var(--space-4)" }}>
                  <span className={`domain-chip ${d.toLowerCase()}`}>{d}</span>
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)" }}>
                  {score !== undefined ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <strong style={{ color: "var(--text-primary)" }}>{score.toFixed(1)}</strong>
                      <div className="progress-bar" style={{ width: 80 }}>
                        <div className="progress-bar-fill" style={{ width: `${score}%`, background: color }} />
                      </div>
                    </div>
                  ) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-secondary)" }}>
                  {weight !== undefined ? (weight * 100).toFixed(1) + "%" : "—"}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-secondary)" }}>
                  {conf !== undefined ? (conf * 100).toFixed(1) + "%" : "—"}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", maxWidth: 280 }}>
                  <span style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {claim ?? "—"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Radar Chart (pure SVG, no dependency) ────────────────────

export function AgentRadarChart({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];
  const scores = domains.map(d => (trace.agent_scores?.[d] ?? 0) / 100);
  const N = domains.length;
  const cx = 200, cy = 200, r = 150;

  function polar(val: number, i: number): [number, number] {
    const angle = (2 * Math.PI * i) / N - Math.PI / 2;
    return [cx + r * val * Math.cos(angle), cy + r * val * Math.sin(angle)];
  }

  const scorePoints = scores.map((v, i) => polar(v, i));
  const scoreD = scorePoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ") + " Z";

  const ringLevels = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className="radar-container">
      <svg viewBox="0 0 400 400" style={{ width: "100%", height: "100%" }}>
        {/* Grid rings */}
        {ringLevels.map(level => {
          const pts = domains.map((_, i) => polar(level, i));
          const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ") + " Z";
          return <path key={level} d={d} fill="none" stroke="var(--border)" strokeWidth={1} />;
        })}

        {/* Axes */}
        {domains.map((_, i) => {
          const [x, y] = polar(1.0, i);
          return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--border)" strokeWidth={1} />;
        })}

        {/* Score polygon */}
        <path d={scoreD} fill="rgba(105,65,239,0.18)" stroke="var(--accent-400)" strokeWidth={2} />

        {/* Score dots */}
        {scorePoints.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={5} fill={DOMAIN_COLORS[domains[i]]} stroke="var(--bg-base)" strokeWidth={2} />
        ))}

        {/* Labels */}
        {domains.map((d, i) => {
          const [x, y] = polar(1.18, i);
          return (
            <text key={d} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
              fill={DOMAIN_COLORS[d]} fontSize="13" fontWeight="600" fontFamily="Inter, sans-serif">
              {d}
            </text>
          );
        })}

        {/* Centre */}
        <circle cx={cx} cy={cy} r={3} fill="var(--border)" />
      </svg>
    </div>
  );
}

// ── Board Transcript ─────────────────────────────────────────

interface TranscriptEvent {
  icon: string;
  label: string;
  content: string;
  time?: string;
}

export function BoardTranscript({ trace }: { trace: DecisionTrace }) {
  const events: TranscriptEvent[] = [];

  events.push({ icon: "🔍", label: "Pitch Received", content: (trace.startup_pitch ?? "").slice(0, 200) + "…" });
  events.push({ icon: "🧩", label: "Digital Twin Extracted", content: JSON.stringify(trace.digital_twin ?? {}, null, 2).slice(0, 300) });
  events.push({ icon: "📚", label: "Evidence Retrieved", content: `${trace.retrieved_case_ids?.length ?? 0} historical cases retrieved for grounding.` });

  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];
  domains.forEach(d => {
    const score = trace.agent_scores?.[d];
    const claim = trace.agent_claims?.[d];
    if (score !== undefined) {
      events.push({ icon: "🤖", label: `${d} Agent`, content: `Score: ${score.toFixed(1)} — ${claim ?? "No claim recorded."}` });
    }
  });

  if (trace.hitl_triggered) {
    events.push({ icon: "⏸️", label: "HITL Triggered", content: trace.hitl_question ?? "Clarifying question sent." });
    if (trace.hitl_answer) {
      events.push({ icon: "💬", label: "User Responded", content: trace.hitl_answer });
    }
    if (trace.hitl_effectiveness !== undefined) {
      events.push({ icon: "📉", label: "Conflict Reduced", content: `CI before: ${(trace.hitl_ci_before ?? 0).toFixed(2)} → after: ${(trace.hitl_ci_after ?? 0).toFixed(2)} (Δ = ${trace.hitl_effectiveness.toFixed(2)})` });
    }
  }

  const cfg = DECISION_CONFIG[trace.decision];
  events.push({ icon: "⚖️", label: "Decision Fused", content: `Final Score: ${(trace.final_score ?? 0).toFixed(1)} ± ${(trace.final_score_uncertainty ?? 0).toFixed(1)} → ${cfg.label}` });

  if (trace.red_team_flag) {
    events.push({ icon: "🛡️", label: "Red Team Escalation", content: `[${(trace.red_team_severity ?? "").toUpperCase()}] ${trace.red_team_reasoning ?? ""}` });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {events.map((ev, i) => (
        <div key={i} className="transcript-event">
          <div className="transcript-icon">{ev.icon}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: "0.88rem", marginBottom: 4 }}>{ev.label}</div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {ev.content}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Version / Reproducibility Info ───────────────────────────

export function VersionInfo({ trace }: { trace: DecisionTrace }) {
  const v = trace.version_info ?? {};
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
        <Info size={14} style={{ color: "var(--text-muted)" }} />
        <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Reproducibility Snapshot
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "var(--space-3)" }}>
        {[
          ["Evaluation ID", trace.evaluation_id],
          ["Worker Model", String(v.model_worker ?? "—")],
          ["Router Model", String(v.model_router ?? "—")],
          ["Prompt Template", String(v.prompt_template_version ?? "—")],
          ["RAG Index", String(v.rag_index_version ?? "—")],
          ["Dataset Version", String(v.dataset_version ?? "—")],
          ["Weight Calibration", String(v.weight_calibration_version ?? "—")],
        ].map(([label, value]) => (
          <div key={label} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "var(--text-secondary)", wordBreak: "break-all" }}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Sensitivity Sweep Table ───────────────────────────────────

export function SensitivitySweep({ trace }: { trace: DecisionTrace }) {
  if (!trace.sensitivity_sweep?.length) return null;
  const originalDecision = trace.decision;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {trace.sensitivity_sweep.map((pt, i) => {
        const isFlip = pt.decision !== originalDecision;
        return (
          <div key={i} className={`sweep-row${isFlip ? " flip" : ""}`}>
            <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", minWidth: 80 }}>
              {String(pt.variable_value)}
            </code>
            <span style={{ flex: 1, color: "var(--text-secondary)", fontSize: "0.85rem" }}>
              Final Score: {pt.final_score.toFixed(1)}
            </span>
            <span className={`badge ${DECISION_CONFIG[pt.decision as Decision]?.class ?? "badge-neutral"}`}>
              {pt.decision}
            </span>
            {isFlip && (
              <span style={{ fontSize: "0.75rem", color: "var(--warning)", fontWeight: 600 }}>
                ⚡ FLIP
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
