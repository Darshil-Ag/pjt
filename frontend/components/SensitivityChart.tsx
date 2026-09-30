"use client";

import React, { useState } from "react";
import type { SweepResult, Decision } from "@/lib/api";

const DOMAIN_COLORS: Record<string, string> = {
  Finance:    "#22c55e",
  Legal:      "#f59e0b",
  Market:     "#3b82f6",
  Operations: "#f97316",
  Technology: "#a855f7",
};

const DECISION_DOT: Record<Decision, string> = {
  PROCEED:    "#22c55e",
  REVIEW:     "#f59e0b",
  "HIGH-RISK":"#ef4444",
};

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(1);
}

interface SensitivityChartProps {
  sweep: SweepResult;
}

export function SensitivityChart({ sweep }: SensitivityChartProps) {
  const domains = Object.keys(sweep.by_domain);
  const [activeDomain, setActiveDomain] = useState<string>(domains[0] ?? "Finance");

  const series = sweep.by_domain[activeDomain] ?? [];
  const baseline = sweep.baseline;
  const flips = sweep.decision_flips;

  // SVG dimensions
  const W = 480, H = 200, PAD = 40;
  const plotW = W - PAD * 2;
  const plotH = H - PAD * 2 - 10;

  // Score range: floor to 0–100 with a window
  const scores = series.map(p => p.final_score).filter(Boolean) as number[];
  const minScore = Math.max(0, Math.min(...scores) - 10);
  const maxScore = Math.min(100, Math.max(...scores) + 10);
  const scoreRange = maxScore - minScore || 1;

  const pts = series.map((p, i) => {
    const x = PAD + (i / (series.length - 1)) * plotW;
    const y = PAD + plotH - ((p.final_score - minScore) / scoreRange) * plotH;
    return { x, y, ...p };
  });

  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  const baselineY = PAD + plotH - ((baseline.final_score - minScore) / scoreRange) * plotH;

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      padding: "var(--space-6)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-4)",
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-3)" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "var(--text-base)", fontWeight: 700, color: "var(--text-primary)" }}>
            Sensitivity Analysis
          </h3>
          <p style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            How Final Score shifts as each domain weight varies ±20%
          </p>
        </div>
        {flips.length > 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: "var(--space-2)",
            background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "var(--radius-sm)", padding: "4px 10px",
            fontSize: "var(--text-xs)", color: "#ef4444", fontWeight: 600,
          }}>
            ⚠ Decision flips: {flips.join(", ")}
          </div>
        )}
      </div>

      {/* Domain selector tabs */}
      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
        {domains.map(d => {
          const isFlip = flips.includes(d);
          const isActive = d === activeDomain;
          return (
            <button
              key={d}
              onClick={() => setActiveDomain(d)}
              style={{
                padding: "4px 12px",
                borderRadius: "var(--radius-sm)",
                border: `1px solid ${isActive ? DOMAIN_COLORS[d] : "var(--border)"}`,
                background: isActive ? `${DOMAIN_COLORS[d]}20` : "transparent",
                color: isActive ? DOMAIN_COLORS[d] : "var(--text-secondary)",
                fontSize: "var(--text-xs)",
                fontWeight: isActive ? 700 : 400,
                cursor: "pointer",
                position: "relative",
              }}
            >
              {d}
              {isFlip && <span style={{ marginLeft: 4, color: "#ef4444" }}>⚠</span>}
            </button>
          );
        })}
      </div>

      {/* SVG chart */}
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: "visible" }}>
        {/* Baseline dashed line */}
        <line
          x1={PAD} y1={baselineY} x2={W - PAD} y2={baselineY}
          stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4 4"
        />
        <text x={W - PAD + 4} y={baselineY + 4} fontSize={9} fill="rgba(255,255,255,0.4)">
          {fmt(baseline.final_score)}
        </text>

        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map(v => {
          const gy = PAD + plotH - ((v - minScore) / scoreRange) * plotH;
          if (gy < PAD || gy > PAD + plotH) return null;
          return (
            <g key={v}>
              <line x1={PAD} y1={gy} x2={W - PAD} y2={gy}
                stroke="rgba(255,255,255,0.04)" strokeWidth={1} />
              <text x={PAD - 4} y={gy + 4} fontSize={9} fill="rgba(255,255,255,0.3)" textAnchor="end">
                {v}
              </text>
            </g>
          );
        })}

        {/* Area fill */}
        {pts.length > 1 && (
          <path
            d={`${pathD} L ${pts[pts.length-1].x} ${PAD + plotH} L ${pts[0].x} ${PAD + plotH} Z`}
            fill={`${DOMAIN_COLORS[activeDomain]}18`}
          />
        )}

        {/* Line */}
        {pts.length > 1 && (
          <path d={pathD} fill="none" stroke={DOMAIN_COLORS[activeDomain]} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        )}

        {/* Data points */}
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={5} fill={DOMAIN_COLORS[activeDomain]} />
            <circle cx={p.x} cy={p.y} r={3} fill={DECISION_DOT[p.decision as Decision] ?? "#888"} />
            {/* X-axis label */}
            <text x={p.x} y={PAD + plotH + 16} fontSize={9} fill="rgba(255,255,255,0.5)" textAnchor="middle">
              {p.delta_pct > 0 ? "+" : ""}{p.delta_pct}%
            </text>
            {/* Score label on hover via title */}
            <title>{`Weight ${p.delta_pct > 0 ? "+" : ""}${p.delta_pct}%: Score=${fmt(p.final_score)}, ${p.decision}`}</title>
          </g>
        ))}

        {/* X-axis label */}
        <text x={W / 2} y={H - 2} fontSize={9} fill="rgba(255,255,255,0.3)" textAnchor="middle">
          Weight Perturbation (%)
        </text>
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
        {(["PROCEED", "REVIEW", "HIGH-RISK"] as Decision[]).map(d => (
          <span key={d} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: DECISION_DOT[d], display: "inline-block" }} />
            {d}
          </span>
        ))}
        <span style={{ marginLeft: "auto" }}>Baseline: <strong style={{ color: "var(--text-primary)" }}>{fmt(baseline.final_score)}</strong> ({baseline.decision})</span>
      </div>
    </div>
  );
}
