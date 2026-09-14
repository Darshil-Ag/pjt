"use client";

import React, { useState } from "react";
import { respondToHITL } from "@/lib/api";
import { MessageSquare, Send, AlertCircle } from "lucide-react";

interface HITLModalProps {
  evaluationId: string;
  question: string;
  onResolved: () => void;
}

export default function HITLModal({ evaluationId, question, onResolved }: HITLModalProps) {
  const [answer, setAnswer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!answer.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await respondToHITL(evaluationId, answer.trim());
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit. Please try again.");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="hitl-title">
      <div className="glass modal-panel fade-in" style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <div style={{
            width: 40, height: 40, borderRadius: "50%",
            background: "rgba(210,153,34,0.15)", border: "1px solid var(--warning)",
            display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <MessageSquare size={18} color="var(--warning)" />
          </div>
          <div>
            <h3 id="hitl-title" style={{ color: "var(--text-primary)", marginBottom: 2 }}>
              Human Clarification Required
            </h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: 0 }}>
              The review board detected significant disagreement and needs more information.
            </p>
          </div>
        </div>

        <div className="divider" />

        {/* Question */}
        <div style={{
          padding: "var(--space-4)",
          borderRadius: "var(--radius-md)",
          background: "rgba(210,153,34,0.06)",
          border: "1px solid rgba(210,153,34,0.25)"
        }}>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: "var(--space-2)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Clarifying Question
          </p>
          <p style={{ color: "var(--text-primary)", margin: 0, lineHeight: 1.6 }}>{question}</p>
        </div>

        {/* Answer form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <textarea
            id="hitl-answer"
            className="textarea"
            rows={5}
            placeholder="Provide as much specific detail as possible. Your answer will be incorporated into the digital twin and re-evaluated."
            value={answer}
            onChange={e => { setAnswer(e.target.value); setError(null); }}
            disabled={isSubmitting}
            autoFocus
          />

          {error && (
            <div style={{
              display: "flex", alignItems: "center", gap: "var(--space-2)",
              padding: "var(--space-3)", borderRadius: "var(--radius-sm)",
              background: "rgba(248,81,73,0.10)", border: "1px solid var(--danger)",
              color: "var(--danger)", fontSize: "0.85rem"
            }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button
            id="hitl-submit"
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting || !answer.trim()}
            style={{ width: "100%" }}
          >
            {isSubmitting ? (
              <><span className="spinner" style={{ width: 16, height: 16 }} /> Resuming Evaluation…</>
            ) : (
              <><Send size={16} /> Submit Answer & Resume</>
            )}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Your answer is merged into the digital twin, then the affected agents re-evaluate.
          A sensitivity sweep will also show how the decision changes across similar values.
        </p>
      </div>
    </div>
  );
}
