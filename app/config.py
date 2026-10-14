"""Central environment-driven configuration for Pushan V1.0."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("PUSHAN_ENV", "development")
    api_host: str = os.getenv("PUSHAN_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("PUSHAN_API_PORT", "8000"))
    api_url: str = os.getenv("PUSHAN_API_URL", "http://127.0.0.1:8000")
    database_path: str | Path = os.getenv("DATABASE_URL") or _path(
        "PUSHAN_DATABASE_PATH", PROJECT_ROOT / "data" / "pushan.db"
    )
    model_path: Path = _path("PUSHAN_MODEL_PATH", PROJECT_ROOT / "artifacts" / "irrigation_model.joblib")
    vector_store_path: Path = _path("PUSHAN_VECTOR_STORE_PATH", PROJECT_ROOT / "artifacts" / "vector_store")
    llm_model: str = os.getenv("PUSHAN_LLM_MODEL", "gemini-3.1-flash-lite")
    embedding_model: str = os.getenv("PUSHAN_EMBEDDING_MODEL", "local-hash-v1")
    max_auto_approved_water_litres: float = float(os.getenv("MAX_AUTO_APPROVED_WATER_LITRES", "5000"))
    automation_webhook_url: str = os.getenv("PUSHAN_AUTOMATION_WEBHOOK_URL", "")
    webhook_timeout_seconds: float = float(os.getenv("PUSHAN_WEBHOOK_TIMEOUT_SECONDS", "5"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()
