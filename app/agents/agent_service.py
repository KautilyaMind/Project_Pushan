"""Stable service boundary around the compiled Pushan graph."""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from app.ml.train import DEFAULT_MODEL_PATH
from app.rag.vector_store import DEFAULT_VECTOR_STORE_PATH

from .graph import pushan_graph


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResponse:
    intent: str
    answer: str
    execution_trace: list[str]
    sources: list[str]
    errors: list[str]
    structured_results: dict[str, Any]


def run_pushan_agent(
    user_request: str,
    field_id: str | None = None,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    vector_store_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
) -> AgentResponse:
    if not user_request.strip():
        raise ValueError("user_request must not be empty")
    logger.info("agent request started")
    state = pushan_graph.invoke({
        "user_request": user_request.strip(), "field_id": field_id,
        "errors": [], "execution_trace": [], "rag_attempts": 0,
        "model_path": str(model_path), "vector_store_path": str(vector_store_path),
    })
    logger.info("agent request completed")
    structured = {key: state[key] for key in (
        "sensor_reading", "rule_recommendation", "ml_prediction", "operational_decision"
    ) if key in state}
    return AgentResponse(
        intent=state["intent"], answer=state["final_answer"],
        execution_trace=state.get("execution_trace", []),
        sources=state.get("rag_sources", []), errors=state.get("errors", []),
        structured_results=structured,
    )
