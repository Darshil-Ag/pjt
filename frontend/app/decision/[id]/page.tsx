"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import HITLModal from "@/components/HITLModal";
import ProgressTracker from "@/components/ProgressTracker";
import {
  DecisionHero,
  DomainAnalysisBars,
  DigitalTwinView,
  CompactAgentCards,
  EvidenceSection,
  BoardTranscript,
  VersionInfo,
  SensitivitySweep,
} from "@/components/Dashboard";
import { getDecision, getEvaluationStatus } from "@/lib/api";
import type { DecisionTrace, ProgressResponse } from "@/lib/api";
import { RefreshCw, Copy, CheckCircle2 } from "lucide-react";

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
    } catch (err) {
      if (err instanceof Error && err.message.includes("404")) {
        stopPolling();
        setTraceError("Evaluation not found. The ID may be invalid or the server restarted.");
      }
    }
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
              <h1 style={{ fontSize: "1.5rem", marginBottom: "var(--space-1)", fontWeight: 700 }}>Startup Evaluation</h1>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <code style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {id}
                </code>
                <button id="copy-eval-id" className="btn-ghost btn" style={{ padding: "2px 6px" }} onClick={copyId}>
                  {copied ? <CheckCircle2 size={12} color="var(--success)" /> : <Copy size={12} />}
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
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
          {isHITLPending && trace?.hitl_question && !trace?.hitl_answer && (
            <HITLModal
              evaluationId={id}
              question={trace.hitl_question}
              onResolved={handleHITLResolved}
            />
          )}

          {/* Trace loading state */}
          {loadingTrace && !trace && (
            <div style={{ textAlign: "center", padding: "var(--space-16)" }}>
              <div className="spinner" style={{ width: 36, height: 36, margin: "0 auto var(--space-4)" }} />
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Loading evaluation report…</p>
            </div>
          )}

          {/* Trace error */}
          {traceError && (
            <div style={{
              padding: "var(--space-6)", borderRadius: "var(--radius-md)",
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              color: "var(--danger-text)", textAlign: "center"
            }}>
              {traceError}
            </div>
          )}

          {/* Dashboard — shown once trace is loaded */}
          {showDashboard && (
            <>
              {/* Decision hero */}
              {trace.decision && (
                <div className="card" style={{ marginBottom: "var(--space-6)" }}>
                  <DecisionHero trace={trace} />
                </div>
              )}

              {/* Navigation Tabs */}
              <div style={{ display: "flex", gap: "var(--space-2)", borderBottom: "1px solid var(--border)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
                {SECTION_TABS.map(tab => (
                  <button
                    key={tab}
                    id={`tab-${tab.toLowerCase()}`}
                    className="btn btn-ghost"
                    onClick={() => setActiveTab(tab)}
                    style={{
                      borderBottom: activeTab === tab ? "2px solid var(--text-primary)" : "2px solid transparent",
                      borderRadius: 0,
                      color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)",
                      fontWeight: activeTab === tab ? 600 : 400,
                      padding: "var(--space-2) var(--space-4)",
                      fontSize: "0.9rem"
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div key={activeTab}>

                {/* ── Overview ── */}
                {activeTab === "Overview" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
                    {/* Key Metrics Grid */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
                      <div className="card" style={{ padding: "var(--space-4)" }}>
                        <span className="kv-label">Final Score</span>
                        <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                          {trace.final_score !== undefined ? trace.final_score.toFixed(0) : "—"}
                          <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 400 }}> / 100</span>
                        </div>
                      </div>

                      <div className="card" style={{ padding: "var(--space-4)" }}>
                        <span className="kv-label">Decision</span>
                        <div style={{ marginTop: 6 }}>
                          <span className={`badge badge-${trace.decision?.toLowerCase().replace("-", "")}`}>
                            {trace.decision}
                          </span>
                        </div>
                      </div>

                      <div className="card" style={{ padding: "var(--space-4)" }}>
                        <span className="kv-label">Confidence</span>
                        <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                          {trace.final_confidence !== undefined ? `${Math.round(trace.final_confidence * 100)}%` : "—"}
                        </div>
                      </div>

                      <div className="card" style={{ padding: "var(--space-4)" }}>
                        <span className="kv-label">Conflict Index</span>
                        <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                          {trace.conflict_index !== undefined ? trace.conflict_index.toFixed(2) : "—"}
                        </div>
                      </div>

                      <div className="card" style={{ padding: "var(--space-4)" }}>
                        <span className="kv-label">Red Team</span>
                        <div style={{ fontSize: "1rem", fontWeight: 600, color: trace.red_team_flag ? "var(--danger-text)" : "var(--success-text)", marginTop: 8 }}>
                          {trace.red_team_flag ? `Flagged (${trace.red_team_severity?.toUpperCase()})` : "Passed"}
                        </div>
                      </div>
                    </div>

                    {/* Domain Analysis */}
                    <div className="card">
                      <h3 style={{ marginBottom: "var(--space-4)" }}>Domain Analysis</h3>
                      <DomainAnalysisBars trace={trace} />
                    </div>

                    {/* Digital Twin */}
                    <div className="card">
                      <h3 style={{ marginBottom: "var(--space-4)" }}>Digital Twin</h3>
                      <DigitalTwinView dt={trace.digital_twin} />
                    </div>
                  </div>
                )}

                {/* ── Agents ── */}
                {activeTab === "Agents" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
                    <div className="card">
                      <h3 style={{ marginBottom: "var(--space-4)" }}>Domain Agents</h3>
                      <CompactAgentCards trace={trace} />
                    </div>
                    {trace.sensitivity_sweep && trace.sensitivity_sweep.length > 0 && (
                      <div className="card">
                        <h3 style={{ marginBottom: "var(--space-2)" }}>Assumption Sensitivity Sweep</h3>
                        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "var(--space-4)" }}>
                          Re-ran fusion across a range of values for the HITL-triggering variable.
                        </p>
                        <SensitivitySweep trace={trace} />
                      </div>
                    )}
                  </div>
                )}

                {/* ── Evidence ── */}
                {activeTab === "Evidence" && (
                  <div className="card">
                    <EvidenceSection trace={trace} />
                  </div>
                )}

                {/* ── Transcript ── */}
                {activeTab === "Transcript" && (
                  <div className="card">
                    <h3 style={{ marginBottom: "var(--space-4)" }}>Board Transcript</h3>
                    <BoardTranscript trace={trace} />
                  </div>
                )}

                {/* ── Reproducibility ── */}
                {activeTab === "Reproducibility" && (
                  <div className="card">
                    <h3 style={{ marginBottom: "var(--space-4)" }}>Technical Information</h3>
                    <VersionInfo trace={trace} />
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
