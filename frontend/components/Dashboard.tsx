"use client";

import React from "react";
import type { DecisionTrace, Decision } from "@/lib/api";
import { CheckCircle, XCircle, AlertTriangle, Shield, Info, TrendingUp, TrendingDown } from "lucide-react";

const DOMAIN_COLORS: Record<string, string> = {
  Finance:    "#22c55e",
  Legal:      "#f59e0b",
  Market:     "#3b82f6",
  Operations: "#f97316",
  Technology: "#a855f7",
};

const DOMAIN_BG: Record<string, string> = {
  Finance:    "rgba(34, 197, 94, 0.08)",
  Legal:      "rgba(245, 158, 11, 0.08)",
  Market:     "rgba(59, 130, 246, 0.08)",
  Operations: "rgba(249, 115, 22, 0.08)",
  Technology: "rgba(168, 85, 247, 0.08)",
};

const DECISION_CONFIG: Record<Decision, {
  label: string; class: string;
  Icon: React.FC<{ size?: number }>;
  color: string; glow: string; bgGradient: string;
}> = {
  PROCEED:    {
    label: "Proceed",    class: "badge-proceed",
    Icon: CheckCircle,   color: "var(--success)",
    glow: "var(--success-glow)",
    bgGradient: "radial-gradient(ellipse at top, rgba(34,197,94,0.1), transparent 60%)",
  },
  "HIGH-RISK": {
    label: "High Risk",  class: "badge-highrisk",
    Icon: XCircle,       color: "var(--danger)",
    glow: "var(--danger-glow)",
    bgGradient: "radial-gradient(ellipse at top, rgba(239,68,68,0.1), transparent 60%)",
  },
  REVIEW:     {
    label: "Review",     class: "badge-review",
    Icon: AlertTriangle, color: "var(--warning)",
    glow: "var(--warning-glow)",
    bgGradient: "radial-gradient(ellipse at top, rgba(245,158,11,0.1), transparent 60%)",
  },
};

// ── Decision Hero ────────────────────────────────────────────

export function DecisionHero({ trace }: { trace: DecisionTrace }) {
  const cfg = DECISION_CONFIG[trace.decision];
  const Icon = cfg.Icon;
  const score = trace.final_score ?? 0;
  const band  = trace.final_score_uncertainty ?? 0;

  // SVG ring
  const R = 68, circumference = 2 * Math.PI * R;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      gap: "var(--space-6)", padding: "var(--space-10) var(--space-6)",
      position: "relative", overflow: "hidden",
    }}>
      {/* Background glow */}
      <div style={{
        position: "absolute", inset: 0,
        background: cfg.bgGradient,
        pointerEvents: "none",
      }} />

      {/* Score ring */}
      <div style={{ position: "relative", width: 180, height: 180 }}>
        {/* Outer ring track */}
        <svg width={180} height={180} style={{ transform: "rotate(-90deg)", position: "absolute", inset: 0 }}>
          <circle cx={90} cy={90} r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10} />
          {/* Animated fill */}
          <circle
            cx={90} cy={90} r={R} fill="none"
            stroke={cfg.color} strokeWidth={10}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1), stroke 0.4s ease",
              filter: `drop-shadow(0 0 12px ${cfg.color})`,
            }}
          />
        </svg>
        {/* Center content */}
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{
            fontSize: "2.8rem", fontWeight: 900, lineHeight: 1, letterSpacing: "-0.05em",
            color: "var(--text-primary)",
          }}>
            {score.toFixed(0)}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 500 }}>
            ±{band.toFixed(1)}
          </span>
        </div>
      </div>

      {/* Decision info */}
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}>
        <span className={`badge ${cfg.class}`} style={{ fontSize: "0.85rem", padding: "7px 18px", gap: "var(--space-2)" }}>
          <Icon size={13} />
          {cfg.label}
        </span>

        {/* Metrics row */}
        <div style={{ display: "flex", gap: "var(--space-6)", flexWrap: "wrap", justifyContent: "center" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 2 }}>
              Confidence
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
              {(trace.final_confidence * 100).toFixed(1)}%
            </div>
          </div>
          <div style={{ width: 1, background: "var(--border-subtle)" }} />
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 2 }}>
              Conflict Index
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
              {(trace.conflict_index ?? 0).toFixed(2)}
            </div>
          </div>
          <div style={{ width: 1, background: "var(--border-subtle)" }} />
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 2 }}>
              Evidence Cases
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
              {trace.retrieved_case_ids?.length ?? 0}
            </div>
          </div>
        </div>

        {/* Red Team Flag */}
        {trace.red_team_flag && (
          <div style={{
            display: "flex", alignItems: "flex-start", gap: "var(--space-3)",
            padding: "var(--space-4) var(--space-5)",
            background: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.35)",
            borderRadius: "var(--radius-md)",
            maxWidth: 480, textAlign: "left",
            boxShadow: "0 0 20px var(--danger-glow)",
          }}>
            <Shield size={16} color="var(--danger)" style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--danger)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                Red Team Override — {trace.red_team_severity} Severity
              </div>
              <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {trace.red_team_reasoning}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Agent Score Cards ────────────────────────────────────────

