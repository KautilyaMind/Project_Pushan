"""Lightweight dependency readiness checks."""

from pathlib import Path
from typing import Any

import joblib

from app.database.db import execute, get_connection


def readiness_report(database_path: str | Path, model_path: str | Path,
                     vector_store_path: str | Path, webhook_url: str = "") -> dict[str, Any]:
    checks = {
        "database": _database_check(database_path),
        "ml_model": _model_check(model_path),
        "knowledge_base": _knowledge_check(vector_store_path),
        "automation_webhook": "configured" if webhook_url else "not_configured",
    }
    critical_ok = checks["database"] == "ok"
    features_ok = checks["ml_model"] == "ok" and checks["knowledge_base"] == "ok"
    status = "ready" if critical_ok and features_ok else "degraded" if critical_ok else "not_ready"
    return {"status": status, "checks": checks}


def _database_check(path: str | Path) -> str:
    try:
        connection = get_connection(path)
        try:
            execute(connection, "SELECT 1").fetchone()
        finally:
            connection.close()
        return "ok"
    except Exception:
        return "unavailable"


def _model_check(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        return "missing"
    try:
        model = joblib.load(candidate)
        return "ok" if hasattr(model, "predict") else "incompatible"
    except Exception:
        return "incompatible"


def _knowledge_check(path: str | Path) -> str:
    candidate = Path(path)
    return "ok" if candidate.is_dir() and any(candidate.iterdir()) else "missing"
