"""Unit tests for the Pushan V0.4 machine-learning pipeline."""

from numbers import Real
from pathlib import Path
import tempfile
import unittest

import joblib

from app.irrigation_engine import calculate_irrigation
from app.ml.data_generator import REQUIRED_COLUMNS, generate_training_data
from app.ml.predict import predict_water_requirement
from app.ml.train import FEATURES, train_and_evaluate_models
from app.models import FarmInput, SensorReading
from app.operational_engine import evaluate_operational_feasibility


class MachineLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.model_path = Path(cls.temporary_directory.name) / "test_model.joblib"
        cls.training_data = generate_training_data(250, random_seed=42)
        cls.results = train_and_evaluate_models(
            cls.training_data,
            cls.model_path,
            n_estimators=25,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    def test_generator_returns_requested_number_of_rows(self) -> None:
        self.assertEqual(len(generate_training_data(25)), 25)

    def test_generated_dataset_has_required_columns(self) -> None:
        self.assertEqual(list(self.training_data.columns), REQUIRED_COLUMNS)

    def test_generated_values_remain_in_expected_ranges(self) -> None:
        self.assertTrue(self.training_data["soil_moisture"].between(5, 60).all())
        self.assertTrue(self.training_data["temperature"].between(15, 45).all())
        self.assertTrue(self.training_data["humidity"].between(20, 95).all())
        self.assertTrue(self.training_data["rain_probability"].between(0, 100).all())
        self.assertTrue(self.training_data["field_area_m2"].between(100, 5000).all())
        self.assertTrue((self.training_data["recommended_water_litres"] >= 0).all())

    def test_generation_is_reproducible(self) -> None:
        first = generate_training_data(20, random_seed=7)
        second = generate_training_data(20, random_seed=7)
        self.assertTrue(first.equals(second))

    def test_model_training_completes(self) -> None:
        self.assertIn(self.results["selected_model"], {"Linear Regression", "Random Forest"})
        self.assertIn("Linear Regression", self.results["metrics"])
        self.assertIn("Random Forest", self.results["metrics"])

    def test_saved_model_can_be_loaded(self) -> None:
        loaded_model = joblib.load(self.model_path)
        self.assertTrue(hasattr(loaded_model, "predict"))

    def test_prediction_returns_a_number(self) -> None:
        prediction = predict_water_requirement(farm_input(), self.model_path)
        self.assertIsInstance(prediction, Real)

    def test_prediction_is_non_negative(self) -> None:
        prediction = predict_water_requirement(farm_input(), self.model_path)
        self.assertGreaterEqual(prediction, 0)

    def test_prediction_handles_known_crops(self) -> None:
        for crop in ("tomato", "rice", "cotton"):
            with self.subTest(crop=crop):
                self.assertGreaterEqual(
                    predict_water_requirement(farm_input(crop=crop), self.model_path),
                    0,
                )

    def test_prediction_handles_known_crop_stages(self) -> None:
        for stage in ("seedling", "vegetative", "flowering", "maturity"):
            with self.subTest(stage=stage):
                self.assertGreaterEqual(
                    predict_water_requirement(
                        farm_input(crop_stage=stage), self.model_path
                    ),
                    0,
                )

    def test_preprocessing_accepts_valid_farm_input(self) -> None:
        loaded_model = joblib.load(self.model_path)
        self.assertEqual(len(loaded_model.feature_names_in_), len(FEATURES))
        predict_water_requirement(farm_input(), self.model_path)

    def test_rule_based_engine_remains_unchanged(self) -> None:
        recommendation = calculate_irrigation(farm_input())
        self.assertTrue(recommendation.irrigation_required)
        self.assertEqual(recommendation.recommended_water_litres, 6325)

    def test_operational_engine_still_controls_execution(self) -> None:
        recommendation = calculate_irrigation(farm_input())
        reading = sensor_reading(pump_status="OFFLINE")
        decision = evaluate_operational_feasibility(recommendation, reading)
        self.assertFalse(decision.execution_possible)
        self.assertEqual(decision.action_required, "MAINTENANCE_REQUIRED")


def farm_input(**overrides: object) -> FarmInput:
    """Build the FIELD_001 farm input with optional test changes."""
    values: dict[str, object] = {
        "soil_moisture": 18,
        "temperature": 36,
        "humidity": 32,
        "rain_probability": 10,
        "crop": "tomato",
        "crop_stage": "flowering",
        "field_area_m2": 1000,
    }
    values.update(overrides)
    return FarmInput(**values)  # type: ignore[arg-type]


def sensor_reading(**overrides: object) -> SensorReading:
    """Build a healthy FIELD_001-like reading with optional changes."""
    values: dict[str, object] = {
        "field_id": "FIELD_001",
        "soil_moisture": 18,
        "temperature": 36,
        "humidity": 32,
        "rain_probability": 10,
        "pump_status": "ONLINE",
        "water_available_litres": 10000,
        "sensor_status": "HEALTHY",
    }
    values.update(overrides)
    return SensorReading(**values)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
