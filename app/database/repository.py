"""Save and retrieve Pushan records without exposing SQL to business logic."""

from datetime import datetime, timezone
from typing import Any

from app.models import IrrigationRecommendation, OperationalDecision, SensorReading

from .db import DEFAULT_DATABASE_PATH, DatabasePath, get_connection


HISTORY_QUERIES = {
    "sensor_readings": (
        "SELECT * FROM sensor_readings WHERE field_id = ? "
        "ORDER BY timestamp DESC, id DESC LIMIT ?"
    ),
    "irrigation_decisions": (
        "SELECT * FROM irrigation_decisions WHERE field_id = ? "
        "ORDER BY timestamp DESC, id DESC LIMIT ?"
    ),
    "operational_actions": (
        "SELECT * FROM operational_actions WHERE field_id = ? "
        "ORDER BY timestamp DESC, id DESC LIMIT ?"
    ),
}


def utc_timestamp() -> str:
    """Return the current time as a timezone-aware ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def save_field(
    field_id: str,
    crop: str,
    crop_stage: str,
    field_area_m2: float,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    timestamp: str | None = None,
) -> None:
    """Store field metadata, leaving an existing field unchanged."""
    if not field_id.strip():
        raise ValueError("field_id must be a non-empty string")
    if field_area_m2 <= 0:
        raise ValueError("field_area_m2 must be greater than 0")

    connection = get_connection(database_path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO fields (field_id, crop, crop_stage, field_area_m2, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(field_id) DO NOTHING
                """,
                (field_id, crop, crop_stage, field_area_m2, timestamp or utc_timestamp()),
            )
    finally:
        connection.close()


def save_sensor_reading(
    reading: SensorReading,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    timestamp: str | None = None,
) -> int:
    """Store one sensor reading and return its database ID."""
    values = (
        reading.field_id,
        timestamp or utc_timestamp(),
        reading.soil_moisture,
        reading.temperature,
        reading.humidity,
        reading.rain_probability,
        reading.pump_status,
        reading.water_available_litres,
        reading.sensor_status,
    )
    return _insert_and_return_id(
        """
        INSERT INTO sensor_readings (
            field_id, timestamp, soil_moisture, temperature, humidity,
            rain_probability, pump_status, water_available_litres, sensor_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
        database_path,
    )


def save_irrigation_decision(
    field_id: str,
    recommendation: IrrigationRecommendation,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    timestamp: str | None = None,
) -> int:
    """Store an irrigation recommendation and return its database ID."""
    values = (
        field_id,
        timestamp or utc_timestamp(),
        int(recommendation.irrigation_required),
        recommendation.recommended_water_litres,
        recommendation.reason,
        recommendation.risk_level,
    )
    return _insert_and_return_id(
        """
        INSERT INTO irrigation_decisions (
            field_id, timestamp, irrigation_required,
            recommended_water_litres, reason, risk_level
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        values,
        database_path,
    )


def save_operational_decision(
    field_id: str,
    decision: OperationalDecision,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    timestamp: str | None = None,
) -> int:
    """Store a final operational decision and return its database ID."""
    values = (
        field_id,
        timestamp or utc_timestamp(),
        int(decision.irrigation_required),
        decision.recommended_water_litres,
        int(decision.execution_possible),
        decision.action_required,
        decision.reason,
        decision.risk_level,
    )
    return _insert_and_return_id(
        """
        INSERT INTO operational_actions (
            field_id, timestamp, irrigation_required, recommended_water_litres,
            execution_possible, action_required, reason, risk_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
        database_path,
    )


def get_sensor_history(
    field_id: str,
    limit: int = 10,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return newest sensor readings first for one field."""
    return _get_history("sensor_readings", field_id, limit, database_path)


def get_decision_history(
    field_id: str,
    limit: int = 10,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return newest irrigation recommendations first for one field."""
    return _get_history("irrigation_decisions", field_id, limit, database_path)


def get_action_history(
    field_id: str,
    limit: int = 10,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return newest operational actions first for one field."""
    return _get_history("operational_actions", field_id, limit, database_path)


def _insert_and_return_id(
    sql: str,
    values: tuple[Any, ...],
    database_path: DatabasePath,
) -> int:
    """Execute one parameterized insert and return its generated ID."""
    connection = get_connection(database_path)
    try:
        with connection:
            cursor = connection.execute(sql, values)
            if cursor.lastrowid is None:
                raise RuntimeError("Database insert did not create a record ID")
            return cursor.lastrowid
    finally:
        connection.close()


def _get_history(
    table_name: str,
    field_id: str,
    limit: int,
    database_path: DatabasePath,
) -> list[dict[str, Any]]:
    """Read history from a known table using safe value parameters."""
    query = HISTORY_QUERIES.get(table_name)
    if query is None:
        raise ValueError("Unsupported history table")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    connection = get_connection(database_path)
    try:
        rows = connection.execute(query, (field_id, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
