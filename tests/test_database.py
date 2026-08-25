"""Unit tests for Pushan's SQLite persistence layer."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.database.db import initialize_database
from app.database.repository import (
    get_action_history,
    get_decision_history,
    get_sensor_history,
    save_field,
    save_irrigation_decision,
    save_operational_decision,
    save_sensor_reading,
)
from app.models import IrrigationRecommendation, OperationalDecision, SensorReading


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test_pushan.db"
        initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def save_test_field(self, field_id: str = "FIELD_001") -> None:
        save_field(field_id, "tomato", "flowering", 1000, self.database_path)

    def test_initialization_creates_required_tables(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        table_names = {row[0] for row in rows}
        self.assertTrue(
            {"fields", "sensor_readings", "irrigation_decisions", "operational_actions"}
            <= table_names
        )

    def test_field_can_be_saved(self) -> None:
        self.save_test_field()
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT crop, field_area_m2 FROM fields WHERE field_id = ?",
                ("FIELD_001",),
            ).fetchone()
        self.assertEqual(row, ("tomato", 1000.0))

    def test_duplicate_field_does_not_corrupt_data(self) -> None:
        self.save_test_field()
        save_field("FIELD_001", "rice", "seedling", 50, self.database_path)
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT crop, field_area_m2 FROM fields WHERE field_id = ?",
                ("FIELD_001",),
            ).fetchone()
        self.assertEqual(row, ("tomato", 1000.0))

    def test_sensor_reading_can_be_stored(self) -> None:
        self.save_test_field()
        record_id = save_sensor_reading(sensor_reading(), self.database_path)
        self.assertGreater(record_id, 0)
        self.assertEqual(len(get_sensor_history("FIELD_001", database_path=self.database_path)), 1)

    def test_irrigation_recommendation_can_be_stored(self) -> None:
        self.save_test_field()
        record_id = save_irrigation_decision(
            "FIELD_001", recommendation(), self.database_path
        )
        self.assertGreater(record_id, 0)
        history = get_decision_history("FIELD_001", database_path=self.database_path)
        self.assertEqual(history[0]["risk_level"], "MEDIUM")

    def test_operational_decision_can_be_stored(self) -> None:
        self.save_test_field()
        record_id = save_operational_decision(
            "FIELD_001", operational_decision(), self.database_path
        )
        self.assertGreater(record_id, 0)
        history = get_action_history("FIELD_001", database_path=self.database_path)
        self.assertEqual(history[0]["action_required"], "IRRIGATE")

    def test_sensor_history_can_be_retrieved_by_field(self) -> None:
        self.save_test_field()
        save_sensor_reading(sensor_reading(), self.database_path)
        self.assertEqual(get_sensor_history("FIELD_001", database_path=self.database_path)[0]["field_id"], "FIELD_001")

    def test_decision_history_can_be_retrieved_by_field(self) -> None:
        self.save_test_field()
        save_irrigation_decision("FIELD_001", recommendation(), self.database_path)
        self.assertEqual(len(get_decision_history("FIELD_001", database_path=self.database_path)), 1)

    def test_action_history_can_be_retrieved_by_field(self) -> None:
        self.save_test_field()
        save_operational_decision("FIELD_001", operational_decision(), self.database_path)
        self.assertEqual(len(get_action_history("FIELD_001", database_path=self.database_path)), 1)

    def test_history_limit_is_respected(self) -> None:
        self.save_test_field()
        for moisture in (10, 20, 30):
            save_sensor_reading(
                sensor_reading(soil_moisture=moisture), self.database_path
            )
        history = get_sensor_history("FIELD_001", limit=2, database_path=self.database_path)
        self.assertEqual(len(history), 2)

    def test_newest_records_are_returned_first(self) -> None:
        self.save_test_field()
        save_sensor_reading(
            sensor_reading(soil_moisture=10),
            self.database_path,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        save_sensor_reading(
            sensor_reading(soil_moisture=30),
            self.database_path,
            timestamp="2026-01-02T00:00:00+00:00",
        )
        history = get_sensor_history("FIELD_001", database_path=self.database_path)
        self.assertEqual([row["soil_moisture"] for row in history], [30.0, 10.0])

    def test_histories_do_not_mix_fields(self) -> None:
        self.save_test_field("FIELD_001")
        self.save_test_field("FIELD_002")
        save_sensor_reading(sensor_reading(field_id="FIELD_001"), self.database_path)
        save_sensor_reading(sensor_reading(field_id="FIELD_002"), self.database_path)
        history = get_sensor_history("FIELD_001", database_path=self.database_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["field_id"], "FIELD_001")


def sensor_reading(**overrides: object) -> SensorReading:
    """Build a valid sensor reading for persistence tests."""
    values: dict[str, object] = {
        "field_id": "FIELD_001",
        "soil_moisture": 20,
        "temperature": 30,
        "humidity": 50,
        "rain_probability": 10,
        "pump_status": "ONLINE",
        "water_available_litres": 10000,
        "sensor_status": "HEALTHY",
    }
    values.update(overrides)
    return SensorReading(**values)  # type: ignore[arg-type]


def recommendation() -> IrrigationRecommendation:
    """Build a valid irrigation recommendation for persistence tests."""
    return IrrigationRecommendation(True, 5000, "Dry soil.", "MEDIUM")


def operational_decision() -> OperationalDecision:
    """Build a valid operational decision for persistence tests."""
    return OperationalDecision(True, 5000, True, "IRRIGATE", "Ready.", "MEDIUM")


if __name__ == "__main__":
    unittest.main()
