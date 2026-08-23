"""Unit tests for the Pushan irrigation decision engine."""

import unittest

from app.irrigation_engine import calculate_irrigation
from app.models import FarmInput


def farm_input(**overrides: object) -> FarmInput:
    """Build a valid default input and replace values needed by a test."""
    values: dict[str, object] = {
        "soil_moisture": 20,
        "temperature": 30,
        "humidity": 50,
        "rain_probability": 20,
        "crop": "tomato",
        "crop_stage": "flowering",
        "field_area_m2": 100,
    }
    values.update(overrides)
    return FarmInput(**values)  # type: ignore[arg-type]


class IrrigationEngineTests(unittest.TestCase):
    def test_dry_tomato_field_requires_irrigation(self) -> None:
        recommendation = calculate_irrigation(farm_input())
        self.assertTrue(recommendation.irrigation_required)
        self.assertEqual(recommendation.recommended_water_litres, 500)

    def test_sufficient_soil_moisture_needs_no_irrigation(self) -> None:
        recommendation = calculate_irrigation(farm_input(soil_moisture=35))
        self.assertFalse(recommendation.irrigation_required)
        self.assertEqual(recommendation.recommended_water_litres, 0)

    def test_likely_rain_postpones_irrigation(self) -> None:
        recommendation = calculate_irrigation(farm_input(rain_probability=70))
        self.assertFalse(recommendation.irrigation_required)
        self.assertIn("postponed", recommendation.reason)

    def test_unsupported_crop_has_unknown_risk(self) -> None:
        recommendation = calculate_irrigation(farm_input(crop="wheat"))
        self.assertFalse(recommendation.irrigation_required)
        self.assertEqual(recommendation.risk_level, "UNKNOWN")

    def test_high_temperature_increases_water(self) -> None:
        recommendation = calculate_irrigation(farm_input(temperature=36))
        self.assertEqual(recommendation.recommended_water_litres, 575)

    def test_low_humidity_increases_water(self) -> None:
        recommendation = calculate_irrigation(farm_input(humidity=34))
        self.assertEqual(recommendation.recommended_water_litres, 550)

    def test_high_temperature_and_low_humidity_produce_6325_litres(self) -> None:
        recommendation = calculate_irrigation(
            farm_input(
                soil_moisture=21,
                temperature=37,
                humidity=30,
                field_area_m2=1000,
            )
        )
        self.assertEqual(recommendation.recommended_water_litres, 6325)

    def test_invalid_humidity_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            farm_input(humidity=101)

    def test_invalid_rain_probability_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            farm_input(rain_probability=-1)

    def test_non_positive_field_area_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            farm_input(field_area_m2=0)

    def test_crop_name_is_case_insensitive(self) -> None:
        recommendation = calculate_irrigation(farm_input(crop=" Tomato "))
        self.assertTrue(recommendation.irrigation_required)

    def test_risk_levels_follow_moisture_deficit(self) -> None:
        self.assertEqual(calculate_irrigation(farm_input(soil_moisture=14)).risk_level, "HIGH")
        self.assertEqual(calculate_irrigation(farm_input(soil_moisture=20)).risk_level, "MEDIUM")
        self.assertEqual(calculate_irrigation(farm_input(soil_moisture=25)).risk_level, "LOW")


if __name__ == "__main__":
    unittest.main()
