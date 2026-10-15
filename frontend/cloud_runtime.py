"""Bootstrap Pushan's local API inside a Streamlit Community Cloud process."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from threading import Lock, Thread
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen


_START_LOCK = Lock()
_STARTED = False
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configure_cloud_environment() -> tuple[Path, int]:
    """Configure writable, ephemeral paths before importing backend modules."""
    runtime_root = Path(
        os.getenv(
            "PUSHAN_CLOUD_RUNTIME_PATH",
            str(Path(tempfile.gettempdir()) / "pushan-streamlit-cloud"),
        )
    )
    runtime_root.mkdir(parents=True, exist_ok=True)
    port = int(os.getenv("PUSHAN_API_PORT", "8000"))

    os.environ.setdefault("PUSHAN_ENV", "streamlit-cloud")
    os.environ.setdefault("PUSHAN_API_HOST", "127.0.0.1")
    os.environ.setdefault("PUSHAN_API_PORT", str(port))
    os.environ.setdefault("PUSHAN_API_URL", f"http://127.0.0.1:{port}")
    os.environ.setdefault("PUSHAN_DATABASE_PATH", str(runtime_root / "pushan.db"))
    os.environ.setdefault(
        "PUSHAN_MODEL_PATH", str(runtime_root / "irrigation_model.joblib")
    )
    os.environ.setdefault(
        "PUSHAN_VECTOR_STORE_PATH", str(runtime_root / "vector_store")
    )
    return runtime_root, port


def prepare_runtime_assets() -> None:
    """Copy bundled assets quickly, rebuilding only when they are unavailable."""
    from app.config import settings

    if not settings.model_path.is_file():
        bundled_model = PROJECT_ROOT / "artifacts" / "irrigation_model.joblib"
        if bundled_model.is_file():
            settings.model_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled_model, settings.model_path)
        else:
            from app.ml.data_generator import generate_training_data
            from app.ml.train import train_and_evaluate_models

            training_data = generate_training_data(num_samples=1000, random_seed=42)
            train_and_evaluate_models(training_data, settings.model_path)

    index_metadata = settings.vector_store_path / "index_metadata.json"
    if not index_metadata.is_file():
        bundled_index = PROJECT_ROOT / "artifacts" / "vector_store"
        if (bundled_index / "index_metadata.json").is_file():
            shutil.copytree(
                bundled_index,
                settings.vector_store_path,
                dirs_exist_ok=True,
            )
        else:
            from app.rag.index import index_knowledge

            index_knowledge(persist_path=settings.vector_store_path)


def _serve_api() -> None:
    from app.config import settings
    from app.main_api import app
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


def _wait_until_healthy(port: int, timeout_seconds: float = 90.0) -> None:
    deadline = monotonic() + timeout_seconds
    health_url = f"http://127.0.0.1:{port}/health"
    while monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            sleep(0.25)
    raise RuntimeError("Pushan's embedded API did not become healthy in time.")


def ensure_cloud_runtime() -> None:
    """Prepare assets and start one reusable background API server."""
    global _STARTED
    with _START_LOCK:
        if _STARTED:
            return
        _, port = configure_cloud_environment()
        prepare_runtime_assets()
        Thread(target=_serve_api, name="pushan-api", daemon=True).start()
        _wait_until_healthy(port)
        _STARTED = True
