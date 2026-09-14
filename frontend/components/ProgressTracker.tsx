"use client";

import React from "react";
import type { ProgressResponse } from "@/lib/api";

const STEPS = [
  { id: "context_router", label: "Building Digital Twin" },
  { id: "retrieval", label: "Retrieving historical evidence" },
  { id: "agent_Finance", label: "Running Finance analysis", isAgent: "Finance" },
  { id: "agent_Legal", label: "Running Legal analysis", isAgent: "Legal" },
  { id: "agent_Market", label: "Running Market analysis", isAgent: "Market" },
  { id: "agent_Operations", label: "Running Operations analysis", isAgent: "Operations" },
  { id: "agent_Technology", label: "Running Technology analysis", isAgent: "Technology" },
  { id: "fusion", label: "Computing final decision" },
];

export default function ProgressTracker({ progress }: { progress: ProgressResponse }) {
  const isError = progress.status === "error";
  const isHITLPending = progress.status === "hitl_pending";

  function getStepState(step: typeof STEPS[number]): "done" | "active" | "pending" | "error" {
    if (isError) return "error";

    if (step.isAgent) {
      const agentEntry = progress.agent_status?.[step.isAgent];
      if (agentEntry?.status === "complete") return "done";
      if (agentEntry?.status === "running") return "active";
      if (agentEntry?.status === "error") return "error";
      if (progress.current_stage === "parallel_dispatch") return "active";
      return "pending";
    }

    if (progress.stages_completed.includes(step.id)) return "done";
    if (progress.current_stage === step.id) return "active";
    if (step.id === "fusion" && (progress.stages_completed.includes("fusion") || progress.stages_completed.includes("red_team"))) return "done";
    if (step.id === "fusion" && (progress.current_stage === "fusion" || progress.current_stage === "red_team" || progress.current_stage === "evaluation_logger")) return "active";

    return "pending";
  }

  return (
    <div className="card" style={{ padding: "var(--space-6)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
        {!isError && <span className="spinner" style={{ width: 16, height: 16 }} />}
        <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>
          {isError ? "Evaluation Error" :
           isHITLPending ? "Awaiting Clarification" :
           "AIRB is analyzing your startup..."}
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {STEPS.map((step) => {
          const state = getStepState(step);
          return (
            <div key={step.id} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", fontSize: "0.9rem" }}>
              <div style={{ width: 20, display: "flex", justifyContent: "center" }}>
                {state === "done" && (
                  <span style={{ color: "var(--success)", fontWeight: 700, fontSize: "0.95rem" }}>✓</span>
                )}
                {state === "active" && (
                  <span className="spinner" style={{ width: 14, height: 14 }} />
                )}
                {state === "pending" && (
                  <span style={{ color: "var(--border-dark)", fontSize: "0.85rem" }}>○</span>
                )}
                {state === "error" && (
                  <span style={{ color: "var(--danger)", fontWeight: 700 }}>✕</span>
                )}
              </div>

              <span style={{
                color: state === "done" ? "var(--text-secondary)" :
                       state === "active" ? "var(--text-primary)" : "var(--text-muted)",
                fontWeight: state === "active" ? 600 : 400,
              }}>
                {step.label}
              </span>

              {step.isAgent && state === "done" && progress.agent_status?.[step.isAgent]?.score !== null && (
                <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "0.82rem", fontWeight: 600, color: "var(--text-muted)", marginLeft: "auto" }}>
                  {progress.agent_status[step.isAgent].score?.toFixed(0)} / 100
                </span>
              )}
            </div>
          );
        })}
      </div>

      {isError && progress.error_message && (
        <div style={{
          marginTop: "var(--space-4)",
          padding: "var(--space-3) var(--space-4)",
          borderRadius: "var(--radius-md)",
          background: "var(--danger-bg)",
          border: "1px solid var(--danger-border)",
          color: "var(--danger-text)",
          fontSize: "0.85rem"
        }}>
          {progress.error_message.split("\n")[0]}
        </div>
      )}

      {isHITLPending && (
        <div style={{
          marginTop: "var(--space-4)",
          padding: "var(--space-3) var(--space-4)",
          borderRadius: "var(--radius-md)",
          background: "var(--warning-bg)",
          border: "1px solid var(--warning-border)",
          color: "var(--warning-text)",
          fontSize: "0.88rem"
        }}>
          Evaluation paused for clarification. Please respond below to resume.
        </div>
      )}
    </div>
  );
}
