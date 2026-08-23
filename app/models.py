"""Data models used by the Pushan irrigation engine."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FarmInput:
    """Measurements and farm details needed for an irrigation decision."""

    soil_moisture: float
    temperature: float
    humidity: float
    rain_probability: float
    crop: str
    crop_stage: str
    field_area_m2: float

    def __post_init__(self) -> None:
        """Reject values that cannot produce a meaningful recommendation."""
        self._validate_percentage("soil_moisture", self.soil_moisture)
        self._validate_number("temperature", self.temperature)
        self._validate_percentage("humidity", self.humidity)
        self._validate_percentage("rain_probability", self.rain_probability)
        self._validate_number("field_area_m2", self.field_area_m2)

        if self.field_area_m2 <= 0:
            raise ValueError("field_area_m2 must be greater than 0")
        if not isinstance(self.crop, str) or not self.crop.strip():
            raise ValueError("crop must be a non-empty string")
        if not isinstance(self.crop_stage, str) or not self.crop_stage.strip():
            raise ValueError("crop_stage must be a non-empty string")

    @staticmethod
    def _validate_number(field_name: str, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite number")

    @classmethod
    def _validate_percentage(cls, field_name: str, value: float) -> None:
        cls._validate_number(field_name, value)
        if not 0 <= value <= 100:
            raise ValueError(f"{field_name} must be between 0 and 100")


@dataclass(frozen=True)
class IrrigationRecommendation:
    """The irrigation decision returned by the rule-based engine."""

    irrigation_required: bool
    recommended_water_litres: float
    reason: str
    risk_level: str
