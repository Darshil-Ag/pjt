"""
Market Intelligence Module — Real-Time Data Enrichment (Future Scope A)

Fetches live market signals for a startup's industry/domain using free APIs:
- DuckDuckGo Instant Answer API (no key required)
- Optional: SerpAPI (if SERPAPI_KEY is set in env)

Signals collected:
  - Recent funding rounds in the same sector (from news headlines)
  - Competitor landscape (top companies in the space)
  - Market size / growth indicators

These signals are injected into agent prompts to replace static dataset context
when live data is available.

Architecture:
  - Called from parallel_dispatch_node BEFORE the agent calls
  - Results stored in state["market_intel"] (new field)
  - If fetch fails or API unavailable → gracefully returns empty dict (no crash)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
_DDG_BASE = "https://api.duckduckgo.com/"


async def _ddg_search(query: str, max_results: int = 5) -> list[str]:
    """
    Free DuckDuckGo Instant Answer API — returns related topics as text snippets.
    No API key required.
    """
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_DDG_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        snippets: list[str] = []
        # AbstractText — concise overview
        if data.get("AbstractText"):
            snippets.append(data["AbstractText"][:300])
        # RelatedTopics — bullet items about related entities
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                snippets.append(topic["Text"][:200])
        return snippets
    except Exception as exc:
        logger.debug(f"DDG search failed for '{query}': {exc}")
        return []


async def _serpapi_search(query: str, max_results: int = 5) -> list[str]:
    """
    SerpAPI Google search — richer results but requires SERPAPI_KEY env var.
    Falls back silently if key is absent.
    """
    if not SERPAPI_KEY:
        return []
    try:
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": max_results,
            "output": "json",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()
        snippets = []
        for result in data.get("organic_results", [])[:max_results]:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if snippet:
                snippets.append(f"{title}: {snippet[:200]}")
        return snippets
    except Exception as exc:
        logger.debug(f"SerpAPI search failed for '{query}': {exc}")
        return []


async def fetch_market_intel(
    industry: str,
    business_model: str,
    target_market: str,
    eval_id: str = "",
) -> dict:
    """
    Entry point: fetch real-time market intelligence for a startup.

    Returns a dict with:
        {
          "funding_signals":   [str],  # recent funding news
          "competitor_signals":[str],  # major competitors
          "market_signals":    [str],  # market size / trends
          "source":            str,    # "serpapi" | "duckduckgo" | "none"
        }

    Gracefully returns empty signals on any failure.
    """
    logger.info(f"[{eval_id}] Fetching real-time market intelligence for '{industry}'...")

    funding_q  = f"{industry} startup funding 2024 2025 venture capital"
    competitor_q = f"top companies {industry} {business_model} competitors"
    market_q = f"{industry} {target_market} market size growth 2024 2025"

    # Run 3 queries concurrently — prefer SerpAPI, fall back to DDG
    if SERPAPI_KEY:
        funding_f, competitor_f, market_f = await asyncio.gather(
            _serpapi_search(funding_q),
            _serpapi_search(competitor_q),
            _serpapi_search(market_q),
        )
        source = "serpapi"
    else:
        funding_f, competitor_f, market_f = await asyncio.gather(
            _ddg_search(funding_q),
            _ddg_search(competitor_q),
            _ddg_search(market_q),
        )
        source = "duckduckgo"

    result = {
        "funding_signals":    funding_f[:5],
        "competitor_signals": competitor_f[:5],
        "market_signals":     market_f[:5],
        "source":             source if (funding_f or competitor_f or market_f) else "none",
    }

    total = len(result["funding_signals"]) + len(result["competitor_signals"]) + len(result["market_signals"])
    logger.info(f"[{eval_id}] Market intel fetched: {total} signals via {result['source']}.")
    return result


def format_market_intel_for_prompt(intel: dict) -> str:
    """
    Format the market intel dict into a clean text block for injection into agent prompts.
    """
    if not intel or intel.get("source") == "none":
        return ""

    lines = ["LIVE MARKET INTELLIGENCE (real-time data):"]
    if intel.get("funding_signals"):
        lines.append("\nRecent Funding Activity:")
        for s in intel["funding_signals"]:
            lines.append(f"  • {s}")
    if intel.get("competitor_signals"):
        lines.append("\nCompetitive Landscape:")
        for s in intel["competitor_signals"]:
            lines.append(f"  • {s}")
    if intel.get("market_signals"):
        lines.append("\nMarket Signals:")
        for s in intel["market_signals"]:
            lines.append(f"  • {s}")
    lines.append(f"\n(Source: {intel['source'].upper()})")
    return "\n".join(lines)


async def upsert_live_companies(
    intel: dict,
    industry: str,
    eval_id: str = "",
) -> int:
    """
    Upsert competitor/market signals discovered during an evaluation into ChromaDB.

    Each signal snippet becomes a lightweight document in the grounding corpus
    with split="live_market" so it's always included in retrieval but never
    counted as a test case (F-03 safe).

    Returns the number of new documents added.
    """
    if not intel or intel.get("source") == "none":
        return 0

    from rag.index import get_collection
    import hashlib

    collection = get_collection()
    existing_ids: set[str] = set(collection.get(include=[])["ids"])

    docs_to_add: list[str] = []
    ids_to_add: list[str] = []
    metas_to_add: list[dict] = []

    all_signals = [
        ("competitor", s) for s in intel.get("competitor_signals", [])
    ] + [
        ("funding",    s) for s in intel.get("funding_signals", [])
    ] + [
        ("market",     s) for s in intel.get("market_signals", [])
    ]

    for signal_type, text in all_signals:
        if not text or len(text) < 20:
            continue
        # Stable deterministic ID based on content hash so duplicates are skipped
        doc_id = "live_" + hashlib.sha1(text.encode()).hexdigest()[:16]
        if doc_id in existing_ids:
            continue

        docs_to_add.append(text)
        ids_to_add.append(doc_id)
        metas_to_add.append({
            "industry": industry,
            "outcome": "unknown",
            "primary_risk_category": signal_type,
            "root_cause_summary": text[:200],
            "split": "live_market",        # never treated as test set (F-03 safe)
            "source": intel.get("source", "unknown"),
            "eval_id": eval_id,
        })

    if not docs_to_add:
        logger.info(f"[{eval_id}] No new live market documents to upsert (all duplicates).")
        return 0

    # Run blocking ChromaDB I/O in a thread so we don't block the event loop
    def _do_upsert():
        collection.add(
            ids=ids_to_add,
            documents=docs_to_add,
            metadatas=metas_to_add,
        )

    await asyncio.to_thread(_do_upsert)
    logger.info(
        f"[{eval_id}] Upserted {len(docs_to_add)} live market documents into ChromaDB "
        f"(industry='{industry}', source={intel.get('source')}). "
        f"Total corpus size: {collection.count()}."
    )
    return len(docs_to_add)
