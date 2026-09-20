import Navbar from "@/components/Navbar";
import PitchForm from "@/components/PitchForm";
import { Layers, ShieldCheck, BarChart2, Cpu, Database, GitBranch, Zap, ArrowRight } from "lucide-react";

const FEATURES = [
  {
    icon: <Layers size={20} />,
    color: "var(--accent-400)",
    glow: "rgba(105, 65, 239, 0.2)",
    title: "Five Domain Specialists",
    body: "Finance, Legal, Market, Operations, and Technology agents evaluate your pitch in parallel against retrieved historical precedent.",
  },
  {
    icon: <ShieldCheck size={20} />,
    color: "var(--success)",
    glow: "rgba(34, 197, 94, 0.2)",
    title: "Calibrated Evidence Weighting",
    body: "Each agent's authority is mathematically calibrated against real outcomes — not asserted by another LLM. Every score cites specific cases.",
  },
  {
    icon: <BarChart2 size={20} />,
    color: "var(--warning)",
    glow: "rgba(245, 158, 11, 0.2)",
    title: "Auditable Decision Fusion",
    body: "Final score computed as Σ(Wᵢ·Cᵢ·Sᵢ) / Σ(Wᵢ·Cᵢ). Three-way verdict: Proceed / High-Risk / Review. Fully traceable.",
  },
  {
    icon: <Database size={20} />,
    color: "var(--cyan-400)",
    glow: "rgba(6, 182, 212, 0.2)",
    title: "RAG Grounding Engine",
    body: "Vector-indexed case library of 409 real-world startup failures. Evidence is cited by ID — you can verify every claim.",
  },
  {
    icon: <Cpu size={20} />,
    color: "#a855f7",
    glow: "rgba(168, 85, 247, 0.2)",
    title: "Red Team Adversarial Check",
    body: "A dedicated Red Team agent actively tries to find fatal flaws that the other agents missed. It can override the final verdict.",
  },
  {
    icon: <GitBranch size={20} />,
    color: "#f97316",
    glow: "rgba(249, 115, 22, 0.2)",
    title: "Sensitivity Sweep Analysis",
    body: "The system varies the conflict threshold across 5 datapoints and shows you exactly when the decision would flip, proving robustness.",
  },
];

const PIPELINE = [
  { name: "Context Router", color: "var(--accent-400)", sub: "Gemini" },
  { name: "RAG Retrieval", color: "var(--cyan-400)", sub: "ChromaDB" },
  { name: "5× Domain Agents", color: "#a855f7", sub: "Groq / Parallel" },
  { name: "Conflict Index", color: "var(--warning)", sub: "Python Math" },
  { name: "Fusion Engine", color: "var(--success)", sub: "Deterministic" },
  { name: "Red Team", color: "var(--danger)", sub: "Adversarial" },
  { name: "Verdict", color: "var(--accent-300)", sub: "PROCEED / REVIEW / HIGH-RISK" },
];

