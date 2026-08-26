"""Shared state carried between Pushan's graph nodes."""

from typing import Any, Literal, TypedDict


AgentIntent = Literal["FIELD_ASSESSMENT", "KNOWLEDGE_QUERY", "FULL_ANALYSIS"]


class PushanAgentState(TypedDict, total=False):
    user_request: str
    field_id: str | None
    intent: AgentIntent
    sensor_reading: dict[str, Any]
    farm_input: dict[str, Any]
    rule_recommendation: dict[str, Any]
    ml_prediction: float
    rag_answer: str
    rag_sources: list[str]
    operational_decision: dict[str, Any]
    errors: list[str]
    rag_attempts: int
    rag_retry_needed: bool
    execution_trace: list[str]
    final_answer: str
    model_path: str
    vector_store_path: str
