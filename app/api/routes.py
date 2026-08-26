"""Thin FastAPI routes exposing reusable Pushan capabilities."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from app.agents.agent_service import run_pushan_agent

from app.database.repository import (
    get_action_history,
    get_decision_history,
    get_sensor_history,
)
from app.ml.predict import predict_water_requirement
from app.models import FarmInput
from app.rag.qa_service import LLMNotConfiguredError, RAGGenerationError, answer_question
from app.services.assessment_service import build_irrigation_assessment
from app.services.sensor_service import FIELD_CONFIGURATIONS, get_latest_reading

from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ComparisonResponse,
    DirectPredictionRequest,
    FarmRecommendationRequest,
    FieldResponse,
    HealthResponse,
    IrrigationAssessmentResponse,
    KnowledgeAnswerResponse,
    KnowledgeQuestionRequest,
    MLPredictionResponse,
    OperationalResponse,
    RuleBasedResponse,
    SensorResponse,
)


router = APIRouter()


@router.post("/agent/run", response_model=AgentRunResponse, tags=["Agent"])
def run_agent(payload: AgentRunRequest, request: Request) -> AgentRunResponse:
    """Run the controlled LangGraph workflow through its service boundary."""
    result = run_pushan_agent(
        payload.message,
        payload.field_id,
        model_path=request.app.state.model_path,
        vector_store_path=request.app.state.vector_store_path,
    )
    return AgentRunResponse(**result.__dict__)


@router.post(
    "/knowledge/ask",
    response_model=KnowledgeAnswerResponse,
    tags=["Knowledge"],
)
def ask_knowledge(
    payload: KnowledgeQuestionRequest,
    request: Request,
) -> KnowledgeAnswerResponse:
    """Return a generated answer grounded in retrieved Pushan documents."""
    try:
        result = answer_question(
            payload.question,
            persist_path=request.app.state.vector_store_path,
        )
    except (FileNotFoundError, LLMNotConfiguredError, RAGGenerationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return KnowledgeAnswerResponse(answer=result.answer, sources=result.sources)


@router.get("/health", response_model=HealthResponse, tags=["Service"])
def health() -> HealthResponse:
    """Report service availability without touching ML or SQLite."""
    return HealthResponse(status="ok", service="Pushan", version="0.8")


@router.get("/fields", response_model=list[FieldResponse], tags=["Fields"])
def list_fields() -> list[FieldResponse]:
    """List deterministic fields and their central metadata."""
    return [
        FieldResponse(field_id=field_id, **configuration)
        for field_id, configuration in FIELD_CONFIGURATIONS.items()
    ]


@router.get(
    "/fields/{field_id}/sensor",
    response_model=SensorResponse,
    tags=["Fields"],
)
def current_sensor_reading(field_id: str) -> SensorResponse:
    """Return the existing sensor service's current field reading."""
    try:
        return SensorResponse.model_validate(get_latest_reading(field_id), from_attributes=True)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/irrigation/recommend",
    response_model=IrrigationAssessmentResponse,
    tags=["Irrigation"],
)
def irrigation_recommendation(
    payload: FarmRecommendationRequest,
    request: Request,
) -> IrrigationAssessmentResponse:
    """Run and persist the complete rule, ML, and operational assessment."""
    try:
        assessment = build_irrigation_assessment(
            **payload.model_dump(),
            database_path=request.app.state.database_path,
            model_path=request.app.state.model_path,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is unavailable. Run 'python -m app.ml.train' first.",
        ) from error

    return IrrigationAssessmentResponse(
        field_id=assessment.field_id,
        sensor=SensorResponse.model_validate(
            assessment.sensor_reading,
            from_attributes=True,
        ),
        rule_based=RuleBasedResponse(
            irrigation_required=assessment.recommendation.irrigation_required,
            recommended_water_litres=assessment.recommendation.recommended_water_litres,
            risk_level=assessment.recommendation.risk_level,
            reason=assessment.recommendation.reason,
        ),
        ml=MLPredictionResponse(
            predicted_water_litres=assessment.ml_predicted_water_litres
        ),
        comparison=ComparisonResponse(
            absolute_difference_litres=assessment.absolute_difference_litres,
            difference_percentage=assessment.difference_percentage,
        ),
        operational=OperationalResponse(
            execution_possible=assessment.operational_decision.execution_possible,
            action_required=assessment.operational_decision.action_required,
            reason=assessment.operational_decision.reason,
        ),
    )


@router.post("/ml/predict", response_model=MLPredictionResponse, tags=["ML"])
def ml_prediction(
    payload: DirectPredictionRequest,
    request: Request,
) -> MLPredictionResponse:
    """Return an advisory ML estimate for directly supplied farm conditions."""
    farm_input = FarmInput(**payload.model_dump())
    try:
        prediction = predict_water_requirement(farm_input, request.app.state.model_path)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is unavailable. Run 'python -m app.ml.train' first.",
        ) from error
    return MLPredictionResponse(predicted_water_litres=prediction)


@router.get("/fields/{field_id}/history/sensors", tags=["History"])
def sensor_history(
    field_id: str,
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, Any]]:
    _ensure_known_field(field_id)
    return get_sensor_history(field_id, limit, request.app.state.database_path)


@router.get("/fields/{field_id}/history/decisions", tags=["History"])
def decision_history(
    field_id: str,
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, Any]]:
    _ensure_known_field(field_id)
    return get_decision_history(field_id, limit, request.app.state.database_path)


@router.get("/fields/{field_id}/history/actions", tags=["History"])
def action_history(
    field_id: str,
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, Any]]:
    _ensure_known_field(field_id)
    return get_action_history(field_id, limit, request.app.state.database_path)


def _ensure_known_field(field_id: str) -> None:
    """Convert an unknown configured field into a consistent API error."""
    if field_id.upper() not in FIELD_CONFIGURATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown field ID: {field_id}")
