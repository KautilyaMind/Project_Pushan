"""V0.9 tests for guardrails, approval, idempotency, and auditability."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main_api import create_app
from app.workflows.approval_service import (
    approve_request, get_approval, get_pending_approvals, reject_request,
)
from app.workflows.guardrails import evaluate_guardrails
from app.workflows.repository import list_records
from app.workflows.workflow_engine import (
    execute_workflow, get_workflow, propose_workflow, resume_approval_workflow,
)


def sensor(**updates):
    value = {"field_id": "FIELD_TEST", "soil_moisture": 20, "temperature": 30,
             "humidity": 50, "rain_probability": 10, "pump_status": "ONLINE",
             "water_available_litres": 10000, "sensor_status": "HEALTHY"}
    value.update(updates); return value


def recommendation(**updates):
    value = {"irrigation_required": True, "recommended_water_litres": 3000.0,
             "risk_level": "LOW", "reason": "Dry soil"}
    value.update(updates); return value


def operational(**updates):
    value = {"execution_possible": True, "action_required": "IRRIGATE",
             "reason": "Ready", "irrigation_required": True,
             "recommended_water_litres": 3000.0, "risk_level": "LOW"}
    value.update(updates); return value


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Path(self.temporary.name) / "workflow.db"

    def tearDown(self):
        self.temporary.cleanup()

    def propose(self, rec=None, op=None, sensed=None, key=None):
        return propose_workflow("FIELD_TEST", sensed or sensor(), rec or recommendation(),
                                op or operational(), self.db, key)

    def test_low_risk_irrigation_auto_approves(self):
        result = self.propose(key="low-risk")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNone(result["approval_request_id"])

    def test_high_risk_requires_approval(self):
        rec = recommendation(risk_level="HIGH")
        result = self.propose(rec=rec, op=operational(risk_level="HIGH"), key="high-risk")
        self.assertEqual(result["status"], "WAITING_FOR_APPROVAL")
        self.assertIsNotNone(result["approval_request_id"])

    def test_high_volume_requires_approval(self):
        rec = recommendation(recommended_water_litres=6000)
        result = self.propose(rec=rec, op=operational(recommended_water_litres=6000), key="high-volume")
        self.assertEqual(result["status"], "WAITING_FOR_APPROVAL")

    def test_faulty_sensor_blocks_irrigation(self):
        result = evaluate_guardrails(sensor(sensor_status="FAULTY"), recommendation(), operational())
        self.assertFalse(result.allowed)
        self.assertIn("SENSOR_FAULT", result.guardrail_flags)

    def test_offline_pump_creates_maintenance_incident(self):
        op = operational(execution_possible=False, action_required="MAINTENANCE_REQUIRED", reason="offline")
        result = self.propose(sensed=sensor(pump_status="OFFLINE"), op=op, key="pump")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(list_records("incidents", self.db)[0]["incident_type"], "PUMP_OFFLINE")

    def test_insufficient_water_creates_refill_workflow(self):
        rec = recommendation(recommended_water_litres=5000)
        op = operational(execution_possible=False, action_required="REFILL_WATER", recommended_water_litres=5000)
        result = self.propose(rec=rec, op=op, sensed=sensor(water_available_litres=100), key="refill")
        self.assertEqual(result["action_type"], "REFILL_WATER")

    def test_pending_approval_is_persisted(self):
        result = self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="persist")
        self.assertEqual(get_approval(result["approval_request_id"], self.db)["status"], "PENDING")

    def test_approve_changes_status_and_executes(self):
        result = self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="approve")
        approve_request(result["approval_request_id"], "operator", "reviewed", self.db)
        workflow = resume_approval_workflow(result["approval_request_id"], self.db)
        self.assertEqual(workflow["status"], "COMPLETED")

    def test_reject_changes_status_and_never_executes(self):
        result = self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="reject")
        reject_request(result["approval_request_id"], "operator", "inspect", self.db)
        workflow = resume_approval_workflow(result["approval_request_id"], self.db)
        self.assertEqual(workflow["status"], "BLOCKED")
        self.assertIsNone(workflow["started_at"])

    def test_duplicate_execution_is_prevented(self):
        first = self.propose(key="duplicate")
        second = execute_workflow(first["workflow_id"], self.db)
        self.assertTrue(second["duplicate_prevented"])

    def test_duplicate_proposal_reuses_workflow(self):
        first = self.propose(key="same")
        second = self.propose(key="same")
        self.assertEqual(first["workflow_id"], second["workflow_id"])
        self.assertTrue(second["duplicate_prevented"])

    def test_notification_is_recorded(self):
        op = operational(execution_possible=False, action_required="MAINTENANCE_REQUIRED")
        self.propose(sensed=sensor(pump_status="OFFLINE"), op=op, key="notify")
        self.assertEqual(len(list_records("notifications", self.db)), 1)

    def test_audit_events_are_persisted(self):
        self.propose(key="audit")
        events = {row["event_type"] for row in list_records("audit_log", self.db)}
        self.assertIn("ACTION_PROPOSED", events)
        self.assertIn("WORKFLOW_COMPLETED", events)

    @patch.dict("os.environ", {"PUSHAN_AUTOMATION_WEBHOOK_URL": "https://invalid.test"})
    @patch("app.workflows.notification_service.httpx.post", side_effect=httpx.ConnectError("down"))
    def test_webhook_failure_does_not_crash(self, _mock):
        op = operational(execution_possible=False, action_required="MAINTENANCE_REQUIRED")
        result = self.propose(sensed=sensor(pump_status="OFFLINE"), op=op, key="webhook-fail")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(list_records("notifications", self.db)[0]["delivery_status"], "FAILED")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_webhook_uses_local_simulation(self):
        op = operational(execution_possible=False, action_required="CHECK_SENSOR")
        self.propose(sensed=sensor(sensor_status="FAULTY"), op=op, key="local")
        self.assertEqual(list_records("notifications", self.db)[0]["delivery_status"], "SIMULATED")

    def test_workflow_survives_database_reload(self):
        result = self.propose(key="reload")
        self.assertEqual(get_workflow(result["workflow_id"], Path(str(self.db)))["status"], "COMPLETED")

    def test_pending_list_only_returns_pending(self):
        self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="pending")
        self.assertEqual(len(get_pending_approvals(self.db)), 1)

    def test_approval_api_and_workflow_status(self):
        result = self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="api")
        with TestClient(create_app(self.db)) as client:
            self.assertEqual(len(client.get("/approvals").json()), 1)
            response = client.post(f"/approvals/{result['approval_request_id']}/approve",
                                   json={"approved_by": "operator", "note": "reviewed"})
            self.assertEqual(response.status_code, 200)
            workflow_id = response.json()["workflow"]["workflow_id"]
            self.assertEqual(client.get(f"/workflows/{workflow_id}").json()["status"], "COMPLETED")

    def test_reject_api_blocks_workflow(self):
        result = self.propose(rec=recommendation(risk_level="HIGH"), op=operational(risk_level="HIGH"), key="api-reject")
        with TestClient(create_app(self.db)) as client:
            response = client.post(f"/approvals/{result['approval_request_id']}/reject",
                                   json={"rejected_by": "operator", "note": "no"})
        self.assertEqual(response.json()["workflow"]["status"], "BLOCKED")

    def test_incident_endpoint(self):
        op = operational(execution_possible=False, action_required="MAINTENANCE_REQUIRED")
        self.propose(sensed=sensor(pump_status="OFFLINE"), op=op, key="incident-api")
        with TestClient(create_app(self.db)) as client:
            self.assertEqual(client.get("/incidents").json()[0]["incident_type"], "PUMP_OFFLINE")


if __name__ == "__main__":
    unittest.main()
