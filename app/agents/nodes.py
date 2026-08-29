"""Small nodes that each own one orchestration responsibility."""

import logging
import re
from time import perf_counter

from app.ml.train import DEFAULT_MODEL_PATH
from app.rag.vector_store import DEFAULT_VECTOR_STORE_PATH
from app.rag.qa_service import _response_text, get_llm
from app.services.sensor_service import FIELD_CONFIGURATIONS

from . import tools
from .state import AgentIntent, PushanAgentState


logger = logging.getLogger(__name__)
MAX_RAG_ATTEMPTS = 2


def _append(state: PushanAgentState, message: str) -> list[str]:
    return [*state.get("execution_trace", []), message]


def _errors(state: PushanAgentState, message: str) -> list[str]:
    return [*state.get("errors", []), message]


def extract_field_id(message: str) -> str | None:
    match = re.search(r"\bFIELD[_ -]?(\d{3})\b", message, re.IGNORECASE)
    return f"FIELD_{match.group(1)}" if match else None


def classify_intent(message: str) -> AgentIntent:
    text = message.lower()
    knowledge_words = ("explain", "guidance", "sop", "what should", "how ", "why ", "knowledge")
    has_field = bool(extract_field_id(message)) or any(
        phrase in text for phrase in ("field assessment", "assess the field")
    )
    has_knowledge = any(word in text for word in knowledge_words)
    if has_field and has_knowledge and any(word in text for word in ("analyse", "analyze", "consider", "explain")):
        return "FULL_ANALYSIS"
    if has_field:
        return "FIELD_ASSESSMENT"
    return "KNOWLEDGE_QUERY"


def _is_ambiguous(message: str) -> bool:
    text = message.lower()
    signals = (
        "field", "assess", "irrigat", "sensor", "pump", "explain", "guidance",
        "sop", "what", "how", "why", "knowledge", "analyse", "analyze",
    )
    return not any(signal in text for signal in signals)


def classify_with_optional_llm(message: str) -> AgentIntent:
    """Use constrained Gemini classification for ambiguity, then fall back safely."""
    fallback = classify_intent(message)
    if not _is_ambiguous(message):
        return fallback
    try:
        response = get_llm().invoke(
            "Classify this Pushan request as exactly one value: FIELD_ASSESSMENT, "
            "KNOWLEDGE_QUERY, or FULL_ANALYSIS. Return only the value.\nRequest: "
            + message
        )
        candidate = _response_text(response).strip().upper()
        if candidate in {"FIELD_ASSESSMENT", "KNOWLEDGE_QUERY", "FULL_ANALYSIS"}:
            return candidate  # type: ignore[return-value]
    except Exception as error:
        logger.info("LLM classification unavailable; deterministic fallback used: %s", type(error).__name__)
    return fallback


def classify_request_node(state: PushanAgentState) -> dict:
    intent = classify_with_optional_llm(state["user_request"])
    field_id = state.get("field_id") or extract_field_id(state["user_request"])
    logger.info("intent classified as %s", intent)
    return {
        "intent": intent,
        "field_id": field_id,
        "execution_trace": _append(state, f"classified as {intent}"),
    }


def fetch_sensor_node(state: PushanAgentState) -> dict:
    field_id = state.get("field_id")
    if not field_id:
        return {
            "errors": _errors(state, "A field ID is required (for example FIELD_001)."),
            "execution_trace": _append(state, "sensor data skipped: field ID missing"),
        }
    try:
        started = perf_counter()
        sensor = tools.get_field_sensor_data(field_id)
        farm_input = tools.build_field_input(field_id, sensor)
        logger.info("sensor data retrieved in %.1f ms", (perf_counter() - started) * 1000,
                    extra={"field_id": field_id})
        return {"sensor_reading": sensor, "farm_input": farm_input,
                "execution_trace": _append(state, "sensor data retrieved")}
    except (ValueError, KeyError) as error:
        return {"errors": _errors(state, str(error)),
                "execution_trace": _append(state, "sensor retrieval failed")}


