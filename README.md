# AIRB — AI Investment Review Board

> **Evidence-Calibrated Multi-Agent Decision Fusion Framework for Startup Pitch Evaluation**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-local-orange)](https://www.trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is AIRB?

AIRB simulates a **venture capital investment board** using a pipeline of AI agents, each a domain-specialist, evaluating a startup pitch from a different lens — Finance, Legal, Market, Operations, and Technology. Their outputs are combined not by averaging or majority vote, but through a **deterministic mathematical fusion** layer that weights each agent by domain relevance and grounds their confidence in retrieved historical precedent.

The result: a reproducible, auditable investment verdict (`PROCEED` / `HIGH-RISK` / `REVIEW`) backed by citations, conflict detection, adversarial review, and a sensitivity analysis showing how stable that verdict really is.

---

## The Problem It Solves

Most AI pitch evaluators prompt a single LLM to "act like a VC." This approach suffers from:

| Problem | Description |
|---|---|
| **Sycophancy** | LLMs tend to agree with confidently-written pitches regardless of merit |
| **Conformity Lock-in** | A single model averages out nuanced risk signals into generic responses |
| **Hallucinated Confidence** | LLMs cannot reliably self-assess how certain they are |
| **No Evidence Grounding** | No mechanism to check claims against historical startup outcomes |
| **Irreproducibility** | The same prompt yields different verdicts on repeated runs |

AIRB is designed to fix all five.

---

## System Architecture

```
Startup Pitch (free text)
        │
        ▼
┌───────────────────┐
│  Context Router   │  Gemini 2.0 Flash → extracts DigitalTwin JSON
│  (F-01)           │  Fallback: Groq llama-3.3-70b if Gemini 503s
└────────┬──────────┘
         │ DigitalTwin
         ▼
┌───────────────────┐
│  RAG Retrieval    │  ChromaDB + all-MiniLM-L6-v2 embeddings
│  (F-04)           │  Top-k similar historical startup cases
└────────┬──────────┘
         │ retrieved_cases
         ▼
┌───────────────────────────────────────────────────────┐
│  Market Intelligence (Scope A)                        │
│  DuckDuckGo / SerpAPI → live competitor + funding     │
│  signals injected into all agent prompts              │
│  → also upserted to ChromaDB (self-growing corpus)   │
└────────┬──────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────┐
│  Dynamic Agent Detection (Scope B)                    │
│  Keyword classifier → spawn extra specialists:        │
│  FDA Regulatory / ESG / Blockchain / Hardware / AI Ethics │
└────────┬──────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Parallel Domain Agents  (F-05)  — all run concurrently via asyncio │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Finance  │ │  Legal   │ │  Market  │ │   Ops    │ │   Tech   │ │ │
│  │ Groq LLM │ │ Groq LLM │ │ Groq LLM │ │ Groq LLM │ │ Groq LLM │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       │             │             │             │             │       │
│   score, claim, cited_case_ids (per agent)                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
         ┌───────────────────────┼────────────────────┐
         │ Ci computation (F-06) │                    │ Wi computation (F-07)
         │ (zero LLM calls)      │                    │ (zero LLM calls)
         │                       │                    │
         │  Ci = w_sim·Msim      │   Wi = softmax((Ri + bi) / T)
         │     + w_ev·Mevidence  │   Ri from Gemini (pre-agent, independent of Si)
         │     + w_rel·Mreliab   │   bi, T from calibrated_weights.json
         ▼                       ▼
┌───────────────────┐
│  Conflict Index   │  CI = Var(Si) weighted by Wi
│  (F-08)           │  CI > θ_conflict → HITL escalation
└────────┬──────────┘
         │
    ┌────┴────────────────────────┐
    │                             │
CI ≤ θ               CI > θ (conflict detected)
    │                             │
    │              ┌──────────────▼──────────────┐
    │              │  Human-in-the-Loop (F-09)   │
    │              │  Pause pipeline, ask user    │
    │              │  for clarification           │
    │              │  Persisted in SQLite         │
    │              └──────────────┬──────────────┘
    │                             │ user answer
    └──────────────┬──────────────┘
                   ▼
┌───────────────────────────────────────────┐
│  Mathematical Decision Fusion  (F-10)     │
│                                           │
│  Final_Score = Σ(Wi · Ci · Si)            │
│               ─────────────────           │
│                  Σ(Wi · Ci)               │
│                                           │
│  PROCEED   → Score ≥ τ_approve AND        │
│              Confidence ≥ τ_confidence    │
│  HIGH-RISK → Score < τ_approve AND        │
│              Confidence ≥ τ_confidence    │
│  REVIEW    → Confidence < τ_confidence   │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────┐
│  Sensitivity      │  Perturb each Wi by ±10%, ±20%
│  Sweep  (F-14)    │  Re-run fusion math deterministically
│                   │  Detect decision flips
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Red Team Agent   │  Independent adversarial LLM
│  (F-13)           │  Reads full board transcript
│                   │  Can override PROCEED → REVIEW
│                   │  (never the reverse)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Evaluation Logger │  Persisted to SQLite (F-17)
│  (F-17)           │  Fully replayable via GET /replay/{id}
└───────────────────┘
```

---

## Novelty Contributions

### 1. Separation of Reasoning and Math (Hybrid Architecture)

AIRB enforces a hard architectural boundary: **LLMs are responsible for language, Python math is responsible for all numbers.**

An agent might say "The market is saturated" — but the *weight* and *confidence* of that claim is computed deterministically from RAG similarity scores, not from anything the LLM says about itself. No LLM can inflate its own score by expressing certainty.

This makes AIRB **provably non-sycophantic**: a pitch can be written to perfectly manipulate an LLM, but the math layer is immune to persuasive writing.

### 2. Evidence-Calibrated Confidence (not self-reported)

Standard LLM evaluators ask the model to rate its own confidence. AIRB never does this.

Confidence (Cᵢ) is computed from three RAG metadata signals:
```
Ci = w_sim · M_similarity + w_ev · M_evidence_alignment + w_rel · M_source_reliability
```
- **M_sim**: cosine similarity of the retrieved cases to the current pitch
- **M_evidence**: fraction of retrieved cases that align with the agent's domain
- **M_reliability**: empirical quality of the grounding corpus for this domain

If no historical precedent exists (novel pitch in an unexplored space), Cᵢ drops → system automatically abstains with `REVIEW` rather than confidently hallucinating.

### 3. Conflict Index as a HITL Trigger

Most multi-agent systems discard inter-agent disagreement or average it away. AIRB treats it as **signal, not noise**.

The Conflict Index (CI) is the weighted variance of agent scores:
```
CI = Σ Wi · (Si − Final_Score)²
```

High CI means the agents fundamentally disagree — which is a **risk indicator**. Instead of forcing a decision, AIRB pauses the pipeline and asks the human to clarify the specific variable that caused the conflict. This is architecturally principled: human intervention is triggered *precisely* when the system is least confident, not randomly.

### 4. Adversarial Red Team as Safety Brake

After the board reaches consensus, a separate Red Team agent reads the full deliberation transcript and actively tries to find fatal flaws the specialists missed. Crucially:

- The Red Team can **only escalate** (PROCEED → REVIEW)
- It **cannot approve** (REVIEW → PROCEED)

This asymmetry is intentional — it models a conservative risk function appropriate for investment decisions.

### 5. Decision Stability Analysis (Sensitivity Sweep)

For each domain, AIRB perturbs its weight by −20%, −10%, 0%, +10%, +20%, renormalizes, and re-runs fusion math. This produces a **stability certificate** for the verdict:

- If the decision class (PROCEED/HIGH-RISK/REVIEW) holds across all perturbations → **stable**
- If a weight shift causes a flip → flagged as a **fragile decision**, reported to the user

This gives investors a quantitative answer to "how confident should I be in this verdict?"

### 6. Self-Enriching RAG Corpus (Live Market Integration)

Every evaluation fetches live competitor and market signals from the web. These signals are automatically upserted back into ChromaDB with a content-hash-based deduplication ID. The grounding corpus grows with every pitch evaluated — the system gets progressively better on industries it has evaluated before, without any manual data collection.

### 7. Dynamic Agent Generation

A keyword classifier scans the pitch and spawns extra specialist agents beyond the base 5 when domain-specific risks are detected:

| Trigger Keywords | Extra Agent |
|---|---|
| `FDA`, `clinical trial`, `medical device` | Regulatory (FDA) Specialist |
| `ESG`, `sustainability`, `carbon`, `net-zero` | ESG & Impact Specialist |
| `blockchain`, `crypto`, `DeFi`, `web3` | Blockchain & Web3 Specialist |
| `hardware`, `IoT`, `manufacturing`, `PCB` | Hardware & Supply Chain Specialist |
| `AI safety`, `alignment`, `GDPR`, `bias` | AI Ethics & Safety Specialist |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI (Python 3.11) |
| **Agent Orchestration** | LangGraph-style async pipeline |
| **LLMs** | Groq (`llama-3.3-70b`, `openai/gpt-oss-120b`), Google Gemini 2.0 Flash |
| **Vector Database** | ChromaDB (local, disk-backed) |
| **Embeddings** | `all-MiniLM-L6-v2` via ChromaDB default EF |
| **Persistence** | SQLite (HITL checkpoints, evaluation traces) |
| **Live Market Data** | DuckDuckGo Instant Answer API / SerpAPI |
| **Frontend** | Next.js 14, React, TypeScript |
| **Styling** | Vanilla CSS (custom design system) |
| **PDF Reports** | Browser-native `window.print()` with HTML/CSS formatting |

---

## Dataset

- **409 historical startup cases** across 6 sectors (FinTech, HealthTech, EdTech, Retail, SaaS, Hardware)
- Split: **327 grounding** (indexed in ChromaDB) / **82 test** (strictly excluded from index per F-03)
- Each case: `case_id`, `industry`, `outcome` (success/failed/acquired), `primary_risk_category`, `root_cause_summary`, `raw_text`

---

## SRS Requirements Coverage

| ID | Requirement | Status |
|---|---|---|
| F-01 | Context Router extracts DigitalTwin from pitch | ✅ |
| F-03 | Test cases never appear in vector index | ✅ |
| F-04 | RAG retrieval via ChromaDB cosine similarity | ✅ |
| F-05 | 5+ domain agents run concurrently | ✅ |
| F-06 | Confidence computed without LLM calls | ✅ |
| F-07 | Weights = softmax(Ri/T), calibrated via grid search | ✅ |
| F-08 | Conflict Index computed per evaluation | ✅ |
| F-09 | HITL state persists across server restarts (SQLite) | ✅ |
| F-10 | Mathematical decision fusion formula | ✅ |
| F-13 | Red Team adversarial review | ✅ |
| F-14 | Sensitivity sweep over weight perturbations | ✅ |
| F-15 | Final score uncertainty band | ✅ |
| F-16 | HITL effectiveness measurement (ΔCI) | ✅ |
| F-17 | Full evaluation trace persisted and replayable | ✅ |

---

## Project Structure

```
CAPSTONE-3CREDITS/
├── backend/
│   ├── api/
│   │   └── routes.py              # FastAPI endpoints
│   ├── graph/
│   │   └── nodes/
│   │       ├── context_router.py  # F-01: DigitalTwin extraction
│   │       ├── retrieval.py       # F-04: RAG retrieval
│   │       ├── parallel_dispatch.py  # F-05/06/07: agents + math
│   │       ├── conflict_index.py  # F-08: CI + HITL routing
│   │       ├── hitl.py            # F-09: Human-in-the-Loop
│   │       ├── fusion.py          # F-10: Decision fusion
│   │       ├── red_team.py        # F-13: Adversarial review
│   │       ├── sensitivity_sweep.py  # F-14: Stability analysis
│   │       └── evaluation_logger.py  # F-17: Trace persistence
│   ├── rag/
│   │   ├── index.py               # ChromaDB build + retrieval
│   │   └── ingest.py              # Dataset loading + F-03 gate
│   ├── schemas/
│   │   ├── digital_twin.py        # DigitalTwin Pydantic model
│   │   └── state.py               # ReviewBoardState TypedDict
│   ├── market_intel.py            # Scope A: Live market data + ChromaDB upsert
│   ├── dynamic_agents.py          # Scope B: Keyword → extra agent classifier
│   ├── calibrate_weights.py       # F-07: Grid search calibration
│   ├── hitl_store.py              # SQLite persistence layer
│   ├── progress.py                # In-memory status tracker
│   ├── config.py / config.yaml    # All parameters (never hardcoded)
│   ├── main.py                    # FastAPI app entry point
│   └── data/
│       ├── historical_cases.jsonl # 409 startup cases
│       ├── calibrated_weights.json  # Calibrated bi, T values
│       └── store.sqlite           # HITL + evaluation persistence
└── frontend/
    ├── app/
    │   ├── page.tsx               # Landing + pitch submission
    │   └── decision/[id]/page.tsx # Results dashboard
    ├── components/
    │   ├── Dashboard.tsx          # All result visualization components
    │   ├── SensitivityChart.tsx   # Interactive SVG sweep chart
    │   ├── ReportGenerator.tsx    # Investment Memo PDF builder
    │   ├── ProgressTracker.tsx    # Real-time pipeline status
    │   ├── HITLModal.tsx          # Human-in-the-Loop UI
    │   └── Navbar.tsx
    └── lib/
        └── api.ts                 # Type-safe API client
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/v1/evaluate` | POST | Submit a startup pitch |
| `GET /api/v1/status/{id}` | GET | Poll evaluation progress |
| `POST /api/v1/hitl-respond` | POST | Submit HITL clarification answer |
| `GET /api/v1/decision/{id}` | GET | Retrieve final evaluation result |
| `GET /api/v1/replay/{id}` | GET | Reconstruct evaluation without LLM calls |
| `GET /health` | GET | Backend health + version info |

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key (`GROQ_API_KEY`)
- Google Gemini API key (`GOOGLE_API_KEY`)
- *(Optional)* SerpAPI key (`SERPAPI_KEY`) for richer market data

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# Build RAG index
.venv/Scripts/python.exe -m rag.index --rebuild

# Run calibration
.venv/Scripts/python.exe calibrate_weights.py

# Start server
.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Test Suite

```bash
cd backend
.venv/Scripts/pytest tests/test_sprint2.py -v
# → 36 passed
```

Key tests cover: weight calibration math, confidence bounds, agent concurrency, graceful failure degradation, HITL SQLite roundtrip, Red Team override logic, RAG auto-indexing, context router schema compliance.

---

## Environment Variables

```env
# backend/.env
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
SERPAPI_KEY=...          # optional — enables Google Search for market intel
```

---

## Future Work

- **Human baseline study**: Have real VCs score a test set; compare AIRB accuracy vs single-LLM vs human panel
- **Fine-tuned Red Team**: Replace cloud LLM with a locally fine-tuned Llama-3-8B trained on VC post-mortems
- **Live API integrations**: Crunchbase / PitchBook for structured funding and valuation data
- **Automated Investment Memo**: Expand the PDF to full 10-page IM format with generated charts

---

## Academic Context

Built as a 3-credit Capstone project. The primary academic contribution is the **architecture pattern**: specifically the separation of LLM reasoning from deterministic confidence/weight computation, and the use of inter-agent conflict (rather than individual agent uncertainty) as the trigger for human escalation.

If extending for publication, the recommended target venue is **ACM ICAIF** (International Conference on AI in Finance) or an **EMNLP / NeurIPS workshop** on LLM agents and decision making.

---

## Authors

Dhruv — [GitHub](https://github.com/Darshil-Ag/pjt)
