"""Idempotent simulated downstream workflow execution."""

from dataclasses import asdict
import hashlib
import uuid

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath, initialize_database
from app.database.repository import utc_timestamp
from .approval_service import create_approval_request, get_approval
from .guardrails import GuardrailResult, evaluate_guardrails
from .incident_service import create_incident
from .notification_service import send_notification
from .repository import audit, find_workflow_by_key, get_one, insert_record, update_record


def stable_idempotency_key(field_id: str, action: str, water: float, risk: str) -> str:
    raw = f"{field_id}|{action}|{water:.2f}|{risk}"
    return hashlib.sha256(raw.encode()).hexdigest()


def propose_workflow(field_id: str, sensor: dict, recommendation: dict, operational: dict,
                     database_path: DatabasePath = DEFAULT_DATABASE_PATH,
                     idempotency_key: str | None = None) -> dict:
    initialize_database(database_path)
    action = operational["action_required"]
    guardrail = evaluate_guardrails(sensor, recommendation, operational)
    key = idempotency_key or stable_idempotency_key(
        field_id, action, recommendation["recommended_water_litres"], recommendation["risk_level"])
    existing = find_workflow_by_key(key, database_path)
    if existing:
        existing["guardrail_result"] = asdict(guardrail)
        existing["duplicate_prevented"] = True
        return existing
    workflow_id = f"WF-{uuid.uuid4().hex[:12].upper()}"
    approval = None
    if action == "IRRIGATE" and guardrail.approval_required:
        approval = create_approval_request(field_id, action,
            recommendation["recommended_water_litres"], recommendation["risk_level"],
            ", ".join(guardrail.guardrail_flags), database_path)
        status = "WAITING_FOR_APPROVAL"
    else:
        status = "PENDING"
    record = {"workflow_id": workflow_id, "field_id": field_id, "created_at": utc_timestamp(),
              "action_type": action, "status": status,
              "approval_request_id": approval["request_id"] if approval else None,
              "started_at": None, "completed_at": None, "failure_reason": None,
              "idempotency_key": key}
    insert_record("workflow_executions", record, database_path)
    audit("ACTION_PROPOSED", "WORKFLOW", workflow_id, field_id, "AGENT",
          {"action": action, "guardrails": asdict(guardrail)}, database_path)
    if not guardrail.allowed:
        audit("GUARDRAIL_BLOCKED", "WORKFLOW", workflow_id, field_id, "SYSTEM",
              {"reason": guardrail.blocked_reason,
               "flags": guardrail.guardrail_flags}, database_path)
    if status == "PENDING":
        record = execute_workflow(workflow_id, database_path)
    record["guardrail_result"] = asdict(guardrail)
    record["duplicate_prevented"] = False
    return record


def execute_workflow(workflow_id: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    workflow = get_workflow(workflow_id, database_path)
    if not workflow:
        raise ValueError(f"Unknown workflow: {workflow_id}")
    if workflow["status"] == "COMPLETED":
        workflow["duplicate_prevented"] = True
        return workflow
    if workflow["status"] == "WAITING_FOR_APPROVAL":
        approval = get_approval(workflow["approval_request_id"], database_path)
        if not approval or approval["status"] == "PENDING":
            return workflow
        if approval["status"] == "REJECTED":
            update_record("workflow_executions", "workflow_id", workflow_id,
                          {"status": "BLOCKED", "failure_reason": "Human approval rejected."}, database_path)
            audit("GUARDRAIL_BLOCKED", "WORKFLOW", workflow_id, workflow["field_id"],
                  "HUMAN_OPERATOR", {"reason": "Human approval rejected."}, database_path)
            return get_workflow(workflow_id, database_path)  # type: ignore[return-value]
    update_record("workflow_executions", "workflow_id", workflow_id,
                  {"status": "RUNNING", "started_at": utc_timestamp()}, database_path)
    audit("WORKFLOW_STARTED", "WORKFLOW", workflow_id, workflow["field_id"], "SYSTEM", {}, database_path)
    action = workflow["action_type"]
    if action in {"MAINTENANCE_REQUIRED", "CHECK_SENSOR", "REFILL_WATER"}:
        incident_type = {"MAINTENANCE_REQUIRED": "PUMP_OFFLINE", "CHECK_SENSOR": "SENSOR_FAULT",
                         "REFILL_WATER": "INSUFFICIENT_WATER"}[action]
        create_incident(workflow["field_id"], incident_type, "HIGH", action.replace("_", " ").title(), workflow_id, database_path)
        send_notification("farm_operator", f"{action} for {workflow['field_id']}",
                          f"Workflow {workflow_id} requires attention.", workflow_id,
                          {"event": action, "field_id": workflow["field_id"], "severity": "HIGH",
                           "message": action, "workflow_id": workflow_id}, database_path)
    update_record("workflow_executions", "workflow_id", workflow_id,
                  {"status": "COMPLETED", "completed_at": utc_timestamp()}, database_path)
    audit("WORKFLOW_COMPLETED", "WORKFLOW", workflow_id, workflow["field_id"], "SYSTEM", {"action": action}, database_path)
    return get_workflow(workflow_id, database_path)  # type: ignore[return-value]


def resume_approval_workflow(request_id: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    from .repository import list_records
    workflows = list_records("workflow_executions", database_path)
    workflow = next((item for item in workflows if item["approval_request_id"] == request_id), None)
    if not workflow:
        raise ValueError(f"No workflow for approval request: {request_id}")
    return execute_workflow(workflow["workflow_id"], database_path)


def get_workflow(workflow_id: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict | None:
    return get_one("workflow_executions", "workflow_id", workflow_id, database_path)
