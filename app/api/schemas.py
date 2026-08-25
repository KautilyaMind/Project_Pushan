"""Validated request and stable response schemas for the Pushan API."""

from pydantic import BaseModel, Field


class FarmRecommendationRequest(BaseModel):
    """Field metadata needed to assess a configured field's current reading."""

    field_id: str = Field(min_length=1)
    crop: str = Field(min_length=1)
    crop_stage: str = Field(min_length=1)
    field_area_m2: float = Field(gt=0)


class DirectPredictionRequest(BaseModel):
    """Direct farm conditions accepted by the advisory ML endpoint."""

    soil_moisture: float = Field(ge=0, le=100)
    temperature: float
    humidity: float = Field(ge=0, le=100)
    rain_probability: float = Field(ge=0, le=100)
    crop: str = Field(min_length=1)
    crop_stage: str = Field(min_length=1)
    field_area_m2: float = Field(gt=0)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class FieldResponse(BaseModel):
    field_id: str
    crop: str
    crop_stage: str
    field_area_m2: float


class SensorResponse(BaseModel):
    field_id: str
    soil_moisture: float
    temperature: float
    humidity: float
    rain_probability: float
    pump_status: str
    water_available_litres: float
    sensor_status: str


class RuleBasedResponse(BaseModel):
    irrigation_required: bool
    recommended_water_litres: float
    risk_level: str
    reason: str


class MLPredictionResponse(BaseModel):
    predicted_water_litres: float
    model_version: str = "v0.4"


class ComparisonResponse(BaseModel):
    absolute_difference_litres: float
    difference_percentage: float


class OperationalResponse(BaseModel):
    execution_possible: bool
    action_required: str
    reason: str


class IrrigationAssessmentResponse(BaseModel):
    field_id: str
    sensor: SensorResponse
    rule_based: RuleBasedResponse
    ml: MLPredictionResponse
    comparison: ComparisonResponse
    operational: OperationalResponse