export function AgentBreakdownTable({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {domains.map(d => {
        const score = trace.agent_scores?.[d];
        const weight = trace.agent_weights?.[d];
        const conf = trace.agent_confidences?.[d];
        const claim = trace.agent_claims?.[d];
        const color = DOMAIN_COLORS[d];
        const bg = DOMAIN_BG[d];
        const excluded = score === undefined;

        return (
          <div
            key={d}
            className="agent-card"
            style={{
              opacity: excluded ? 0.45 : 1,
              borderColor: excluded ? "var(--border)" : `${color}25`,
            }}
          >
            {/* Color top stripe */}
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0,
              height: 2, borderRadius: "var(--radius-md) var(--radius-md) 0 0",
              background: excluded ? "var(--border)" : `linear-gradient(90deg, ${color}, transparent)`,
            }} />

            <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-5)" }}>
              {/* Domain chip */}
              <div style={{ paddingTop: 2 }}>
                <span className={`domain-chip ${d.toLowerCase()}`}>{d}</span>
              </div>

              {/* Score + bar */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {excluded ? (
                  <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                    Agent excluded from fusion (rate limit during parallel dispatch).
                  </p>
                ) : (
                  <>
                    {/* Score bar */}
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
                      <div className="progress-bar" style={{ flex: 1, height: 6 }}>
                        <div className="progress-bar-fill" style={{ width: `${score}%`, background: `linear-gradient(90deg, ${color}99, ${color})` }} />
                      </div>
                      <span style={{ fontWeight: 800, color, fontSize: "0.95rem", fontVariantNumeric: "tabular-nums", minWidth: 36, textAlign: "right" }}>
                        {score.toFixed(0)}
                      </span>
                    </div>
                    {/* Claim */}
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.65 }}>{claim ?? "—"}</p>
                  </>
                )}
              </div>

              {/* Stats */}
              {!excluded && (
                <div style={{ display: "flex", gap: "var(--space-5)", flexShrink: 0 }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Wᵢ</div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-secondary)" }}>{weight !== undefined ? (weight * 100).toFixed(1) + "%" : "—"}</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>Cᵢ</div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-secondary)" }}>{conf !== undefined ? (conf * 100).toFixed(1) + "%" : "—"}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Radar Chart (pure SVG) ────────────────────────────────────

export function AgentRadarChart({ trace }: { trace: DecisionTrace }) {
  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];
  const scores = domains.map(d => (trace.agent_scores?.[d] ?? 0) / 100);
  const N = domains.length;
  const cx = 200, cy = 200, r = 148;

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
        <defs>
          <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(105,65,239,0.3)" />
            <stop offset="100%" stopColor="rgba(105,65,239,0.05)" />
          </radialGradient>
        </defs>

        {/* Grid rings */}
        {ringLevels.map(level => {
          const pts = domains.map((_, i) => polar(level, i));
          const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ") + " Z";
          return <path key={level} d={d} fill="none" stroke="rgba(45,58,82,0.6)" strokeWidth={1} strokeDasharray={level < 1 ? "4 4" : undefined} />;
        })}

        {/* Axes */}
        {domains.map((_, i) => {
          const [x, y] = polar(1.0, i);
          return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(45,58,82,0.4)" strokeWidth={1} />;
        })}

        {/* Score polygon */}
        <path d={scoreD} fill="url(#radarFill)" stroke="var(--accent-400)" strokeWidth={2} />

        {/* Score dots */}
        {scorePoints.map(([x, y], i) => (
          <g key={i}>
            <circle cx={x} cy={y} r={7} fill={DOMAIN_COLORS[domains[i]]} opacity={0.2} />
            <circle cx={x} cy={y} r={4} fill={DOMAIN_COLORS[domains[i]]} stroke="var(--bg-base)" strokeWidth={2} />
          </g>
        ))}

        {/* Labels */}
        {domains.map((d, i) => {
          const [x, y] = polar(1.22, i);
          return (
            <text key={d} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
              fill={DOMAIN_COLORS[d]} fontSize="12" fontWeight="700" fontFamily="Inter, sans-serif">
              {d}
            </text>
          );
        })}

        <circle cx={cx} cy={cy} r={3} fill="var(--accent-400)" opacity={0.6} />
      </svg>
    </div>
  );
}

