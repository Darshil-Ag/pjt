"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import HITLModal from "@/components/HITLModal";
import ProgressTracker from "@/components/ProgressTracker";
import {
  DecisionHero,
  AgentBreakdownTable,
  AgentRadarChart,
  BoardTranscript,
  VersionInfo,
  SensitivitySweep,
} from "@/components/Dashboard";
import { getDecision, getEvaluationStatus } from "@/lib/api";
import type { DecisionTrace, ProgressResponse } from "@/lib/api";
import { RefreshCw, Copy, CheckCircle2 } from "lucide-react";
import ReportGenerator from "@/components/ReportGenerator";


const SECTION_TABS = ["Overview", "Agents", "Evidence", "Transcript", "Reproducibility"] as const;
type Tab = (typeof SECTION_TABS)[number];

const POLL_INTERVAL_MS = 2000;

export default function DecisionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [copied, setCopied] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch decision trace (only once status is "complete") ───────────────────
  async function fetchTrace() {
    setLoadingTrace(true);
    setTraceError(null);
    try {
      const data = await getDecision(id);
      setTrace(data);
    } catch (err) {
      setTraceError(err instanceof Error ? err.message : "Failed to load decision trace.");
    } finally {
      setLoadingTrace(false);
    }
  }

  // ── Poll /status/{id} while evaluation is in-progress ─────────────────────
  async function pollStatus() {
    try {
      const p = await getEvaluationStatus(id);
      setProgress(p);

      if (p.status === "complete") {
        stopPolling();
        await fetchTrace();
      } else if (p.status === "error") {
        stopPolling();
      }
      // "hitl_pending" keeps polling so we can detect resume
    } catch (err) {
      // 404 means the ID was never registered (bad URL); stop polling
      if (err instanceof Error && err.message.includes("404")) {
        stopPolling();
        setTraceError("Evaluation not found. The ID may be invalid or the server restarted.");
      }
      // Other errors (network blip) — keep polling silently
    }
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    // Kick off first poll immediately, then every 2 seconds
    pollStatus();
    pollRef.current = setInterval(pollStatus, POLL_INTERVAL_MS);
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // ── Handlers ─────────────────────────────────────────────────────────────────
  function copyId() {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleHITLResolved() {
    // Resume polling after HITL answer submitted
    if (!pollRef.current) {
      pollRef.current = setInterval(pollStatus, POLL_INTERVAL_MS);
    }
  }

  // ── Derived state ─────────────────────────────────────────────────────────
  const isTerminal = progress?.status === "complete" || progress?.status === "error";
  const isHITLPending = progress?.status === "hitl_pending";
  const showTracker = progress && progress.status !== "complete";
  const showDashboard = !!trace;

  // ── Render ────────────────────────────────────────────────────────────────
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
              {isTerminal && trace && (
                <ReportGenerator trace={trace} />
              )}
              {isTerminal && (
                <button
                  id="refresh-decision"
                  className="btn btn-secondary btn-sm"
                  onClick={() => { setLoadingTrace(true); fetchTrace(); }}
                >
                  <RefreshCw size={14} /> Refresh
                </button>
              )}
              <button id="new-evaluation" className="btn btn-ghost btn-sm" onClick={() => router.push("/")}>
                ← New Pitch
              </button>
            </div>
          </div>

          {/* Progress tracker — shown while pipeline is running */}
          {showTracker && progress && (
            <div className="fade-in" style={{ marginBottom: "var(--space-6)" }}>
              <ProgressTracker progress={progress} />
            </div>
          )}

          {/* HITL Modal */}
          {isHITLPending && (
            <HITLModal
              evaluationId={id}
              question={
                progress?.hitl_question ||
                trace?.hitl_question ||
                "The review board detected significant disagreement between domain specialists. Please provide additional clarification to resolve the conflict."
              }
              onResolved={handleHITLResolved}
            />
          )}

          {/* Trace loading state */}
          {loadingTrace && !trace && (
            <div style={{ textAlign: "center", padding: "var(--space-16)" }}>
              <div className="spinner" style={{ width: 40, height: 40, margin: "0 auto var(--space-4)" }} />
              <p style={{ color: "var(--text-muted)" }}>Loading decision trace…</p>
            </div>
          )}

          {/* Trace error */}
          {traceError && (
            <div style={{
              padding: "var(--space-6)", borderRadius: "var(--radius-md)",
              background: "rgba(248,81,73,0.10)", border: "1px solid var(--danger)",
              color: "var(--danger)", textAlign: "center"
            }}>
              {traceError}
            </div>
          )}

          {/* Dashboard — shown once trace is loaded */}
          {showDashboard && (
            <>
              {/* Decision hero */}
              {trace.decision && (
                <div className="card glow-border fade-in" style={{ marginBottom: "var(--space-6)" }}>
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
                      These are the most similar historical precedent cases retrieved from ChromaDB to anchor agent reasoning.
                    </p>
                    {trace.retrieved_cases && trace.retrieved_cases.length > 0 ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
                        {trace.retrieved_cases.map((c, i) => {
                          const cid = String(c.case_id ?? `case_${i + 1}`);
                          const outcome = String(c.outcome ?? "unknown").toLowerCase();
                          const risk = String(c.primary_risk_category ?? "General");
                          const summary = String(c.root_cause_summary ?? "");
                          const rawText = String(c.raw_text ?? "");
                          const industry = c.industry ? String(c.industry) : null;
                          const similarity = typeof c.similarity_score === "number"
                            ? (c.similarity_score * 100).toFixed(1) + "%"
                            : null;

                          return (
                            <div key={cid} className="card" style={{ padding: "var(--space-4)", background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)", flexWrap: "wrap", gap: "var(--space-2)" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                  <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.85rem", color: "var(--accent-300)", fontWeight: 600 }}>
                                    {cid}
                                  </code>
                                  {industry && (
                                    <span style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: "999px", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                                      {industry}
                                    </span>
                                  )}
                                  <span className={`domain-chip ${risk.toLowerCase()}`}>
                                    {risk} Risk
                                  </span>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                  {similarity && (
                                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                                      Similarity: <strong style={{ color: "var(--text-secondary)" }}>{similarity}</strong>
                                    </span>
                                  )}
                                  <span className={`badge ${outcome === "success" ? "badge-proceed" : outcome === "failed" ? "badge-highrisk" : "badge-review"}`}>
                                    {outcome.toUpperCase()}
                                  </span>
                                </div>
                              </div>
                              {summary && (
                                <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
                                  {summary}
                                </p>
                              )}
                              {rawText && (
                                <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
                                  {rawText}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : trace.retrieved_case_ids?.length ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                        {trace.retrieved_case_ids.map(cid => (
                          <div key={cid} className="evidence-card">
                            <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "var(--accent-300)" }}>{cid}</code>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>No historical grounding cases retrieved for this evaluation.</p>
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
