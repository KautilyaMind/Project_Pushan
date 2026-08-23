"""Data models used throughout Pushan V0.2."""

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


@dataclass(frozen=True)
class SensorReading:
    """A deterministic snapshot of field sensors and operational resources."""

    field_id: str
    soil_moisture: float
    temperature: float
    humidity: float
    rain_probability: float
    pump_status: str
    water_available_litres: float
    sensor_status: str

    def __post_init__(self) -> None:
        """Validate sensor measurements and supported status values."""
        if not isinstance(self.field_id, str) or not self.field_id.strip():
            raise ValueError("field_id must be a non-empty string")

        FarmInput._validate_percentage("soil_moisture", self.soil_moisture)
        FarmInput._validate_number("temperature", self.temperature)
        FarmInput._validate_percentage("humidity", self.humidity)
        FarmInput._validate_percentage("rain_probability", self.rain_probability)
        FarmInput._validate_number("water_available_litres", self.water_available_litres)

        if self.water_available_litres < 0:
            raise ValueError("water_available_litres must be greater than or equal to 0")
        if self.pump_status not in {"ONLINE", "OFFLINE"}:
            raise ValueError("pump_status must be ONLINE or OFFLINE")
        if self.sensor_status not in {"HEALTHY", "FAULTY"}:
            raise ValueError("sensor_status must be HEALTHY or FAULTY")


@dataclass(frozen=True)
class OperationalDecision:
    """The final action after checking whether irrigation can be executed."""

    irrigation_required: bool
    recommended_water_litres: float
    execution_possible: bool
    action_required: str
    reason: str
    risk_level: str