// ── Board Transcript ─────────────────────────────────────────

interface TranscriptEvent {
  icon: string;
  label: string;
  content: string;
  color?: string;
}

export function BoardTranscript({ trace }: { trace: DecisionTrace }) {
  const events: TranscriptEvent[] = [];

  events.push({ icon: "🔍", label: "Pitch Received", content: (trace.startup_pitch ?? "").slice(0, 200) + "…" });
  events.push({ icon: "🧩", label: "Digital Twin Extracted", content: JSON.stringify(trace.digital_twin ?? {}, null, 2).slice(0, 300) });
  events.push({ icon: "📚", label: "Evidence Retrieved", content: `${trace.retrieved_case_ids?.length ?? 0} historical cases retrieved for grounding from the ChromaDB vector index.` });

  const domains = ["Finance", "Legal", "Market", "Operations", "Technology"];
  domains.forEach(d => {
    const score = trace.agent_scores?.[d];
    const claim = trace.agent_claims?.[d];
    if (score !== undefined) {
      events.push({
        icon: "🤖",
        label: `${d} Agent`,
        content: `Score: ${score.toFixed(1)} — ${claim ?? "No claim recorded."}`,
        color: DOMAIN_COLORS[d],
      });
    }
  });

  if (trace.hitl_triggered) {
    events.push({ icon: "⏸️", label: "HITL Triggered", content: trace.hitl_question ?? "Clarifying question sent to human reviewer.", color: "var(--warning)" });
    if (trace.hitl_answer) {
      events.push({ icon: "💬", label: "User Responded", content: trace.hitl_answer });
    }
    if (trace.hitl_effectiveness !== undefined) {
      events.push({ icon: "📉", label: "Conflict Reduced", content: `CI before: ${(trace.hitl_ci_before ?? 0).toFixed(2)} → after: ${(trace.hitl_ci_after ?? 0).toFixed(2)} (Δ = ${trace.hitl_effectiveness.toFixed(2)})` });
    }
  }

  const cfg = DECISION_CONFIG[trace.decision];
  events.push({ icon: "⚖️", label: "Decision Fused", content: `Final Score: ${(trace.final_score ?? 0).toFixed(1)} ± ${(trace.final_score_uncertainty ?? 0).toFixed(1)} → ${cfg.label}`, color: cfg.color });

  if (trace.red_team_flag) {
    events.push({ icon: "🛡️", label: "Red Team Escalation", content: `[${(trace.red_team_severity ?? "").toUpperCase()}] ${trace.red_team_reasoning ?? ""}`, color: "var(--danger)" });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {events.map((ev, i) => (
        <div key={i} className="transcript-event fade-in" style={{ animationDelay: `${i * 40}ms` }}>
          <div className="transcript-icon" style={{ borderColor: ev.color ? `${ev.color}30` : undefined }}>
            {ev.icon}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{
              fontWeight: 600, fontSize: "0.85rem", marginBottom: 4,
              color: ev.color ?? "var(--text-primary)",
            }}>
              {ev.label}
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.65 }}>
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
  const fields = [
    ["Evaluation ID", trace.evaluation_id],
    ["Worker Model", String(v.model_worker ?? "—")],
    ["Router Model", String(v.model_router ?? "—")],
    ["Prompt Template", String(v.prompt_template_version ?? "—")],
    ["RAG Index", String(v.rag_index_version ?? "—")],
    ["Dataset Version", String(v.dataset_version ?? "—")],
    ["Weight Calibration", String(v.weight_calibration_version ?? "—")],
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Info size={14} style={{ color: "var(--accent-400)" }} />
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Reproducibility Snapshot
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "var(--space-3)" }}>
        {fields.map(([label, value]) => (
          <div key={label} style={{
            padding: "var(--space-3) var(--space-4)",
            background: "rgba(15, 21, 35, 0.5)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
          }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 4 }}>{label}</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.78rem", color: "var(--text-secondary)", wordBreak: "break-all" }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Market Intelligence Card (Scope A) ────────────────────────

export function MarketIntelCard({ trace }: { trace: DecisionTrace }) {
  const intel = (trace as any).market_intel;
  if (!intel || intel.source === "none") return null;

  const sections: Array<{ label: string; key: "funding_signals" | "competitor_signals" | "market_signals"; color: string }> = [
    { label: "💰 Funding Activity", key: "funding_signals", color: "var(--success)" },
    { label: "🏢 Competitive Landscape", key: "competitor_signals", color: "var(--accent-400)" },
    { label: "📈 Market Signals", key: "market_signals", color: "var(--warning)" },
  ];

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      padding: "var(--space-6)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-4)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "var(--text-base)", fontWeight: 700, color: "var(--text-primary)" }}>
            Live Market Intelligence
          </h3>
          <p style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            Real-time signals fetched during evaluation
          </p>
        </div>
        <span style={{
          fontSize: "var(--text-xs)", fontWeight: 700, padding: "3px 10px",
          borderRadius: "var(--radius-sm)", background: "rgba(99,102,241,0.15)",
          color: "#818cf8", border: "1px solid rgba(99,102,241,0.3)",
          textTransform: "uppercase", letterSpacing: "0.06em",
        }}>
          {intel.source === "serpapi" ? "SerpAPI" : "DuckDuckGo"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
        {sections.map(({ label, key, color }) => {
          const items: string[] = intel[key] ?? [];
          if (!items.length) return null;
          return (
            <div key={key} style={{
              background: "rgba(15,21,35,0.5)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-4)",
            }}>
              <div style={{ fontSize: "var(--text-xs)", fontWeight: 700, color, marginBottom: "var(--space-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                {label}
              </div>
              <ul style={{ margin: 0, padding: "0 0 0 var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {items.slice(0, 3).map((s, i) => (
                  <li key={i} style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {s.length > 150 ? s.slice(0, 150) + "…" : s}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Extra Agents Badge (Scope B) ──────────────────────────────

export function ExtraAgentsBadge({ trace }: { trace: DecisionTrace }) {
  const extra = trace.extra_agents_triggered;
  if (!extra || extra.length === 0) return null;

  const SPEC_COLORS: Record<string, string> = {
    "Regulatory (FDA)": "#f43f5e",
    "ESG & Impact": "#22c55e",
    "Blockchain & Web3": "#f59e0b",
    "Hardware & Supply Chain": "#60a5fa",
    "AI Ethics & Safety": "#a78bfa",
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: "var(--space-2)",
      padding: "var(--space-3) var(--space-4)",
      background: "rgba(168,85,247,0.08)",
      border: "1px solid rgba(168,85,247,0.25)",
      borderRadius: "var(--radius-md)",
      flexWrap: "wrap",
    }}>
      <span style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginRight: "var(--space-2)" }}>
        ⚡ Dynamic Specialists
      </span>
      {extra.map(domain => (
        <span key={domain} style={{
          fontSize: "var(--text-xs)", fontWeight: 600, padding: "2px 10px",
          borderRadius: "999px", border: `1px solid ${SPEC_COLORS[domain] ?? "#888"}40`,
          background: `${SPEC_COLORS[domain] ?? "#888"}18`,
          color: SPEC_COLORS[domain] ?? "var(--text-secondary)",
        }}>
          {domain}
        </span>
      ))}
    </div>
  );
}

// ── Sensitivity Sweep (delegates to SensitivityChart) ─────────

export function SensitivitySweep({ trace }: { trace: DecisionTrace }) {
  const sweep = trace.sensitivity_sweep as import("@/lib/api").SweepResult | undefined;
  if (!sweep?.by_domain) return null;
  const { SensitivityChart } = require("./SensitivityChart");
  return <SensitivityChart sweep={sweep} />;
}
