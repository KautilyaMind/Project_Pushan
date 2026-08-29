"""Pushan AI process-intelligence platform."""

__version__ = "1.0.0"

from .irrigation_engine import CROP_REQUIREMENTS, calculate_irrigation
from .models import (
    FarmInput,
    IrrigationRecommendation,
    OperationalDecision,
    SensorReading,
)
from .operational_engine import evaluate_operational_feasibility

__all__ = [
    "CROP_REQUIREMENTS",
    "FarmInput",
    "IrrigationRecommendation",
    "OperationalDecision",
    "SensorReading",
    "calculate_irrigation",
    "evaluate_operational_feasibility",
]
