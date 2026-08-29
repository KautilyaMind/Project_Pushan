"""Persistent human approval decisions and workflow resumption."""

import uuid

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath, initialize_database
from app.database.repository import utc_timestamp
from .repository import audit, get_one, insert_record, list_records, update_record


def create_approval_request(field_id: str, action_type: str, water_litres: float,
                            risk_level: str, reason: str,
                            database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    initialize_database(database_path)
    request_id = f"APR-{uuid.uuid4().hex[:12].upper()}"
    record = {"request_id": request_id, "field_id": field_id, "created_at": utc_timestamp(),
              "action_type": action_type, "recommended_water_litres": water_litres,
              "risk_level": risk_level, "status": "PENDING", "reason": reason,
              "approved_by": None, "approved_at": None, "rejected_at": None,
              "decision_note": None}
    insert_record("approval_requests", record, database_path)
    audit("APPROVAL_REQUESTED", "APPROVAL", request_id, field_id, "AGENT", {"reason": reason}, database_path)
    return record


def get_approval(request_id: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict | None:
    return get_one("approval_requests", "request_id", request_id, database_path)


def get_pending_approvals(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> list[dict]:
    return list_records("approval_requests", database_path, status="PENDING")


def approve_request(request_id: str, approved_by: str, note: str = "",
                    database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    return _decide(request_id, "APPROVED", approved_by, note, database_path)


def reject_request(request_id: str, rejected_by: str, note: str = "",
                   database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    return _decide(request_id, "REJECTED", rejected_by, note, database_path)


def _decide(request_id: str, status: str, actor: str, note: str, database_path: DatabasePath) -> dict:
    approval = get_approval(request_id, database_path)
    if not approval:
        raise ValueError(f"Unknown approval request: {request_id}")
    if approval["status"] != "PENDING":
        raise ValueError(f"Approval request is already {approval['status']}")
    now = utc_timestamp()
    updates = {"status": status, "approved_by": actor, "decision_note": note,
               "approved_at" if status == "APPROVED" else "rejected_at": now}
    update_record("approval_requests", "request_id", request_id, updates, database_path)
    audit("APPROVAL_GRANTED" if status == "APPROVED" else "APPROVAL_REJECTED",
          "APPROVAL", request_id, approval["field_id"], "HUMAN_OPERATOR",
          {"actor": actor, "note": note}, database_path)
    return get_approval(request_id, database_path)  # type: ignore[return-value]
