"use client";

import Link from "next/link";
import { Activity, Cpu } from "lucide-react";
import { useState, useEffect } from "react";
import { checkHealth } from "@/lib/api";

export default function Navbar() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <nav className="nav">
      <div className="container flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="nav-logo" id="nav-logo">
          <div style={{
            width: 32, height: 32,
            borderRadius: "var(--radius-sm)",
            background: "linear-gradient(135deg, var(--accent-600), var(--accent-400))",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 12px var(--accent-glow)",
          }}>
            <Activity size={16} color="#fff" />
          </div>
          AIR<span>B</span>
        </Link>

        {/* Center label */}
        <div style={{
          display: "flex", alignItems: "center", gap: "var(--space-2)",
          padding: "4px 12px",
          borderRadius: "999px",
          background: "rgba(105, 65, 239, 0.08)",
          border: "1px solid rgba(105, 65, 239, 0.2)",
        }}>
          <Cpu size={11} color="var(--accent-300)" />
          <span style={{ fontSize: "0.72rem", color: "var(--accent-300)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            Multi-Agent Decision Fusion
          </span>
        </div>

        {/* Right side */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          {/* API Health dot */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: healthy === null ? "var(--text-muted)" : healthy ? "var(--success)" : "var(--danger)",
              boxShadow: healthy ? "0 0 6px var(--success-glow)" : undefined,
              animation: healthy === null ? "pulse 1.5s ease-in-out infinite" : undefined,
            }} />
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 500 }}>
              {healthy === null ? "Connecting…" : healthy ? "API Live" : "Offline"}
            </span>
          </div>

          <span className="badge badge-neutral" style={{ fontSize: "0.65rem", letterSpacing: "0.06em" }}>
            Sprint 1
          </span>

          <a
            href="https://github.com/Darshil-Ag/pjt"
            target="_blank" rel="noopener noreferrer"
            id="nav-github"
            style={{
              display: "flex", alignItems: "center", gap: "var(--space-1)",
              color: "var(--text-muted)", fontSize: "0.78rem",
              transition: "color var(--t-fast)",
            }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
          </a>
        </div>
      </div>
    </nav>
  );
}
