import Navbar from "@/components/Navbar";
import PitchForm from "@/components/PitchForm";
import { Users, BookOpen, Scale, ShieldAlert } from "lucide-react";

const FEATURES = [
  {
    icon: <Users size={18} color="var(--text-primary)" />,
    title: "Five Specialist Agents",
    body: "Finance, Legal, Market, Operations, and Technology agents evaluate your pitch independently.",
  },
  {
    icon: <BookOpen size={18} color="var(--text-primary)" />,
    title: "Historical Evidence RAG",
    body: "Anchors reasoning against retrieved historical precedent cases from ChromaDB vector index.",
  },
  {
    icon: <Scale size={18} color="var(--text-primary)" />,
    title: "Deterministic Fusion",
    body: "Combines domain scores mathematically using evidence confidence and relevance weighting.",
  },
  {
    icon: <ShieldAlert size={18} color="var(--text-primary)" />,
    title: "Human-in-the-Loop & Red Team",
    body: "Detects domain conflicts to request founder clarification and stress-tests for fatal blind spots.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main style={{ padding: "var(--space-12) 0" }}>
        <div className="container">
          {/* Header */}
          <div style={{ textAlign: "center", marginBottom: "var(--space-8)" }}>
            <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
              AIRB · AI Review Board
            </div>
            <h1 style={{ marginBottom: "var(--space-3)" }}>Evaluate Your Startup</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "1.05rem", maxWidth: 540, margin: "0 auto" }}>
              Get an AI-powered multi-domain assessment of your startup idea.
            </p>
          </div>

          {/* Prompt Form */}
          <div style={{ maxWidth: 760, margin: "0 auto var(--space-16)" }}>
            <PitchForm />
          </div>

          {/* Minimal Feature Grid */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: "var(--space-12)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-6)" }}>
              {FEATURES.map(f => (
                <div key={f.title} style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", color: "var(--text-primary)", fontWeight: 600, fontSize: "0.92rem" }}>
                    {f.icon}
                    {f.title}
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {f.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
