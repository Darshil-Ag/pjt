"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { submitPitch } from "@/lib/api";
import { Zap, FileText, AlertCircle, DollarSign, Scale, TrendingUp, Settings, Cpu } from "lucide-react";

const EXAMPLE_PITCHES = [
  {
    label: "FinTech – Mobile Payments",
    icon: <DollarSign size={11} />,
    text: `We are building ZunoPay, a B2C mobile payments app targeting unbanked users in rural India. Our team has 3 engineers and 1 designer. We are seeking $500,000 in seed funding. Business model: 1.5% transaction fee on peer-to-peer transfers. Target market: 200M+ unbanked adults in Tier 2 and Tier 3 Indian cities. We plan to integrate with UPI and launch in Maharashtra first.`,
  },
  {
    label: "HealthTech – AI Diagnostics",
    icon: <Cpu size={11} />,
    text: `MedBot Health is an AI-powered diagnostic assistant for rural clinics in Southeast Asia. We use a fine-tuned NLP model trained on 1.2M clinical notes. Budget: $300K seed. Business model: SaaS subscription at $49/month per clinic. Team of 5. Target: 50,000 rural clinics across Vietnam, Indonesia, and Philippines. Current traction: 3 pilot clinics, 12-week retention of 88%.`,
  },
  {
    label: "SaaS – B2B Logistics",
    icon: <Settings size={11} />,
    text: `CargoMatch is a freight brokerage platform connecting truckers to shippers in India. We charge a 3% commission on matched freight. Current GMV: $80K/month. Team: 8 people. Raising $1.5M Series A to expand to 5 new cities and build a driver mobile app. LTV:CAC ratio is 4.1:1. Gross margin: 62%.`,
  },
];

const AGENT_CHIPS = [
  { label: "Finance", color: "#22c55e" },
  { label: "Legal", color: "#f59e0b" },
  { label: "Market", color: "#3b82f6" },
  { label: "Operations", color: "#f97316" },
  { label: "Technology", color: "#a855f7" },
];

export default function PitchForm() {
  const router = useRouter();
  const [pitch, setPitch] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const charCount = pitch.length;
  const isReady = pitch.trim().length > 40;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pitch.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);

    try {
      const res = await submitPitch(pitch.trim());
      router.push(`/decision/${res.evaluation_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="fade-in" style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>

      {/* Example pitch loader */}
      <div>
        <p style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "var(--space-2)" }}>
          Load an example pitch
        </p>
        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
          {EXAMPLE_PITCHES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              id={`example-${ex.label.toLowerCase().replace(/\W+/g, "-")}`}
              className="btn btn-ghost btn-sm"
              onClick={() => { setPitch(ex.text); setError(null); }}
              style={{
                fontSize: "0.78rem",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                gap: "var(--space-1)",
              }}
            >
              {ex.icon}
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {/* Pitch textarea */}
      <div style={{ position: "relative" }}>
        <textarea
          id="pitch-input"
          className="textarea"
          rows={11}
          placeholder={`Describe your startup in detail. Include:\n\n• Industry & target market\n• Business model & revenue strategy  \n• Team size & key expertise\n• Funding ask & use of capital\n• Current traction (users, revenue, pilots)\n\nThe more detail you provide, the better the evidence grounding.`}
          value={pitch}
          onChange={(e) => { setPitch(e.target.value); setError(null); }}
          disabled={isLoading}
          style={{
            minHeight: "280px",
            fontSize: "0.9rem",
            lineHeight: 1.7,
            transition: "border-color var(--t-fast), box-shadow var(--t-fast)",
          }}
        />
        {/* Char counter */}
        <div style={{
          position: "absolute", bottom: "var(--space-3)", right: "var(--space-4)",
          display: "flex", alignItems: "center", gap: "var(--space-2)",
        }}>
          {isReady && (
            <span style={{ fontSize: "0.65rem", color: "var(--success)", fontWeight: 600 }}>✓ Ready</span>
          )}
          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            {charCount.toLocaleString()} chars
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          display: "flex", alignItems: "flex-start", gap: "var(--space-3)",
          padding: "var(--space-4)", borderRadius: "var(--radius-md)",
          background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.35)",
          color: "var(--danger)", fontSize: "0.85rem",
          boxShadow: "0 0 16px var(--danger-glow)",
        }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong style={{ display: "block", marginBottom: 2 }}>Evaluation Failed</strong>
            {error}
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        id="submit-evaluate"
        type="submit"
        className="btn btn-primary btn-lg"
        disabled={isLoading || !isReady}
        style={{
          width: "100%",
          justifyContent: "center",
          gap: "var(--space-3)",
          fontSize: "1rem",
          padding: "16px",
        }}
      >
        {isLoading ? (
          <>
            <span className="spinner" style={{ width: 18, height: 18 }} />
            Queueing Evaluation…
          </>
        ) : (
          <>
            <Zap size={18} />
            Evaluate Startup
          </>
        )}
      </button>

      {/* Agent info */}
      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
          Your pitch will be evaluated by 5 specialist agents in parallel
        </p>
        <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "center", flexWrap: "wrap" }}>
          {AGENT_CHIPS.map(chip => (
            <span key={chip.label} style={{
              fontSize: "0.65rem", fontWeight: 700,
              color: chip.color,
              background: `${chip.color}12`,
              border: `1px solid ${chip.color}30`,
              padding: "2px 8px", borderRadius: "999px",
              letterSpacing: "0.04em", textTransform: "uppercase",
            }}>
              {chip.label}
            </span>
          ))}
        </div>
      </div>
    </form>
  );
}