def retrieve_knowledge_node(state: PushanAgentState) -> dict:
    attempts = state.get("rag_attempts", 0) + 1
    try:
        started = perf_counter()
        answer, sources = tools.search_agriculture_knowledge(
            state["user_request"], state.get("vector_store_path", str(DEFAULT_VECTOR_STORE_PATH))
        )
        logger.info("RAG retrieval completed in %.1f ms", (perf_counter() - started) * 1000)
        return {"rag_answer": answer, "rag_sources": sources, "rag_attempts": attempts,
                "rag_retry_needed": False,
                "execution_trace": _append(state, "RAG knowledge retrieved")}
    except Exception as error:  # provider/index errors degrade the graph, not the API
        logger.warning("RAG attempt %s failed: %s", attempts, type(error).__name__)
        retry = attempts < MAX_RAG_ATTEMPTS
        update = {"rag_attempts": attempts, "rag_retry_needed": retry,
                  "execution_trace": _append(state, "RAG retrieval retry scheduled" if retry else "RAG unavailable; continuing in degraded mode")}
        if not retry:
            update["errors"] = _errors(state, f"Knowledge service unavailable: {error}")
        return update


def rule_engine_node(state: PushanAgentState) -> dict:
    if "farm_input" not in state:
        return {"execution_trace": _append(state, "rule engine skipped")}
    try:
        result = tools.get_rule_recommendation(state["farm_input"])
        return {"rule_recommendation": result,
                "execution_trace": _append(state, "rule engine completed")}
    except (ValueError, TypeError) as error:
        return {"errors": _errors(state, f"Rule engine unavailable: {error}"),
                "execution_trace": _append(state, "rule engine failed")}


def ml_prediction_node(state: PushanAgentState) -> dict:
    if "farm_input" not in state:
        return {"execution_trace": _append(state, "ML prediction skipped")}
    try:
        started = perf_counter()
        prediction = tools.get_ml_prediction(
            state["farm_input"], state.get("model_path", str(DEFAULT_MODEL_PATH))
        )
        logger.info("ML prediction completed in %.1f ms", (perf_counter() - started) * 1000,
                    extra={"field_id": state.get("field_id")})
        return {"ml_prediction": prediction,
                "execution_trace": _append(state, "ML prediction completed")}
    except (FileNotFoundError, ValueError) as error:
        return {"errors": _errors(state, f"ML advisory unavailable: {error}"),
                "execution_trace": _append(state, "ML unavailable; continuing in degraded mode")}


def operational_node(state: PushanAgentState) -> dict:
    if "rule_recommendation" not in state or "sensor_reading" not in state:
        return {"execution_trace": _append(state, "operational evaluation skipped")}
    decision = tools.get_operational_decision(
        state["rule_recommendation"], state["sensor_reading"]
    )
    return {"operational_decision": decision,
            "execution_trace": _append(state, "operational evaluation completed")}


def final_answer_node(state: PushanAgentState) -> dict:
    lines: list[str] = []
    field_id = state.get("field_id")
    rule = state.get("rule_recommendation")
    operation = state.get("operational_decision")
    if rule and field_id:
        lines.append(f"{field_id} {'requires' if rule['irrigation_required'] else 'does not require'} irrigation.")
        lines.append(f"Rule-based estimate: {rule['recommended_water_litres']:g} L ({rule['risk_level']} risk).")
    if "ml_prediction" in state:
        lines.append(f"ML advisory: {state['ml_prediction']:g} L.")
    if operation:
        status = "PERMITTED" if operation["execution_possible"] else "BLOCKED"
        lines.extend([f"Operational status: {status}.", f"Reason: {operation['reason']}",
                      f"Recommended action: {operation['action_required']}."])
    if state.get("rag_answer"):
        guidance = state["rag_answer"]
        if operation and not operation["execution_possible"] and re.search(
            r"\b(proceed|start irrigation|run irrigation|irrigation can proceed)\b",
            guidance,
            re.IGNORECASE,
        ):
            guidance = "Retrieved guidance was omitted because it conflicted with the operational safety state."
        lines.append(f"Relevant knowledge guidance: {guidance}")
    if not lines:
        lines.append("Pushan could not complete the requested analysis. " + (state.get("errors") or ["Provide more information."])[-1])
    if state.get("errors"):
        lines.append("Warnings: " + " | ".join(state["errors"]))
    return {"final_answer": "\n\n".join(lines),
            "execution_trace": _append(state, "final answer generated")}
