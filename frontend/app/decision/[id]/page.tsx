"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import HITLModal from "@/components/HITLModal";
import {
  DecisionHero,
  AgentBreakdownTable,
  AgentRadarChart,
  BoardTranscript,
  VersionInfo,
  SensitivitySweep,
} from "@/components/Dashboard";
import { getDecision } from "@/lib/api";
import type { DecisionTrace } from "@/lib/api";
import { RefreshCw, Copy, CheckCircle2 } from "lucide-react";

const SECTION_TABS = ["Overview", "Agents", "Evidence", "Transcript", "Reproducibility"] as const;
type Tab = (typeof SECTION_TABS)[number];

function StatusBanner({ status }: { status: string }) {
  if (status === "complete") return null;
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: "var(--space-3)",
      padding: "var(--space-4) var(--space-6)",
      background: "rgba(105,65,239,0.10)", border: "1px solid var(--accent-500)",
      borderRadius: "var(--radius-md)", marginBottom: "var(--space-6)"
    }}>
      <span className="spinner" />
      <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
        {status === "running" ? "Evaluation is running… agents are deliberating." : status}
      </span>
    </div>
  );
}

export default function DecisionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [status, setStatus] = useState<string>("running");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [copied, setCopied] = useState(false);

  async function fetchDecision() {
    try {
      const data = await getDecision(id);
      setTrace(data);
      setStatus(data.decision ? "complete" : "running");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load decision.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDecision();
    // Poll while running (Sprint 2+: replace with WebSocket/SSE)
    const interval = setInterval(() => {
      if (status !== "complete") fetchDecision();
    }, 4000);
    return () => clearInterval(interval);
  }, [id]);

  function copyId() {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleHITLResolved() {
    setStatus("running");
    fetchDecision();
  }

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <Navbar />
      <main>
        <div className="container" style={{ padding: "var(--space-8) var(--space-6)" }}>

          {/* Header row */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "var(--space-6)", gap: "var(--space-4)", flexWrap: "wrap" }}>
            <div>
              <h1 style={{ fontSize: "1.6rem", marginBottom: "var(--space-1)" }}>Decision Report</h1>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  {id}
                </code>
                <button id="copy-eval-id" className="btn-ghost btn" style={{ padding: "2px 6px" }} onClick={copyId}>
                  {copied ? <CheckCircle2 size={12} color="var(--success)" /> : <Copy size={12} />}
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <button id="refresh-decision" className="btn btn-secondary btn-sm" onClick={() => { setLoading(true); fetchDecision(); }}>
                <RefreshCw size={14} /> Refresh
              </button>
              <button id="new-evaluation" className="btn btn-ghost btn-sm" onClick={() => router.push("/")}>
                ← New Pitch
              </button>
            </div>
          </div>

          {/* Loading */}
          {loading && !trace && (
            <div style={{ textAlign: "center", padding: "var(--space-16)" }}>
              <div className="spinner" style={{ width: 40, height: 40, margin: "0 auto var(--space-4)" }} />
              <p style={{ color: "var(--text-muted)" }}>Loading decision trace…</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              padding: "var(--space-6)", borderRadius: "var(--radius-md)",
              background: "rgba(248,81,73,0.10)", border: "1px solid var(--danger)",
              color: "var(--danger)", textAlign: "center"
            }}>
              {error}
            </div>
          )}

          {trace && (
            <>
              <StatusBanner status={status} />

              {/* HITL Modal */}
              {trace.hitl_triggered && !trace.hitl_answer && trace.hitl_question && (
                <HITLModal
                  evaluationId={id}
                  question={trace.hitl_question}
                  onResolved={handleHITLResolved}
                />
              )}

              {/* Decision hero (only when complete) */}
              {trace.decision && (
                <div className="card glow-border" style={{ marginBottom: "var(--space-6)" }}>
                  <DecisionHero trace={trace} />
                </div>
              )}

              {/* Tabs */}
              <div style={{ display: "flex", gap: "var(--space-1)", borderBottom: "1px solid var(--border)", marginBottom: "var(--space-6)" }}>
                {SECTION_TABS.map(tab => (
                  <button
                    key={tab}
                    id={`tab-${tab.toLowerCase()}`}
                    className="btn btn-ghost"
                    onClick={() => setActiveTab(tab)}
                    style={{
                      borderBottom: activeTab === tab ? "2px solid var(--accent-400)" : "2px solid transparent",
                      borderRadius: 0, color: activeTab === tab ? "var(--accent-400)" : "var(--text-muted)",
                      fontWeight: activeTab === tab ? 600 : 400,
                      paddingBottom: "var(--space-3)"
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="fade-in" key={activeTab}>

                {/* ── Overview ── */}
                {activeTab === "Overview" && (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "var(--space-6)" }}>
                    <div className="card">
                      <h3 style={{ marginBottom: "var(--space-6)" }}>Risk Radar</h3>
                      <AgentRadarChart trace={trace} />
                    </div>
                    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
                      <h3>Key Metrics</h3>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
                        {[
                          { label: "Final Score", value: trace.final_score !== undefined ? `${trace.final_score.toFixed(1)}` : "—", sub: `± ${(trace.final_score_uncertainty ?? 0).toFixed(1)} uncertainty` },
                          { label: "Confidence", value: trace.final_confidence !== undefined ? `${(trace.final_confidence * 100).toFixed(1)}%` : "—", sub: "C_final = Σ(Wᵢ·Cᵢ)" },
                          { label: "Conflict Index", value: trace.conflict_index !== undefined ? trace.conflict_index.toFixed(2) : "—", sub: "CI = Var(S₁…S₅)" },
                          { label: "HITL Triggered", value: trace.hitl_triggered ? "Yes" : "No", sub: trace.hitl_effectiveness !== undefined ? `Δ CI = ${trace.hitl_effectiveness.toFixed(2)}` : "" },
                        ].map(m => (
                          <div key={m.label} className="metric-card">
                            <span className="metric-label">{m.label}</span>
                            <span className="metric-value" style={{ fontSize: "1.5rem" }}>{m.value}</span>
                            {m.sub && <span className="metric-sub">{m.sub}</span>}
                          </div>
                        ))}
                      </div>
                      {trace.red_team_flag && (
                        <>
                          <div className="divider" />
                          <div style={{ padding: "var(--space-4)", borderRadius: "var(--radius-md)", background: "rgba(248,81,73,0.08)", border: "1px solid var(--danger)" }}>
                            <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--danger)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "var(--space-2)" }}>
                              🛡️ Red Team — {trace.red_team_severity?.toUpperCase()} Severity
                            </p>
                            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0 }}>{trace.red_team_reasoning}</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* ── Agents ── */}
                {activeTab === "Agents" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
                    <div className="card">
                      <h3 style={{ marginBottom: "var(--space-5)" }}>Agent Score Breakdown</h3>
                      <AgentBreakdownTable trace={trace} />
                    </div>
                    {trace.sensitivity_sweep && trace.sensitivity_sweep.length > 0 && (
                      <div className="card">
                        <h3 style={{ marginBottom: "var(--space-2)" }}>Assumption Sensitivity Sweep</h3>
                        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "var(--space-5)" }}>
                          Re-ran fusion across a range of values for the HITL-triggering variable. Decision flips are highlighted.
                        </p>
                        <SensitivitySweep trace={trace} />
                      </div>
                    )}
                  </div>
                )}

                {/* ── Evidence ── */}
                {activeTab === "Evidence" && (
                  <div className="card">
                    <h3 style={{ marginBottom: "var(--space-2)" }}>Retrieved Historical Cases</h3>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "var(--space-5)" }}>
                      These are the most similar cases from the grounding corpus used to anchor agent reasoning.
                    </p>
                    {trace.retrieved_case_ids?.length ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                        {trace.retrieved_case_ids.map(cid => (
                          <div key={cid} className="evidence-card">
                            <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "var(--accent-300)" }}>{cid}</code>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>No evidence retrieved yet (requires Sprint 2 RAG integration).</p>
                    )}
                  </div>
                )}

                {/* ── Transcript ── */}
                {activeTab === "Transcript" && (
                  <div className="card">
                    <h3 style={{ marginBottom: "var(--space-5)" }}>Board Transcript</h3>
                    <BoardTranscript trace={trace} />
                  </div>
                )}

                {/* ── Reproducibility ── */}
                {activeTab === "Reproducibility" && (
                  <div className="card">
                    <h3 style={{ marginBottom: "var(--space-5)" }}>Version Snapshot (F-17)</h3>
                    <VersionInfo trace={trace} />
                    <div className="divider" style={{ margin: "var(--space-6) 0" }} />
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                      Use <code style={{ fontFamily: "JetBrains Mono, monospace" }}>GET /replay/{id}</code> to
                      reconstruct this exact decision without re-invoking any LLM (SRS F-17).
                    </p>
                  </div>
                )}

              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
