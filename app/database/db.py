"""Database connection and schema initialization for Pushan V0.3."""

from pathlib import Path
import sqlite3


DEFAULT_DATABASE_PATH = Path("data") / "pushan.db"
DatabasePath = str | Path


def get_connection(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key checks enabled."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: DatabasePath = DEFAULT_DATABASE_PATH) -> None:
    """Create all Pushan tables when they do not already exist."""
    connection = get_connection(database_path)
    try:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS fields (
                    field_id TEXT PRIMARY KEY,
                    crop TEXT NOT NULL,
                    crop_stage TEXT NOT NULL,
                    field_area_m2 REAL NOT NULL CHECK (field_area_m2 > 0),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    irrigation_required INTEGER NOT NULL,
                    recommended_water_litres REAL NOT NULL,
                    reason TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    FOREIGN KEY (field_id) REFERENCES fields(field_id)
                );

                CREATE TABLE IF NOT EXISTS operational_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                """
            )
    finally:
        connection.close()
