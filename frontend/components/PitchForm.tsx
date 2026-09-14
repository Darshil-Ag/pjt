"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { submitPitch } from "@/lib/api";
import { ArrowUp, AlertCircle, FileText } from "lucide-react";

const EXAMPLE_PITCHES = [
  {
    label: "FinTech Payments",
    text: `We are building ZunoPay, a B2C mobile payments app targeting unbanked users in rural India. Our team has 3 engineers and 1 designer. We are seeking $500,000 in seed funding. Business model: 1.5% transaction fee on peer-to-peer transfers. Target market: 200M+ unbanked adults in Tier 2 and Tier 3 Indian cities. We plan to integrate with UPI and launch in Maharashtra first.`,
  },
  {
    label: "HealthTech AI",
    text: `MedBot Health is an AI-powered diagnostic assistant for rural clinics in Southeast Asia. We use a fine-tuned NLP model trained on 1.2M clinical notes. Budget: $300K seed. Business model: SaaS subscription at $49/month per clinic. Team of 5. Target: 50,000 rural clinics across Vietnam, Indonesia, and Philippines. Current traction: 3 pilot clinics, 12-week retention of 88%.`,
  },
  {
    label: "B2B Logistics",
    text: `CargoMatch is a freight brokerage platform connecting truckers to shippers in India. We charge a 3% commission on matched freight. Current GMV: $80K/month. Team: 8 people. Raising $1.5M Series A to expand to 5 new cities and build a driver mobile app. LTV:CAC ratio is 4.1:1. Gross margin: 62%.`,
  },
];

export default function PitchForm() {
  const router = useRouter();
  const [pitch, setPitch] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      {/* Input container styled like a clean prompt box */}
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-xl)",
          background: "var(--bg-surface)",
          padding: "var(--space-4)",
          boxShadow: "var(--shadow-md)",
          transition: "border-color 0.15s ease",
        }}
      >
        <textarea
          id="pitch-input"
          className="textarea"
          rows={6}
          placeholder="Describe your startup, business model, market, team, funding, technology, and any known risks..."
          value={pitch}
          onChange={(e) => { setPitch(e.target.value); setError(null); }}
          disabled={isLoading}
          style={{
            border: "none",
            boxShadow: "none",
            padding: 0,
            fontSize: "0.98rem",
            lineHeight: 1.6,
            minHeight: "160px",
            background: "transparent",
          }}
        />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "var(--space-3)", borderTop: "1px solid var(--bg-elevated)" }}>
          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
            {EXAMPLE_PITCHES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => { setPitch(ex.text); setError(null); }}
                style={{ fontSize: "0.78rem", padding: "3px 8px" }}
              >
                <FileText size={12} />
                {ex.label}
              </button>
            ))}
          </div>

          <button
            id="submit-evaluate"
            type="submit"
            className="btn btn-primary"
            disabled={isLoading || !pitch.trim()}
            style={{ borderRadius: "var(--radius-md)", padding: "8px 16px" }}
          >
            {isLoading ? (
              <span className="spinner" style={{ width: 14, height: 14, borderTopColor: "#fff" }} />
            ) : (
              <>
                Evaluate Startup
                <ArrowUp size={16} />
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-md)",
          background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
          color: "var(--danger-text)", fontSize: "0.88rem"
        }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}
    </form>
  );
}
