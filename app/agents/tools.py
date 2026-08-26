"""Thin wrappers exposing existing Pushan capabilities to graph nodes."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.irrigation_engine import calculate_irrigation
from app.ml.predict import predict_water_requirement
from app.models import FarmInput, IrrigationRecommendation, SensorReading
from app.operational_engine import evaluate_operational_feasibility
from app.rag.qa_service import answer_question
from app.services.sensor_service import (
    FIELD_CONFIGURATIONS,
    build_farm_input,
    get_latest_reading,
)


def get_field_sensor_data(field_id: str) -> dict[str, Any]:
    return asdict(get_latest_reading(field_id))


def build_field_input(field_id: str, sensor: dict[str, Any]) -> dict[str, Any]:
    configuration = FIELD_CONFIGURATIONS[field_id]
    reading = SensorReading(**sensor)
    return asdict(build_farm_input(reading, **configuration))


def get_rule_recommendation(farm_input: dict[str, Any]) -> dict[str, Any]:
    return asdict(calculate_irrigation(FarmInput(**farm_input)))


def get_ml_prediction(farm_input: dict[str, Any], model_path: str | Path) -> float:
    return predict_water_requirement(FarmInput(**farm_input), model_path)


def get_operational_decision(
    recommendation: dict[str, Any], sensor: dict[str, Any]
) -> dict[str, Any]:
    return asdict(
        evaluate_operational_feasibility(
            IrrigationRecommendation(**recommendation), SensorReading(**sensor)
        )
    )


def search_agriculture_knowledge(
    question: str, vector_store_path: str | Path
) -> tuple[str, list[str]]:
    result = answer_question(question, persist_path=vector_store_path)
    return result.answer, result.sources
