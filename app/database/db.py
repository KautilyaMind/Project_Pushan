"""SQLite/PostgreSQL connection and schema initialization for Pushan."""

from pathlib import Path
import sqlite3
from typing import Any


DEFAULT_DATABASE_PATH = Path("data") / "pushan.db"
DatabasePath = str | Path
CURRENT_SCHEMA_VERSION = 1


def is_postgres(database_path: DatabasePath) -> bool:
    """Return whether the configured target is a PostgreSQL connection URL."""
    return str(database_path).startswith(("postgres://", "postgresql://"))


def get_connection(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> Any:
    """Open a PostgreSQL connection URL or a local SQLite database."""
    if is_postgres(database_path):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError(
                "PostgreSQL requires the 'psycopg[binary]' package."
            ) from error
        return psycopg.connect(str(database_path), row_factory=dict_row)

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def execute(connection: Any, sql: str, parameters: tuple[Any, ...] | list[Any] = ()) -> Any:
    """Execute portable parameterized SQL on SQLite or PostgreSQL."""
    if connection.__class__.__module__.startswith("psycopg"):
        sql = sql.replace("?", "%s")
    return connection.execute(sql, parameters)


def initialize_database(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> None:
    """Create all Pushan tables when they do not already exist."""
    connection = get_connection(database_path)
    try:
        with connection:
            schema = """
                CREATE TABLE IF NOT EXISTS fields (
                    field_id TEXT PRIMARY KEY,
                    crop TEXT NOT NULL,
                    crop_stage TEXT NOT NULL,
                    field_area_m2 REAL NOT NULL CHECK (field_area_m2 > 0),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id {identity},
                    field_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    soil_moisture REAL NOT NULL,
                    temperature REAL NOT NULL,
                    humidity REAL NOT NULL,
                    rain_probability REAL NOT NULL,
                    pump_status TEXT NOT NULL,
                    water_available_litres REAL NOT NULL,
                    sensor_status TEXT NOT NULL,
                    FOREIGN KEY (field_id) REFERENCES fields(field_id)
                );

                CREATE TABLE IF NOT EXISTS irrigation_decisions (
                    id {identity},
                    field_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    irrigation_required INTEGER NOT NULL,
                    recommended_water_litres REAL NOT NULL,
                    reason TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    FOREIGN KEY (field_id) REFERENCES fields(field_id)
                );

                CREATE TABLE IF NOT EXISTS operational_actions (
                    id {identity},
                    field_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    irrigation_required INTEGER NOT NULL,
                    recommended_water_litres REAL NOT NULL,
                    execution_possible INTEGER NOT NULL,
                    action_required TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    FOREIGN KEY (field_id) REFERENCES fields(field_id)
                );

                CREATE TABLE IF NOT EXISTS approval_requests (
                    id {identity},
                    request_id TEXT NOT NULL UNIQUE,
                    field_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    recommended_water_litres REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    rejected_at TEXT,
                    decision_note TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id {identity},
                    workflow_id TEXT NOT NULL UNIQUE,
                    field_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approval_request_id TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    failure_reason TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS incidents (
                    id {identity},
                    incident_id TEXT NOT NULL UNIQUE,
                    field_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source_workflow_id TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id {identity},
                    notification_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    delivery_status TEXT NOT NULL,
                    workflow_id TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id {identity},
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    field_id TEXT,
                    actor TEXT NOT NULL,
                    details TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """.format(
                identity=(
                    "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"
                    if is_postgres(database_path)
                    else "INTEGER PRIMARY KEY AUTOINCREMENT"
                )
            )
            if is_postgres(database_path):
                for statement in schema.split(";"):
                    if statement.strip():
                        connection.execute(statement)
            else:
                connection.executescript(schema)
            version_insert = (
                "INSERT INTO schema_version (version) VALUES (?) ON CONFLICT (version) DO NOTHING"
                if is_postgres(database_path)
                else "INSERT OR IGNORE INTO schema_version (version) VALUES (?)"
            )
            execute(
                connection,
                version_insert,
                (CURRENT_SCHEMA_VERSION,),
            )
    finally:
        connection.close()


def get_schema_version(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> int:
    """Return the latest safely applied schema version."""
    initialize_database(database_path)
    with get_connection(database_path) as connection:
        row = execute(connection, "SELECT MAX(version) AS version FROM schema_version").fetchone()
    return int(row["version"])
