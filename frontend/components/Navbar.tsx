import Link from "next/link";
import { Sparkles } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="nav">
      <div className="container flex items-center justify-between">
        <Link href="/" className="nav-logo" id="nav-logo">
          <Sparkles size={18} />
          AIRB
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            AI Review Board
          </span>
        </div>
      </div>
    </nav>
  );
}
