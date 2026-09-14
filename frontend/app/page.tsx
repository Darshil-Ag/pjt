import Navbar from "@/components/Navbar";
import PitchForm from "@/components/PitchForm";
import { Users, BookOpen, Scale, ShieldAlert } from "lucide-react";

const FEATURES = [
  {
    icon: <Users size={16} color="var(--text-primary)" />,
    title: "Five Specialist Agents",
    body: "Finance, Legal, Market, Operations, and Technology domain agents evaluate your pitch independently.",
  },
  {
    icon: <BookOpen size={16} color="var(--text-primary)" />,
    title: "Historical Evidence RAG",
    body: "Anchors reasoning against retrieved historical precedent cases from ChromaDB vector index.",
  },
  {
    icon: <Scale size={16} color="var(--text-primary)" />,
    title: "Deterministic Fusion",
    body: "Combines domain scores mathematically using evidence confidence and relevance weighting.",
  },
  {
    icon: <ShieldAlert size={16} color="var(--text-primary)" />,
    title: "HITL & Red Team",
    body: "Detects domain conflicts for founder clarification and stress-tests for fatal blind spots.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main style={{ padding: "var(--space-10) 0 var(--space-16)" }}>
        <div className="container">
          {/* Hero Heading */}
          <div style={{ textAlign: "center", marginBottom: "var(--space-8)" }}>
            <h1 style={{
              fontSize: "2.5rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              marginBottom: "var(--space-2)"
            }}>
              Evaluate Your Startup
            </h1>
            <p style={{
              color: "var(--text-muted)",
              fontSize: "1.08rem",
              maxWidth: 520,
              margin: "0 auto",
              lineHeight: 1.5
            }}>
              Get an AI-powered multi-domain assessment of your startup idea.
            </p>
          </div>

          {/* Prompt Form Container */}
          <div style={{ maxWidth: 760, margin: "0 auto var(--space-12)" }}>
            <PitchForm />
          </div>

          {/* Minimal Feature Cards Grid */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: "var(--space-10)" }}>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "var(--space-4)"
            }}>
              {FEATURES.map(f => (
                <div
                  key={f.title}
                  className="card card-hover"
                  style={{
                    padding: "var(--space-5)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-3)",
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-lg)"
                  }}
                >
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                  }}>
                    {f.icon}
                  </div>
                  <div>
                    <h4 style={{ fontSize: "0.92rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                      {f.title}
                    </h4>
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.55, margin: 0 }}>
                      {f.body}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
