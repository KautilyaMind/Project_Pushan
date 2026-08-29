"""Local notification recording with optional future-automation webhook."""

import os
import uuid

import httpx

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath
from app.database.repository import utc_timestamp
from .config import WEBHOOK_TIMEOUT_SECONDS
from .repository import audit, insert_record


def send_notification(recipient: str, subject: str, message: str, workflow_id: str,
                      payload: dict, database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> dict:
    webhook = os.getenv("PUSHAN_AUTOMATION_WEBHOOK_URL", "").strip()
    status = "SIMULATED"
    if webhook:
        try:
            httpx.post(webhook, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS).raise_for_status()
            status = "DELIVERED"
        except (httpx.HTTPError, ValueError):
            status = "FAILED"
    record = {"notification_id": f"NOT-{uuid.uuid4().hex[:12].upper()}",
              "created_at": utc_timestamp(), "recipient": recipient, "subject": subject,
              "message": message, "delivery_status": status, "workflow_id": workflow_id}
    insert_record("notifications", record, database_path)
    audit("ALERT_SENT", "WORKFLOW", workflow_id, payload.get("field_id"), "SYSTEM",
          {"delivery_status": status}, database_path)
    return record
