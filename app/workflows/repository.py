"""Safe SQLite persistence helpers for workflows, approvals, and auditability."""

import json
from typing import Any

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath, get_connection
from app.database.repository import utc_timestamp


def insert_record(table: str, values: dict[str, Any], database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> None:
    allowed = {"approval_requests", "workflow_executions", "incidents", "notifications", "audit_log"}
    if table not in allowed:
        raise ValueError("Unsupported workflow table")
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))
    finally:
        connection.close()


def get_one(table: str, key: str, value: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    allowed = {"approval_requests": "request_id", "workflow_executions": "workflow_id", "incidents": "incident_id"}
    if allowed.get(table) != key:
        raise ValueError("Unsupported workflow lookup")
    connection = get_connection(database_path)
    try:
        row = connection.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_records(table: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH, *, status: str | None = None, field_id: str | None = None) -> list[dict[str, Any]]:
    allowed = {"approval_requests", "workflow_executions", "incidents", "notifications", "audit_log"}
    if table not in allowed:
        raise ValueError("Unsupported workflow table")
    clauses, parameters = [], []
    if status:
        clauses.append("status = ?"); parameters.append(status)
    if field_id and table != "notifications":
        clauses.append("field_id = ?"); parameters.append(field_id)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    order = "timestamp" if table == "audit_log" else "created_at"
    connection = get_connection(database_path)
    try:
        rows = connection.execute(f"SELECT * FROM {table}{where} ORDER BY {order} DESC, id DESC", parameters).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def update_record(table: str, key: str, value: str, updates: dict[str, Any], database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> None:
    allowed = {"approval_requests": "request_id", "workflow_executions": "workflow_id"}
    if allowed.get(table) != key:
        raise ValueError("Unsupported workflow update")
    assignments = ", ".join(f"{column} = ?" for column in updates)
    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(f"UPDATE {table} SET {assignments} WHERE {key} = ?", (*updates.values(), value))
    finally:
        connection.close()


def find_workflow_by_key(idempotency_key: str, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    connection = get_connection(database_path)
    try:
        row = connection.execute("SELECT * FROM workflow_executions WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def audit(event_type: str, entity_type: str, entity_id: str, field_id: str | None, actor: str, details: dict[str, Any], database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> None:
    insert_record("audit_log", {"timestamp": utc_timestamp(), "event_type": event_type,
        "entity_type": entity_type, "entity_id": entity_id, "field_id": field_id,
        "actor": actor, "details": json.dumps(details, sort_keys=True)}, database_path)