const STATS = [
  { value: "409", label: "Real-world Cases", sub: "Indexed in ChromaDB" },
  { value: "5", label: "Domain Agents", sub: "Finance, Legal, Market, Ops, Tech" },
  { value: "3", label: "Verdict Classes", sub: "Proceed · Review · High-Risk" },
  { value: "100%", label: "Math Fusion", sub: "No LLM in the scoring layer" },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main>

        {/* ── Hero ──────────────────────────────────────────── */}
        <section className="hero">
          <div className="hero-glow" />
          <div className="hero-grid" />
          <div className="container">

            {/* Eyebrow badge */}
            <div style={{
              display: "inline-flex", alignItems: "center", gap: "var(--space-2)",
              padding: "5px 16px", borderRadius: "999px",
              background: "rgba(105,65,239,0.1)",
              border: "1px solid rgba(105, 65, 239, 0.35)",
              marginBottom: "var(--space-6)",
              boxShadow: "0 0 20px rgba(105, 65, 239, 0.1)",
            }}>
              <Zap size={11} color="var(--accent-300)" />
              <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--accent-300)" }}>
                Research Capstone · AIRB Framework
              </span>
            </div>

            <h1 style={{ marginBottom: "var(--space-5)" }}>
              AI Investment Risk<br />
              <span style={{
                background: "linear-gradient(135deg, var(--accent-300) 0%, var(--cyan-400) 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>
                Board
              </span>
            </h1>

            <p className="hero-tagline">
              Submit your startup pitch. Five domain-specialist AI agents evaluate it against{" "}
              <strong style={{ color: "var(--text-primary)" }}>409 real-world failure cases</strong>.
              A deterministic fusion engine — not an LLM judge — produces an auditable{" "}
              <strong style={{ color: "var(--success)" }}>PROCEED</strong> /{" "}
              <strong style={{ color: "var(--warning)" }}>REVIEW</strong> /{" "}
              <strong style={{ color: "var(--danger)" }}>HIGH-RISK</strong> verdict with a full evidence trail.
            </p>

            {/* Quick stats row */}
            <div style={{
              display: "flex", gap: "var(--space-6)", justifyContent: "center",
              flexWrap: "wrap", marginBottom: "var(--space-10)",
            }}>
              {STATS.map(s => (
                <div key={s.label} style={{ textAlign: "center" }}>
                  <div style={{
                    fontSize: "1.8rem", fontWeight: 900, letterSpacing: "-0.04em",
                    background: "linear-gradient(135deg, #f1f5ff, var(--accent-300))",
                    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                    lineHeight: 1,
                  }}>{s.value}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Pitch Form ─────────────────────────────────────── */}
        <section style={{ padding: "0 0 var(--space-20)" }}>
          <div className="container">
            <div style={{ maxWidth: 780, margin: "0 auto" }}>
              <div className="card glow-border" style={{ padding: "var(--space-10)" }}>
                <div style={{ marginBottom: "var(--space-6)" }}>
                  <h2 style={{ marginBottom: "var(--space-2)" }}>Submit Your Pitch</h2>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                    Describe your startup in plain language. The more detail you provide, the better the evidence grounding.
                  </p>
                </div>
                <PitchForm />
              </div>
            </div>
          </div>
        </section>

        {/* ── Pipeline Visualization ──────────────────────────── */}
        <section style={{ padding: "var(--space-12) 0 var(--space-20)", borderTop: "1px solid var(--border-subtle)" }}>
          <div className="container">
            <div style={{ textAlign: "center", marginBottom: "var(--space-12)" }}>
              <h2 style={{ marginBottom: "var(--space-3)" }}>Pipeline Architecture</h2>
              <p style={{ color: "var(--text-muted)", maxWidth: 540, margin: "0 auto", fontSize: "0.9rem" }}>
                All subjective reasoning stays inside the agent layer. Weighting, confidence, and routing logic is deterministic Python.
              </p>
            </div>

            <div style={{ maxWidth: 1000, margin: "0 auto" }}>
              <div className="card" style={{ padding: "var(--space-8)" }}>
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexWrap: "wrap", gap: "var(--space-2)",
                }}>
                  {PIPELINE.map((step, i) => (
                    <div key={step.name} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <div style={{
                        textAlign: "center",
                        padding: "var(--space-3) var(--space-4)",
                        borderRadius: "var(--radius-md)",
                        background: `rgba(${step.color === "var(--accent-400)" ? "105,65,239" : "255,255,255"}, 0.04)`,
                        border: `1px solid rgba(255,255,255,0.07)`,
                        minWidth: 100,
                      }}>
                        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: step.color, whiteSpace: "nowrap" }}>{step.name}</div>
                        <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: 2, letterSpacing: "0.04em" }}>{step.sub}</div>
                      </div>
                      {i < PIPELINE.length - 1 && (
                        <ArrowRight size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Feature Cards ──────────────────────────────────── */}
        <section style={{ padding: "var(--space-4) 0 var(--space-20)", borderTop: "1px solid var(--border-subtle)" }}>
          <div className="container">
            <div style={{ textAlign: "center", marginBottom: "var(--space-12)" }}>
              <h2 style={{ marginBottom: "var(--space-3)" }}>Why AIRB is Different</h2>
              <p style={{ color: "var(--text-muted)", maxWidth: 520, margin: "0 auto", fontSize: "0.9rem" }}>
                Not a single-prompt wrapper. A multi-layer, evidence-grounded, mathematically-fused system.
              </p>
            </div>
            <div className="grid grid-3 gap-6" style={{ maxWidth: 1100, margin: "0 auto" }}>
              {FEATURES.map(f => (
                <div key={f.title} className="card" style={{ position: "relative", overflow: "hidden" }}>
                  {/* Glow blob */}
                  <div style={{
                    position: "absolute", top: -30, right: -30,
                    width: 100, height: 100,
                    borderRadius: "50%",
                    background: f.glow,
                    filter: "blur(30px)",
                    pointerEvents: "none",
                  }} />
                  <div style={{
                    width: 40, height: 40, borderRadius: "var(--radius-md)",
                    background: f.glow,
                    border: `1px solid ${f.color}30`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginBottom: "var(--space-4)",
                    color: f.color,
                  }}>
                    {f.icon}
                  </div>
                  <h4 style={{ marginBottom: "var(--space-2)", color: "var(--text-primary)" }}>{f.title}</h4>
                  <p style={{ fontSize: "0.85rem", lineHeight: 1.75, color: "var(--text-muted)" }}>{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Footer ─────────────────────────────────────────── */}
        <footer style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "var(--space-8) 0",
          textAlign: "center",
        }}>
          <div className="container">
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              AIRB · AI Investment Risk Board · Research Capstone · Built with Gemini + Groq + LangGraph + ChromaDB
            </p>
          </div>
        </footer>
      </main>
    </>
  );
}
