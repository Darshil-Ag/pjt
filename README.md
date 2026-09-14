# AIRB — Evidence-Calibrated Multi-Agent Decision Fusion Framework

**Research Capstone · Sprint 1 Build**

> A startup-feasibility evaluator where five domain-specialist LLM agents debate historical precedent, and a deterministic Python layer — not an LLM judge — fuses their opinions into an auditable PROCEED / HIGH-RISK / REVIEW verdict.

---

## Repo Structure

```
airb/
├── backend/              # FastAPI + LangGraph pipeline
│   ├── config.yaml       # ← ALL thresholds and dataset params live here (NF-04)
│   ├── .env.example      # ← Copy to .env, fill in API keys (NF-03)
│   ├── main.py           # FastAPI entry point
│   ├── schemas/          # Frozen Pydantic models + TypedDict state (SRS §6.1, §6.2)
│   ├── graph/            # LangGraph state machine (all 9 nodes wired)
│   ├── rag/              # ChromaDB index build + retrieval + dataset ingestion
│   ├── dataset/          # LLM-assisted labeling pipeline + Cohen's kappa check
│   ├── api/              # FastAPI routes
│   ├── tests/            # Pytest unit tests
│   └── data/             # Dataset files (not committed — in .gitignore)
└── frontend/             # Next.js dashboard
    ├── app/              # App Router pages
    │   ├── page.tsx      # Home (pitch submission)
    │   └── decision/[id] # Decision report with radar, agents, transcript
    ├── components/       # PitchForm, Dashboard, HITLModal, Navbar
    └── lib/api.ts        # Typed API client
```

---

## Sprint 1 Status

| Deliverable | Status |
|---|---|
| Digital twin schema (Pydantic) | ✅ Done |
| ReviewBoardState TypedDict (SRS §6.2) | ✅ Done |
| LangGraph topology (all 9 nodes wired) | ✅ Done |
| Conflict Index + Fusion math (deterministic Python) | ✅ Done |
| FastAPI skeleton (4 endpoints) | ✅ Done |
| Dataset ingestion + split enforcement (F-03) | ✅ Done |
| F-03 test-leakage hard gate | ✅ Done |
| ChromaDB RAG index builder | ✅ Done |
| LLM-assisted labeling pipeline | ✅ Done |
| Inter-rater kappa check (SRS §6.3) | ✅ Done |
| Evaluation logger (UUID + version_info) | ✅ Done |
| config.yaml (single source of truth) | ✅ Done |
| Next.js frontend skeleton | ✅ Done |
| Unit tests (TC-05, TC-06, TC-08, TC-09, TC-11, TC-15) | ✅ Done |
| Seed dataset (20 cases) | ✅ Done |
| Context Router (F-01, Gemini) | 🔲 Sprint 2 |
| Retrieval node (F-04) | 🔲 Sprint 2 |
| 5 domain agents via Groq (F-05) | 🔲 Sprint 2 |
| Confidence scoring (F-06) | 🔲 Sprint 2 |
| Weight calibration (F-07) | 🔲 Sprint 2 |
| HITL pause/resume (F-09) | 🔲 Sprint 3 |
| Red Team (F-13) | 🔲 Sprint 3 |
| Sensitivity sweep (F-14) | 🔲 Sprint 3 |
| SQLite persistence + replay (F-17) | 🔲 Sprint 3 |
| Dashboard full integration | 🔲 Sprint 3 |
| Ablation harness + bootstrap CIs (F-12) | 🔲 Sprint 4 |

---

## Quick Start

### 1. Backend

```powershell
# Create and activate virtual environment
cd airb/backend
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — fill in GROQ_API_KEY and GOOGLE_API_KEY

# Run dev server
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Dataset Pipeline (Sprint 1)

```powershell
# Run LLM-assisted labeling on seed dataset
python -m dataset.label_pipeline --input data/raw_cases.csv --output data/labeled_draft.jsonl

# After human verification of labeled_draft.jsonl:
# Run ingestion + split assignment
python -m rag.ingest --input data/labeled_draft.jsonl --output data/historical_cases.jsonl

# Build ChromaDB index
python -m rag.index --rebuild --input data/historical_cases.jsonl

# Run F-03 split integrity check
python -m rag.ingest --check-split
```

### 3. Inter-Rater Kappa Check

```powershell
# Run on synthetic test fixture to verify tool works
python -m dataset.kappa_check --test

# Run on two real rater files
python -m dataset.kappa_check --rater1 data/rater1.csv --rater2 data/rater2.csv
```

### 4. Unit Tests

```powershell
cd airb/backend
pytest tests/ -v
```

### 5. Frontend

```powershell
cd airb/frontend
npm run dev
```

Open: http://localhost:3000

---

## Architecture Principle

> **All subjective judgment stays inside the LLM agent layer. All weighting, scoring math, conflict detection, and routing logic is deterministic Python — no LLM calls inside the fusion, confidence (Cᵢ), weight (Wᵢ), or conflict-index (CI) computations.**

This separation is the entire auditability argument the research contribution rests on.

---

## Key Configuration (config.yaml)

| Parameter | Default | Description |
|---|---|---|
| `thresholds.theta_conflict` | 150.0 | CI threshold for HITL trigger (F-08) |
| `thresholds.tau_approve` | 60.0 | Min score for PROCEED verdict (F-10) |
| `thresholds.tau_confidence` | 0.40 | Min C_final for non-REVIEW verdict (F-10) |
| `rag.top_k` | 5 | Retrieved cases per query (F-04) |
| `dataset.N` | 300 | Target dataset size (configurable) |
| `sensitivity_sweep.num_points` | 5 | Sweep points for HITL variable (F-14) |

---

## Dataset Requirements

See BRD §6 for sizing guidance. **Recommended: 250–350 cases** split as:
- **60% grounding** → RAG corpus
- **15% calibration** → weight calibration (Sprint 2)
- **25% test** → held-out ablation study (Sprint 4)

**Hard rule (F-03):** Test-set cases must never enter the vector index. Enforced automatically.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/evaluate` | Submit pitch, get evaluation_id |
| `POST` | `/api/v1/hitl-respond` | Submit HITL answer, resume graph |
| `GET` | `/api/v1/decision/{id}` | Full decision trace |
| `GET` | `/api/v1/replay/{id}` | Exact replay, zero LLM calls (F-17) |
| `GET` | `/health` | System health check |

---

## Stack (all free-tier)

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (Python) |
| Worker agents | Llama 3.3 70B via Groq free tier |
| Router / embeddings | Gemini 2.5 Flash via Google AI Studio |
| Vector store | ChromaDB (local, disk-backed) |
| Backend | FastAPI + Uvicorn |
| Persistence | SQLite (LangGraph checkpoints) |
| Frontend | Next.js (App Router) |
| Hosting | Vercel (frontend) + Render/Railway free tier (backend) |
