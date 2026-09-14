"use client";

import React from "react";
import type { ProgressResponse } from "@/lib/api";

// ── Stage definitions ─────────────────────────────────────────────────────────

interface StageConfig {
  key: string;
  label: string;
  emoji: string;
  isAgentStage?: boolean;
}

const PIPELINE_STAGES: StageConfig[] = [
  { key: "context_router",    label: "Context Router",       emoji: "🧩" },
  { key: "retrieval",         label: "Evidence Retrieval",   emoji: "📚" },
  { key: "parallel_dispatch", label: "Agent Deliberation",   emoji: "🤖", isAgentStage: true },
  { key: "conflict_index",    label: "Conflict Analysis",    emoji: "⚖️" },
  { key: "hitl",              label: "HITL Clarification",   emoji: "💬" },
  { key: "fusion",            label: "Decision Fusion",      emoji: "🔀" },
  { key: "sensitivity_sweep", label: "Sensitivity Sweep",    emoji: "📊" },
  { key: "red_team",          label: "Red Team Check",       emoji: "🛡️" },
  { key: "evaluation_logger", label: "Audit Logger",         emoji: "🗂️" },
];

const AGENT_DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"];

const AGENT_COLORS: Record<string, string> = {
  Finance:    "#3fb950",
  Legal:      "#d29922",
  Market:     "#58a6ff",
  Operations: "#f0883e",
  Technology: "#bc8cff",
};

// ── Stage status helpers ──────────────────────────────────────────────────────

function getStageStatus(
  stageKey: string,
  progress: ProgressResponse,
): "complete" | "active" | "pending" {
  if (progress.stages_completed.includes(stageKey)) return "complete";
  if (progress.current_stage === stageKey) return "active";
  return "pending";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StageIcon({ status }: { status: "complete" | "active" | "pending" }) {
  if (status === "complete") {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="8" fill="var(--success)" fillOpacity="0.2" />
        <circle cx="8" cy="8" r="7" stroke="var(--success)" strokeWidth="1.5" fill="none" />
        <path d="M5 8l2.5 2.5L11 5.5" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === "active") {
    return (
      <span style={{ display: "inline-flex", width: 16, height: 16, alignItems: "center", justifyContent: "center" }}>
        <span className="spinner" style={{ width: 14, height: 14 }} />
      </span>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="7" stroke="var(--border)" strokeWidth="1.5" fill="none" />
    </svg>
  );
}

function AgentSubRow({
  domain,
  entry,
}: {
  domain: string;
  entry: { status: string; score: number | null };
}) {
  const color = AGENT_COLORS[domain] ?? "var(--text-muted)";
  const isDone = entry.status === "complete";
  const isErr = entry.status === "error";
  const isRun = entry.status === "running";

  return (
    <div
      className="agent-sub-step fade-in"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-2) var(--space-4)",
        borderRadius: "var(--radius-sm)",
        background: isDone
          ? `rgba(${color === "#3fb950" ? "63,185,80" : color === "#d29922" ? "210,153,34" : color === "#58a6ff" ? "88,166,255" : color === "#f0883e" ? "240,136,62" : "188,140,255"},0.06)`
          : "transparent",
        border: `1px solid ${isDone || isRun ? color + "44" : "transparent"}`,
        transition: "all 220ms ease",
      }}
    >
      {/* Colour dot */}
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: isDone ? color : isErr ? "var(--danger)" : isRun ? color : "var(--border)",
        boxShadow: isRun ? `0 0 6px ${color}` : "none",
        flexShrink: 0,
        transition: "background 220ms, box-shadow 220ms",
      }} />

      {/* Domain name */}
      <span style={{
        fontSize: "0.82rem",
        fontWeight: 600,
        color: isDone || isRun ? color : "var(--text-muted)",
        minWidth: 90,
        transition: "color 220ms",
      }}>
        {domain}
      </span>

      {/* Status / Score */}
      <span style={{ flex: 1, fontSize: "0.78rem", color: "var(--text-muted)" }}>
        {isRun && <span className="pulse" style={{ color: color }}>evaluating…</span>}
        {isErr && <span style={{ color: "var(--danger)" }}>error</span>}
        {entry.status === "pending" && "waiting"}
      </span>

      {/* Score preview — appears as soon as agent finishes */}
      {isDone && entry.score !== null && (
        <span className="fade-in" style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.85rem",
          fontWeight: 700,
          color: color,
          minWidth: 40,
          textAlign: "right",
        }}>
          {entry.score.toFixed(1)}
        </span>
      )}
    </div>
  );
}

