"use client";

import { FileDown } from "lucide-react";
import type { DecisionTrace } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 1): string {
  if (n == null) return "\u2014";
  return n.toFixed(decimals);
}

function pct(n: number | undefined | null): string {
  if (n == null) return "\u2014";
  return (n * 100).toFixed(1) + "%";
}

function formatDate(): string {
  return new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function verdictColor(decision: string): string {
  if (decision === "PROCEED") return "#16a34a";
  if (decision === "HIGH-RISK") return "#dc2626";
  return "#d97706";
}

function verdictBg(decision: string): string {
  if (decision === "PROCEED") return "#f0fdf4";
  if (decision === "HIGH-RISK") return "#fef2f2";
  return "#fffbeb";
}

function verdictLabel(decision: string): string {
  if (decision === "PROCEED") return "\u2713  PROCEED";
  if (decision === "HIGH-RISK") return "\u2717  HIGH-RISK";
  return "\u26a0  REVIEW";
}

const DOMAIN_COLORS: Record<string, string> = {
  Finance: "#16a34a",
  Legal: "#d97706",
  Market: "#2563eb",
  Operations: "#ea580c",
  Technology: "#7c3aed",
};

// ── HTML Generator ────────────────────────────────────────────────────────────

function buildReportHTML(trace: DecisionTrace): string {
  const domains = Object.keys(trace.agent_scores);
  const decision = trace.decision ?? "REVIEW";
  const vc = verdictColor(decision);
  const vb = verdictBg(decision);

  // Agent rows
  const agentRows = domains
    .map((d) => {
      const score = trace.agent_scores[d];
      const weight = trace.agent_weights[d];
      const conf = trace.agent_confidences[d];
      const claim = (trace.agent_claims[d] ?? "\u2014").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const cited = (trace.agent_citations[d] ?? []).join(", ") || "\u2014";
      const color = DOMAIN_COLORS[d] ?? "#374151";
      const scoreBar = Math.round((score / 100) * 80);
      return `<tr>
        <td><span style="display:inline-block;width:7pt;height:7pt;border-radius:50%;background:${color};margin-right:5pt;vertical-align:middle"></span><strong>${d}</strong></td>
        <td style="text-align:center">
          <div style="display:flex;align-items:center;gap:6pt">
            <div style="width:80pt;height:6pt;background:#e5e7eb;border-radius:3pt;overflow:hidden">
              <div style="width:${scoreBar}pt;height:100%;background:${color};border-radius:3pt"></div>
            </div>
            <span style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;color:${color}">${fmt(score, 0)}</span>
          </div>
        </td>
        <td style="text-align:center">${(weight * 100).toFixed(1)}%</td>
        <td style="text-align:center">${pct(conf)}</td>
        <td>${claim}</td>
        <td style="text-align:center;font-size:8pt;color:#6b7280;font-family:'Courier New',monospace">${cited}</td>
      </tr>`;
    })
    .join("");

  // Digital twin rows
  const dt = trace.digital_twin ?? {};
  const dtFields: [string, string][] = [
    ["Industry", String(dt.industry ?? "\u2014")],
    ["Location", String(dt.location ?? "\u2014")],
    ["Budget (USD)", dt.budget != null ? `$${Number(dt.budget).toLocaleString()}` : "\u2014"],
    ["Business Model", String(dt.business_model_summary ?? "\u2014")],
    ["Team Size", dt.team_size != null ? String(dt.team_size) : "\u2014"],
    ["Revenue Model", String(dt.revenue_model ?? "\u2014")],
    ["Target Market", String(dt.target_market ?? "\u2014")],
    ["Competitive Advantage", String(dt.competitive_advantage ?? "\u2014")],
    ["Tech Stack", String(dt.tech_stack ?? "\u2014")],
    ["Regulatory Environment", String(dt.regulatory_environment ?? "\u2014")],
    ["Traction", String(dt.traction ?? "\u2014")],
  ].filter(([, v]) => v !== "\u2014" && v !== "null" && v !== "undefined") as [string, string][];

  const dtRows = dtFields
    .map(([k, v]) => `<tr><td style="font-family:Arial,sans-serif;font-size:8pt;font-weight:600;color:#374151;width:140pt">${k}</td><td>${v.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</td></tr>`)
    .join("");

  // Evidence rows
  const evidenceRows = (trace.retrieved_cases ?? [])
    .map((c, i) => {
      const cid = String(c.case_id ?? `case_${i + 1}`);
      const outcome = String(c.outcome ?? "unknown");
      const risk = String(c.primary_risk_category ?? "General");
      const summary = String(c.root_cause_summary ?? "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const sim = typeof c.similarity_score === "number"
        ? (c.similarity_score * 100).toFixed(1) + "%" : "\u2014";
      const oc = outcome === "success" ? "#16a34a" : outcome === "failed" ? "#dc2626" : "#d97706";
      return `<tr>
        <td><code>${cid}</code></td>
        <td>${String(c.industry ?? "\u2014")}</td>
        <td><strong style="color:${oc}">${outcome.toUpperCase()}</strong></td>
        <td>${risk}</td>
        <td style="text-align:center">${sim}</td>
        <td style="font-size:8pt;color:#374151">${summary}</td>
      </tr>`;
    }).join("");

  // Board transcript
  const transcriptRows = domains.map((d) => {
    const claim = (trace.agent_claims[d] ?? "\u2014").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const cited = (trace.agent_citations[d] ?? []).join(", ") || "\u2014";
    const color = DOMAIN_COLORS[d] ?? "#374151";
    return `<div style="margin-bottom:14pt;padding-bottom:14pt;border-bottom:0.5pt solid #e5e7eb">
      <div style="display:flex;justify-content:space-between;align-items:baseline;padding-left:8pt;border-left:3pt solid ${color};margin-bottom:6pt">
        <span style="font-family:Arial,sans-serif;font-weight:700;font-size:9pt;color:${color}">${d} Specialist</span>
        <span style="font-family:Arial,sans-serif;font-size:8pt;color:#6b7280">Score: ${fmt(trace.agent_scores[d], 0)} / 100</span>
      </div>
      <p style="font-size:9pt;color:#111827;line-height:1.6;font-style:italic;margin-bottom:4pt">&ldquo;${claim}&rdquo;</p>
      <p style="font-size:7.5pt;color:#9ca3af;font-family:'Courier New',monospace">Cited cases: ${cited}</p>
    </div>`;
  }).join("");

  const vi = trace.version_info ?? {};
  const thresholds = (vi.thresholds as Record<string, number>) ?? {};
  const versionRows = [
    ["Worker Model", String(vi.model_worker ?? "\u2014")],
    ["Router Model", String(vi.model_router ?? "\u2014")],
    ["Red Team Model", String(vi.model_red_team ?? "\u2014")],
    ["Prompt Template Version", String(vi.prompt_template_version ?? "\u2014")],
    ["RAG Index Version", String(vi.rag_index_version ?? "\u2014")],
    ["Dataset Version", String(vi.dataset_version ?? "\u2014")],
    ["Weight Calibration", String(vi.weight_calibration_version ?? "\u2014")],
  ].map(([k, v]) => `<tr><td style="font-family:Arial,sans-serif;font-size:8pt;font-weight:600;color:#374151;width:180pt">${k}</td><td>${v}</td></tr>`).join("");

  const sectionBase = trace.hitl_triggered ? 1 : 0;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>AIRB Feasibility Report \u2014 ${trace.evaluation_id}</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:10pt}
body{font-family:"Georgia","Times New Roman",serif;color:#111827;background:#fff;padding:0}
h1,h2,h3,h4{font-family:Arial,"Helvetica Neue",sans-serif}
@page{size:A4;margin:18mm 20mm 18mm 20mm}
@media print{.no-print{display:none!important}.page-break{page-break-before:always}body{font-size:9.5pt}}
table{width:100%;border-collapse:collapse;font-size:8.5pt}
th{background:#1e1b4b;color:#fff;font-family:Arial,sans-serif;font-size:7.5pt;font-weight:600;text-transform:uppercase;letter-spacing:.06em;padding:6pt 8pt;text-align:left}
td{padding:7pt 8pt;border-bottom:.5pt solid #e5e7eb;vertical-align:top}
tr:nth-child(even) td{background:#f9fafb}
code{font-family:"Courier New",monospace;font-size:8.5pt}
.no-print{position:fixed;top:16px;right:16px;display:flex;gap:8px;z-index:9999}
.no-print button{padding:10px 20px;border-radius:6px;border:none;cursor:pointer;font-family:Arial,sans-serif;font-size:13px;font-weight:600}
.btn-print{background:#6d28d9;color:white}
.btn-close{background:#f3f4f6;color:#374151}
</style>
</head>
<body>
<div class="no-print">
  <button class="btn-print" onclick="window.print()">\u2b07 Save as PDF</button>
  <button class="btn-close" onclick="window.close()">\u2715 Close</button>
</div>

<!-- COVER PAGE -->
<div style="display:flex;flex-direction:column;align-items:center;padding:48pt 36pt 36pt;min-height:100vh;text-align:center">
  <div style="font-family:Arial,sans-serif;font-size:32pt;font-weight:900;letter-spacing:-1px;color:#1e1b4b;margin-bottom:4pt">
    AIR<span style="color:#6d28d9">B</span>
  </div>
  <div style="font-family:Arial,sans-serif;font-size:9pt;letter-spacing:.12em;text-transform:uppercase;color:#6b7280;margin-bottom:40pt">
    AI Investment Review Board &middot; Evidence-Calibrated Multi-Agent Framework
  </div>
  <hr style="width:100%;border:none;border-top:2pt solid #1e1b4b;margin:0 0 24pt"/>
  <div style="font-size:22pt;font-weight:700;color:#111827;margin-bottom:8pt;text-transform:uppercase;letter-spacing:.04em;font-family:Arial,sans-serif">
    Startup Feasibility Assessment
  </div>
  <div style="font-size:11pt;color:#4b5563;margin-bottom:40pt">
    Multi-Domain Expert Panel &middot; Adversarial Review &middot; Evidence-Grounded Decision
  </div>
  <div style="display:inline-block;margin:28pt auto;padding:14pt 40pt;border-radius:4pt;font-family:Arial,sans-serif;font-size:20pt;font-weight:900;letter-spacing:.06em;background:${vb};color:${vc};border:2pt solid ${vc}">
    ${verdictLabel(decision)}
  </div>
  <div style="display:flex;gap:28pt;justify-content:center;margin:0 auto 32pt;flex-wrap:wrap">
    ${[
      ["Final Score", `${fmt(trace.final_score, 1)}&thinsp;<span style='font-size:11pt'>/100</span>`],
      ["Uncertainty", `\u00b1${fmt(trace.final_score_uncertainty, 1)}`],
      ["Board Confidence", pct(trace.final_confidence)],
      ["Conflict Index", fmt(trace.conflict_index, 2)],
    ].map(([label, value]) => `
      <div style="text-align:center;font-family:Arial,sans-serif">
        <div style="font-size:18pt;font-weight:700;color:#111827">${value}</div>
        <div style="font-size:7.5pt;color:#6b7280;text-transform:uppercase;letter-spacing:.08em">${label}</div>
      </div>`).join("")}
  </div>
  <hr style="width:100%;border:none;border-top:2pt solid #1e1b4b;margin:0 0 20pt"/>
  <div style="font-family:Arial,sans-serif;font-size:9pt;color:#6b7280;line-height:2">
    <div><strong style="color:#111827">Evaluation ID:</strong>&nbsp; <code>${trace.evaluation_id}</code></div>
    <div><strong style="color:#111827">Generated:</strong>&nbsp; ${formatDate()}</div>
    <div><strong style="color:#111827">Classification:</strong>&nbsp; Confidential &mdash; Internal Use Only</div>
    <div><strong style="color:#111827">Domains Evaluated:</strong>&nbsp; Finance &middot; Legal &middot; Market &middot; Operations &middot; Technology</div>
    <div style="margin-top:10pt;font-size:8pt;color:#9ca3af">
      This report was produced by the AIRB system and does not constitute financial or investment advice.
    </div>
  </div>
</div>

<!-- CONTENT PAGES -->
<div style="padding:28pt 36pt" class="page-break">

  <!-- S1: Executive Summary -->
  <div style="margin-bottom:28pt">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">1</span>
      Executive Summary
    </div>
    <div style="display:flex;gap:16pt;padding:14pt;background:${vb};border:1.5pt solid ${vc};border-radius:4pt;margin-bottom:18pt;align-items:flex-start">
      <div style="padding:6pt 14pt;background:${vc};color:white;font-family:Arial,sans-serif;font-weight:900;font-size:11pt;border-radius:3pt;white-space:nowrap;letter-spacing:.06em">
        ${verdictLabel(decision)}
      </div>
      <div style="font-size:9pt;color:#374151;line-height:1.6">
        The AIRB panel of five domain-specialist AI agents evaluated the submitted startup pitch
        against ${(trace.retrieved_cases ?? []).length > 0 ? trace.retrieved_cases!.length : (trace.retrieved_case_ids?.length ?? 0)} retrieved historical precedent cases.
        The fusion engine computed a weighted evidence score of <strong>${fmt(trace.final_score, 1)} / 100</strong> with
        board confidence of <strong>${pct(trace.final_confidence)}</strong> and an uncertainty band of &plusmn;${fmt(trace.final_score_uncertainty, 1)} points.
        ${trace.hitl_triggered ? "<br/><br/>\u26a0 <strong>Human-in-the-Loop (HITL) escalation was triggered</strong> due to significant inter-agent disagreement." : ""}
        ${trace.red_team_flag ? `<br/><br/>\uD83D\uDEE1 <strong>Red Team flagged a ${(trace.red_team_severity ?? "").toUpperCase()}-severity risk</strong> not addressed by the primary board.` : ""}
      </div>
    </div>
  </div>

  <!-- S2: Submitted Pitch -->
  <div style="margin-bottom:28pt">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">2</span>
      Submitted Startup Pitch
    </div>
    <div style="background:#f9fafb;border:.5pt solid #d1d5db;border-radius:4pt;padding:12pt 14pt;font-size:8.5pt;line-height:1.8;font-style:italic">
      ${(trace.startup_pitch ?? "\u2014").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br/>")}
    </div>
  </div>

  <!-- S3: Digital Twin Profile -->
  ${dtRows ? `
  <div style="margin-bottom:28pt">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">3</span>
      Startup Digital Twin Profile
    </div>
    <p style="font-size:8.5pt;color:#6b7280;margin-bottom:10pt">Structured attributes extracted by the Context Router. Only explicitly stated or directly inferable fields are populated.</p>
    <table><thead><tr><th style="width:140pt">Attribute</th><th>Extracted Value</th></tr></thead><tbody>${dtRows}</tbody></table>
  </div>` : ""}

  <!-- S4: Agent Assessment Matrix -->
  <div style="margin-bottom:28pt" class="page-break">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">4</span>
      Domain Agent Assessment Matrix
    </div>
    <p style="font-size:8.5pt;color:#6b7280;margin-bottom:10pt">Five domain-specialist agents evaluated the startup in parallel. Weights (W\u1d62) are calibrated by domain relevance, not score. Confidence (C\u1d62) uses zero LLM calls.</p>
    <table>
      <thead>
        <tr>
          <th>Domain</th><th>Score / 100</th><th>Weight (W\u1d62)</th>
          <th>Confidence (C\u1d62)</th><th>Assessment</th><th>Cited Cases</th>
        </tr>
      </thead>
      <tbody>${agentRows}</tbody>
      <tfoot>
        <tr style="background:#1e1b4b">
          <td style="color:white;font-family:Arial,sans-serif;font-size:8pt;font-weight:700">FUSED RESULT</td>
          <td style="text-align:center"><span style="color:#a78bfa;font-family:Arial,sans-serif;font-weight:900;font-size:10pt">${fmt(trace.final_score, 1)}</span></td>
          <td style="text-align:center;color:#9ca3af;font-size:8pt">\u03a3 = 100%</td>
          <td style="text-align:center"><span style="color:#a78bfa;font-family:Arial,sans-serif;font-weight:700">${pct(trace.final_confidence)}</span></td>
          <td style="color:#9ca3af;font-size:8pt">\u03a3(W\u1d62\u00b7C\u1d62\u00b7S\u1d62) / \u03a3(W\u1d62\u00b7C\u1d62)</td>
          <td></td>
        </tr>
      </tfoot>
    </table>
    <div style="margin-top:8pt;font-size:7.5pt;color:#9ca3af;text-align:right">
      Fusion score: ${fmt(trace.final_score, 4)} &nbsp;|&nbsp;
      Uncertainty band: \u00b1${fmt(trace.final_score_uncertainty, 4)} &nbsp;|&nbsp;
      \u03c4_approve = ${thresholds.tau_approve ?? 60}, \u03c4_confidence = ${thresholds.tau_confidence ?? 0.40}
    </div>
  </div>

  <!-- S5: HITL (conditional) -->
  ${trace.hitl_triggered ? `
  <div style="margin-bottom:28pt">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">5</span>
      Human-in-the-Loop (HITL) Escalation
    </div>
    <div style="padding:12pt 14pt;background:#fffbeb;border:1.5pt solid #d97706;border-radius:4pt;margin-bottom:14pt">
      <div style="font-family:Arial,sans-serif;font-size:8pt;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#d97706;margin-bottom:8pt">\u26a0 HITL Triggered \u2014 Inter-Agent Conflict Detected</div>
      <div style="display:flex;gap:16pt;flex-wrap:wrap;margin-bottom:8pt">
        <div style="font-size:9pt;flex:1;min-width:120pt"><strong style="font-family:Arial,sans-serif">CI Before HITL:</strong><br/>${fmt(trace.hitl_ci_before, 2)}</div>
        <div style="font-size:9pt;flex:1;min-width:120pt"><strong style="font-family:Arial,sans-serif">CI After HITL:</strong><br/>${trace.hitl_ci_after != null ? fmt(trace.hitl_ci_after, 2) : "Pending"}</div>
        <div style="font-size:9pt;flex:1;min-width:120pt"><strong style="font-family:Arial,sans-serif">Effectiveness (\u0394 CI):</strong><br/>${trace.hitl_effectiveness != null ? fmt(trace.hitl_effectiveness, 4) : "\u2014"}</div>
      </div>
      ${trace.hitl_question ? `<div style="margin-top:8pt"><strong style="font-size:8pt;color:#d97706;font-family:Arial,sans-serif">Clarifying Question:</strong><p style="font-size:9pt;margin-top:4pt;font-style:italic">&ldquo;${trace.hitl_question.replace(/</g, "&lt;").replace(/>/g, "&gt;")}&rdquo;</p></div>` : ""}
      ${trace.hitl_answer ? `<div style="margin-top:8pt"><strong style="font-size:8pt;color:#374151;font-family:Arial,sans-serif">User Response:</strong><p style="font-size:9pt;margin-top:4pt">&ldquo;${trace.hitl_answer.replace(/</g, "&lt;").replace(/>/g, "&gt;")}&rdquo;</p></div>` : ""}
    </div>
  </div>` : ""}

  <!-- S Red Team -->
  <div style="margin-bottom:28pt">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">${5 + sectionBase}</span>
      Red Team Adversarial Review
    </div>
    <p style="font-size:8.5pt;color:#6b7280;margin-bottom:10pt">
      An independent adversarial agent stress-tested the board&rsquo;s decision post-fusion. The Red Team can only escalate toward REVIEW &mdash; never toward PROCEED.
    </p>
    ${trace.red_team_flag ? `
    <div style="padding:12pt 14pt;background:#fef2f2;border:1.5pt solid #dc2626;border-radius:4pt">
      <div style="font-family:Arial,sans-serif;font-size:8pt;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#dc2626;margin-bottom:6pt">\uD83D\uDEE1 Flag Raised &mdash; Severity: ${(trace.red_team_severity ?? "").toUpperCase()}</div>
      <div style="font-size:9pt;color:#374151;line-height:1.6">${(trace.red_team_reasoning ?? "").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
    </div>
    <p style="font-size:8pt;color:${trace.red_team_severity === "high" ? "#dc2626" : "#374151"};margin-top:8pt;font-family:Arial,sans-serif">
      ${trace.red_team_severity === "high" ? "\u2192 High-severity flag triggered automatic decision override to REVIEW." : `\u2192 ${trace.red_team_severity}-severity flag recorded. Primary board decision preserved.`}
    </p>` : `
    <div style="padding:10pt 14pt;background:#f0fdf4;border:1pt solid #16a34a;border-radius:4pt;font-size:9pt;color:#15803d;font-family:Arial,sans-serif">
      \u2713 No material unconsidered risks identified. Board assessment deemed comprehensive.
    </div>`}
  </div>

  <!-- S Evidence -->
  ${(trace.retrieved_cases ?? []).length > 0 ? `
  <div style="margin-bottom:28pt" class="page-break">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">${6 + sectionBase}</span>
      Historical Evidence Base
    </div>
    <p style="font-size:8.5pt;color:#6b7280;margin-bottom:10pt">Top-${trace.retrieved_cases!.length} cases retrieved from ChromaDB via Gemini text-embedding-004 cosine similarity. Test-set cases are hard-excluded (SRS F-03).</p>
    <table>
      <thead>
        <tr><th>Case ID</th><th>Industry</th><th>Outcome</th><th>Primary Risk</th><th>Similarity</th><th>Root Cause Summary</th></tr>
      </thead>
      <tbody>${evidenceRows}</tbody>
    </table>
  </div>` : ""}

  <!-- S Transcript -->
  <div style="margin-bottom:28pt" class="page-break">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">${(trace.retrieved_cases ?? []).length > 0 ? 7 + sectionBase : 6 + sectionBase}</span>
      Board Deliberation Transcript
    </div>
    <p style="font-size:8.5pt;color:#6b7280;margin-bottom:14pt">Verbatim claims from each domain-specialist agent. Claims are LLM-generated and do not affect fusion math.</p>
    ${transcriptRows}
  </div>

  <!-- S Methodology -->
  <div style="margin-bottom:28pt" class="page-break">
    <div style="font-family:Arial,sans-serif;font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#6d28d9;border-bottom:1.5pt solid #6d28d9;padding-bottom:4pt;margin-bottom:14pt">
      <span style="display:inline-block;width:18pt;height:18pt;background:#1e1b4b;color:white;border-radius:2pt;font-size:8pt;font-weight:700;text-align:center;line-height:18pt;margin-right:6pt;vertical-align:middle">${(trace.retrieved_cases ?? []).length > 0 ? 8 + sectionBase : 7 + sectionBase}</span>
      Methodology &amp; Reproducibility (SRS F-17)
    </div>
    <div style="background:#f9fafb;border:.5pt solid #d1d5db;border-radius:4pt;padding:12pt 14pt;font-size:8.5pt;line-height:1.8;margin-bottom:14pt">
      <strong style="font-family:Arial,sans-serif">Decision Fusion (F-10):</strong>
      <code style="display:block;font-family:'Courier New',monospace;background:#1e1b4b;color:#a78bfa;padding:8pt 12pt;border-radius:3pt;font-size:9pt;margin:8pt 0">Final_Score = \u03a3(W\u1d62 \u00b7 C\u1d62 \u00b7 S\u1d62) / \u03a3(W\u1d62 \u00b7 C\u1d62)</code>
      <strong style="font-family:Arial,sans-serif">Confidence Formula (F-06):</strong>
      <code style="display:block;font-family:'Courier New',monospace;background:#1e1b4b;color:#a78bfa;padding:8pt 12pt;border-radius:3pt;font-size:9pt;margin:8pt 0">C\u1d62 = w_sim \u00b7 M_sim + w_evidence \u00b7 M_evidence + w_reliability \u00b7 M_reliability</code>
      <strong style="font-family:Arial,sans-serif">Weight Calibration (F-07):</strong>
      <code style="display:block;font-family:'Courier New',monospace;background:#1e1b4b;color:#a78bfa;padding:8pt 12pt;border-radius:3pt;font-size:9pt;margin:8pt 0">W\u1d62 = softmax((R\u1d62 + b\u1d62) / T)</code>
      <strong style="font-family:Arial,sans-serif">Decision Classes:</strong>
      <code style="display:block;font-family:'Courier New',monospace;background:#1e1b4b;color:#a78bfa;padding:8pt 12pt;border-radius:3pt;font-size:9pt;margin:8pt 0">PROCEED   \u2192 Score \u2265 ${thresholds.tau_approve ?? 60} AND Confidence \u2265 ${thresholds.tau_confidence ?? 0.40}
HIGH-RISK \u2192 Score &lt; ${thresholds.tau_approve ?? 60} AND Confidence \u2265 ${thresholds.tau_confidence ?? 0.40}
REVIEW    \u2192 Confidence &lt; ${thresholds.tau_confidence ?? 0.40}  (abstain)</code>
    </div>
    <table><thead><tr><th style="width:180pt">Component</th><th>Version / Identifier</th></tr></thead><tbody>${versionRows}</tbody></table>
    <p style="font-size:7.5pt;color:#6b7280;margin-top:8pt">
      Replay: <code>GET /api/v1/replay/${trace.evaluation_id}</code> reconstructs this decision without re-invoking any LLM.
    </p>
  </div>

  <!-- Disclaimer -->
  <div style="padding:12pt 14pt;background:#f3f4f6;border-radius:4pt;font-size:7.5pt;color:#6b7280;line-height:1.6;margin-top:20pt">
    <strong>DISCLAIMER:</strong> This report was generated automatically by the AIRB system, an experimental AI-powered research prototype.
    The decision, scores, and assessments contained herein are produced by language models and deterministic mathematical fusion and do
    <strong>not</strong> constitute financial, legal, or investment advice. All outputs should be reviewed by qualified human experts
    before any investment or business decision is made.
  </div>

  <!-- Footer -->
  <div style="border-top:1pt solid #d1d5db;margin-top:32pt;padding-top:10pt;font-family:Arial,sans-serif;font-size:7pt;color:#9ca3af;line-height:1.6">
    AIRB \u2014 Evidence-Calibrated Multi-Agent Decision Fusion Framework &nbsp;|&nbsp;
    Evaluation ID: ${trace.evaluation_id} &nbsp;|&nbsp;
    Generated: ${formatDate()} &nbsp;|&nbsp; Confidential
  </div>

</div>
</body>
</html>`;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  trace: DecisionTrace;
}

export default function ReportGenerator({ trace }: Props) {
  function handleGenerate() {
    const html = buildReportHTML(trace);
    const win = window.open("", "_blank", "width=920,height=1100");
    if (!win) {
      alert("Pop-up blocked. Please allow pop-ups for this site and try again.");
      return;
    }
    win.document.open();
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 800);
  }

  return (
    <button
      id="export-report"
      className="btn btn-primary btn-sm"
      onClick={handleGenerate}
      title="Generate a formal PDF feasibility report"
      style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}
    >
      <FileDown size={14} />
      Export Report
    </button>
  );
}
