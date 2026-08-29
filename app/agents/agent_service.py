"""Stable service boundary around the compiled Pushan graph."""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

from app.ml.train import DEFAULT_MODEL_PATH
from app.rag.vector_store import DEFAULT_VECTOR_STORE_PATH
from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath
from app.workflows.workflow_engine import propose_workflow

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
    workflow_id: str | None = None
    workflow_status: str | None = None
    approval_request_id: str | None = None
    approval_required: bool = False
    technically_executable: bool | None = None
    authorized_to_execute: bool | None = None


def run_pushan_agent(
    user_request: str,
    field_id: str | None = None,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    vector_store_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
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
    workflow = None
    if all(key in structured for key in (
        "sensor_reading", "rule_recommendation", "operational_decision"
    )):
        workflow = propose_workflow(
            state.get("field_id") or "UNKNOWN", structured["sensor_reading"],
            structured["rule_recommendation"], structured["operational_decision"],
            database_path,
        )
        structured["guardrail"] = workflow["guardrail_result"]
        structured["workflow"] = {key: workflow.get(key) for key in (
            "workflow_id", "status", "action_type", "duplicate_prevented"
        )}
        workflow_trace = [
            f"guardrails: {'approval required' if workflow['guardrail_result']['approval_required'] else 'evaluated'}",
            f"workflow: {workflow['status']}",
        ]
        trace = state.setdefault("execution_trace", [])
        final_index = trace.index("final answer generated") if "final answer generated" in trace else len(trace)
        trace[final_index:final_index] = workflow_trace
        state["final_answer"] += f"\n\nWorkflow status: {workflow['status']}."
        if workflow["status"] == "WAITING_FOR_APPROVAL":
            state["final_answer"] += " Human approval is required before execution."
    return AgentResponse(
        intent=state["intent"], answer=state["final_answer"],
        execution_trace=state.get("execution_trace", []),
        sources=state.get("rag_sources", []), errors=state.get("errors", []),
        structured_results=structured,
        workflow_id=workflow["workflow_id"] if workflow else None,
        workflow_status=workflow["status"] if workflow else None,
        approval_request_id=workflow.get("approval_request_id") if workflow else None,
        approval_required=bool(workflow and workflow["status"] == "WAITING_FOR_APPROVAL"),
        technically_executable=(
            structured["operational_decision"]["execution_possible"]
            if "operational_decision" in structured else None
        ),
        authorized_to_execute=bool(workflow and workflow["status"] == "COMPLETED"),
    )
