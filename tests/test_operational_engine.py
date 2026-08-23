"""Unit tests for operational feasibility decisions."""

import unittest

from app.models import IrrigationRecommendation, SensorReading
from app.operational_engine import evaluate_operational_feasibility


def recommendation(
    irrigation_required: bool = True,
    water: float = 5000,
) -> IrrigationRecommendation:
    """Build a recommendation for an operational test."""
    return IrrigationRecommendation(
        irrigation_required=irrigation_required,
        recommended_water_litres=water,
        reason="Test irrigation recommendation.",
        risk_level="MEDIUM",
    )


def sensor_reading(**overrides: object) -> SensorReading:
    """Build a valid operational sensor reading for a test."""
    values: dict[str, object] = {
        "field_id": "TEST_FIELD",
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


class OperationalEngineTests(unittest.TestCase):
    def test_irrigation_not_required_returns_no_action(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(irrigation_required=False, water=0), sensor_reading()
        )
        self.assertFalse(decision.execution_possible)
        self.assertEqual(decision.action_required, "NO_ACTION")

    def test_faulty_sensor_requires_sensor_check(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(), sensor_reading(sensor_status="FAULTY")
        )
        self.assertFalse(decision.execution_possible)
        self.assertEqual(decision.action_required, "CHECK_SENSOR")

    def test_offline_pump_requires_maintenance(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(), sensor_reading(pump_status="OFFLINE")
        )
        self.assertFalse(decision.execution_possible)
        self.assertEqual(decision.action_required, "MAINTENANCE_REQUIRED")

    def test_insufficient_water_requires_refill(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(water=5000), sensor_reading(water_available_litres=3000)
        )
        self.assertFalse(decision.execution_possible)
        self.assertEqual(decision.action_required, "REFILL_WATER")
        self.assertIn("5000 L", decision.reason)
        self.assertIn("3000 L", decision.reason)
        self.assertIn("2000 L", decision.reason)

    def test_operational_field_can_irrigate(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(water=5000), sensor_reading(water_available_litres=5000)
        )
        self.assertTrue(decision.execution_possible)
        self.assertEqual(decision.action_required, "IRRIGATE")

    def test_sensor_problem_takes_priority_over_pump_and_water(self) -> None:
        decision = evaluate_operational_feasibility(
            recommendation(),
            sensor_reading(
                sensor_status="FAULTY",
                pump_status="OFFLINE",
                water_available_litres=0,
            ),
        )
        self.assertEqual(decision.action_required, "CHECK_SENSOR")


if __name__ == "__main__":
    unittest.main()