// ── Main ProgressTracker component ────────────────────────────────────────────

interface ProgressTrackerProps {
  progress: ProgressResponse;
}

export default function ProgressTracker({ progress }: ProgressTrackerProps) {
  const totalStages = PIPELINE_STAGES.length;
  const completedCount = progress.stages_completed.length;
  const pct = Math.round((completedCount / totalStages) * 100);

  const isHITLPending = progress.status === "hitl_pending";
  const isError = progress.status === "error";

  return (
    <div className="card" style={{ padding: "var(--space-6)" }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-5)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {!isError && <span className="spinner" style={{ width: 16, height: 16 }} />}
          <h3 style={{ fontSize: "1rem", margin: 0 }}>
            {isError ? "⚠️ Evaluation Error" :
             isHITLPending ? "💬 Awaiting Clarification" :
             progress.status === "queued" ? "⏳ Queued…" :
             "Pipeline Running…"}
          </h3>
        </div>
        <span style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: "0.82rem",
          color: "var(--accent-400)",
          fontWeight: 700,
        }}>
          {pct}%
        </span>
      </div>

      {/* Overall progress bar */}
      <div className="progress-bar" style={{ marginBottom: "var(--space-6)", height: 4 }}>
        <div
          className="progress-bar-fill"
          style={{ width: `${pct}%`, transition: "width 0.6s ease" }}
        />
      </div>

      {/* Stage timeline */}
      <div className="progress-timeline">
        {PIPELINE_STAGES.map((stage, idx) => {
          const status = getStageStatus(stage.key, progress);
          const isLast = idx === PIPELINE_STAGES.length - 1;

          return (
            <div key={stage.key} className={`progress-step progress-step--${status}`}>
              {/* Connector line */}
              {!isLast && (
                <div className="progress-step__connector" />
              )}

              {/* Row */}
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", position: "relative", zIndex: 1 }}>
                <div style={{ width: 20, display: "flex", justifyContent: "center", flexShrink: 0 }}>
                  <StageIcon status={status} />
                </div>

                <span style={{ fontSize: "0.8rem" }}>{stage.emoji}</span>

                <span style={{
                  fontSize: "0.88rem",
                  fontWeight: status === "active" ? 700 : 500,
                  color: status === "complete" ? "var(--text-secondary)" :
                         status === "active"   ? "var(--text-primary)" :
                                                  "var(--text-muted)",
                  flex: 1,
                  transition: "color 220ms",
                }}>
                  {stage.label}
                </span>

                {status === "active" && (
                  <span className="pulse" style={{ fontSize: "0.72rem", color: "var(--accent-400)", fontWeight: 600 }}>
                    running
                  </span>
                )}
                {status === "complete" && (
                  <span style={{ fontSize: "0.72rem", color: "var(--success)", fontWeight: 600 }}>done</span>
                )}
              </div>

              {/* Agent sub-rows — only visible when this stage is active or complete */}
              {stage.isAgentStage && (status === "active" || status === "complete") && (
                <div style={{
                  marginLeft: 38,
                  marginTop: "var(--space-2)",
                  marginBottom: "var(--space-1)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-2)",
                }}>
                  {AGENT_DOMAINS.map(domain => (
                    <AgentSubRow
                      key={domain}
                      domain={domain}
                      entry={progress.agent_status[domain] ?? { status: "pending", score: null }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {isError && progress.error_message && (
        <div className="fade-in" style={{
          marginTop: "var(--space-5)",
          padding: "var(--space-4)",
          borderRadius: "var(--radius-md)",
          background: "rgba(248,81,73,0.08)",
          border: "1px solid var(--danger)",
          fontSize: "0.82rem",
          color: "var(--danger)",
          fontFamily: "JetBrains Mono, monospace",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}>
          {progress.error_message.split("\n").slice(0, 6).join("\n")}
        </div>
      )}

      {/* HITL pause notice */}
      {isHITLPending && (
        <div className="fade-in" style={{
          marginTop: "var(--space-5)",
          padding: "var(--space-4)",
          borderRadius: "var(--radius-md)",
          background: "rgba(210,153,34,0.08)",
          border: "1px solid var(--warning)",
          fontSize: "0.85rem",
          color: "var(--warning)",
        }}>
          Pipeline paused — agents disagreed beyond the conflict threshold. Answer the question above to resume.
        </div>
      )}
    </div>
  );
}
