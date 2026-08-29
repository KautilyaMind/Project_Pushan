"""End-to-end component flows without paid or external services."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.agents.agent_service import run_pushan_agent
from app.models import SensorReading
from app.ml.data_generator import generate_training_data
from app.ml.train import train_and_evaluate_models
from app.rag.qa_service import RAGResponse
from app.workflows.approval_service import approve_request
from app.workflows.repository import list_records
from app.workflows.workflow_engine import resume_approval_workflow


def reading(*, field_id: str = "FIELD_001", soil: float = 18,
            pump: str = "ONLINE", water: float = 20000) -> SensorReading:
    return SensorReading(field_id, soil, 32, 45, 10, pump, water, "HEALTHY")


class PlatformIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.model = cls.root / "model.joblib"
        train_and_evaluate_models(generate_training_data(200, 42), cls.model, n_estimators=10)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def setUp(self) -> None:
        self.db = self.root / f"{self._testMethodName}.db"

    @patch("app.agents.tools.get_latest_reading", return_value=reading(field_id="FIELD_002", soil=35))
    def test_normal_assessment_reaches_completed_workflow(self, _: object) -> None:
        result = run_pushan_agent("Assess FIELD_002", model_path=self.model, database_path=self.db)
        self.assertEqual(result.workflow_status, "COMPLETED")
        self.assertEqual(result.structured_results["workflow"]["action_type"], "NO_ACTION")

    @patch("app.agents.tools.get_latest_reading", return_value=reading(pump="OFFLINE"))
    def test_pump_offline_creates_incident_and_audit(self, _: object) -> None:
        result = run_pushan_agent("Assess FIELD_001", model_path=self.model, database_path=self.db)
        self.assertEqual(result.workflow_status, "COMPLETED")
        self.assertEqual(list_records("incidents", self.db)[0]["incident_type"], "PUMP_OFFLINE")
        self.assertTrue(list_records("audit_log", self.db))

    @patch("app.agents.tools.get_latest_reading", return_value=reading(soil=10))
    def test_high_risk_approval_resumes_execution(self, _: object) -> None:
        result = run_pushan_agent("Assess FIELD_001", model_path=self.model, database_path=self.db)
        self.assertEqual(result.workflow_status, "WAITING_FOR_APPROVAL")
        approve_request(result.approval_request_id, "integration_operator", "reviewed", self.db)  # type: ignore[arg-type]
        workflow = resume_approval_workflow(result.approval_request_id, self.db)  # type: ignore[arg-type]
        self.assertEqual(workflow["status"], "COMPLETED")

    @patch("app.agents.tools.answer_question", return_value=RAGResponse(
        "Check the filter and pressure regulator.", ["drip_irrigation_sop.md"], ["context"]
    ))
    def test_knowledge_flow_returns_grounded_source(self, _: object) -> None:
        result = run_pushan_agent("What should I check for low drip pressure?", database_path=self.db)
        self.assertIn("drip_irrigation_sop.md", result.sources)
        self.assertIn("pressure", result.answer)

    @patch("app.agents.tools.get_ml_prediction", side_effect=FileNotFoundError("missing"))
    @patch("app.agents.tools.get_latest_reading", return_value=reading(field_id="FIELD_002", soil=35))
    def test_degraded_ml_keeps_rules_and_operations(self, _: object, __: object) -> None:
        result = run_pushan_agent("Assess FIELD_002", model_path=self.model, database_path=self.db)
        self.assertIn("rule_recommendation", result.structured_results)
        self.assertIn("operational_decision", result.structured_results)
        self.assertTrue(any("ML advisory unavailable" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
