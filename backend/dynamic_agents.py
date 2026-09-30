"""
Dynamic Agent Registry — Future Scope B
Detects whether a startup pitch needs extra specialized agents beyond the base 5.

Keywords → specialist agents:
  FDA / pharma / drug / clinical     → "Regulatory (FDA)" specialist
  ESG / sustainability / carbon      → "ESG & Impact" specialist
  blockchain / crypto / web3 / DeFi  → "Blockchain & Web3" specialist
  hardware / IoT / manufacturing     → "Hardware & Supply Chain" specialist
  AI safety / alignment / bias       → "AI Ethics & Safety" specialist

Each extra agent follows the same Groq prompt contract as the base agents.
"""

from __future__ import annotations

import re
from typing import Optional

# ── Specialist Definitions ────────────────────────────────────────────────────

EXTRA_SPECIALISTS: list[dict] = [
    {
        "domain": "Regulatory (FDA)",
        "keywords": [
            r"\bfda\b", r"\bpharm", r"\bclinical trial", r"\bdrug\b", r"\bmedical device",
            r"\bprescription\b", r"\bfda appro", r"\bbiologic\b", r"\bide\b", r"\b510k\b",
        ],
        "prompt_persona": (
            "You are an FDA Regulatory Affairs specialist. Evaluate ONLY the regulatory risk "
            "of bringing this product to market: clinical trial requirements, FDA approval pathway "
            "(510(k), PMA, BLA, NDA), labeling, adverse event reporting, and post-market surveillance."
        ),
    },
    {
        "domain": "ESG & Impact",
        "keywords": [
            r"\besg\b", r"\bsustainab", r"\bcarbon\b", r"\bnet.?zero\b", r"\bgreen\b",
            r"\bclimate\b", r"\bimpact invest", r"\bcircular economy\b", r"\brenewable\b",
            r"\bsocial impact\b",
        ],
        "prompt_persona": (
            "You are an ESG (Environmental, Social, Governance) investment specialist. Evaluate "
            "the startup's sustainability claims, carbon impact, UN SDG alignment, ESG reporting "
            "readiness, greenwashing risk, and attractiveness to impact-focused LPs."
        ),
    },
    {
        "domain": "Blockchain & Web3",
        "keywords": [
            r"\bblockchain\b", r"\bcrypto\b", r"\bweb3\b", r"\bdefi\b", r"\bnft\b",
            r"\bsmart contract\b", r"\btoken\b", r"\bdao\b", r"\bsolana\b", r"\bethereum\b",
        ],
        "prompt_persona": (
            "You are a Blockchain & Web3 investment specialist. Evaluate the startup's token "
            "economics, consensus mechanism choices, regulatory exposure (SEC, MiCA), on-chain "
            "security, decentralization credibility, and ecosystem moat."
        ),
    },
    {
        "domain": "Hardware & Supply Chain",
        "keywords": [
            r"\bhardware\b", r"\biot\b", r"\bmanufactur", r"\bsemiconductor\b", r"\brobotics\b",
            r"\bphysical product\b", r"\bsupply chain\b", r"\bfabrication\b", r"\bbom\b",
            r"\bpcb\b", r"\bembedded\b",
        ],
        "prompt_persona": (
            "You are a Hardware & Supply Chain specialist. Evaluate manufacturing scalability, "
            "BOM costs, contract manufacturing options (ODM/OEM), component sourcing risk, "
            "tariff exposure, time-to-first-unit, and capital intensity of tooling."
        ),
    },
    {
        "domain": "AI Ethics & Safety",
        "keywords": [
            r"\bai safety\b", r"\balignment\b", r"\bbias\b", r"\bexplainab", r"\bfairness\b",
            r"\bgdpr\b", r"\bai act\b", r"\bresponsible ai\b", r"\bprivacy\b", r"\bsurveillance\b",
        ],
        "prompt_persona": (
            "You are an AI Ethics & Safety specialist. Evaluate algorithmic bias risks, GDPR/EU AI Act "
            "compliance, explainability requirements, data sovereignty, model security, and the "
            "reputational risk of harmful outputs at scale."
        ),
    },
]


def detect_extra_agents(pitch: str, digital_twin: Optional[dict] = None) -> list[dict]:
    """
    Scan the pitch (and optionally the digital_twin) for specialist trigger keywords.
    Returns a list of specialist dicts whose keywords matched.

    Each returned dict has: domain, prompt_persona
    """
    text = pitch.lower()
    if digital_twin:
        text += " " + " ".join(str(v) for v in digital_twin.values() if v).lower()

    triggered = []
    for spec in EXTRA_SPECIALISTS:
        if any(re.search(kw, text) for kw in spec["keywords"]):
            triggered.append(spec)

    return triggered


def get_all_active_domains(extra_agents: list[dict]) -> list[str]:
    """Return the full ordered list of domains (base 5 + any extras)."""
    base = ["Finance", "Legal", "Market", "Operations", "Technology"]
    extra_names = [a["domain"] for a in extra_agents]
    return base + extra_names
