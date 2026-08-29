"""Persistent simulated incident creation."""

import uuid

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath
from app.database.repository import utc_timestamp
from .repository import audit, insert_record, list_records


def create_incident(field_id: str, incident_type: str, severity: str, description: str,
                    workflow_id: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    incident_id = f"INC-{uuid.uuid4().hex[:12].upper()}"
    record = {"incident_id": incident_id, "field_id": field_id, "created_at": utc_timestamp(),
              "incident_type": incident_type, "severity": severity, "status": "OPEN",
              "description": description, "source_workflow_id": workflow_id}
    insert_record("incidents", record, database_path)
    audit("INCIDENT_CREATED", "INCIDENT", incident_id, field_id, "SYSTEM", record, database_path)
    return record


def get_incidents(database_path: DatabasePath = DEFAULT_DATABASE_PATH, field_id: str | None = None) -> list[dict]:
    return list_records("incidents", database_path, field_id=field_id)
