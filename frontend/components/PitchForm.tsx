"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { submitPitch } from "@/lib/api";
import { Zap, FileText, AlertCircle } from "lucide-react";

const EXAMPLE_PITCHES = [
  {
    label: "FinTech – Mobile Payments",
    text: `We are building ZunoPay, a B2C mobile payments app targeting unbanked users in rural India. Our team has 3 engineers and 1 designer. We are seeking $500,000 in seed funding. Business model: 1.5% transaction fee on peer-to-peer transfers. Target market: 200M+ unbanked adults in Tier 2 and Tier 3 Indian cities. We plan to integrate with UPI and launch in Maharashtra first.`,
  },
  {
    label: "HealthTech – AI Diagnostics",
    text: `MedBot Health is an AI-powered diagnostic assistant for rural clinics in Southeast Asia. We use a fine-tuned NLP model trained on 1.2M clinical notes. Budget: $300K seed. Business model: SaaS subscription at $49/month per clinic. Team of 5. Target: 50,000 rural clinics across Vietnam, Indonesia, and Philippines. Current traction: 3 pilot clinics, 12-week retention of 88%.`,
  },
  {
    label: "SaaS – B2B Logistics",
    text: `CargoMatch is a freight brokerage platform connecting truckers to shippers in India. We charge a 3% commission on matched freight. Current GMV: $80K/month. Team: 8 people. Raising $1.5M Series A to expand to 5 new cities and build a driver mobile app. LTV:CAC ratio is 4.1:1. Gross margin: 62%.`,
  },
];

export default function PitchForm() {
  const router = useRouter();
  const [pitch, setPitch] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const charCount = pitch.length;

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
    <form onSubmit={handleSubmit} className="fade-in" style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Example pitch loader */}
      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
        {EXAMPLE_PITCHES.map((ex) => (
          <button
            key={ex.label}
            type="button"
            id={`example-${ex.label.toLowerCase().replace(/\W+/g, "-")}`}
            className="btn btn-ghost btn-sm"
            onClick={() => { setPitch(ex.text); setError(null); }}
            style={{ fontSize: "0.78rem" }}
          >
            <FileText size={12} />
            {ex.label}
          </button>
        ))}
      </div>

      {/* Pitch textarea */}
      <div style={{ position: "relative" }}>
        <textarea
          id="pitch-input"
          className="textarea"
          rows={10}
          placeholder={`Describe your startup pitch in detail. Include:\n• Industry & target market\n• Business model & revenue strategy\n• Team size & key expertise\n• Funding ask & use of capital\n• Current traction (users, revenue, pilots)\n\nThe more detail you provide, the more precise the analysis.`}
          value={pitch}
          onChange={(e) => { setPitch(e.target.value); setError(null); }}
          disabled={isLoading}
          style={{ minHeight: "280px", fontSize: "0.92rem" }}
        />
        <span style={{
          position: "absolute", bottom: "var(--space-3)", right: "var(--space-4)",
          fontSize: "0.75rem", color: "var(--text-muted)"
        }}>
          {charCount.toLocaleString()} chars
        </span>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-3)",
          padding: "var(--space-4)", borderRadius: "var(--radius-md)",
          background: "rgba(248,81,73,0.10)", border: "1px solid var(--danger)",
          color: "var(--danger)", fontSize: "0.88rem"
        }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Submit */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <button
          id="submit-evaluate"
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={isLoading || !pitch.trim()}
          style={{ flex: 1 }}
        >
          {isLoading ? (
            <>
              <span className="spinner" style={{ width: 18, height: 18 }} />
              Initialising Evaluation…
            </>
          ) : (
            <>
              <Zap size={18} />
              Evaluate Startup
            </>
          )}
        </button>
        {pitch && !isLoading && (
          <button
            id="clear-pitch"
            type="button"
            className="btn btn-ghost"
            onClick={() => { setPitch(""); setError(null); }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Info */}
      <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "center" }}>
        Five domain-specialist agents (Finance, Legal, Market, Operations, Technology) will evaluate your pitch
        against historical precedent using calibrated evidence-weighted fusion.
      </p>
    </form>
  );
}
