"""Configuration helpers shared by the local RAG stack."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "Data"

MASTER_FILENAME = "reframing_retirement_master_data_set.txt"
ACTIVITY_FILENAME = "reframing_retirement_activity_list.txt"

EMBED_DIMENSIONS = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}


def _path_from_env(var_name: str, default: Path) -> Path:
    value = os.getenv(var_name)
    if value:
        return Path(value).expanduser()
    return default


def _coerce_int(value: Optional[str], fallback: int) -> int:
    try:
        return int(value) if value is not None else fallback
    except ValueError:
        return fallback


def _read_openai_key() -> str:
    key = os.getenv("OPENAI_API_key") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_key (preferred) or OPENAI_API_KEY in your environment.")
    return key


@dataclass
class RagConfig:
    """Holds runtime settings for ingestion and retrieval."""

    openai_api_key: str
    chat_model: str
    embedding_model: str
    embedding_dimensions: int
    master_collection: str
    activities_collection: str
    qdrant_url: str
    qdrant_api_key: Optional[str]
    master_data_path: Path
    activity_data_path: Path
    master_top_k: int = 5
    activity_top_k: int = 4


def load_rag_config() -> RagConfig:
    """Load configuration from .env with safe defaults."""

    openai_api_key = _read_openai_key()
    chat_model = os.getenv("OPENAI_MODEL", "gpt-4o")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    embedding_dimensions = EMBED_DIMENSIONS.get(embedding_model, 3072)

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    master_collection = os.getenv("RR_MASTER_COLLECTION", "rr_master")
    activities_collection = os.getenv("RR_ACTIVITIES_COLLECTION", "rr_activities")

    master_data_path = _path_from_env("RR_MASTER_DATA_PATH", DATA_DIR / MASTER_FILENAME)
    activity_data_path = _path_from_env("RR_ACTIVITY_DATA_PATH", DATA_DIR / ACTIVITY_FILENAME)

    master_top_k = _coerce_int(os.getenv("RR_MASTER_TOP_K"), 5)
    activity_top_k = _coerce_int(os.getenv("RR_ACTIVITY_TOP_K"), 4)

    return RagConfig(
        openai_api_key=openai_api_key,
        chat_model=chat_model,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        master_collection=master_collection,
        activities_collection=activities_collection,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        master_data_path=master_data_path,
        activity_data_path=activity_data_path,
        master_top_k=master_top_k,
        activity_top_k=activity_top_k,
    )
