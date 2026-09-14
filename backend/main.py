"""
AIRB FastAPI Application Entry Point
Mounts routes, configures CORS and logging.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from api.routes import router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AIRB — Evidence-Calibrated Multi-Agent Decision Fusion Framework",
    description=(
        "Startup feasibility evaluator using calibrated multi-agent LLM decision fusion. "
        "Every final score is traceable to specific agent contributions, weights, "
        "confidence values, and cited historical evidence."
    ),
    version="1.0.0-sprint1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


# ── Startup Event ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event() -> None:
    """Ensure ChromaDB grounding index is populated on startup."""
    try:
        from rag.index import get_collection, build_index
        col = get_collection()
        if col.count() == 0:
            logging.info("ChromaDB collection is empty on startup. Building grounding corpus index...")
            build_index()
    except Exception as exc:
        logging.warning(f"Startup index build skipped/failed: {exc}")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health() -> dict:
    """System health check."""
    return {"status": "ok", "version": "1.0.0-sprint1"}


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=Config.api.host,
        port=Config.api.port,
        reload=True,
    )
