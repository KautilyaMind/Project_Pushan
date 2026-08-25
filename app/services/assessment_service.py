"""Orchestrate one complete Pushan irrigation assessment."""

from dataclasses import dataclass
import logging
from pathlib import Path

from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath, initialize_database
from app.database.repository import (
    save_field,
    save_irrigation_decision,
    save_operational_decision,
    save_sensor_reading,
)
from app.irrigation_engine import calculate_irrigation
from app.ml.predict import predict_water_requirement
from app.ml.train import DEFAULT_MODEL_PATH
from app.models import (
    IrrigationRecommendation,
    OperationalDecision,
    SensorReading,
)
from app.operational_engine import evaluate_operational_feasibility
from app.services.sensor_service import build_farm_input, get_latest_reading


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IrrigationAssessment:
    """Combined result returned by the API-facing orchestration service."""

    field_id: str
    sensor_reading: SensorReading
    recommendation: IrrigationRecommendation
    ml_predicted_water_litres: float
    absolute_difference_litres: float
    difference_percentage: float
    operational_decision: OperationalDecision


def build_irrigation_assessment(
    *,
    field_id: str,
    crop: str,
    crop_stage: str,
    field_area_m2: float,
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> IrrigationAssessment:
    """Run existing Pushan components, persist results, and combine their output."""
    logger.info("assessment started for %s", field_id)
    initialize_database(database_path)

    sensor_reading = get_latest_reading(field_id)
    save_field(field_id, crop, crop_stage, field_area_m2, database_path)
    save_sensor_reading(sensor_reading, database_path)

    farm_input = build_farm_input(
        reading=sensor_reading,
        crop=crop,
        crop_stage=crop_stage,
        field_area_m2=field_area_m2,
    )
    recommendation = calculate_irrigation(farm_input)
    save_irrigation_decision(field_id, recommendation, database_path)

    ml_prediction = predict_water_requirement(farm_input, model_path)
    logger.info("ML prediction completed for %s", field_id)
    difference = abs(recommendation.recommended_water_litres - ml_prediction)
    if recommendation.recommended_water_litres > 0:
        difference_percentage = (
            difference / recommendation.recommended_water_litres * 100
        )
    else:
        difference_percentage = 0.0

    operational_decision = evaluate_operational_feasibility(
        recommendation,
        sensor_reading,
    )
    save_operational_decision(field_id, operational_decision, database_path)
    logger.info("decision persisted for %s", field_id)
    if not operational_decision.execution_possible:
        logger.info(
            "operational action blocked for %s: %s",
            field_id,
            operational_decision.action_required,
        )

    return IrrigationAssessment(
        field_id=field_id,
        sensor_reading=sensor_reading,
        recommendation=recommendation,
        ml_predicted_water_litres=ml_prediction,
        absolute_difference_litres=round(difference, 2),
        difference_percentage=round(difference_percentage, 2),
        operational_decision=operational_decision,
    )
