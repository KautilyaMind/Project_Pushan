"""API tests for the Pushan V0.5 FastAPI service layer."""

from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.main_api import create_app
from app.ml.data_generator import generate_training_data
from app.ml.train import train_and_evaluate_models


RECOMMENDATION_PAYLOAD = {
    "field_id": "FIELD_001",
    "crop": "tomato",
    "crop_stage": "flowering",
    "field_area_m2": 1000,
}
PREDICTION_PAYLOAD = {
    "soil_moisture": 20,
    "temperature": 34,
    "humidity": 40,
    "rain_probability": 15,
    "crop": "tomato",
    "crop_stage": "flowering",
    "field_area_m2": 1000,
}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        temporary_path = Path(cls.temporary_directory.name)
        cls.database_path = temporary_path / "api_test.db"
        cls.model_path = temporary_path / "api_test_model.joblib"
        training_data = generate_training_data(250, random_seed=42)
        train_and_evaluate_models(
            training_data,
            cls.model_path,
            n_estimators=20,
        )
        cls.client_context = TestClient(
            create_app(cls.database_path, cls.model_path)
        )
        cls.client = cls.client_context.__enter__()
        cls.initial_assessment = cls.client.post(
            "/irrigation/recommend",
            json=RECOMMENDATION_PAYLOAD,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        cls.temporary_directory.cleanup()

    def test_health_returns_200(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_health_returns_current_version(self) -> None:
        response = self.client.get("/health").json()
        self.assertEqual(response["version"], "0.9")

    def test_fields_returns_known_fields(self) -> None:
        response = self.client.get("/fields")
        self.assertEqual(response.status_code, 200)
        field_ids = {field["field_id"] for field in response.json()}
        self.assertEqual(field_ids, {"FIELD_001", "FIELD_002", "FIELD_003"})

    def test_known_sensor_endpoint_returns_reading(self) -> None:
        response = self.client.get("/fields/FIELD_001/sensor")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["soil_moisture"], 18)

    def test_unknown_sensor_endpoint_returns_404(self) -> None:
        response = self.client.get("/fields/FIELD_999/sensor")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown field ID", response.json()["detail"])

    def test_valid_recommendation_returns_200(self) -> None:
        self.assertEqual(self.initial_assessment.status_code, 200)

    def test_recommendation_contains_rule_result(self) -> None:
        rule_result = self.initial_assessment.json()["rule_based"]
        self.assertTrue(rule_result["irrigation_required"])
        self.assertEqual(rule_result["recommended_water_litres"], 6325)

    def test_recommendation_contains_ml_prediction(self) -> None:
        ml_result = self.initial_assessment.json()["ml"]
        self.assertGreaterEqual(ml_result["predicted_water_litres"], 0)
        self.assertEqual(ml_result["model_version"], "v0.4")

    def test_recommendation_contains_operational_decision(self) -> None:
        operational = self.initial_assessment.json()["operational"]
        self.assertFalse(operational["execution_possible"])
        self.assertEqual(operational["action_required"], "MAINTENANCE_REQUIRED")

    def test_invalid_field_area_returns_422(self) -> None:
        payload = {**RECOMMENDATION_PAYLOAD, "field_area_m2": 0}
        self.assertEqual(
            self.client.post("/irrigation/recommend", json=payload).status_code,
            422,
        )

    def test_invalid_humidity_returns_422(self) -> None:
        payload = {**PREDICTION_PAYLOAD, "humidity": 101}
        self.assertEqual(self.client.post("/ml/predict", json=payload).status_code, 422)

    def test_sensor_history_returns_a_list(self) -> None:
        response = self.client.get("/fields/FIELD_001/history/sensors")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_decision_history_returns_a_list(self) -> None:
        response = self.client.get("/fields/FIELD_001/history/decisions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_action_history_returns_a_list(self) -> None:
        response = self.client.get("/fields/FIELD_001/history/actions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_history_limit_is_respected(self) -> None:
        self.client.post("/irrigation/recommend", json=RECOMMENDATION_PAYLOAD)
        response = self.client.get("/fields/FIELD_001/history/sensors?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_ml_predict_returns_non_negative_number(self) -> None:
        response = self.client.post("/ml/predict", json=PREDICTION_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        prediction = response.json()["predicted_water_litres"]
        self.assertIsInstance(prediction, (int, float))
        self.assertGreaterEqual(prediction, 0)

    def test_missing_model_returns_controlled_503(self) -> None:
        missing_path = Path(self.temporary_directory.name) / "missing.joblib"
        other_database = Path(self.temporary_directory.name) / "missing_model.db"
        with TestClient(create_app(other_database, missing_path)) as client:
            response = client.post("/ml/predict", json=PREDICTION_PAYLOAD)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "ML model is unavailable. Run 'python -m app.ml.train' first.",
        )

    def test_swagger_and_openapi_are_available(self) -> None:
        self.assertEqual(self.client.get("/docs").status_code, 200)
        openapi_response = self.client.get("/openapi.json")
        self.assertEqual(openapi_response.status_code, 200)
        self.assertEqual(openapi_response.json()["info"]["version"], "0.9")


if __name__ == "__main__":
    unittest.main()
