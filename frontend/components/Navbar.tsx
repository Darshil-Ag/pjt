import Link from "next/link";
import { Sparkles } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="nav">
      <div className="container flex items-center justify-between">
        <Link href="/" className="nav-logo" id="nav-logo">
          <div style={{
            width: 26, height: 26, borderRadius: 6,
            background: "var(--text-primary)", color: "#FFF",
            display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <Sparkles size={14} />
          </div>
          <span style={{ fontWeight: 700, fontSize: "1.05rem", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>AIRB</span>
          <span style={{
            fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)",
            background: "var(--bg-elevated)", border: "1px solid var(--border)",
            padding: "2px 7px", borderRadius: 4
          }}>
            AI Review Board
          </span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)",
            background: "var(--bg-elevated)", border: "1px solid var(--border)",
            padding: "3px 10px", borderRadius: 999
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} />
            Grounded RAG Pipeline
          </div>
        </div>
      </div>
    </nav>
  );
}
