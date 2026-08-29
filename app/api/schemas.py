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


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


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


class KnowledgeQuestionRequest(BaseModel):
    """A non-blank agriculture question for the grounded knowledge service."""

    question: str = Field(min_length=1, max_length=1000, pattern=r".*\S.*")


class KnowledgeAnswerResponse(BaseModel):
    answer: str
    sources: list[str]


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, pattern=r".*\S.*")
    field_id: str | None = Field(default=None, min_length=1)


class AgentRunResponse(BaseModel):
    intent: str
    answer: str
    execution_trace: list[str]
    sources: list[str]
    errors: list[str]
    structured_results: dict
    workflow_id: str | None = None
    workflow_status: str | None = None
    approval_request_id: str | None = None
    approval_required: bool = False
    technically_executable: bool | None = None
    authorized_to_execute: bool | None = None


class ApprovalDecisionRequest(BaseModel):
    approved_by: str | None = Field(default=None, min_length=1)
    rejected_by: str | None = Field(default=None, min_length=1)
    note: str = Field(default="", max_length=1000)
