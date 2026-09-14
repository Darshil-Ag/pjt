import Navbar from "@/components/Navbar";
import PitchForm from "@/components/PitchForm";
import { Layers, ShieldCheck, BarChart2, Cpu } from "lucide-react";

const FEATURES = [
  {
    icon: <Layers size={22} color="var(--accent-400)" />,
    title: "Five Domain Specialists",
    body: "Finance, Legal, Market, Operations, and Technology agents evaluate your pitch in parallel against retrieved historical precedent.",
  },
  {
    icon: <ShieldCheck size={22} color="var(--success)" />,
    title: "Calibrated Evidence Weighting",
    body: "Each agent's authority is mathematically calibrated against real outcomes — not asserted by another LLM. Every score cites specific cases.",
  },
  {
    icon: <BarChart2 size={22} color="var(--warning)" />,
    title: "Auditable Decision Fusion",
    body: "Final score computed as Σ(Wᵢ·Cᵢ·Sᵢ) / Σ(Wᵢ·Cᵢ). Three-way verdict: Proceed / High-Risk / Review. Fully traceable.",
  },
  {
    icon: <Cpu size={22} color="var(--info)" />,
    title: "Human-in-the-Loop Escalation",
    body: "When agents disagree beyond a calibrated threshold, the system pauses and asks a targeted clarifying question before re-evaluating.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        {/* Hero */}
        <section className="hero">
          <div className="hero-glow" />
          <div className="container">
            <div style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", padding: "4px 14px", borderRadius: "999px", background: "rgba(105,65,239,0.12)", border: "1px solid var(--accent-500)", marginBottom: "var(--space-6)" }}>
              <span style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent-300)" }}>
                Research Capstone · Sprint 1
              </span>
            </div>
            <h1 style={{ marginBottom: "var(--space-5)" }}>
              Evidence-Calibrated<br />
              <span style={{ background: "linear-gradient(135deg, var(--accent-400) 0%, var(--accent-300) 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Multi-Agent
              </span>{" "}
              Decision Fusion
            </h1>
            <p className="hero-tagline">
              Submit your startup pitch. Five domain-specialist AI agents evaluate it against
              150+ historical precedents. A deterministic fusion engine — not an LLM judge —
              produces an auditable PROCEED / HIGH-RISK / REVIEW verdict with full evidence trail.
            </p>
          </div>
        </section>

        {/* Pitch Form */}
        <section style={{ padding: "0 0 var(--space-16)" }}>
          <div className="container">
            <div style={{ maxWidth: 760, margin: "0 auto" }}>
              <div className="card glow-border" style={{ padding: "var(--space-8)" }}>
                <h2 style={{ marginBottom: "var(--space-2)" }}>Submit Your Pitch</h2>
                <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-6)", fontSize: "0.9rem" }}>
                  Describe your startup in plain language. The more detail, the better the grounding.
                </p>
                <PitchForm />
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section style={{ padding: "var(--space-12) 0 var(--space-16)", borderTop: "1px solid var(--border)" }}>
          <div className="container">
            <div style={{ textAlign: "center", marginBottom: "var(--space-12)" }}>
              <h2 style={{ marginBottom: "var(--space-4)" }}>How AIRB Works</h2>
              <p style={{ color: "var(--text-muted)", maxWidth: 520, margin: "0 auto" }}>
                A layered, orchestrated pipeline where all subjective judgment stays inside the LLM agent layer
                and all weighting and routing logic is deterministic Python.
              </p>
            </div>
            <div className="grid grid-2 gap-6">
              {FEATURES.map(f => (
                <div key={f.title} className="card">
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
                    {f.icon}
                    <h4>{f.title}</h4>
                  </div>
                  <p style={{ fontSize: "0.88rem", lineHeight: 1.7 }}>{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline diagram */}
        <section style={{ padding: "var(--space-8) 0 var(--space-16)", borderTop: "1px solid var(--border)" }}>
          <div className="container">
            <h2 style={{ textAlign: "center", marginBottom: "var(--space-8)" }}>Pipeline Topology</h2>
            <div style={{ maxWidth: 900, margin: "0 auto" }}>
              <div className="card" style={{ padding: "var(--space-6)" }}>
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: "var(--space-3)", fontSize: "0.82rem" }}>
                  {[
                    "Context Router",
                    "→",
                    "Retrieval Node",
                    "→",
                    "Parallel Dispatch",
                    "→",
                    "Conflict Index",
                    "⇒ HITL (if CI>θ)",
                    "→",
                    "Fusion Node",
                    "→",
                    "Sensitivity Sweep",
                    "→",
                    "Red Team Check",
                    "→",
                    "Evaluation Logger",
                  ].map((step, i) => (
                    <span key={i} style={{
                      color: step.startsWith("→") || step.startsWith("⇒") ? "var(--text-muted)" :
                             step.includes("HITL") ? "var(--warning)" :
                             step.includes("Red Team") ? "var(--danger)" :
                             step.includes("Fusion") ? "var(--success)" : "var(--text-secondary)",
                      fontWeight: step.startsWith("→") || step.startsWith("⇒") ? 400 : 600,
                      padding: step.startsWith("→") || step.startsWith("⇒") ? 0 : "4px 10px",
                      borderRadius: step.startsWith("→") || step.startsWith("⇒") ? 0 : "var(--radius-sm)",
                      background: step.startsWith("→") || step.startsWith("⇒") ? "transparent" : "var(--bg-elevated)",
                      border: step.startsWith("→") || step.startsWith("⇒") ? "none" : "1px solid var(--border)",
                    }}>
                      {step}
                    </span>
                  ))}
                </div>
                <p style={{ textAlign: "center", marginTop: "var(--space-5)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  All weighting, confidence, and routing math is deterministic Python — no LLM calls inside the fusion layer.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
