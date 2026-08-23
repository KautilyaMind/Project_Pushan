"""Core package for Pushan V0.1."""

from .irrigation_engine import CROP_REQUIREMENTS, calculate_irrigation
from .models import FarmInput, IrrigationRecommendation

__all__ = [
    "CROP_REQUIREMENTS",
    "FarmInput",
    "IrrigationRecommendation",
    "calculate_irrigation",
]
