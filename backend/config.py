"""
AIRB Config Loader
Reads config.yaml and .env, exposes a typed Config object.
Per SRS NF-04: all thresholds and dataset sizes are centralised here.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env from backend root
_backend_root = Path(__file__).parent.resolve()
load_dotenv(_backend_root / ".env")


def _abs_path(rel_path: str) -> str:
    p = Path(rel_path)
    if p.is_absolute():
        return str(p)
    return str((_backend_root / p).resolve())


def _load_yaml() -> dict[str, Any]:
    config_path = _backend_root / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


_cfg = _load_yaml()


class _DatasetConfig:
    N: int = _cfg["dataset"]["N"]
    split_ratios: dict[str, float] = _cfg["dataset"]["split_ratios"]
    raw_data_path: str = _abs_path(_cfg["dataset"]["raw_data_path"])
    split_manifest_path: str = _abs_path(_cfg["dataset"]["split_manifest_path"])


class _RAGConfig:
    top_k: int = _cfg["rag"]["top_k"]
    index_type: str = _cfg["rag"]["index_type"]
    chroma_persist_dir: str = _abs_path(_cfg["rag"]["chroma_persist_dir"])
    embedding_model: str = _cfg["rag"]["embedding_model"]


class _ThresholdConfig:
    theta_conflict: float = _cfg["thresholds"]["theta_conflict"]
    tau_approve: float = _cfg["thresholds"]["tau_approve"]
    tau_confidence: float = _cfg["thresholds"]["tau_confidence"]


class _ConfidenceConfig:
    w_sim: float = _cfg["confidence"]["w_sim"]
    w_evidence: float = _cfg["confidence"]["w_evidence"]
    w_reliability: float = _cfg["confidence"]["w_reliability"]


class _SensitivityConfig:
    num_points: int = _cfg["sensitivity_sweep"]["num_points"]


class _LLMConfig:
    worker_model: str = _cfg["llm"]["worker_model"]
    router_model: str = _cfg["llm"]["router_model"]
    red_team_model: str = _cfg["llm"]["red_team_model"]
    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "")
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    supabase_key: str = os.environ.get("SUPABASE_KEY", "")


class _CalibrationConfig:
    temperature_range: list[float] = _cfg["calibration"]["temperature_range"]
    bias_range: list[float] = _cfg["calibration"]["bias_range"]
    random_seed: int = _cfg["calibration"]["random_seed"]
    output_path: str = _abs_path(_cfg["calibration"]["output_path"])


class _LabelingConfig:
    raw_input_path: str = _abs_path(_cfg["labeling"]["raw_input_path"])
    output_path: str = _abs_path(_cfg["labeling"]["output_path"])
    kappa_subset_size: int = _cfg["labeling"]["kappa_subset_size"]
    kappa_target: float = _cfg["labeling"]["kappa_target"]


class _VersioningConfig:
    prompt_template_version: str = _cfg["versioning"]["prompt_template_version"]
    dataset_version: str = _cfg["versioning"]["dataset_version"]
    rag_index_version: str = _cfg["versioning"]["rag_index_version"]
    weight_calibration_version: str = _cfg["versioning"]["weight_calibration_version"]


class _APIConfig:
    host: str = os.environ.get("HOST", _cfg["api"]["host"])
    port: int = int(os.environ.get("PORT", str(_cfg["api"]["port"])))
    cors_origins: list[str] = (
        [o.strip() for o in os.environ.get("CORS_ORIGINS").split(",") if o.strip()]
        if os.environ.get("CORS_ORIGINS")
        else _cfg["api"]["cors_origins"] + ["*"]
    )


class Config:
    """Single import point for all configuration. Usage: from config import Config"""
    dataset = _DatasetConfig()
    rag = _RAGConfig()
    thresholds = _ThresholdConfig()
    confidence = _ConfidenceConfig()
    sensitivity = _SensitivityConfig()
    llm = _LLMConfig()
    calibration = _CalibrationConfig()
    labeling = _LabelingConfig()
    versioning = _VersioningConfig()
    api = _APIConfig()
    sqlite_db_path: str = (
        _abs_path(os.environ.get("SQLITE_DB_PATH"))
        if os.environ.get("SQLITE_DB_PATH")
        else _abs_path("data/airb.db")
    )

