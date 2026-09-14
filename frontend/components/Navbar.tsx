import Link from "next/link";
import { Activity } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="nav">
      <div className="container flex items-center justify-between">
        <Link href="/" className="nav-logo" id="nav-logo">
          <Activity size={20} color="var(--accent-400)" />
          AIR<span>B</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Evidence-Calibrated Multi-Agent Decision Fusion
          </span>
          <span className="badge badge-neutral" style={{ fontSize: "0.7rem" }}>
            Sprint 1
          </span>
        </div>
      </div>
    </nav>
  );
}
