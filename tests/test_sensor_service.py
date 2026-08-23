"""Unit tests for simulated sensor acquisition and conversion."""

import unittest

from app.models import SensorReading
from app.services.sensor_service import build_farm_input, get_latest_reading


def make_sensor_reading(**overrides: object) -> SensorReading:
    """Build a valid sensor reading with selected values replaced."""
    values: dict[str, object] = {
        "field_id": "TEST_FIELD",
        "soil_moisture": 20,
        "temperature": 30,
        "humidity": 50,
        "rain_probability": 10,
        "pump_status": "ONLINE",
        "water_available_litres": 1000,
        "sensor_status": "HEALTHY",
    }
    values.update(overrides)
    return SensorReading(**values)  # type: ignore[arg-type]


class SensorServiceTests(unittest.TestCase):
    def test_field_001_returns_expected_reading(self) -> None:
        reading = get_latest_reading("FIELD_001")
        self.assertEqual(reading.field_id, "FIELD_001")
        self.assertEqual(reading.soil_moisture, 18)
        self.assertEqual(reading.temperature, 36)
        self.assertEqual(reading.humidity, 32)
        self.assertEqual(reading.rain_probability, 10)
        self.assertEqual(reading.pump_status, "OFFLINE")
        self.assertEqual(reading.water_available_litres, 10000)
        self.assertEqual(reading.sensor_status, "HEALTHY")

    def test_unknown_field_id_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown field ID"):
            get_latest_reading("FIELD_999")

    def test_invalid_humidity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_sensor_reading(humidity=101)

    def test_negative_water_availability_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_sensor_reading(water_available_litres=-1)

    def test_sensor_reading_converts_to_farm_input(self) -> None:
        reading = get_latest_reading("FIELD_001")
        farm_input = build_farm_input(reading, "tomato", "flowering", 1000)
        self.assertEqual(farm_input.soil_moisture, reading.soil_moisture)
        self.assertEqual(farm_input.crop, "tomato")
        self.assertEqual(farm_input.field_area_m2, 1000)


if __name__ == "__main__":
    unittest.main()
