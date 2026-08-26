"""Tests for V0.8 controlled LangGraph routing and degraded behavior."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.agent_service import AgentResponse, run_pushan_agent
from app.agents.nodes import (
    MAX_RAG_ATTEMPTS,
    fetch_sensor_node,
    final_answer_node,
    ml_prediction_node,
    operational_node,
    retrieve_knowledge_node,
    rule_engine_node,
)
from app.main_api import create_app


SENSOR = {
    "field_id": "FIELD_001", "soil_moisture": 18, "temperature": 36,
    "humidity": 32, "rain_probability": 10, "pump_status": "OFFLINE",
    "water_available_litres": 10000, "sensor_status": "HEALTHY",
}
FARM_INPUT = {
    "soil_moisture": 18, "temperature": 36, "humidity": 32,
    "rain_probability": 10, "crop": "tomato", "crop_stage": "flowering",
    "field_area_m2": 1000,
}
RULE = {
    "irrigation_required": True, "recommended_water_litres": 6325,
    "risk_level": "MEDIUM", "reason": "Moisture is low.",
}


class AgentTests(unittest.TestCase):
    @patch("app.agents.tools.get_ml_prediction", return_value=5980.0)
    def test_field_request_routes_sensor_path(self, _mock):
        result = run_pushan_agent("Should FIELD_001 be irrigated?")
        self.assertEqual(result.intent, "FIELD_ASSESSMENT")
        self.assertIn("sensor data retrieved", result.execution_trace)
        self.assertFalse(result.structured_results["operational_decision"]["execution_possible"])

    @patch("app.agents.tools.search_agriculture_knowledge", return_value=("Check the filter.", ["drip_irrigation_sop.md"]))
    def test_knowledge_request_routes_rag_path(self, _mock):
        result = run_pushan_agent("What should I check if drip pressure is low?")
        self.assertEqual(result.intent, "KNOWLEDGE_QUERY")
        self.assertNotIn("sensor data retrieved", result.execution_trace)
        self.assertEqual(result.sources, ["drip_irrigation_sop.md"])

    @patch("app.agents.tools.search_agriculture_knowledge", return_value=("Check pump status.", ["drip_irrigation_sop.md"]))
    @patch("app.agents.tools.get_ml_prediction", return_value=5980.0)
    def test_full_analysis_uses_field_and_rag_paths(self, _ml, _rag):
        result = run_pushan_agent("Analyse FIELD_001 and explain whether irrigation should run.")
        self.assertEqual(result.intent, "FULL_ANALYSIS")
        self.assertIn("sensor data retrieved", result.execution_trace)
        self.assertIn("RAG knowledge retrieved", result.execution_trace)

    def test_sensor_node_updates_state(self):
        update = fetch_sensor_node({"field_id": "FIELD_001", "execution_trace": [], "errors": []})
        self.assertEqual(update["sensor_reading"]["field_id"], "FIELD_001")
        self.assertIn("farm_input", update)

    def test_rule_node_updates_state(self):
        update = rule_engine_node({"farm_input": FARM_INPUT, "execution_trace": [], "errors": []})
        self.assertTrue(update["rule_recommendation"]["irrigation_required"])

    @patch("app.agents.tools.get_ml_prediction", return_value=1234.0)
    def test_ml_node_updates_state(self, _mock):
        update = ml_prediction_node({"farm_input": FARM_INPUT, "execution_trace": [], "errors": [], "model_path": "model"})
        self.assertEqual(update["ml_prediction"], 1234.0)

    @patch("app.agents.tools.search_agriculture_knowledge", return_value=("Answer", ["source.md"]))
    def test_rag_node_updates_state(self, _mock):
        update = retrieve_knowledge_node({"user_request": "question", "execution_trace": [], "errors": [], "rag_attempts": 0, "vector_store_path": "vectors"})
        self.assertEqual(update["rag_sources"], ["source.md"])

    def test_operational_node_updates_state(self):
        update = operational_node({"rule_recommendation": RULE, "sensor_reading": SENSOR, "execution_trace": []})
        self.assertFalse(update["operational_decision"]["execution_possible"])

    def test_final_answer_preserves_operational_block(self):
        operation = {"execution_possible": False, "reason": "Pump offline.", "action_required": "MAINTENANCE_REQUIRED"}
        update = final_answer_node({"field_id": "FIELD_001", "rule_recommendation": RULE, "operational_decision": operation, "rag_answer": "Proceed immediately.", "execution_trace": [], "errors": []})
        self.assertIn("Operational status: BLOCKED", update["final_answer"])
        self.assertNotIn("Operational status: PERMITTED", update["final_answer"])
        self.assertNotIn("Proceed immediately", update["final_answer"])

    def test_missing_field_is_clear(self):
        result = run_pushan_agent("Provide a field assessment")
        self.assertIn("field ID is required", result.errors[0])

    @patch("app.agents.tools.get_field_sensor_data", side_effect=ValueError("Sensor unavailable"))
    def test_sensor_failure_is_controlled(self, _mock):
        result = run_pushan_agent("Assess FIELD_001")
        self.assertIn("Sensor unavailable", result.errors)
        self.assertIn("sensor retrieval failed", result.execution_trace)

    @patch("app.agents.tools.get_ml_prediction", side_effect=FileNotFoundError("missing model"))
    def test_ml_failure_allows_degraded_completion(self, _mock):
        result = run_pushan_agent("Assess FIELD_001")
        self.assertIn("Operational status: BLOCKED", result.answer)
        self.assertTrue(any("ML advisory unavailable" in error for error in result.errors))

    @patch("app.agents.tools.search_agriculture_knowledge", side_effect=FileNotFoundError("missing index"))
    def test_rag_failure_allows_degraded_completion(self, mock):
        result = run_pushan_agent("What is safe AWD?")
        self.assertEqual(mock.call_count, MAX_RAG_ATTEMPTS)
        self.assertTrue(any("Knowledge service unavailable" in error for error in result.errors))

    @patch("app.agents.tools.search_agriculture_knowledge", side_effect=RuntimeError("provider down"))
    def test_retry_never_exceeds_maximum(self, mock):
        result = run_pushan_agent("Explain drip filters")
        self.assertEqual(mock.call_count, MAX_RAG_ATTEMPTS)
        self.assertEqual(result.execution_trace.count("RAG retrieval retry scheduled"), 1)

    @patch("app.agents.tools.get_ml_prediction", return_value=5980.0)
    def test_trace_has_expected_steps(self, _mock):
        result = run_pushan_agent("Assess FIELD_001")
        self.assertEqual(result.execution_trace[-1], "final answer generated")
        self.assertIn("operational evaluation completed", result.execution_trace)

    def test_unknown_field_is_handled(self):
        result = run_pushan_agent("Assess FIELD_999")
        self.assertTrue(any("Unknown field ID" in error for error in result.errors))

    def test_api_accepts_valid_request(self):
        fake = AgentResponse("FIELD_ASSESSMENT", "Blocked", ["classified"], [], [], {})
        with patch("app.api.routes.run_pushan_agent", return_value=fake):
            with tempfile.TemporaryDirectory() as temporary:
                with TestClient(create_app(Path(temporary) / "db.sqlite")) as client:
                    response = client.post("/agent/run", json={"message": "Assess FIELD_001"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Blocked")

    def test_api_rejects_empty_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            with TestClient(create_app(Path(temporary) / "db.sqlite")) as client:
                response = client.post("/agent/run", json={"message": " "})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
