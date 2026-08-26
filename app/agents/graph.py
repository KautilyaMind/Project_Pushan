"""Construct Pushan's explicit, finite LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from .nodes import (
    classify_request_node, fetch_sensor_node, final_answer_node,
    ml_prediction_node, operational_node, retrieve_knowledge_node,
    rule_engine_node,
)
from .state import PushanAgentState


def _route_intent(state: PushanAgentState) -> str:
    return state["intent"]


def _route_rag_retry(state: PushanAgentState) -> str:
    return "retry" if state.get("rag_retry_needed", False) else "continue"


def _route_after_sensor(state: PushanAgentState) -> str:
    return "rules" if "farm_input" in state else "final"


def build_pushan_graph():
    graph = StateGraph(PushanAgentState)
    graph.add_node("classify_request", classify_request_node)
    graph.add_node("fetch_sensor", fetch_sensor_node)
    graph.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph.add_node("rule_engine", rule_engine_node)
    graph.add_node("ml_prediction", ml_prediction_node)
    graph.add_node("operational", operational_node)
    graph.add_node("final_answer", final_answer_node)
    graph.add_edge(START, "classify_request")
    graph.add_conditional_edges("classify_request", _route_intent, {
        "KNOWLEDGE_QUERY": "retrieve_knowledge",
        "FIELD_ASSESSMENT": "fetch_sensor",
        "FULL_ANALYSIS": "fetch_sensor",
    })
    graph.add_conditional_edges("fetch_sensor", _route_after_sensor, {
        "rules": "rule_engine", "final": "final_answer"
    })
    graph.add_conditional_edges("retrieve_knowledge", _route_rag_retry, {
        "retry": "retrieve_knowledge", "continue": "final_answer"
    })
    graph.add_edge("rule_engine", "ml_prediction")
    graph.add_edge("ml_prediction", "operational")
    graph.add_conditional_edges("operational", lambda state: state["intent"], {
        "FULL_ANALYSIS": "retrieve_knowledge",
        "FIELD_ASSESSMENT": "final_answer",
        "KNOWLEDGE_QUERY": "final_answer",
    })
    graph.add_edge("final_answer", END)
    return graph.compile()


pushan_graph = build_pushan_graph()
