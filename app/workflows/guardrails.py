"""Deterministic guardrails between recommendations and execution."""

from dataclasses import dataclass
from typing import Any

from .config import MAX_AUTO_APPROVED_WATER_LITRES


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    approval_required: bool
    risk_level: str
    blocked_reason: str | None
    guardrail_flags: list[str]


def evaluate_guardrails(
    sensor: dict[str, Any],
    recommendation: dict[str, Any],
    operational: dict[str, Any],
) -> GuardrailResult:
    """Apply safety policy without consulting an LLM or ML prediction."""
    flags: list[str] = []
    if sensor["sensor_status"] == "FAULTY":
        return GuardrailResult(False, False, recommendation["risk_level"],
                               "Faulty sensor must be inspected.", ["SENSOR_FAULT"])
    if sensor["pump_status"] == "OFFLINE" and recommendation["irrigation_required"]:
        return GuardrailResult(False, False, recommendation["risk_level"],
                               "Pump is offline.", ["PUMP_OFFLINE"])
    if sensor["water_available_litres"] < recommendation["recommended_water_litres"]:
        return GuardrailResult(False, False, recommendation["risk_level"],
                               "Available water is insufficient.", ["INSUFFICIENT_WATER"])
    if not recommendation["irrigation_required"]:
        return GuardrailResult(True, False, recommendation["risk_level"], None, ["NO_ACTION"])
    if not operational["execution_possible"]:
        return GuardrailResult(False, False, recommendation["risk_level"],
                               operational["reason"], ["OPERATIONALLY_BLOCKED"])
    if recommendation["recommended_water_litres"] > MAX_AUTO_APPROVED_WATER_LITRES:
        flags.append("HIGH_VOLUME")
    if recommendation["risk_level"] == "HIGH":
        flags.append("HIGH_RISK")
    return GuardrailResult(True, bool(flags), recommendation["risk_level"], None, flags)
